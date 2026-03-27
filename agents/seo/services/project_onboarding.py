"""
Project Onboarding Service

Orchestrates the project onboarding workflow:
1. Accept GitHub URL
2. Clone and analyze repository
3. Auto-detect tech stack and content directory
4. Allow user confirmation/override
5. Store project config in database
"""

from typing import Optional
from datetime import datetime

from api.models.project import (
    Project,
    ProjectSettings,
    TechStackDetection,
    ContentDirectoryConfig,
    ProjectConfigOverrides,
    OnboardingStatus,
    OnboardProjectResponse,
    ProjectDetectionResult,
    ConfirmProjectRequest,
)
from agents.seo.config.project_store import project_store
from agents.seo.tools.repo_analyzer import GitHubRepoAnalyzer


class ProjectOnboardingService:
    """
    Service for orchestrating project onboarding workflow.

    Handles the complete flow from GitHub URL to configured project.
    """

    def __init__(self, workspace_dir: Optional[str] = None):
        """
        Initialize the onboarding service.

        Args:
            workspace_dir: Optional custom workspace for cloning repos
        """
        self.analyzer = GitHubRepoAnalyzer(workspace_dir=workspace_dir)
        self.store = project_store

    def _extract_repo_name(self, github_url: str) -> str:
        """Extract repository name from GitHub URL."""
        url = str(github_url).rstrip('/')
        repo_name = url.split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        return repo_name

    async def initiate_onboarding(
        self,
        user_id: str,
        github_url: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> OnboardProjectResponse:
        """
        Start the onboarding process for a new project.

        Creates a project record with PENDING status.

        Args:
            user_id: Owner user ID
            github_url: GitHub repository URL
            name: Optional project name (defaults to repo name)
            description: Optional project description

        Returns:
            OnboardProjectResponse with project_id and status
        """
        # Check if project already exists for this user/URL
        existing = await self.store.get_by_url(user_id, str(github_url))
        if existing:
            return OnboardProjectResponse(
                project_id=existing.id,
                status=existing.settings.onboarding_status if existing.settings else OnboardingStatus.PENDING,
                message=f"Project already exists. Current status: {existing.settings.onboarding_status.value if existing.settings else 'pending'}"
            )

        # Extract repo name if no name provided
        project_name = name or self._extract_repo_name(github_url)

        # Create project with pending status
        project = await self.store.create(
            user_id=user_id,
            name=project_name,
            url=str(github_url),
            description=description
        )

        # Update status to cloning (indicates onboarding has started)
        await self.store.update_onboarding_status(
            project_id=project.id,
            status=OnboardingStatus.CLONING
        )

        return OnboardProjectResponse(
            project_id=project.id,
            status=OnboardingStatus.CLONING,
            message=f"Project '{project_name}' created. Ready for analysis."
        )

    async def analyze_project(
        self,
        project_id: str,
        force_reclone: bool = False
    ) -> ProjectDetectionResult:
        """
        Analyze a project repository.

        Clones the repository, detects tech stack and content directories.

        Args:
            project_id: Project ID
            force_reclone: Force re-clone even if exists locally

        Returns:
            ProjectDetectionResult with all detected information
        """
        # Get project
        project = await self.store.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        # Update status to analyzing
        await self.store.update_onboarding_status(
            project_id=project_id,
            status=OnboardingStatus.ANALYZING
        )

        try:
            # Run the analyzer
            analysis = self.analyzer.analyze_for_onboarding(
                repo_url=project.url,
                force_reclone=force_reclone
            )

            # Extract results
            tech_stack: TechStackDetection = analysis["tech_stack"]
            content_directories = analysis["content_directories"]
            suggested_content_dir = analysis["suggested_content_dir"]
            repo_path = analysis["repo_path"]

            # Créer un ContentDirectoryConfig pour chaque dossier détecté.
            # Le dossier suggéré passe en premier (priorité la plus haute).
            ordered_dirs = []
            if suggested_content_dir:
                ordered_dirs.append(suggested_content_dir)
            ordered_dirs += [d for d in content_directories if d != suggested_content_dir]

            content_dir_configs = [
                ContentDirectoryConfig(
                    path=d,
                    auto_detected=True,
                    file_extensions=[".md", ".mdx"]
                )
                for d in ordered_dirs
            ]

            # Update project with detection results
            await self.store.update_onboarding_status(
                project_id=project_id,
                status=OnboardingStatus.AWAITING_CONFIRMATION,
                tech_stack=tech_stack,
                content_directories=content_dir_configs,
                local_repo_path=repo_path
            )

            return ProjectDetectionResult(
                project_id=project_id,
                tech_stack=tech_stack,
                content_directories=content_directories,
                suggested_content_dir=suggested_content_dir,
                total_content_files=analysis["total_content_files"],
                framework_config_found=analysis["framework_config_found"]
            )

        except Exception as e:
            # Update status to failed
            await self.store.update_onboarding_status(
                project_id=project_id,
                status=OnboardingStatus.FAILED
            )
            raise RuntimeError(f"Analysis failed: {str(e)}")

    async def confirm_project(
        self,
        request: ConfirmProjectRequest
    ) -> Project:
        """
        Confirm or override detected project settings.

        Completes the onboarding workflow.

        Args:
            request: Confirmation request with optional overrides

        Returns:
            Completed Project
        """
        project = await self.store.get_by_id(request.project_id)
        if not project:
            raise ValueError(f"Project not found: {request.project_id}")

        settings = project.settings or ProjectSettings()

        # Apply content directories override if provided
        if request.content_directories_override:
            settings.content_directories = request.content_directories_override

        # Apply config overrides
        if request.config_overrides:
            settings.config_overrides = request.config_overrides

        # Mark as completed
        settings.onboarding_status = OnboardingStatus.COMPLETED

        # Update project
        updated = await self.store.update_settings(request.project_id, settings)

        # Update last analyzed timestamp
        await self.store.update_last_analyzed(request.project_id)

        return updated

    async def refresh_analysis(
        self,
        project_id: str
    ) -> ProjectDetectionResult:
        """
        Re-analyze an existing project.

        Updates detection results while preserving user overrides.

        Args:
            project_id: Project ID

        Returns:
            Updated ProjectDetectionResult
        """
        project = await self.store.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        # Store existing overrides
        existing_settings = project.settings
        existing_overrides = existing_settings.config_overrides if existing_settings else None

        # Re-analyze (force reclone to get latest)
        result = await self.analyze_project(project_id, force_reclone=True)

        # Restore overrides if they existed
        if existing_overrides:
            settings = (await self.store.get_by_id(project_id)).settings
            settings.config_overrides = existing_overrides
            await self.store.update_settings(project_id, settings)

        # Update last analyzed
        await self.store.update_last_analyzed(project_id)

        return result


# Global service instance
project_onboarding_service = ProjectOnboardingService()
