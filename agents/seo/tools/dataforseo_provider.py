"""
DataForSEO Provider — SEO research tools powered by DataForSEO API v3.

Classes: DFSSERPAnalyzer, DFSTrendMonitor, DFSKeywordGapFinder,
DFSRankingPatternExtractor.

Requires DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD in env.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from agents.seo.tools.dataforseo_client import DataForSEOClient, DataForSEOError

logger = logging.getLogger(__name__)


class DFSSERPAnalyzer:
    """SERP analysis via DataForSEO — same interface as SERPAnalyzer."""

    def __init__(self, location: str = "us", language: str = "en"):
        self.client = DataForSEOClient()
        self.location = location
        self.language = language

    def analyze_serp(
        self, keyword: str, location: str = "us"
    ) -> Dict[str, Any]:
        try:
            loc = location if location != "United States" else "us"
            serp = self.client.serp_google_organic(
                keyword, location=loc, language=self.language, depth=10
            )

            if not serp:
                return {"error": "No SERP data returned", "keyword": keyword}

            # Extract organic items
            items = [
                item
                for item in serp.get("items", [])
                if item.get("type") == "organic"
            ]

            # Build competitor list (same shape as SerpApi version)
            competitors = []
            domains = set()
            word_counts = []

            for idx, item in enumerate(items[:10], 1):
                domain = item.get("domain", "")
                if not domain:
                    url = item.get("url", "")
                    domain = urlparse(url).netloc if url else ""

                competitor = {
                    "position": item.get("rank_absolute", idx),
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("description", ""),
                    "domain": domain,
                    "etv": item.get("etv"),  # estimated traffic volume (DFS bonus)
                }
                competitors.append(competitor)
                if domain:
                    domains.add(domain)

                # Word count from snippet
                snippet = item.get("description", "")
                if snippet:
                    word_counts.append(len(snippet.split()) * 10)

            # Search intent — use DFS Labs if available, else heuristic
            intent = self._detect_intent_from_serp(keyword, serp)

            # Featured snippet
            featured_snippet = None
            for item in serp.get("items", []):
                if item.get("type") == "featured_snippet":
                    featured_snippet = {
                        "type": item.get("featured_title", "unknown"),
                        "snippet": item.get("description", ""),
                        "source": item.get("url", ""),
                    }
                    break

            # Related searches
            related_searches = []
            for item in serp.get("items", []):
                if item.get("type") == "related_searches":
                    for rs in item.get("items", []):
                        related_searches.append(rs.get("title", ""))

            # People also ask
            people_also_ask = []
            for item in serp.get("items", []):
                if item.get("type") == "people_also_ask":
                    for paa in item.get("items", []):
                        people_also_ask.append(paa.get("title", ""))

            import statistics as stats

            avg_word_count = (
                int(stats.mean(word_counts)) if word_counts else None
            )

            competitive_score = min(
                10.0, len(domains) + (len(items) / 2)
            )

            all_text = " ".join(
                f"{c['title']} {c['snippet']}" for c in competitors
            )
            common_topics = self._extract_common_topics(all_text)

            return {
                "keyword": keyword,
                "search_intent": intent,
                "total_results": serp.get("se_results_count", 0),
                "top_competitors": competitors,
                "featured_snippet": featured_snippet,
                "related_searches": related_searches[:8],
                "people_also_ask": people_also_ask[:5],
                "average_word_count": avg_word_count,
                "common_topics": common_topics,
                "competitive_score": round(competitive_score, 1),
                "item_types": serp.get("item_types", []),
                "analysis_timestamp": datetime.now().isoformat(),
                "provider": "dataforseo",
            }

        except DataForSEOError as e:
            return {"error": f"DFS SERP analysis failed: {e}", "keyword": keyword}
        except Exception as e:
            return {"error": f"SERP analysis failed: {e}", "keyword": keyword}

    def _detect_intent_from_serp(
        self, keyword: str, serp: Dict[str, Any]
    ) -> str:
        """Detect search intent from keyword + SERP features."""
        kw = keyword.lower()

        transactional = ["buy", "price", "purchase", "order", "shop", "deal", "discount"]
        if any(t in kw for t in transactional):
            return "Transactional"

        commercial = ["best", "top", "review", "compare", "vs", "alternative"]
        if any(c in kw for c in commercial):
            return "Commercial"

        informational = ["how", "what", "why", "when", "guide", "tutorial", "learn"]
        if any(i in kw for i in informational):
            return "Informational"

        # Check SERP features
        item_types = serp.get("item_types", [])
        if "featured_snippet" in item_types or "people_also_ask" in item_types:
            return "Informational"
        if "shopping" in item_types or "paid" in item_types:
            return "Commercial"
        if "knowledge_graph" in item_types:
            return "Navigational"

        return "Informational"

    @staticmethod
    def _extract_common_topics(text: str, top_n: int = 5) -> List[str]:
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "is", "are", "was", "were",
            "this", "that", "your", "from", "how", "what", "can", "will",
        }
        words = text.lower().split()
        freq: Dict[str, int] = {}
        for w in words:
            w = "".join(c for c in w if c.isalnum())
            if len(w) > 3 and w not in stop_words:
                freq[w] = freq.get(w, 0) + 1
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:top_n]]


class DFSTrendMonitor:
    """Trend monitoring via DataForSEO Google Trends — same interface as TrendMonitor."""

    def __init__(self, location: str = "us", language: str = "en"):
        self.client = DataForSEOClient()
        self.location = location
        self.language = language

    def monitor_trends(
        self,
        sector: str,
        keywords: List[str],
        time_period: str = "12m",
    ) -> Dict[str, Any]:
        try:
            # Map time_period to DFS format
            period_map = {
                "1m": "past_30_days",
                "3m": "past_90_days",
                "6m": "past_12_months",  # DFS has no 6m, use 12m
                "12m": "past_12_months",
                "5y": "past_5_years",
            }
            dfs_period = period_map.get(time_period, "past_12_months")

            # Get keyword metrics for volume data
            kw_data = self.client.keyword_overview(
                keywords[:10], location=self.location, language=self.language
            )

            # Build volume lookup
            volume_map = {}
            for item in kw_data:
                kw_info = item.get("keyword_data", {}).get("keyword_info", {})
                volume_map[item.get("keyword_data", {}).get("keyword", "")] = {
                    "search_volume": kw_info.get("search_volume", 0),
                    "cpc": kw_info.get("cpc"),
                    "competition": kw_info.get("competition"),
                    "monthly_searches": kw_info.get("monthly_searches", []),
                }

            # Get trends data (batches of 5 — DFS limit)
            trends_data = {}
            for i in range(0, len(keywords[:10]), 5):
                batch = keywords[i : i + 5]
                try:
                    result = self.client.google_trends_explore(
                        batch,
                        location=self.location,
                        language=self.language,
                        time_range=dfs_period,
                    )
                    for line in result.get("lines", []):
                        kw = line.get("keyword", "")
                        values = line.get("values", [])
                        if values:
                            first_val = values[0].get("value", 50)
                            last_val = values[-1].get("value", 50)
                            growth = (
                                ((last_val - first_val) / first_val * 100)
                                if first_val > 0
                                else 0
                            )
                            trends_data[kw] = {
                                "trend_score": last_val,
                                "growth_rate": round(growth, 1),
                                "values": values,
                            }
                except DataForSEOError as e:
                    logger.warning("Trends batch failed: %s", e)

            # Classify emerging vs declining
            emerging = []
            declining = []

            for kw in keywords[:10]:
                vol_info = volume_map.get(kw, {})
                trend_info = trends_data.get(kw, {})

                entry = {
                    "keyword": kw,
                    "trend_score": trend_info.get("trend_score", 0),
                    "search_volume": vol_info.get("search_volume", 0),
                    "cpc": vol_info.get("cpc"),
                    "competition": vol_info.get("competition"),
                    "growth_rate": trend_info.get("growth_rate", 0),
                    "monthly_searches": vol_info.get("monthly_searches", []),
                }

                if entry["growth_rate"] > 0:
                    emerging.append(entry)
                else:
                    declining.append(entry)

            emerging.sort(key=lambda x: x["growth_rate"], reverse=True)
            declining.sort(key=lambda x: x["growth_rate"])

            recommendations = []
            if emerging:
                top_kw = emerging[0]["keyword"]
                recommendations.append(
                    f"Prioritize '{top_kw}' — highest growth at {emerging[0]['growth_rate']}%"
                )
            if declining:
                recommendations.append(
                    f"Deprioritize {len(declining)} declining keywords"
                )
            recommendations.append(
                f"Monitor {sector} sector — {len(emerging)} keywords trending up"
            )

            return {
                "sector": sector,
                "analysis_period": time_period,
                "emerging_trends": emerging,
                "declining_trends": declining,
                "recommendations": recommendations,
                "confidence_score": 0.9 if trends_data else 0.5,
                "generated_at": datetime.now().isoformat(),
                "provider": "dataforseo",
            }

        except DataForSEOError as e:
            return {"error": f"DFS trend monitoring failed: {e}", "sector": sector}
        except Exception as e:
            return {"error": f"Trend monitoring failed: {e}", "sector": sector}


class DFSKeywordGapFinder:
    """Keyword gap analysis via DataForSEO domain_intersection."""

    def __init__(self, location: str = "us", language: str = "en"):
        self.client = DataForSEOClient()
        self.location = location
        self.language = language

    def identify_keyword_gaps(
        self,
        target_domain: Optional[str],
        competitor_domains: List[str],
        seed_keywords: List[str],
    ) -> Dict[str, Any]:
        try:
            gaps = []

            # Strategy 1: Domain intersection (best for gap analysis)
            if target_domain and competitor_domains:
                targets = {"1": target_domain}
                for i, comp in enumerate(competitor_domains[:19], 2):
                    targets[str(i)] = comp

                try:
                    intersection = self.client.domain_intersection(
                        targets=targets,
                        location=self.location,
                        language=self.language,
                        limit=100,
                    )

                    for item in intersection:
                        kw_data = item.get("keyword_data", {})
                        kw_info = kw_data.get("keyword_info", {})
                        kw = kw_data.get("keyword", "")

                        # Check: competitor ranks, target doesn't
                        intersections = item.get("intersection_result", {})
                        target_pos = intersections.get("1", {})
                        target_ranks = target_pos.get("rank_absolute") if target_pos else None

                        if target_ranks is None or target_ranks > 100:
                            volume = kw_info.get("search_volume", 0)
                            difficulty = kw_info.get("keyword_difficulty", 50)
                            cpc = kw_info.get("cpc", 0)

                            # Opportunity = high volume + low difficulty
                            opportunity = (
                                (volume / 1000) * (100 - difficulty) / 100
                                if volume
                                else 0
                            )

                            ranking_comps = []
                            for key, val in intersections.items():
                                if key != "1" and val:
                                    idx = int(key) - 2
                                    if 0 <= idx < len(competitor_domains):
                                        ranking_comps.append(competitor_domains[idx])

                            gaps.append({
                                "keyword": kw,
                                "search_volume": volume,
                                "difficulty": difficulty,
                                "cpc": cpc,
                                "opportunity_score": round(opportunity, 2),
                                "competitors_ranking": ranking_comps,
                                "search_intent": kw_info.get("search_intent"),
                                "content_type_suggested": self._suggest_content_type(
                                    kw_info.get("search_intent")
                                ),
                            })
                except DataForSEOError as e:
                    logger.warning("Domain intersection failed: %s", e)

            # Strategy 2: Enrich with keyword data from seeds
            if seed_keywords and not gaps:
                kw_data = self.client.keyword_overview(
                    seed_keywords[:20],
                    location=self.location,
                    language=self.language,
                )
                for item in kw_data:
                    kd = item.get("keyword_data", {})
                    ki = kd.get("keyword_info", {})
                    kw = kd.get("keyword", "")
                    volume = ki.get("search_volume", 0)
                    difficulty = ki.get("keyword_difficulty", 50)

                    opportunity = (
                        (volume / 1000) * (100 - difficulty) / 100
                        if volume
                        else 0
                    )

                    gaps.append({
                        "keyword": kw,
                        "search_volume": volume,
                        "difficulty": difficulty,
                        "cpc": ki.get("cpc", 0),
                        "opportunity_score": round(opportunity, 2),
                        "competitors_ranking": [],
                        "search_intent": ki.get("search_intent"),
                        "content_type_suggested": self._suggest_content_type(
                            ki.get("search_intent")
                        ),
                    })

            gaps.sort(key=lambda x: x["opportunity_score"], reverse=True)
            total_opp = sum(g["opportunity_score"] for g in gaps)
            priority_kws = [g["keyword"] for g in gaps[:10]]

            return {
                "target_domain": target_domain,
                "competitor_domains": competitor_domains,
                "gaps_identified": gaps,
                "total_opportunity_value": round(total_opp, 2),
                "priority_keywords": priority_kws,
                "analysis_date": datetime.now().isoformat(),
                "provider": "dataforseo",
            }

        except DataForSEOError as e:
            return {
                "error": f"DFS keyword gap analysis failed: {e}",
                "target_domain": target_domain,
            }
        except Exception as e:
            return {
                "error": f"Keyword gap analysis failed: {e}",
                "target_domain": target_domain,
            }

    @staticmethod
    def _suggest_content_type(intent: Optional[str]) -> str:
        if not intent:
            return "blog"
        content_map = {
            "informational": "guide",
            "commercial": "comparison",
            "transactional": "review",
            "navigational": "tool",
        }
        return content_map.get(intent.lower() if intent else "", "blog")


class DFSRankingPatternExtractor:
    """Ranking pattern extraction via DataForSEO — same interface as RankingPatternExtractor."""

    def __init__(self, location: str = "us", language: str = "en"):
        self.serp_analyzer = DFSSERPAnalyzer(location, language)
        self.client = DataForSEOClient()
        self.location = location
        self.language = language

    def extract_ranking_patterns(self, keyword: str) -> Dict[str, Any]:
        try:
            serp_data = self.serp_analyzer.analyze_serp(keyword, self.location)

            if "error" in serp_data:
                return serp_data

            # Get keyword metrics for difficulty + volume
            kw_metrics = {}
            try:
                overview = self.client.keyword_overview(
                    [keyword],
                    location=self.location,
                    language=self.language,
                )
                if overview:
                    kw_metrics = (
                        overview[0]
                        .get("keyword_data", {})
                        .get("keyword_info", {})
                    )
            except DataForSEOError:
                pass

            avg_words = serp_data.get("average_word_count") or 1500
            content_length_pattern = {
                "min": int(avg_words * 0.7),
                "max": int(avg_words * 1.3),
                "avg": avg_words,
                "recommended": int(avg_words * 1.1),
            }

            titles = [c["title"] for c in serp_data.get("top_competitors", [])]
            structure_patterns = self._analyze_title_patterns(titles)

            difficulty = kw_metrics.get("keyword_difficulty", 50)
            volume = kw_metrics.get("search_volume", 0)

            ranking_factors = [
                {
                    "factor_name": "Content Comprehensiveness",
                    "importance_score": 9.0,
                    "observation": f"Top rankers average {avg_words} words",
                    "actionable_insight": f"Target {content_length_pattern['recommended']} words minimum",
                },
                {
                    "factor_name": "Search Intent Alignment",
                    "importance_score": 10.0,
                    "observation": f"Search intent is {serp_data.get('search_intent')}",
                    "actionable_insight": f"Structure content for {serp_data.get('search_intent')} intent",
                },
                {
                    "factor_name": "Topic Coverage",
                    "importance_score": 8.5,
                    "observation": f"Common topics: {', '.join(serp_data.get('common_topics', [])[:3])}",
                    "actionable_insight": "Include these topics in your content",
                },
                {
                    "factor_name": "Keyword Difficulty",
                    "importance_score": 8.0,
                    "observation": f"Difficulty: {difficulty}/100, Volume: {volume}/mo",
                    "actionable_insight": (
                        "Low competition — good opportunity"
                        if difficulty < 40
                        else "Moderate competition — strong content needed"
                        if difficulty < 70
                        else "High competition — authority + backlinks required"
                    ),
                },
            ]

            if serp_data.get("featured_snippet"):
                ranking_factors.append({
                    "factor_name": "Featured Snippet Optimization",
                    "importance_score": 8.0,
                    "observation": "Featured snippet present in SERP",
                    "actionable_insight": "Structure content with clear definitions and lists",
                })

            if serp_data.get("people_also_ask"):
                ranking_factors.append({
                    "factor_name": "People Also Ask Coverage",
                    "importance_score": 7.5,
                    "observation": f"PAA questions: {', '.join(serp_data['people_also_ask'][:3])}",
                    "actionable_insight": "Answer these questions in your content with H2/H3 sections",
                })

            # Success probability based on real difficulty
            success_probability = round(max(0.05, (100 - difficulty) / 100), 2)

            return {
                "keyword_analyzed": keyword,
                "search_volume": volume,
                "keyword_difficulty": difficulty,
                "cpc": kw_metrics.get("cpc"),
                "content_length_pattern": content_length_pattern,
                "structure_patterns": structure_patterns,
                "ranking_factors": ranking_factors,
                "content_freshness": "Monthly updates recommended",
                "schema_markup_usage": ["Article", "FAQPage"],
                "success_probability": success_probability,
                "serp_features": serp_data.get("item_types", []),
                "extracted_at": datetime.now().isoformat(),
                "provider": "dataforseo",
            }

        except Exception as e:
            return {"error": f"Pattern extraction failed: {e}", "keyword": keyword}

    @staticmethod
    def _analyze_title_patterns(titles: List[str]) -> List[str]:
        patterns = []
        if any("how to" in t.lower() for t in titles):
            patterns.append("How-to format common")
        if any(any(c.isdigit() for c in t) for t in titles):
            patterns.append("Numbered lists/statistics present")
        if any("best" in t.lower() or "top" in t.lower() for t in titles):
            patterns.append("Superlative rankings common")
        if any("guide" in t.lower() for t in titles):
            patterns.append("Comprehensive guides favored")
        if not patterns:
            patterns.append("Standard informational titles")
        return patterns
