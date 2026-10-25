import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models import (
    GitHubWebhookDelivery,
    IntegrationProvider,
    Mission,
    MissionStatus,
    MissionTransition,
    OutboxJob,
    Project,
    Repository,
    WorkspaceMembership,
    WorkspaceRole,
)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
SUPPORTED_PULL_REQUEST_ACTIONS = {"opened", "reopened", "synchronize", "ready_for_review"}


def _verify_signature(body: bytes, signature: str | None) -> bool:
    secret = settings.github_webhook_secret.get_secret_value()
    if not secret or not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post(
    "/github",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive a GitHub webhook",
)
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(default=None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    body = await request.body()
    if not _verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature")
    if not x_github_event or not x_github_delivery:
        raise HTTPException(status_code=400, detail="Missing GitHub webhook headers")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid GitHub webhook payload") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid GitHub webhook payload")

    repository_payload = payload.get("repository")
    full_name = (
        repository_payload.get("full_name") if isinstance(repository_payload, dict) else None
    )
    if not isinstance(full_name, str) or not full_name.strip():
        raise HTTPException(status_code=400, detail="GitHub repository is missing")

    existing = await session.scalar(
        select(GitHubWebhookDelivery).where(
            GitHubWebhookDelivery.delivery_id == x_github_delivery
        )
    )
    if existing is not None:
        return {"accepted": True, "duplicate": True, "delivery_id": x_github_delivery}

    repository = await session.scalar(
        select(Repository).where(
            Repository.provider == IntegrationProvider.GITHUB,
            Repository.full_name == full_name.strip(),
        )
    )
    if repository is None:
        # A valid webhook for an unregistered repository is acknowledged so GitHub
        # does not retry it, but no workspace data is created or exposed.
        return {
            "accepted": False,
            "reason": "repository_not_registered",
            "delivery_id": x_github_delivery,
        }

    delivery = GitHubWebhookDelivery(
        workspace_id=repository.workspace_id,
        repository_id=repository.id,
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        action=payload.get("action") if isinstance(payload.get("action"), str) else None,
        repository_full_name=full_name.strip(),
        payload=payload,
        status="received",
    )
    session.add(delivery)

    action = payload.get("action")
    pull_request = payload.get("pull_request")
    is_supported_pull_request = (
        x_github_event == "pull_request"
        and isinstance(action, str)
        and action in SUPPORTED_PULL_REQUEST_ACTIONS
        and isinstance(pull_request, dict)
    )
    if not is_supported_pull_request:
        delivery.status = "ignored"
        await session.commit()
        return {
            "accepted": True,
            "duplicate": False,
            "delivery_id": x_github_delivery,
            "status": "ignored",
        }

    if repository.project_id is None:
        delivery.status = "ignored"
        await session.commit()
        return {
            "accepted": True,
            "duplicate": False,
            "delivery_id": x_github_delivery,
            "status": "ignored",
            "reason": "repository_project_not_configured",
        }

    project = await session.scalar(
        select(Project).where(
            Project.id == repository.project_id,
            Project.workspace_id == repository.workspace_id,
        )
    )
    creator = await session.scalar(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == repository.workspace_id,
            WorkspaceMembership.role.in_(
                [WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MANAGER]
            ),
        )
        .order_by(WorkspaceMembership.created_at)
        .limit(1)
    )
    pull_number = pull_request.get("number")
    if project is None or creator is None or not isinstance(pull_number, int):
        delivery.status = "ignored"
        await session.commit()
        return {
            "accepted": True,
            "duplicate": False,
            "delivery_id": x_github_delivery,
            "status": "ignored",
            "reason": "repository_configuration_incomplete",
        }

    title = pull_request.get("title")
    title_text = title.strip() if isinstance(title, str) else f"Pull request #{pull_number}"
    mission = Mission(
        workspace_id=repository.workspace_id,
        created_by_user_id=creator.user_id,
        project_id=project.id,
        prompt=(
            f"Review GitHub pull request {full_name}#{pull_number}: {title_text}. "
            "Assess risk, changed files, reviewer needs, and proposed follow-up actions."
        )[:10_000],
        project_name=project.name,
        source_context={
            "provider": "github",
            "repository": full_name.strip(),
            "pull_request_number": pull_number,
            "pull_request_id": pull_request.get("id"),
            "url": pull_request.get("html_url"),
        },
        status=MissionStatus.QUEUED,
        progress_current=0,
        progress_total=1,
        correlation_id=request.state.correlation_id,
    )
    session.add(mission)
    await session.flush()
    delivery.mission_id = mission.id
    delivery.status = "queued"
    session.add_all(
        [
            MissionTransition(
                workspace_id=mission.workspace_id,
                mission_id=mission.id,
                from_status=None,
                to_status=MissionStatus.QUEUED,
                reason="GitHub pull-request webhook accepted",
                actor_user_id=None,
            ),
            OutboxJob(
                workspace_id=mission.workspace_id,
                mission_id=mission.id,
                job_type="prepare_mission",
                payload={"mission_id": str(mission.id), "source": "github_webhook"},
                status="pending",
            ),
        ]
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"accepted": True, "duplicate": True, "delivery_id": x_github_delivery}
    return {
        "accepted": True,
        "duplicate": False,
        "delivery_id": x_github_delivery,
        "status": "queued",
        "mission_id": str(mission.id),
    }
