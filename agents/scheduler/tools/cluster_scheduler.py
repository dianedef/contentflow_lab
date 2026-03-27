"""
Cluster Scheduler
Groups imported articles by topical cluster, then proposes a strategic
publication order using an LLM — asking the user to validate before
assigning pubDates and transitioning articles to SCHEDULED.

Cluster detection is path-based first (folder structure), enriched with tags.
LLM reasoning explains WHY to start with cluster X over cluster Y.
"""

import os
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from status.service import get_status_service
from status.schemas import ContentLifecycleStatus


# ─── Cluster Detection ────────────────────────────────────────────────────────

def _extract_cluster(content_path: str, tags: List[str]) -> str:
    """
    Derive a cluster name from the file path and tags.

    Priority:
    1. Second-level folder inside content dir  (e.g. src/data/outils/marketing/... → "outils/marketing")
    2. Top-level folder                         (e.g. src/content/docs/bonheur/... → "bonheur")
    3. First tag                                (fallback)
    4. "uncategorized"
    """
    parts = Path(content_path).parts

    # Remove common prefixes
    skip = {"src", "data", "content", "docs", "pages", "posts", "articles", "blog"}
    clean = [p for p in parts[:-1] if p.lower() not in skip]

    if len(clean) >= 2:
        return f"{clean[0]}/{clean[1]}"
    if len(clean) == 1:
        return clean[0]
    if tags:
        return tags[0]
    return "uncategorized"


def group_by_cluster(articles: List[Dict]) -> Dict[str, List[Dict]]:
    """Group a list of article records by cluster."""
    clusters: Dict[str, List[Dict]] = defaultdict(list)
    for article in articles:
        tags = article.get("tags") or []
        cluster = _extract_cluster(article.get("content_path", ""), tags)
        clusters[cluster].append(article)
    return dict(clusters)


# ─── Cluster Analysis ─────────────────────────────────────────────────────────

def analyze_cluster(name: str, articles: List[Dict]) -> Dict[str, Any]:
    """Compute basic signals for a cluster."""
    total = len(articles)
    has_index = any(
        Path(a.get("content_path", "")).stem in {"index", "introduction", "overview"}
        for a in articles
    )
    all_tags = []
    for a in articles:
        all_tags.extend(a.get("tags") or [])
    top_tags = sorted(set(all_tags), key=all_tags.count, reverse=True)[:5]

    return {
        "cluster": name,
        "article_count": total,
        "has_index_page": has_index,
        "top_tags": top_tags,
        "sample_titles": [a.get("title", "") for a in articles[:3]],
    }


# ─── LLM Ordering Proposal ────────────────────────────────────────────────────

def _build_prompt(cluster_analyses: List[Dict], cadence_per_week: int) -> str:
    lines = ["You are a content strategist for a French SEO-focused website."]
    lines.append(
        f"We have {len(cluster_analyses)} topical clusters of articles to publish "
        f"progressively at a cadence of {cadence_per_week} articles/week.\n"
    )
    lines.append("Here are the clusters:\n")
    for i, c in enumerate(cluster_analyses, 1):
        lines.append(
            f"{i}. **{c['cluster']}** — {c['article_count']} articles"
            + (", has index page" if c["has_index_page"] else "")
            + (f", tags: {', '.join(c['top_tags'])}" if c["top_tags"] else "")
        )
        if c["sample_titles"]:
            lines.append(f"   Examples: {' | '.join(c['sample_titles'])}")

    lines.append(
        "\nPropose an ordering of these clusters (1 = publish first) with a brief "
        "strategic reason for each choice. Consider: topical authority building, "
        "internal linking opportunities, cluster completeness, and SEO impact.\n"
        "Reply as a numbered list: `1. cluster_name — reason`"
    )
    return "\n".join(lines)


