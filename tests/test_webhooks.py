import hashlib
import hmac
import json
import uuid

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select

from app.config import settings
from app.models import IntegrationProvider, Project, Repository


def _signed_headers(body: bytes, secret: str = "webhook-secret") -> dict[str, str]:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": str(uuid.uuid4()),
        "X-Hub-Signature-256": f"sha256={digest}",
    }


def _payload(full_name: str = "acme/service") -> dict[str, object]:
    return {
        "action": "opened",
        "repository": {"full_name": full_name},
        "pull_request": {"number": 7, "title": "Safe change"},
    }


def test_github_webhook_requires_valid_signature(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "github_webhook_secret", SecretStr("webhook-secret"))
    body = json.dumps(_payload()).encode()
    response = client.post(
        "/api/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": str(uuid.uuid4()),
            "X-Hub-Signature-256": "sha256=invalid",
        },
    )
    assert response.status_code == 401


def test_github_webhook_acknowledges_unknown_repository(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "github_webhook_secret", SecretStr("webhook-secret"))
    body = json.dumps(_payload()).encode()
    response = client.post(
        "/api/webhooks/github",
        content=body,
        headers=_signed_headers(body),
    )
    assert response.status_code == 202
    assert response.json()["reason"] == "repository_not_registered"


def test_github_webhook_persists_once_and_deduplicates(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "github_webhook_secret", SecretStr("webhook-secret"))
    registration = client.post(
        "/api/auth/register",
        json={
            "email": "webhook-owner@example.com",
            "password": "correct-horse-battery-staple",
            "display_name": "Webhook Owner",
            "workspace_name": "Webhook Workspace",
            "workspace_slug": "webhook-workspace",
        },
    )
    assert registration.status_code == 201
    workspace_id = uuid.UUID(registration.json()["workspace_id"])
    factory = client.test_session_factory  # type: ignore[attr-defined]

    import asyncio

    async def register_repository() -> None:
        async with factory() as session:
            project = await session.scalar(
                select(Project).where(
                    Project.workspace_id == workspace_id, Project.name == "General"
                )
            )
            session.add(
                Repository(
                    workspace_id=workspace_id,
                    provider=IntegrationProvider.GITHUB,
                    external_id="42",
                    full_name="acme/service",
                    project_id=project.id if project else None,
                )
            )
            await session.commit()

    asyncio.run(register_repository())

    payload = _payload()
    body = json.dumps(payload).encode()
    headers = _signed_headers(body)
    first = client.post("/api/webhooks/github", content=body, headers=headers)
    second = client.post("/api/webhooks/github", content=body, headers=headers)
    assert first.status_code == 202
    assert first.json()["accepted"] is True
    assert first.json()["status"] == "queued"
    assert first.json()["mission_id"]
    assert second.status_code == 202
    assert second.json()["duplicate"] is True


def test_github_webhook_respects_repository_configuration(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "github_webhook_secret", SecretStr("webhook-secret"))
    registration = client.post(
        "/api/auth/register",
        json={
            "email": "configured-webhook-owner@example.com",
            "password": "correct-horse-battery-staple",
            "display_name": "Configured Webhook Owner",
            "workspace_name": "Configured Webhook Workspace",
            "workspace_slug": "configured-webhook-workspace",
        },
    )
    assert registration.status_code == 201
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    registered = client.post(
        "/api/integrations/github/repositories",
        headers=headers,
        json={"full_name": "acme/configured", "default_branch": "main"},
    )
    assert registered.status_code == 201
    repository_id = registered.json()["id"]
    updated = client.patch(
        f"/api/integrations/github/repositories/{repository_id}",
        headers=headers,
        json={"default_branch": "main", "webhook_enabled": False, "webhook_events": ["opened"]},
    )
    assert updated.status_code == 200
    payload = {
        "repository": {"full_name": "acme/configured"},
        "action": "opened",
        "pull_request": {"number": 1},
    }
    body = json.dumps(payload).encode()
    response = client.post(
        "/api/webhooks/github",
        content=body,
        headers={
            **_signed_headers(body),
            "X-GitHub-Delivery": "disabled-1",
            "X-GitHub-Event": "pull_request",
        },
    )
    assert response.status_code == 202
    assert response.json()["reason"] == "webhook_disabled"
