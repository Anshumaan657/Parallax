import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies import RequestIdentity, get_current_identity, require_roles
from app.integrations.contracts import AdapterError
from app.integrations.registry import build_adapter, build_github_adapter
from app.models import (
    AuditEvent,
    Integration,
    IntegrationProvider,
    IntegrationStatus,
    Project,
    Repository,
    WorkspaceRole,
)
from app.schemas import (
    ErrorResponse,
    GitHubRepositoryCreate,
    GitHubRepositoryRead,
    GitHubRepositoryUpdate,
    IntegrationCapabilitiesRead,
    IntegrationCapabilityRead,
    IntegrationStatusRead,
)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])
ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
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
            detail=(record.configuration.get("last_message") if record else None)
            or (record.display_name if record else "Not configured"),
        )
        for provider in IntegrationProvider
    ]


@router.get(
    "/{provider}/capabilities",
    response_model=IntegrationCapabilitiesRead,
    responses=ERRORS,
    summary="Describe integration capabilities",
)
async def capabilities(
    provider: IntegrationProvider,
    _: RequestIdentity = Depends(get_current_identity),
) -> IntegrationCapabilitiesRead:
    adapter = build_adapter(provider)
    try:
        return IntegrationCapabilitiesRead(
            name=DISPLAY[provider],
            mode=settings.integration_mode,
            capabilities=[
                IntegrationCapabilityRead(
                    operation=item.operation,
                    access=item.access,
                    description=item.description,
                )
                for item in adapter.capabilities
            ],
        )
    finally:
        await adapter.close()


