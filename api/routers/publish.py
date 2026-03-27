"""
Publish Router — Multi-platform social publishing via Zernio (Late) API.

Endpoints:
  POST /api/publish              — Publish content to connected platforms
  GET  /api/publish/accounts     — List connected social accounts
  GET  /api/publish/status/{id}  — Check publish status
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies.auth import CurrentUser, require_current_user
from api.dependencies.ownership import require_owned_content_record
from status.schemas import ContentLifecycleStatus
from status.service import InvalidTransitionError, get_status_service

router = APIRouter(prefix="/api/publish", tags=["publish"])

ZERNIO_BASE = "https://zernio.com/api/v1"


def _get_api_key() -> str:
    key = os.getenv("ZERNIO_API_KEY") or os.getenv("LATE_API_KEY")
    if not key:
        raise HTTPException(
            status_code=503,
            detail="ZERNIO_API_KEY not configured. Set it in your environment.",
        )
    return key


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


# ── Models ──


class PlatformTarget(BaseModel):
    platform: str = Field(..., description="Platform ID: twitter, linkedin, instagram, tiktok, etc.")
    account_id: str = Field(..., description="Connected account ID from Zernio")
    custom_content: Optional[str] = Field(None, description="Override content for this platform")


class PublishRequest(BaseModel):
    content: str = Field(..., description="Post content/text")
    platforms: List[PlatformTarget] = Field(..., min_length=1)
    title: Optional[str] = Field(None, description="Reference title")
    media_urls: List[str] = Field(default_factory=list, description="URLs of images/videos to attach")
    scheduled_for: Optional[str] = Field(None, description="ISO 8601 datetime for scheduling")
    publish_now: bool = Field(default=True, description="Publish immediately")
    tags: List[str] = Field(default_factory=list)
    content_record_id: Optional[str] = Field(None, description="Link to ContentRecord for status tracking")


class PublishResponse(BaseModel):
    success: bool
    post_id: Optional[str] = None
    status: str = "unknown"
    platform_urls: Dict[str, str] = Field(default_factory=dict)
    error: Optional[str] = None


# ── Endpoints ──


def _resolve_target_url(platform_urls: Dict[str, str]) -> Optional[str]:
    """Pick the best canonical target URL from the publish result."""
    if not platform_urls:
        return None

    for preferred in ("ghost", "wordpress", "linkedin", "twitter", "instagram", "youtube", "tiktok"):
        if preferred in platform_urls:
            return platform_urls[preferred]

    return next(iter(platform_urls.values()), None)


def _merge_publish_metadata(
    existing: Dict[str, Any],
    *,
    post_id: Optional[str],
    status: str,
    platform_urls: Dict[str, str],
    scheduled_for: Optional[str],
) -> Dict[str, Any]:
    """Merge Zernio publish data into the content metadata blob."""
    metadata = dict(existing)
    publish_meta = metadata.get("publish")
    publish_state = dict(publish_meta) if isinstance(publish_meta, dict) else {}

    publish_state.update(
        {
            "provider": "zernio",
            "post_id": post_id,
            "status": status,
            "platform_urls": platform_urls,
            "scheduled_for": scheduled_for,
            "synced_at": datetime.utcnow().isoformat(),
        }
    )

    metadata["publish"] = publish_state
    return metadata


def _persist_publish_result(
    *,
    content_record_id: str,
    current_user: CurrentUser,
    post_id: Optional[str],
    status: str,
    platform_urls: Dict[str, str],
    scheduled_for: Optional[str],
) -> None:
    """Persist publish metadata and lifecycle state back to the content record."""
    svc = get_status_service()
    record = svc.get_content(content_record_id)
    target_url = _resolve_target_url(platform_urls)
    metadata = _merge_publish_metadata(
        record.metadata or {},
        post_id=post_id,
        status=status,
        platform_urls=platform_urls,
        scheduled_for=scheduled_for,
    )

    svc.update_content(
        content_record_id,
        metadata=metadata,
        target_url=target_url,
    )

    lifecycle = str(record.status)
    if status == "scheduled":
        if lifecycle == ContentLifecycleStatus.APPROVED.value:
            svc.transition(
                content_record_id,
                ContentLifecycleStatus.SCHEDULED.value,
                current_user.user_id,
                reason="Queued in Zernio",
            )
        return

    if lifecycle in {
        ContentLifecycleStatus.APPROVED.value,
        ContentLifecycleStatus.SCHEDULED.value,
    }:
        svc.transition(
            content_record_id,
            ContentLifecycleStatus.PUBLISHING.value,
            current_user.user_id,
            reason="Publishing via Zernio",
        )
        lifecycle = ContentLifecycleStatus.PUBLISHING.value

    if lifecycle == ContentLifecycleStatus.PUBLISHING.value:
        svc.transition(
            content_record_id,
            ContentLifecycleStatus.PUBLISHED.value,
            current_user.user_id,
            reason="Published via Zernio",
        )


@router.post("", response_model=PublishResponse, summary="Publish content to social platforms")
async def publish_content(
    request: PublishRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Publish or schedule a post across multiple platforms via Zernio API."""
    if request.content_record_id:
        svc = get_status_service()
        await require_owned_content_record(request.content_record_id, current_user, svc)

    payload: Dict[str, Any] = {
        "content": request.content,
        "platforms": [
            {
                "platform": p.platform,
                "accountId": p.account_id,
                **({"customContent": {"text": p.custom_content}} if p.custom_content else {}),
            }
            for p in request.platforms
        ],
        "publishNow": request.publish_now,
    }

    if request.title:
        payload["title"] = request.title
    if request.tags:
        payload["tags"] = request.tags
    if request.media_urls:
        payload["media"] = [{"type": "image", "url": url} for url in request.media_urls]
    if request.scheduled_for and not request.publish_now:
        payload["scheduledFor"] = request.scheduled_for

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{ZERNIO_BASE}/posts", headers=_headers(), json=payload)

        if resp.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid Zernio API key")

        if resp.status_code >= 400:
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            raise HTTPException(status_code=resp.status_code, detail=data.get("error", resp.text))

        data = resp.json()
        posts = data.get("posts", [data]) if isinstance(data, dict) else data
        post = posts[0] if posts else {}

        # Extract platform URLs
        platform_urls = {}
        for p in post.get("platforms", []):
            url = p.get("platformPostUrl")
            if url:
                platform_urls[p.get("platform", "unknown")] = url

        publish_status = post.get("status", "published")

        # Persist publish metadata + lifecycle if content record is provided
        if request.content_record_id:
            try:
                _persist_publish_result(
                    content_record_id=request.content_record_id,
                    current_user=current_user,
                    post_id=post.get("_id"),
                    status=publish_status,
                    platform_urls=platform_urls,
                    scheduled_for=post.get("scheduledFor"),
                )
            except InvalidTransitionError:
                raise HTTPException(
                    status_code=409,
                    detail="Content record could not be transitioned to the publish lifecycle state.",
                )

        return PublishResponse(
            success=True,
            post_id=post.get("_id"),
            status=publish_status,
            platform_urls=platform_urls,
        )

    except HTTPException:
        raise
    except httpx.TimeoutException:
        return PublishResponse(success=False, error="Zernio API timeout")
    except Exception as e:
        return PublishResponse(success=False, error=str(e))


