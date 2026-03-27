"""Pydantic models for the Reels repurposing pipeline"""

from pydantic import BaseModel, Field
from typing import Optional


class DownloadReelRequest(BaseModel):
    url: str = Field(..., description="Instagram Reel URL")
    user_id: str = Field(..., description="User ID for cookie lookup")
    bunny_storage_key: str = Field(..., description="Bunny Storage API key")
    bunny_cdn_hostname: str = Field(..., description="Bunny CDN hostname")


class DownloadReelResponse(BaseModel):
    reel_id: str
    video_url: str
    audio_url: str
    duration: Optional[float] = None
    thumbnail_url: Optional[str] = None
    caption: Optional[str] = None
    author: Optional[str] = None


class UploadCookiesRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    cookies_content: str = Field(..., description="Netscape cookies.txt content")


class CookieStatusResponse(BaseModel):
    has_cookies: bool
    username: Optional[str] = None


class DeleteCookiesRequest(BaseModel):
    user_id: str
