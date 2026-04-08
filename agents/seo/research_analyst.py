"""
Research Analyst Agent - Competitive Intelligence & SEO Opportunity Identification
Part of the SEO multi-agent system (Agent 1/6)

Responsibilities:
- SERP analysis and competitive positioning
- Sector trend monitoring and seasonality
- Content gap identification and keyword opportunities
- Ranking pattern extraction and success factors
"""
from typing import List, Optional, Dict, Any
from crewai import Agent, Task, Crew
from dotenv import load_dotenv
import os

from agents.seo.tools.research_tools import (
    SERPAnalyzer,
    TrendMonitor,
    KeywordGapFinder,
    RankingPatternExtractor,
    ConsensusResearcher,
    analyze_serp_tool,
    monitor_trends_tool,
    identify_keyword_gaps_tool,
    extract_ranking_patterns_tool,
    consensus_deep_search_tool
)
from agents.seo.config.research_config import AI_TOOL_SETTINGS
from agents.shared.tools.exa_tools import exa_search, exa_find_similar
from agents.shared.tools.firecrawl_tools import scrape_url, crawl_site

load_dotenv()


class ResearchAnalystAgent:
    """
    Research Analyst Agent for competitive intelligence and SEO analysis.
    First agent in the SEO content generation pipeline.
    """
    
    def __init__(self, llm_model: str = "groq/mixtral-8x7b-32768", use_consensus_ai: Optional[bool] = None):
        """
        Initialize Research Analyst with research tools.

        Args:
            llm_model: LiteLLM model string (default: groq/mixtral-8x7b-32768)
            use_consensus_ai: Whether to use Consensus AI tool (default: from config)
        """
        self.llm_model = llm_model
        self.use_consensus_ai = use_consensus_ai if use_consensus_ai is not None else AI_TOOL_SETTINGS.get("use_consensus_ai", False)

        # Initialize tools
        self.serp_analyzer = SERPAnalyzer()
        self.trend_monitor = TrendMonitor()
        self.gap_finder = KeywordGapFinder()
        self.pattern_extractor = RankingPatternExtractor()
        self.consensus_researcher = ConsensusResearcher()

        # Create agent
        self.agent = self._create_agent()
    
    def _create_agent(self) -> Agent:
        """Create the Research Analyst CrewAI agent with tools."""
        tools = [
            analyze_serp_tool,
            monitor_trends_tool,
            identify_keyword_gaps_tool,
            extract_ranking_patterns_tool,
            exa_search,
            exa_find_similar,
            scrape_url,
            crawl_site,
        ]

        if self.use_consensus_ai:
            tools.append(consensus_deep_search_tool)
            
        return Agent(
            role="SEO Research Analyst",
            goal=(
                "Conduct comprehensive competitive intelligence and identify SEO opportunities. "
                "Analyze SERP landscapes, monitor industry trends, discover content gaps, "
                "extract winning patterns from top-ranking content, and investigate scientific "
                "consensus for relevant academic or medical topics."
            ),
            backstory=(
                "You are an expert SEO analyst with 10+ years of experience in competitive intelligence. "
                "You specialize in SERP analysis, keyword research, and identifying content opportunities "
                "that drive organic traffic. Your analytical approach combines data-driven insights with "
                "strategic thinking to uncover high-value SEO opportunities. You have a deep understanding "
                "of search intent, ranking factors, and content strategies. Additionally, you are skilled "
                "at synthesizing scientific literature and academic consensus to ensure content accuracy "
                "and authority, especially for YMYL (Your Money Your Life) topics."
            ),
            tools=tools,
            llm=self.llm_model,  # CrewAI uses LiteLLM internally
            verbose=True,
            allow_delegation=False
        )
    
    def create_analysis_task(
        self,
        target_keyword: str,
        competitor_domains: Optional[List[str]] = None,
        sector: Optional[str] = None,
        target_domain: Optional[str] = None
    ) -> Task:
        """
        Create a comprehensive SEO analysis task.
        
        Args:
            target_keyword: Primary keyword to analyze
            competitor_domains: List of competitor domains (optional)
            sector: Industry sector for trend analysis (optional)
            target_domain: Your domain for gap analysis (optional)
            
        Returns:
            CrewAI Task configured for research analysis
        """
        description = f"""
        Conduct a comprehensive SEO competitive analysis for the keyword: "{target_keyword}"
        
        Your analysis must include:
        
        1. SERP ANALYSIS:
           - Analyze search results for "{target_keyword}"
           - Identify top 10 competitors and their positioning
           - Determine search intent (Informational, Commercial, Transactional, Navigational)
           - Evaluate competitive difficulty
           - Note any featured snippets or SERP features
        
        2. SCIENTIFIC CONSENSUS (If Applicable):
           - If the topic is scientific, medical, or academic, use the Consensus Deep Search tool.
           - Identify the current scientific consensus and key findings from peer-reviewed literature.
           - This is critical for YMYL topics to ensure E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness).
        
        3. RANKING PATTERNS:
           - Extract success patterns from top-ranking content
           - Analyze content length, structure, and topics covered
           - Identify key ranking factors
           - Determine success probability for new content
        """
        
        if competitor_domains:
            description += f"""
        3. KEYWORD GAP ANALYSIS:
           - Compare against competitors: {', '.join(competitor_domains)}
           - Identify keyword opportunities where competitors rank but target domain doesn't
           - Prioritize gaps by opportunity score
           - Suggest content types for each gap
        """
        
        if sector:
            description += f"""
        4. TREND MONITORING:
           - Monitor trends in {sector} sector
           - Identify emerging keywords and topics
           - Detect seasonal patterns
           - Provide strategic recommendations
        """
        
        description += """
        
        DELIVERABLE FORMAT:
        Provide a structured markdown report with:
        - Executive Summary (2-3 sentences)
        - SERP Analysis findings
        - Scientific Consensus & Evidence (if applicable)
        - Ranking Patterns and success factors
        - Keyword Gap opportunities (if applicable)
        - Trend insights (if applicable)
        - Strategic Recommendations (prioritized list)
        
        Use data-driven insights and be specific with metrics.
        """
        
        return Task(
            description=description,
            agent=self.agent,
            expected_output=(
                "A comprehensive SEO competitive analysis report in markdown format with "
                "SERP insights, ranking patterns, keyword opportunities, and actionable recommendations."
            )
        )
    
    def run_analysis(
        self,
        target_keyword: str,
        competitor_domains: Optional[List[str]] = None,
        sector: Optional[str] = None,
        target_domain: Optional[str] = None
    ) -> str:
        """
        Execute a complete competitive analysis.
        
        Args:
            target_keyword: Primary keyword to analyze
            competitor_domains: List of competitor domains (optional)
            sector: Industry sector for trend analysis (optional)
            target_domain: Your domain for gap analysis (optional)
            
        Returns:
            Markdown report with analysis results
        """
        task = self.create_analysis_task(
            target_keyword=target_keyword,
            competitor_domains=competitor_domains,
            sector=sector,
            target_domain=target_domain
        )
        
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=True
        )
        
        result = crew.kickoff()
        return result


# Convenience function for direct usage
def analyze_keyword(
    keyword: str,
    competitors: Optional[List[str]] = None,
    sector: Optional[str] = None,
    your_domain: Optional[str] = None
) -> str:
    """
    Quick function to analyze a keyword with Research Analyst.
    
    Args:
        keyword: Target keyword to analyze
        competitors: Competitor domains (optional)
        sector: Industry sector (optional)
        your_domain: Your domain (optional)
        
    Returns:
        Analysis report in markdown
    """
    analyst = ResearchAnalystAgent()
    return analyst.run_analysis(
        target_keyword=keyword,
        competitor_domains=competitors,
        sector=sector,
        target_domain=your_domain
    )


if __name__ == "__main__":
    # Example usage
    print("=== Research Analyst Agent - Test Run ===\n")
    
    result = analyze_keyword(
        keyword="content marketing strategy",
        competitors=["hubspot.com", "contentmarketinginstitute.com", "semrush.com"],
        sector="Digital Marketing"
    )
    
    print("\n=== ANALYSIS COMPLETE ===")
    print(result)