def _call_llm(prompt: str) -> str:
    """Call Claude via the Anthropic SDK."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as exc:
        return f"[LLM unavailable: {exc}]"


def _parse_ordering(llm_output: str, clusters: Dict[str, List]) -> List[Dict]:
    """
    Parse the LLM's numbered list into a structured ordering.
    Falls back to alphabetical if parsing fails.
    """
    ordered = []
    seen = set()

    for line in llm_output.splitlines():
        m = re.match(r"^\s*\d+\.\s*\*?\*?([^—*\n]+)\*?\*?\s*[—-]\s*(.+)", line)
        if not m:
            continue
        raw_name = m.group(1).strip()
        reason = m.group(2).strip()

        # Fuzzy match against actual cluster names
        match = next(
            (k for k in clusters if k.lower() == raw_name.lower()
             or raw_name.lower() in k.lower() or k.lower() in raw_name.lower()),
            None,
        )
        if match and match not in seen:
            ordered.append({
                "cluster": match,
                "article_count": len(clusters[match]),
                "reason": reason,
            })
            seen.add(match)

    # Append any clusters the LLM missed
    for k in clusters:
        if k not in seen:
            ordered.append({
                "cluster": k,
                "article_count": len(clusters[k]),
                "reason": "—",
            })

    return ordered


# ─── Date Assignment ──────────────────────────────────────────────────────────

def assign_pub_dates(
    ordered_clusters: List[Dict],
    clusters: Dict[str, List[Dict]],
    start_date: date,
    cadence_per_week: int,
) -> List[Dict]:
    """
    Assign a pubDate to each article following the cluster order.
    Returns a flat list of {id, title, cluster, pub_date}.
    """
    interval_days = max(1, round(7 / cadence_per_week))
    current = start_date
    assignments = []

    for entry in ordered_clusters:
        for article in clusters[entry["cluster"]]:
            assignments.append({
                "id": article["id"],
                "title": article.get("title", ""),
                "cluster": entry["cluster"],
                "pub_date": current.isoformat(),
            })
            current += timedelta(days=interval_days)

    return assignments


# ─── Main Scheduler ───────────────────────────────────────────────────────────

class ClusterScheduler:
    """
    Proposes a cluster-based publication plan for a project.

    Flow:
    1. Load all pending_review articles for the project
    2. Group by cluster (folder/tags)
    3. Ask LLM to rank clusters strategically
    4. Return a proposal (cluster order + date preview) for user approval
    5. On approval: call apply_schedule() to write pubDates and transition to SCHEDULED
    """

    def __init__(self):
        self._status = get_status_service()

    def propose(
        self,
        project_id: str,
        cadence_per_week: int = 5,
        start_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a scheduling proposal for user review.

        Args:
            project_id:       Project to schedule
            cadence_per_week: Articles per week
            start_date:       ISO date string (default: tomorrow)

        Returns:
            {
              "cluster_order": [...],   # LLM-ordered clusters with reasons
              "llm_reasoning": str,     # Raw LLM output
              "total_articles": int,
              "estimated_weeks": float,
              "start_date": str,
              "cadence_per_week": int,
              "preview": [...]          # First 10 assignments
            }
        """
        # 1. Load articles
        articles = self._load_pending(project_id)
        if not articles:
            return {"success": False, "error": "No pending_review articles found for this project"}

        # 2. Group by cluster
        clusters = group_by_cluster(articles)

        # 3. Analyse each cluster
        analyses = [analyze_cluster(name, arts) for name, arts in clusters.items()]
        analyses.sort(key=lambda c: c["article_count"], reverse=True)

        # 4. Ask LLM for strategic ordering
        prompt = _build_prompt(analyses, cadence_per_week)
        llm_output = _call_llm(prompt)
        ordered = _parse_ordering(llm_output, clusters)

        # 5. Preview date assignments
        start = date.fromisoformat(start_date) if start_date else date.today() + timedelta(days=1)
        assignments = assign_pub_dates(ordered, clusters, start, cadence_per_week)

        return {
            "success": True,
            "project_id": project_id,
            "cluster_order": ordered,
            "llm_reasoning": llm_output,
            "total_articles": len(articles),
            "cluster_count": len(clusters),
            "estimated_weeks": round(len(articles) / cadence_per_week, 1),
            "start_date": start.isoformat(),
            "cadence_per_week": cadence_per_week,
            "preview": assignments[:10],
        }

    def apply_schedule(
        self,
        project_id: str,
        cadence_per_week: int = 5,
        start_date: Optional[str] = None,
        cluster_order: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Apply the schedule: write pubDates to metadata and transition to PENDING_REVIEW.
        Call this after the user validates the proposal.

        Args:
            project_id:      Project ID
            cadence_per_week: Articles per week
            start_date:      ISO date string
            cluster_order:   Optional explicit cluster ordering (list of cluster names)

        Returns:
            Summary of applied assignments
        """
        articles = self._load_pending(project_id)
        if not articles:
            return {"success": False, "error": "No articles to schedule"}

        clusters = group_by_cluster(articles)

        # Use provided order or default alphabetical
        if cluster_order:
            ordered = [
                {"cluster": c, "article_count": len(clusters.get(c, []))}
                for c in cluster_order
                if c in clusters
            ]
            # Append any missing clusters
            for k in clusters:
                if k not in cluster_order:
                    ordered.append({"cluster": k, "article_count": len(clusters[k])})
        else:
            ordered = [{"cluster": k, "article_count": len(v)} for k, v in clusters.items()]

        start = date.fromisoformat(start_date) if start_date else date.today() + timedelta(days=1)
        assignments = assign_pub_dates(ordered, clusters, start, cadence_per_week)

        applied = 0
        for assignment in assignments:
            try:
                self._status.update_content(
                    assignment["id"],
                    metadata={
                        "scheduled_pub_date": assignment["pub_date"],
                        "cluster": assignment["cluster"],
                    },
                )
                applied += 1
            except Exception:
                pass

        return {
            "success": True,
            "applied": applied,
            "total": len(assignments),
            "first_publish": assignments[0]["pub_date"] if assignments else None,
            "last_publish": assignments[-1]["pub_date"] if assignments else None,
        }

    def _load_pending(self, project_id: str) -> List[Dict]:
        """Load all pending_review articles for a project as plain dicts."""
        records = self._status.list_content(
            project_id=project_id,
            status=ContentLifecycleStatus.PENDING_REVIEW,
            limit=5000,
        )
        return [
            {
                "id": r.id,
                "title": r.title,
                "content_path": r.content_path or "",
                "tags": r.tags or [],
                "metadata": r.metadata or {},
            }
            for r in records
        ]


# ─── Singleton ────────────────────────────────────────────────────────────────

_scheduler: Optional[ClusterScheduler] = None


def get_cluster_scheduler() -> ClusterScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ClusterScheduler()
    return _scheduler
