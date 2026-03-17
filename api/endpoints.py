import os

import valkey
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List

from schemas import CrawlStartRequest, CrawlJobStatus, CrawlJobResult
from core.manager import CrawlerManager

from config import settings

router = APIRouter(prefix="/crawl", tags=["crawl"])
manager = CrawlerManager()
vk = valkey.Valkey(host=settings.VALKEY_HOST, port=6379, db=0, decode_responses=True)
os.makedirs(settings.OUTPUT_BASE_FOLDER,exist_ok=True)

@router.post("/start", response_model=dict)
async def start_crawl(request: CrawlStartRequest):
    job_id = await manager.start_job(
        seeds=[str(url) for url in request.seeds],
        max_concurrency=request.max_concurrency
    )
    return {"job_id": job_id, "message": "Crawl job started"}

@router.get("/{job_id}/status", response_model=CrawlJobStatus)
async def job_status(job_id: str):
    crawler = manager.get_job(job_id)
    if not crawler:
        raise HTTPException(status_code=404, detail="Job not found")
    task = manager.tasks.get(job_id)
    status = "running"
    if task and task.done():
        status = "completed" if not task.cancelled() and not task.exception() else "failed"
    return CrawlJobStatus(
        job_id=job_id,
        status=status,
        visited_count=len(crawler.visited),
        queue_size=crawler.queue.qsize(),
        output_dir=settings.OUTPUT_BASE_FOLDER
    )

@router.get("/results", response_model=List[CrawlJobResult])
async def job_results():
    output_dir = settings.OUTPUT_BASE_FOLDER
    if not os.path.exists(output_dir):
        return []

    results = []
    for fname in os.listdir(output_dir):
        if fname.endswith(".md"):
            image = vk.get(vk.get(fname)) if vk.get(vk.get(fname)) is not None else ''  # url -> image

            results.append(
                CrawlJobResult(
                    url=vk.get(fname),
                    markdown_file=fname,
                    image_path=image
                )
            )
    return results

@router.post("/clear")
async def clear_results():
    output_dir = settings.OUTPUT_BASE_FOLDER
    for fname in os.listdir(output_dir):
        p = os.path.join(output_dir, fname)
        os.remove(p)
    vk.flushall()
    return {"Folder cleared"}

@router.get("/file/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(settings.OUTPUT_BASE_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="text/markdown", filename=filename)

@router.get("/file/{filename}/url")
async def get_file_url(filename: str):
    file_path = os.path.join(settings.OUTPUT_BASE_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    url = vk.get(filename)
    if url is None:
        raise HTTPException(status_code=404, detail="File URL not found")
    return {"url": url}

@router.post("/{job_id}/stop")
async def stop_job(job_id: str):
    crawler = manager.get_job(job_id)
    if not crawler:
        raise HTTPException(status_code=404, detail="Job not found")
    crawler.stop()
    return {"message": "Job stopping"}

@router.get("/image")
async def get_image_by_url(url: str):
    image_path = os.path.join(settings.OUTPUT_BASE_FOLDER, vk.get(url))
    if not image_path:
        raise HTTPException(status_code=404, detail="Image not found")

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image file missing")

    return FileResponse(image_path)