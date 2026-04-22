from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.models.user_data import OpenRouterCredentialUpsertRequest
from api.routers import settings_integrations as router


@pytest.mark.asyncio
async def test_get_openrouter_status_returns_unconfigured_when_missing(monkeypatch):
    monkeypatch.setattr(
        router.user_key_store,
        "get_credential_status",
        AsyncMock(return_value=None),
    )

    response = await router.get_openrouter_credential(
        current_user=SimpleNamespace(user_id="user-1"),
    )

    assert response.configured is False
    assert response.masked_secret is None


@pytest.mark.asyncio
async def test_put_openrouter_masks_secret_and_never_returns_raw_key(monkeypatch):
    monkeypatch.setattr(
        router.user_key_store,
        "upsert_secret",
        AsyncMock(
            return_value={
                "provider": "openrouter",
                "configured": True,
                "masked_secret": "••••••••1234",
                "validation_status": "unknown",
                "updated_at": None,
                "last_validated_at": None,
            }
        ),
    )
    req = OpenRouterCredentialUpsertRequest(api_key="sk-or-v1-secret-1234")

    response = await router.put_openrouter_credential(
        request=req,
        current_user=SimpleNamespace(user_id="user-1"),
    )
    payload = response.model_dump(by_alias=True)

    assert payload["maskedSecret"] == "••••••••1234"
    assert "sk-or-v1-secret-1234" not in str(payload)


@pytest.mark.asyncio
async def test_delete_openrouter_credential_calls_store(monkeypatch):
    delete_mock = AsyncMock()
    monkeypatch.setattr(router.user_key_store, "delete_credential", delete_mock)

    response = await router.delete_openrouter_credential(
        current_user=SimpleNamespace(user_id="user-1"),
    )

    assert response == {"deleted": True}
    delete_mock.assert_awaited_once_with("user-1", provider="openrouter")


@pytest.mark.asyncio
async def test_validate_openrouter_credential_marks_valid(monkeypatch):
    monkeypatch.setattr(
        router.user_key_store,
        "get_secret",
        AsyncMock(return_value="sk-or-v1-secret-1234"),
    )
    set_status = AsyncMock()
    monkeypatch.setattr(router.user_key_store, "set_validation_status", set_status)

    response_mock = MagicMock(status_code=200)

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *args, **kwargs):
            return response_mock

    monkeypatch.setattr(router.httpx, "AsyncClient", lambda timeout=12.0: _Client())

    response = await router.validate_openrouter_credential(
        current_user=SimpleNamespace(user_id="user-1"),
    )

    assert response.valid is True
    assert response.validation_status == "valid"
    set_status.assert_awaited_once_with(
        "user-1",
        provider="openrouter",
        validation_status="valid",
    )


@pytest.mark.asyncio
async def test_validate_openrouter_credential_returns_missing_when_not_configured(monkeypatch):
    monkeypatch.setattr(
        router.user_key_store,
        "get_secret",
        AsyncMock(return_value=None),
    )

    response = await router.validate_openrouter_credential(
        current_user=SimpleNamespace(user_id="user-1"),
    )

    assert response.valid is False
    assert response.validation_status == "missing"


@pytest.mark.asyncio
async def test_validate_openrouter_credential_marks_invalid_on_http_error(monkeypatch):
    monkeypatch.setattr(
        router.user_key_store,
        "get_secret",
        AsyncMock(return_value="sk-or-v1-secret-1234"),
    )
    set_status = AsyncMock()
    monkeypatch.setattr(router.user_key_store, "set_validation_status", set_status)

    response_mock = MagicMock(status_code=401)

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *args, **kwargs):
            return response_mock

    monkeypatch.setattr(router.httpx, "AsyncClient", lambda timeout=12.0: _Client())

    response = await router.validate_openrouter_credential(
        current_user=SimpleNamespace(user_id="user-1"),
    )

    assert response.valid is False
    assert response.validation_status == "invalid"
    set_status.assert_awaited_once_with(
        "user-1",
        provider="openrouter",
        validation_status="invalid",
    )
