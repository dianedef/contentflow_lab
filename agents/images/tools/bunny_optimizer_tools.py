"""
Bunny Optimizer Tools
Tools for generating on-the-fly image transformation URLs using Bunny CDN's Optimizer API.
Instead of uploading multiple image variants, upload once and generate dynamic URLs with query parameters.
API Reference: https://docs.bunny.net/docs/stream-image-processing
"""
import os
import requests
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
from crewai.tools import tool

from agents.images.config.image_config import BUNNY_CONFIG

logger = logging.getLogger(__name__)


def _get_optimizer_config() -> Dict[str, Any]:
    """Get Bunny Optimizer configuration"""
    return BUNNY_CONFIG.get("optimizer", {})


def _build_optimizer_url(base_url: str, params: Dict[str, Any]) -> str:
    """
    Build a Bunny Optimizer URL with query parameters.

    Args:
        base_url: The base CDN URL of the original image
        params: Dictionary of transformation parameters

    Returns:
        URL with optimizer query parameters
    """
    # Filter out None values
    params = {k: v for k, v in params.items() if v is not None}

    if not params:
        return base_url

    # Parse existing URL
    parsed = urlparse(base_url)

    # Merge with existing query params if any
    existing_params = parse_qs(parsed.query)
    for key, value in params.items():
        existing_params[key] = [str(value)]

    # Build query string (flatten single-value lists)
    query_params = {k: v[0] if len(v) == 1 else v for k, v in existing_params.items()}
    query_string = urlencode(query_params)

    # Reconstruct URL
    new_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        query_string,
        parsed.fragment
    ))

    return new_url


