"""
Bunny.net CDN Tools
Tools for uploading images to Bunny.net Storage and managing CDN delivery
API Reference: https://docs.bunny.net/reference/storage-api
"""
import os
import time
import requests
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from crewai.tools import tool

from agents.images.config.image_config import BUNNY_CONFIG

logger = logging.getLogger(__name__)


def _get_storage_api_key() -> str:
    """Get Bunny Storage API key"""
    api_key = BUNNY_CONFIG["storage"].get("api_key") or os.getenv("BUNNY_STORAGE_API_KEY")
    if not api_key:
        raise ValueError("BUNNY_STORAGE_API_KEY not configured")
    return api_key


def _get_cdn_api_key() -> str:
    """Get Bunny CDN API key"""
    api_key = BUNNY_CONFIG["cdn"].get("api_key") or os.getenv("BUNNY_CDN_API_KEY")
    if not api_key:
        raise ValueError("BUNNY_CDN_API_KEY not configured")
    return api_key


def _get_storage_url(path: str) -> str:
    """Build Bunny Storage URL"""
    base_url = BUNNY_CONFIG["storage"].get("base_url", "https://storage.bunnycdn.com")
    storage_zone = BUNNY_CONFIG["storage"].get("storage_zone", "")
    region = BUNNY_CONFIG["storage"].get("region", "")

    # Regional endpoints
    if region and region != "de":
        region_map = {
            "ny": "ny",
            "la": "la",
            "sg": "sg",
            "syd": "syd"
        }
        region_prefix = region_map.get(region, "")
        if region_prefix:
            base_url = f"https://{region_prefix}.storage.bunnycdn.com"

    return f"{base_url}/{storage_zone}{path}"


def _get_cdn_url(storage_path: str) -> str:
    """Get CDN URL for a storage path"""
    hostname = BUNNY_CONFIG["storage"].get("hostname") or os.getenv("BUNNY_CDN_HOSTNAME")
    if not hostname:
        raise ValueError("BUNNY_CDN_HOSTNAME not configured")

    # Ensure hostname has protocol
    if not hostname.startswith("http"):
        hostname = f"https://{hostname}"

    return f"{hostname}{storage_path}"


