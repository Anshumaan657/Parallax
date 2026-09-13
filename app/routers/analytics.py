import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies import RequestIdentity, get_current_identity
from app.models import (
    ActionProposal,
    AuditEvent,
    ExecutionRecord,
    Integration,
    IntegrationProvider,
    Mission,
    MissionStatus,
    MissionTransition,
)
from app.schemas import (
    AnalyticsOverviewRead,
    AuditEventRead,
    ErrorResponse,
    IntegrationHealthRead,
    MissionSLARead,
    ProviderExecutionRead,
    StatusCountRead,
    TimelineEventRead,
)

router = APIRouter(prefix="/api", tags=["analytics"])
ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
}
DISPLAY = {
    IntegrationProvider.GITHUB: "GitHub",
    IntegrationProvider.JIRA: "Jira",
    IntegrationProvider.NOTION: "Notion",
    IntegrationProvider.SLACK: "Slack",
}


async def _mission(
    session: AsyncSession, workspace_id: uuid.UUID, mission_id: uuid.UUID
) -> Mission:
    mission = await session.scalar(
        select(Mission).where(Mission.id == mission_id, Mission.workspace_id == workspace_id)
    )
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.get(
    "/missions/{mission_id}/timeline",
    response_model=list[TimelineEventRead],
    responses=ERRORS,
    summary="Get the complete mission timeline",
)
async def mission_timeline(
    mission_id: uuid.UUID,
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[TimelineEventRead]:
    await _mission(session, identity.workspace.id, mission_id)
    transitions = list(
        await session.scalars(
            select(MissionTransition)
            .where(
                MissionTransition.workspace_id == identity.workspace.id,
                MissionTransition.mission_id == mission_id,
            )
            .order_by(MissionTransition.created_at, MissionTransition.id)
        )
    )
    return [
        TimelineEventRead(
            id=item.id,
            event_type="mission.transition",
            from_status=item.from_status,
            to_status=item.to_status,
            title=f"Mission {item.to_status.value}",
            detail=item.reason,
            actor_user_id=item.actor_user_id,
            created_at=item.created_at,
        )
        for item in transitions
    ]


@router.get(
    "/audit-events",
    response_model=list[AuditEventRead],
    responses=ERRORS,
    summary="List immutable workspace audit events",
)
async def audit_events(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
    mission_id: uuid.UUID | None = None,
    event_type: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AuditEventRead]:
    statement = select(AuditEvent).where(AuditEvent.workspace_id == identity.workspace.id)
    if mission_id is not None:
        statement = statement.where(AuditEvent.mission_id == mission_id)
    if event_type is not None:
        statement = statement.where(AuditEvent.event_type == event_type)
    records = list(
        await session.scalars(
            statement.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return [
        AuditEventRead(
            id=item.id,
            mission_id=item.mission_id,
            actor_user_id=item.actor_user_id,
            event_type=item.event_type,
            correlation_id=item.correlation_id,
            payload=item.payload,
            created_at=item.created_at,
        )
        for item in records
    ]


@router.get(
    "/missions/{mission_id}/sla",
    response_model=MissionSLARead,
    responses=ERRORS,
    summary="Get mission SLA state",
)
async def mission_sla(
    mission_id: uuid.UUID,
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> MissionSLARead:
    mission = await _mission(session, identity.workspace.id, mission_id)
    created_at = mission.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    age = max(0, int((datetime.now(UTC) - created_at).total_seconds()))
    target = settings.mission_sla_minutes * 60
    terminal = mission.status in {
        MissionStatus.COMPLETED,
        MissionStatus.REJECTED,
        MissionStatus.CANCELLED,
    }
    return MissionSLARead(
        mission_id=mission.id,
        status=mission.status,
        age_seconds=age,
        target_seconds=target,
        remaining_seconds=max(0, target - age),
        breached=not terminal and age > target,
    )


@router.get(
    "/analytics/overview",
    response_model=AnalyticsOverviewRead,
    responses=ERRORS,
    summary="Get workspace mission and execution analytics",
)
async def analytics_overview(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> AnalyticsOverviewRead:
    status_rows = (
        await session.execute(
            select(Mission.status, func.count(Mission.id))
            .where(Mission.workspace_id == identity.workspace.id)
            .group_by(Mission.status)
        )
    ).all()
    counts = {status: int(count) for status, count in status_rows}
    total = sum(counts.values())
    completed = counts.get(MissionStatus.COMPLETED, 0)
    execution_rows = (
        await session.execute(
            select(ExecutionRecord.status, func.count(ExecutionRecord.id))
            .where(ExecutionRecord.workspace_id == identity.workspace.id)
            .group_by(ExecutionRecord.status)
        )
    ).all()
    execution_counts = {status: int(count) for status, count in execution_rows}
    execution_total = sum(execution_counts.values())
    provider_rows = (
        await session.execute(
            select(ActionProposal.provider, ExecutionRecord.status, func.count(ExecutionRecord.id))
            .join(ActionProposal, ActionProposal.id == ExecutionRecord.action_proposal_id)
            .where(ExecutionRecord.workspace_id == identity.workspace.id)
            .group_by(ActionProposal.provider, ExecutionRecord.status)
        )
    ).all()
    by_provider: dict[IntegrationProvider, dict[str, int]] = {}
    for provider, status, count in provider_rows:
        by_provider.setdefault(provider, {})[status] = int(count)
    completion_times = (
        await session.execute(
            select(Mission.created_at, Mission.updated_at).where(
                Mission.workspace_id == identity.workspace.id,
                Mission.status == MissionStatus.COMPLETED,
            )
        )
    ).all()
    durations = [(updated - created).total_seconds() for created, updated in completion_times]
    completed_duration = sum(durations) / len(durations) if durations else None
    return AnalyticsOverviewRead(
        total_missions=total,
        completion_rate_pct=round((completed / total * 100) if total else 0.0, 2),
        verification_rate_pct=round(
            (execution_counts.get("verified", 0) / execution_total * 100)
            if execution_total
            else 0.0,
            2,
        ),
        average_completion_seconds=(
            round(float(completed_duration), 2) if completed_duration else None
        ),
        missions_by_status=[
            StatusCountRead(status=status, count=counts.get(status, 0)) for status in MissionStatus
        ],
        executions_by_provider=[
            ProviderExecutionRead(
                provider=provider,
                verified=by_provider.get(provider, {}).get("verified", 0),
                failed=by_provider.get(provider, {}).get("failed", 0),
            )
            for provider in IntegrationProvider
        ],
    )


@router.get(
    "/integrations/health",
    response_model=list[IntegrationHealthRead],
    responses=ERRORS,
    summary="Get stored health for all four integrations",
)
async def integration_health(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[IntegrationHealthRead]:
    records = list(
        await session.scalars(
            select(Integration).where(Integration.workspace_id == identity.workspace.id)
        )
    )
    by_provider = {item.provider: item for item in records}
    return [
        IntegrationHealthRead(
            name=DISPLAY[provider],
            status=(record.status.value if (record := by_provider.get(provider)) else "missing"),
            mode=settings.integration_mode,
            last_checked_at=record.last_checked_at if record else None,
            detail=(record.configuration.get("last_message") if record else None)
            or "Connection has not been checked",
        )
        for provider in IntegrationProvider
    ]
