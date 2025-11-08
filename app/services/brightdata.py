import asyncio
import logging
from typing import Any, Dict, List

import httpx

from app.core.config import get_settings
from app.models.instagram import InstagramProfile

logger = logging.getLogger(__name__)
settings = get_settings()


class BrightDataError(Exception):
    """Raised when the Bright Data API returns an error or invalid response."""


async def fetch_instagram_profile(username: str) -> InstagramProfile:
    """Fetch and normalize an Instagram profile using the Bright Data API.

    Args:
        username: The Instagram handle to fetch, without the leading ``@``.

    Returns:
        A populated :class:`InstagramProfile` built from the Bright Data dataset.

    Raises:
        BrightDataError: If the Bright Data credentials are missing or the API
            returns an unexpected response.
    """

    if (
        not settings.brightdata_api_token
        or not settings.brightdata_instagram_dataset_id
    ):
        raise BrightDataError(
            "Bright Data credentials or dataset ID are not configured"
        )

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
    """Trigger a Bright Data snapshot request for an Instagram username.

    Args:
        client: The HTTP client used to communicate with Bright Data.
        headers: HTTP headers including authorization metadata.
        username: The Instagram handle to request.

    Returns:
        The Bright Data ``snapshot_id`` that can be polled for progress.

    Raises:
        BrightDataError: If the trigger request fails or the response is missing
            a ``snapshot_id``.
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
        raise BrightDataError(
            f"Bright Data trigger error: {exc.response.text}"
        ) from exc

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
    """Poll the Bright Data API until a snapshot finishes building.

    Args:
        client: The HTTP client used to communicate with Bright Data.
        headers: HTTP headers including authorization metadata.
        snapshot_id: The identifier returned by :func:`_trigger_snapshot`.

    Raises:
        BrightDataError: If polling fails, the snapshot reports an error, or the
            maximum wait time is exceeded.
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
            raise BrightDataError(
                f"Bright Data progress error: {exc.response.text}"
            ) from exc

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
    """Fetch the completed snapshot payload from Bright Data.

    Args:
        client: The HTTP client used to communicate with Bright Data.
        headers: HTTP headers including authorization metadata.
        snapshot_id: The identifier returned by :func:`_trigger_snapshot`.

    Returns:
        A dictionary containing the raw profile data extracted from the
        snapshot.

    Raises:
        BrightDataError: If the API returns an error, an unexpected payload, or
            the snapshot never becomes available.
    """

    snapshot_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
    interval = settings.brightdata_poll_interval
    max_attempts = 5

    for attempt in range(1, max_attempts + 1):
        logger.info(
            "Fetching snapshot JSON (attempt %s/%s) from %s",
            attempt,
            max_attempts,
            snapshot_url,
        )

        resp = await client.get(snapshot_url, headers=headers)

        if resp.status_code == 202:
            logger.info("Snapshot %s not ready yet (202 Accepted)", snapshot_id)
        else:
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("Snapshot fetch error: %s", exc.response.text)
                raise BrightDataError(
                    f"Bright Data snapshot fetch error: {exc.response.text}"
                ) from exc

            data = resp.json()
            logger.debug("Snapshot data: %s", data)

            if isinstance(data, list) and data:
                profile = data[0]
                if not isinstance(profile, dict):
                    raise BrightDataError(
                        f"Snapshot {snapshot_id} first item is not an object: {profile}"
                    )
                return profile

            if isinstance(data, dict):
                status = data.get("status")
                message = str(data.get("message", "")).lower()

                if status in ("building",) or "not ready yet" in message:
                    logger.info(
                        "Snapshot %s still building according to body (status=%s)",
                        snapshot_id,
                        status,
                    )
                elif (
                    data.get("account")
                    or data.get("profile_name")
                    or data.get("full_name")
                ):
                    return data
                else:
                    raise BrightDataError(
                        f"Snapshot {snapshot_id} returned unexpected JSON object: {data}"
                    )

            logger.info(
                "Snapshot %s returned empty or invalid JSON structure: %s",
                snapshot_id,
                data,
            )

        if attempt < max_attempts:
            await asyncio.sleep(interval)

    raise BrightDataError(
        f"Snapshot {snapshot_id} not ready after {max_attempts} fetch attempts"
    )
