"""Default system templates for content generation.

Each template defines the standard sections for a content type,
with well-crafted default prompts for AI generation.
"""

from api.models.templates import DefaultTemplateData, TemplateSectionData


def get_default_templates() -> list[DefaultTemplateData]:
    """Return the 4 default system templates."""
    return [
        _seo_article_template(),
        _newsletter_template(),
        _youtube_longform_template(),
        _shortform_video_template(),
    ]


def _seo_article_template() -> DefaultTemplateData:
    return DefaultTemplateData(
        name="SEO Article",
        slug="seo-article",
        content_type="article",
        description="Complete SEO-optimized article with keyword targeting, semantic entities, and internal linking strategy.",
        sections=[
            TemplateSectionData(
                name="title",
                label="Title",
                field_type="text",
                order=0,
                description="SEO-optimized article title with primary keyword",
                placeholder="e.g. How to Optimize Your Website for Core Web Vitals in 2025",
                default_prompt="Generate an SEO-optimized title for the article. Include the primary keyword naturally. Keep it under 60 characters for SERP display. Make it compelling and click-worthy while accurately representing the content. Use power words where appropriate.",
            ),
            TemplateSectionData(
                name="target_keyword",
                label="Target Keyword",
                field_type="text",
                order=1,
                description="Primary keyword to target for search rankings",
                placeholder="e.g. core web vitals optimization",
                default_prompt="Identify the most strategic primary keyword for this article based on the topic and audience. Consider search volume, competition level, and user intent. Return a single keyword phrase (2-4 words) that best represents the article's focus.",
            ),
            TemplateSectionData(
                name="meta_description",
                label="Meta Description",
                field_type="text",
                order=2,
                description="SERP meta description (150-160 chars)",
                placeholder="e.g. Learn how to improve your Core Web Vitals scores...",
                default_prompt="Write a compelling meta description for the article (150-160 characters). Include the target keyword naturally. Create urgency or curiosity. Focus on the benefit the reader gets. End with an implicit or explicit call to action.",
            ),
            TemplateSectionData(
                name="semantic_entities",
                label="Semantic Entities",
                field_type="tags",
                order=3,
                description="Related semantic entities for topical authority",
                default_prompt="Identify 8-12 semantic entities (NLP entities, related concepts, LSI keywords) that should be covered in this article to demonstrate topical authority. Include related terms, synonyms, and contextually relevant concepts that search engines associate with the primary topic.",
            ),
            TemplateSectionData(
                name="introduction",
                label="Introduction",
                field_type="markdown",
                order=4,
                description="Engaging opening paragraph with hook",
                default_prompt="Write a compelling introduction (150-200 words). Start with a hook that addresses the reader's pain point or curiosity. Establish relevance and authority. Include the target keyword in the first 100 words. Preview what the reader will learn. Use a conversational but professional tone.",
            ),
            TemplateSectionData(
                name="body_sections",
                label="Body Sections",
                field_type="markdown",
                order=5,
                description="Main article content with H2/H3 structure",
                default_prompt="Generate the main article body with 4-6 H2 sections, each with 2-3 H3 subsections. Include the target keyword and semantic entities naturally throughout. Use short paragraphs (2-3 sentences). Include bullet points and numbered lists where appropriate. Add practical examples, data points, or case studies. Aim for 1500-2000 words total. Each section should flow logically to the next.",
            ),
            TemplateSectionData(
                name="internal_links",
                label="Internal Links",
                field_type="list",
                order=6,
                description="Suggested internal linking opportunities",
                default_prompt="Suggest 5-8 internal linking opportunities for this article. For each, provide: the anchor text, the type of page to link to (pillar page, cluster article, resource), and why this link strengthens topical authority. Consider the content's position in the topical cluster.",
            ),
            TemplateSectionData(
                name="conclusion",
                label="Conclusion",
                field_type="markdown",
                order=7,
                description="Summary and call to action",
                default_prompt="Write a conclusion (100-150 words). Summarize the key takeaways in 2-3 sentences. Reinforce the main value proposition. Include a clear call to action relevant to the reader's next step. Optionally include the target keyword one final time.",
            ),
            TemplateSectionData(
                name="hero_image",
                label="Hero Image",
                field_type="image",
                required=False,
                order=8,
                description="Featured image prompt for the article header",
                default_prompt="Generate a detailed image prompt for the article's hero image. Describe the subject, visual style (photographic, illustration, 3D render), composition, color palette, lighting, and mood. The image should visually represent the article's main topic and appeal to the target audience. Be specific enough for an AI image generator to produce a high-quality result.",
            ),
        ],
    )


