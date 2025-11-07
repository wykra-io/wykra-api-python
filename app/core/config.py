import logging
from functools import lru_cache
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s :: %(levelname)s :: %(processName)s :: %(threadName)s :: %(filename)s :: %(funcName)s :: %(message)s",
)
logger = logging.getLogger(__name__)


class Settings(BaseModel):
    app_name: str = "Wykra API"
    api_v1_prefix: str = "/api/v1"

    brightdata_api_token: str | None = os.getenv("BRIGHTDATA_API_TOKEN")
    brightdata_instagram_dataset_id: str | None = os.getenv("BRIGHTDATA_INSTAGRAM_DATASET_ID")
    brightdata_poll_interval: int = int(os.getenv("BRIGHTDATA_POLL_INTERVAL", "5"))
    brightdata_max_wait_time: int = int(os.getenv("BRIGHTDATA_MAX_WAIT_TIME", "300"))

    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

    environment: str = os.getenv("ENVIRONMENT", "local")


@lru_cache
def get_settings() -> Settings:
    return Settings()
