from datetime import UTC, datetime
from typing import Any

import httpx

from app.integrations.contracts import (
    AdapterHealth,
    ApprovedWriteContext,
    ExternalRecord,
    IntegrationCapability,
    require_approval,
)
from app.integrations.github_auth import GitHubTokenManager
from app.integrations.http import VendorHttpClient
from app.models import IntegrationProvider


class GitHubAdapter:
    provider = IntegrationProvider.GITHUB
    capabilities = [
        IntegrationCapability(
            operation="repository.get", access="read", description="Repository metadata"
        ),
        IntegrationCapability(
            operation="pull_request.get",
            access="read",
            description="Pull request metadata and diff",
        ),
        IntegrationCapability(
            operation="pull_request.files",
            access="read",
            description="Pull request changed files",
        ),
        IntegrationCapability(
            operation="pull_request.commits",
            access="read",
            description="Pull request commits",
        ),
        IntegrationCapability(
            operation="pull_request.list", access="read", description="Repository pull requests"
        ),
        IntegrationCapability(
            operation="contents.get", access="read", description="CODEOWNERS and repository files"
        ),
        IntegrationCapability(
            operation="pull_request.comment",
            access="write",
            description="Post an approved pull request comment",
        ),
        IntegrationCapability(
            operation="pull_request.review",
            access="write",
            description="Submit an approved pull request review",
        ),
    ]

    def __init__(
        self,
        token: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
        *,
        refresh_token: str = "",
        token_expires_at: datetime | None = None,
        oauth_client_id: str = "",
        oauth_client_secret: str = "",
    ):
        self.token_manager = GitHubTokenManager(
            access_token=token,
            refresh_token=refresh_token,
            expires_at=token_expires_at,
            client_id=oauth_client_id,
            client_secret=oauth_client_secret,
            transport=transport,
        )
        self.configured = self.token_manager.configured
        self.http = VendorHttpClient(
            self.provider,
            "https://api.github.com",
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout,
            transport,
        )

    async def _ensure_token(self) -> None:
        token = await self.token_manager.ensure_valid()
        self.http.client.headers["Authorization"] = f"Bearer {token}"

    async def health(self) -> AdapterHealth:
        if not self.configured:
            return AdapterHealth(
                provider=self.provider,
                connected=False,
                detail="Missing GITHUB_TOKEN",
                checked_at=datetime.now(UTC),
            )
        await self._ensure_token()
        data = await self.http.request("GET", "/user")
        return AdapterHealth(
            provider=self.provider,
            connected=True,
            detail=f"Authenticated as {data.get('login', 'GitHub user')}",
            checked_at=datetime.now(UTC),
        )

    async def get_repository(self, full_name: str) -> ExternalRecord:
        await self._ensure_token()
        data: dict[str, Any] = await self.http.request("GET", f"/repos/{full_name}")
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data["id"]),
            url=data.get("html_url"),
            title=str(data.get("full_name", full_name)),
            data=data,
        )

    async def get_pull_request(self, full_name: str, number: int) -> ExternalRecord:
        await self._ensure_token()
        data: dict[str, Any] = await self.http.request("GET", f"/repos/{full_name}/pulls/{number}")
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data["id"]),
            url=data.get("html_url"),
            title=str(data.get("title", f"PR #{number}")),
            data=data,
        )

    async def list_pull_requests(self, full_name: str, state: str = "open") -> list[dict[str, Any]]:
        await self._ensure_token()
        data: list[dict[str, Any]] = await self.http.request(
            "GET", f"/repos/{full_name}/pulls", params={"state": state}
        )
        return data

    async def get_pull_request_files(self, full_name: str, number: int) -> list[dict[str, Any]]:
        await self._ensure_token()
        data: list[dict[str, Any]] = await self.http.request(
            "GET", f"/repos/{full_name}/pulls/{number}/files", params={"per_page": 100}
        )
        return data

    async def get_pull_request_commits(self, full_name: str, number: int) -> list[dict[str, Any]]:
        await self._ensure_token()
        data: list[dict[str, Any]] = await self.http.request(
            "GET", f"/repos/{full_name}/pulls/{number}/commits", params={"per_page": 100}
        )
        return data

    async def get_contents(
        self, full_name: str, path: str, ref: str | None = None
    ) -> dict[str, Any]:
        await self._ensure_token()
        params = {"ref": ref} if ref else None
        data: dict[str, Any] = await self.http.request(
            "GET", f"/repos/{full_name}/contents/{path.lstrip('/')}", params=params
        )
        return data

    async def create_pull_request_comment(
        self,
        full_name: str,
        number: int,
        body: str,
        approval: ApprovedWriteContext | None,
    ) -> ExternalRecord:
        require_approval(approval)
        await self._ensure_token()
        data: dict[str, Any] = await self.http.request(
            "POST", f"/repos/{full_name}/issues/{number}/comments", json={"body": body}
        )
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data["id"]),
            url=data.get("html_url"),
            title=f"GitHub comment on PR #{number}",
            data=data,
        )

    async def create_pull_request_review(
        self,
        full_name: str,
        number: int,
        body: str,
        event: str,
        approval: ApprovedWriteContext | None,
    ) -> ExternalRecord:
        require_approval(approval)
        await self._ensure_token()
        if event not in {"COMMENT", "APPROVE", "REQUEST_CHANGES"}:
            raise ValueError("Unsupported GitHub review event")
        data: dict[str, Any] = await self.http.request(
            "POST",
            f"/repos/{full_name}/pulls/{number}/reviews",
            json={"body": body, "event": event},
        )
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data["id"]),
            url=data.get("html_url"),
            title=f"GitHub review on PR #{number}",
            data=data,
        )

    async def get_issue_comment(self, comment_id: str) -> ExternalRecord:
        await self._ensure_token()
        repository, raw_id = comment_id.split(":", 1)
        data: dict[str, Any] = await self.http.request(
            "GET", f"/repos/{repository}/issues/comments/{raw_id}"
        )
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data["id"]),
            url=data.get("html_url"),
            title="GitHub pull request comment",
            data=data,
        )

    async def get_pull_request_review(self, review_id: str) -> ExternalRecord:
        await self._ensure_token()
        repository, raw_id = review_id.split(":", 1)
        data: dict[str, Any] = await self.http.request(
            "GET", f"/repos/{repository}/pulls/reviews/{raw_id}"
        )
        return ExternalRecord(
            provider=self.provider,
            external_id=str(data["id"]),
            url=data.get("html_url"),
            title="GitHub pull request review",
            data=data,
        )

    async def revoke_token(self) -> None:
        await self.token_manager.revoke()

    async def close(self) -> None:
        await self.http.close()
