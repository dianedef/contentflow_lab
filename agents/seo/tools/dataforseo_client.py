"""
DataForSEO API v3 Client

Reusable HTTP client for all DataForSEO endpoints.
Uses Basic Auth (login:password base64-encoded).

Docs: https://docs.dataforseo.com/v3/

Usage:
    client = DataForSEOClient()
    results = client.serp_google_organic("content marketing", location_code=2840)
    keywords = client.keyword_overview(["seo tools", "content marketing"])
"""

import os
import json
import logging
from base64 import b64encode
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://api.dataforseo.com/v3"

# Common location codes
LOCATIONS = {
    "us": 2840,
    "uk": 2826,
    "fr": 2250,
    "de": 2276,
    "ca": 2124,
    "au": 2036,
}

# Common language codes
LANGUAGES = {
    "en": "en",
    "fr": "fr",
    "de": "de",
    "es": "es",
}


class DataForSEOError(Exception):
    """Raised when the DataForSEO API returns an error."""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class DataForSEOClient:
    """
    Client for DataForSEO API v3.

    Requires DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD env vars.
    """

    def __init__(
        self,
        login: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
    ):
        self.login = login or os.getenv("DATAFORSEO_LOGIN")
        self.password = password or os.getenv("DATAFORSEO_PASSWORD")

        if not self.login or not self.password:
            raise ValueError(
                "DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD must be set "
                "in environment variables or passed explicitly"
            )

        creds = b64encode(f"{self.login}:{self.password}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
        }
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post(self, endpoint: str, payload: List[Dict]) -> List[Dict]:
        """
        POST to a DataForSEO endpoint and return the results array.

        Args:
            endpoint: API path after /v3/ (e.g. "serp/google/organic/live/advanced")
            payload: List of task dicts (DFS always expects a list)

        Returns:
            List of result dicts from the response

        Raises:
            DataForSEOError on HTTP or API-level errors
        """
        url = f"{BASE_URL}/{endpoint}"

        try:
            resp = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise DataForSEOError(f"HTTP request failed: {e}")

        if resp.status_code != 200:
            raise DataForSEOError(
                f"HTTP {resp.status_code}: {resp.text[:500]}",
                status_code=resp.status_code,
            )

        data = resp.json()

        if data.get("status_code") != 20000:
            raise DataForSEOError(
                f"API error {data.get('status_code')}: {data.get('status_message')}",
                status_code=data.get("status_code"),
                response=data,
            )

        tasks = data.get("tasks", [])
        if not tasks:
            return []

        # Each task has a result array; we typically send 1 task
        results = []
        for task in tasks:
            if task.get("status_code") != 20000:
                logger.warning(
                    "Task error %s: %s",
                    task.get("status_code"),
                    task.get("status_message"),
                )
                continue
            task_results = task.get("result") or []
            results.extend(task_results)

        return results

    @staticmethod
    def _location_code(location: str) -> int:
        """Resolve a location string to a DFS location code."""
        if isinstance(location, int):
            return location
        return LOCATIONS.get(location.lower(), 2840)  # default US

    # ------------------------------------------------------------------
    # SERP
    # ------------------------------------------------------------------

    def serp_google_organic(
        self,
        keyword: str,
        location: str | int = "us",
        language: str = "en",
        depth: int = 10,
    ) -> Dict[str, Any]:
        """
        Live Google organic SERP results.

        Args:
            keyword: Search query
            location: Country code ("us", "fr") or DFS location code (2840)
            language: Language code ("en", "fr")
            depth: Number of results (10, 20, 50, 100)

        Returns:
            Dict with items (organic results), item_types, spell, etc.
        """
        payload = [
            {
                "keyword": keyword,
                "location_code": self._location_code(location),
                "language_code": language,
                "depth": depth,
            }
        ]

        results = self._post("serp/google/organic/live/advanced", payload)
        return results[0] if results else {}

    # ------------------------------------------------------------------
    # DataForSEO Labs — Keyword Research
    # ------------------------------------------------------------------

    def keyword_overview(
        self,
        keywords: List[str],
        location: str | int = "us",
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Get keyword metrics: search volume, CPC, competition, difficulty.

        Args:
            keywords: List of keywords (max 1000)
            location: Country code or DFS location code
            language: Language code

        Returns:
            List of keyword data dicts
        """
        payload = [
            {
                "keywords": keywords[:1000],
                "location_code": self._location_code(location),
                "language_code": language,
            }
        ]

        results = self._post(
            "dataforseo_labs/google/keyword_overview/live", payload
        )
        if not results:
            return []
        return results[0].get("items", [])

    def keyword_ideas(
        self,
        keywords: List[str],
        location: str | int = "us",
        language: str = "en",
        limit: int = 50,
        include_seed: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get keyword ideas based on seed keywords.

        Returns related keywords with volume, difficulty, CPC.
        """
        payload = [
            {
                "keywords": keywords,
                "location_code": self._location_code(location),
                "language_code": language,
                "limit": limit,
                "include_seed_keyword": include_seed,
            }
        ]

        results = self._post(
            "dataforseo_labs/google/keyword_ideas/live", payload
        )
        if not results:
            return []
        return results[0].get("items", [])

    def keyword_suggestions(
        self,
        keyword: str,
        location: str | int = "us",
        language: str = "en",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get keyword suggestions (autocomplete-style) for a seed keyword.
        """
        payload = [
            {
                "keyword": keyword,
                "location_code": self._location_code(location),
                "language_code": language,
                "limit": limit,
            }
        ]

        results = self._post(
            "dataforseo_labs/google/keyword_suggestions/live", payload
        )
        if not results:
            return []
        return results[0].get("items", [])

    # ------------------------------------------------------------------
    # DataForSEO Labs — Competitor Research
    # ------------------------------------------------------------------

    def competitors_domain(
        self,
        target: str,
        location: str | int = "us",
        language: str = "en",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Find competing domains for a target domain.

        Args:
            target: Target domain (e.g. "example.com")
            location: Country code or DFS location code
            language: Language code
            limit: Max results

        Returns:
            List of competitor dicts with avg_position, intersections, etc.
        """
        payload = [
            {
                "target": target,
                "location_code": self._location_code(location),
                "language_code": language,
                "limit": limit,
            }
        ]

        results = self._post(
            "dataforseo_labs/google/competitors_domain/live", payload
        )
        if not results:
            return []
        return results[0].get("items", [])

    def ranked_keywords(
        self,
        target: str,
        location: str | int = "us",
        language: str = "en",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get keywords a domain ranks for, with positions and metrics.

        Args:
            target: Domain to analyze (e.g. "hubspot.com")

        Returns:
            List of keyword ranking dicts
        """
        payload = [
            {
                "target": target,
                "location_code": self._location_code(location),
                "language_code": language,
                "limit": limit,
            }
        ]

        results = self._post(
            "dataforseo_labs/google/ranked_keywords/live", payload
        )
        if not results:
            return []
        return results[0].get("items", [])

    def domain_intersection(
        self,
        targets: Dict[str, str],
        location: str | int = "us",
        language: str = "en",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Find keywords where multiple domains intersect/differ.

        Args:
            targets: Dict like {"1": "domain1.com", "2": "domain2.com"}
                     Up to 20 domains. DFS compares them.
            location: Country code or DFS location code
            language: Language code
            limit: Max results

        Returns:
            List of keyword intersection dicts
        """
        payload = [
            {
                "targets": targets,
                "location_code": self._location_code(location),
                "language_code": language,
                "limit": limit,
            }
        ]

        results = self._post(
            "dataforseo_labs/google/domain_intersection/live", payload
        )
        if not results:
            return []
        return results[0].get("items", [])

    # ------------------------------------------------------------------
    # Google Trends
    # ------------------------------------------------------------------

    def google_trends_explore(
        self,
        keywords: List[str],
        location: str | int = "us",
        language: str = "en",
        time_range: str = "past_12_months",
    ) -> Dict[str, Any]:
        """
        Google Trends data for keywords.

        Args:
            keywords: Up to 5 keywords to compare
            location: Country code or DFS location code
            language: Language code
            time_range: One of "past_hour", "past_4_hours", "past_day",
                       "past_7_days", "past_30_days", "past_90_days",
                       "past_12_months", "past_5_years"

        Returns:
            Trends data with interest over time
        """
        payload = [
            {
                "keywords": keywords[:5],
                "location_code": self._location_code(location),
                "language_code": language,
                "time_range": time_range,
            }
        ]

        results = self._post(
            "keywords_data/google_trends/explore/live", payload
        )
        return results[0] if results else {}

    # ------------------------------------------------------------------
    # Search Intent
    # ------------------------------------------------------------------

    def search_intent(
        self,
        keywords: List[str],
        location: str | int = "us",
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Classify search intent for keywords (informational, commercial,
        navigational, transactional).

        Args:
            keywords: List of keywords (max 1000)

        Returns:
            List of dicts with keyword, intent, probability
        """
        payload = [
            {
                "keywords": keywords[:1000],
                "location_code": self._location_code(location),
                "language_code": language,
            }
        ]

        results = self._post(
            "dataforseo_labs/google/search_intent/live", payload
        )
        if not results:
            return []
        return results[0].get("items", [])

    # ------------------------------------------------------------------
    # Domain Overview
    # ------------------------------------------------------------------

    def domain_rank_overview(
        self,
        target: str,
        location: str | int = "us",
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Get domain rank overview: organic/paid traffic, keywords count, etc.

        Args:
            target: Domain to analyze

        Returns:
            Domain metrics dict
        """
        payload = [
            {
                "target": target,
                "location_code": self._location_code(location),
                "language_code": language,
            }
        ]

        results = self._post(
            "dataforseo_labs/google/domain_rank_overview/live", payload
        )
        if not results:
            return {}
        items = results[0].get("items", [])
        return items[0] if items else {}
