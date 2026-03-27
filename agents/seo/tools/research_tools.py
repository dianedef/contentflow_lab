"""
Tools for Research Analyst agent.
Handles SERP analysis, trend monitoring, keyword gaps, and ranking patterns.

Powered by DataForSEO API v3.
"""
import os
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from crewai.tools import tool
from dotenv import load_dotenv

from agents.seo.tools.dataforseo_provider import (
    DFSSERPAnalyzer,
    DFSTrendMonitor,
    DFSKeywordGapFinder,
    DFSRankingPatternExtractor,
)

load_dotenv()

# Re-export provider classes under original names for backward compat
SERPAnalyzer = DFSSERPAnalyzer
TrendMonitor = DFSTrendMonitor
KeywordGapFinder = DFSKeywordGapFinder
RankingPatternExtractor = DFSRankingPatternExtractor


class ConsensusResearcher:
    """Scientific literature review and consensus analysis tools."""

    def __init__(self):
        self.api_key = os.getenv("CONSENSUS_API_KEY")
        self.base_url = "https://api.consensus.app/v1"

    def deep_search(self, query: str) -> Dict[str, Any]:
        """
        Perform a deep search for scientific consensus on a query.

        Args:
            query: Research question or topic to investigate

        Returns:
            Structured summary of literature review and consensus
        """
        if not self.api_key:
            return {"error": "CONSENSUS_API_KEY not found in environment variables"}

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {"query": query, "limit": 10}

            response = requests.post(
                f"{self.base_url}/reports/literature-review",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code != 200:
                return {
                    "error": f"Consensus API returned status {response.status_code}",
                    "details": response.text,
                }

            data = response.json()

            return {
                "query": query,
                "summary": data.get("summary", "No summary available"),
                "consensus_meter": data.get("consensus_meter"),
                "key_findings": data.get("key_findings", []),
                "sources": [
                    {
                        "title": s.get("title"),
                        "authors": s.get("authors"),
                        "year": s.get("year"),
                        "journal": s.get("journal"),
                        "url": s.get("url"),
                    }
                    for s in data.get("papers", [])
                ],
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "error": f"Consensus deep search failed: {str(e)}",
                "query": query,
            }


# ------------------------------------------------------------------
# Singleton instances for CrewAI tool wrappers
# ------------------------------------------------------------------
_serp_analyzer = None
_trend_monitor = None
_gap_finder = None
_pattern_extractor = None
_consensus_researcher = None


def get_serp_analyzer():
    global _serp_analyzer
    if _serp_analyzer is None:
        _serp_analyzer = DFSSERPAnalyzer()
    return _serp_analyzer


def get_trend_monitor():
    global _trend_monitor
    if _trend_monitor is None:
        _trend_monitor = DFSTrendMonitor()
    return _trend_monitor


def get_gap_finder():
    global _gap_finder
    if _gap_finder is None:
        _gap_finder = DFSKeywordGapFinder()
    return _gap_finder


def get_pattern_extractor():
    global _pattern_extractor
    if _pattern_extractor is None:
        _pattern_extractor = DFSRankingPatternExtractor()
    return _pattern_extractor


def get_consensus_researcher():
    global _consensus_researcher
    if _consensus_researcher is None:
        _consensus_researcher = ConsensusResearcher()
    return _consensus_researcher


# ------------------------------------------------------------------
# CrewAI @tool wrappers
# ------------------------------------------------------------------


@tool("Analyze SERP results")
def analyze_serp_tool(keyword: str, location: str = "us") -> str:
    """
    Analyze SERP results for a keyword to understand competitive landscape.

    Args:
        keyword: Target keyword to analyze
        location: Country code (us, fr, uk, de) or DFS location code

    Returns:
        JSON string with SERP analysis including top competitors, search intent, and competitive metrics
    """
    import json

    analyzer = get_serp_analyzer()
    result = analyzer.analyze_serp(keyword, location)
    return json.dumps(result, indent=2)


@tool("Monitor sector trends")
def monitor_trends_tool(sector: str, keywords: str, time_period: str = "12m") -> str:
    """
    Monitor trends for a sector and identify emerging opportunities.

    Args:
        sector: Industry or topic sector to analyze
        keywords: Comma-separated list of keywords to monitor
        time_period: Time period for analysis (e.g., "12m", "6m", "3m")

    Returns:
        JSON string with trend report including emerging/declining trends and recommendations
    """
    import json

    monitor = get_trend_monitor()
    keyword_list = [k.strip() for k in keywords.split(",")]
    result = monitor.monitor_trends(sector, keyword_list, time_period)
    return json.dumps(result, indent=2)


@tool("Identify keyword gaps")
def identify_keyword_gaps_tool(
    competitor_domains: str,
    seed_keywords: str,
    target_domain: str = None,
) -> str:
    """
    Identify keyword gaps by comparing your site with competitors.

    Args:
        competitor_domains: Comma-separated list of competitor domains
        seed_keywords: Comma-separated list of starting keywords
        target_domain: Your domain (optional)

    Returns:
        JSON string with keyword gap analysis and opportunities ranked by priority
    """
    import json

    finder = get_gap_finder()
    domains = [d.strip() for d in competitor_domains.split(",")]
    keywords = [k.strip() for k in seed_keywords.split(",")]
    result = finder.identify_keyword_gaps(target_domain, domains, keywords)
    return json.dumps(result, indent=2)


@tool("Extract ranking patterns")
def extract_ranking_patterns_tool(keyword: str) -> str:
    """
    Extract ranking patterns and success factors from top-performing content.

    Args:
        keyword: Keyword to analyze top-ranking content for

    Returns:
        JSON string with ranking patterns including content structure, length, and key factors
    """
    import json

    extractor = get_pattern_extractor()
    result = extractor.extract_ranking_patterns(keyword)
    return json.dumps(result, indent=2)


@tool("Consensus deep search")
def consensus_deep_search_tool(query: str) -> str:
    """
    Perform a deep search for scientific consensus on a query using Consensus AI.

    Args:
        query: Research question or topic to investigate

    Returns:
        JSON string with structured summary of literature review, including key findings and consensus meter
    """
    import json

    researcher = get_consensus_researcher()
    result = researcher.deep_search(query)
    return json.dumps(result, indent=2)
