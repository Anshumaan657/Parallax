import uuid
from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.integrations.contracts import AdapterError, ApprovedWriteContext
from app.integrations.github import GitHubAdapter
from app.integrations.jira import JiraAdapter
from app.integrations.notion import NotionAdapter
from app.integrations.registry import (
    build_github_adapter,
    build_jira_adapter,
    build_notion_adapter,
    build_slack_adapter,
)
from app.integrations.slack import SlackAdapter

OWNER = {
    "email": "integration-owner@example.com",
    "password": "correct-horse-battery-staple",
    "display_name": "Integration Owner",
    "workspace_name": "Integration Workspace",
    "workspace_slug": "integration-workspace",
}


def auth(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/register", json=OWNER)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def approval() -> ApprovedWriteContext:
    return ApprovedWriteContext(
        approval_id=uuid.uuid4(), mission_id=uuid.uuid4(), approved_at=datetime.now(UTC)
    )


def test_mock_connection_checks_and_capabilities(client: TestClient) -> None:
    headers = auth(client)
    for provider in ("github", "jira", "notion", "slack"):
        checked = client.post(f"/api/integrations/{provider}/check", headers=headers)
        assert checked.status_code == 200
        assert checked.json()["connected"] is True
        capabilities = client.get(f"/api/integrations/{provider}/capabilities", headers=headers)
        assert capabilities.status_code == 200
        assert capabilities.json()["mode"] == "mock"
        assert capabilities.json()["capabilities"]

    statuses = client.get("/api/integrations", headers=headers).json()
    assert len(statuses) == 4
    assert all(item["connected"] for item in statuses)


def test_workspace_can_register_and_list_github_repositories(client: TestClient) -> None:
    headers = auth(client)
    registered = client.post(
        "/api/integrations/github/repositories",
        headers=headers,
        json={"full_name": "acme/service", "default_branch": "main"},
    )
    assert registered.status_code == 201
    body = registered.json()
    assert body["full_name"] == "acme/service"
    assert body["project_id"]
    assert body["external_id"] == "mock-repository"
    assert body["webhook_enabled"] is True
    assert set(body["webhook_events"]) == {"opened", "reopened", "ready_for_review", "synchronize"}

    updated = client.patch(
        f"/api/integrations/github/repositories/{body['id']}",
        headers=headers,
        json={
            "default_branch": "trunk",
            "webhook_enabled": False,
            "webhook_events": ["opened", "synchronize"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["default_branch"] == "trunk"
    assert updated.json()["webhook_enabled"] is False
    assert set(updated.json()["webhook_events"]) == {"opened", "synchronize"}

    duplicate = client.post(
        "/api/integrations/github/repositories",
        headers=headers,
        json={"full_name": "acme/service"},
    )
    assert duplicate.status_code == 409

    repositories = client.get(
        "/api/integrations/github/repositories", headers=headers
    )
    assert repositories.status_code == 200
    assert [item["full_name"] for item in repositories.json()] == ["acme/service"]

    removed = client.delete(
        f"/api/integrations/github/repositories/{body['id']}", headers=headers
    )
    assert removed.status_code == 204
    assert client.get("/api/integrations/github/repositories", headers=headers).json() == []


def test_real_mode_missing_credentials_is_disconnected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = auth(client)
    monkeypatch.setattr(settings, "integration_mode", "real")
    response = client.post("/api/integrations/github/check", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "name": "GitHub",
        "connected": False,
        "detail": "Missing GITHUB_TOKEN",
    }


@pytest.mark.asyncio
async def test_mock_adapters_match_read_and_write_boundaries() -> None:
    github = build_github_adapter()
    jira = build_jira_adapter()
    notion = build_notion_adapter()
    slack = build_slack_adapter()
    try:
        assert (await github.get_pull_request("acme/service", 7)).data["mock"] is True
        assert (await jira.get_issue("PAY-7")).external_id == "PAY-7"
        assert (await notion.search_pages("release"))[0]["mock"] is True
        assert (await slack.channel_history("C123"))[0]["mock"] is True
        with pytest.raises(PermissionError):
            await jira.create_issue({"summary": "Blocked"}, None)
        assert (await slack.post_message("C123", "Approved", approval())).data["mock"] is True
    finally:
        await github.close()
        await jira.close()
        await notion.close()
        await slack.close()


@pytest.mark.asyncio
async def test_github_read_client_uses_expected_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/user":
            return httpx.Response(200, json={"login": "octocat"})
        if request.url.path.endswith("/files"):
            return httpx.Response(200, json=[{"filename": "app.py", "status": "modified"}])
        if request.url.path.endswith("/commits"):
            return httpx.Response(200, json=[{"sha": "abc", "commit": {"message": "Change"}}])
        return httpx.Response(
            200,
            json={
                "id": 42,
                "title": "Safe change",
                "html_url": "https://github.example/pr/7",
            },
        )

    adapter = GitHubAdapter("token", 2, httpx.MockTransport(handler))
    try:
        assert (await adapter.health()).connected is True
        pull = await adapter.get_pull_request("acme/service", 7)
        assert pull.external_id == "42"
        assert pull.title == "Safe change"
        assert (await adapter.get_pull_request_files("acme/service", 7))[0]["filename"] == "app.py"
        assert (await adapter.get_pull_request_commits("acme/service", 7))[0]["sha"] == "abc"
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_vendor_error_is_safe_and_marks_retryability() -> None:
    adapter = GitHubAdapter(
        "secret-token",
        2,
        httpx.MockTransport(lambda _: httpx.Response(503, text="sensitive vendor response")),
    )
    try:
        with pytest.raises(AdapterError) as captured:
            await adapter.health()
        assert str(captured.value) == "Integration returned HTTP 503"
        assert captured.value.retryable is True
        assert "sensitive" not in str(captured.value)
        assert "secret-token" not in str(captured.value)
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_write_clients_require_approval_before_network() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == "/rest/api/3/issue":
            return httpx.Response(201, json={"id": "1", "key": "PAY-1"})
        if request.url.path.endswith("/comments"):
            return httpx.Response(201, json={"id": 123, "html_url": "https://github.example/comment/123"})
        if request.url.path.endswith("/children"):
            return httpx.Response(200, json={"results": []})
        return httpx.Response(200, json={"ok": True, "ts": "123.456"})

    transport = httpx.MockTransport(handler)
    github = GitHubAdapter("token", 2, transport)
    jira = JiraAdapter("https://jira.example", "owner@example.com", "token", 2, transport)
    notion = NotionAdapter("token", 2, transport)
    slack = SlackAdapter("token", 2, transport)
    try:
        with pytest.raises(PermissionError):
            await jira.create_issue({"summary": "No approval"}, None)
        with pytest.raises(PermissionError):
            await notion.append_blocks("page-1", [], None)
        with pytest.raises(PermissionError):
            await slack.post_message("C123", "No approval", None)
        with pytest.raises(PermissionError):
            await github.create_pull_request_comment("acme/service", 7, "No approval", None)
        assert calls == []

        approved = approval()
        comment = await github.create_pull_request_comment("acme/service", 7, "Approved", approved)
        assert comment.external_id == "123"
        assert (await jira.create_issue({"summary": "Approved"}, approved)).external_id == "PAY-1"
        await notion.append_blocks("page-1", [], approved)
        assert (await slack.post_message("C123", "Approved", approved)).external_id == "123.456"
        assert calls == [
            ("POST", "/repos/acme/service/issues/7/comments"),
            ("POST", "/rest/api/3/issue"),
            ("PATCH", "/v1/blocks/page-1/children"),
            ("POST", "/api/chat.postMessage"),
        ]
    finally:
        await github.close()
        await jira.close()
        await notion.close()
        await slack.close()