@router.get(
    "/connect/{platform}",
    summary="Get OAuth connect URL for a platform",
)
async def get_connect_url(
    platform: str,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Return the OAuth authorization URL to connect a social account.

    The client should open this URL in a browser. After the user authorizes,
    Zernio will handle the callback and the account will appear in /accounts.

    Supported platforms: twitter, linkedin, instagram, tiktok, facebook, pinterest.
    """
    supported = {"twitter", "linkedin", "instagram", "tiktok", "facebook", "pinterest"}
    if platform.lower() not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform '{platform}'. Supported: {sorted(supported)}",
        )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{ZERNIO_BASE}/accounts/connect/{platform.lower()}",
                headers=_headers(),
            )

        if resp.status_code >= 400:
            # Fallback: construct a generic Zernio dashboard URL
            return {
                "platform": platform.lower(),
                "connect_url": f"https://zernio.com/dashboard/accounts/connect?platform={platform.lower()}",
                "method": "dashboard_fallback",
            }

        data = resp.json()
        return {
            "platform": platform.lower(),
            "connect_url": data.get("url") or data.get("connect_url") or data.get("authorization_url"),
            "method": "oauth",
        }

    except Exception:
        # Fallback to dashboard URL if API call fails
        return {
            "platform": platform.lower(),
            "connect_url": f"https://zernio.com/dashboard/accounts/connect?platform={platform.lower()}",
            "method": "dashboard_fallback",
        }


@router.delete(
    "/accounts/{account_id}",
    summary="Disconnect a social account",
)
async def disconnect_account(
    account_id: str,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Disconnect a social account from Zernio."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.delete(
                f"{ZERNIO_BASE}/accounts/{account_id}",
                headers=_headers(),
            )

        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail="Failed to disconnect account")

        return {"disconnected": True, "account_id": account_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/accounts", summary="List connected social accounts")
async def list_accounts(
    current_user: CurrentUser = Depends(require_current_user),
):
    """Fetch all connected social accounts from Zernio."""
    del current_user
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{ZERNIO_BASE}/accounts", headers=_headers())

        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch accounts")

        data = resp.json()
        accounts = data.get("accounts", data) if isinstance(data, dict) else data

        return {
            "accounts": [
                {
                    "id": a.get("_id", a.get("id")),
                    "platform": a.get("platform"),
                    "username": a.get("username"),
                    "display_name": a.get("displayName", a.get("username")),
                    "avatar": a.get("avatar"),
                    "status": a.get("status", "active"),
                }
                for a in accounts
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/status/{post_id}", summary="Check publish status")
async def get_publish_status(
    post_id: str,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Check the publish status of a post."""
    del current_user
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{ZERNIO_BASE}/posts/{post_id}", headers=_headers())

        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Post not found")
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch status")

        post = resp.json()
        platform_urls = {}
        for p in post.get("platforms", []):
            url = p.get("platformPostUrl")
            if url:
                platform_urls[p.get("platform", "unknown")] = url

        return {
            "post_id": post.get("_id"),
            "status": post.get("status"),
            "platform_urls": platform_urls,
            "created_at": post.get("createdAt"),
            "scheduled_for": post.get("scheduledFor"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