@router.post(
    "/{provider}/check",
    response_model=IntegrationStatusRead,
    responses=ERRORS,
    summary="Check an integration connection",
)
async def check_integration(
    provider: IntegrationProvider,
    request: Request,
    identity: RequestIdentity = Depends(
        require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MANAGER)
    ),
    session: AsyncSession = Depends(get_session),
) -> IntegrationStatusRead:
    record = (
        await session.execute(
            select(Integration).where(
                Integration.workspace_id == identity.workspace.id,
                Integration.provider == provider,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    adapter = build_adapter(provider)
    try:
        health = await adapter.health()
    except AdapterError as exc:
        record.status = IntegrationStatus.ERROR
        record.configuration = {**record.configuration, "last_message": str(exc)}
        await session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from None
    finally:
        await adapter.close()
    record.status = (
        IntegrationStatus.CONNECTED if health.connected else IntegrationStatus.DISCONNECTED
    )
    record.last_checked_at = health.checked_at
    record.configuration = {
        **record.configuration,
        "mode": settings.integration_mode,
        "last_message": health.detail,
    }
    session.add(
        AuditEvent(
            workspace_id=identity.workspace.id,
            actor_user_id=identity.user.id,
            mission_id=None,
            event_type="integration.connection_checked",
            correlation_id=request.state.correlation_id,
            payload={
                "provider": provider.value,
                "connected": health.connected,
                "mode": settings.integration_mode,
            },
        )
    )
    await session.commit()
    return IntegrationStatusRead(
        name=DISPLAY[provider], connected=health.connected, detail=health.detail
    )


@router.post(
    "/github/revoke",
    response_model=IntegrationStatusRead,
    responses={**ERRORS, 502: {"model": ErrorResponse}},
    summary="Revoke the configured GitHub token",
)
async def revoke_github_token(
    request: Request,
    identity: RequestIdentity = Depends(
        require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MANAGER)
    ),
    session: AsyncSession = Depends(get_session),
) -> IntegrationStatusRead:
    record = (
        await session.execute(
            select(Integration).where(
                Integration.workspace_id == identity.workspace.id,
                Integration.provider == IntegrationProvider.GITHUB,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="GitHub integration not found")
    adapter = build_github_adapter()
    try:
        await adapter.revoke_token()
    except AdapterError as exc:
        record.status = IntegrationStatus.ERROR
        record.configuration = {**record.configuration, "last_message": str(exc)}
        await session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from None
    finally:
        await adapter.close()
    record.status = IntegrationStatus.DISCONNECTED
    record.last_checked_at = None
    record.configuration = {
        **record.configuration,
        "last_message": "GitHub token revoked",
        "mode": settings.integration_mode,
    }
    session.add(
        AuditEvent(
            workspace_id=identity.workspace.id,
            actor_user_id=identity.user.id,
            mission_id=None,
            event_type="integration.token_revoked",
            correlation_id=request.state.correlation_id,
            payload={"provider": IntegrationProvider.GITHUB.value},
        )
    )
    await session.commit()
    return IntegrationStatusRead(
        name="GitHub", connected=False, detail="GitHub token revoked"
    )


@router.get(
    "/github/repositories",
    response_model=list[GitHubRepositoryRead],
    responses=ERRORS,
    summary="List registered GitHub repositories",
)
async def list_github_repositories(
    identity: RequestIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> list[GitHubRepositoryRead]:
    repositories = (
        await session.execute(
            select(Repository)
            .where(
                Repository.workspace_id == identity.workspace.id,
                Repository.provider == IntegrationProvider.GITHUB,
            )
            .order_by(Repository.full_name)
        )
    ).scalars()
    return [
        GitHubRepositoryRead(
            id=repository.id,
            full_name=repository.full_name,
            external_id=repository.external_id,
            project_id=repository.project_id,
            default_branch=repository.default_branch,
            webhook_enabled=repository.webhook_enabled,
            webhook_events=repository.webhook_events,
            created_at=repository.created_at,
        )
        for repository in repositories
    ]


@router.post(
    "/github/repositories",
    response_model=GitHubRepositoryRead,
    status_code=201,
    responses={**ERRORS, 409: {"model": ErrorResponse}},
    summary="Register a GitHub repository",
)
async def register_github_repository(
    payload: GitHubRepositoryCreate,
    identity: RequestIdentity = Depends(
        require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MANAGER)
    ),
    session: AsyncSession = Depends(get_session),
) -> GitHubRepositoryRead:
    project = None
    if payload.project_id is not None:
        project = await session.scalar(
            select(Project).where(
                Project.id == payload.project_id,
                Project.workspace_id == identity.workspace.id,
            )
        )
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
    if project is None:
        project = await session.scalar(
            select(Project).where(
                Project.workspace_id == identity.workspace.id,
                Project.name == "General",
            )
        )
        if project is None:
            raise HTTPException(status_code=409, detail="Default project is not configured")

    adapter = build_github_adapter()
    try:
        remote = await adapter.get_repository(payload.full_name)
    except AdapterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    finally:
        await adapter.close()

    repository = Repository(
        workspace_id=identity.workspace.id,
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        external_id=remote.external_id,
        full_name=payload.full_name,
        default_branch=payload.default_branch,
        webhook_enabled=True,
        webhook_events=["opened", "reopened", "synchronize", "ready_for_review"],
    )
    session.add(repository)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="GitHub repository is already registered"
        ) from None
    await session.refresh(repository)
    return GitHubRepositoryRead(
        id=repository.id,
        full_name=repository.full_name,
        external_id=repository.external_id,
        project_id=repository.project_id,
        default_branch=repository.default_branch,
        webhook_enabled=repository.webhook_enabled,
        webhook_events=repository.webhook_events,
        created_at=repository.created_at,
    )


@router.patch(
    "/github/repositories/{repository_id}",
    response_model=GitHubRepositoryRead,
    responses={**ERRORS, 409: {"model": ErrorResponse}},
    summary="Update a registered GitHub repository",
)
async def update_github_repository(
    repository_id: uuid.UUID,
    payload: GitHubRepositoryUpdate,
    identity: RequestIdentity = Depends(
        require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MANAGER)
    ),
    session: AsyncSession = Depends(get_session),
) -> GitHubRepositoryRead:
    repository = await session.scalar(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.workspace_id == identity.workspace.id,
            Repository.provider == IntegrationProvider.GITHUB,
        )
    )
    if repository is None:
        raise HTTPException(status_code=404, detail="GitHub repository not found")
    repository.default_branch = payload.default_branch
    repository.webhook_enabled = payload.webhook_enabled
    repository.webhook_events = payload.webhook_events
    await session.commit()
    await session.refresh(repository)
    return GitHubRepositoryRead(
        id=repository.id,
        full_name=repository.full_name,
        external_id=repository.external_id,
        project_id=repository.project_id,
        default_branch=repository.default_branch,
        webhook_enabled=repository.webhook_enabled,
        webhook_events=repository.webhook_events,
        created_at=repository.created_at,
    )


@router.delete(
    "/github/repositories/{repository_id}",
    status_code=204,
    responses={**ERRORS, 204: {"description": "Repository removed"}},
    summary="Remove a registered GitHub repository",
)
async def remove_github_repository(
    repository_id: uuid.UUID,
    identity: RequestIdentity = Depends(
        require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)
    ),
    session: AsyncSession = Depends(get_session),
) -> None:
    repository = await session.scalar(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.workspace_id == identity.workspace.id,
            Repository.provider == IntegrationProvider.GITHUB,
        )
    )
    if repository is None:
        raise HTTPException(status_code=404, detail="GitHub repository not found")
    await session.delete(repository)
    await session.commit()
