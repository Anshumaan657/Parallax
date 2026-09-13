import asyncio
import contextlib
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from arq import cron
from arq.connections import ArqRedis, RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.database import session_factory
from app.logging import configure_logging
from app.models import Mission, MissionStatus, MissionStep, OutboxJob
from app.services.missions import record_mission_event, transition_mission

configure_logging()
logger = structlog.get_logger()


async def _heartbeat(ctx: dict[str, Any]) -> None:
    redis = ctx["redis"]
    interval = max(3, settings.worker_heartbeat_ttl_seconds // 3)
    while True:
        await redis.set(
            settings.worker_heartbeat_key,
            "up",
            ex=settings.worker_heartbeat_ttl_seconds,
        )
        await asyncio.sleep(interval)


async def startup(ctx: dict[str, Any]) -> None:
    ctx["session_factory"] = session_factory
    ctx["heartbeat_task"] = asyncio.create_task(_heartbeat(ctx))
    logger.info("worker_started")


async def shutdown(ctx: dict[str, Any]) -> None:
    task: asyncio.Task[None] = ctx["heartbeat_task"]
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    await ctx["redis"].delete(settings.worker_heartbeat_key)
    logger.info("worker_stopped")


async def phase_one_noop(_: dict[str, Any]) -> str:
    """Queue smoke-test job; mission jobs are added in the mission phase."""
    return "ok"


async def dispatch_outbox(ctx: dict[str, Any]) -> int:
    """Reliably transfer committed PostgreSQL job intents to ARQ."""
    factory: async_sessionmaker[AsyncSession] = ctx["session_factory"]
    redis: ArqRedis = ctx["redis"]
    dispatched = 0
    async with factory() as session:
        jobs = (
            await session.execute(
                select(OutboxJob)
                .where(OutboxJob.status == "pending")
                .order_by(OutboxJob.created_at)
                .limit(50)
                .with_for_update(skip_locked=True)
            )
        ).scalars()
        for job in jobs:
            try:
                await redis.enqueue_job(
                    job.job_type,
                    str(job.mission_id),
                    _job_id=f"outbox:{job.id}",
                )
                job.status = "dispatched"
                job.dispatched_at = datetime.now(UTC)
                dispatched += 1
            except Exception as exc:
                job.attempts += 1
                job.last_error = str(exc)[:1000]
        await session.commit()
    return dispatched


async def prepare_mission(ctx: dict[str, Any], mission_id: str) -> str:
    """Stop at the pre-agent planning boundary until Phase 5 is available."""
    factory: async_sessionmaker[AsyncSession] = ctx["session_factory"]
    async with factory() as session:
        mission = (
            await session.execute(
                select(Mission).where(Mission.id == uuid.UUID(mission_id)).with_for_update()
            )
        ).scalar_one_or_none()
        if mission is None:
            return "missing"
        if mission.status != MissionStatus.QUEUED:
            return str(mission.status.value)
        transition_mission(
            session,
            mission,
            MissionStatus.PLANNING,
            "Worker accepted mission; awaiting Phase-5 context and agent gateway",
            None,
        )
        mission.progress_current = 1
        mission.progress_total = 3
        session.add(
            MissionStep(
                workspace_id=mission.workspace_id,
                mission_id=mission.id,
                sequence=1,
                name="Mission accepted",
                status="completed",
                detail="Validated and handed to the durable worker",
            )
        )
        record_mission_event(
            session,
            mission,
            "mission.planning_started",
            "Mission planning started",
            "The worker accepted the mission",
            None,
        )
        await session.commit()
    return "planning"


class WorkerSettings:
    functions = [phase_one_noop, prepare_mission]
    cron_jobs = [cron(dispatch_outbox, second=set(range(0, 60, 5)), run_at_startup=True)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    health_check_interval = 10
