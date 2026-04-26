import importlib.util
import sys
import types
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from api.models.project import OnboardProjectRequest, OnboardingStatus, Project, ProjectSettings


_PROJECTS_ROUTER_PATH = Path(__file__).resolve().parent.parent / "api" / "routers" / "projects.py"


def _load_projects_router_module(*, project_store_stub: object, user_data_store_stub: object):
    sys.modules["agents.scheduler.tools.content_scanner"] = types.SimpleNamespace(
        get_content_scanner=lambda: None
    )
    sys.modules["agents.scheduler.tools.cluster_scheduler"] = types.SimpleNamespace(
        get_cluster_scheduler=lambda: None
    )
    sys.modules["agents.seo.services.project_onboarding"] = types.SimpleNamespace(
        project_onboarding_service=None
    )
    project_store_module = types.SimpleNamespace(project_store=project_store_stub)
    sys.modules["agents.seo.config.project_store"] = project_store_module
    agents_seo_config_pkg = types.ModuleType("agents.seo.config")
    agents_seo_config_pkg.project_store = project_store_module
    sys.modules["agents.seo.config"] = agents_seo_config_pkg

    user_data_module = types.SimpleNamespace(user_data_store=user_data_store_stub)
    sys.modules["api.services.user_data_store"] = user_data_module
    api_services_pkg = types.ModuleType("api.services")
    api_services_pkg.user_data_store = user_data_module
    sys.modules["api.services"] = api_services_pkg

    sys.modules["api.dependencies.auth"] = types.SimpleNamespace(
        CurrentUser=object,
        require_current_user=lambda: None,
    )
    sys.modules.pop("contentflow_lab_projects_router", None)

    spec = importlib.util.spec_from_file_location("contentflow_lab_projects_router", _PROJECTS_ROUTER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_create_project_marks_onboarding_complete_and_sets_default(monkeypatch):
    project = Project(
        id="project-1",
        user_id="user-1",
        name="Project 1",
        url="https://github.com/acme/project-1",
        settings=ProjectSettings(onboarding_status=OnboardingStatus.PENDING),
        created_at=datetime.now(),
    )
    completed_project = project.model_copy(
        update={
            "settings": project.settings.model_copy(update={"onboarding_status": OnboardingStatus.COMPLETED}),
        },
    )

    project_store_stub = SimpleNamespace(
        create=AsyncMock(return_value=project),
        update_onboarding_status=AsyncMock(return_value=completed_project),
        get_by_id=AsyncMock(return_value=completed_project),
    )
    user_data_store_stub = SimpleNamespace(
        get_user_settings=AsyncMock(return_value={}),
        update_user_settings=AsyncMock(),
    )

    router = _load_projects_router_module(
        project_store_stub=project_store_stub,
        user_data_store_stub=user_data_store_stub,
    )

    user = SimpleNamespace(user_id="user-1", email="user@example.com")
    request = OnboardProjectRequest(github_url="https://github.com/acme/project-1")

    response = await router.create_project(request=request, current_user=user)

    assert response.id == "project-1"
    assert response.settings is not None
    assert response.settings.onboarding_status == OnboardingStatus.COMPLETED
    assert response.is_default is True
    user_data_store_stub.update_user_settings.assert_awaited_once_with(
        "user-1",
        {"defaultProjectId": "project-1", "projectSelectionMode": "selected"},
    )


@pytest.mark.asyncio
async def test_create_project_accepts_empty_source_url_and_marks_manual_type():
    project = Project(
        id="project-2",
        user_id="user-1",
        name="Manual project",
        url="",
        type="manual",
        settings=ProjectSettings(onboarding_status=OnboardingStatus.PENDING),
        created_at=datetime.now(),
    )
    completed_project = project.model_copy(
        update={
            "settings": project.settings.model_copy(update={"onboarding_status": OnboardingStatus.COMPLETED}),
        },
    )

    project_store_stub = SimpleNamespace(
        create=AsyncMock(return_value=project),
        update_onboarding_status=AsyncMock(return_value=completed_project),
        get_by_id=AsyncMock(return_value=completed_project),
    )
    user_data_store_stub = SimpleNamespace(
        get_user_settings=AsyncMock(return_value={}),
        update_user_settings=AsyncMock(),
    )

    router = _load_projects_router_module(
        project_store_stub=project_store_stub,
        user_data_store_stub=user_data_store_stub,
    )

    user = SimpleNamespace(user_id="user-1", email="user@example.com")
    request = OnboardProjectRequest(name="Manual project", source_url="")

    response = await router.create_project(request=request, current_user=user)

    assert response.url == ""
    assert response.type == "manual"
    project_store_stub.create.assert_awaited_once_with(
        user_id="user-1",
        name="Manual project",
        url="",
        project_type="manual",
        description=None,
    )


@pytest.mark.asyncio
async def test_create_project_accepts_non_github_website_url():
    project = Project(
        id="project-3",
        user_id="user-1",
        name="example.com",
        url="https://example.com",
        type="website",
        settings=ProjectSettings(onboarding_status=OnboardingStatus.PENDING),
        created_at=datetime.now(),
    )
    completed_project = project.model_copy(
        update={
            "settings": project.settings.model_copy(update={"onboarding_status": OnboardingStatus.COMPLETED}),
        },
    )

    project_store_stub = SimpleNamespace(
        create=AsyncMock(return_value=project),
        update_onboarding_status=AsyncMock(return_value=completed_project),
        get_by_id=AsyncMock(return_value=completed_project),
    )
    user_data_store_stub = SimpleNamespace(
        get_user_settings=AsyncMock(return_value={}),
        update_user_settings=AsyncMock(),
    )

    router = _load_projects_router_module(
        project_store_stub=project_store_stub,
        user_data_store_stub=user_data_store_stub,
    )

    user = SimpleNamespace(user_id="user-1", email="user@example.com")
    request = OnboardProjectRequest(source_url="https://example.com")

    response = await router.create_project(request=request, current_user=user)

    assert response.url == "https://example.com"
    assert response.type == "website"
    project_store_stub.create.assert_awaited_once_with(
        user_id="user-1",
        name="example.com",
        url="https://example.com",
        project_type="website",
        description=None,
    )


@pytest.mark.asyncio
async def test_create_project_treats_non_github_host_with_github_query_as_website():
    source_url = "https://example.com/landing?next=https://github.com/acme/project-3"
    explicit_name = "Website source"
    project = Project(
        id="project-4",
        user_id="user-1",
        name=explicit_name,
        url=source_url,
        type="website",
        settings=ProjectSettings(onboarding_status=OnboardingStatus.PENDING),
        created_at=datetime.now(),
    )
    completed_project = project.model_copy(
        update={
            "settings": project.settings.model_copy(update={"onboarding_status": OnboardingStatus.COMPLETED}),
        },
    )

    project_store_stub = SimpleNamespace(
        create=AsyncMock(return_value=project),
        update_onboarding_status=AsyncMock(return_value=completed_project),
        get_by_id=AsyncMock(return_value=completed_project),
    )
    user_data_store_stub = SimpleNamespace(
        get_user_settings=AsyncMock(return_value={}),
        update_user_settings=AsyncMock(),
    )

    router = _load_projects_router_module(
        project_store_stub=project_store_stub,
        user_data_store_stub=user_data_store_stub,
    )

    user = SimpleNamespace(user_id="user-1", email="user@example.com")
    request = OnboardProjectRequest(name=explicit_name, source_url=source_url)

    response = await router.create_project(request=request, current_user=user)

    assert response.type == "website"
    project_store_stub.create.assert_awaited_once_with(
        user_id="user-1",
        name=explicit_name,
        url=source_url,
        project_type="website",
        description=None,
    )


@pytest.mark.asyncio
async def test_archive_project_returns_403_for_non_owner():
    project = Project(
        id="project-5",
        user_id="user-2",
        name="Project 5",
        url="https://example.com",
        type="website",
        settings=ProjectSettings(onboarding_status=OnboardingStatus.COMPLETED),
        created_at=datetime.now(),
    )

    project_store_stub = SimpleNamespace(
        get_by_id=AsyncMock(return_value=project),
        archive=AsyncMock(),
        get_by_user=AsyncMock(return_value=[]),
    )
    user_data_store_stub = SimpleNamespace(
        get_user_settings=AsyncMock(return_value={}),
        update_user_settings=AsyncMock(),
    )
    router = _load_projects_router_module(
        project_store_stub=project_store_stub,
        user_data_store_stub=user_data_store_stub,
    )

    user = SimpleNamespace(user_id="user-1", email="user@example.com")

    with pytest.raises(HTTPException) as exc_info:
        await router.archive_project(project_id="project-5", current_user=user)

    assert exc_info.value.status_code == 403
    project_store_stub.archive.assert_not_awaited()


@pytest.mark.asyncio
async def test_archive_project_clears_selected_default_when_archiving_selected_project():
    project = Project(
        id="project-6",
        user_id="user-1",
        name="Project 6",
        url="https://example.com",
        type="website",
        settings=ProjectSettings(onboarding_status=OnboardingStatus.COMPLETED),
        created_at=datetime.now(),
    )
    archived_project = project.model_copy(update={"archived_at": datetime.now()})

    project_store_stub = SimpleNamespace(
        get_by_id=AsyncMock(return_value=project),
        archive=AsyncMock(return_value=archived_project),
        get_by_user=AsyncMock(return_value=[archived_project]),
    )
    user_data_store_stub = SimpleNamespace(
        get_user_settings=AsyncMock(
            return_value={"defaultProjectId": "project-6", "projectSelectionMode": "selected"}
        ),
        update_user_settings=AsyncMock(),
    )
    router = _load_projects_router_module(
        project_store_stub=project_store_stub,
        user_data_store_stub=user_data_store_stub,
    )

    user = SimpleNamespace(user_id="user-1", email="user@example.com")
    response = await router.archive_project(project_id="project-6", current_user=user)

    assert response.id == "project-6"
    assert response.is_archived is True
    assert response.is_default is False
    user_data_store_stub.update_user_settings.assert_awaited_once_with(
        "user-1",
        {"defaultProjectId": None, "projectSelectionMode": "none"},
    )


@pytest.mark.asyncio
async def test_unarchive_project_restores_project_and_keeps_selected_default():
    archived_project = Project(
        id="project-7",
        user_id="user-1",
        name="Project 7",
        url="https://example.com",
        type="website",
        archived_at=datetime.now(),
        settings=ProjectSettings(onboarding_status=OnboardingStatus.COMPLETED),
        created_at=datetime.now(),
    )
    restored_project = archived_project.model_copy(update={"archived_at": None})

    project_store_stub = SimpleNamespace(
        get_by_id=AsyncMock(return_value=archived_project),
        unarchive=AsyncMock(return_value=restored_project),
        get_by_user=AsyncMock(return_value=[restored_project]),
    )
    user_data_store_stub = SimpleNamespace(
        get_user_settings=AsyncMock(
            return_value={"defaultProjectId": "project-7", "projectSelectionMode": "selected"}
        ),
        update_user_settings=AsyncMock(),
    )
    router = _load_projects_router_module(
        project_store_stub=project_store_stub,
        user_data_store_stub=user_data_store_stub,
    )

    user = SimpleNamespace(user_id="user-1", email="user@example.com")
    response = await router.unarchive_project(project_id="project-7", current_user=user)

    assert response.id == "project-7"
    assert response.is_archived is False
    assert response.is_default is True
