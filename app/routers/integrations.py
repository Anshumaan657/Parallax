from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import RequestIdentity, get_current_identity
from app.models import Integration, IntegrationProvider, IntegrationStatus
from app.schemas import ErrorResponse, IntegrationStatusRead

router = APIRouter(prefix="/api/integrations", tags=["integrations"])
ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
}
DISPLAY = {
    IntegrationProvider.GITHUB: "GitHub",
    IntegrationProvider.JIRA: "Jira",
    IntegrationProvider.NOTION: "Notion",
    IntegrationProvider.SLACK: "Slack",
}


@router.get(
    "", response_model=list[IntegrationStatusRead], responses=ERRORS, summary="Integrations"
)
async def integrations(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[IntegrationStatusRead]:
    records = (
        await session.execute(
            select(Integration).where(Integration.workspace_id == identity.workspace.id)
        )
    ).scalars()
    by_provider = {record.provider: record for record in records}
    return [
        IntegrationStatusRead(
            name=DISPLAY[provider],
            connected=(record := by_provider.get(provider)) is not None
            and record.status == IntegrationStatus.CONNECTED,
            detail=record.display_name if record else "Not configured",
        )
        for provider in IntegrationProvider
    ]
