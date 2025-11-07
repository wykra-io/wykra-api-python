from functools import lru_cache
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseModel):
    # FastAPI
    app_name: str = "Wykra API"
    api_v1_prefix: str = "/api/v1"

    # Bright Data
    brightdata_api_token: str | None = os.getenv("BRIGHTDATA_API_TOKEN")
    # Your "Instagram - Profiles by username" (or similar) dataset/scraper id
    brightdata_instagram_dataset_id: str | None = os.getenv("BRIGHTDATA_INSTAGRAM_DATASET_ID")

    # OpenRouter (OpenAI-compatible endpoint)
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    # Any OpenRouter chat model id, override in .env
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

    # Misc
    environment: str = os.getenv("ENVIRONMENT", "local")


@lru_cache
def get_settings() -> Settings:
    return Settings()
