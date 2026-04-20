import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    MAX_CONCURRENCY: int = int(os.getenv("MAX_CONCURRENCY", 20))
    OUTPUT_BASE_FOLDER: str = os.getenv("OUTPUT_FOLDER", "parsed_content")
    VALKEY_HOST: str = os.getenv("VALKEY_HOST", "localhost")


settings = Settings()
