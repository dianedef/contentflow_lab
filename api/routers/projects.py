"""Projects API endpoints.

Handles project onboarding workflow and CRUD operations.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import urlparse

from api.models.project import (
    OnboardProjectRequest,
    OnboardProjectResponse,
    AnalyzeProjectRequest,
    ProjectDetectionResult,
    ConfirmProjectRequest,
    ProjectContentTreeDirectory,
    ProjectContentTreeFile,
    ProjectContentTreeResponse,
    UpdateProjectRequest,
    ProjectResponse,
    ProjectListResponse,
    Project,
    OnboardingStatus,
)
try:
    from agents.seo.services.project_onboarding import project_onboarding_service
except Exception as exc:  # pragma: no cover - exercised when optional AI deps are missing
    class _UnavailableProjectOnboardingService:
        """Fallback service when onboarding dependencies are not installed."""

        def __init__(self, reason: str) -> None:
            self._reason = reason

        def _raise_unavailable(self) -> None:
            raise HTTPException(
                status_code=503,
                detail=f"Project onboarding is temporarily unavailable ({self._reason}).",
            )

        def _unavailable_fn(self, *args, **kwargs):
            del args, kwargs
            self._raise_unavailable()

        initiate_onboarding = _unavailable_fn
        analyze_project = _unavailable_fn
        confirm_project = _unavailable_fn
        refresh_analysis = _unavailable_fn

    project_onboarding_service = _UnavailableProjectOnboardingService(str(exc))

from api.dependencies.auth import CurrentUser, require_current_user
from api.services import user_data_store as user_data_store_module
from agents.seo.config import project_store as project_store_module


router = APIRouter(
    prefix="/api/projects",
    tags=["Projects"],
    responses={404: {"description": "Project not found"}},
)

_PROJECT_SELECTION_AUTO = "auto"
_PROJECT_SELECTION_SELECTED = "selected"
_PROJECT_SELECTION_NONE = "none"


def _normalize_selection_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or _PROJECT_SELECTION_AUTO).strip().lower()
    if mode in {
        _PROJECT_SELECTION_AUTO,
        _PROJECT_SELECTION_SELECTED,
        _PROJECT_SELECTION_NONE,
    }:
        return mode
    return _PROJECT_SELECTION_AUTO


def _is_selectable_project(project: Project) -> bool:
    return project.archived_at is None and project.deleted_at is None


def _normalize_source_url(raw_url: Optional[str]) -> str:
    return (raw_url or "").strip()


def _resolve_project_type(source_url: str) -> str:
    normalized = source_url.strip()
    if not normalized:
        return "manual"
    parsed = urlparse(normalized)
    host = parsed.netloc.lower()
    if host in {"github.com", "www.github.com"}:
        return "github"
    return "website"


def _derive_project_name(explicit_name: Optional[str], source_url: str) -> str:
    if explicit_name and explicit_name.strip():
        return explicit_name.strip()
    normalized = source_url.strip().rstrip("/")
    if normalized:
        candidate = normalized.rsplit("/", 1)[-1].replace(".git", "").strip()
        if candidate:
            return candidate
    return "Untitled project"


async def _resolve_user_project_selection(
    user_id: str,
    projects: Optional[list[Project]] = None,
) -> tuple[str, Optional[str]]:
    settings = await user_data_store_module.user_data_store.get_user_settings(user_id)
    mode = _normalize_selection_mode(settings.get("projectSelectionMode"))
    configured_default = settings.get("defaultProjectId")
    configured_default = configured_default if isinstance(configured_default, str) else None

    available_projects = projects
    if available_projects is None:
        available_projects = await project_store_module.project_store.get_by_user(
            user_id,
            include_archived=True,
            include_deleted=False,
        )
    selectable_projects = [project for project in available_projects if _is_selectable_project(project)]

    if mode == _PROJECT_SELECTION_NONE:
        return mode, None

    if mode == _PROJECT_SELECTION_SELECTED:
        if configured_default and any(project.id == configured_default for project in selectable_projects):
            return mode, configured_default
        return mode, None

    if configured_default and any(project.id == configured_default for project in selectable_projects):
        return mode, configured_default

    flagged_default = next(
        (project.id for project in selectable_projects if project.is_default),
        None,
    )
    if flagged_default:
        return mode, flagged_default

    fallback = selectable_projects[0].id if selectable_projects else None
    return mode, fallback


def _build_project_tree_root(project_path: str) -> Path:
    repo_root = Path(project_path).expanduser().resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        raise HTTPException(status_code=404, detail="Local repo path does not exist.")
    return repo_root


def _project_tree_safe_path(repo_root: Path, requested: str) -> Path:
    normalized_path = requested.strip().lstrip("/")
    if ".." in normalized_path.split("/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    candidate = repo_root / normalized_path if normalized_path else repo_root
    try:
        resolved_candidate = candidate.resolve()
    except OSError:
        raise HTTPException(status_code=400, detail="Invalid path")

    if resolved_candidate != repo_root and repo_root not in resolved_candidate.parents:
        raise HTTPException(status_code=400, detail="Path escapes repository root")

    if not resolved_candidate.exists() or not resolved_candidate.is_dir():
        raise HTTPException(status_code=400, detail="Invalid content directory")
    return resolved_candidate


def _normalize_parent_path(repo_root: Path, target: Path) -> Optional[str]:
    if target == repo_root:
        return None
    parent = target.parent.relative_to(repo_root)
    return parent.as_posix() if str(parent) else ""


def project_to_response(project: Project, *, default_project_id: str | None = None) -> ProjectResponse:
    """Convert Project model to response format."""
    return ProjectResponse(
        id=project.id,
        user_id=project.user_id,
        name=project.name,
        url=project.url,
        type=project.type,
        description=project.description,
        is_default=project.id == default_project_id,
        is_archived=project.archived_at is not None,
        is_deleted=project.deleted_at is not None,
        settings=project.settings,
        last_analyzed_at=project.last_analyzed_at,
        archived_at=project.archived_at,
        deleted_at=project.deleted_at,
        created_at=project.created_at
    )


async def get_user_default_project_id(user_id: str) -> str | None:
    """Resolve the effective active project id for the current selection mode."""
    _, default_project_id = await _resolve_user_project_selection(user_id)
    return default_project_id


async def require_owned_project(
    project_id: str,
    current_user: CurrentUser,
    *,
    allow_archived: bool = True,
    allow_deleted: bool = False,
) -> Project:
    """Load a project and ensure the current user owns it."""
    project = await project_store_module.project_store.get_by_id(
        project_id,
        include_deleted=allow_deleted,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if project.deleted_at is not None and not allow_deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.archived_at is not None and not allow_archived:
        raise HTTPException(status_code=409, detail="Archived project")
    return project


@router.get(
    "/{project_id}/content-tree",
    response_model=ProjectContentTreeResponse,
    summary="Browse project content tree",
    description="""
    Browse folders from the cloned project to help source selection.

    Query param:
    - path: relative path from repository root (default = root)
    """
)
async def project_content_tree(
    project_id: str,
    path: str = Query("", description="Relative repository path to browse"),
    current_user: CurrentUser = Depends(require_current_user),
) -> ProjectContentTreeResponse:
    """Return directories and markdown files from a project working tree."""
    project = await require_owned_project(project_id, current_user)
    project_path = project.settings.local_repo_path if project.settings else None
    if not project_path:
        raise HTTPException(
            status_code=404,
            detail="Repo local path not available. Analyze the project first.",
        )

    repo_root = _build_project_tree_root(project_path)
    target = _project_tree_safe_path(repo_root, path)

    ignore = {
        ".git",
        ".next",
        "node_modules",
        "dist",
        "build",
        ".turbo",
        ".cache",
        "coverage",
        "tmp",
    }

    directories: list[ProjectContentTreeDirectory] = []
    files: list[ProjectContentTreeFile] = []

    for entry in sorted(target.iterdir(), key=lambda item: item.name.lower()):
        if entry.name in ignore or entry.name.startswith("."):
            continue
        rel = entry.relative_to(repo_root).as_posix()
        if entry.is_dir():
            has_markdown = any(
                child.is_file() and child.suffix.lower() in {".md", ".mdx"}
                for child in entry.rglob("*")
            )
            directories.append(
                ProjectContentTreeDirectory(
                    name=entry.name,
                    path=rel,
                    has_markdown_files=has_markdown,
                )
            )
        elif entry.is_file() and entry.suffix.lower() in {".md", ".mdx"}:
            files.append(
                ProjectContentTreeFile(
                    name=entry.name,
                    path=rel,
                )
            )

    return ProjectContentTreeResponse(
        project_id=project_id,
        current_path="" if target == repo_root else target.relative_to(repo_root).as_posix(),
        parent_path=_normalize_parent_path(repo_root, target),
        directories=directories,
        files=files,
    )


# ─────────────────────────────────────────────────
# Onboarding Endpoints
# ─────────────────────────────────────────────────

@router.post(
    "/onboard",
    response_model=OnboardProjectResponse,
    summary="Start project onboarding",
    description="""
    Start the onboarding process for a new project.

    **What it does:**
    - Creates a new project record
    - Prepares for repository analysis
    - Returns project_id for subsequent steps

    **Next step:** Call `/api/projects/{id}/analyze` to analyze the repository.

    **Example:**
    ```json
    {
      "github_url": "https://github.com/user/my-site"
    }
    ```
    """
)
async def onboard_project(
    request: OnboardProjectRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> OnboardProjectResponse:
    """Start onboarding a new project.

    For manual or website sources (or empty source), this creates the project
    directly and marks onboarding as completed because there is no GitHub clone
    step to run in this route.
    """
    source_url = _normalize_source_url(request.source_url)
    source_type = _resolve_project_type(source_url)

    if source_type != "github":
        project = await project_store_module.project_store.create(
            user_id=current_user.user_id,
            name=_derive_project_name(request.name, source_url),
            url=source_url,
            description=request.description,
            project_type=source_type,
        )
        await project_store_module.project_store.update_onboarding_status(
            project.id,
            OnboardingStatus.COMPLETED,
        )
        await user_data_store_module.user_data_store.update_user_settings(
            current_user.user_id,
            {
                "defaultProjectId": project.id,
                "projectSelectionMode": _PROJECT_SELECTION_SELECTED,
            },
        )
        return OnboardProjectResponse(
            project_id=project.id,
            status=OnboardingStatus.COMPLETED,
            message="Project created.",
        )

    return await project_onboarding_service.initiate_onboarding(
        user_id=current_user.user_id,
        github_url=source_url,
        name=request.name,
        description=request.description,
    )


@router.post(
    "",
    response_model=ProjectResponse,
    summary="Create project",
    description="Create a project record directly from a GitHub repository URL."
)
async def create_project(
    request: OnboardProjectRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> Any:
    """Create a project without running the full onboarding wizard."""
    source_url = _normalize_source_url(request.source_url)
    source_type = _resolve_project_type(source_url)
    project = await project_store_module.project_store.create(
        user_id=current_user.user_id,
        name=_derive_project_name(request.name, source_url),
        url=source_url,
        project_type=source_type,
        description=request.description,
    )

    # Direct-create is an explicit user action in the app onboarding flow.
    # Mark onboarding as complete immediately so clients don't treat the project
    # as an unfinished wizard step on next launch.
    project = await project_store_module.project_store.update_onboarding_status(
        project.id,
        OnboardingStatus.COMPLETED,
    ) or project

    await user_data_store_module.user_data_store.update_user_settings(
        current_user.user_id,
        {
            "defaultProjectId": project.id,
            "projectSelectionMode": _PROJECT_SELECTION_SELECTED,
        },
    )
    return project_to_response(project, default_project_id=project.id)


@router.post(
    "/{project_id}/analyze",
    response_model=ProjectDetectionResult,
    summary="Analyze project repository",
    description="""
    Clone and analyze the project repository.

    **What it does:**
    - Clones the GitHub repository
    - Detects framework (Astro, Next.js, etc.)
    - Detects package manager (npm, yarn, pnpm)
    - Finds content directories
    - Counts content files

    **Next step:** Call `/api/projects/{id}/confirm` to confirm or override settings.

    **Returns:**
    - Detected tech stack with confidence score
    - List of content directories
    - Suggested primary content directory
    """
)
async def analyze_project(
    project_id: str,
    request: AnalyzeProjectRequest = AnalyzeProjectRequest(),
    current_user: CurrentUser = Depends(require_current_user),
) -> ProjectDetectionResult:
    """Analyze project repository and detect settings."""
    await require_owned_project(project_id, current_user, allow_archived=False)

    integration = await user_data_store_module.user_data_store.get_github_integration(current_user.user_id)
    github_token = integration.get("token") if integration else None

    try:
        return await project_onboarding_service.analyze_project(
            project_id=project_id,
            force_reclone=request.force_reclone,
            github_token=github_token,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{project_id}/confirm",
    response_model=ProjectResponse,
    summary="Confirm project settings",
    description="""
    Confirm or override the detected project settings.

    **What it does:**
    - Accepts auto-detected settings OR
    - Applies user overrides for content directory
    - Applies configuration overrides
    - Marks onboarding as complete

    **Example - Accept detected settings:**
    ```json
    {
      "project_id": "uuid-here",
      "confirmed": true
    }
    ```

    **Example - Override content directories:**
    ```json
    {
      "project_id": "uuid-here",
      "confirmed": false,
      "content_directories_override": [
        {"path": "src/content/blog", "auto_detected": false, "file_extensions": [".md", ".mdx"]},
        {"path": "src/content/docs", "auto_detected": false, "file_extensions": [".md", ".mdx"]}
      ]
    }
    ```
    """
)
async def confirm_project(
    project_id: str,
    request: ConfirmProjectRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> Any:
    """Confirm or override project settings."""
    # Ensure project_id in path matches request
    if request.project_id != project_id:
        request.project_id = project_id
    await require_owned_project(project_id, current_user, allow_archived=False)

    try:
        project = await project_onboarding_service.confirm_project(request)
        default_project_id = await get_user_default_project_id(current_user.user_id)
        return project_to_response(project, default_project_id=default_project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─────────────────────────────────────────────────
# CRUD Endpoints
# ─────────────────────────────────────────────────

@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List all projects",
    description="Get all projects for the current user."
)
async def list_projects(
    current_user: CurrentUser = Depends(require_current_user),
) -> ProjectListResponse:
    """Get all projects for current user."""
    projects = await project_store_module.project_store.get_by_user(
        current_user.user_id,
        include_archived=True,
        include_deleted=False,
    )
    _, default_project_id = await _resolve_user_project_selection(
        current_user.user_id,
        projects,
    )

    return ProjectListResponse(
        projects=[
            project_to_response(p, default_project_id=default_project_id)
            for p in projects
        ],
        total=len(projects),
        default_project_id=default_project_id
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details",
    description="Get full details for a specific project."
)
async def get_project(
    project_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> Any:
    """Get project by ID."""
    project = await require_owned_project(project_id, current_user)
    default_project_id = await get_user_default_project_id(current_user.user_id)

    return project_to_response(project, default_project_id=default_project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
    description="Update project details, content directory, or config overrides."
)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> Any:
    """Update project details."""
    await require_owned_project(project_id, current_user, allow_archived=False)
    project_type = (
        _resolve_project_type(request.source_url)
        if request.source_url is not None
        else None
    )
    project = await project_store_module.project_store.update(
        project_id=project_id,
        name=request.name,
        url=request.source_url,
        project_type=project_type,
        description=request.description,
        content_directories=request.content_directories,
        config_overrides=request.config_overrides,
        analytics_enabled=request.analytics_enabled,
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    default_project_id = await get_user_default_project_id(current_user.user_id)
    return project_to_response(project, default_project_id=default_project_id)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project (legacy)",
    description="Legacy alias for PATCH /{project_id}."
)
async def update_project_legacy(
    project_id: str,
    request: UpdateProjectRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> Any:
    """Keep backward compatibility with clients still using PUT for updates."""
    return await update_project(
        project_id=project_id,
        request=request,
        current_user=current_user,
    )


@router.delete(
    "/{project_id}",
    summary="Delete project",
    description="Delete a project. This action cannot be undone."
)
async def delete_project(
    project_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    """Hard-delete a project (reserved explicit path; default UI should archive)."""
    await require_owned_project(project_id, current_user, allow_archived=True, allow_deleted=False)
    await project_store_module.project_store.hard_delete(project_id)

    settings = await user_data_store_module.user_data_store.get_user_settings(
        current_user.user_id
    )
    if settings.get("defaultProjectId") == project_id:
        await user_data_store_module.user_data_store.update_user_settings(
            current_user.user_id,
            {
                "defaultProjectId": None,
                "projectSelectionMode": _PROJECT_SELECTION_NONE,
            },
        )
    return {"deleted": True, "project_id": project_id}


@router.post(
    "/{project_id}/archive",
    response_model=ProjectResponse,
    summary="Archive project",
    description="Archive a project (default removal action in UI).",
)
async def archive_project(
    project_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> Any:
    project = await require_owned_project(
        project_id,
        current_user,
        allow_archived=True,
        allow_deleted=False,
    )
    if project.archived_at is not None:
        default_project_id = await get_user_default_project_id(current_user.user_id)
        return project_to_response(project, default_project_id=default_project_id)

    archived = await project_store_module.project_store.archive(project_id)
    if not archived:
        raise HTTPException(status_code=404, detail="Project not found")

    settings = await user_data_store_module.user_data_store.get_user_settings(
        current_user.user_id
    )
    if settings.get("defaultProjectId") == project_id:
        await user_data_store_module.user_data_store.update_user_settings(
            current_user.user_id,
            {
                "defaultProjectId": None,
                "projectSelectionMode": _PROJECT_SELECTION_NONE,
            },
        )
        return project_to_response(archived, default_project_id=None)

    default_project_id = await get_user_default_project_id(current_user.user_id)
    return project_to_response(archived, default_project_id=default_project_id)


@router.post(
    "/{project_id}/unarchive",
    response_model=ProjectResponse,
    summary="Unarchive project",
    description="Restore an archived project back to normal lists.",
)
async def unarchive_project(
    project_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> Any:
    await require_owned_project(
        project_id,
        current_user,
        allow_archived=True,
        allow_deleted=False,
    )
    project = await project_store_module.project_store.unarchive(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    default_project_id = await get_user_default_project_id(current_user.user_id)
    return project_to_response(project, default_project_id=default_project_id)


@router.post(
    "/{project_id}/set-default",
    response_model=ProjectResponse,
    summary="Set default project",
    description="Set this project as the user's default project."
)
async def set_default_project(
    project_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> Any:
    """Set project as default."""
    await require_owned_project(project_id, current_user, allow_archived=False)
    project = await project_store_module.project_store.set_default(
        current_user.user_id,
        project_id,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await user_data_store_module.user_data_store.update_user_settings(
        current_user.user_id,
        {
            "defaultProjectId": project_id,
            "projectSelectionMode": _PROJECT_SELECTION_SELECTED,
        },
    )
    return project_to_response(project, default_project_id=project_id)


@router.post(
    "/{project_id}/refresh",
    response_model=ProjectDetectionResult,
    summary="Refresh project analysis",
    description="""
    Re-analyze the project repository.

    **What it does:**
    - Pulls latest changes from GitHub
    - Re-detects tech stack
    - Updates content directory detection
    - Preserves user config overrides

    Useful when the repository has changed.
    """
)
async def refresh_project(
    project_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> ProjectDetectionResult:
    """Re-analyze project repository."""
    await require_owned_project(project_id, current_user, allow_archived=False)
    integration = await user_data_store_module.user_data_store.get_github_integration(current_user.user_id)
    github_token = integration.get("token") if integration else None
    try:
        return await project_onboarding_service.refresh_analysis(
            project_id=project_id,
            github_token=github_token,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{project_id}/scan-content",
    summary="Scan and import content",
    description="""
    Scan the project's content directories and import all articles into the scheduling queue.

    **What it does:**
    - Reads `local_repo_path` and `content_directories` from project settings
    - Parses frontmatter (title, pubDate, draft, tags) from each markdown file
    - Creates a ContentRecord per article in the status queue
    - Already published articles → status `published`
    - Drafts or future-dated articles → status `pending_review`
    - Skips files already imported (deduplication by path)

    **Prerequisite:** Project must have been analyzed (`/analyze` + `/confirm`).
    """
)
async def scan_project_content(
    project_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    """Import all markdown content from the project into the scheduling queue."""
    await require_owned_project(project_id, current_user, allow_archived=False)
    try:
        from agents.scheduler.tools.content_scanner import get_content_scanner
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Content scan is temporarily unavailable ({exc}).",
        )
    scanner = get_content_scanner()
    result = await scanner.scan_project(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Scan failed"))
    return result


@router.post(
    "/{project_id}/propose-schedule",
    summary="AI scheduling proposal",
    description="""
    Groups pending articles by topical cluster and asks Claude to propose
    a strategic publication order.

    **Returns a proposal for user review — does NOT apply anything yet.**
    Call `/{project_id}/apply-schedule` to confirm.

    Query params:
    - `cadence`: articles per week (default: 5)
    - `start_date`: ISO date for first publication (default: tomorrow)
    """
)
async def propose_schedule(
    project_id: str,
    cadence: int = 5,
    start_date: Optional[str] = None,
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    """Generate an AI-powered cluster scheduling proposal."""
    await require_owned_project(project_id, current_user, allow_archived=False)
    try:
        from agents.scheduler.tools.cluster_scheduler import get_cluster_scheduler
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Scheduling proposal is temporarily unavailable ({exc}).",
        )
    scheduler = get_cluster_scheduler()
    result = scheduler.propose(project_id, cadence_per_week=cadence, start_date=start_date)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Proposal failed"))
    return result


@router.post(
    "/{project_id}/apply-schedule",
    summary="Apply scheduling plan",
    description="""
    Applies a validated scheduling plan: assigns pubDates to all pending articles
    following the cluster order, and updates their metadata.

    Call this after reviewing the proposal from `propose-schedule`.

    Body (optional):
    - `cadence`: articles per week
    - `start_date`: ISO date string
    - `cluster_order`: list of cluster names in desired order (from the proposal)
    """
)
async def apply_schedule(
    project_id: str,
    cadence: int = 5,
    start_date: Optional[str] = None,
    cluster_order: Optional[list] = None,
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    """Apply the validated schedule to all pending articles."""
    await require_owned_project(project_id, current_user, allow_archived=False)
    try:
        from agents.scheduler.tools.cluster_scheduler import get_cluster_scheduler
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Schedule application is temporarily unavailable ({exc}).",
        )
    scheduler = get_cluster_scheduler()
    result = scheduler.apply_schedule(
        project_id,
        cadence_per_week=cadence,
        start_date=start_date,
        cluster_order=cluster_order,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Apply failed"))
    return result
