import asyncio
import contextlib
from typing import Any

import structlog
from arq.connections import RedisSettings

from app.config import settings
from app.logging import configure_logging

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


class WorkerSettings:
    functions = [phase_one_noop]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    health_check_interval = 10

