"""
Status Service - Singleton service for content lifecycle management.

Provides CRUD operations, status transitions with validation,
audit trail, and statistics.
"""

import json
import uuid
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional

from status.db import get_connection, init_db
from status.schemas import (
    ContentLifecycleStatus,
    ContentRecord,
    StatusChange,
    WorkDomainRecord,
    VALID_TRANSITIONS,
)
from agents.scheduler.schemas.publishing_schemas import ContentType, SourceRobot


class InvalidTransitionError(Exception):
    """Raised when a status transition is not allowed."""
    pass


class ContentNotFoundError(Exception):
    """Raised when a content record is not found."""
    pass


class StatusService:
    """
    Singleton service managing content lifecycle status.
    All robots use this to track content from creation to publication.
    """

    def __init__(self, db_path: Optional[str] = None):
        self._conn = get_connection(db_path)
        init_db(self._conn)

    # ─── Content CRUD ─────────────────────────────────

    def create_content(
        self,
        title: str,
        content_type: str,
        source_robot: str,
        status: str = ContentLifecycleStatus.TODO,
        project_id: Optional[str] = None,
        content_path: Optional[str] = None,
        content_preview: Optional[str] = None,
        content_hash: Optional[str] = None,
        priority: int = 3,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        target_url: Optional[str] = None,
    ) -> ContentRecord:
        """Create a new content record."""
        now = datetime.utcnow().isoformat()
        content_id = str(uuid.uuid4())

        # Validate enum values
        ContentType(content_type)
        SourceRobot(source_robot)
        if isinstance(status, str):
            status = ContentLifecycleStatus(status)

        record = ContentRecord(
            id=content_id,
            title=title,
            content_type=content_type,
            source_robot=source_robot,
            status=status,
            project_id=project_id,
            content_path=content_path,
            content_preview=content_preview,
            content_hash=content_hash,
            priority=priority,
            tags=tags or [],
            metadata=metadata or {},
            target_url=target_url,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self._conn.execute(
            """
            INSERT INTO content_records
            (id, title, content_type, source_robot, status, project_id,
             content_path, content_preview, content_hash, priority, tags,
             metadata, target_url, current_version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.title,
                record.content_type,
                record.source_robot,
                record.status,
                record.project_id,
                record.content_path,
                record.content_preview,
                record.content_hash,
                record.priority,
                json.dumps(record.tags),
                json.dumps(record.metadata),
                record.target_url,
                record.current_version,
                now,
                now,
            ),
        )
        self._conn.commit()
        return record

    def get_content(self, content_id: str) -> ContentRecord:
        """Get a single content record by ID."""
        row = self._conn.execute(
            "SELECT * FROM content_records WHERE id = ?", (content_id,)
        ).fetchone()

        if not row:
            raise ContentNotFoundError(f"Content {content_id} not found")

        return self._row_to_record(row)

    def update_content(self, content_id: str, **kwargs: Any) -> ContentRecord:
        """Update content record fields (not status - use transition() for that)."""
        # Ensure record exists
        self.get_content(content_id)

        allowed_fields = {
            "title", "content_path", "content_preview", "content_hash",
            "priority", "tags", "metadata", "target_url", "project_id",
            "reviewer_note", "reviewed_by", "scheduled_for", "published_at",
            "current_version",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return self.get_content(content_id)

        # Serialize complex types
        if "tags" in updates:
            updates["tags"] = json.dumps(updates["tags"])
        if "metadata" in updates:
            updates["metadata"] = json.dumps(updates["metadata"])
        if "scheduled_for" in updates and isinstance(updates["scheduled_for"], datetime):
            updates["scheduled_for"] = updates["scheduled_for"].isoformat()
        if "published_at" in updates and isinstance(updates["published_at"], datetime):
            updates["published_at"] = updates["published_at"].isoformat()

        updates["updated_at"] = datetime.utcnow().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [content_id]

        self._conn.execute(
            f"UPDATE content_records SET {set_clause} WHERE id = ?",
            values,
        )
        self._conn.commit()
        return self.get_content(content_id)

    def list_content(
        self,
        status: Optional[str] = None,
        content_type: Optional[str] = None,
        source_robot: Optional[str] = None,
        project_id: Optional[str] = None,
        project_ids: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ContentRecord]:
        """List content records with optional filters."""
        query = "SELECT * FROM content_records WHERE 1=1"
        params: List[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if content_type:
            query += " AND content_type = ?"
            params.append(content_type)
        if source_robot:
            query += " AND source_robot = ?"
            params.append(source_robot)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        elif project_ids is not None:
            if not project_ids:
                return []
            placeholders = ", ".join("?" for _ in project_ids)
            query += f" AND project_id IN ({placeholders})"
            params.extend(project_ids)

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def delete_content(self, content_id: str) -> None:
        """Delete a content record and its history."""
        self.get_content(content_id)  # Ensure exists
        self._conn.execute("DELETE FROM content_records WHERE id = ?", (content_id,))
        self._conn.commit()

    # ─── Status Transitions ───────────────────────────

    def transition(
        self,
        content_id: str,
        to_status: str,
        changed_by: str,
        reason: Optional[str] = None,
    ) -> ContentRecord:
        """
        Transition a content record to a new status.
        Validates the transition against the allowed matrix.
        Creates an audit trail entry.
        """
        record = self.get_content(content_id)
        from_status = ContentLifecycleStatus(record.status)
        to_status_enum = ContentLifecycleStatus(to_status)

        # Validate transition
        allowed = VALID_TRANSITIONS.get(from_status, [])
        if to_status_enum not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition from '{from_status.value}' to '{to_status_enum.value}'. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        now = datetime.utcnow().isoformat()
        change_id = str(uuid.uuid4())

        # Update status
        update_fields = {"status": to_status_enum.value, "updated_at": now}

        # Auto-set published_at when transitioning to PUBLISHED
        if to_status_enum == ContentLifecycleStatus.PUBLISHED:
            update_fields["published_at"] = now

        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        values = list(update_fields.values()) + [content_id]
        self._conn.execute(
            f"UPDATE content_records SET {set_clause} WHERE id = ?",
            values,
        )

        # Record the change
        self._conn.execute(
            """
            INSERT INTO status_changes (id, content_id, from_status, to_status, changed_by, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (change_id, content_id, from_status.value, to_status_enum.value, changed_by, reason, now),
        )

        self._conn.commit()
        return self.get_content(content_id)

    def get_history(self, content_id: str) -> List[StatusChange]:
        """Get the full audit trail for a content record."""
        rows = self._conn.execute(
            "SELECT * FROM status_changes WHERE content_id = ? ORDER BY timestamp ASC",
            (content_id,),
        ).fetchall()

        return [
            StatusChange(
                id=row["id"],
                content_id=row["content_id"],
                from_status=row["from_status"],
                to_status=row["to_status"],
                changed_by=row["changed_by"],
                reason=row["reason"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
            for row in rows
        ]

    # ─── Statistics ───────────────────────────────────

    def get_stats(
        self,
        project_id: Optional[str] = None,
        project_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get content counts grouped by status."""
        query = "SELECT status, COUNT(*) as count FROM content_records"
        params: List[Any] = []

        if project_id:
            query += " WHERE project_id = ?"
            params.append(project_id)
        elif project_ids is not None:
            if not project_ids:
                counts = {s.value: 0 for s in ContentLifecycleStatus}
                return {"total": 0, "by_status": counts}
            placeholders = ", ".join("?" for _ in project_ids)
            query += f" WHERE project_id IN ({placeholders})"
            params.extend(project_ids)

        query += " GROUP BY status"
        rows = self._conn.execute(query, params).fetchall()

        counts = {s.value: 0 for s in ContentLifecycleStatus}
        for row in rows:
            counts[row["status"]] = row["count"]

        total = sum(counts.values())
        return {"total": total, "by_status": counts}

    # ─── Work Domains ─────────────────────────────────

    def get_domains(
        self,
        project_id: Optional[str] = None,
        project_ids: Optional[List[str]] = None,
    ) -> List[WorkDomainRecord]:
        """Get work domain records, optionally filtered by project."""
        query = "SELECT * FROM work_domains"
        params: List[Any] = []

        if project_id:
            query += " WHERE project_id = ?"
            params.append(project_id)
        elif project_ids is not None:
            if not project_ids:
                return []
            placeholders = ", ".join("?" for _ in project_ids)
            query += f" WHERE project_id IN ({placeholders})"
            params.extend(project_ids)

        query += " ORDER BY domain ASC"
        rows = self._conn.execute(query, params).fetchall()

        return [
            WorkDomainRecord(
                id=row["id"],
                project_id=row["project_id"],
                domain=row["domain"],
                status=row["status"],
                last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
                last_run_status=row["last_run_status"],
                items_pending=row["items_pending"],
                items_completed=row["items_completed"],
                metadata=json.loads(row["metadata"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    def upsert_domain(
        self,
        project_id: str,
        domain: str,
        **kwargs: Any,
    ) -> WorkDomainRecord:
        """Create or update a work domain record."""
        now = datetime.utcnow().isoformat()

        existing = self._conn.execute(
            "SELECT * FROM work_domains WHERE project_id = ? AND domain = ?",
            (project_id, domain),
        ).fetchone()

        if existing:
            updates = {k: v for k, v in kwargs.items() if k in {
                "status", "last_run_at", "last_run_status",
                "items_pending", "items_completed", "metadata",
            }}
            if "metadata" in updates:
                updates["metadata"] = json.dumps(updates["metadata"])
            if "last_run_at" in updates and isinstance(updates["last_run_at"], datetime):
                updates["last_run_at"] = updates["last_run_at"].isoformat()
            updates["updated_at"] = now

            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [project_id, domain]
            self._conn.execute(
                f"UPDATE work_domains SET {set_clause} WHERE project_id = ? AND domain = ?",
                values,
            )
        else:
            domain_id = str(uuid.uuid4())
            metadata = kwargs.get("metadata", {})
            self._conn.execute(
                """
                INSERT INTO work_domains
                (id, project_id, domain, status, last_run_at, last_run_status,
                 items_pending, items_completed, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    domain_id,
                    project_id,
                    domain,
                    kwargs.get("status", "idle"),
                    kwargs.get("last_run_at", "").isoformat() if isinstance(kwargs.get("last_run_at"), datetime) else kwargs.get("last_run_at"),
                    kwargs.get("last_run_status"),
                    kwargs.get("items_pending", 0),
                    kwargs.get("items_completed", 0),
                    json.dumps(metadata),
                    now,
                ),
            )

        self._conn.commit()
        result = self._conn.execute(
            "SELECT * FROM work_domains WHERE project_id = ? AND domain = ?",
            (project_id, domain),
        ).fetchone()
        return WorkDomainRecord(
            id=result["id"],
            project_id=result["project_id"],
            domain=result["domain"],
            status=result["status"],
            last_run_at=datetime.fromisoformat(result["last_run_at"]) if result["last_run_at"] else None,
            last_run_status=result["last_run_status"],
            items_pending=result["items_pending"],
            items_completed=result["items_completed"],
            metadata=json.loads(result["metadata"]),
            updated_at=datetime.fromisoformat(result["updated_at"]),
        )

    # ─── Content Body ─────────────────────────────────

    def save_content_body(
        self,
        content_id: str,
        body: str,
        edited_by: str = "user",
        edit_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save a new version of content body. Creates version history."""
        record = self.get_content(content_id)
        previous_version = record.current_version
        new_version = previous_version + 1
        now = datetime.utcnow().isoformat()
        body_id = str(uuid.uuid4())
        edit_id = str(uuid.uuid4())

        # Insert new body version
        self._conn.execute(
            """
            INSERT INTO content_bodies (id, content_id, body, version, edited_by, edit_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (body_id, content_id, body, new_version, edited_by, edit_note, now),
        )

        # Insert edit audit entry
        self._conn.execute(
            """
            INSERT INTO content_edits (id, content_id, edited_by, edit_note, previous_version, new_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (edit_id, content_id, edited_by, edit_note, previous_version, new_version, now),
        )

        # Update current_version on content record
        self._conn.execute(
            "UPDATE content_records SET current_version = ?, updated_at = ? WHERE id = ?",
            (new_version, now, content_id),
        )
        self._conn.commit()

        return {
            "id": body_id,
            "content_id": content_id,
            "version": new_version,
            "edited_by": edited_by,
            "edit_note": edit_note,
            "created_at": now,
        }

    def get_content_body(
        self,
        content_id: str,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get content body, latest version or specific version."""
        self.get_content(content_id)  # Ensure exists

        if version is not None:
            row = self._conn.execute(
                "SELECT * FROM content_bodies WHERE content_id = ? AND version = ?",
                (content_id, version),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM content_bodies WHERE content_id = ? ORDER BY version DESC LIMIT 1",
                (content_id,),
            ).fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "content_id": row["content_id"],
            "body": row["body"],
            "version": row["version"],
            "edited_by": row["edited_by"],
            "edit_note": row["edit_note"],
            "created_at": row["created_at"],
        }

    def get_edit_history(self, content_id: str) -> List[Dict[str, Any]]:
        """Get edit history for a content record."""
        self.get_content(content_id)  # Ensure exists

        rows = self._conn.execute(
            "SELECT * FROM content_edits WHERE content_id = ? ORDER BY created_at DESC",
            (content_id,),
        ).fetchall()

        return [
            {
                "id": row["id"],
                "content_id": row["content_id"],
                "edited_by": row["edited_by"],
                "edit_note": row["edit_note"],
                "previous_version": row["previous_version"],
                "new_version": row["new_version"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    # ─── Schedule Jobs ────────────────────────────────

    def create_schedule_job(self, **kwargs: Any) -> Dict[str, Any]:
        """Create a new schedule job."""
        now = datetime.utcnow().isoformat()
        job_id = str(uuid.uuid4())

        self._conn.execute(
            """
            INSERT INTO schedule_jobs
            (id, user_id, project_id, job_type, generator_id, configuration,
             schedule, cron_expression, schedule_day, schedule_time, timezone,
             enabled, next_run_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                kwargs.get("user_id", "system"),
                kwargs.get("project_id"),
                kwargs["job_type"],
                kwargs.get("generator_id"),
                json.dumps(kwargs.get("configuration", {})),
                kwargs["schedule"],
                kwargs.get("cron_expression"),
                kwargs.get("schedule_day"),
                kwargs.get("schedule_time"),
                kwargs.get("timezone", "UTC"),
                1 if kwargs.get("enabled", True) else 0,
                kwargs.get("next_run_at"),
                now,
                now,
            ),
        )
        self._conn.commit()

        return self.get_schedule_job(job_id)

    def get_schedule_job(self, job_id: str) -> Dict[str, Any]:
        """Get a schedule job by ID."""
        row = self._conn.execute(
            "SELECT * FROM schedule_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if not row:
            raise ContentNotFoundError(f"Schedule job {job_id} not found")
        return self._row_to_job(row)

    def list_schedule_jobs(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """List schedule jobs with optional filters."""
        query = "SELECT * FROM schedule_jobs WHERE 1=1"
        params: List[Any] = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if enabled_only:
            query += " AND enabled = 1"

        query += " ORDER BY created_at DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_job(row) for row in rows]

    def update_schedule_job(self, job_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Update a schedule job."""
        self.get_schedule_job(job_id)  # Ensure exists
        now = datetime.utcnow().isoformat()

        allowed = {
            "project_id", "job_type", "generator_id", "configuration",
            "schedule", "cron_expression", "schedule_day", "schedule_time",
            "timezone", "enabled", "last_run_at", "last_run_status", "next_run_at",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_schedule_job(job_id)

        if "configuration" in updates:
            updates["configuration"] = json.dumps(updates["configuration"])
        if "enabled" in updates:
            updates["enabled"] = 1 if updates["enabled"] else 0

        updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [job_id]

        self._conn.execute(
            f"UPDATE schedule_jobs SET {set_clause} WHERE id = ?", values
        )
        self._conn.commit()
        return self.get_schedule_job(job_id)

    def delete_schedule_job(self, job_id: str) -> None:
        """Delete a schedule job."""
        self.get_schedule_job(job_id)  # Ensure exists
        self._conn.execute("DELETE FROM schedule_jobs WHERE id = ?", (job_id,))
        self._conn.commit()

    def get_due_jobs(self) -> List[Dict[str, Any]]:
        """Get jobs that are due to run (next_run_at <= now and enabled)."""
        now = datetime.utcnow().isoformat()
        rows = self._conn.execute(
            "SELECT * FROM schedule_jobs WHERE enabled = 1 AND next_run_at IS NOT NULL AND next_run_at <= ?",
            (now,),
        ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def _row_to_job(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a schedule job dict."""
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "project_id": row["project_id"],
            "job_type": row["job_type"],
            "generator_id": row["generator_id"],
            "configuration": json.loads(row["configuration"]) if row["configuration"] else {},
            "schedule": row["schedule"],
            "cron_expression": row["cron_expression"],
            "schedule_day": row["schedule_day"],
            "schedule_time": row["schedule_time"],
            "timezone": row["timezone"],
            "enabled": bool(row["enabled"]),
            "last_run_at": row["last_run_at"],
            "last_run_status": row["last_run_status"],
            "next_run_at": row["next_run_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ─── Sync Helpers ─────────────────────────────────

    def get_unsynced_records(self) -> List[ContentRecord]:
        """Get records where synced_at is NULL or older than updated_at."""
        rows = self._conn.execute(
            """
            SELECT * FROM content_records
            WHERE synced_at IS NULL OR synced_at < updated_at
            ORDER BY updated_at ASC
            """,
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def mark_synced(self, content_id: str) -> None:
        """Mark a content record as synced."""
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            "UPDATE content_records SET synced_at = ? WHERE id = ?",
            (now, content_id),
        )
        self._conn.commit()

    # ─── Private Helpers ──────────────────────────────

    def _row_to_record(self, row: sqlite3.Row) -> ContentRecord:
        """Convert a database row to a ContentRecord."""
        # Handle current_version column (may not exist in older DBs)
        try:
            current_version = row["current_version"]
        except (IndexError, KeyError):
            current_version = 0

        return ContentRecord(
            id=row["id"],
            title=row["title"],
            content_type=row["content_type"],
            source_robot=row["source_robot"],
            status=row["status"],
            project_id=row["project_id"],
            content_path=row["content_path"],
            content_preview=row["content_preview"],
            content_hash=row["content_hash"],
            priority=row["priority"],
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            target_url=row["target_url"],
            reviewer_note=row["reviewer_note"],
            reviewed_by=row["reviewed_by"],
            current_version=current_version,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            scheduled_for=datetime.fromisoformat(row["scheduled_for"]) if row["scheduled_for"] else None,
            published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
            synced_at=datetime.fromisoformat(row["synced_at"]) if row["synced_at"] else None,
        )


    # ─── Idea Pool CRUD ──────────────────────────────────

    def create_idea(
        self,
        source: str,
        title: str,
        raw_data: Optional[Dict[str, Any]] = None,
        seo_signals: Optional[Dict[str, Any]] = None,
        trending_signals: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        priority_score: Optional[float] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new idea in the pool."""
        now = datetime.utcnow().isoformat()
        idea_id = str(uuid.uuid4())

        self._conn.execute(
            """INSERT INTO idea_pool
               (id, source, title, raw_data, seo_signals, trending_signals,
                tags, priority_score, status, project_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'raw', ?, ?, ?)""",
            (
                idea_id,
                source,
                title,
                json.dumps(raw_data or {}),
                json.dumps(seo_signals) if seo_signals else None,
                json.dumps(trending_signals) if trending_signals else None,
                json.dumps(tags or []),
                priority_score,
                project_id,
                now,
                now,
            ),
        )
        self._conn.commit()
        return self.get_idea(idea_id)

    def get_idea(self, idea_id: str) -> Dict[str, Any]:
        """Get a single idea by ID."""
        row = self._conn.execute(
            "SELECT * FROM idea_pool WHERE id = ?", (idea_id,)
        ).fetchone()
        if not row:
            raise ContentNotFoundError(f"Idea {idea_id} not found")
        return self._idea_from_row(row)

    def list_ideas(
        self,
        source: Optional[str] = None,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
        project_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Dict[str, Any]], int]:
        """List ideas with optional filters. Returns (items, total)."""
        conditions = []
        params: list = []

        if source:
            conditions.append("source = ?")
            params.append(source)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if min_score is not None:
            conditions.append("priority_score >= ?")
            params.append(min_score)
        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        total = self._conn.execute(
            f"SELECT COUNT(*) FROM idea_pool {where}", params
        ).fetchone()[0]

        rows = self._conn.execute(
            f"""SELECT * FROM idea_pool {where}
                ORDER BY COALESCE(priority_score, 0) DESC, created_at DESC
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()

        return [self._idea_from_row(r) for r in rows], total

    def update_idea(self, idea_id: str, **kwargs) -> Dict[str, Any]:
        """Update an idea's fields."""
        allowed = {
            "title", "seo_signals", "trending_signals", "tags",
            "priority_score", "status", "project_id",
        }
        updates = []
        params = []
        for key, value in kwargs.items():
            if key not in allowed:
                continue
            if key in ("seo_signals", "trending_signals"):
                updates.append(f"{key} = ?")
                params.append(json.dumps(value) if value is not None else None)
            elif key == "tags":
                updates.append(f"{key} = ?")
                params.append(json.dumps(value or []))
            else:
                updates.append(f"{key} = ?")
                params.append(value)

        if not updates:
            return self.get_idea(idea_id)

        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(idea_id)

        self._conn.execute(
            f"UPDATE idea_pool SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        self._conn.commit()
        return self.get_idea(idea_id)

    def delete_idea(self, idea_id: str) -> None:
        """Delete an idea."""
        self._conn.execute("DELETE FROM idea_pool WHERE id = ?", (idea_id,))
        self._conn.commit()

    def bulk_create_ideas(
        self,
        source: str,
        items: List[Dict[str, Any]],
        project_id: Optional[str] = None,
    ) -> int:
        """Bulk insert ideas. Returns count created."""
        now = datetime.utcnow().isoformat()
        count = 0
        for item in items:
            title = item.get("title", "").strip()
            if not title:
                continue
            self._conn.execute(
                """INSERT INTO idea_pool
                   (id, source, title, raw_data, seo_signals, trending_signals,
                    tags, priority_score, status, project_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'raw', ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    source,
                    title,
                    json.dumps(item.get("raw_data", {})),
                    json.dumps(item["seo_signals"]) if item.get("seo_signals") else None,
                    json.dumps(item["trending_signals"]) if item.get("trending_signals") else None,
                    json.dumps(item.get("tags", [])),
                    item.get("priority_score"),
                    project_id,
                    now,
                    now,
                ),
            )
            count += 1
        self._conn.commit()
        return count

    def _idea_from_row(self, row) -> Dict[str, Any]:
        """Convert a database row to an idea dict."""
        return {
            "id": row["id"],
            "source": row["source"],
            "title": row["title"],
            "raw_data": json.loads(row["raw_data"]),
            "seo_signals": json.loads(row["seo_signals"]) if row["seo_signals"] else None,
            "trending_signals": json.loads(row["trending_signals"]) if row["trending_signals"] else None,
            "tags": json.loads(row["tags"]),
            "priority_score": row["priority_score"],
            "status": row["status"],
            "project_id": row["project_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


# ─── Singleton ────────────────────────────────────────

_service_instance: Optional[StatusService] = None


def get_status_service(db_path: Optional[str] = None) -> StatusService:
    """Get or create the singleton StatusService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = StatusService(db_path)
    return _service_instance
