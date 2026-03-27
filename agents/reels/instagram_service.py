"""Instagram service using instagrapi for Reel downloading"""

import json
import hashlib
import logging
import re
import tempfile
from pathlib import Path
from typing import Optional

from instagrapi import Client
from instagrapi.exceptions import LoginRequired

logger = logging.getLogger(__name__)

COOKIES_DIR = Path("data/reels/cookies")


def _user_cookie_path(user_id: str) -> Path:
    """Get the cookie file path for a given user ID."""
    hashed = hashlib.sha256(user_id.encode()).hexdigest()[:16]
    return COOKIES_DIR / f"{hashed}.json"


def save_cookies(user_id: str, cookies_content: str) -> None:
    """Parse Netscape cookies.txt and save as instagrapi JSON session."""
    COOKIES_DIR.mkdir(parents=True, exist_ok=True)

    # Parse Netscape cookies.txt format into a dict
    cookie_dict = {}
    for line in cookies_content.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            cookie_dict[parts[5]] = parts[6]

    if not cookie_dict:
        raise ValueError("No valid cookies found in the provided content")

    # Create an instagrapi client to validate and save session
    cl = Client()
    cl.set_cookies(cookie_dict)

    # Save session as JSON
    path = _user_cookie_path(user_id)
    cl.dump_settings(path)
    logger.info(f"Saved cookies for user {user_id[:8]}...")


def get_cookie_status(user_id: str) -> dict:
    """Check if valid cookies exist for a user."""
    path = _user_cookie_path(user_id)
    if not path.exists():
        return {"has_cookies": False, "username": None}

    try:
        cl = Client()
        cl.load_settings(path)
        cl.login_by_sessionid(cl.sessionid)
        username = cl.account_info().username
        return {"has_cookies": True, "username": username}
    except Exception as e:
        logger.warning(f"Cookie validation failed: {e}")
        return {"has_cookies": False, "username": None}


def delete_cookies(user_id: str) -> None:
    """Remove stored cookies for a user."""
    path = _user_cookie_path(user_id)
    if path.exists():
        path.unlink()


def extract_media_pk(url: str) -> str:
    """Extract the media PK from an Instagram URL."""
    # Handle various IG URL formats
    patterns = [
        r"instagram\.com/reel/([A-Za-z0-9_-]+)",
        r"instagram\.com/reels/([A-Za-z0-9_-]+)",
        r"instagram\.com/p/([A-Za-z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract media code from URL: {url}")


def download_reel(user_id: str, url: str) -> dict:
    """
    Download an Instagram Reel video.

    Returns dict with:
        - video_path: path to downloaded video file
        - reel_id: the shortcode/media code
        - caption: reel caption
        - author: username of the author
    """
    path = _user_cookie_path(user_id)
    if not path.exists():
        raise LoginRequired("No cookies found. Please upload Instagram cookies first.")

    cl = Client()
    cl.load_settings(path)

    try:
        cl.login_by_sessionid(cl.sessionid)
    except Exception:
        raise LoginRequired("Session expired. Please upload fresh Instagram cookies.")

    shortcode = extract_media_pk(url)
    media_pk = cl.media_pk_from_code(shortcode)
    media_info = cl.media_info(media_pk)

    # Download video to temp directory
    tmp_dir = Path(tempfile.mkdtemp(prefix="reels_"))
    video_path = cl.clip_download(media_pk, folder=tmp_dir)

    return {
        "video_path": str(video_path),
        "reel_id": shortcode,
        "caption": media_info.caption_text if media_info.caption_text else None,
        "author": media_info.user.username if media_info.user else None,
    }
