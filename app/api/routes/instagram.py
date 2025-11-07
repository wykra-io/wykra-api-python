import logging
from fastapi import APIRouter, HTTPException, Query

from app.services.brightdata import fetch_instagram_profile, BrightDataError
from app.agents.instagram_analyzer import analyze_profile
from app.models.instagram import InstagramAnalysis

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/analysis", response_model=InstagramAnalysis)
async def analyze_instagram_profile(
    profile: str = Query(..., description="Instagram username (without @)")
):
    logger.info(f"Analysis request for profile: {profile}")
    try:
        ig_profile = await fetch_instagram_profile(profile)
    except BrightDataError as e:
        logger.error(f"Bright Data error for {profile}: {e}")
        raise HTTPException(status_code=502, detail=str(e))

    analysis = await analyze_profile(ig_profile)
    logger.info(f"Analysis complete for {profile}")
    return analysis
