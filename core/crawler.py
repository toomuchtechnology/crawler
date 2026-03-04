import asyncio
import logging
import os
from urllib.parse import urljoin, urldefrag, urlparse

import aiohttp
from bs4 import BeautifulSoup
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from docling_core.types.doc import ImageRefMode
import valkey

logger = logging.getLogger(__name__)

class AsyncCrawler:
    def __init__(self, job_id: str, seeds: list, max_concurrency: int, output_dir: str):
        self.job_id = job_id
        self.output_dir = output_dir
        self.visited = set()
        self.queue = asyncio.Queue()
        self.converter = DocumentConverter()
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.allowed_domains = set()
        self.valkey = valkey.Valkey(host="localhost", port=6379, db=0, decode_responses=True)
        self._stop_event = asyncio.Event()

        os.makedirs(self.output_dir, exist_ok=True)

        for url in seeds:
            parsed = urlparse(str(url))
            base_domain = self._get_base_domain(parsed.netloc)
            self.allowed_domains.add(base_domain)
            self.queue.put_nowait(str(url))

    def _get_base_domain(self, netloc):
        parts = netloc.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return netloc

    def _is_allowed(self, url):
        parsed = urlparse(url)
        base_domain = self._get_base_domain(parsed.netloc)
        return base_domain in self.allowed_domains

    async def fetch(self, session, url):
        try:
            async with self.semaphore:
                async with session.get(url, timeout=10) as response:
                    if (
                        response.status == 200
                        and "text/html" in response.headers.get("Content-Type", "")
                    ):
                        return await response.text()
        except Exception as e:
            logger.error(f"Fetch failed: {url} | {e}")
        return None

    def extract_links(self, base_url, html):
        soup = BeautifulSoup(html, "html.parser")
        links = set()
        for a_tag in soup.find_all("a", href=True):
            href = urljoin(base_url, a_tag["href"])
            href = urldefrag(href)[0]
            parsed = urlparse(href)
            if parsed.scheme in ("http", "https"):
                links.add(href)
        return links

    def save_markdown(self, url, markdown):
        parsed = urlparse(url)
        safe_path = parsed.netloc + parsed.path
        safe_path = safe_path.strip("/").replace("/", "_")
        if not safe_path:
            safe_path = "index"
        filename = f"{safe_path}.md"
        self.valkey.set(filename, url)
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)
        return filename

    async def process_url(self, session, url):
        if url in self.visited:
            return
        if not self._is_allowed(url):
            logger.info(f"Skipped (outside domain): {url}")
            return

        self.visited.add(url)

        html = await self.fetch(session, url)
        if not html:
            logger.error(f"Failed to parse: {url}")
            return

        try:
            result = self.converter.convert_string(html, format=InputFormat.HTML)
            markdown = result.document.export_to_markdown(image_mode=ImageRefMode.REFERENCED)
            filename = self.save_markdown(url, markdown)
            logger.info(f"Parsed successfully: {url} -> {filename}")
        except Exception as e:
            logger.error(f"Docling conversion failed: {url} | {e}")
            return

        for link in self.extract_links(url, html):
            if link not in self.visited:
                await self.queue.put(link)

    async def worker(self, session):
        while not self._stop_event.is_set():
            try:
                url = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            await self.process_url(session, url)
            self.queue.task_done()

    async def run(self):
        async with aiohttp.ClientSession() as session:
            workers = [
                asyncio.create_task(self.worker(session))
                for _ in range(self.semaphore._value)
            ]
            await self.queue.join()
            self._stop_event.set()
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

    def stop(self):
        self._stop_event.set()