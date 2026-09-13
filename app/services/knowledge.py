"""Mission knowledge base: append-only facts with provenance.

The knowledge base is the persistent operational memory of a mission.
It is append-only: facts are never updated in place and never deleted.
A new observation for the same subject (mission, kind, source, source_ref)
supersedes the previous live fact; contradictory observations can mark a
fact conflicted so the agent is warned instead of trusting stale memory.

Two knowledge kinds are strictly separated:

- ``source_fact``: what an integration actually returned (GitHub, Jira,
  Notion, Slack). This is observed knowledge.
- ``decision``: what the agent concluded. This is derived knowledge and is
  never treated as source truth.

The mission context pack built here is the bounded read-model the agent
receives on every call: current task, latest verified facts, recent
actions, pending actions, conflicts and recent decisions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActionProposal,
    ExecutionRecord,
    IntegrationProvider,
    KnowledgeFact,
    KnowledgeFactKind,
    KnowledgeFactStatus,
    KnowledgeSource,
    Mission,
    VerificationRecord,
)

_LIVE_STATUSES = (KnowledgeFactStatus.OBSERVED, KnowledgeFactStatus.VERIFIED)

_MAX_CONTEXT_FACTS_PER_SOURCE = 6
_MAX_CONTEXT_DECISIONS = 5
_MAX_CONTEXT_ACTIONS = 5

_SOURCE_BY_PROVIDER: dict[IntegrationProvider, KnowledgeSource] = {
    IntegrationProvider.GITHUB: KnowledgeSource.GITHUB,
    IntegrationProvider.JIRA: KnowledgeSource.JIRA,
    IntegrationProvider.NOTION: KnowledgeSource.NOTION,
    IntegrationProvider.SLACK: KnowledgeSource.SLACK,
}


def knowledge_source_for(provider: IntegrationProvider) -> KnowledgeSource:
    """Map an integration provider to its knowledge source."""
    return _SOURCE_BY_PROVIDER[provider]


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def _live_subject_facts(
    session: AsyncSession,
    mission_id: uuid.UUID,
    *,
    kind: KnowledgeFactKind,
    source: KnowledgeSource,
    source_ref: str,
) -> list[KnowledgeFact]:
    """Latest-first list of live facts for one subject of a mission."""
    return list(
        (
            await session.execute(
                select(KnowledgeFact)
                .where(
                    KnowledgeFact.mission_id == mission_id,
                    KnowledgeFact.kind == kind,
                    KnowledgeFact.source == source,
                    KnowledgeFact.source_ref == source_ref,
                    KnowledgeFact.status.in_(_LIVE_STATUSES),
                )
                .order_by(KnowledgeFact.observed_at.desc(), KnowledgeFact.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


async def record_fact(
    session: AsyncSession,
    mission: Mission,
    *,
    kind: KnowledgeFactKind,
    source: KnowledgeSource,
    source_ref: str,
    fact: str,
    data: dict[str, Any] | None = None,
    agent_run_id: uuid.UUID | None = None,
    confidence: float | None = None,
    verified: bool = False,
) -> KnowledgeFact:
    """Append a fact to the mission knowledge base.

    Append-only semantics:

    - Identical live fact for the same subject -> the existing fact is
      returned unchanged (idempotent, no duplicate rows).
    - Different value for the same subject -> previous live facts are
      marked ``superseded`` and linked to the new fact; the new fact
      becomes the only live one for that subject.

    The caller owns the transaction (``session.commit()``).
    """
    normalized_fact = fact.strip()
    live_facts = await _live_subject_facts(
        session,
        mission.id,
        kind=kind,
        source=source,
        source_ref=source_ref,
    )

    for existing in live_facts:
        if existing.fact.strip() == normalized_fact:
            return existing

    new_fact = KnowledgeFact(
        workspace_id=mission.workspace_id,
        mission_id=mission.id,
        kind=kind,
        source=source,
        source_ref=source_ref,
        fact=normalized_fact,
        data=data or {},
        status=KnowledgeFactStatus.VERIFIED if verified else KnowledgeFactStatus.OBSERVED,
        verified_at=_utcnow() if verified else None,
        agent_run_id=agent_run_id,
        confidence=confidence,
    )
    session.add(new_fact)
    await session.flush()  # assign new_fact.id for supersede links

    for stale in live_facts:
        stale.status = KnowledgeFactStatus.SUPERSEDED
        stale.superseded_by_id = new_fact.id

    return new_fact


def mark_fact_verified(
    session: AsyncSession,
    fact: KnowledgeFact,
) -> KnowledgeFact:
    """Promote an observed fact to verified (read-after-write confirmation)."""
    if fact.status is KnowledgeFactStatus.VERIFIED:
        return fact
    if fact.status not in (KnowledgeFactStatus.OBSERVED, KnowledgeFactStatus.CONFLICTED):
        raise ValueError(f"Fact {fact.id} in status {fact.status.value} cannot be verified")
    fact.status = KnowledgeFactStatus.VERIFIED
    fact.verified_at = _utcnow()
    return fact


def mark_fact_conflicted(
    session: AsyncSession,
    fact: KnowledgeFact,
    *,
    reason: str,
) -> KnowledgeFact:
    """Flag a fact as conflicted: fresh source data contradicts it."""
    fact.status = KnowledgeFactStatus.CONFLICTED
    fact.data = {**fact.data, "conflict_reason": reason}
    return fact


def _fact_payload(fact: KnowledgeFact) -> dict[str, Any]:
    return {
        "id": str(fact.id),
        "kind": fact.kind.value,
        "source": fact.source.value,
        "source_ref": fact.source_ref,
        "fact": fact.fact,
        "observed_at": fact.observed_at.isoformat(),
        "verified_at": fact.verified_at.isoformat() if fact.verified_at else None,
        "status": fact.status.value,
        "confidence": fact.confidence,
        "data": fact.data,
    }


async def build_mission_context(
    session: AsyncSession,
    mission: Mission,
    *,
    max_facts_per_source: int = _MAX_CONTEXT_FACTS_PER_SOURCE,
    max_decisions: int = _MAX_CONTEXT_DECISIONS,
    max_actions: int = _MAX_CONTEXT_ACTIONS,
) -> dict[str, Any]:
    """Assemble the bounded mission context pack for the next agent call.

    Contents (deterministically ordered, newest first, size-capped):

    - the current task and mission status
    - latest live facts per source (verified first, then observed;
      conflicts included)
    - recent decisions (derived knowledge, clearly separated)
    - recent and pending actions with their execution outcomes
    - open conflicts / uncertainties

    Keys are snake_case to match the backend agent contracts; adapters
    translate to agent-core payloads when bridging services.
    """
    facts = list(
        (
            await session.execute(
                select(KnowledgeFact)
                .where(
                    KnowledgeFact.mission_id == mission.id,
                    KnowledgeFact.kind == KnowledgeFactKind.SOURCE_FACT,
                    KnowledgeFact.status.in_(
                        (
                            KnowledgeFactStatus.OBSERVED,
                            KnowledgeFactStatus.VERIFIED,
                            KnowledgeFactStatus.CONFLICTED,
                        )
                    ),
                )
                .order_by(KnowledgeFact.observed_at.desc(), KnowledgeFact.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    per_source_counts: dict[KnowledgeSource, int] = {}
    selected_facts: list[KnowledgeFact] = []
    # Verified facts first so they survive the per-source caps.
    for fact in sorted(
        facts,
        key=lambda item: (
            0 if item.status is KnowledgeFactStatus.VERIFIED else 1,
            item.observed_at,
        ),
    ):
        if per_source_counts.get(fact.source, 0) >= max_facts_per_source:
            continue
        per_source_counts[fact.source] = per_source_counts.get(fact.source, 0) + 1
        selected_facts.append(fact)

    decisions = list(
        (
            await session.execute(
                select(KnowledgeFact)
                .where(
                    KnowledgeFact.mission_id == mission.id,
                    KnowledgeFact.kind == KnowledgeFactKind.DECISION,
                    KnowledgeFact.status.in_(_LIVE_STATUSES),
                )
                .order_by(KnowledgeFact.observed_at.desc())
                .limit(max_decisions)
            )
        )
        .scalars()
        .all()
    )

    proposals = list(
        (
            await session.execute(
                select(ActionProposal)
                .where(ActionProposal.mission_id == mission.id)
                .order_by(ActionProposal.created_at.desc())
                .limit(max_actions)
            )
        )
        .scalars()
        .all()
    )
    executions = {
        record.action_proposal_id: record
        for record in (
            await session.execute(
                select(ExecutionRecord).where(ExecutionRecord.mission_id == mission.id)
            )
        )
        .scalars()
        .all()
    }
    verifications = {
        record.execution_id: record
        for record in (
            await session.execute(
                select(VerificationRecord).where(VerificationRecord.mission_id == mission.id)
            )
        )
        .scalars()
        .all()
    }

    recent_actions: list[dict[str, Any]] = []
    pending_actions: list[dict[str, Any]] = []
    verified_outcomes: list[dict[str, Any]] = []
    for proposal in proposals:
        execution = executions.get(proposal.id)
        verification = verifications.get(execution.id) if execution else None
        entry: dict[str, Any] = {
            "id": str(proposal.id),
            "provider": proposal.provider.value,
            "operation": proposal.operation,
            "rationale": proposal.rationale,
            "status": proposal.status,
        }
        if execution is not None:
            entry["execution_status"] = execution.status
            entry["external_id"] = execution.external_id
        if verification is not None:
            entry["verification_status"] = verification.status
        if proposal.status in ("proposed", "pending"):
            pending_actions.append(entry)
        else:
            recent_actions.append(entry)
            if verification is not None and verification.status == "verified":
                verified_outcomes.append(entry)

    conflicts = [
        _fact_payload(fact) for fact in facts if fact.status is KnowledgeFactStatus.CONFLICTED
    ]

    return {
        "task": mission.prompt,
        "mission_status": mission.status.value,
        "result_summary": mission.result_summary,
        "facts": [_fact_payload(fact) for fact in selected_facts],
        "decisions": [_fact_payload(fact) for fact in decisions],
        "recent_actions": recent_actions,
        "pending_actions": pending_actions,
        "verified_outcomes": verified_outcomes,
        "conflicts": conflicts,
    }


async def kb_metrics(session: AsyncSession, mission: Mission) -> dict[str, int]:
    """Knowledge-quality counters for the dashboard (context/memory quality)."""
    facts = list(
        (
            await session.execute(select(KnowledgeFact).where(KnowledgeFact.mission_id == mission.id))
        )
        .scalars()
        .all()
    )

    return {
        "total_facts": len(facts),
        "live_facts": sum(1 for fact in facts if fact.status in _LIVE_STATUSES),
        "verified_facts": sum(1 for fact in facts if fact.status is KnowledgeFactStatus.VERIFIED),
        "conflicted_facts": sum(
            1 for fact in facts if fact.status is KnowledgeFactStatus.CONFLICTED
        ),
        "superseded_facts": sum(
            1 for fact in facts if fact.status is KnowledgeFactStatus.SUPERSEDED
        ),
        "decisions": sum(1 for fact in facts if fact.kind is KnowledgeFactKind.DECISION),
    }


