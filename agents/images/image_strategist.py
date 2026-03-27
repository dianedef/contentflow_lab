"""
Image Strategist Agent
Analyzes article content and defines optimal visual strategy
"""
from crewai import Agent, Task
from typing import Dict, Any, Optional
import logging

from agents.images.tools.strategy_tools import (
    analyze_article_for_images,
    extract_key_topics,
    determine_image_count,
    select_templates_for_article
)
from agents.images.schemas.image_schemas import ImageStrategy, ImageBrief, ImageType

logger = logging.getLogger(__name__)


def create_image_strategist(llm_model: str = "gpt-4o-mini") -> Agent:
    """
    Create the Image Strategist Agent.

    This agent analyzes article content to determine:
    - Optimal number of images
    - Types of images needed (hero, sections, OG card)
    - Template selection for each image
    - Style guide to use

    Args:
        llm_model: LLM model to use for reasoning

    Returns:
        Configured CrewAI Agent
    """
    return Agent(
        role="Visual Content Strategist",
        goal="Analyze article content and create optimal visual strategy for engagement and SEO",
        backstory="""You are an expert visual content strategist with deep expertise in:
        - Content analysis and visual storytelling
        - SEO-optimized image strategy
        - Blog article visual design best practices
        - Understanding how images enhance reader engagement

        You analyze articles to determine the perfect image placement, quantity,
        and style that will maximize reader engagement while maintaining fast
        page load times. You understand that:
        - Hero images grab attention and set the tone
        - Section images break up long content and illustrate key points
        - OG cards are crucial for social sharing
        - Too many images slow down pages; too few reduce engagement

        You always consider the article's length, topic complexity, and target
        audience when recommending visual strategy.""",
        tools=[
            analyze_article_for_images,
            extract_key_topics,
            determine_image_count,
            select_templates_for_article
        ],
        verbose=True,
        allow_delegation=False
    )


def create_strategy_task(
    agent: Agent,
    article_content: str,
    article_title: str,
    article_slug: str,
    strategy_type: Optional[str] = None,
    style_guide: str = "brand_primary"
) -> Task:
    """
    Create a strategy task for the Image Strategist.

    Args:
        agent: The Image Strategist agent
        article_content: Markdown content of the article
        article_title: Title of the article
        article_slug: URL slug for the article
        strategy_type: Optional override for strategy type
        style_guide: Style guide to use

    Returns:
        CrewAI Task for image strategy
    """
    return Task(
        description=f"""Analyze the following article and create a comprehensive image strategy.

**Article Title:** {article_title}
**Article Slug:** {article_slug}
**Requested Style Guide:** {style_guide}
**Strategy Type Override:** {strategy_type or 'auto-detect'}

**Article Content:**
```
{article_content[:3000]}{'...' if len(article_content) > 3000 else ''}
```

**Your Tasks:**
1. Analyze the article structure (headings, length, topics)
2. Determine the recommended image strategy based on content
3. Extract key topics and keywords for image context
4. Select appropriate templates for each required image
5. Create detailed briefs for each image to generate

**Consider:**
- Article length (shorter = fewer images)
- Number of H2 sections (potential image opportunities)
- Topic complexity (complex topics may need more visuals)
- Target audience engagement

**Output Requirements:**
Return a complete ImageStrategy with:
- Recommended strategy type
- Number of images
- Detailed brief for each image (type, title, subtitle, placement)
- Template selections
- Style guide configuration""",
        agent=agent,
        expected_output="""A complete image strategy including:
- strategy_type: The recommended strategy (minimal/standard/hero+sections/rich)
- num_images: Total number of images to generate
- image_briefs: List of detailed briefs for each image with:
  - image_type (hero_image, section_image, og_card)
  - title_text (main text overlay)
  - subtitle_text (optional secondary text)
  - template_id (Robolly template to use)
  - placement_hint (where in article to place)
- style_guide: Confirmed style guide name
- reasoning: Brief explanation of strategy choices"""
    )


class ImageStrategist:
    """
    High-level interface for the Image Strategist agent.
    Provides methods for analyzing articles and creating image strategies.
    """

    def __init__(self, llm_model: str = "gpt-4o-mini"):
        self.agent = create_image_strategist(llm_model)
        self.llm_model = llm_model

    def analyze_article(
        self,
        content: str,
        title: str,
        slug: str,
        strategy_type: Optional[str] = None,
        style_guide: str = "brand_primary"
    ) -> Dict[str, Any]:
        """
        Analyze an article and create image strategy.

        Args:
            content: Article markdown content
            title: Article title
            slug: Article URL slug
            strategy_type: Optional strategy override
            style_guide: Style guide to use

        Returns:
            ImageStrategy as dict
        """
        try:
            # Use tools directly for faster processing
            analysis = analyze_article_for_images(
                content=content,
                title=title,
                strategy_type=strategy_type
            )

            if not analysis.get("success"):
                return {
                    "success": False,
                    "error": analysis.get("error", "Analysis failed")
                }

            topics = extract_key_topics(
                content=content,
                title=title,
                max_topics=5
            )

            # Get template selections
            image_types = [img["image_type"] for img in analysis["recommended_images"]]
            templates = select_templates_for_article(
                image_types=image_types,
                style_guide=style_guide
            )

            # Build image briefs
            image_briefs = []
            for img in analysis["recommended_images"]:
                img_type = img["image_type"]
                template_config = templates["templates"].get(img_type, {})

                brief = ImageBrief(
                    image_type=ImageType(img_type),
                    title_text=img["title_text"],
                    subtitle_text=img.get("subtitle_text"),
                    template_id=template_config.get("template_id"),
                    placement_hint=img.get("placement_hint"),
                    context_keywords=topics.get("keywords", [])[:3]
                )
                image_briefs.append(brief)

            # Build strategy
            strategy = ImageStrategy(
                article_title=title,
                article_slug=slug,
                article_topics=topics.get("topics", []),
                article_word_count=analysis["word_count"],
                strategy_type=analysis["recommended_strategy"],
                style_guide=style_guide,
                num_images=len(image_briefs),
                image_briefs=image_briefs,
                generate_og_card=any(b.image_type == ImageType.OG_CARD for b in image_briefs),
                generate_responsive=True
            )

            return {
                "success": True,
                "strategy": strategy.dict(),
                "analysis": analysis,
                "templates": templates
            }

        except Exception as e:
            logger.error(f"Error analyzing article: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def quick_strategy(
        self,
        title: str,
        word_count: int,
        heading_count: int = 0,
        strategy_type: str = "standard"
    ) -> Dict[str, Any]:
        """
        Quick strategy determination without full article analysis.

        Args:
            title: Article title
            word_count: Approximate word count
            heading_count: Number of H2 headings
            strategy_type: Strategy to use

        Returns:
            Quick strategy recommendation
        """
        counts = determine_image_count(
            word_count=word_count,
            heading_count=heading_count,
            strategy_type=strategy_type
        )

        return {
            "title": title,
            "recommended_images": counts.get("total_images", 2),
            "breakdown": counts.get("breakdown", {}),
            "strategy": strategy_type
        }
