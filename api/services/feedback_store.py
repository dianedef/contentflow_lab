"""Persistence layer for user feedback entries."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from utils.libsql_async import create_client


def _ts(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    if isinstance(raw, str):
        try:
            normalized = raw.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
    return datetime.now(tz=timezone.utc)


class FeedbackStore:
    def __init__(self) -> None:
        self.db_client = None
        if os.getenv("TURSO_DATABASE_URL") and os.getenv("TURSO_AUTH_TOKEN"):
            self.db_client = create_client(
                url=os.getenv("TURSO_DATABASE_URL"),
                auth_token=os.getenv("TURSO_AUTH_TOKEN"),
            )

    def _ensure_connected(self) -> None:
        if not self.db_client:
            raise RuntimeError(
                "Database not configured. Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN."
            )

    async def ensure_table(self) -> None:
        self._ensure_connected()
        await self.db_client.execute(
            """
            CREATE TABLE IF NOT EXISTS FeedbackEntry (
                id TEXT PRIMARY KEY NOT NULL,
                type TEXT NOT NULL,
                message TEXT,
                audioStorageId TEXT,
                durationMs INTEGER,
                platform TEXT NOT NULL,
                locale TEXT NOT NULL,
                userId TEXT,
                userEmail TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                createdAt INTEGER NOT NULL,
                reviewedAt INTEGER,
                reviewedByUserId TEXT,
                reviewedByEmail TEXT
            )
            """
        )
        await self.db_client.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_feedback_createdAt
            ON FeedbackEntry(createdAt DESC)
            """
        )
        await self.db_client.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_feedback_status_createdAt
            ON FeedbackEntry(status, createdAt DESC)
            """
        )
        await self.db_client.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_feedback_type_createdAt
            ON FeedbackEntry(type, createdAt DESC)
            """
        )

    def _from_row(self, row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": row[0],
            "type": row[1],
            "message": row[2],
            "audioStorageId": row[3],
            "durationMs": row[4],
            "platform": row[5],
            "locale": row[6],
            "userId": row[7],
            "userEmail": row[8],
            "status": row[9] or "new",
            "createdAt": _ts(row[10]),
            "reviewedAt": _ts(row[11]) if row[11] else None,
            "reviewedByUserId": row[12],
            "reviewedByEmail": row[13],
        }

    async def create_entry(
        self,
        *,
        entry_type: str,
        platform: str,
        locale: str,
        message: str | None = None,
        audio_storage_id: str | None = None,
        duration_ms: int | None = None,
        user_id: str | None = None,
        user_email: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_connected()
        entry_id = str(uuid.uuid4())
        now = int(datetime.now(tz=timezone.utc).timestamp())
        await self.db_client.execute(
            """
            INSERT INTO FeedbackEntry (
                id, type, message, audioStorageId, durationMs, platform,
                locale, userId, userEmail, status, createdAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                entry_id,
                entry_type,
                message,
                audio_storage_id,
                duration_ms,
                platform,
                locale,
                user_id,
                user_email,
                "new",
                now,
            ],
        )
        entry = await self.get_entry(entry_id)
        if not entry:
            raise RuntimeError("Failed to create feedback entry")
        return entry

    async def get_entry(self, entry_id: str) -> dict[str, Any] | None:
        self._ensure_connected()
        rs = await self.db_client.execute(
            """
            SELECT id, type, message, audioStorageId, durationMs, platform,
                   locale, userId, userEmail, status, createdAt,
                   reviewedAt, reviewedByUserId, reviewedByEmail
            FROM FeedbackEntry
            WHERE id = ?
            LIMIT 1
            """,
            [entry_id],
        )
        if not rs.rows:
            return None
        return self._from_row(rs.rows[0])

    async def list_entries(
        self,
        *,
        status: str | None = None,
        entry_type: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        self._ensure_connected()
        query = """
            SELECT id, type, message, audioStorageId, durationMs, platform,
                   locale, userId, userEmail, status, createdAt,
                   reviewedAt, reviewedByUserId, reviewedByEmail
            FROM FeedbackEntry
            WHERE 1 = 1
        """
        params: list[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if entry_type:
            query += " AND type = ?"
            params.append(entry_type)
        query += " ORDER BY createdAt DESC LIMIT ?"
        params.append(limit)
        rs = await self.db_client.execute(query, params)
        return [self._from_row(row) for row in rs.rows]

    async def mark_reviewed(
        self,
        *,
        entry_id: str,
        reviewer_user_id: str,
        reviewer_email: str | None,
    ) -> dict[str, Any] | None:
        self._ensure_connected()
        entry = await self.get_entry(entry_id)
        if not entry:
            return None

        reviewed_at = int(datetime.now(tz=timezone.utc).timestamp())
        await self.db_client.execute(
            """
            UPDATE FeedbackEntry
            SET status = ?, reviewedAt = ?, reviewedByUserId = ?, reviewedByEmail = ?
            WHERE id = ?
            """,
            [
                "reviewed",
                reviewed_at,
                reviewer_user_id,
                reviewer_email,
                entry_id,
            ],
        )
        return await self.get_entry(entry_id)


feedback_store = FeedbackStore()
