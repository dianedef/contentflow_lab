import importlib


def test_detect_git_sha_prefers_render_commit(monkeypatch):
    monkeypatch.delenv("BACKEND_GIT_SHA", raising=False)
    monkeypatch.setenv(
        "RENDER_GIT_COMMIT",
        "1234567890abcdef1234567890abcdef12345678",
    )
    monkeypatch.delenv("GIT_SHA", raising=False)

    from api.routers import health

    assert health._detect_git_sha() == "1234567"


def test_detect_git_sha_prefers_backend_git_sha(monkeypatch):
    monkeypatch.setenv("BACKEND_GIT_SHA", "abcdef0123456789")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "1234567890abcdef")
    monkeypatch.setenv("GIT_SHA", "fedcba9876543210")

    from api.routers import health

    assert health._detect_git_sha() == "abcdef0"


def test_normalize_git_sha_handles_blank_values():
    from api.routers import health

    assert health._normalize_git_sha("   ") is None
    assert health._normalize_git_sha("abcdef0") == "abcdef0"
    assert health._normalize_git_sha("abcdef012345") == "abcdef0"
