"""Store encrypted user-managed provider credentials."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from utils.libsql_async import create_client

from api.services.crypto import get_crypto


def _mask_secret(secret: str) -> str:
    tail = secret[-4:] if len(secret) >= 4 else secret
    return f"••••••••{tail}"


class UserKeyStore:
    """Persistence layer for user provider keys (OpenRouter v1)."""

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
            CREATE TABLE IF NOT EXISTS UserProviderCredential (
                userId TEXT NOT NULL,
                provider TEXT NOT NULL,
                encryptedSecret TEXT NOT NULL,
                maskedSecret TEXT NOT NULL,
                createdAt INTEGER NOT NULL,
                updatedAt INTEGER NOT NULL,
                lastValidatedAt INTEGER,
                validationStatus TEXT NOT NULL DEFAULT 'unknown',
                PRIMARY KEY (userId, provider)
            )
            """
        )

    async def upsert_secret(
        self,
        user_id: str,
        *,
        provider: str,
        secret: str,
        validation_status: str = "unknown",
        last_validated_at: int | None = None,
    ) -> dict[str, Any]:
        self._ensure_connected()
        now = int(datetime.now().timestamp())
        crypto = get_crypto()
        encrypted = crypto.encrypt(secret)
        masked = _mask_secret(secret)
        await self.db_client.execute(
            """
            INSERT INTO UserProviderCredential (
                userId, provider, encryptedSecret, maskedSecret,
                createdAt, updatedAt, lastValidatedAt, validationStatus
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(userId, provider) DO UPDATE SET
                encryptedSecret = excluded.encryptedSecret,
                maskedSecret = excluded.maskedSecret,
                updatedAt = excluded.updatedAt,
                lastValidatedAt = excluded.lastValidatedAt,
                validationStatus = excluded.validationStatus
            """,
            [
                user_id,
                provider,
                encrypted,
                masked,
                now,
                now,
                last_validated_at,
                validation_status,
            ],
        )
        status = await self.get_credential_status(user_id, provider=provider)
        if status is None:
            raise RuntimeError("Failed to persist user provider credential.")
        return status

    async def get_secret(self, user_id: str, *, provider: str) -> str | None:
        self._ensure_connected()
        rs = await self.db_client.execute(
            """
            SELECT encryptedSecret
            FROM UserProviderCredential
            WHERE userId = ? AND provider = ?
            LIMIT 1
            """,
            [user_id, provider],
        )
        if not rs.rows:
            return None
        encrypted = rs.rows[0][0]
        if not encrypted:
            return None
        crypto = get_crypto()
        return crypto.decrypt(str(encrypted))

    async def get_credential_status(
        self,
        user_id: str,
        *,
        provider: str,
    ) -> dict[str, Any] | None:
        self._ensure_connected()
        rs = await self.db_client.execute(
            """
            SELECT userId, provider, maskedSecret, updatedAt, lastValidatedAt, validationStatus
            FROM UserProviderCredential
            WHERE userId = ? AND provider = ?
            LIMIT 1
            """,
            [user_id, provider],
        )
        if not rs.rows:
            return None
        row = rs.rows[0]
        return {
            "user_id": row[0],
            "provider": row[1],
            "configured": True,
            "masked_secret": row[2],
            "updated_at": datetime.fromtimestamp(int(row[3])) if row[3] else None,
            "last_validated_at": datetime.fromtimestamp(int(row[4])) if row[4] else None,
            "validation_status": row[5] or "unknown",
        }

    async def set_validation_status(
        self,
        user_id: str,
        *,
        provider: str,
        validation_status: str,
    ) -> dict[str, Any] | None:
        self._ensure_connected()
        now = int(datetime.now().timestamp())
        await self.db_client.execute(
            """
            UPDATE UserProviderCredential
            SET validationStatus = ?, lastValidatedAt = ?, updatedAt = ?
            WHERE userId = ? AND provider = ?
            """,
            [validation_status, now, now, user_id, provider],
        )
        return await self.get_credential_status(user_id, provider=provider)

    async def delete_credential(self, user_id: str, *, provider: str) -> None:
        self._ensure_connected()
        await self.db_client.execute(
            """
            DELETE FROM UserProviderCredential
            WHERE userId = ? AND provider = ?
            """,
            [user_id, provider],
        )


user_key_store = UserKeyStore()