@tool("generate_optimized_url")
def generate_optimized_url(
    base_url: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    quality: Optional[int] = None,
    format: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    crop: Optional[str] = None,
    crop_gravity: Optional[str] = None,
    sharpen: Optional[bool] = None,
    blur: Optional[int] = None,
    brightness: Optional[int] = None,
    saturation: Optional[int] = None,
    contrast: Optional[int] = None,
    sepia: Optional[int] = None,
    flip: Optional[bool] = None,
    flop: Optional[bool] = None,
    auto_optimize: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a Bunny Optimizer URL with transformation parameters.

    Bunny CDN's Optimizer allows on-the-fly image transformations via URL query parameters.
    This eliminates the need to generate and upload multiple image variants.

    Args:
        base_url: CDN URL of the original uploaded image
        width: Target width in pixels (1-3000)
        height: Target height in pixels (1-3000)
        quality: Compression quality (1-100, default 85)
        format: Output format (webp, avif, jpeg, png, gif, auto)
        aspect_ratio: Force aspect ratio (e.g., "16:9", "1:1", "4:3")
        crop: Crop mode (fit, fill, scale, crop, pad)
        crop_gravity: Gravity for cropping (center, north, south, east, west,
                      northeast, northwest, southeast, southwest, smart)
        sharpen: Apply sharpening filter
        blur: Blur amount (1-100)
        brightness: Brightness adjustment (-100 to 100)
        saturation: Saturation adjustment (-100 to 100)
        contrast: Contrast adjustment (-100 to 100)
        sepia: Sepia filter amount (0-100)
        flip: Flip image vertically
        flop: Flip image horizontally
        auto_optimize: Auto optimization level (low, medium, high)

    Returns:
        Dict containing:
        - success: bool
        - url: str (optimized URL with params)
        - base_url: str (original URL)
        - params: dict (applied parameters)

    Example:
        >>> generate_optimized_url(
        ...     "https://cdn.example.com/image.jpg",
        ...     width=800,
        ...     quality=85,
        ...     format="webp"
        ... )
        {
            "success": True,
            "url": "https://cdn.example.com/image.jpg?width=800&quality=85&format=webp",
            ...
        }
    """
    try:
        config = _get_optimizer_config()

        # Use default quality from config if not specified
        if quality is None:
            quality = config.get("default_quality", 85)

        # Build parameters dict using Bunny Optimizer parameter names
        params = {}

        if width is not None:
            params["width"] = min(max(1, width), 3000)
        if height is not None:
            params["height"] = min(max(1, height), 3000)
        if quality is not None:
            params["quality"] = min(max(1, quality), 100)
        if format is not None:
            # Validate format
            valid_formats = ["webp", "avif", "jpeg", "png", "gif", "auto"]
            if format.lower() in valid_formats:
                params["format"] = format.lower()
        if aspect_ratio is not None:
            params["aspect_ratio"] = aspect_ratio
        if crop is not None:
            valid_crops = ["fit", "fill", "scale", "crop", "pad"]
            if crop.lower() in valid_crops:
                params["crop"] = crop.lower()
        if crop_gravity is not None:
            valid_gravities = [
                "center", "north", "south", "east", "west",
                "northeast", "northwest", "southeast", "southwest", "smart"
            ]
            if crop_gravity.lower() in valid_gravities:
                params["crop_gravity"] = crop_gravity.lower()
        if sharpen:
            params["sharpen"] = "true"
        if blur is not None:
            params["blur"] = min(max(1, blur), 100)
        if brightness is not None:
            params["brightness"] = min(max(-100, brightness), 100)
        if saturation is not None:
            params["saturation"] = min(max(-100, saturation), 100)
        if contrast is not None:
            params["contrast"] = min(max(-100, contrast), 100)
        if sepia is not None:
            params["sepia"] = min(max(0, sepia), 100)
        if flip:
            params["flip"] = "true"
        if flop:
            params["flop"] = "true"
        if auto_optimize is not None:
            valid_levels = ["low", "medium", "high"]
            if auto_optimize.lower() in valid_levels:
                params["auto_optimize"] = auto_optimize.lower()

        optimized_url = _build_optimizer_url(base_url, params)

        return {
            "success": True,
            "url": optimized_url,
            "base_url": base_url,
            "params": params
        }

    except Exception as e:
        logger.error(f"Error generating optimized URL: {e}")
        return {
            "success": False,
            "error": str(e),
            "base_url": base_url
        }


@tool("generate_responsive_srcset")
def generate_responsive_srcset(
    base_url: str,
    widths: Optional[List[int]] = None,
    quality: Optional[int] = None,
    format: Optional[str] = None,
    image_type: str = "hero"
) -> Dict[str, Any]:
    """
    Generate srcset and sizes attributes with multiple optimized URLs.

    Creates a complete set of responsive image URLs for different viewport sizes,
    using Bunny Optimizer's on-the-fly transformation.

    Args:
        base_url: CDN URL of the original uploaded image
        widths: List of target widths (defaults to config responsive_widths)
        quality: Compression quality for all variants (1-100)
        format: Output format (webp, avif, jpeg, auto)
        image_type: Type of image for sizes attribute (hero, section, thumbnail)

    Returns:
        Dict containing:
        - success: bool
        - srcset: str (HTML srcset attribute value)
        - sizes: str (HTML sizes attribute value)
        - urls: dict (mapping of width to full URL)
        - primary_url: str (largest/default URL)

    Example:
        >>> generate_responsive_srcset(
        ...     "https://cdn.example.com/hero.jpg",
        ...     widths=[480, 800, 1200],
        ...     quality=85,
        ...     format="webp"
        ... )
        {
            "success": True,
            "srcset": "...?width=480&quality=85&format=webp 480w, ...",
            "sizes": "(max-width: 480px) 100vw, ...",
            ...
        }
    """
    try:
        config = _get_optimizer_config()

        # Use config widths if not specified
        if widths is None:
            widths = config.get("responsive_widths", [480, 800, 1200, 2400])

        # Sort widths ascending
        widths = sorted(widths)

        # Use default quality if not specified
        if quality is None:
            quality = config.get("default_quality", 85)

        # Use auto format if not specified and auto_format is enabled
        if format is None and config.get("auto_format", True):
            format = "auto"

        urls = {}
        srcset_parts = []

        for width in widths:
            result = generate_optimized_url(
                base_url=base_url,
                width=width,
                quality=quality,
                format=format
            )

            if result.get("success"):
                url = result["url"]
                urls[width] = url
                srcset_parts.append(f"{url} {width}w")

        # Build srcset string
        srcset = ", ".join(srcset_parts)

        # Build sizes attribute based on image type
        sizes_map = {
            "hero": "(max-width: 480px) 100vw, (max-width: 800px) 100vw, (max-width: 1200px) 100vw, 1200px",
            "section": "(max-width: 400px) 100vw, (max-width: 600px) 100vw, (max-width: 800px) 100vw, 800px",
            "thumbnail": "(max-width: 200px) 100vw, (max-width: 400px) 100vw, 400px",
            "og_card": "1200px"
        }
        sizes = sizes_map.get(image_type, "(max-width: 800px) 100vw, 1200px")

        # Primary URL is the largest width
        primary_url = urls.get(max(widths), base_url)

        return {
            "success": True,
            "srcset": srcset,
            "sizes": sizes,
            "urls": urls,
            "primary_url": primary_url,
            "base_url": base_url,
            "widths": widths,
            "quality": quality,
            "format": format or "auto"
        }

    except Exception as e:
        logger.error(f"Error generating responsive srcset: {e}")
        return {
            "success": False,
            "error": str(e),
            "base_url": base_url
        }


@tool("verify_optimizer_enabled")
def verify_optimizer_enabled(test_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Verify that Bunny Optimizer is enabled on the pull zone.

    Makes a test request with optimizer parameters and checks for
    optimization headers in the response.

    Args:
        test_url: Optional test image URL. If not provided, will attempt
                  to construct one from config.

    Returns:
        Dict containing:
        - enabled: bool (whether optimizer appears to be working)
        - headers: dict (relevant response headers)
        - test_url: str (URL that was tested)
        - message: str (status message)
    """
    try:
        config = _get_optimizer_config()

        # If no test URL, try to construct one from config
        if test_url is None:
            hostname = BUNNY_CONFIG["storage"].get("hostname") or os.getenv("BUNNY_CDN_HOSTNAME")
            if not hostname:
                return {
                    "enabled": False,
                    "error": "No test URL provided and BUNNY_CDN_HOSTNAME not configured",
                    "message": "Cannot verify optimizer without a test URL"
                }

            if not hostname.startswith("http"):
                hostname = f"https://{hostname}"

            # Use a simple test path
            test_url = f"{hostname}/test-optimizer.jpg"

        # Make request with optimizer params to trigger optimization
        optimized_url = _build_optimizer_url(test_url, {
            "width": 100,
            "quality": 80,
            "format": "webp"
        })

        response = requests.head(
            optimized_url,
            timeout=10,
            allow_redirects=True
        )

        # Check for Bunny optimization headers
        relevant_headers = {}
        optimizer_headers = [
            "x-bunny-optimizer",
            "x-bunny-optimizer-class",
            "cdn-cache",
            "x-cache",
            "content-type",
            "content-length"
        ]

        for header in optimizer_headers:
            if header in response.headers:
                relevant_headers[header] = response.headers[header]

        # Determine if optimizer is enabled based on headers and response
        optimizer_enabled = (
            response.status_code == 200 and
            (
                "x-bunny-optimizer" in response.headers or
                "x-bunny-optimizer-class" in response.headers or
                response.headers.get("content-type", "").startswith("image/webp")
            )
        )

        # If we get a 404, the test image doesn't exist but optimizer might still work
        if response.status_code == 404:
            return {
                "enabled": None,  # Unknown - test image doesn't exist
                "status_code": 404,
                "test_url": optimized_url,
                "message": "Test image not found. Upload an image first to verify optimizer.",
                "config_enabled": config.get("enabled", False)
            }

        return {
            "enabled": optimizer_enabled,
            "status_code": response.status_code,
            "headers": relevant_headers,
            "test_url": optimized_url,
            "message": "Optimizer is enabled and working" if optimizer_enabled else "Optimizer may not be enabled",
            "config_enabled": config.get("enabled", False)
        }

    except requests.exceptions.Timeout:
        return {
            "enabled": False,
            "error": "Request timed out",
            "message": "Could not verify optimizer - request timed out"
        }
    except requests.exceptions.RequestException as e:
        return {
            "enabled": False,
            "error": str(e),
            "message": f"Could not verify optimizer: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error verifying optimizer: {e}")
        return {
            "enabled": False,
            "error": str(e),
            "message": f"Unexpected error: {str(e)}"
        }


def generate_picture_element(
    base_url: str,
    alt_text: str,
    widths: Optional[List[int]] = None,
    quality: int = 85,
    css_class: Optional[str] = None,
    lazy: bool = False
) -> str:
    """
    Generate an HTML <picture> element with WebP and fallback sources.

    This helper function creates a complete responsive picture element
    that serves WebP to supporting browsers with JPEG fallback.

    Args:
        base_url: CDN URL of the original image
        alt_text: Alt text for the image
        widths: List of responsive widths
        quality: Image quality
        css_class: Optional CSS class
        lazy: Whether to add lazy loading

    Returns:
        HTML <picture> element string
    """
    if widths is None:
        widths = [480, 800, 1200]

    # Generate WebP srcset
    webp_result = generate_responsive_srcset(
        base_url=base_url,
        widths=widths,
        quality=quality,
        format="webp"
    )

    # Generate JPEG srcset for fallback
    jpeg_result = generate_responsive_srcset(
        base_url=base_url,
        widths=widths,
        quality=quality,
        format="jpeg"
    )

    class_attr = f' class="{css_class}"' if css_class else ''
    loading_attr = ' loading="lazy"' if lazy else ''

    # Primary fallback URL
    primary_url = jpeg_result.get("primary_url", base_url)

    html = f"""<picture>
  <source type="image/webp" srcset="{webp_result.get('srcset', '')}" sizes="{webp_result.get('sizes', '')}">
  <source type="image/jpeg" srcset="{jpeg_result.get('srcset', '')}" sizes="{jpeg_result.get('sizes', '')}">
  <img src="{primary_url}" alt="{alt_text}"{class_attr}{loading_attr}>
</picture>"""

    return html


def get_optimizer_url_for_size(
    base_url: str,
    size_preset: str,
    quality: Optional[int] = None,
    format: str = "auto"
) -> str:
    """
    Get an optimized URL for a common size preset.

    Args:
        base_url: Original image URL
        size_preset: One of "thumb", "small", "medium", "large", "hero", "og"
        quality: Quality override
        format: Output format

    Returns:
        Optimized URL string
    """
    presets = {
        "thumb": {"width": 200, "height": 200, "crop": "fill", "crop_gravity": "smart"},
        "small": {"width": 480},
        "medium": {"width": 800},
        "large": {"width": 1200},
        "hero": {"width": 1920},
        "og": {"width": 1200, "height": 630, "crop": "fill"}
    }

    preset = presets.get(size_preset, {"width": 800})

    result = generate_optimized_url(
        base_url=base_url,
        width=preset.get("width"),
        height=preset.get("height"),
        crop=preset.get("crop"),
        crop_gravity=preset.get("crop_gravity"),
        quality=quality,
        format=format
    )

    return result.get("url", base_url)
