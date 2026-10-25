import hashlib
import hmac
import json
import uuid

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import settings


def test_non_pull_request_webhooks_are_acknowledged(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "github_webhook_secret", SecretStr("webhook-secret"))
    body = json.dumps(
        {"action": "created", "repository": {"full_name": "acme/service"}}
    ).encode()
    signature = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
    response = client.post(
        "/api/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "star",
            "X-GitHub-Delivery": str(uuid.uuid4()),
            "X-Hub-Signature-256": f"sha256={signature}",
        },
    )
    assert response.status_code == 202
    assert response.json()["reason"] == "repository_not_registered"
