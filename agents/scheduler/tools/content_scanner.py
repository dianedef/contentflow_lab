"""
Content Scanner
Scans a project's content directories and imports articles into the status queue.

Reads project settings (local_repo_path + content_directories) from the database,
parses frontmatter from each markdown file, and creates ContentRecord entries.
"""

import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from agents.seo.config.project_store import ProjectStore
from status.schemas import ContentLifecycleStatus
from status.service import get_status_service


# ─── Frontmatter Parser ───────────────────────────────────────────────────────

def parse_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from a markdown file."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def content_hash(file_path: Path) -> str:
    """SHA256 hash of file contents for deduplication."""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]


# ─── Article Status Resolver ─────────────────────────────────────────────────

def resolve_status(frontmatter: Dict[str, Any]) -> str:
    """
    Determine the lifecycle status from frontmatter:
    - draft: true  → PENDING_REVIEW (needs validation before publishing)
    - published (draft: false, past pubDate) → PUBLISHED
    - future pubDate → PENDING_REVIEW
    - no pubDate    → PENDING_REVIEW
    """
    is_draft = frontmatter.get("draft", None)
    pub_date_raw = frontmatter.get("pubDate") or frontmatter.get("date")

    # Explicit draft
    if is_draft is True:
        return ContentLifecycleStatus.PENDING_REVIEW

    # Parse pubDate
    pub_date = None
    if pub_date_raw:
        try:
            if isinstance(pub_date_raw, (date, datetime)):
                pub_date = pub_date_raw if isinstance(pub_date_raw, date) else pub_date_raw.date()
            else:
                pub_date = date.fromisoformat(str(pub_date_raw).strip("'\""))
        except (ValueError, TypeError):
            pass

    today = date.today()

    if pub_date and pub_date <= today and is_draft is not True:
        return ContentLifecycleStatus.PUBLISHED

    return ContentLifecycleStatus.PENDING_REVIEW


# ─── Scanner ─────────────────────────────────────────────────────────────────

class ContentScanner:
    """
    Scans a registered project's content directories and imports articles
    into the status queue for scheduling and validation.
    """

    SUPPORTED_EXTENSIONS = {".md", ".mdx"}

    def __init__(self):
        self._store = ProjectStore()
        self._status = get_status_service()

    async def scan_project(self, project_id: str) -> Dict[str, Any]:
        """
        Scan all content directories of a project and import articles.

        Args:
            project_id: Project ID (from database)

        Returns:
            Summary dict: total, imported, skipped, errors
        """
        project = await self._store.get_by_id(project_id)
        if not project:
            return {"success": False, "error": f"Project {project_id} not found"}

        settings = project.settings
        if not settings:
            return {"success": False, "error": "Project has no settings (run analysis first)"}

        repo_path = settings.local_repo_path
        if not repo_path:
            return {"success": False, "error": "Project has no local_repo_path (run analysis first)"}

        content_dirs = settings.content_directories or []
        if not content_dirs:
            return {"success": False, "error": "No content directories configured for this project"}

        repo_root = Path(repo_path)
        results = {"success": True, "project": project.name, "directories": [], "total": 0, "imported": 0, "skipped": 0, "errors": 0}

        for content_dir in content_dirs:
            dir_result = await self._scan_directory(
                repo_root=repo_root,
                rel_dir=content_dir.path,
                project_id=project_id,
                project_name=project.name,
                extensions=set(content_dir.file_extensions) or self.SUPPORTED_EXTENSIONS,
            )
            results["directories"].append(dir_result)
            results["total"] += dir_result["total"]
            results["imported"] += dir_result["imported"]
            results["skipped"] += dir_result["skipped"]
            results["errors"] += dir_result["errors"]

        return results

    async def _scan_directory(
        self,
        repo_root: Path,
        rel_dir: str,
        project_id: str,
        project_name: str,
        extensions: set,
    ) -> Dict[str, Any]:
        """Scan a single content directory."""
        abs_dir = repo_root / rel_dir
        result = {"path": rel_dir, "total": 0, "imported": 0, "skipped": 0, "errors": 0, "items": []}

        if not abs_dir.exists():
            result["error"] = f"Directory not found: {abs_dir}"
            return result

        files = [
            f for f in abs_dir.rglob("*")
            if f.is_file() and f.suffix in extensions
        ]
        result["total"] = len(files)

        for file_path in files:
            try:
                rel_path = str(file_path.relative_to(repo_root))
                file_hash = content_hash(file_path)

                # Skip if already imported (same path + hash)
                existing = self._status.list_content(
                    project_id=project_id,
                    limit=1,
                    # Filter by content_path if supported, else check metadata
                )
                already_exists = any(
                    r.content_path == rel_path for r in existing
                )
                if already_exists:
                    result["skipped"] += 1
                    continue

                # Parse frontmatter
                raw = file_path.read_text(encoding="utf-8", errors="replace")
                fm = parse_frontmatter(raw)

                title = str(fm.get("title") or file_path.stem).strip().strip("'\"")
                description = str(fm.get("description") or "")[:500] if fm.get("description") else None
                tags = fm.get("tags") or []
                if isinstance(tags, str):
                    tags = [tags]
                pub_date_raw = fm.get("pubDate") or fm.get("date")
                status = resolve_status(fm)

                # Build metadata
                metadata: Dict[str, Any] = {
                    "project_name": project_name,
                    "file_hash": file_hash,
                    "framework": "astro",
                }
                if pub_date_raw:
                    metadata["pub_date"] = str(pub_date_raw)
                if fm.get("draft") is not None:
                    metadata["draft"] = fm["draft"]

                # Create in status queue
                record = self._status.create_content(
                    title=title,
                    content_type="article",
                    source_robot="manual",
                    status=status,
                    project_id=project_id,
                    content_path=rel_path,
                    content_preview=(raw[:300].strip() if raw else None),
                    content_hash=file_hash,
                    tags=tags,
                    metadata=metadata,
                )

                result["imported"] += 1
                result["items"].append({"id": record.id, "title": title, "status": status, "path": rel_path})

            except Exception as exc:
                result["errors"] += 1
                result["items"].append({"path": str(file_path), "error": str(exc)})

        return result


# ─── Singleton ────────────────────────────────────────────────────────────────

_scanner: Optional[ContentScanner] = None


def get_content_scanner() -> ContentScanner:
    global _scanner
    if _scanner is None:
        _scanner = ContentScanner()
    return _scanner
