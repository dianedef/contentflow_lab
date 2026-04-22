"""Application-level encryption for user-managed provider secrets."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


class SecretsCrypto:
    """Encrypt/decrypt user secrets using a key derived from env configuration."""

    def __init__(self) -> None:
        raw_key = os.getenv("USER_SECRETS_MASTER_KEY")
        if not raw_key:
            raise RuntimeError(
                "USER_SECRETS_MASTER_KEY is required to manage user provider credentials."
            )
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
        fernet_key = base64.urlsafe_b64encode(digest)
        self._fernet = Fernet(fernet_key)

    def encrypt(self, secret: str) -> str:
        return self._fernet.encrypt(secret.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_secret: str) -> str:
        try:
            return self._fernet.decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError("Failed to decrypt stored user credential.") from exc


_crypto: SecretsCrypto | None = None


def get_crypto() -> SecretsCrypto:
    global _crypto
    if _crypto is None:
        _crypto = SecretsCrypto()
    return _crypto

