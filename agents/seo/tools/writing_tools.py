"""
Writing Tools for Copywriter Agent
Real keyword analysis with DataForSEO integration.
"""
from typing import Dict, List, Any, Optional
import re


class KeywordIntegrator:
    """Analyze keyword usage in content and fetch real SEO data from DataForSEO."""

    def integrate_keywords(
        self,
        content: str,
        primary_keyword: str,
        secondary_keywords: Optional[List[str]] = None,
        target_density: float = 1.5
    ) -> Dict[str, Any]:
        """
        Analyze keyword density, positions, and fetch real search volume/difficulty.

        Args:
            content: Content text to analyze
            primary_keyword: Primary target keyword
            secondary_keywords: Secondary keywords list
            target_density: Target keyword density (percentage)

        Returns:
            Analysis with density metrics, position checks, and DataForSEO data
        """
        word_count = len(content.split())

        # Count primary keyword occurrences
        primary_count = len(re.findall(
            r'\b' + re.escape(primary_keyword.lower()) + r'\b',
            content.lower()
        ))
        primary_density = (primary_count / word_count * 100) if word_count > 0 else 0

        # Analyze secondary keywords
        secondary_analysis = []
        if secondary_keywords:
            for kw in secondary_keywords:
                count = len(re.findall(
                    r'\b' + re.escape(kw.lower()) + r'\b',
                    content.lower()
                ))
                secondary_analysis.append({
                    "keyword": kw,
                    "count": count,
                    "density": (count / word_count * 100) if word_count > 0 else 0
                })

        keyword_positions = self._detect_keyword_positions(content, primary_keyword)

        result = {
            "word_count": word_count,
            "primary_keyword": primary_keyword,
            "primary_keyword_count": primary_count,
            "primary_keyword_density": round(primary_density, 2),
            "target_density": target_density,
            "density_status": self._evaluate_density(primary_density, target_density),
            "keyword_positions": keyword_positions,
            "secondary_keywords": secondary_analysis,
            "recommendations": self._generate_keyword_recommendations(
                primary_density,
                target_density,
                keyword_positions,
                secondary_analysis
            ),
        }

        # Enrich with real DataForSEO data (graceful fallback if unavailable)
        keyword_data = self._get_keyword_data(primary_keyword)
        if keyword_data:
            result.update(keyword_data)

        return result

    def _get_keyword_data(self, keyword: str) -> Dict[str, Any]:
        """Fetch real search volume and related keywords from DataForSEO."""
        try:
            from agents.seo.tools.dataforseo_client import DataForSEOClient
            client = DataForSEOClient()
            results = client.keyword_overview([keyword])
            if results:
                item = results[0]
                return {
                    "search_volume": item.get("search_volume"),
                    "keyword_difficulty": item.get("keyword_difficulty"),
                    "related_keywords": [
                        k["keyword"] for k in item.get("related_keywords", [])[:5]
                    ]
                }
        except Exception:
            pass
        return {}

    def _detect_keyword_positions(self, content: str, keyword: str) -> Dict[str, bool]:
        """Detect where keyword appears in content."""
        content_lower = content.lower()
        keyword_lower = keyword.lower()

        first_100_words = ' '.join(content.split()[:100])
        last_100_words = ' '.join(content.split()[-100:])

        return {
            "in_first_100_words": keyword_lower in first_100_words.lower(),
            "in_last_100_words": keyword_lower in last_100_words.lower(),
            "in_headings": bool(re.search(r'#+.*' + re.escape(keyword_lower), content_lower)),
            "well_distributed": True
        }

    def _evaluate_density(self, actual: float, target: float) -> str:
        """Evaluate if keyword density is appropriate."""
        if actual < target * 0.5:
            return "too_low"
        elif actual > target * 1.5:
            return "too_high"
        else:
            return "optimal"

    def _generate_keyword_recommendations(
        self,
        density: float,
        target: float,
        positions: Dict[str, bool],
        secondary: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate keyword integration recommendations."""
        recommendations = []

        if density < target * 0.5:
            recommendations.append(f"Increase primary keyword usage — current density {density:.1f}% is below target {target}%")
        elif density > target * 1.5:
            recommendations.append(f"Reduce primary keyword usage — {density:.1f}% density may appear over-optimized")
        else:
            recommendations.append(f"Keyword density is optimal at {density:.1f}%")

        if not positions["in_first_100_words"]:
            recommendations.append("Add primary keyword in first 100 words")

        if not positions["in_headings"]:
            recommendations.append("Include primary keyword in at least one H2 or H3 heading")

        if not positions["in_last_100_words"]:
            recommendations.append("Mention primary keyword in conclusion")

        if secondary:
            low_usage = [s for s in secondary if s["count"] < 2]
            if low_usage:
                recommendations.append(
                    f"Consider using secondary keywords more: {', '.join([s['keyword'] for s in low_usage[:3]])}"
                )

        recommendations.append("Use semantic variations and related terms naturally")
        recommendations.append("Prioritize natural language over keyword frequency")

        return recommendations
