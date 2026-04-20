"""
Google Search Console Client — Submit URLs for indexing and check indexation status.

Uses the Google Indexing API (for URL submission) and
Search Console API (for indexation status checks).

Requires a Google Service Account with:
- Indexing API enabled
- Search Console API enabled
- Service account added as owner in GSC property

Environment:
    GSC_SERVICE_ACCOUNT_JSON: path to service account JSON file
    GSC_SERVICE_ACCOUNT_DATA: JSON string of service account credentials (alternative)
    GOOGLE_CREDENTIALS_FILE: legacy alias for GSC_SERVICE_ACCOUNT_JSON
    GOOGLE_CREDENTIALS_JSON: legacy alias for GSC_SERVICE_ACCOUNT_DATA
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False


INDEXING_SCOPES = ["https://www.googleapis.com/auth/indexing"]
WEBMASTERS_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def _get_credentials(scopes: List[str]):
    """Load Google Service Account credentials."""
    if not HAS_GOOGLE:
        raise RuntimeError(
            "google-auth and google-api-python-client are required. "
            "Install with: pip install google-auth google-api-python-client"
        )

    # Try JSON file path first
    json_path = os.getenv("GSC_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_CREDENTIALS_FILE")
    if json_path:
        return service_account.Credentials.from_service_account_file(json_path, scopes=scopes)

    # Try inline JSON data
    json_data = os.getenv("GSC_SERVICE_ACCOUNT_DATA") or os.getenv("GOOGLE_CREDENTIALS_JSON")
    if json_data:
        info = json.loads(json_data)
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)

    raise RuntimeError(
        "No GSC credentials found. Set GSC_SERVICE_ACCOUNT_JSON (file path) "
        "or GSC_SERVICE_ACCOUNT_DATA (JSON string) in environment."
    )


class GSCClient:
    """Google Search Console client for URL submission and indexation monitoring."""

    def __init__(self):
        self._indexing_service = None
        self._webmasters_service = None

    @property
    def available(self) -> bool:
        """Check if Google libraries are installed."""
        return HAS_GOOGLE

    def _get_indexing_service(self):
        if not self._indexing_service:
            creds = _get_credentials(INDEXING_SCOPES)
            self._indexing_service = build("indexing", "v3", credentials=creds)
        return self._indexing_service

    def _get_webmasters_service(self):
        if not self._webmasters_service:
            creds = _get_credentials(WEBMASTERS_SCOPES)
            self._webmasters_service = build("searchconsole", "v1", credentials=creds)
        return self._webmasters_service

    # ─── URL Submission ──────────────────────────────

    def submit_url(self, url: str) -> Dict[str, Any]:
        """Submit a single URL for indexing via the Indexing API.

        Uses URL_UPDATED notification type (works for both new and updated pages).
        """
        service = self._get_indexing_service()
        body = {"url": url, "type": "URL_UPDATED"}

        result = service.urlNotifications().publish(body=body).execute()

        return {
            "url": url,
            "status": "submitted",
            "notification_type": "URL_UPDATED",
            "response": result,
            "submitted_at": datetime.utcnow().isoformat(),
        }

    def submit_urls_batch(
        self,
        urls: List[str],
        max_per_day: int = 200,
    ) -> Dict[str, Any]:
        """Submit multiple URLs for indexing.

        Respects the daily quota (default 200/day per property).
        """
        submitted = []
        errors = []
        skipped = []

        for i, url in enumerate(urls):
            if i >= max_per_day:
                skipped.extend(urls[i:])
                break

            try:
                result = self.submit_url(url)
                submitted.append(result)
            except Exception as e:
                errors.append({"url": url, "error": str(e)})

        return {
            "submitted": len(submitted),
            "errors": len(errors),
            "skipped": len(skipped),
            "details": submitted,
            "error_details": errors if errors else None,
            "skipped_urls": skipped if skipped else None,
        }

    # ─── Indexation Status ───────────────────────────

    def check_indexation(self, site_url: str, page_url: str) -> Dict[str, Any]:
        """Check if a URL is indexed using the URL Inspection API.

        Args:
            site_url: The GSC property URL (e.g., "https://gocharbon.com")
            page_url: The specific page URL to check
        """
        service = self._get_webmasters_service()

        body = {
            "inspectionUrl": page_url,
            "siteUrl": site_url,
        }

        try:
            result = service.urlInspection().index().inspect(body=body).execute()
            inspection = result.get("inspectionResult", {})
            index_status = inspection.get("indexStatusResult", {})

            return {
                "url": page_url,
                "verdict": index_status.get("verdict", "UNKNOWN"),
                "coverage_state": index_status.get("coverageState", "UNKNOWN"),
                "indexing_state": index_status.get("indexingState", "UNKNOWN"),
                "last_crawl_time": index_status.get("lastCrawlTime"),
                "page_fetch_state": index_status.get("pageFetchState"),
                "robots_txt_state": index_status.get("robotsTxtState"),
                "checked_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "url": page_url,
                "verdict": "ERROR",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat(),
            }

    def check_indexation_batch(
        self,
        site_url: str,
        page_urls: List[str],
    ) -> Dict[str, Any]:
        """Check indexation status for multiple URLs."""
        results = []
        indexed = 0
        not_indexed = 0
        errors = 0

        for url in page_urls:
            result = self.check_indexation(site_url, url)
            results.append(result)

            verdict = result.get("verdict", "UNKNOWN")
            if verdict == "PASS":
                indexed += 1
            elif verdict == "ERROR":
                errors += 1
            else:
                not_indexed += 1

        return {
            "total": len(results),
            "indexed": indexed,
            "not_indexed": not_indexed,
            "errors": errors,
            "results": results,
        }


# ─── Singleton ───────────────────────────────────────

_client: Optional[GSCClient] = None


def get_gsc_client() -> GSCClient:
    global _client
    if _client is None:
        _client = GSCClient()
    return _client
