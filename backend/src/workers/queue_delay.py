"""Report when a video-queue job waits too long before a worker starts it.

The wait is enqueue time to pickup, which is what grows when renders occupy
every slot. A per-user deferral creates a new job, so its own wait stays
short and does not log on top of the original delay. One error log line per
interval keeps the logs from filling with one entry per late job.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..config import get_config
from .job_queue import DEFAULT_QUEUE_NAME

logger = logging.getLogger(__name__)

QUEUE_DELAY_ALERT_KEY = "queue_delay_alert:weberslinkclip_tasks"


class QueueDelayExceeded(Exception):
    """A job sat in the video queue longer than the configured threshold."""


def wait_seconds(enqueue_time: datetime | None, now: datetime) -> float:
    if not isinstance(enqueue_time, datetime):
        return 0.0
    if enqueue_time.tzinfo is None:
        enqueue_time = enqueue_time.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - enqueue_time).total_seconds()


async def maybe_report_queue_delay(
    redis,
    *,
    enqueue_time: datetime | None,
    queue_name: str = DEFAULT_QUEUE_NAME,
    now: datetime | None = None,
    threshold_seconds: int | None = None,
    interval_seconds: int | None = None,
    rate_limit_key: str = QUEUE_DELAY_ALERT_KEY,
) -> bool:
    """Log at most one ``queue_delay_exceeded`` error per interval.

    Returns True when this call won the rate-limit slot. No account id is
    attached.
    """
    config = get_config()
    threshold = (
        config.queue_delay_alert_seconds
        if threshold_seconds is None
        else threshold_seconds
    )
    interval = (
        config.queue_delay_alert_interval_seconds
        if interval_seconds is None
        else interval_seconds
    )
    waited = wait_seconds(enqueue_time, now or datetime.now(timezone.utc))
    if waited < threshold:
        return False
    try:
        acquired = await redis.set(rate_limit_key, "1", nx=True, ex=int(interval))
    except Exception:
        logger.exception("Queue delay alert rate limit failed")
        return False
    if not acquired:
        return False

    depth = -1
    try:
        depth = int(await redis.zcard(queue_name))
    except Exception:
        logger.exception("Queue depth lookup failed")
    waited_s = max(0, int(waited))
    logger.error(
        "queue_delay_exceeded wait_seconds=%s queue_depth=%s queue=%s threshold_seconds=%s",
        waited_s,
        depth,
        queue_name,
        int(threshold),
    )
    return True


async def on_video_job_start(ctx) -> None:
    """arq hook: measure pickup delay for every job on the video queue."""
    try:
        await maybe_report_queue_delay(
            ctx["redis"],
            enqueue_time=ctx.get("enqueue_time"),
            queue_name=DEFAULT_QUEUE_NAME,
        )
    except Exception:
        logger.exception("Queue delay check failed")
