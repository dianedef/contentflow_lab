"""Authenticated settings integrations endpoints (OpenRouter user key V1)."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException

from api.dependencies.auth import CurrentUser, require_current_user
from api.models.user_data import (
    OpenRouterCredentialStatus,
    OpenRouterCredentialUpsertRequest,
    OpenRouterCredentialValidateResponse,
)
from api.services.user_key_store import user_key_store

router = APIRouter(prefix="/api/settings/integrations", tags=["Settings Integrations"])

_OPENROUTER_PROVIDER = "openrouter"
_OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def _empty_openrouter_status() -> OpenRouterCredentialStatus:
    return OpenRouterCredentialStatus(
        provider="openrouter",
        configured=False,
        masked_secret=None,
        validation_status="unknown",
        last_validated_at=None,
        updated_at=None,
    )


@router.get(
    "/openrouter",
    response_model=OpenRouterCredentialStatus,
    summary="Get OpenRouter credential status",
)
async def get_openrouter_credential(
    current_user: CurrentUser = Depends(require_current_user),
) -> OpenRouterCredentialStatus:
    status = await user_key_store.get_credential_status(
        current_user.user_id,
        provider=_OPENROUTER_PROVIDER,
    )
    if status is None:
        return _empty_openrouter_status()
    return OpenRouterCredentialStatus(**status)


@router.put(
    "/openrouter",
    response_model=OpenRouterCredentialStatus,
    summary="Store OpenRouter credential",
)
async def put_openrouter_credential(
    request: OpenRouterCredentialUpsertRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> OpenRouterCredentialStatus:
    try:
        status = await user_key_store.upsert_secret(
            current_user.user_id,
            provider=_OPENROUTER_PROVIDER,
            secret=request.api_key,
            validation_status="unknown",
            last_validated_at=None,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return OpenRouterCredentialStatus(**status)


@router.delete("/openrouter", summary="Delete OpenRouter credential")
async def delete_openrouter_credential(
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, bool]:
    await user_key_store.delete_credential(
        current_user.user_id,
        provider=_OPENROUTER_PROVIDER,
    )
    return {"deleted": True}


@router.post(
    "/openrouter/validate",
    response_model=OpenRouterCredentialValidateResponse,
    summary="Validate stored OpenRouter credential",
)
async def validate_openrouter_credential(
    current_user: CurrentUser = Depends(require_current_user),
) -> OpenRouterCredentialValidateResponse:
    api_key = await user_key_store.get_secret(
        current_user.user_id,
        provider=_OPENROUTER_PROVIDER,
    )
    if not api_key:
        return OpenRouterCredentialValidateResponse(
            provider="openrouter",
            valid=False,
            validation_status="missing",
            message="No OpenRouter key configured.",
        )

    validation_status = "invalid"
    message = "OpenRouter key is invalid."
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(
                _OPENROUTER_MODELS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if response.status_code < 400:
            validation_status = "valid"
            message = "OpenRouter key is valid."
    except Exception:
        validation_status = "invalid"
        message = "OpenRouter validation request failed."

    await user_key_store.set_validation_status(
        current_user.user_id,
        provider=_OPENROUTER_PROVIDER,
        validation_status=validation_status,
    )
    return OpenRouterCredentialValidateResponse(
        provider="openrouter",
        valid=validation_status == "valid",
        validation_status=validation_status,
        message=message,
    )

