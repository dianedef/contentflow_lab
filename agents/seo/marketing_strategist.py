"""
Marketing Strategist Agent - Business Prioritization & ROI Analysis
Part of the SEO multi-agent system (Agent 5/6 - inserted before Editor)

Responsibilities:
- Create prioritization matrix aligned with business objectives
- Analyze potential ROI of SEO actions
- Provide strategic recommendations for competitive markets
- Validate marketing relevance of content
"""
from typing import List, Optional, Dict, Any
from crewai import Agent, Task, Crew
from dotenv import load_dotenv
import os

from agents.shared.prompt_loader import load_prompt
from agents.seo.tools.marketing_tools import (
    PrioritizationMatrix,
    ROIAnalyzer,
    CompetitivePositioning,
    MarketingValidator
)

load_dotenv()


class MarketingStrategistAgent:
    """
    Marketing Strategist Agent for business alignment and ROI optimization.
    Works between Technical SEO and Editor to ensure business value.
    Reviews content strategy and technical implementation for business impact.
    """

    def __init__(self, llm_model: str = "groq/mixtral-8x7b-32768"):
        """
        Initialize Marketing Strategist with marketing tools.

        Args:
            llm_model: LiteLLM model string (default: groq/mixtral-8x7b-32768)
        """
        self.llm_model = llm_model

        # Initialize tools
        self.prioritization_matrix = PrioritizationMatrix()
        self.roi_analyzer = ROIAnalyzer()
        self.competitive_positioning = CompetitivePositioning()
        self.marketing_validator = MarketingValidator()

        # Create agent
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """Create the Marketing Strategist CrewAI agent with tools."""
        p = load_prompt("seo", "marketing_strategist")
        return Agent(
            role=p["role"],
            goal=p["goal"],
            backstory=p["backstory"],
            tools=[
                self.prioritization_matrix.create_priority_matrix,
                self.roi_analyzer.analyze_roi,
                self.competitive_positioning.assess_positioning,
                self.marketing_validator.validate_marketing_fit
            ],
            llm=self.llm_model,  # CrewAI uses LiteLLM internally
            verbose=True,
            allow_delegation=False
        )
    
    def create_strategy_task(
        self,
        business_goals: Optional[List[str]] = None,
        target_audience: Optional[str] = None,
        competitive_landscape: Optional[Dict[str, Any]] = None,
        budget_constraints: Optional[Dict[str, Any]] = None
    ) -> Task:
        """Create a marketing strategy task. Content/strategy/technical context injected via task.context."""
        p = load_prompt("seo", "marketing_strategist")
        task_cfg = p["tasks"]["strategy_validation"]
        description = task_cfg["description"].format(
            business_goals=", ".join(business_goals or ["Increase organic traffic and conversions"]),
            target_audience=target_audience or "Not specified",
        )

        if business_goals:
            description += f"""

      GOAL ALIGNMENT: For each goal ({', '.join(business_goals)}), assess contribution,
      expected impact, timeline to results, and key metrics."""

        if competitive_landscape:
            description += """

      COMPETITIVE POSITIONING: How does this content differentiate us?
      Are we leading or late to this topic?"""
        
        description += """

      DELIVERABLES: ROI projection, priority score (0-100), strategic recommendations,
      success KPIs (30/60/90-day benchmarks), and Go/No-Go recommendation."""

        return Task(
            description=description,
            agent=self.agent,
            expected_output=task_cfg["expected_output"],
        )
    
    def evaluate_strategy(
        self,
        content_strategy: str,
        article_content: str,
        technical_seo: str,
        business_goals: Optional[List[str]] = None,
        target_audience: Optional[str] = None,
        competitive_landscape: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute marketing strategy evaluation.
        
        Args:
            content_strategy: Content strategy from strategist
            article_content: Article from copywriter
            technical_seo: Technical SEO report
            business_goals: Business objectives
            target_audience: Target audience
            competitive_landscape: Competitive data
            
        Returns:
            Marketing strategy report with recommendations
        """
        task = self.create_strategy_task(
            content_strategy=content_strategy,
            article_content=article_content,
            technical_seo=technical_seo,
            business_goals=business_goals,
            target_audience=target_audience,
            competitive_landscape=competitive_landscape
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=True
        )
        
        result = crew.kickoff()
        return result


# Convenience function
def validate_business_case(
    strategy: str,
    article: str,
    technical: str,
    business_goals: Optional[List[str]] = None
) -> str:
    """
    Quick function to validate business case for content.
    
    Args:
        strategy: Content strategy
        article: Article content
        technical: Technical SEO report
        business_goals: Business objectives
        
    Returns:
        Marketing strategy report
    """
    strategist = MarketingStrategistAgent()
    return strategist.evaluate_strategy(
        content_strategy=strategy,
        article_content=article,
        technical_seo=technical,
        business_goals=business_goals
    )


if __name__ == "__main__":
    print("=== Marketing Strategist Agent - Test Run ===\n")
    
    # Mock inputs for testing
    test_strategy = """
    Content Strategy: Build pillar content on "content marketing strategy"
    with 5 supporting cluster articles targeting SMB marketing managers.
    """
    
    test_article = """
    # Content Marketing Strategy Guide
    
    A comprehensive 2,500-word guide covering strategy frameworks,
    implementation tactics, and measurement approaches...
    """
    
    test_technical = """
    Technical SEO: Schema markup added, metadata optimized,
    internal linking strategy defined.
    """
    
    result = validate_business_case(
        strategy=test_strategy,
        article=test_article,
        technical=test_technical,
        business_goals=["Increase organic leads", "Establish thought leadership"]
    )
    
    print("\n=== MARKETING STRATEGY COMPLETE ===")
    print(result[:500] + "...")
