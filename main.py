import logging

from fastapi import FastAPI
from api.endpoints import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

app = FastAPI(title="Async Web Crawler", version="1.0.0")
app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Async Crawler API. Go to /docs for documentation."
    }
