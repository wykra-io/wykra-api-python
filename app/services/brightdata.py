import asyncio
import logging
import csv
import io
from typing import Any, Dict, Optional, List

import httpx

from app.core.config import get_settings
from app.models.instagram import InstagramProfile

logger = logging.getLogger(__name__)
settings = get_settings()


class BrightDataError(Exception):
    pass


async def fetch_instagram_profile(username: str) -> InstagramProfile:
    if not settings.brightdata_api_token or not settings.brightdata_instagram_dataset_id:
        raise BrightDataError("Bright Data credentials or dataset ID are not configured")

    headers = {
        "Authorization": f"Bearer {settings.brightdata_api_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        trigger_url = (
            "https://api.brightdata.com/datasets/v3/trigger"
            f"?dataset_id={settings.brightdata_instagram_dataset_id}"
            "&include_errors=true"
            "&type=discover_new"
            "&discover_by=user_name"
        )

        payload: List[Dict[str, Any]] = [{"user_name": username}]

        logger.info(f"Triggering Bright Data scrape for username: {username}")
        trigger_resp = await client.post(trigger_url, headers=headers, json=payload)

        try:
            trigger_resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(f"Bright Data trigger failed: {exc.response.text}")
            raise BrightDataError(f"Bright Data trigger error: {exc.response.text}") from exc

        trigger_data = trigger_resp.json()
        logger.info(f"Trigger response: {trigger_data}")

        snapshot_id = _extract_snapshot_id(trigger_data)
        if not snapshot_id:
            raise BrightDataError(f"Could not find snapshot_id in trigger response: {trigger_data}")

        logger.info(f"Snapshot ID from trigger: {snapshot_id}")

        progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
        max_attempts = settings.brightdata_max_wait_time // settings.brightdata_poll_interval

        logger.info(
            f"Polling for snapshot progress (max {max_attempts} attempts, "
            f"{settings.brightdata_poll_interval}s interval)"
        )

        status = None
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                await asyncio.sleep(settings.brightdata_poll_interval)

            logger.info(f"Progress attempt {attempt}/{max_attempts}")
            progress_resp = await client.get(progress_url, headers=headers)
            try:
                progress_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error(f"Progress error: {exc.response.text}")
                raise BrightDataError(f"Bright Data progress error: {exc.response.text}") from exc

            progress_data = progress_resp.json()
            logger.info(f"Progress data: {progress_data}")

            status = (progress_data or {}).get("status") or (progress_data or {}).get("state")
            if status in ("ready", "completed", "done"):
                logger.info(f"Snapshot {snapshot_id} is {status}")
                break
            if status in ("failed", "error"):
                raise BrightDataError(f"Bright Data snapshot failed: {progress_data}")

        if status not in ("ready", "completed", "done"):
            raise BrightDataError(
                f"Bright Data snapshot not ready after {settings.brightdata_max_wait_time} seconds"
            )

        snapshot_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=csv"
        logger.info(f"Fetching snapshot CSV from {snapshot_url}")

        snapshot_resp = await client.get(snapshot_url, headers=headers)
        try:
            snapshot_resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(f"Snapshot fetch error: {exc.response.text}")
            raise BrightDataError(f"Bright Data snapshot fetch error: {exc.response.text}") from exc

        csv_text = snapshot_resp.text
        if not csv_text.strip():
            raise BrightDataError("Bright Data returned empty CSV for snapshot")

        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        if not rows:
            raise BrightDataError("Bright Data CSV has no rows")

        raw_profile = _find_row_for_username(rows, username)
        if not raw_profile:
            raw_profile = rows[0]
            logger.warning(
                f"No exact match for username={username}, using first row username={raw_profile.get('user_name') or raw_profile.get('username')}"
            )

        profile = InstagramProfile(
            username=(
                raw_profile.get("user_name")
                or raw_profile.get("username")
                or raw_profile.get("account")
                or username
            ),
            full_name=(
                raw_profile.get("full_name")
                or raw_profile.get("profile_name")
                or raw_profile.get("name")
            ),
            bio=raw_profile.get("bio") or raw_profile.get("biography"),
            followers=_to_int(
                raw_profile.get("followers")
                or raw_profile.get("followers_count")
            ),
            following=_to_int(
                raw_profile.get("following")
                or raw_profile.get("following_count")
            ),
            posts_count=_to_int(
                raw_profile.get("posts_count")
                or raw_profile.get("posts")
                or raw_profile.get("media_count")
            ),
            is_verified=_to_bool(raw_profile.get("is_verified")),
            is_business=_to_bool(
                raw_profile.get("is_business_account")
                or raw_profile.get("is_professional_account")
            ),
            profile_url=raw_profile.get("profile_url") or raw_profile.get("url"),
            raw=raw_profile,
        )

        logger.info(f"Successfully built InstagramProfile for {profile.username}")
        return profile


def _extract_snapshot_id(trigger_data: Any) -> Optional[str]:
    if isinstance(trigger_data, dict):
        snap = (
            trigger_data.get("snapshot_id")
            or trigger_data.get("snapshot")
            or trigger_data.get("id")
            or trigger_data.get("job_id")
            or trigger_data.get("snapshotId")
        )
        if isinstance(snap, str):
            return snap

    if isinstance(trigger_data, list):
        for item in trigger_data:
            if not isinstance(item, dict):
                continue
            snap = (
                item.get("snapshot_id")
                or item.get("snapshot")
                or item.get("id")
                or item.get("job_id")
                or item.get("snapshotId")
            )
            if isinstance(snap, str):
                return snap

    if isinstance(trigger_data, dict):
        for _, v in trigger_data.items():
            if isinstance(v, str) and v.startswith("sd_"):
                return v
    if isinstance(trigger_data, list):
        for item in trigger_data:
            if isinstance(item, dict):
                for _, v in item.items():
                    if isinstance(v, str) and v.startswith("sd_"):
                        return v
    return None


def _find_row_for_username(rows: List[Dict[str, Any]], username: str) -> Optional[Dict[str, Any]]:
    u = username.lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        candidate = (
            row.get("user_name")
            or row.get("username")
            or row.get("account")
        )
        if candidate and candidate.lower() == u:
            return row
    return None


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    if isinstance(value, (int, float)):
        return value != 0
    return False
