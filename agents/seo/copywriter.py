"""
Copywriter Agent - SEO-Optimized Content Generation
Part of the SEO multi-agent system (Agent 3/6)

Responsibilities:
- Write natural, engaging, SEO-optimized content
- Strategic keyword insertion without over-optimization
- Create compelling metadata (titles, descriptions)
- Adapt tone of voice to target audience
"""
from typing import List, Optional, Dict, Any
from crewai import Agent, Task, Crew
from dotenv import load_dotenv
import os

from agents.seo.tools.writing_tools import KeywordIntegrator
from agents.shared.tools.firecrawl_tools import scrape_url
from agents.shared.prompt_loader import load_prompt

load_dotenv()


class CopywriterAgent:
    """
    Copywriter Agent for SEO-optimized content creation.
    Third agent in the SEO content generation pipeline.
    Works with Content Strategist output to create final content.
    """

    def __init__(self, llm_model: str = "groq/mixtral-8x7b-32768"):
        """
        Initialize Copywriter with writing tools.

        Args:
            llm_model: LiteLLM model string (default: groq/mixtral-8x7b-32768)
        """
        self.llm_model = llm_model

        # Initialize tools
        self.keyword_integrator = KeywordIntegrator()

        # Create agent
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """Create the Copywriter CrewAI agent with tools."""
        p = load_prompt("seo", "copywriter")
        return Agent(
            role=p["role"],
            goal=p["goal"],
            backstory=p["backstory"],
            tools=[
                self.keyword_integrator.integrate_keywords,
                scrape_url,
            ],
            llm=self.llm_model,  # CrewAI uses LiteLLM internally
            verbose=True,
            allow_delegation=False
        )
    
    def create_writing_task(
        self,
        target_keywords: List[str],
        tone: str = "professional",
        brand_voice: Optional[str] = None,
        target_audience: Optional[str] = None,
        word_count: int = 2000
    ) -> Task:
        """Create a writing task. Content outline is injected via task.context."""
        primary_keyword = target_keywords[0] if target_keywords else "topic"
        secondary_keywords = ", ".join(target_keywords[1:5]) if len(target_keywords) > 1 else "None"

        p = load_prompt("seo", "copywriter")
        task_cfg = p["tasks"]["writing"]
        description = task_cfg["description"].format(
            primary_keyword=primary_keyword,
            word_count=word_count,
            tone=tone,
        )

        description += f"""

      YOUR WRITING REQUIREMENTS:

      1. CONTENT QUALITY:
         - Write engaging, valuable content that serves the reader first
         - Use storytelling techniques to maintain interest
         - Include specific examples and actionable advice
         - Break up text with subheadings every 300-400 words
         - Use short paragraphs (3-4 sentences max) for readability

      2. SEO OPTIMIZATION:
         - Integrate primary keyword "{primary_keyword}" naturally (1-2% density)
         - Include secondary keywords: {secondary_keywords}
         - Place primary keyword in first 100 words, one H2, and conclusion
         - Never keyword stuff — prioritize natural language"""

        if brand_voice:
            description += f"\n\n      3. BRAND VOICE: {brand_voice}"

        if target_audience:
            description += f"\n\n      4. TARGET AUDIENCE: {target_audience} — write at their level, address their pain points"

        description += """

      DELIVERABLE FORMAT:
      Return the complete article in markdown with metadata section (title tag,
      meta description, tags), full content, image placeholders, and a CTA.

      Write for humans first, search engines second."""

        return Task(
            description=description,
            agent=self.agent,
            expected_output=(
                f"A complete, SEO-optimized article of approximately {word_count} words in markdown format "
                "with metadata, proper structure, keyword integration, and compelling copy."
            ),
        )
    
    def write_article(
        self,
        content_outline: str,
        target_keywords: List[str],
        tone: str = "professional",
        brand_voice: Optional[str] = None,
        target_audience: Optional[str] = None,
        word_count: int = 2000
    ) -> str:
        """
        Execute article writing based on outline.
        
        Args:
            content_outline: Content outline from strategist
            target_keywords: Target keywords list
            tone: Writing tone
            brand_voice: Brand voice guidelines
            target_audience: Target audience
            word_count: Target word count
            
        Returns:
            Complete article in markdown format
        """
        task = self.create_writing_task(
            content_outline=content_outline,
            target_keywords=target_keywords,
            tone=tone,
            brand_voice=brand_voice,
            target_audience=target_audience,
            word_count=word_count
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=True
        )
        
        result = crew.kickoff()
        return result


# Convenience function for direct usage
def write_seo_article(
    outline: str,
    keywords: List[str],
    tone: str = "professional",
    word_count: int = 2000
) -> str:
    """
    Quick function to write SEO article from outline.
    
    Args:
        outline: Content outline
        keywords: Target keywords
        tone: Writing tone
        word_count: Target word count
        
    Returns:
        Complete article in markdown
    """
    copywriter = CopywriterAgent()
    return copywriter.write_article(
        content_outline=outline,
        target_keywords=keywords,
        tone=tone,
        word_count=word_count
    )


if __name__ == "__main__":
    # Example usage
    print("=== Copywriter Agent - Test Run ===\n")
    
    # Mock outline for testing
    outline = """
    # Content Marketing Strategy Guide
    
    ## Introduction (200 words)
    - Hook: Content marketing statistics
    - What is content marketing strategy
    - Why it matters for businesses
    
    ## What is Content Marketing Strategy (400 words)
    - Definition
    - Core components
    - Difference from tactics
    
    ## Building a Content Strategy (500 words)
    - Audience research
    - Goal setting
    - Content planning
    - Distribution channels
    
    ## Best Practices (400 words)
    - Consistency
    - Quality over quantity
    - Data-driven decisions
    - Continuous optimization
    
    ## Conclusion (200 words)
    - Recap key points
    - Call to action
    """
    
    result = write_seo_article(
        outline=outline,
        keywords=["content marketing strategy", "content strategy", "marketing plan"],
        tone="professional",
        word_count=2000
    )
    
    print("\n=== ARTICLE COMPLETE ===")
    print(result[:500] + "...")