def _newsletter_template() -> DefaultTemplateData:
    return DefaultTemplateData(
        name="Newsletter",
        slug="newsletter",
        content_type="newsletter",
        description="Professional newsletter with curated sections, engaging subject line, and clear CTA.",
        sections=[
            TemplateSectionData(
                name="subject_line",
                label="Subject Line",
                field_type="text",
                order=0,
                description="Email subject line (max 50 chars for mobile)",
                placeholder="e.g. 3 AI Tools That Changed My Workflow This Week",
                default_prompt="Generate 3 subject line options for this newsletter. Each should be under 50 characters, create curiosity or urgency, and avoid spam trigger words. Use personalization where possible. Include one emoji-based option and one question-based option.",
            ),
            TemplateSectionData(
                name="preview_text",
                label="Preview Text",
                field_type="text",
                order=1,
                description="Email preview text shown in inbox (60-90 chars)",
                default_prompt="Write preview text (60-90 characters) that complements the subject line without repeating it. This appears after the subject in inbox previews. Add context that increases open rates.",
            ),
            TemplateSectionData(
                name="introduction",
                label="Introduction",
                field_type="markdown",
                order=2,
                description="Personal greeting and context setting",
                default_prompt="Write a brief, warm introduction (50-80 words). Address the reader directly. Reference something timely or relevant to the audience. Set expectations for what's in this issue. Keep it conversational and authentic.",
            ),
            TemplateSectionData(
                name="sections",
                label="Content Sections",
                field_type="markdown",
                order=3,
                description="Main newsletter content sections",
                default_prompt="Generate 3-5 newsletter sections based on the topics. Each section should have: a catchy heading, 80-120 words of insightful content, and a key takeaway or action item. Include relevant data points, tools, or resources. Mix formats: one trend analysis, one practical tip, and one curated resource recommendation.",
            ),
            TemplateSectionData(
                name="cta",
                label="Call to Action",
                field_type="markdown",
                order=4,
                description="Primary call to action",
                default_prompt="Write a clear, compelling call to action. It should feel natural, not salesy. Tie it to the newsletter's main theme. Provide one primary CTA and one secondary CTA. Use action verbs and make the benefit clear.",
            ),
            TemplateSectionData(
                name="outro",
                label="Outro",
                field_type="markdown",
                order=5,
                description="Sign-off and social links",
                default_prompt="Write a brief sign-off (30-50 words). Include a personal touch or teaser for the next issue. Encourage replies or feedback. Keep it warm and authentic.",
            ),
        ],
    )


def _youtube_longform_template() -> DefaultTemplateData:
    return DefaultTemplateData(
        name="YouTube Long-form",
        slug="youtube-longform",
        content_type="video_script",
        description="Complete YouTube video script with hook, structured outline, B-roll suggestions, and SEO metadata.",
        sections=[
            TemplateSectionData(
                name="title",
                label="Video Title",
                field_type="text",
                order=0,
                description="YouTube title optimized for CTR and search",
                placeholder="e.g. I Tested 10 AI Coding Tools — Here's What Actually Works",
                default_prompt="Generate a YouTube video title optimized for both click-through rate and search. Keep it under 70 characters. Use proven patterns: numbers, curiosity gaps, 'How to', or contrarian takes. Include the main keyword naturally. Avoid clickbait that doesn't deliver.",
            ),
            TemplateSectionData(
                name="hook",
                label="Hook (First 30s)",
                field_type="markdown",
                order=1,
                description="Opening hook to retain viewers in the first 30 seconds",
                default_prompt="Write a compelling hook for the first 30 seconds of the video. Start with a bold statement, surprising statistic, or relatable problem. Create a loop that makes viewers want to stay. Include a brief preview of what they'll learn. Write it as a spoken script (conversational, use 'you').",
            ),
            TemplateSectionData(
                name="outline",
                label="Video Outline",
                field_type="list",
                order=2,
                description="Structured outline with timestamps",
                default_prompt="Create a detailed video outline with 5-8 main sections. For each section include: title, estimated duration, key points to cover, and transition to the next section. Aim for a 10-15 minute total video. Include a mid-roll CTA position. Structure for maximum retention (front-load value).",
            ),
            TemplateSectionData(
                name="script_body",
                label="Full Script",
                field_type="markdown",
                order=3,
                description="Complete spoken script with delivery notes",
                default_prompt="Write the full video script based on the outline. Use conversational language (contractions, 'you', direct address). Include [DELIVERY NOTES] for emphasis, pauses, or tone changes. Add [B-ROLL] markers where visual aids should appear. Write at ~150 words per minute of target duration. Include pattern interrupts every 2-3 minutes to maintain retention.",
            ),
            TemplateSectionData(
                name="b_roll_suggestions",
                label="B-Roll Suggestions",
                field_type="list",
                order=4,
                description="Visual aids and B-roll footage ideas",
                default_prompt="Suggest 8-12 B-roll shots or visual aids for the video. Include: screen recordings, graphics/animations to create, stock footage suggestions, and text overlays. For each, specify the section it corresponds to and why it enhances understanding.",
            ),
            TemplateSectionData(
                name="thumbnail_text",
                label="Thumbnail Text",
                field_type="text",
                order=5,
                description="Text overlay for YouTube thumbnail (2-4 words)",
                default_prompt="Suggest 3 thumbnail text options (2-4 words each). They should be readable at small sizes, create curiosity, and complement the title without repeating it. Consider contrast and emotional triggers.",
            ),
            TemplateSectionData(
                name="description",
                label="Video Description",
                field_type="markdown",
                order=6,
                description="YouTube description with timestamps and links",
                default_prompt="Write a YouTube description. First 2 lines should hook readers (shown before 'Show more'). Include: brief summary, chapter timestamps matching the outline, relevant links and resources mentioned, 3 related video suggestions, and a standard outro with social links placeholder. Include 3-5 relevant keywords naturally.",
            ),
            TemplateSectionData(
                name="tags",
                label="Tags",
                field_type="tags",
                order=7,
                description="YouTube tags for discoverability",
                default_prompt="Generate 15-20 YouTube tags. Include: the exact title, main keyword variations, long-tail keywords, related topics, and the channel name placeholder. Order from most to least specific. Keep total character count under 500.",
            ),
            TemplateSectionData(
                name="thumbnail_image",
                label="Thumbnail Image",
                field_type="image",
                required=False,
                order=8,
                description="AI image prompt for the YouTube thumbnail",
                default_prompt="Generate a detailed image prompt for the YouTube thumbnail. Describe a bold, eye-catching composition with high contrast. Include: main subject/person, facial expression if applicable, background style, text placement area, color scheme (bright, saturated), and visual hierarchy. The thumbnail must be readable at small sizes and stand out in a feed. Style: professional YouTube thumbnail aesthetic.",
            ),
        ],
    )


