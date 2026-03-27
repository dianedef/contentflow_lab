"""DB-backed store for authenticated user data migrated out of Next.js."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any

import libsql_client


def _ts(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw)
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return datetime.fromtimestamp(float(raw))
    return datetime.now()


def _json_load(raw: Any, fallback: Any) -> Any:
    if raw is None:
        return fallback
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return fallback


def _json_dump(raw: Any) -> str | None:
    if raw is None:
        return None
    return json.dumps(raw)


def _mask_api_keys(api_keys: dict[str, Any] | None) -> dict[str, Any] | None:
    if not api_keys:
        return None
    safe: dict[str, Any] = {}
    for key, value in api_keys.items():
        if key == "posthogHost":
            safe[key] = value
        else:
            safe[key] = "••••••••" if value else None
    return safe


class UserDataStore:
    """Small repository layer for user-owned app data."""

    def __init__(self) -> None:
        self.db_client = None
        if os.getenv("TURSO_DATABASE_URL") and os.getenv("TURSO_AUTH_TOKEN"):
            self.db_client = libsql_client.create_client(
                url=os.getenv("TURSO_DATABASE_URL"),
                auth_token=os.getenv("TURSO_AUTH_TOKEN"),
            )

    def _ensure_connected(self) -> None:
        if not self.db_client:
            raise RuntimeError(
                "Database not configured. Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN."
            )

    def _settings_from_row(self, row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": row[0],
            "userId": row[1],
            "theme": row[2],
            "language": row[3],
            "emailNotifications": bool(row[4]),
            "webhookUrl": row[5],
            "apiKeys": _mask_api_keys(_json_load(row[6], None)),
            "defaultProjectId": row[7],
            "dashboardLayout": _json_load(row[8], None),
            "robotSettings": _json_load(row[9], None),
            "createdAt": _ts(row[10]),
            "updatedAt": _ts(row[11]),
        }

    def _creator_profile_from_row(self, row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": row[0],
            "userId": row[1],
            "projectId": row[2],
            "displayName": row[3],
            "voice": _json_load(row[4], None),
            "positioning": _json_load(row[5], None),
            "values": _json_load(row[6], []),
            "currentChapterId": row[7],
            "createdAt": _ts(row[8]),
            "updatedAt": _ts(row[9]),
        }

    def _persona_from_row(self, row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": row[0],
            "userId": row[1],
            "projectId": row[2],
            "name": row[3],
            "avatar": row[4],
            "demographics": _json_load(row[5], None),
            "painPoints": _json_load(row[6], []),
            "goals": _json_load(row[7], []),
            "language": _json_load(row[8], None),
            "contentPreferences": _json_load(row[9], None),
            "confidence": row[10] or 50,
            "createdAt": _ts(row[11]),
            "updatedAt": _ts(row[12]),
        }

    async def get_user_settings(self, user_id: str) -> dict[str, Any]:
        self._ensure_connected()
        rs = await self.db_client.execute(
            """
            SELECT id, userId, theme, language, emailNotifications, webhookUrl,
                   apiKeys, defaultProjectId, dashboardLayout, robotSettings,
                   createdAt, updatedAt
            FROM UserSettings
            WHERE userId = ?
            LIMIT 1
            """,
            [user_id],
        )
        if rs.rows:
            return self._settings_from_row(rs.rows[0])

        now = int(datetime.now().timestamp())
        settings_id = str(uuid.uuid4())
        await self.db_client.execute(
            """
            INSERT INTO UserSettings (id, userId, theme, language, emailNotifications, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [settings_id, user_id, "system", "en", True, now, now],
        )
        return await self.get_user_settings(user_id)

    async def update_user_settings(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        self._ensure_connected()
        current = await self.get_user_settings(user_id)
        update_fields: list[str] = ["updatedAt = ?"]
        params: list[Any] = [int(datetime.now().timestamp())]

        mapping = {
            "theme": "theme",
            "language": "language",
            "emailNotifications": "emailNotifications",
            "webhookUrl": "webhookUrl",
            "defaultProjectId": "defaultProjectId",
        }
        for key, column in mapping.items():
            if key in updates:
                update_fields.append(f"{column} = ?")
                params.append(updates[key])

        if "dashboardLayout" in updates:
            update_fields.append("dashboardLayout = ?")
            params.append(_json_dump(updates["dashboardLayout"]))

        if "robotSettings" in updates:
            update_fields.append("robotSettings = ?")
            params.append(_json_dump(updates["robotSettings"]))

        params.append(user_id)
        await self.db_client.execute(
            f"UPDATE UserSettings SET {', '.join(update_fields)} WHERE userId = ?",
            params,
        )
        return await self.get_user_settings(user_id)

    async def get_creator_profile(self, user_id: str, project_id: str | None = None) -> dict[str, Any] | None:
        self._ensure_connected()
        query = """
            SELECT id, userId, projectId, displayName, voice, positioning,
                   values, currentChapterId, createdAt, updatedAt
            FROM CreatorProfile
            WHERE userId = ?
        """
        params: list[Any] = [user_id]
        if project_id is not None:
            query += " AND projectId = ?"
            params.append(project_id)
        query += " ORDER BY updatedAt DESC LIMIT 1"
        rs = await self.db_client.execute(query, params)
        if not rs.rows:
            return None
        return self._creator_profile_from_row(rs.rows[0])

    async def upsert_creator_profile(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_connected()
        project_id = payload.get("projectId")
        existing = await self.get_creator_profile(user_id, project_id)
        now = int(datetime.now().timestamp())

        if existing:
            update_fields: list[str] = ["updatedAt = ?"]
            params: list[Any] = [now]
            mapping = {
                "displayName": "displayName",
                "currentChapterId": "currentChapterId",
            }
            for key, column in mapping.items():
                if key in payload:
                    update_fields.append(f"{column} = ?")
                    params.append(payload[key])
            for key in ("voice", "positioning", "values"):
                if key in payload:
                    update_fields.append(f"{key} = ?")
                    params.append(_json_dump(payload[key]))
            params.append(existing["id"])
            await self.db_client.execute(
                f"UPDATE CreatorProfile SET {', '.join(update_fields)} WHERE id = ?",
                params,
            )
        else:
            await self.db_client.execute(
                """
                INSERT INTO CreatorProfile (
                    id, userId, projectId, displayName, voice, positioning,
                    values, currentChapterId, createdAt, updatedAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(uuid.uuid4()),
                    user_id,
                    project_id,
                    payload.get("displayName"),
                    _json_dump(payload.get("voice")),
                    _json_dump(payload.get("positioning")),
                    _json_dump(payload.get("values")),
                    payload.get("currentChapterId"),
                    now,
                    now,
                ],
            )
        profile = await self.get_creator_profile(user_id, project_id)
        if not profile:
            raise RuntimeError("Failed to upsert creator profile")
        return profile

    async def list_personas(self, user_id: str, project_id: str | None = None) -> list[dict[str, Any]]:
        self._ensure_connected()
        query = """
            SELECT id, userId, projectId, name, avatar, demographics,
                   painPoints, goals, language, contentPreferences,
                   confidence, createdAt, updatedAt
            FROM CustomerPersona
            WHERE userId = ?
        """
        params: list[Any] = [user_id]
        if project_id is not None:
            query += " AND projectId = ?"
            params.append(project_id)
        query += " ORDER BY updatedAt DESC"
        rs = await self.db_client.execute(query, params)
        return [self._persona_from_row(row) for row in rs.rows]

    async def get_persona(self, user_id: str, persona_id: str) -> dict[str, Any] | None:
        self._ensure_connected()
        rs = await self.db_client.execute(
            """
            SELECT id, userId, projectId, name, avatar, demographics,
                   painPoints, goals, language, contentPreferences,
                   confidence, createdAt, updatedAt
            FROM CustomerPersona
            WHERE id = ? AND userId = ?
            LIMIT 1
            """,
            [persona_id, user_id],
        )
        if not rs.rows:
            return None
        return self._persona_from_row(rs.rows[0])

    async def create_persona(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_connected()
        now = int(datetime.now().timestamp())
        persona_id = str(uuid.uuid4())
        await self.db_client.execute(
            """
            INSERT INTO CustomerPersona (
                id, userId, projectId, name, avatar, demographics,
                painPoints, goals, language, contentPreferences,
                confidence, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                persona_id,
                user_id,
                payload.get("projectId"),
                payload["name"],
                payload.get("avatar"),
                _json_dump(payload.get("demographics")),
                _json_dump(payload.get("painPoints") or []),
                _json_dump(payload.get("goals") or []),
                _json_dump(payload.get("language")),
                _json_dump(payload.get("contentPreferences")),
                payload.get("confidence") or 50,
                now,
                now,
            ],
        )
        persona = await self.get_persona(user_id, persona_id)
        if not persona:
            raise RuntimeError("Failed to create persona")
        return persona

    async def update_persona(self, user_id: str, persona_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        self._ensure_connected()
        existing = await self.get_persona(user_id, persona_id)
        if not existing:
            return None
        update_fields: list[str] = ["updatedAt = ?"]
        params: list[Any] = [int(datetime.now().timestamp())]
        scalar_fields = {
            "name": "name",
            "avatar": "avatar",
            "confidence": "confidence",
        }
        for key, column in scalar_fields.items():
            if key in payload:
                update_fields.append(f"{column} = ?")
                params.append(payload[key])
        json_fields = {
            "demographics": "demographics",
            "painPoints": "painPoints",
            "goals": "goals",
            "language": "language",
            "contentPreferences": "contentPreferences",
        }
        for key, column in json_fields.items():
            if key in payload:
                update_fields.append(f"{column} = ?")
                params.append(_json_dump(payload[key]))
        params.extend([persona_id, user_id])
        await self.db_client.execute(
            f"UPDATE CustomerPersona SET {', '.join(update_fields)} WHERE id = ? AND userId = ?",
            params,
        )
        return await self.get_persona(user_id, persona_id)

    async def delete_persona(self, user_id: str, persona_id: str) -> bool:
        self._ensure_connected()
        persona = await self.get_persona(user_id, persona_id)
        if not persona:
            return False
        await self.db_client.execute(
            "DELETE FROM CustomerPersona WHERE id = ? AND userId = ?",
            [persona_id, user_id],
        )
        return True


user_data_store = UserDataStore()
