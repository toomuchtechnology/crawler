from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class CrawlStartRequest(BaseModel):
    seeds: List[HttpUrl]
    max_concurrency: Optional[int] = None

class CrawlJobStatus(BaseModel):
    job_id: str
    status: str
    visited_count: int
    queue_size: int
    output_dir: Optional[str] = None

class CrawlJobResult(BaseModel):
    url: str
    markdown_file: str
    image_path: str