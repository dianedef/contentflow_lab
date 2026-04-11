"""
Editor Agent - Quality Control & Final Harmonization
Part of the SEO multi-agent system (Agent 6/6)

Responsibilities:
- Validate content quality and grammar
- Ensure tone of voice and brand consistency
- Final harmonization before publication
- Format markdown and prepare for deployment
"""
from typing import List, Optional, Dict, Any
from crewai import Agent, Task, Crew
from dotenv import load_dotenv
import os

from agents.shared.prompt_loader import load_prompt
from agents.seo.tools.editing_tools import (
    QualityChecker,
    ConsistencyValidator,
    MarkdownFormatter,
    PublicationPreparer
)

load_dotenv()


class EditorAgent:
    """
    Editor Agent for final quality control and content harmonization.
    Final agent in the SEO content generation pipeline.
    Reviews all previous work and prepares content for publication.
    """

    def __init__(self, llm_model: str = "groq/mixtral-8x7b-32768"):
        """
        Initialize Editor with editing tools.

        Args:
            llm_model: LiteLLM model string (default: groq/mixtral-8x7b-32768)
        """
        self.llm_model = llm_model

        # Initialize tools
        self.quality_checker = QualityChecker()
        self.consistency_validator = ConsistencyValidator()
        self.markdown_formatter = MarkdownFormatter()
        self.publication_preparer = PublicationPreparer()

        # Create agent
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """Create the Editor CrewAI agent with tools."""
        p = load_prompt("seo", "editor")
        return Agent(
            role=p["role"],
            goal=p["goal"],
            backstory=p["backstory"],
            tools=[
                self.quality_checker.check_quality,
                self.consistency_validator.validate_consistency,
                self.markdown_formatter.format_markdown,
                self.publication_preparer.prepare_for_publication
            ],
            llm=self.llm_model,  # CrewAI uses LiteLLM internally
            verbose=True,
            allow_delegation=False
        )
    
    def create_editing_task(
        self,
        brand_guidelines: Optional[Dict[str, Any]] = None,
        quality_standards: Optional[Dict[str, Any]] = None
    ) -> Task:
        """Create a final editing task. Article and SEO report are injected via task.context."""
        p = load_prompt("seo", "editor")
        task_cfg = p["tasks"]["editing"]
        description = task_cfg["description"]

        if brand_guidelines:
            description += (
                f"\n\nBRAND GUIDELINES: Voice={brand_guidelines.get('voice', 'N/A')}, "
                f"Tone={brand_guidelines.get('tone', 'N/A')}, "
                f"Values={', '.join(brand_guidelines.get('values', []))}"
            )

        if quality_standards:
            description += (
                f"\n\nQUALITY STANDARDS: Min words={quality_standards.get('min_words', 1500)}, "
                f"Uniqueness={quality_standards.get('uniqueness', 90)}%, "
                f"Readability={quality_standards.get('readability_target', 'Flesch 60-70')}"
            )

        return Task(
            description=description,
            agent=self.agent,
            expected_output=task_cfg["expected_output"],
        )
    
    def edit_and_finalize(
        self,
        article_content: str,
        technical_seo_report: str,
        brand_guidelines: Optional[Dict[str, Any]] = None,
        quality_standards: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute final editing and prepare for publication.
        
        Args:
            article_content: Article to edit
            technical_seo_report: Technical SEO recommendations
            brand_guidelines: Brand guidelines
            quality_standards: Quality standards
            
        Returns:
            Editorial report, final article, and publication checklist
        """
        task = self.create_editing_task(
            article_content=article_content,
            technical_seo_report=technical_seo_report,
            brand_guidelines=brand_guidelines,
            quality_standards=quality_standards
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=True
        )
        
        result = crew.kickoff()
        return result


# Convenience function
def finalize_article(
    article: str,
    technical_report: str,
    brand_voice: Optional[str] = None
) -> str:
    """
    Quick function to finalize article for publication.
    
    Args:
        article: Article content
        technical_report: Technical SEO report
        brand_voice: Brand voice description
        
    Returns:
        Final edited article with editorial report
    """
    editor = EditorAgent()
    
    brand_guidelines = {"voice": brand_voice} if brand_voice else None
    
    return editor.edit_and_finalize(
        article_content=article,
        technical_seo_report=technical_report,
        brand_guidelines=brand_guidelines
    )


if __name__ == "__main__":
    print("=== Editor Agent - Test Run ===\n")
    
    # Mock inputs for testing
    test_article = """
    # Content Marketing Strategy Guide
    
    Content marketing has become essential for businesses in 2024...
    
    ## What is Content Marketing
    Content marketing is the strategic approach...
    """
    
    test_technical = """
    Technical SEO Report:
    - Schema markup: Article schema generated
    - Metadata: All validated
    - Internal links: 3 opportunities identified
    """
    
    result = finalize_article(
        article=test_article,
        technical_report=test_technical,
        brand_voice="Professional but approachable"
    )
    
    print("\n=== EDITORIAL REVIEW COMPLETE ===")
    print(result[:500] + "...")
