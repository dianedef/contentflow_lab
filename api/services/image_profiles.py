"""Image profile registry for on-demand generation.

Provides:
- Built-in system profiles (OG, blog hero, YouTube thumbnail, etc.)
- Persistent custom profiles stored in data/images/image_profiles.json
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional


BUILTIN_IMAGE_PROFILES: Dict[str, Dict[str, Any]] = {
    "og-default": {
        "profile_id": "og-default",
        "name": "Open Graph Standard",
        "description": "Social card 1200x630 for Open Graph sharing.",
        "image_type": "og_card",
        "image_provider": "robolly",
        "style_guide": "brand_primary",
        "path_type": "social",
        "template_id": None,
        "default_alt_text": "Open Graph image",
        "base_prompt": None,
        "tags": ["og", "social", "meta"],
        "is_system": True,
    },
    "blog-hero": {
        "profile_id": "blog-hero",
        "name": "Blog Hero",
        "description": "Main featured image for article headers.",
        "image_type": "hero_image",
        "image_provider": "robolly",
        "style_guide": "brand_primary",
        "path_type": "articles",
        "template_id": None,
        "default_alt_text": "Featured image",
        "base_prompt": None,
        "tags": ["blog", "hero", "article"],
        "is_system": True,
    },
    "blog-section": {
        "profile_id": "blog-section",
        "name": "Blog Section",
        "description": "Mid-article section visual.",
        "image_type": "section_image",
        "image_provider": "robolly",
        "style_guide": "brand_primary",
        "path_type": "articles",
        "template_id": None,
        "default_alt_text": "Section illustration",
        "base_prompt": None,
        "tags": ["blog", "section", "article"],
        "is_system": True,
    },
    "youtube-thumbnail": {
        "profile_id": "youtube-thumbnail",
        "name": "YouTube Thumbnail",
        "description": "Clickable thumbnail visual for YouTube.",
        "image_type": "thumbnail",
        "image_provider": "robolly",
        "style_guide": "brand_primary",
        "path_type": "thumbnails",
        "template_id": None,
        "default_alt_text": "YouTube thumbnail",
        "base_prompt": None,
        "tags": ["youtube", "thumbnail", "video"],
        "is_system": True,
    },
    "youtube-og": {
        "profile_id": "youtube-og",
        "name": "YouTube Social Card",
        "description": "Social card for video pages and sharing.",
        "image_type": "og_card",
        "image_provider": "robolly",
        "style_guide": "brand_primary",
        "path_type": "social",
        "template_id": None,
        "default_alt_text": "Video social card",
        "base_prompt": None,
        "tags": ["youtube", "social", "og"],
        "is_system": True,
    },
}


class ImageProfileStore:
    """Storage layer for system and custom image profiles."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "image_profiles.json"

    def list_profiles(self) -> List[Dict[str, Any]]:
        builtins = [deepcopy(profile) for profile in BUILTIN_IMAGE_PROFILES.values()]
        custom_profiles = list(self._load_custom_profiles().values())
        custom_profiles.sort(key=lambda p: p.get("name", "").lower())
        return builtins + custom_profiles

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        builtin = BUILTIN_IMAGE_PROFILES.get(profile_id)
        if builtin:
            return deepcopy(builtin)
        return self._load_custom_profiles().get(profile_id)

    def save_custom_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        profile_id = profile["profile_id"]
        if profile_id in BUILTIN_IMAGE_PROFILES:
            raise ValueError("Cannot overwrite a system profile")

        custom_profiles = self._load_custom_profiles()
        stored = {
            **profile,
            "is_system": False,
        }
        custom_profiles[profile_id] = stored
        self._write_custom_profiles(custom_profiles)
        return stored

    def delete_custom_profile(self, profile_id: str) -> bool:
        if profile_id in BUILTIN_IMAGE_PROFILES:
            raise ValueError("Cannot delete a system profile")

        custom_profiles = self._load_custom_profiles()
        if profile_id not in custom_profiles:
            return False

        del custom_profiles[profile_id]
        self._write_custom_profiles(custom_profiles)
        return True

    def _load_custom_profiles(self) -> Dict[str, Dict[str, Any]]:
        if not self.file_path.exists():
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return {}

        if isinstance(data, list):
            normalized = {}
            for item in data:
                if isinstance(item, dict) and "profile_id" in item:
                    normalized[item["profile_id"]] = {
                        **item,
                        "is_system": False,
                    }
            return normalized

        if isinstance(data, dict):
            normalized = {}
            for profile_id, item in data.items():
                if not isinstance(item, dict):
                    continue
                normalized[profile_id] = {
                    **item,
                    "profile_id": item.get("profile_id", profile_id),
                    "is_system": False,
                }
            return normalized

        return {}

    def _write_custom_profiles(self, profiles: Dict[str, Dict[str, Any]]) -> None:
        with open(self.file_path, "w", encoding="utf-8") as handle:
            json.dump(profiles, handle, indent=2, ensure_ascii=True)