def _shortform_video_template() -> DefaultTemplateData:
    return DefaultTemplateData(
        name="Short-form Video",
        slug="shortform-video",
        content_type="video_script",
        description="Short-form video script (TikTok, Reels, Shorts) with hook-first structure and viral optimization.",
        sections=[
            TemplateSectionData(
                name="title",
                label="Title / Caption",
                field_type="text",
                order=0,
                description="Short video title or caption",
                placeholder="e.g. This AI trick saves me 2 hours every day",
                default_prompt="Write a short video caption/title that creates immediate curiosity. Keep it under 100 characters. Use first-person perspective. Include a number or specific claim. Make it shareable and relatable.",
            ),
            TemplateSectionData(
                name="hook",
                label="Hook (First 3s)",
                field_type="text",
                order=1,
                description="Opening hook — must grab attention in 3 seconds",
                default_prompt="Write a 3-second opening hook. This is the most critical part — viewers decide to stay or scroll. Use one of these patterns: bold claim, 'Stop scrolling if...', controversial opinion, visual surprise description, or 'POV:'. Keep it under 15 words. Write as spoken text.",
            ),
            TemplateSectionData(
                name="script_body",
                label="Script Body",
                field_type="markdown",
                order=2,
                description="Main content (30-60 seconds of speaking)",
                default_prompt="Write a short-form video script (30-60 seconds). Structure: Hook → Problem → Solution/Value → CTA. Use punchy, conversational language. Include [VISUAL] markers for cuts or overlays. Keep sentences under 10 words. Use rhythm and repetition for engagement. End with a loop back to the hook or a cliffhanger for comments.",
            ),
            TemplateSectionData(
                name="captions",
                label="On-screen Captions",
                field_type="list",
                order=3,
                description="Text overlays timed to the script",
                default_prompt="Generate on-screen caption text for key moments in the script. Include 5-8 text overlays, each 3-6 words. Highlight key stats, surprising claims, or action items. Specify timing (e.g. '0:03-0:05'). Use ALL CAPS for emphasis words.",
            ),
            TemplateSectionData(
                name="hashtags",
                label="Hashtags",
                field_type="tags",
                order=4,
                description="Relevant hashtags for discoverability",
                default_prompt="Generate 10-15 hashtags. Mix: 3-4 high-volume tags (1M+ posts), 5-6 medium tags (100K-1M), and 3-4 niche-specific tags. Include trending format tags if applicable (e.g. #LearnOnTikTok). Keep total under 30 hashtags.",
            ),
            TemplateSectionData(
                name="thumbnail_text",
                label="Cover/Thumbnail Text",
                field_type="text",
                order=5,
                description="Text for the video cover image (2-3 words)",
                default_prompt="Suggest 3 cover/thumbnail text options (2-3 words max). They should be bold, readable on small screens, and create enough curiosity to tap. Consider using emoji or symbols sparingly.",
            ),
        ],
    )
