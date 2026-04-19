from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies.auth import CurrentUser, require_current_user
from api.routers.publish import router as publish_router


class _FakeAsyncClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return self._response

    async def get(self, *args, **kwargs):
        return self._response


def _build_client(*, authenticated: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(publish_router)
    if authenticated:
        app.dependency_overrides[require_current_user] = lambda: CurrentUser(
            user_id="user_123",
            email="user@example.com",
            bearer_token="test-token",
        )
    return TestClient(app)


def test_publish_accounts_requires_auth():
    client = _build_client(authenticated=False)
    response = client.get("/api/publish/accounts")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_publish_persists_metadata_and_published_transitions():
    client = _build_client()
    fake_record = SimpleNamespace(
        status="approved",
        metadata={"existing": "value"},
    )
    fake_service = MagicMock()
    fake_service.get_content.return_value = fake_record

    http_response = MagicMock()
    http_response.status_code = 200
    http_response.headers = {"content-type": "application/json"}
    http_response.json.return_value = {
        "posts": [
            {
                "_id": "post_123",
                "status": "published",
                "platforms": [
                    {
                        "platform": "twitter",
                        "platformPostUrl": "https://x.example/post_123",
                    }
                ],
            }
        ]
    }

    with (
        patch("api.routers.publish.get_status_service", return_value=fake_service),
        patch(
            "api.routers.publish.require_owned_content_record",
            AsyncMock(return_value=fake_record),
        ),
        patch(
            "api.routers.publish.httpx.AsyncClient",
            return_value=_FakeAsyncClient(http_response),
        ),
    ):
        response = client.post(
            "/api/publish",
            json={
                "content": "Hello world",
                "platforms": [{"platform": "twitter", "account_id": "acct_1"}],
                "title": "Test publish",
                "content_record_id": "content_1",
                "publish_now": True,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["post_id"] == "post_123"
    assert payload["platform_urls"] == {"twitter": "https://x.example/post_123"}

    fake_service.update_content.assert_called_once()
    _, kwargs = fake_service.update_content.call_args
    assert kwargs["target_url"] == "https://x.example/post_123"
    assert kwargs["metadata"]["existing"] == "value"
    assert kwargs["metadata"]["publish"]["provider"] == "zernio"
    assert kwargs["metadata"]["publish"]["post_id"] == "post_123"
    assert kwargs["metadata"]["publish"]["status"] == "published"
    assert kwargs["metadata"]["publish"]["platform_urls"] == {
        "twitter": "https://x.example/post_123"
    }

    assert fake_service.transition.call_count == 2
    assert fake_service.transition.call_args_list[0].args == (
        "content_1",
        "publishing",
        "user_123",
    )
    assert fake_service.transition.call_args_list[1].args == (
        "content_1",
        "published",
        "user_123",
    )


def test_publish_persists_scheduled_state_without_published_transition():
    client = _build_client()
    fake_record = SimpleNamespace(
        status="approved",
        metadata={},
    )
    fake_service = MagicMock()
    fake_service.get_content.return_value = fake_record

    http_response = MagicMock()
    http_response.status_code = 200
    http_response.headers = {"content-type": "application/json"}
    http_response.json.return_value = {
        "posts": [
            {
                "_id": "post_sched_1",
                "status": "scheduled",
                "scheduledFor": "2026-03-30T10:00:00Z",
                "platforms": [],
            }
        ]
    }

    with (
        patch("api.routers.publish.get_status_service", return_value=fake_service),
        patch(
            "api.routers.publish.require_owned_content_record",
            AsyncMock(return_value=fake_record),
        ),
        patch(
            "api.routers.publish.httpx.AsyncClient",
            return_value=_FakeAsyncClient(http_response),
        ),
    ):
        response = client.post(
            "/api/publish",
            json={
                "content": "Scheduled post",
                "platforms": [{"platform": "twitter", "account_id": "acct_1"}],
                "content_record_id": "content_2",
                "publish_now": False,
                "scheduled_for": "2026-03-30T10:00:00Z",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "scheduled"

    fake_service.update_content.assert_called_once()
    _, kwargs = fake_service.update_content.call_args
    assert kwargs["target_url"] is None
    assert kwargs["metadata"]["publish"]["status"] == "scheduled"
    assert kwargs["metadata"]["publish"]["scheduled_for"] == "2026-03-30T10:00:00Z"

    fake_service.transition.assert_called_once_with(
        "content_2",
        "scheduled",
        "user_123",
        reason="Queued in Zernio",
    )
