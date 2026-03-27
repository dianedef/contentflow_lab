"""
Image Strategy Tools
Tools for analyzing articles and determining image generation strategy
"""
import re
import logging
from typing import Dict, Any, List, Optional
from crewai.tools import tool

from agents.images.config.image_config import (
    IMAGE_STRATEGY_CONFIG,
    ROBOLLY_CONFIG
)
from agents.images.schemas.image_schemas import ImageType, ImageBrief

logger = logging.getLogger(__name__)


def _count_words(text: str) -> int:
    """Count words in text"""
    # Remove markdown syntax
    clean_text = re.sub(r'[#*`\[\]()!]', '', text)
    words = clean_text.split()
    return len(words)


def _extract_headings(content: str) -> List[Dict[str, Any]]:
    """Extract headings from markdown content"""
    headings = []
    lines = content.split('\n')

    for i, line in enumerate(lines):
        # Match markdown headings
        match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append({
                "level": level,
                "text": text,
                "line": i
            })

    return headings


def _extract_first_paragraph(content: str) -> str:
    """Extract first meaningful paragraph from content"""
    lines = content.split('\n')
    paragraph_lines = []

    in_paragraph = False
    for line in lines:
        stripped = line.strip()

        # Skip frontmatter
        if stripped == '---':
            in_paragraph = not in_paragraph
            continue

        # Skip headings
        if stripped.startswith('#'):
            continue

        # Skip empty lines
        if not stripped:
            if paragraph_lines:
                break
            continue

        paragraph_lines.append(stripped)

    return ' '.join(paragraph_lines[:3])  # First 3 lines


