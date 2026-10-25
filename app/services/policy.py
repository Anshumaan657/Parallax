from dataclasses import dataclass
from typing import Any

from app.agent.contracts import ALLOWED_PROPOSALS, AgentProposal
from app.models import IntegrationProvider


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    approval_required: bool
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "approval_required": self.approval_required,
            "reasons": self.reasons,
        }


def evaluate_actions(
    actions: list[AgentProposal], evidence_keys: set[str], confidence: float
) -> PolicyResult:
    reasons: list[str] = []
    if not actions:
        reasons.append("At least one action is required")
    if confidence < 0.3:
        reasons.append("Agent confidence is below the minimum policy threshold")
    for index, action in enumerate(actions, start=1):
        label = f"Action {index}"
        if action.operation not in ALLOWED_PROPOSALS[action.provider]:
            reasons.append(f"{label} uses unsupported operation {action.operation}")
        unknown = set(action.citations) - evidence_keys
        if unknown:
            reasons.append(f"{label} cites unknown evidence")
        if action.provider == IntegrationProvider.GITHUB:
            repository = action.payload.get("repository")
            pull_number = action.payload.get("pull_number")
            body = action.payload.get("body")
            if not isinstance(repository, str) or not repository.strip():
                reasons.append(f"{label} requires a GitHub repository")
            if not isinstance(pull_number, int) or pull_number < 1:
                reasons.append(f"{label} requires a valid GitHub pull number")
            if not isinstance(body, str) or not body.strip() or len(body) > 10_000:
                reasons.append(
                    f"{label} requires a non-empty GitHub body of at most 10,000 characters"
                )
            if action.operation == "pull_request.review" and action.payload.get("event") not in {
                "COMMENT",
                "APPROVE",
                "REQUEST_CHANGES",
            }:
                reasons.append(f"{label} requires a supported GitHub review event")
        if action.provider == IntegrationProvider.JIRA:
            if action.operation == "issue.create" and not isinstance(
                action.payload.get("fields"), dict
            ):
                reasons.append(f"{label} requires Jira fields")
            if action.operation == "issue.update" and not action.payload.get("key"):
                reasons.append(f"{label} requires a Jira issue key")
        if action.provider == IntegrationProvider.NOTION and (
            not action.payload.get("page_id")
            or not isinstance(action.payload.get("children"), list)
        ):
            reasons.append(f"{label} requires a Notion page_id and children")
        if action.provider == IntegrationProvider.SLACK and not action.payload.get("text"):
            reasons.append(f"{label} requires Slack message text")
    return PolicyResult(allowed=not reasons, approval_required=True, reasons=reasons)
