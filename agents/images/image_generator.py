"""
Image Generator Agent
Generates images using Robolly API based on strategy briefs
"""
from crewai import Agent, Task
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from agents.images.tools.robolly_tools import (
    generate_robolly_image,
    validate_robolly_image,
    get_robolly_templates,
    generate_image_for_type,
    download_image
)
from agents.images.schemas.image_schemas import (
    GeneratedImage,
    ImageBrief,
    ImageType,
    ImageFormat
)
from agents.images.config.image_config import ROBOLLY_CONFIG

logger = logging.getLogger(__name__)


def create_image_generator(llm_model: str = "gpt-4o-mini") -> Agent:
    """
    Create the Image Generator Agent.

    This agent generates images using Robolly API:
    - Takes image briefs from Strategist
    - Calls Robolly API with appropriate templates
    - Validates generated images
    - Handles retries on failures

    Args:
        llm_model: LLM model to use for reasoning

    Returns:
        Configured CrewAI Agent
    """
    return Agent(
        role="Image Generation Specialist",
        goal="Generate high-quality images using Robolly API based on provided briefs",
        backstory="""You are an expert in automated image generation using template-based
        APIs. You understand:
        - How to work with Robolly's template system
        - Best practices for text overlays and composition
        - Importance of brand consistency
        - Error handling and retry strategies for API calls

        You take image briefs and transform them into API calls, ensuring:
        - Templates are correctly selected
        - Text is properly formatted for overlays
        - Style guides are applied consistently
        - Generated images are validated for quality

        You handle failures gracefully with retries and always validate
        that generated images meet quality standards before passing them on.""",
        tools=[
            generate_robolly_image,
            validate_robolly_image,
            get_robolly_templates
        ],
        verbose=True,
        allow_delegation=False
    )


def create_generation_task(
    agent: Agent,
    image_briefs: List[Dict[str, Any]],
    style_guide: str = "brand_primary"
) -> Task:
    """
    Create a generation task for the Image Generator.

    Args:
        agent: The Image Generator agent
        image_briefs: List of image briefs to generate
        style_guide: Style guide to apply

    Returns:
        CrewAI Task for image generation
    """
    briefs_text = "\n".join([
        f"- Type: {b['image_type']}, Title: {b['title_text']}, Template: {b.get('template_id', 'default')}"
        for b in image_briefs
    ])

    return Task(
        description=f"""Generate images based on the following briefs using Robolly API.

**Style Guide:** {style_guide}

**Image Briefs:**
{briefs_text}

**Your Tasks:**
1. For each brief, call the Robolly API with the appropriate template
2. Apply the {style_guide} style guide for consistent branding
3. Validate each generated image is accessible
4. Track generation time and file sizes
5. Retry failed generations up to 3 times

**Quality Requirements:**
- All images must be successfully generated
- All images must pass validation (accessible, correct format)
- Hero images should be 1200x630px
- Section images should be 800x450px
- OG cards should be 1200x630px""",
        agent=agent,
        expected_output="""List of GeneratedImage objects for each brief:
- robolly_render_id: Unique render ID
- original_url: URL to generated image
- dimensions: Width and height
- format: Image format (jpg, webp)
- generation_time_ms: Time taken
- validation_status: Pass/fail"""
    )


class ImageGenerator:
    """
    High-level interface for the Image Generator agent.
    Provides methods for generating images from briefs.
    """

    def __init__(self, llm_model: str = "gpt-4o-mini"):
        self.agent = create_image_generator(llm_model)
        self.llm_model = llm_model

    def generate_from_brief(
        self,
        brief: ImageBrief,
        style_guide: str = "brand_primary",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate a single image from a brief.

        Args:
            brief: ImageBrief with generation parameters
            style_guide: Style guide to apply
            max_retries: Maximum retry attempts

        Returns:
            Generation result with GeneratedImage if successful
        """
        start_time = datetime.utcnow()
        last_error = None

        for attempt in range(max_retries):
            try:
                # Get template ID
                template_id = brief.template_id
                if not template_id:
                    # Get default template for type
                    template_config = ROBOLLY_CONFIG["templates"].get(brief.image_type.value, {})
                    template_id = template_config.get("template_id")

                if not template_id:
                    return {
                        "success": False,
                        "error": f"No template configured for {brief.image_type.value}"
                    }

                # Generate image
                result = generate_robolly_image(
                    template_id=template_id,
                    title=brief.title_text,
                    subtitle=brief.subtitle_text,
                    style_guide=style_guide
                )

                if not result.get("success"):
                    last_error = result.get("error", "Generation failed")
                    logger.warning(f"Generation attempt {attempt + 1} failed: {last_error}")
                    continue

                # Validate image
                validation = validate_robolly_image(result["image_url"])
                if not validation.get("valid"):
                    last_error = f"Validation failed: {validation.get('error')}"
                    logger.warning(f"Validation attempt {attempt + 1} failed: {last_error}")
                    continue

                # Success - build GeneratedImage
                end_time = datetime.utcnow()
                total_time_ms = int((end_time - start_time).total_seconds() * 1000)

                generated = GeneratedImage(
                    image_type=brief.image_type,
                    robolly_render_id=result["render_id"],
                    original_url=result["image_url"],
                    title_text=brief.title_text,
                    template_id=template_id,
                    style_guide=style_guide,
                    dimensions=result.get("dimensions", {"width": 1200, "height": 630}),
                    format=ImageFormat(result.get("format", "jpg")),
                    file_size_bytes=validation.get("size_bytes"),
                    generated_at=datetime.utcnow(),
                    generation_time_ms=result.get("generation_time_ms", total_time_ms)
                )

                return {
                    "success": True,
                    "generated": generated.dict(),
                    "attempts": attempt + 1,
                    "total_time_ms": total_time_ms
                }

            except Exception as e:
                last_error = str(e)
                logger.error(f"Generation attempt {attempt + 1} error: {e}")

        return {
            "success": False,
            "error": last_error or "Max retries exceeded",
            "attempts": max_retries
        }

    def generate_batch(
        self,
        briefs: List[ImageBrief],
        style_guide: str = "brand_primary"
    ) -> Dict[str, Any]:
        """
        Generate multiple images from a list of briefs.

        Args:
            briefs: List of ImageBrief objects
            style_guide: Style guide to apply

        Returns:
            Batch generation results
        """
        start_time = datetime.utcnow()
        results = []
        successful = 0
        failed = 0

        for i, brief in enumerate(briefs):
            logger.info(f"Generating image {i + 1}/{len(briefs)}: {brief.image_type.value}")

            result = self.generate_from_brief(
                brief=brief,
                style_guide=style_guide
            )

            results.append({
                "brief_index": i,
                "image_type": brief.image_type.value,
                "result": result
            })

            if result.get("success"):
                successful += 1
            else:
                failed += 1

        end_time = datetime.utcnow()
        total_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return {
            "success": failed == 0,
            "results": results,
            "total": len(briefs),
            "successful": successful,
            "failed": failed,
            "total_time_ms": total_time_ms
        }

    def download_generated_image(
        self,
        image_url: str,
        local_path: str
    ) -> Dict[str, Any]:
        """
        Download a generated image to local storage.

        Args:
            image_url: URL of generated image
            local_path: Local path to save to

        Returns:
            Download result
        """
        return download_image(image_url, local_path)

    def get_available_templates(self) -> Dict[str, Any]:
        """
        Get list of configured templates.

        Returns:
            Template configuration
        """
        return get_robolly_templates()