@tool("upload_to_bunny_storage")
def upload_to_bunny_storage(
    source: str,
    file_name: str,
    path_type: str = "articles"
) -> Dict[str, Any]:
    """
    Upload an image to Bunny.net Storage and return CDN URL.

    Args:
        source: Either a local file path or a URL to download from
        file_name: Filename to use in storage (should be SEO-friendly)
        path_type: Content type for path (articles, newsletter, social, thumbnails)

    Returns:
        Dict containing:
        - success: bool
        - cdn_url: str (final CDN URL)
        - storage_path: str (path in storage)
        - file_size_bytes: int
        - uploaded_at: str (ISO timestamp)
        - error: str (if failed)
    """
    try:
        # Determine storage path
        cdn_path = BUNNY_CONFIG["paths"].get(path_type, "/images/")
        storage_path = f"{cdn_path}{file_name}"

        # Get image data
        if source.startswith(("http://", "https://")):
            # Download from URL
            logger.info(f"Downloading image from {source}")
            response = requests.get(source, timeout=30)
            response.raise_for_status()
            image_data = response.content
            content_type = response.headers.get("Content-Type", "image/jpeg")
        else:
            # Read local file
            if not os.path.exists(source):
                return {
                    "success": False,
                    "error": f"Local file not found: {source}"
                }
            with open(source, "rb") as f:
                image_data = f.read()

            # Determine content type from extension
            ext = Path(source).suffix.lower()
            content_type_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".avif": "image/avif",
                ".gif": "image/gif"
            }
            content_type = content_type_map.get(ext, "image/jpeg")

        file_size = len(image_data)
        logger.info(f"Uploading {file_size} bytes to {storage_path}")

        # Upload to Bunny Storage
        upload_url = _get_storage_url(storage_path)

        upload_response = requests.put(
            upload_url,
            headers={
                "AccessKey": _get_storage_api_key(),
                "Content-Type": content_type
            },
            data=image_data,
            timeout=60
        )

        if upload_response.status_code == 401:
            return {
                "success": False,
                "error": "Invalid Bunny Storage API key"
            }

        upload_response.raise_for_status()

        # Generate CDN URL
        cdn_url = _get_cdn_url(storage_path)

        return {
            "success": True,
            "cdn_url": cdn_url,
            "storage_path": storage_path,
            "file_size_bytes": file_size,
            "file_size_kb": round(file_size / 1024, 2),
            "content_type": content_type,
            "uploaded_at": datetime.utcnow().isoformat()
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Upload request timed out"
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Bunny upload error: {e}")
        return {
            "success": False,
            "error": f"Upload failed: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error uploading to Bunny: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


@tool("verify_cdn_propagation")
def verify_cdn_propagation(
    cdn_url: str,
    max_attempts: int = 5,
    delay_seconds: int = 2
) -> Dict[str, Any]:
    """
    Verify that an image is accessible via CDN after upload.

    Args:
        cdn_url: The CDN URL to verify
        max_attempts: Maximum number of verification attempts
        delay_seconds: Delay between attempts

    Returns:
        Dict containing:
        - propagated: bool
        - cdn_url: str
        - attempts: int (attempts needed)
        - cache_status: str (CDN cache header)
        - response_time_ms: int
        - error: str (if not propagated)
    """
    for attempt in range(max_attempts):
        try:
            start_time = datetime.utcnow()
            response = requests.head(
                cdn_url,
                timeout=10,
                allow_redirects=True
            )
            end_time = datetime.utcnow()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)

            if response.status_code == 200:
                cache_status = response.headers.get("X-Cache", "unknown")
                cdn_cache = response.headers.get("CDN-Cache", "unknown")

                return {
                    "propagated": True,
                    "cdn_url": cdn_url,
                    "attempts": attempt + 1,
                    "cache_status": cache_status,
                    "cdn_cache": cdn_cache,
                    "response_time_ms": response_time_ms,
                    "content_type": response.headers.get("Content-Type", ""),
                    "content_length": response.headers.get("Content-Length", "0")
                }

            elif response.status_code == 404 and attempt < max_attempts - 1:
                # Not yet propagated, wait and retry
                time.sleep(delay_seconds)
                continue

            else:
                return {
                    "propagated": False,
                    "cdn_url": cdn_url,
                    "attempts": attempt + 1,
                    "error": f"HTTP {response.status_code}"
                }

        except requests.exceptions.Timeout:
            if attempt < max_attempts - 1:
                time.sleep(delay_seconds)
                continue
            return {
                "propagated": False,
                "cdn_url": cdn_url,
                "attempts": attempt + 1,
                "error": "Request timeout"
            }
        except requests.exceptions.RequestException as e:
            if attempt < max_attempts - 1:
                time.sleep(delay_seconds)
                continue
            return {
                "propagated": False,
                "cdn_url": cdn_url,
                "attempts": attempt + 1,
                "error": str(e)
            }

    return {
        "propagated": False,
        "cdn_url": cdn_url,
        "attempts": max_attempts,
        "error": f"CDN propagation timeout after {max_attempts} attempts"
    }


@tool("purge_cdn_cache")
def purge_cdn_cache(cdn_url: str) -> Dict[str, Any]:
    """
    Purge CDN cache for a specific URL.

    Args:
        cdn_url: The CDN URL to purge

    Returns:
        Dict containing:
        - success: bool
        - purged_url: str
        - error: str (if failed)
    """
    try:
        pull_zone_id = BUNNY_CONFIG["cdn"].get("pull_zone_id") or os.getenv("BUNNY_PULL_ZONE_ID")
        if not pull_zone_id:
            return {
                "success": False,
                "error": "BUNNY_PULL_ZONE_ID not configured"
            }

        base_url = BUNNY_CONFIG["cdn"].get("base_url", "https://api.bunny.net")

        response = requests.post(
            f"{base_url}/pullzone/{pull_zone_id}/purgeCache",
            headers={
                "AccessKey": _get_cdn_api_key(),
                "Content-Type": "application/json"
            },
            json={"url": cdn_url},
            timeout=30
        )

        # 204 No Content is success for purge
        if response.status_code in [200, 204]:
            return {
                "success": True,
                "purged_url": cdn_url
            }
        else:
            return {
                "success": False,
                "purged_url": cdn_url,
                "error": f"HTTP {response.status_code}: {response.text}"
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "purged_url": cdn_url,
            "error": str(e)
        }


@tool("get_cdn_url")
def get_cdn_url(storage_path: str) -> Dict[str, Any]:
    """
    Get the CDN URL for a given storage path.

    Args:
        storage_path: Path in Bunny Storage (e.g., /articles/images/hero.jpg)

    Returns:
        Dict containing:
        - cdn_url: str
        - hostname: str
    """
    try:
        cdn_url = _get_cdn_url(storage_path)
        hostname = BUNNY_CONFIG["storage"].get("hostname", "")

        return {
            "cdn_url": cdn_url,
            "storage_path": storage_path,
            "hostname": hostname
        }
    except ValueError as e:
        return {
            "error": str(e)
        }


def delete_from_storage(storage_path: str) -> Dict[str, Any]:
    """
    Delete a file from Bunny Storage.

    Args:
        storage_path: Path to delete

    Returns:
        Dict with success status
    """
    try:
        delete_url = _get_storage_url(storage_path)

        response = requests.delete(
            delete_url,
            headers={"AccessKey": _get_storage_api_key()},
            timeout=30
        )

        if response.status_code in [200, 204]:
            return {
                "success": True,
                "deleted_path": storage_path
            }
        elif response.status_code == 404:
            return {
                "success": True,
                "deleted_path": storage_path,
                "note": "File did not exist"
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def list_storage_files(path: str = "/") -> Dict[str, Any]:
    """
    List files in a Bunny Storage path.

    Args:
        path: Storage path to list

    Returns:
        Dict with files list
    """
    try:
        list_url = _get_storage_url(path)

        response = requests.get(
            list_url,
            headers={"AccessKey": _get_storage_api_key()},
            timeout=30
        )
        response.raise_for_status()

        files = response.json()

        return {
            "success": True,
            "path": path,
            "files": files,
            "count": len(files)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
