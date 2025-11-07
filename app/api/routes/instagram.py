# app/api/routes/instagram.py

from fastapi import APIRouter, HTTPException, Query

from app.services.brightdata import fetch_instagram_profile, BrightDataError
from app.agents.instagram_analyzer import analyze_profile
from app.models.instagram import InstagramAnalysis

router = APIRouter()  


@router.get("/analysis", response_model=InstagramAnalysis)
async def analyze_instagram_profile(
    profile: str = Query(..., description="Instagram username (without @)")
):
    """
    Fetch Instagram profile data from Bright Data and return AI-powered analysis.
    """
    try:
        ig_profile = await fetch_instagram_profile(profile)
    except BrightDataError as e:
        raise HTTPException(status_code=502, detail=str(e))

    analysis = await analyze_profile(ig_profile)
    return analysis
