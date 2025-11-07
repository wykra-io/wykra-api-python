import logging
from fastapi import FastAPI

from app.core.config import get_settings
from app.api.routes import instagram as instagram_routes

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title=settings.app_name)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment}


# /api/v1/instagram/analysis?profile=...
app.include_router(
    instagram_routes.router,
    prefix=f"{settings.api_v1_prefix}/instagram",
    tags=["instagram"],
)
