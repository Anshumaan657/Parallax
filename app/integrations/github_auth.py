from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from app.integrations.contracts import AdapterError
from app.models import IntegrationProvider


@dataclass
class GitHubTokenManager:
    access_token: str
    refresh_token: str = ""
    expires_at: datetime | None = None
    client_id: str = ""
    client_secret: str = ""
    transport: httpx.AsyncBaseTransport | None = None
    refresh_skew_seconds: int = 60

    @property
    def configured(self) -> bool:
        return bool(self.access_token)

    @property
    def expired(self) -> bool:
        if not self.expires_at:
            return False
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC) + timedelta(seconds=self.refresh_skew_seconds)

    async def ensure_valid(self) -> str:
        if not self.access_token:
            raise AdapterError(IntegrationProvider.GITHUB, "Missing GITHUB_TOKEN")
        if not self.expired:
            return self.access_token
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise AdapterError(
                IntegrationProvider.GITHUB,
                "GitHub access token expired and refresh is not configured",
            )
        await self.refresh()
        return self.access_token

    async def refresh(self) -> str:
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise AdapterError(
                IntegrationProvider.GITHUB, "GitHub refresh credentials are incomplete"
            )
        async with httpx.AsyncClient(
            base_url="https://github.com", timeout=15, transport=self.transport
        ) as client:
            try:
                response = await client.post(
                    "/login/oauth/access_token",
                    json={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token",
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise AdapterError(
                    IntegrationProvider.GITHUB,
                    "GitHub token refresh failed",
                    retryable=True,
                ) from exc
        if not isinstance(data, dict) or not data.get("access_token"):
            raise AdapterError(IntegrationProvider.GITHUB, "GitHub token refresh returned no token")
        self.access_token = str(data["access_token"])
        if data.get("refresh_token"):
            self.refresh_token = str(data["refresh_token"])
        expires_in = data.get("expires_in")
        self.expires_at = (
            datetime.now(UTC) + timedelta(seconds=int(expires_in))
            if expires_in is not None
            else None
        )
        return self.access_token

    async def revoke(self) -> None:
        if not self.access_token or not self.client_id or not self.client_secret:
            raise AdapterError(
                IntegrationProvider.GITHUB, "GitHub revocation credentials are incomplete"
            )
        async with httpx.AsyncClient(
            base_url="https://api.github.com", timeout=15, transport=self.transport
        ) as client:
            try:
                response = await client.request(
                    "DELETE",
                    f"/applications/{self.client_id}/token",
                    auth=(self.client_id, self.client_secret),
                    json={"access_token": self.access_token},
                    headers={"Accept": "application/vnd.github+json"},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise AdapterError(
                    IntegrationProvider.GITHUB,
                    "GitHub token revocation failed",
                    retryable=response.status_code >= 500 if "response" in locals() else True,
                ) from exc
        self.access_token = ""
        self.refresh_token = ""
        self.expires_at = None
