"""Projects API endpoints.

Handles project onboarding workflow and CRUD operations.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pathlib import Path
from typing import Any, List, Optional

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
        settings=project.settings,
        last_analyzed_at=project.last_analyzed_at,
        created_at=project.created_at
    )


async def get_user_default_project_id(user_id: str) -> str | None:
    """Return the last-opened project id stored in user settings."""
    settings = await user_data_store_module.user_data_store.get_user_settings(user_id)
    default_project_id = settings.get("defaultProjectId")
    return default_project_id if isinstance(default_project_id, str) else None


async def require_owned_project(
    project_id: str,
    current_user: CurrentUser,
) -> Project:
    """Load a project and ensure the current user owns it."""
    project = await project_store_module.project_store.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
    """Start onboarding a new project."""
    return await project_onboarding_service.initiate_onboarding(
        user_id=current_user.user_id,
        github_url=str(request.github_url),
        name=request.name,
        description=request.description
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
    project = await project_store_module.project_store.create(
        user_id=current_user.user_id,
        name=request.name or str(request.github_url).rstrip("/").split("/")[-1],
        url=str(request.github_url),
        description=request.description,
    )

    # Direct-create is an explicit user action in the app onboarding flow.
    # Mark onboarding as complete immediately so clients don't treat the project
    # as an unfinished wizard step on next launch.
    project = await project_store_module.project_store.update_onboarding_status(
        project.id,
        OnboardingStatus.COMPLETED,
    ) or project

    default_project_id = await get_user_default_project_id(current_user.user_id)
    if not default_project_id:
        await user_data_store_module.user_data_store.update_user_settings(
            current_user.user_id,
            {"defaultProjectId": project.id},
        )
        default_project_id = project.id
    return project_to_response(project, default_project_id=default_project_id)


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
    await require_owned_project(project_id, current_user)

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
    await require_owned_project(project_id, current_user)

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
    projects = await project_store_module.project_store.get_by_user(current_user.user_id)
    default_project_id = await get_user_default_project_id(current_user.user_id)

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
    await require_owned_project(project_id, current_user)
    project = await project_store_module.project_store.update(
        project_id=project_id,
        name=request.name,
        url=str(request.github_url) if request.github_url else None,
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
    """Delete a project."""
    await require_owned_project(project_id, current_user)

    await project_store_module.project_store.delete(project_id)
    return {"deleted": True, "project_id": project_id}


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
    await require_owned_project(project_id, current_user)
    await user_data_store_module.user_data_store.update_user_settings(
        current_user.user_id,
        {"defaultProjectId": project_id},
    )
    project = await project_store_module.project_store.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

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
    await require_owned_project(project_id, current_user)
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
    await require_owned_project(project_id, current_user)
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
    await require_owned_project(project_id, current_user)
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
    await require_owned_project(project_id, current_user)
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
