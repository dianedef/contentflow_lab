"""Clerk JWT validation helpers for FastAPI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from jwt import InvalidTokenError, PyJWKClient


class ClerkConfigurationError(RuntimeError):
    """Raised when Clerk auth is not configured."""


class ClerkAuthenticationError(RuntimeError):
    """Raised when a Clerk token cannot be validated."""


@dataclass(frozen=True)
class ClerkClaims:
    """Normalized claims extracted from a validated Clerk token."""

    user_id: str
    email: str | None = None
    raw_claims: dict[str, Any] | None = None


@dataclass(frozen=True)
class ClerkSettings:
    """Runtime Clerk configuration loaded from environment variables."""

    issuer: str
    jwks_url: str
    audience: str | None = None


@lru_cache(maxsize=1)
def get_clerk_settings() -> ClerkSettings:
    """Load Clerk settings from the environment."""
    issuer = (
        os.getenv("CLERK_JWT_ISSUER")
        or os.getenv("CLERK_ISSUER")
        or ""
    ).strip()
    jwks_url = (os.getenv("CLERK_JWKS_URL") or "").strip()
    audience = (
        os.getenv("CLERK_JWT_AUDIENCE")
        or os.getenv("CLERK_AUDIENCE")
        or ""
    ).strip() or None

    if not issuer and not jwks_url:
        raise ClerkConfigurationError(
            "Clerk auth not configured. Set CLERK_JWT_ISSUER or CLERK_JWKS_URL."
        )

    if not jwks_url:
        jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"

    if not issuer:
        issuer = jwks_url.removesuffix("/.well-known/jwks.json")

    return ClerkSettings(
        issuer=issuer.rstrip("/"),
        jwks_url=jwks_url,
        audience=audience,
    )


@lru_cache(maxsize=1)
def get_jwk_client() -> PyJWKClient:
    """Create a cached JWK client for Clerk."""
    settings = get_clerk_settings()
    return PyJWKClient(settings.jwks_url)


def validate_clerk_token(token: str) -> ClerkClaims:
    """Validate a Clerk JWT and return normalized claims."""
    if not token:
        raise ClerkAuthenticationError("Missing bearer token")

    settings = get_clerk_settings()

    try:
        signing_key = get_jwk_client().get_signing_key_from_jwt(token)
        decode_kwargs: dict[str, Any] = {
            "algorithms": ["RS256"],
            "issuer": settings.issuer,
        }
        if settings.audience:
            decode_kwargs["audience"] = settings.audience
        else:
            decode_kwargs["options"] = {"verify_aud": False}

        claims = jwt.decode(
            token,
            signing_key.key,
            **decode_kwargs,
        )
    except ClerkConfigurationError:
        raise
    except InvalidTokenError as exc:
        raise ClerkAuthenticationError(f"Invalid Clerk token: {exc}") from exc
    except Exception as exc:
        raise ClerkAuthenticationError(
            f"Failed to validate Clerk token: {exc}"
        ) from exc

    user_id = str(claims.get("sub") or "").strip()
    if not user_id:
        raise ClerkAuthenticationError("Validated Clerk token is missing 'sub'")

    email = claims.get("email")
    if isinstance(email, str) and not email.strip():
        email = None

    return ClerkClaims(
        user_id=user_id,
        email=email,
        raw_claims=claims,
    )
