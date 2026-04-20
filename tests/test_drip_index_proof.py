import sys
import types
import sqlite3
from datetime import datetime, timedelta

import pytest

sys.modules.setdefault("libsql", types.SimpleNamespace(connect=lambda **_kwargs: None))


@pytest.fixture
def local_status_service(monkeypatch):
    from status import StatusService
    import status.service as status_service

    def _sqlite_conn(_db_path=None):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(status_service, "get_connection", _sqlite_conn)
    return StatusService()


def _write_md(path, frontmatter: str, body: str = "Hello") -> None:
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def test_drip_schedule_spacing_and_safe_mode(tmp_path, local_status_service):
    from api.services.drip_service import DripService

    svc = DripService(local_status_service)

    content_dir = tmp_path / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    opted_in = content_dir / "a.md"
    opted_out = content_dir / "b.md"

    _write_md(
        opted_in,
        "title: A\n"
        "dripManaged: true\n"
        "draft: false\n"
        "robots: index, follow\n",
    )
    _write_md(
        opted_out,
        "title: B\n"
        "dripManaged: false\n"
        "draft: false\n"
        "robots: index, follow\n",
    )

    start = (datetime.utcnow() + timedelta(days=1)).date().isoformat()

    plan = svc.create_plan(
        name="Test Drip",
        user_id="user-1",
        cadence_config={
            "mode": "fixed",
            "items_per_day": 2,
            "start_date": start,
            "publish_days": [0, 1, 2, 3, 4, 5, 6],
            "publish_time": "06:00",
            "timezone": "UTC",
            "spacing_minutes": 60,
        },
        cluster_strategy={"mode": "directory", "pillar_first": True, "cluster_gap_days": 0},
        ssg_config={
            "framework": "astro",
            "gating_method": "both",
            "rebuild_method": "manual",
            "content_directory": str(content_dir),
            "require_opt_in": True,
            "frontmatter_opt_in_field": "dripManaged",
            "frontmatter_opt_in_value": True,
            "enforce_robots_noindex_until_publish": True,
            "frontmatter_robots_field": "robots",
            "robots_noindex_value": "noindex, follow",
            "robots_index_value": "index, follow",
            "frontmatter_date_field": "pubDate",
            "frontmatter_draft_field": "draft",
        },
        gsc_config=None,
        project_id=None,
    )

    imported = svc.import_from_directory(plan["id"], str(content_dir), exclude_drafts=False)
    assert imported == 2

    svc.cluster_by_directory(plan["id"])
    schedule = svc.generate_schedule(plan["id"], dry_run=False)
    assert len(schedule) == 2

    items = svc.get_plan_items(plan["id"])
    assert len(items) == 2

    by_title = {item.title: item for item in items}
    assert by_title["A"].scheduled_for is not None
    assert by_title["B"].scheduled_for is not None
    assert (by_title["B"].scheduled_for - by_title["A"].scheduled_for).total_seconds() == 3600

    # Opted-in file gets pre-gated.
    from api.services.frontmatter import read_frontmatter

    a_fm = read_frontmatter(str(opted_in))
    assert a_fm.get("draft") is True
    assert a_fm.get("robots") == "noindex, follow"

    # Opted-out file is not mutated in safe mode.
    b_fm = read_frontmatter(str(opted_out))
    assert b_fm.get("draft") is False
    assert b_fm.get("robots") == "index, follow"

    preflight = svc.preflight_plan(plan["id"])
    assert preflight["issue_count"] >= 1


def test_drip_tick_publishes_due_items_only(tmp_path, local_status_service):
    from api.services.drip_service import DripService
    from api.services.frontmatter import read_frontmatter

    svc = DripService(local_status_service)

    content_dir = tmp_path / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    a = content_dir / "a.md"
    b = content_dir / "b.md"

    _write_md(a, "title: A\ndripManaged: true\ndraft: true\nrobots: noindex, follow\n")
    _write_md(b, "title: B\ndripManaged: false\ndraft: true\nrobots: noindex, follow\n")

    start = (datetime.utcnow() + timedelta(days=1)).date().isoformat()

    plan = svc.create_plan(
        name="Tick Test",
        user_id="user-1",
        cadence_config={
            "mode": "fixed",
            "items_per_day": 2,
            "start_date": start,
            "publish_days": [0, 1, 2, 3, 4, 5, 6],
            "publish_time": "06:00",
            "timezone": "UTC",
            "spacing_minutes": 0,
        },
        ssg_config={
            "framework": "astro",
            "gating_method": "both",
            "rebuild_method": "manual",
            "content_directory": str(content_dir),
            "require_opt_in": True,
            "frontmatter_opt_in_field": "dripManaged",
            "frontmatter_opt_in_value": True,
            "enforce_robots_noindex_until_publish": True,
            "frontmatter_robots_field": "robots",
            "robots_index_value": "index, follow",
            "frontmatter_date_field": "pubDate",
            "frontmatter_draft_field": "draft",
        },
    )

    svc.import_from_directory(plan["id"], str(content_dir), exclude_drafts=False)
    svc.generate_schedule(plan["id"], dry_run=False)
    activated = svc.activate_plan(plan["id"])
    assert activated["status"] == "active"

    # Force items to be due.
    items = svc.get_plan_items(plan["id"], status="scheduled")
    assert items
    for item in items:
        local_status_service.update_content(item.id, scheduled_for=datetime.utcnow() - timedelta(minutes=1))

    result = svc.execute_drip_tick(plan["id"])
    assert result["published"] == 1
    assert result["errors"] >= 1  # opted-out item should fail opt-in

    a_fm = read_frontmatter(str(a))
    assert a_fm.get("draft") is False
    assert a_fm.get("robots") == "index, follow"
    assert "pubDate" in a_fm
