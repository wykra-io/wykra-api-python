import asyncio
import logging
from typing import Any, Dict, List

import httpx

from app.core.config import get_settings
from app.models.instagram import InstagramProfile

logger = logging.getLogger(__name__)
settings = get_settings()


class BrightDataError(Exception):
    pass


async def fetch_instagram_profile(username: str) -> InstagramProfile:
    """
    1) Триггерит Bright Data Instagram dataset для одного username.
    2) Ждет, пока snapshot станет ready.
    3) Забирает snapshot (JSON), берет первый объект.
    4) Маппит в InstagramProfile.
    """
    if not settings.brightdata_api_token or not settings.brightdata_instagram_dataset_id:
        raise BrightDataError("Bright Data credentials or dataset ID are not configured")

    headers = {
        "Authorization": f"Bearer {settings.brightdata_api_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        snapshot_id = await _trigger_snapshot(client, headers, username)
        await _wait_for_snapshot_ready(client, headers, snapshot_id)
        raw_profile = await _fetch_snapshot_profile(client, headers, snapshot_id)

    profile = InstagramProfile(
        username=raw_profile.get("account") or username,
        full_name=raw_profile.get("profile_name") or raw_profile.get("full_name"),
        bio=raw_profile.get("biography"),
        followers=raw_profile.get("followers"),
        following=raw_profile.get("following"),
        posts_count=raw_profile.get("posts_count"),
        is_verified=raw_profile.get("is_verified", False),
        is_business=(
            raw_profile.get("is_business_account")
            or raw_profile.get("is_professional_account")
            or False
        ),
        profile_url=raw_profile.get("profile_url") or raw_profile.get("url"),
        raw=raw_profile,
    )

    logger.info("Successfully built InstagramProfile for %s", profile.username)
    return profile


async def _trigger_snapshot(
    client: httpx.AsyncClient,
    headers: Dict[str, str],
    username: str,
) -> str:
    """
    Делает /datasets/v3/trigger и возвращает snapshot_id.
    Ожидаемый ответ: {"snapshot_id": "sd_..."}.
    """
    trigger_url = (
        "https://api.brightdata.com/datasets/v3/trigger"
        f"?dataset_id={settings.brightdata_instagram_dataset_id}"
        "&include_errors=true"
        "&type=discover_new"
        "&discover_by=user_name"
    )

    payload = [{"user_name": username}]
    logger.info("Triggering Bright Data scrape for username=%s", username)

    resp = await client.post(trigger_url, headers=headers, json=payload)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Bright Data trigger failed: %s", exc.response.text)
        raise BrightDataError(f"Bright Data trigger error: {exc.response.text}") from exc

    data = resp.json()
    logger.debug("Trigger response: %s", data)

    snapshot_id = data.get("snapshot_id")
    if not snapshot_id:
        raise BrightDataError(f"Unexpected trigger response (no snapshot_id): {data}")

    logger.info("Snapshot ID from trigger: %s", snapshot_id)
    return snapshot_id


async def _wait_for_snapshot_ready(
    client: httpx.AsyncClient,
    headers: Dict[str, str],
    snapshot_id: str,
) -> None:
    """
    Крутит /datasets/v3/progress/{snapshot_id} пока не будет ready/completed/done,
    либо не кончится max_wait_time.
    """
    progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
    interval = settings.brightdata_poll_interval
    max_attempts = settings.brightdata_max_wait_time // interval

    logger.info(
        "Polling snapshot %s (max %s attempts, %ss interval)",
        snapshot_id,
        max_attempts,
        interval,
    )

    last_status = None

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            await asyncio.sleep(interval)

        logger.debug(
            "Progress attempt %s/%s for snapshot %s",
            attempt,
            max_attempts,
            snapshot_id,
        )

        resp = await client.get(progress_url, headers=headers)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Progress error: %s", exc.response.text)
            raise BrightDataError(f"Bright Data progress error: {exc.response.text}") from exc

        data = resp.json()
        logger.debug("Progress data: %s", data)

        status = (data or {}).get("status") or (data or {}).get("state")
        last_status = status

        if status in ("ready", "completed", "done"):
            logger.info("Snapshot %s is %s", snapshot_id, status)
            return

        if status in ("failed", "error"):
            raise BrightDataError(f"Bright Data snapshot {snapshot_id} failed: {data}")

    raise BrightDataError(
        f"Bright Data snapshot {snapshot_id} not ready after "
        f"{settings.brightdata_max_wait_time} seconds (last status={last_status})"
    )


async def _fetch_snapshot_profile(
    client: httpx.AsyncClient,
    headers: Dict[str, str],
    snapshot_id: str,
) -> Dict[str, Any]:
    """
    Забирает /datasets/v3/snapshot/{snapshot_id},
    ожидает list[dict], возвращает первый объект.
    """
    snapshot_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
    logger.info("Fetching snapshot JSON from %s", snapshot_url)

    resp = await client.get(snapshot_url, headers=headers)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Snapshot fetch error: %s", exc.response.text)
        raise BrightDataError(f"Bright Data snapshot fetch error: {exc.response.text}") from exc

    data = resp.json()
    logger.debug("Snapshot data: %s", data)

    if not isinstance(data, list) or not data:
        raise BrightDataError(f"Snapshot {snapshot_id} returned empty or invalid JSON: {data}")

    profile = data[0]
    if not isinstance(profile, dict):
        raise BrightDataError(
            f"Snapshot {snapshot_id} first item is not an object: {profile}"
        )

    return profile
