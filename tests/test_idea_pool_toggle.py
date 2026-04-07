"""Tests for the ideaPoolEnabled setting and its effect on the article pipeline."""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Model tests ──────────────────────────────────────────


def test_robot_settings_model_accepts_idea_pool():
    from api.models.user_data import RobotSettings

    rs = RobotSettings(ideaPoolEnabled=True)
    assert rs.ideaPoolEnabled is True

    rs2 = RobotSettings(ideaPoolEnabled=False)
    assert rs2.ideaPoolEnabled is False


def test_robot_settings_default_none():
    from api.models.user_data import RobotSettings

    rs = RobotSettings()
    assert rs.ideaPoolEnabled is None


def test_robot_settings_serialization_roundtrip():
    from api.models.user_data import RobotSettings

    rs = RobotSettings(autoRun=True, ideaPoolEnabled=True)
    data = rs.model_dump()
    assert data["ideaPoolEnabled"] is True

    restored = RobotSettings(**data)
    assert restored.ideaPoolEnabled is True


# ─── Scheduler gating tests ──────────────────────────────


@pytest.mark.asyncio
async def test_is_idea_pool_enabled_returns_false_for_system():
    from scheduler.scheduler_service import SchedulerService

    svc = SchedulerService()
    assert await svc._is_idea_pool_enabled({"user_id": "system"}) is False
    assert await svc._is_idea_pool_enabled({}) is False


@pytest.mark.asyncio
async def test_is_idea_pool_enabled_reads_setting():
    from scheduler.scheduler_service import SchedulerService

    svc = SchedulerService()

    mock_settings = {
        "robotSettings": {"ideaPoolEnabled": True},
    }

    with patch(
        "api.services.user_data_store.user_data_store.get_user_settings",
        new_callable=AsyncMock,
        return_value=mock_settings,
    ):
        assert await svc._is_idea_pool_enabled({"user_id": "user_123"}) is True


@pytest.mark.asyncio
async def test_is_idea_pool_enabled_defaults_false_when_missing():
    from scheduler.scheduler_service import SchedulerService

    svc = SchedulerService()

    mock_settings = {"robotSettings": {}}

    with patch(
        "api.services.user_data_store.user_data_store.get_user_settings",
        new_callable=AsyncMock,
        return_value=mock_settings,
    ):
        assert await svc._is_idea_pool_enabled({"user_id": "user_123"}) is False


@pytest.mark.asyncio
async def test_article_job_skips_when_enabled_no_ideas():
    """When ideaPoolEnabled=True and no enriched ideas exist, the job should skip."""
    from scheduler.scheduler_service import SchedulerService

    svc = SchedulerService()
    job = {
        "id": "job_1",
        "job_type": "article",
        "configuration": {},
        "user_id": "user_123",
        "project_id": "proj_1",
    }

    mock_status_svc = MagicMock()
    mock_status_svc.list_ideas.return_value = ([], 0)

    with (
        patch.object(svc, "_is_idea_pool_enabled", new_callable=AsyncMock, return_value=True),
        patch("scheduler.scheduler_service.get_status_service", return_value=mock_status_svc),
    ):
        await svc._run_article_job(job)

    # Should not have called create_content (no content generated)
    mock_status_svc.create_content.assert_not_called()


@pytest.mark.asyncio
async def test_article_job_proceeds_when_disabled_with_angle():
    """When ideaPoolEnabled=False and a config angle is provided, the job should proceed."""
    from scheduler.scheduler_service import SchedulerService

    svc = SchedulerService()
    job = {
        "id": "job_2",
        "job_type": "article",
        "configuration": {
            "angle": {"title": "Test Article", "seo_keyword": "test"},
        },
        "user_id": "user_123",
        "project_id": "proj_1",
    }

    mock_status_svc = MagicMock()
    mock_status_svc.list_ideas.return_value = ([], 0)
    mock_record = MagicMock()
    mock_record.id = "content_1"
    mock_status_svc.create_content.return_value = mock_record

    # Inject a mock SEOContentCrew module so the in-function import succeeds
    mock_crew_cls = MagicMock()
    mock_crew_instance = MagicMock()
    mock_crew_instance.generate_content.return_value = {
        "outputs": {"article": "Generated content body"},
    }
    mock_crew_cls.return_value = mock_crew_instance

    mock_module = MagicMock()
    mock_module.SEOContentCrew = mock_crew_cls
    sys.modules["agents.seo.seo_crew"] = mock_module

    # Mock asyncio.to_thread to call the function synchronously
    async def mock_to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    try:
        with (
            patch.object(svc, "_is_idea_pool_enabled", new_callable=AsyncMock, return_value=False),
            patch("scheduler.scheduler_service.get_status_service", return_value=mock_status_svc),
            patch("scheduler.scheduler_service.asyncio.to_thread", side_effect=mock_to_thread),
        ):
            await svc._run_article_job(job)

        mock_status_svc.create_content.assert_called_once()
    finally:
        sys.modules.pop("agents.seo.seo_crew", None)