@tool("analyze_article_for_images")
def analyze_article_for_images(
    content: str,
    title: str,
    strategy_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze article content to determine optimal image strategy.

    Args:
        content: Article markdown content
        title: Article title
        strategy_type: Optional strategy type override (minimal, standard, hero+sections, rich)

    Returns:
        Dict containing:
        - recommended_strategy: str
        - word_count: int
        - heading_count: int
        - recommended_images: list of image briefs
        - section_opportunities: list of sections suitable for images
    """
    try:
        word_count = _count_words(content)
        headings = _extract_headings(content)
        h2_headings = [h for h in headings if h["level"] == 2]

        # Determine strategy based on content length
        thresholds = IMAGE_STRATEGY_CONFIG["auto_detect_threshold"]

        if strategy_type:
            recommended_strategy = strategy_type
        elif word_count < thresholds["short_article_words"]:
            recommended_strategy = "minimal"
        elif word_count < thresholds["medium_article_words"]:
            recommended_strategy = "standard"
        elif word_count < thresholds["long_article_words"]:
            recommended_strategy = "hero+sections"
        else:
            recommended_strategy = "rich"

        strategy_config = IMAGE_STRATEGY_CONFIG["strategies"].get(
            recommended_strategy,
            IMAGE_STRATEGY_CONFIG["strategies"]["standard"]
        )

        # Calculate number of section images
        num_section_images = 0
        if "sections_per_1000_words" in strategy_config:
            num_section_images = min(
                int(word_count / 1000 * strategy_config["sections_per_1000_words"]),
                len(h2_headings),
                strategy_config["max_images"] - 2  # Reserve space for hero and OG
            )

        # Build recommended images list
        recommended_images = []

        # Always include hero image
        if "hero_image" in strategy_config["image_types"]:
            recommended_images.append({
                "image_type": "hero_image",
                "title_text": title,
                "subtitle_text": _extract_first_paragraph(content)[:100] if content else None,
                "placement_hint": "top"
            })

        # Add section images
        if "section_image" in strategy_config["image_types"] and h2_headings:
            # Select evenly distributed sections
            step = max(1, len(h2_headings) // (num_section_images + 1))
            selected_sections = h2_headings[::step][:num_section_images]

            for i, section in enumerate(selected_sections):
                recommended_images.append({
                    "image_type": "section_image",
                    "title_text": section["text"],
                    "subtitle_text": None,
                    "placement_hint": f"after_heading_{section['line']}"
                })

        # Add OG card
        if "og_card" in strategy_config["image_types"]:
            recommended_images.append({
                "image_type": "og_card",
                "title_text": title,
                "subtitle_text": _extract_first_paragraph(content)[:80] if content else None,
                "placement_hint": "metadata"
            })

        # Identify all potential section opportunities
        section_opportunities = []
        for h in h2_headings:
            section_opportunities.append({
                "heading": h["text"],
                "line": h["line"],
                "recommended": h in [s for s in h2_headings[::step][:num_section_images]] if h2_headings else False
            })

        return {
            "success": True,
            "recommended_strategy": recommended_strategy,
            "word_count": word_count,
            "heading_count": len(headings),
            "h2_count": len(h2_headings),
            "recommended_images": recommended_images,
            "total_images": len(recommended_images),
            "section_opportunities": section_opportunities,
            "strategy_description": strategy_config["description"]
        }

    except Exception as e:
        logger.error(f"Article analysis error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool("extract_key_topics")
def extract_key_topics(
    content: str,
    title: str,
    max_topics: int = 5
) -> Dict[str, Any]:
    """
    Extract key topics from article for image context.

    Args:
        content: Article markdown content
        title: Article title
        max_topics: Maximum number of topics to extract

    Returns:
        Dict containing:
        - topics: list of topic strings
        - keywords: list of extracted keywords
    """
    try:
        # Simple keyword extraction (could be enhanced with NLP)
        # Remove markdown syntax
        clean_content = re.sub(r'[#*`\[\]()!]', '', content)
        clean_content = re.sub(r'http\S+', '', clean_content)

        # Extract potential keywords (capitalized words, repeated words)
        words = clean_content.split()
        word_freq = {}

        for word in words:
            # Clean word
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if len(clean_word) > 3:  # Skip short words
                word_freq[clean_word] = word_freq.get(clean_word, 0) + 1

        # Get most frequent words as keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [w[0] for w in sorted_words[:max_topics * 2]]

        # Extract headings as topics
        headings = _extract_headings(content)
        topics = [h["text"] for h in headings if h["level"] <= 2][:max_topics]

        # Add title keywords to topics if not enough
        if len(topics) < max_topics:
            title_words = [w for w in title.split() if len(w) > 3]
            for word in title_words:
                if word not in topics:
                    topics.append(word)
                    if len(topics) >= max_topics:
                        break

        return {
            "success": True,
            "topics": topics,
            "keywords": keywords[:max_topics],
            "title": title
        }

    except Exception as e:
        logger.error(f"Topic extraction error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool("determine_image_count")
def determine_image_count(
    word_count: int,
    heading_count: int,
    strategy_type: str = "standard"
) -> Dict[str, Any]:
    """
    Determine optimal number of images based on article metrics.

    Args:
        word_count: Number of words in article
        heading_count: Number of H2 headings
        strategy_type: Image strategy to use

    Returns:
        Dict with image count recommendations
    """
    try:
        strategy_config = IMAGE_STRATEGY_CONFIG["strategies"].get(
            strategy_type,
            IMAGE_STRATEGY_CONFIG["strategies"]["standard"]
        )

        max_images = strategy_config.get("max_images", 5)
        image_types = strategy_config.get("image_types", ["hero_image", "og_card"])

        # Base counts
        counts = {
            "hero_image": 1 if "hero_image" in image_types else 0,
            "og_card": 1 if "og_card" in image_types else 0,
            "section_image": 0,
            "thumbnail": 1 if "thumbnail" in image_types else 0
        }

        # Calculate section images
        if "section_image" in image_types:
            sections_per_1000 = strategy_config.get("sections_per_1000_words", 1)
            calculated_sections = int(word_count / 1000 * sections_per_1000)
            # Cap by heading count and max images
            max_sections = max_images - counts["hero_image"] - counts["og_card"] - counts["thumbnail"]
            counts["section_image"] = min(
                calculated_sections,
                heading_count,
                max_sections
            )

        total = sum(counts.values())

        return {
            "success": True,
            "total_images": total,
            "breakdown": counts,
            "strategy": strategy_type,
            "max_allowed": max_images,
            "word_count": word_count,
            "heading_count": heading_count
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@tool("select_templates_for_article")
def select_templates_for_article(
    image_types: List[str],
    style_guide: str = "brand_primary"
) -> Dict[str, Any]:
    """
    Select appropriate Robolly templates for required image types.

    Args:
        image_types: List of image types needed (hero_image, section_image, og_card, thumbnail)
        style_guide: Style guide to use

    Returns:
        Dict mapping image types to template configurations
    """
    try:
        templates = {}
        missing_templates = []

        for image_type in image_types:
            template_config = ROBOLLY_CONFIG["templates"].get(image_type)

            if template_config and template_config.get("template_id"):
                templates[image_type] = {
                    "template_id": template_config["template_id"],
                    "dimensions": template_config.get("dimensions", {}),
                    "format": template_config.get("format", "jpg"),
                    "quality": template_config.get("quality", 85),
                    "description": template_config.get("description", "")
                }
            else:
                missing_templates.append(image_type)
                templates[image_type] = {
                    "template_id": None,
                    "error": f"No template configured for {image_type}"
                }

        style = ROBOLLY_CONFIG["style_guides"].get(
            style_guide,
            ROBOLLY_CONFIG["style_guides"]["brand_primary"]
        )

        return {
            "success": len(missing_templates) == 0,
            "templates": templates,
            "style_guide": style_guide,
            "style_config": style,
            "missing_templates": missing_templates,
            "configured_count": len(image_types) - len(missing_templates)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def generate_seo_filename(
    title: str,
    image_type: str,
    file_hash: Optional[str] = None
) -> str:
    """
    Generate SEO-friendly filename for an image.

    Args:
        title: Article title
        image_type: Type of image
        file_hash: Optional hash for uniqueness

    Returns:
        SEO-optimized filename (without extension)
    """
    # Clean title
    clean_title = re.sub(r'[^\w\s-]', '', title.lower())
    clean_title = re.sub(r'[-\s]+', '-', clean_title).strip('-')

    # Truncate if too long
    if len(clean_title) > 50:
        clean_title = clean_title[:50].rsplit('-', 1)[0]

    # Add image type suffix
    type_suffix = {
        "hero_image": "hero",
        "section_image": "section",
        "og_card": "og",
        "thumbnail": "thumb"
    }.get(image_type, "img")

    # Build filename
    if file_hash:
        return f"{clean_title}-{type_suffix}-{file_hash[:8]}"
    else:
        return f"{clean_title}-{type_suffix}"


def generate_alt_text(
    title: str,
    image_type: str,
    context_keywords: Optional[List[str]] = None
) -> str:
    """
    Generate SEO-optimized alt text for an image.

    Args:
        title: Article/section title
        image_type: Type of image
        context_keywords: Optional context keywords

    Returns:
        Alt text string (20-100 characters)
    """
    # Base alt text from title
    alt_text = title

    # Add context based on image type
    type_context = {
        "hero_image": "featured image for",
        "section_image": "illustration for",
        "og_card": "social media card for",
        "thumbnail": "thumbnail for"
    }

    prefix = type_context.get(image_type, "image for")

    # Build alt text
    if context_keywords and len(context_keywords) > 0:
        keyword = context_keywords[0]
        alt_text = f"{prefix} {title} - {keyword}"
    else:
        alt_text = f"{prefix} {title}"

    # Ensure reasonable length
    if len(alt_text) < 20:
        alt_text = f"{alt_text} article"
    elif len(alt_text) > 100:
        alt_text = alt_text[:97] + "..."

    return alt_text
