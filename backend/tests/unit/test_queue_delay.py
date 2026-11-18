"""Pickup delay is logged once, without an account id."""

from datetime import datetime, timedelta, timezone

import logging

import pytest

from src.workers.queue_delay import maybe_report_queue_delay


class _Redis:
    def __init__(self, depth=12):
        self.depth = depth
        self.keys = set()
        self.sets = []

    async def set(self, key, value, nx=False, ex=None):
        self.sets.append((key, nx, ex))
        if nx and key in self.keys:
            return None
        self.keys.add(key)
        return True

    async def zcard(self, _name):
        return self.depth


@pytest.mark.asyncio
async def test_a_short_wait_does_not_report():
    redis = _Redis()
    reported = await maybe_report_queue_delay(
        redis,
        enqueue_time=datetime.now(timezone.utc) - timedelta(seconds=30),
        threshold_seconds=600,
        rate_limit_key="queue_delay_alert:test-short",
    )
    assert reported is False
    assert redis.sets == []


@pytest.mark.asyncio
async def test_a_long_wait_logs_once_with_depth_and_no_account(caplog):
    redis = _Redis(depth=284)
    now = datetime.now(timezone.utc)
    # Naive timestamps are the shape arq puts on the job context.
    enqueue_time = (now - timedelta(seconds=4850)).replace(tzinfo=None)
    kwargs = dict(
        enqueue_time=enqueue_time,
        now=now,
        threshold_seconds=600,
        interval_seconds=900,
        rate_limit_key="queue_delay_alert:test-long",
    )
    with caplog.at_level(logging.ERROR, logger="src.workers.queue_delay"):
        first = await maybe_report_queue_delay(
            redis, queue_name="weberslinkclip_tasks", **kwargs
        )
        second = await maybe_report_queue_delay(redis, **kwargs)
    assert first is True
    assert second is False
    records = [r for r in caplog.records if "queue_delay_exceeded" in r.getMessage()]
    assert len(records) == 1
    message = records[0].getMessage()
    assert "queue_depth=284" in message
    assert "wait_seconds=4850" in message
    assert "queue=weberslinkclip_tasks" in message
    assert "user" not in message
    assert redis.sets[0][1] is True
    assert redis.sets[0][2] == 900


@pytest.mark.asyncio
async def test_report_consumes_the_rate_limit_slot():
    redis = _Redis()
    reported = await maybe_report_queue_delay(
        redis,
        enqueue_time=datetime.now(timezone.utc) - timedelta(seconds=700),
        threshold_seconds=600,
        rate_limit_key="queue_delay_alert:test-slot",
    )
    assert reported is True
    assert "queue_delay_alert:test-slot" in redis.keys


def test_video_worker_measures_delay_on_start():
    from src.workers.tasks import WorkerSettings

    assert WorkerSettings.cron_jobs == []
    assert WorkerSettings.on_job_start.__name__ == "on_video_job_start"
