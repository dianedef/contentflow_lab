"""
Image Optimization Tools
Tools for compressing, converting, and generating responsive image variants
"""
import os
import io
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from crewai.tools import tool

from agents.images.config.image_config import IMAGE_PROCESSING_CONFIG

logger = logging.getLogger(__name__)

# Try to import PIL for image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not installed - image optimization features limited")


def _ensure_pil():
    """Check that PIL is available"""
    if not PIL_AVAILABLE:
        raise ImportError("Pillow is required for image optimization. Install with: pip install Pillow")


@tool("compress_image")
def compress_image(
    input_path: str,
    output_path: Optional[str] = None,
    quality: int = 85,
    max_size_kb: Optional[int] = None
) -> Dict[str, Any]:
    """
    Compress an image to reduce file size while maintaining quality.

    Args:
        input_path: Path to input image
        output_path: Path for output (defaults to input with -compressed suffix)
        quality: Compression quality (1-100)
        max_size_kb: Target maximum file size in KB (will reduce quality if needed)

    Returns:
        Dict containing:
        - success: bool
        - output_path: str
        - original_size_kb: float
        - compressed_size_kb: float
        - compression_ratio: float
        - final_quality: int
    """
    _ensure_pil()

    try:
        if not os.path.exists(input_path):
            return {
                "success": False,
                "error": f"Input file not found: {input_path}"
            }

        # Default output path
        if output_path is None:
            path = Path(input_path)
            output_path = str(path.parent / f"{path.stem}-compressed{path.suffix}")

        original_size = os.path.getsize(input_path)

        with Image.open(input_path) as img:
            # Convert to RGB if necessary (for JPEG)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            current_quality = quality
            min_quality = IMAGE_PROCESSING_CONFIG["compression"].get("min_quality", 60)

            # Iteratively compress if max_size specified
            if max_size_kb:
                while current_quality >= min_quality:
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=current_quality, optimize=True)
                    size_kb = buffer.tell() / 1024

                    if size_kb <= max_size_kb:
                        break
                    current_quality -= 5

                buffer.seek(0)
                with open(output_path, 'wb') as f:
                    f.write(buffer.read())
            else:
                img.save(output_path, quality=current_quality, optimize=True)

        compressed_size = os.path.getsize(output_path)

        return {
            "success": True,
            "output_path": output_path,
            "original_size_kb": round(original_size / 1024, 2),
            "compressed_size_kb": round(compressed_size / 1024, 2),
            "compression_ratio": round(compressed_size / original_size, 3),
            "savings_percent": round((1 - compressed_size / original_size) * 100, 1),
            "final_quality": current_quality
        }

    except Exception as e:
        logger.error(f"Compression error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool("convert_to_webp")
def convert_to_webp(
    input_path: str,
    output_path: Optional[str] = None,
    quality: int = 82
) -> Dict[str, Any]:
    """
    Convert an image to WebP format for better web performance.

    Args:
        input_path: Path to input image
        output_path: Path for WebP output (defaults to input with .webp extension)
        quality: WebP compression quality (1-100)

    Returns:
        Dict containing:
        - success: bool
        - output_path: str
        - original_size_kb: float
        - webp_size_kb: float
        - savings_percent: float
    """
    _ensure_pil()

    try:
        if not os.path.exists(input_path):
            return {
                "success": False,
                "error": f"Input file not found: {input_path}"
            }

        # Default output path
        if output_path is None:
            path = Path(input_path)
            output_path = str(path.parent / f"{path.stem}.webp")

        original_size = os.path.getsize(input_path)

        with Image.open(input_path) as img:
            # Handle transparency
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')

            img.save(output_path, 'WEBP', quality=quality, method=6)

        webp_size = os.path.getsize(output_path)

        return {
            "success": True,
            "output_path": output_path,
            "original_size_kb": round(original_size / 1024, 2),
            "webp_size_kb": round(webp_size / 1024, 2),
            "savings_percent": round((1 - webp_size / original_size) * 100, 1),
            "format": "webp"
        }

    except Exception as e:
        logger.error(f"WebP conversion error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool("generate_responsive_variants")
def generate_responsive_variants(
    input_path: str,
    output_dir: Optional[str] = None,
    image_type: str = "hero",
    output_format: str = "webp"
) -> Dict[str, Any]:
    """
    Generate responsive image variants at different sizes.

    Args:
        input_path: Path to input image
        output_dir: Directory for outputs (defaults to input directory)
        image_type: Type of image (hero, section, thumbnail) for size presets
        output_format: Output format (webp, jpg)

    Returns:
        Dict containing:
        - success: bool
        - variants: list of generated variants with paths and sizes
        - srcset: str (HTML srcset attribute)
        - sizes: str (suggested HTML sizes attribute)
    """
    _ensure_pil()

    try:
        if not os.path.exists(input_path):
            return {
                "success": False,
                "error": f"Input file not found: {input_path}"
            }

        # Get size presets for image type
        size_presets = IMAGE_PROCESSING_CONFIG["responsive_sizes"].get(
            image_type,
            IMAGE_PROCESSING_CONFIG["responsive_sizes"]["hero"]
        )

        # Default output directory
        if output_dir is None:
            output_dir = str(Path(input_path).parent)

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        base_name = Path(input_path).stem
        extension = ".webp" if output_format == "webp" else ".jpg"

        quality = IMAGE_PROCESSING_CONFIG["compression"].get(
            f"{output_format}_quality",
            82
        )

        variants = []
        srcset_parts = []

        with Image.open(input_path) as img:
            original_width, original_height = img.size
            aspect_ratio = original_height / original_width

            for preset in size_presets:
                target_width = preset["width"]
                suffix = preset["suffix"]

                # Skip if target is larger than original
                if target_width > original_width:
                    continue

                target_height = int(target_width * aspect_ratio)

                # Resize
                resized = img.copy()
                resized.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)

                # Output filename
                output_filename = f"{base_name}{suffix}{extension}"
                output_path = os.path.join(output_dir, output_filename)

                # Save
                if output_format == "webp":
                    if resized.mode in ('RGBA', 'LA', 'P'):
                        resized = resized.convert('RGBA')
                    else:
                        resized = resized.convert('RGB')
                    resized.save(output_path, 'WEBP', quality=quality, method=6)
                else:
                    if resized.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', resized.size, (255, 255, 255))
                        if resized.mode == 'P':
                            resized = resized.convert('RGBA')
                        background.paste(resized, mask=resized.split()[-1] if resized.mode == 'RGBA' else None)
                        resized = background
                    resized.save(output_path, 'JPEG', quality=quality, optimize=True)

                file_size = os.path.getsize(output_path)

                variants.append({
                    "path": output_path,
                    "filename": output_filename,
                    "width": target_width,
                    "height": target_height,
                    "size_kb": round(file_size / 1024, 2),
                    "suffix": suffix
                })

                srcset_parts.append(f"{output_filename} {target_width}w")

        # Generate srcset attribute
        srcset = ", ".join(srcset_parts)

        # Suggest sizes attribute based on image type
        sizes_map = {
            "hero": "(max-width: 480px) 100vw, (max-width: 800px) 100vw, 1200px",
            "section": "(max-width: 400px) 100vw, (max-width: 600px) 100vw, 800px",
            "thumbnail": "(max-width: 200px) 100vw, 400px"
        }
        sizes = sizes_map.get(image_type, "100vw")

        return {
            "success": True,
            "variants": variants,
            "count": len(variants),
            "srcset": srcset,
            "sizes": sizes,
            "format": output_format
        }

    except Exception as e:
        logger.error(f"Responsive variants error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool("calculate_image_hash")
def calculate_image_hash(file_path: str) -> Dict[str, Any]:
    """
    Calculate MD5 hash of an image file for deduplication and cache busting.

    Args:
        file_path: Path to image file

    Returns:
        Dict containing:
        - hash: str (MD5 hash)
        - short_hash: str (first 8 characters)
        - file_size_kb: float
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }

        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        file_size = os.path.getsize(file_path)

        return {
            "success": True,
            "hash": file_hash,
            "short_hash": file_hash[:8],
            "file_size_kb": round(file_size / 1024, 2)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_image_info(file_path: str) -> Dict[str, Any]:
    """
    Get detailed information about an image file.

    Args:
        file_path: Path to image

    Returns:
        Dict with image metadata
    """
    _ensure_pil()

    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }

        with Image.open(file_path) as img:
            width, height = img.size
            format_name = img.format
            mode = img.mode

        file_size = os.path.getsize(file_path)

        return {
            "success": True,
            "path": file_path,
            "width": width,
            "height": height,
            "aspect_ratio": round(width / height, 2),
            "format": format_name,
            "mode": mode,
            "file_size_kb": round(file_size / 1024, 2)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def resize_image(
    input_path: str,
    output_path: str,
    width: int,
    height: Optional[int] = None,
    maintain_aspect: bool = True
) -> Dict[str, Any]:
    """
    Resize an image to specific dimensions.

    Args:
        input_path: Source image path
        output_path: Destination path
        width: Target width
        height: Target height (optional if maintain_aspect=True)
        maintain_aspect: Whether to maintain aspect ratio

    Returns:
        Dict with resize result
    """
    _ensure_pil()

    try:
        with Image.open(input_path) as img:
            original_width, original_height = img.size

            if maintain_aspect:
                aspect_ratio = original_height / original_width
                if height is None:
                    height = int(width * aspect_ratio)
                img.thumbnail((width, height), Image.Resampling.LANCZOS)
            else:
                img = img.resize((width, height), Image.Resampling.LANCZOS)

            # Determine format from output path
            ext = Path(output_path).suffix.lower()
            if ext == '.webp':
                img.save(output_path, 'WEBP', quality=82)
            elif ext in ['.jpg', '.jpeg']:
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(output_path, 'JPEG', quality=85, optimize=True)
            else:
                img.save(output_path)

        return {
            "success": True,
            "output_path": output_path,
            "width": width,
            "height": height,
            "file_size_kb": round(os.path.getsize(output_path) / 1024, 2)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
