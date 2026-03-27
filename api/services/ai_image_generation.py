"""AI image generation providers.

Current providers:
- openai (Images API)
"""

from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path
from typing import Dict

from openai import OpenAI


def _resolve_openai_size(image_type: str) -> str:
    """Map internal image type to OpenAI supported sizes."""
    if image_type in {"hero_image", "section_image", "og_card"}:
        return "1536x1024"
    return "1024x1024"


def generate_openai_image_to_file(
    prompt: str,
    image_type: str,
    model: str | None = None,
) -> Dict[str, str]:
    """
    Generate an image using OpenAI Images API and save it locally.

    Returns:
    - local_path: temporary PNG path
    - provider: "openai"
    - model: model used
    - size: generation size
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    resolved_model = model or os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    size = _resolve_openai_size(image_type)

    client = OpenAI(api_key=api_key)
    result = client.images.generate(
        model=resolved_model,
        prompt=prompt,
        size=size,
    )

    if not result.data:
        raise RuntimeError("OpenAI image generation returned no data")

    image_item = result.data[0]
    b64_data = getattr(image_item, "b64_json", None)
    image_url = getattr(image_item, "url", None)

    suffix = ".png"
    fd, tmp_path = tempfile.mkstemp(prefix="img-openai-", suffix=suffix)
    os.close(fd)

    if b64_data:
        decoded = base64.b64decode(b64_data)
        Path(tmp_path).write_bytes(decoded)
    elif image_url:
        import requests

        response = requests.get(image_url, timeout=60)
        response.raise_for_status()
        Path(tmp_path).write_bytes(response.content)
    else:
        raise RuntimeError("OpenAI image response missing b64_json and url")

    return {
        "local_path": tmp_path,
        "provider": "openai",
        "model": resolved_model,
        "size": size,
    }
