"""
Robolly API Tools
Tools for generating images via Robolly's template-based image generation API
API Reference: https://robolly.com/docs/api-reference/
"""
import os
import time
import requests
import logging
from typing import Dict, Any, Optional, List
from crewai.tools import tool
from datetime import datetime

from agents.images.config.image_config import ROBOLLY_CONFIG

logger = logging.getLogger(__name__)


def _get_api_key() -> str:
    """Get Robolly API key from config or environment"""
    api_key = ROBOLLY_CONFIG.get("api_key") or os.getenv("ROBOLLY_API_KEY")
    if not api_key:
        raise ValueError("ROBOLLY_API_KEY not configured")
    return api_key


def _get_headers() -> Dict[str, str]:
    """Get API headers with authentication"""
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json"
    }


@tool("generate_robolly_image")
def generate_robolly_image(
    template_id: str,
    title: str,
    subtitle: Optional[str] = None,
    style_guide: str = "brand_primary",
    custom_modifications: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate an image using Robolly API with a specified template.

    Args:
        template_id: The Robolly template ID to use
        title: Main title text to overlay on the image
        subtitle: Optional subtitle text
        style_guide: Style guide name for colors/branding (brand_primary, brand_dark, minimal)
        custom_modifications: Additional template modifications

    Returns:
        Dict containing:
        - success: bool
        - render_id: str (if successful)
        - image_url: str (if successful)
        - dimensions: dict with width/height
        - generation_time_ms: int
        - error: str (if failed)
    """
    start_time = datetime.utcnow()

    try:
        base_url = ROBOLLY_CONFIG.get("base_url", "https://api.robolly.com")
        style = ROBOLLY_CONFIG["style_guides"].get(style_guide,
            ROBOLLY_CONFIG["style_guides"]["brand_primary"])

        # Build modifications payload
        modifications = {}

        # Title modification
        if title:
            modifications["title"] = {
                "text": title,
                "color": style["colors"]["primary"]
            }

        # Subtitle modification
        if subtitle:
            modifications["subtitle"] = {
                "text": subtitle,
                "color": style["colors"]["secondary"]
            }

        # Logo modification
        if style.get("logo_url"):
            modifications["logo"] = {
                "src": style["logo_url"]
            }

        # Background color
        if style["colors"].get("background"):
            modifications["background"] = {
                "color": style["colors"]["background"]
            }

        # Merge custom modifications
        if custom_modifications:
            modifications.update(custom_modifications)

        # API request payload
        payload = {
            "template": template_id,
            "modifications": modifications
        }

        logger.info(f"Generating image with template {template_id}")

        # Create render request
        response = requests.post(
            f"{base_url}/v1/render",
            headers=_get_headers(),
            json=payload,
            timeout=ROBOLLY_CONFIG.get("api_timeout_seconds", 30)
        )

        if response.status_code == 401:
            return {
                "success": False,
                "error": "Invalid Robolly API key"
            }

        if response.status_code == 404:
            return {
                "success": False,
                "error": f"Template not found: {template_id}"
            }

        response.raise_for_status()
        render_data = response.json()

        render_id = render_data.get("id") or render_data.get("renderId")

        if not render_id:
            return {
                "success": False,
                "error": "No render ID returned from Robolly"
            }

        # Poll for completion
        poll_interval = ROBOLLY_CONFIG.get("poll_interval_seconds", 1)
        max_attempts = ROBOLLY_CONFIG.get("poll_max_attempts", 30)

        for attempt in range(max_attempts):
            status_response = requests.get(
                f"{base_url}/v1/render/{render_id}",
                headers=_get_headers(),
                timeout=10
            )
            status_response.raise_for_status()
            status_data = status_response.json()

            status = status_data.get("status", "").lower()

            if status == "ready" or status == "completed":
                end_time = datetime.utcnow()
                generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

                return {
                    "success": True,
                    "render_id": render_id,
                    "image_url": status_data.get("url") or status_data.get("output"),
                    "dimensions": {
                        "width": status_data.get("width", 1200),
                        "height": status_data.get("height", 630)
                    },
                    "format": status_data.get("format", "jpg"),
                    "generation_time_ms": generation_time_ms
                }

            elif status == "failed" or status == "error":
                return {
                    "success": False,
                    "render_id": render_id,
                    "error": status_data.get("error", "Render failed")
                }

            time.sleep(poll_interval)

        # Timeout
        return {
            "success": False,
            "render_id": render_id,
            "error": f"Render timeout after {max_attempts * poll_interval}s"
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Robolly API request timed out"
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Robolly API error: {e}")
        return {
            "success": False,
            "error": f"API request failed: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error generating image: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


@tool("validate_robolly_image")
def validate_robolly_image(image_url: str) -> Dict[str, Any]:
    """
    Validate that a generated Robolly image is accessible and valid.

    Args:
        image_url: URL of the image to validate

    Returns:
        Dict containing:
        - valid: bool
        - size_bytes: int (if valid)
        - content_type: str (if valid)
        - error: str (if invalid)
    """
    try:
        response = requests.head(image_url, timeout=10, allow_redirects=True)

        if response.status_code != 200:
            return {
                "valid": False,
                "error": f"HTTP {response.status_code}"
            }

        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            return {
                "valid": False,
                "error": f"Invalid content type: {content_type}"
            }

        content_length = int(response.headers.get("Content-Length", 0))
        if content_length == 0:
            # Try GET to verify
            get_response = requests.get(image_url, timeout=10, stream=True)
            content_length = len(get_response.content)
            get_response.close()

        if content_length == 0:
            return {
                "valid": False,
                "error": "Empty image file"
            }

        return {
            "valid": True,
            "size_bytes": content_length,
            "size_kb": round(content_length / 1024, 2),
            "content_type": content_type
        }

    except requests.exceptions.Timeout:
        return {
            "valid": False,
            "error": "Request timed out"
        }
    except requests.exceptions.RequestException as e:
        return {
            "valid": False,
            "error": f"Request failed: {str(e)}"
        }


@tool("get_robolly_templates")
def get_robolly_templates() -> Dict[str, Any]:
    """
    Get list of available Robolly templates from configuration.

    Returns:
        Dict containing configured templates with their settings
    """
    templates = ROBOLLY_CONFIG.get("templates", {})

    result = {
        "templates": [],
        "count": 0
    }

    for template_type, config in templates.items():
        template_info = {
            "type": template_type,
            "template_id": config.get("template_id", ""),
            "dimensions": config.get("dimensions", {}),
            "format": config.get("format", "jpg"),
            "quality": config.get("quality", 85),
            "description": config.get("description", ""),
            "configured": bool(config.get("template_id"))
        }
        result["templates"].append(template_info)

    result["count"] = len(result["templates"])
    result["configured_count"] = sum(1 for t in result["templates"] if t["configured"])

    return result


def download_image(image_url: str, local_path: str) -> Dict[str, Any]:
    """
    Download an image from URL to local path.

    Args:
        image_url: URL to download from
        local_path: Local file path to save to

    Returns:
        Dict with success status and file info
    """
    try:
        response = requests.get(image_url, timeout=30, stream=True)
        response.raise_for_status()

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = os.path.getsize(local_path)

        return {
            "success": True,
            "local_path": local_path,
            "size_bytes": file_size,
            "size_kb": round(file_size / 1024, 2)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def generate_image_for_type(
    image_type: str,
    title: str,
    subtitle: Optional[str] = None,
    style_guide: str = "brand_primary"
) -> Dict[str, Any]:
    """
    Generate an image using the configured template for a specific image type.

    Args:
        image_type: Type of image (hero_image, section_image, og_card, thumbnail)
        title: Title text
        subtitle: Optional subtitle
        style_guide: Style guide to use

    Returns:
        Generation result dict
    """
    template_config = ROBOLLY_CONFIG["templates"].get(image_type)

    if not template_config:
        return {
            "success": False,
            "error": f"Unknown image type: {image_type}"
        }

    template_id = template_config.get("template_id")
    if not template_id:
        return {
            "success": False,
            "error": f"No template configured for {image_type}"
        }

    return generate_robolly_image(
        template_id=template_id,
        title=title,
        subtitle=subtitle,
        style_guide=style_guide
    )
