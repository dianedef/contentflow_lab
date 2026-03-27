"""
Status Database - SQLite storage for content lifecycle tracking.

Uses stdlib sqlite3 (zero new dependencies). WAL mode for concurrency.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = os.environ.get(
    "STATUS_DB_PATH",
    str(Path(__file__).parent.parent / "data" / "status" / "status.db"),
)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Create a SQLite connection with WAL mode and row factory.
    """
    path = db_path or DEFAULT_DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """
    Create all tables if they don't exist.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS content_records (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content_type TEXT NOT NULL,
            source_robot TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'todo',
            project_id TEXT,
            content_path TEXT,
            content_preview TEXT,
            content_hash TEXT,
            priority INTEGER NOT NULL DEFAULT 3,
            tags TEXT NOT NULL DEFAULT '[]',
            metadata TEXT NOT NULL DEFAULT '{}',
            target_url TEXT,
            reviewer_note TEXT,
            reviewed_by TEXT,
            current_version INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            scheduled_for TEXT,
            published_at TEXT,
            synced_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_content_status ON content_records(status);
        CREATE INDEX IF NOT EXISTS idx_content_type ON content_records(content_type);
        CREATE INDEX IF NOT EXISTS idx_content_project ON content_records(project_id);
        CREATE INDEX IF NOT EXISTS idx_content_source ON content_records(source_robot);

        CREATE TABLE IF NOT EXISTS status_changes (
            id TEXT PRIMARY KEY,
            content_id TEXT NOT NULL,
            from_status TEXT NOT NULL,
            to_status TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            reason TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (content_id) REFERENCES content_records(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_changes_content ON status_changes(content_id);
        CREATE INDEX IF NOT EXISTS idx_changes_timestamp ON status_changes(timestamp);

        CREATE TABLE IF NOT EXISTS work_domains (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'idle',
            last_run_at TEXT,
            last_run_status TEXT,
            items_pending INTEGER NOT NULL DEFAULT 0,
            items_completed INTEGER NOT NULL DEFAULT 0,
            metadata TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, domain)
        );

        CREATE INDEX IF NOT EXISTS idx_domains_project ON work_domains(project_id);

        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction TEXT NOT NULL,
            records_synced INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL DEFAULT 'running',
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS content_bodies (
            id TEXT PRIMARY KEY,
            content_id TEXT NOT NULL,
            body TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            edited_by TEXT,
            edit_note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (content_id) REFERENCES content_records(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_bodies_content ON content_bodies(content_id);
        CREATE INDEX IF NOT EXISTS idx_bodies_version ON content_bodies(content_id, version);

        CREATE TABLE IF NOT EXISTS content_edits (
            id TEXT PRIMARY KEY,
            content_id TEXT NOT NULL,
            edited_by TEXT NOT NULL,
            edit_note TEXT,
            previous_version INTEGER NOT NULL,
            new_version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (content_id) REFERENCES content_records(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_edits_content ON content_edits(content_id);

        CREATE TABLE IF NOT EXISTS schedule_jobs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            project_id TEXT,
            job_type TEXT NOT NULL,
            generator_id TEXT,
            configuration TEXT NOT NULL DEFAULT '{}',
            schedule TEXT NOT NULL,
            cron_expression TEXT,
            schedule_day INTEGER,
            schedule_time TEXT,
            timezone TEXT NOT NULL DEFAULT 'UTC',
            enabled INTEGER NOT NULL DEFAULT 1,
            last_run_at TEXT,
            last_run_status TEXT,
            next_run_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_enabled ON schedule_jobs(enabled);
        CREATE INDEX IF NOT EXISTS idx_jobs_next_run ON schedule_jobs(next_run_at);

        CREATE TABLE IF NOT EXISTS content_templates (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            project_id TEXT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            content_type TEXT NOT NULL,
            description TEXT,
            is_system INTEGER NOT NULL DEFAULT 0,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_template_user ON content_templates(user_id);
        CREATE INDEX IF NOT EXISTS idx_template_type ON content_templates(content_type);
        CREATE INDEX IF NOT EXISTS idx_template_slug ON content_templates(slug);

        CREATE TABLE IF NOT EXISTS template_sections (
            id TEXT PRIMARY KEY,
            template_id TEXT NOT NULL,
            name TEXT NOT NULL,
            label TEXT NOT NULL,
            field_type TEXT NOT NULL,
            required INTEGER NOT NULL DEFAULT 1,
            "order" INTEGER NOT NULL DEFAULT 0,
            description TEXT,
            placeholder TEXT,
            default_prompt TEXT,
            user_prompt TEXT,
            prompt_strategy TEXT NOT NULL DEFAULT 'auto_generate',
            generation_hints TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (template_id) REFERENCES content_templates(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_section_template ON template_sections(template_id);
        CREATE INDEX IF NOT EXISTS idx_section_order ON template_sections(template_id, "order");

        CREATE TABLE IF NOT EXISTS idea_pool (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            raw_data TEXT NOT NULL DEFAULT '{}',
            seo_signals TEXT,
            trending_signals TEXT,
            tags TEXT NOT NULL DEFAULT '[]',
            priority_score REAL,
            status TEXT NOT NULL DEFAULT 'raw',
            project_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_ideas_source ON idea_pool(source);
        CREATE INDEX IF NOT EXISTS idx_ideas_status ON idea_pool(status);
        CREATE INDEX IF NOT EXISTS idx_ideas_priority ON idea_pool(priority_score);
        CREATE INDEX IF NOT EXISTS idx_ideas_project ON idea_pool(project_id);
        """
    )
    conn.commit()
