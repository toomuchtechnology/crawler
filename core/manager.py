import asyncio
import uuid
from typing import Dict, Optional

from core.crawler import AsyncCrawler
from config import settings


class CrawlerManager:
    def __init__(self):
        self.jobs: Dict[str, AsyncCrawler] = {}
        self.tasks: Dict[str, asyncio.Task] = {}

    async def start_job(
        self, seeds: list, max_concurrency: Optional[int] = None
    ) -> str:
        job_id = str(uuid.uuid4())
        output_dir = settings.OUTPUT_BASE_FOLDER
        concurrency = max_concurrency or settings.MAX_CONCURRENCY

        crawler = AsyncCrawler(job_id, seeds, concurrency, output_dir)
        self.jobs[job_id] = crawler

        task = asyncio.create_task(crawler.run(), name=f"crawl-{job_id}")
        self.tasks[job_id] = task

        def done_callback(_):
            self.jobs.pop(job_id, None)
            self.tasks.pop(job_id, None)

        task.add_done_callback(done_callback)

        return job_id

    def get_job(self, job_id: str) -> Optional[AsyncCrawler]:
        return self.jobs.get(job_id)

    def stop_job(self, job_id: str):
        crawler = self.jobs.get(job_id)
        if crawler:
            crawler.stop()
