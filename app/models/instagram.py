from typing import Any, Optional, List
from pydantic import BaseModel


class InstagramProfile(BaseModel):
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    posts_count: Optional[int] = None
    is_verified: Optional[bool] = None
    is_business: Optional[bool] = None
    profile_url: Optional[str] = None
    raw: dict[str, Any]


class InstagramAnalysis(BaseModel):
    summary: str
    qualityScore: int
    topic: str
    niche: Optional[str] = None
    sponsoredFrequency: str
    contentAuthenticity: str
    followerAuthenticity: str
    visibleBrands: List[str]
    engagementStrength: str
    postsAnalysis: str
    hashtagsStatistics: str
