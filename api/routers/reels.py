"""Reels repurposing API endpoints

Provides:
- Instagram cookie management (upload/check/delete)
- Reel download + audio extraction + Bunny CDN upload
"""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.models.reels import (
    CookieStatusResponse,
    DeleteCookiesRequest,
    DownloadReelRequest,
    DownloadReelResponse,
    UploadCookiesRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/reels",
    tags=["Reels"],
    responses={404: {"description": "Not found"}},
)


@router.post("/cookies", summary="Upload Instagram cookies")
async def upload_cookies(req: UploadCookiesRequest):
    from agents.reels.instagram_service import save_cookies

    try:
        save_cookies(req.user_id, req.cookies_content)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Cookie upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save cookies")


@router.get("/cookies/status", summary="Check Instagram cookie status")
async def cookie_status(user_id: str) -> CookieStatusResponse:
    from agents.reels.instagram_service import get_cookie_status

    result = get_cookie_status(user_id)
    return CookieStatusResponse(**result)


@router.delete("/cookies", summary="Delete Instagram cookies")
async def delete_cookies(req: DeleteCookiesRequest):
    from agents.reels.instagram_service import delete_cookies

    delete_cookies(req.user_id)
    return {"success": True}


@router.post(
    "/download",
    response_model=DownloadReelResponse,
    summary="Download reel, extract audio, upload to Bunny CDN",
)
async def download_reel(req: DownloadReelRequest):
    from agents.reels.instagram_service import download_reel
    from agents.reels.audio_extractor import extract_audio
    from agents.reels.bunny_uploader import upload_to_bunny

    try:
        # 1. Download the reel video
        result = download_reel(req.user_id, req.url)
        video_path = result["video_path"]
        reel_id = result["reel_id"]

        # 2. Extract audio
        audio_result = extract_audio(video_path)
        audio_path = audio_result["audio_path"]
        duration = audio_result["duration"]

        # 3. Upload video to Bunny CDN
        video_cdn_url = upload_to_bunny(
            file_path=video_path,
            cdn_path=f"reels/{reel_id}/video.mp4",
            storage_key=req.bunny_storage_key,
            cdn_hostname=req.bunny_cdn_hostname,
        )

        # 4. Upload audio to Bunny CDN
        audio_cdn_url = upload_to_bunny(
            file_path=audio_path,
            cdn_path=f"reels/{reel_id}/audio.mp3",
            storage_key=req.bunny_storage_key,
            cdn_hostname=req.bunny_cdn_hostname,
        )

        # 5. Cleanup temp files
        try:
            Path(video_path).unlink(missing_ok=True)
            Path(audio_path).unlink(missing_ok=True)
            Path(video_path).parent.rmdir()
        except Exception:
            pass

        return DownloadReelResponse(
            reel_id=reel_id,
            video_url=video_cdn_url,
            audio_url=audio_cdn_url,
            duration=duration,
            caption=result.get("caption"),
            author=result.get("author"),
        )

    except Exception as e:
        logger.error(f"Reel download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
