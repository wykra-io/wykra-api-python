from typing import Any, Dict, Optional

import httpx

from app.core.config import get_settings
from app.models.instagram import InstagramProfile

settings = get_settings()


class BrightDataError(Exception):
    pass


async def fetch_instagram_profile(username: str) -> InstagramProfile:
    """
    Fetch Instagram profile data for a given username via Bright Data.

    This assumes you have configured an "Instagram - Profiles by username" scraper
    or dataset and exposed its id via BRIGHTDATA_INSTAGRAM_DATASET_ID.

    Adjust payload -> keys based on your actual Bright Data endpoint.
    See the Web Scraper / Social Media Scrapers docs for exact schema.
    """
    if not settings.brightdata_api_token or not settings.brightdata_instagram_dataset_id:
        raise BrightDataError("Bright Data credentials or dataset ID are not configured")

    url = (
        "https://api.brightdata.com/datasets/v3/scrape"
        f"?dataset_id={settings.brightdata_instagram_dataset_id}"
        "&notify=false&include_errors=true&type=discover_new&discover_by=user_name"
    )

    # Bright Data API expects input array with user_name field
    payload: Dict[str, Any] = {
        "input": [{"user_name": username}]
    }

    headers = {
        "Authorization": f"Bearer {settings.brightdata_api_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise BrightDataError(f"Bright Data API error: {exc.response.text}") from exc

        data = resp.json()

    if not isinstance(data, list) or not data:
        raise BrightDataError("Bright Data returned empty or invalid response")

    raw_profile = data[0]

    username_value = (
        raw_profile.get("account")
        or raw_profile.get("username")
        or username
    )
    profile_url = raw_profile.get("profile_url") or raw_profile.get("url")

    profile = InstagramProfile(
        username=username_value,
        full_name=raw_profile.get("profile_name") or raw_profile.get("full_name") or raw_profile.get("name"),
        bio=raw_profile.get("bio") or raw_profile.get("biography"),
        followers=_to_int(raw_profile.get("followers")),
        following=_to_int(raw_profile.get("following")),
        posts_count=_to_int(raw_profile.get("posts_count") or raw_profile.get("posts")),
        is_verified=raw_profile.get("is_verified", False),
        is_business=raw_profile.get("is_business_account", False) or raw_profile.get("is_professional_account", False),
        profile_url=profile_url,
        raw=raw_profile,
    )

    return profile


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
