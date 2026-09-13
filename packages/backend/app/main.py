"""Parallax FastAPI control-plane.

Responsibilities (per project architecture):
- API routes and request validation
- Forwarding natural-language missions to Agent Core (:4010)
- Relaying mission state, approvals and audit info to callers

Mission planning, approval gating, authorized execution,
verification and auditability live in Agent Core (LangGraph),
NOT here.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .agent_client import AgentCoreClient, AgentCoreError
from .config import AGENT_CORE_URL

app = FastAPI(
    title="Parallax Backend",
    description=(
        "Control-plane API. Missions are planned, approved, executed, "
        "verified and audited by Agent Core."
    ),
    version="0.1.0",
)


async def get_agent_core_client() -> AsyncIterator[AgentCoreClient]:
    client = AgentCoreClient()
    try:
        yield client
    finally:
        await client.aclose()


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------


class MissionRequest(BaseModel):
    mission: str = Field(min_length=1, description="Natural-language mission.")
    missionId: str | None = Field(
        default=None,
        description="Optional client-supplied mission identifier.",
    )


class MissionAck(BaseModel):
    missionId: str
    status: str
    currentStep: str | None = None
    proposedActions: list[Any] = Field(default_factory=list)
    policyDecision: Any = None
    errors: list[str] = Field(default_factory=list)


class MissionDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "agentCore": AGENT_CORE_URL,
    }


@app.post(
    "/missions",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MissionAck,
)
async def create_mission(
    request: MissionRequest,
    client: AgentCoreClient = Depends(get_agent_core_client),
) -> Any:
    """Forward a natural-language mission to Agent Core."""
    try:
        return await client.create_mission(
            mission=request.mission,
            mission_id=request.missionId,
        )
    except AgentCoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.get("/missions/{mission_id}")
async def get_mission(
    mission_id: str,
    client: AgentCoreClient = Depends(get_agent_core_client),
) -> Any:
    """Fetch mission status and full state from Agent Core."""
    try:
        return await client.get_mission(mission_id)
    except AgentCoreError as exc:
        raise _map_agent_core_error(exc) from exc


@app.post("/missions/{mission_id}/decision")
async def decide_mission(
    mission_id: str,
    request: MissionDecisionRequest,
    client: AgentCoreClient = Depends(get_agent_core_client),
) -> Any:
    """Relay the PM's approve/reject decision to Agent Core."""
    try:
        return await client.decide_mission(
            mission_id=mission_id,
            decision=request.decision,
        )
    except AgentCoreError as exc:
        raise _map_agent_core_error(exc) from exc


def _map_agent_core_error(exc: AgentCoreError) -> HTTPException:
    message = str(exc)
    if "404" in message:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=message,
    )


@app.exception_handler(AgentCoreError)
async def agent_core_error_handler(
    _request: Any,
    exc: AgentCoreError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"error": str(exc)},
    )
