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
from app.models import GitHubWebhookDelivery, IntegrationProvider, Repository

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


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
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"accepted": True, "duplicate": True, "delivery_id": x_github_delivery}
    return {"accepted": True, "duplicate": False, "delivery_id": x_github_delivery}
