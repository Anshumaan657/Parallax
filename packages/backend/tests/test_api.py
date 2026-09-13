"""Hermetic tests for the Parallax control-plane API.

Agent Core is simulated with httpx.MockTransport so tests never
require the Agent Core server or live credentials.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent_client import AgentCoreClient
from app.main import app, get_agent_core_client


def make_client(
    handler: Any,
) -> TestClient:
    """Build a TestClient whose Agent Core client uses a mock transport."""

    def override() -> Iterator[AgentCoreClient]:
        yield AgentCoreClient(
            base_url="http://agent-core.test",
            transport=httpx.MockTransport(handler),
        )

    app.dependency_overrides[get_agent_core_client] = override
    return TestClient(app)


MISSION_ACK = {
    "missionId": "mission-1",
    "status": "waiting_for_approval",
    "currentStep": "approval_gate",
    "proposedActions": [
        {
            "id": "action-1",
            "type": "jira.create_issue",
            "target": "PAY",
            "reason": "Track follow-up work.",
            "requiresApproval": True,
            "status": "proposed",
        },
    ],
    "policyDecision": {
        "allowed": True,
        "requiresApproval": True,
        "reason": "High-risk changes require approval.",
    },
    "errors": [],
}

MISSION_STATE = {
    "missionId": "mission-1",
    "status": "waiting_for_approval",
    "state": {"currentStep": "approval_gate", "errors": []},
}

DECISION_RESULT = {
    "missionId": "mission-1",
    "status": "completed",
    "currentStep": "audit_actions",
    "policyRecommendation": None,
    "proposedActions": [],
    "executionResults": [],
    "verificationResults": [],
    "slackSummary": "",
    "errors": [],
}


def route_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "POST" and request.url.path == "/missions":
        if b"unreachable" in request.content:
            return httpx.Response(500, json={"error": "boom"})

        return httpx.Response(202, json=MISSION_ACK)

    if request.method == "GET" and request.url.path == "/missions/mission-1":
        return httpx.Response(200, json=MISSION_STATE)

    if request.method == "GET" and request.url.path == "/missions/missing":
        return httpx.Response(404, json={"error": "Mission not found"})

    if (
        request.method == "POST"
        and request.url.path == "/missions/mission-1/approve"
    ):
        return httpx.Response(200, json=DECISION_RESULT)

    if (
        request.method == "POST"
        and request.url.path == "/missions/mission-1/reject"
    ):
        return httpx.Response(200, json=DECISION_RESULT)

    return httpx.Response(404, json={"error": "Route not found"})


@pytest.fixture()
def api() -> TestClient:
    test_client = make_client(route_handler)
    yield test_client
    app.dependency_overrides.clear()


def test_health(api: TestClient) -> None:
    response = api.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "agentCore" in body


def test_create_mission_forwards_to_agent_core(api: TestClient) -> None:
    response = api.post(
        "/missions",
        json={"mission": "Review PR 142 in payments-service"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["missionId"] == "mission-1"
    assert body["status"] == "waiting_for_approval"
    assert body["policyDecision"]["requiresApproval"] is True
    assert body["errors"] == []


def test_create_mission_requires_mission_text(api: TestClient) -> None:
    response = api.post("/missions", json={})

    assert response.status_code == 422


def test_get_mission(api: TestClient) -> None:
    response = api.get("/missions/mission-1")

    assert response.status_code == 200
    body = response.json()
    assert body["missionId"] == "mission-1"
    assert body["state"]["currentStep"] == "approval_gate"


def test_get_missing_mission_maps_to_404(api: TestClient) -> None:
    response = api.get("/missions/missing")

    assert response.status_code == 404


def test_approve_decision(api: TestClient) -> None:
    response = api.post(
        "/missions/mission-1/decision",
        json={"decision": "approve"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["currentStep"] == "audit_actions"


def test_reject_decision(api: TestClient) -> None:
    response = api.post(
        "/missions/mission-1/decision",
        json={"decision": "reject"},
    )

    assert response.status_code == 200
    assert response.json()["missionId"] == "mission-1"


def test_invalid_decision_is_rejected(api: TestClient) -> None:
    response = api.post(
        "/missions/mission-1/decision",
        json={"decision": "maybe"},
    )

    assert response.status_code == 422


def test_agent_core_failure_maps_to_502(api: TestClient) -> None:
    response = api.post(
        "/missions",
        json={"mission": "unreachable"},
    )

    assert response.status_code == 502
