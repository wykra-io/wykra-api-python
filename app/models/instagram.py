from typing import Any, Optional, List
from pydantic import BaseModel, HttpUrl


class InstagramProfile(BaseModel):
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    posts_count: Optional[int] = None
    is_verified: Optional[bool] = None
    is_business: Optional[bool] = None
    profile_url: Optional[HttpUrl] = None
    raw: dict[str, Any]


class InstagramAnalysis(BaseModel):
    handle: str
    profile_url: Optional[HttpUrl] = None

    summary: str                   # overall summary
    topics: List[str]              # main content themes
    audience: str                  # who they seem to reach
    strengths: List[str]           # good signals
    risks: List[str]               # red flags / concerns
    fit_score: float               # 0–100 collaboration suitability
