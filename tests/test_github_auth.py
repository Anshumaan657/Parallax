from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.integrations.contracts import AdapterError
from app.integrations.github import GitHubAdapter
from app.integrations.github_auth import GitHubTokenManager


@pytest.mark.asyncio
async def test_expired_token_refreshes_and_updates_api_authorization() -> None:
    calls: list[tuple[str, str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, request.headers.get("authorization")))
        if request.url.path == "/login/oauth/access_token":
            return httpx.Response(
                200,
                json={
                    "access_token": "refreshed-token",
                    "refresh_token": "next-refresh-token",
                    "expires_in": 3600,
                },
            )
        return httpx.Response(200, json={"login": "octocat"})

    adapter = GitHubAdapter(
        "expired-token",
        2,
        httpx.MockTransport(handler),
        refresh_token="refresh-token",
        token_expires_at=datetime.now(UTC) - timedelta(minutes=1),
        oauth_client_id="client-id",
        oauth_client_secret="client-secret",
    )
    try:
        assert (await adapter.health()).connected is True
        assert adapter.token_manager.access_token == "refreshed-token"
        assert calls[0][1] == "/login/oauth/access_token"
        assert calls[1] == ("GET", "/user", "Bearer refreshed-token")
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_expired_token_without_refresh_configuration_fails_closed() -> None:
    manager = GitHubTokenManager(
        access_token="expired-token",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    with pytest.raises(AdapterError, match="refresh is not configured"):
        await manager.ensure_valid()


@pytest.mark.asyncio
async def test_revoke_clears_tokens() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/applications/client-id/token"
        return httpx.Response(204)

    manager = GitHubTokenManager(
        access_token="token",
        refresh_token="refresh",
        client_id="client-id",
        client_secret="client-secret",
        transport=httpx.MockTransport(handler),
    )
    await manager.revoke()
    assert manager.access_token == ""
    assert manager.refresh_token == ""
    assert manager.expires_at is None
