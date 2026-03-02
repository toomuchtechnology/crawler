import time

t0 = time.time()

import asyncio
import aiohttp
import os
import logging
from urllib.parse import urljoin, urldefrag, urlparse
from bs4 import BeautifulSoup
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from docling_core.types.doc import ImageRefMode
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logging.info(f"IMPORTED LIBRARIES IN {(time.time()-t0):.3f} SECONDS")


load_dotenv()

MAX_CONCURRENCY = int(os.getenv('MAX_CONCURRENCY', 20))
SEED_FILE = os.getenv('SEED_FILE', 'seeds.txt')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', 'parsed_content')


class AsyncCrawler:
    def __init__(self, seeds_file, output_dir):
        self.seeds_file = seeds_file
        self.output_dir = output_dir
        self.visited = set()
        self.queue = asyncio.Queue()
        self.converter = DocumentConverter()
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        self.allowed_domains = set()

        os.makedirs(self.output_dir, exist_ok=True)

    async def load_seeds(self):
        with open(self.seeds_file, "r") as f:
            for line in f:
                url = line.strip()
                if not url:
                    continue

                parsed = urlparse(url)
                base_domain = self._get_base_domain(parsed.netloc)
                self.allowed_domains.add(base_domain)

                await self.queue.put(url)

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
            logging.error(f"Fetch failed: {url} | {e}")
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
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)

    async def process_url(self, session, url):
        if url in self.visited:
            return

        if not self._is_allowed(url):
            logging.info(f"Skipped (outside domain): {url}")
            return

        self.visited.add(url)

        html = await self.fetch(session, url)
        if not html:
            logging.error(f"Failed to parse: {url}")
            return

        try:
            result = self.converter.convert_string(
                html,
                format=InputFormat.HTML
            )
            markdown = result.document.export_to_markdown(image_mode=ImageRefMode.REFERENCED)
            self.save_markdown(url, markdown)
            logging.info(f"Parsed successfully: {url}")
        except Exception as e:
            logging.error(f"Docling conversion failed: {url} | {e}")
            return

        for link in self.extract_links(url, html):
            if link not in self.visited:
                await self.queue.put(link)

    async def worker(self, session):
        while True:
            url = await self.queue.get()
            await self.process_url(session, url)
            self.queue.task_done()

    async def run(self):
        await self.load_seeds()

        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.create_task(self.worker(session))
                for _ in range(MAX_CONCURRENCY)
            ]

            await self.queue.join()

            for task in tasks:
                task.cancel()


if __name__ == "__main__":
    t1 = time.time()
    crawler = AsyncCrawler(SEED_FILE, OUTPUT_FOLDER)
    t2 = time.time()
    dt1 = t2-t1
    logging.info(f"CREATED CRAWLER IN {(t2-t1):.3f} SECONDS")
    asyncio.run(crawler.run())
    t3 = time.time()
    logging.info(f"FINISHED CRAWLING IN {(t3-t2):.3f} SECONDS")