"""
On-Page Technical SEO Agent - Individual Page Optimization & Schema Markup
Part of the SEO multi-agent system (Agent 4/6)

Responsibilities:
- Generate schema.org structured data for NEW content
- Validate and optimize metadata for individual pages
- Recommend internal linking for new articles
- Optimize on-page technical factors during content creation

Note: For site-wide health monitoring, see scheduler/site_health_monitor.py
"""
from typing import List, Optional, Dict, Any
from crewai import Agent, Task, Crew
from dotenv import load_dotenv
import os

from agents.shared.prompt_loader import load_prompt
from agents.seo.tools.technical_tools import (
    SchemaGenerator,
    MetadataValidator,
    InternalLinkingAnalyzer,
    OnPageOptimizer
)

load_dotenv()


class OnPageTechnicalSEOAgent:
    """
    Technical SEO Specialist for on-page optimization and structured data.
    Fourth agent in the SEO content generation pipeline.
    Works with Copywriter output to add technical SEO elements.
    """

    def __init__(self, llm_model: str = "groq/mixtral-8x7b-32768"):
        """
        Initialize Technical SEO Specialist with technical tools.

        Args:
            llm_model: LiteLLM model string (default: groq/mixtral-8x7b-32768)
        """
        self.llm_model = llm_model

        # Initialize tools
        self.schema_generator = SchemaGenerator()
        self.metadata_validator = MetadataValidator()
        self.linking_analyzer = InternalLinkingAnalyzer()
        self.onpage_optimizer = OnPageOptimizer()

        # Create agent
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """Create the Technical SEO Specialist CrewAI agent with tools."""
        p = load_prompt("seo", "technical_seo")
        return Agent(
            role=p["role"],
            goal=p["goal"],
            backstory=p["backstory"],
            tools=[
                self.schema_generator.generate_schema,
                self.metadata_validator.validate_metadata,
                self.linking_analyzer.analyze_internal_links,
                self.onpage_optimizer.optimize_onpage
            ],
            llm=self.llm_model,  # CrewAI uses LiteLLM internally
            verbose=True,
            allow_delegation=False
        )
    
    def create_technical_task(
        self,
        article_metadata: Dict[str, Any],
        site_structure: Optional[Dict[str, Any]] = None,
        existing_pages: Optional[List[str]] = None
    ) -> Task:
        """Create a technical SEO task. Article content is injected via task.context."""
        p = load_prompt("seo", "technical_seo")
        task_cfg = p["tasks"]["technical_optimization"]
        description = task_cfg["description"].format(
            article_metadata=(
                f"Title: {article_metadata.get('title', 'N/A')}\n"
                f"Description: {article_metadata.get('description', 'N/A')}\n"
                f"Keywords: {', '.join(article_metadata.get('keywords', []))}"
            ),
            existing_pages=", ".join(existing_pages[:5]) if existing_pages else "None",
        )

        description += """

      YOUR TECHNICAL SEO DELIVERABLES:

      1. SCHEMA.ORG STRUCTURED DATA:
         - Generate Article schema (headline, description, author, datePublished)
         - Add BreadcrumbList and FAQPage schemas where applicable
         - Validate JSON-LD syntax

      2. METADATA VALIDATION:
         - Title tag (50-60 characters), meta description (150-160 characters)
         - Open Graph and Twitter Card tags

      3. ON-PAGE OPTIMIZATION:
         - Heading hierarchy, alt text, keyword placement, URL recommendations

      DELIVERABLE FORMAT:
      Complete technical SEO report with JSON-LD markup, validated metadata,
      on-page checklist, and prioritized action items."""

        return Task(
            description=description,
            agent=self.agent,
            expected_output=task_cfg["expected_output"],
        )
    
    def optimize_technical_seo(
        self,
        article_content: str,
        article_metadata: Dict[str, Any],
        site_structure: Optional[Dict[str, Any]] = None,
        existing_pages: Optional[List[str]] = None
    ) -> str:
        """
        Execute technical SEO optimization.
        
        Args:
            article_content: Article content to optimize
            article_metadata: Article metadata
            site_structure: Site structure info
            existing_pages: Existing pages for linking
            
        Returns:
            Technical SEO report with implementation code
        """
        task = self.create_technical_task(
            article_content=article_content,
            article_metadata=article_metadata,
            site_structure=site_structure,
            existing_pages=existing_pages
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=True
        )
        
        result = crew.kickoff()
        return result


# Convenience function
def add_technical_seo(
    article: str,
    metadata: Dict[str, Any],
    existing_pages: Optional[List[str]] = None
) -> str:
    """
    Quick function to add technical SEO to article.
    
    Args:
        article: Article content
        metadata: Article metadata
        existing_pages: Pages for internal linking
        
    Returns:
        Technical SEO report
    """
    specialist = OnPageTechnicalSEOAgent()
    return specialist.optimize_technical_seo(
        article_content=article,
        article_metadata=metadata,
        existing_pages=existing_pages
    )


if __name__ == "__main__":
    print("=== Technical SEO Specialist - Test Run ===\n")
    
    # Mock article for testing
    test_article = """
    # Content Marketing Strategy Guide
    
    Content marketing is essential for modern businesses...
    
    ## What is Content Marketing
    Content marketing involves creating valuable content...
    """
    
    test_metadata = {
        "title": "Content Marketing Strategy Guide",
        "description": "Learn content marketing strategies...",
        "keywords": ["content marketing", "marketing strategy"]
    }
    
    result = add_technical_seo(
        article=test_article,
        metadata=test_metadata,
        existing_pages=["blog/seo-guide", "blog/social-media"]
    )
    
    print("\n=== TECHNICAL OPTIMIZATION COMPLETE ===")
    print(result[:500] + "...")
