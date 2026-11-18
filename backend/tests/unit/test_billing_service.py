from datetime import datetime, timezone

import pytest

from src.services.billing_service import (
    BillingLimitExceeded,
    BillingService,
    grants_paid_access,
    reduced_media_limits,
)


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeSession:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, *_args, **_kwargs):
        return _FakeResult(self.rows.pop(0))


def _billing_row(
    plan: str,
    status: str = "active",
    provider: str | None = None,
    cancel_at: datetime | None = None,
    legacy_hd: bool = False,
):
    return type(
        "BillingRow",
        (),
        {
            "plan": plan,
            "subscription_status": status,
            "subscription_provider": provider,
            "billing_period_start": datetime.now(timezone.utc),
            "billing_period_end": datetime.now(timezone.utc),
            "trial_ends_at": None,
            "subscription_cancel_at": cancel_at,
            "legacy_hd": legacy_hd,
        },
    )()


def _usage_row(total: int, minutes: int = 0):
    return type("UsageRow", (), {"total": total, "minutes": minutes})()


@pytest.mark.asyncio
async def test_billing_summary_requires_paid_subscription():
    service = BillingService(  # type: ignore[arg-type]
        _FakeSession([_billing_row("free", "inactive"), _usage_row(2)])
    )
    service.config.self_host = False
    service.config.monetization_enabled = True
    service.config.early_bird_enabled = False

    summary = await service.get_usage_summary("user-1")

    assert summary["can_create_task"] is False
    assert summary["upgrade_required"] is True
    assert summary["usage_limit"] == 0
    assert summary["remaining"] == 0
    assert summary["reason"] == "Choose a paid plan to process videos."


@pytest.mark.asyncio
async def test_assert_can_create_task_raises_when_minutes_used_up():
    service = BillingService(  # type: ignore[arg-type]
        _FakeSession([_billing_row("pro"), _usage_row(4, 600)])
    )
    service.config.self_host = False
    service.config.monetization_enabled = True
    service.config.pro_plan_minute_limit = 600

    with pytest.raises(BillingLimitExceeded):
        await service.assert_can_create_task("user-1")


@pytest.mark.asyncio
@pytest.mark.parametrize("plan,limit", [("pro", 600), ("scale", 1500)])
async def test_paid_plans_meter_source_minutes(plan, limit):
    service = BillingService(  # type: ignore[arg-type]
        _FakeSession([_billing_row(plan), _usage_row(3, limit - 1)])
    )
    service.config.self_host = False
    service.config.monetization_enabled = True
    service.config.pro_plan_minute_limit = 600
    service.config.scale_plan_minute_limit = 1500

    summary = await service.get_usage_summary("user-1")

    assert summary["plan"] == plan
    assert summary["usage_count"] == 3
    assert summary["usage_limit"] is None
    assert summary["usage_minutes"] == limit - 1
    assert summary["minute_limit"] == limit
    assert summary["remaining_minutes"] == 1
    assert summary["can_create_task"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "plan,legacy_hd,short_side,can_schedule",
    [
        ("pro", False, 720, False),
        ("pro", True, 1080, False),
        ("scale", False, 1080, True),
        ("scale", True, 1080, True),
    ],
)
async def test_plan_entitlements(plan, legacy_hd, short_side, can_schedule):
    service = BillingService(  # type: ignore[arg-type]
        _FakeSession([_billing_row(plan, legacy_hd=legacy_hd), _usage_row(0, 0)])
    )
    service.config.self_host = False
    service.config.monetization_enabled = True

    summary = await service.get_usage_summary("user-1")

    assert summary["output_short_side"] == short_side
    assert summary["legacy_hd"] is (plan == "pro" and legacy_hd)
    assert summary["can_schedule_posts"] is can_schedule


@pytest.mark.asyncio
async def test_lapsed_legacy_subscriber_loses_full_hd():
    service = BillingService(  # type: ignore[arg-type]
        _FakeSession([_billing_row("pro", "canceled", legacy_hd=True), _usage_row(0, 0)])
    )
    service.config.self_host = False
    service.config.monetization_enabled = True

    summary = await service.get_usage_summary("user-1")

    assert summary["output_short_side"] == 720
    assert summary["legacy_hd"] is False


@pytest.mark.parametrize(
    "now,expected_start,expected_end",
    [
        # Monthly anniversaries of a Jan 31 annual start clamp to short months.
        (datetime(2026, 2, 10, tzinfo=timezone.utc), datetime(2026, 1, 31, tzinfo=timezone.utc), datetime(2026, 2, 28, tzinfo=timezone.utc)),
        (datetime(2026, 3, 30, tzinfo=timezone.utc), datetime(2026, 2, 28, tzinfo=timezone.utc), datetime(2026, 3, 31, tzinfo=timezone.utc)),
        (datetime(2026, 3, 31, tzinfo=timezone.utc), datetime(2026, 3, 31, tzinfo=timezone.utc), datetime(2026, 4, 30, tzinfo=timezone.utc)),
        (datetime(2027, 1, 20, tzinfo=timezone.utc), datetime(2026, 12, 31, tzinfo=timezone.utc), datetime(2027, 1, 31, tzinfo=timezone.utc)),
    ],
)
def test_annual_period_resets_allowance_monthly(now, expected_start, expected_end):
    period_start = datetime(2026, 1, 31, tzinfo=timezone.utc)
    period_end = datetime(2027, 1, 31, tzinfo=timezone.utc)

    assert BillingService._usage_window(period_start, period_end, now) == (expected_start, expected_end)


def test_monthly_period_is_used_as_is():
    start = datetime(2026, 10, 12, tzinfo=timezone.utc)
    end = datetime(2026, 11, 12, tzinfo=timezone.utc)

    assert BillingService._usage_window(start, end, datetime(2026, 10, 20, tzinfo=timezone.utc)) == (start, end)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,can_create",
    [
        ("past_due", True),
        ("unpaid", False),
        ("incomplete", False),
    ],
)
async def test_payment_failure_access(status, can_create):
    service = BillingService(  # type: ignore[arg-type]
        _FakeSession([_billing_row("scale", status, provider="stripe"), _usage_row(1, 10)])
    )
    service.config.self_host = False
    service.config.monetization_enabled = True
    service.config.early_bird_enabled = False
    service.config.scale_plan_minute_limit = 1500

    summary = await service.get_usage_summary("user-1")

    assert summary["plan"] == "scale"
    assert summary["subscription_status"] == status
    assert summary["can_create_task"] is can_create
    assert summary["upgrade_required"] is (not can_create)
    if can_create:
        assert summary["minute_limit"] == 1500
        assert summary["remaining_minutes"] == 1490


@pytest.mark.asyncio
async def test_billing_summary_exposes_scheduled_cancellation():
    cancel_at = datetime(2026, 10, 21, tzinfo=timezone.utc)
    service = BillingService(  # type: ignore[arg-type]
        _FakeSession([_billing_row("pro", cancel_at=cancel_at), _usage_row(1)])
    )
    service.config.self_host = False
    service.config.monetization_enabled = True

    summary = await service.get_usage_summary("user-1")

    assert summary["plan"] == "pro"
    assert summary["can_create_task"] is True
    assert summary["cancel_at"] == cancel_at


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "plan,status,expected",
    [
        ("pro", "active", 5400),
        ("scale", "trialing", 10800),
        ("scale", "inactive", 5400),
        ("scale", "past_due", 10800),
        ("scale", "unpaid", 5400),
    ],
)
async def test_billing_summary_exposes_enforced_duration_limit(plan, status, expected):
    service = BillingService(_FakeSession([_billing_row(plan, status, provider="stripe"), _usage_row(0)]))
    service.config.monetization_enabled = True
    service.config.early_bird_enabled = False
    service.config.max_video_duration = 5400
    service.config.pro_youtube_max_video_duration = 5400
    service.config.scale_youtube_max_video_duration = 10800
    service.config.max_video_upload_bytes = 4_000_000_000
    summary = await service.get_usage_summary("user-1")
    assert summary["max_youtube_duration_seconds"] == expected
    assert summary["max_upload_duration_seconds"] == 5400
    assert summary["max_upload_bytes"] == 4_000_000_000


@pytest.mark.parametrize(
    "summary,expected",
    [
        ({"output_short_side": 720}, ("720", 720)),
        ({"output_short_side": 1080}, (None, None)),
        ({"output_short_side": None}, (None, None)),  # self-hosted
        ({}, (None, None)),
    ],
)
def test_reduced_media_limits(summary, expected):
    assert reduced_media_limits(summary) == expected


def test_reduced_quality_youtube_sources_get_their_own_cache_entry():
    import hashlib

    from src.services.task_service import TaskService
    from src.ai import TRANSCRIPT_ANALYSIS_CACHE_VERSION

    url = "https://youtu.be/abcdefghijk"
    full = TaskService._build_cache_key(url, "youtube", "fast")
    # Full-quality keys are unchanged, so existing cache entries stay valid.
    assert full == hashlib.sha256(
        f"youtube|fast|{TRANSCRIPT_ANALYSIS_CACHE_VERSION}|{url}".encode()
    ).hexdigest()
    assert TaskService._build_cache_key(url, "youtube", "fast", "720") != full
    # Uploads are the same file whatever the plan.
    assert TaskService._build_cache_key("upload://a.mp4", "video_url", "fast", "720") == (
        TaskService._build_cache_key("upload://a.mp4", "video_url", "fast")
    )


def test_grants_paid_access_is_stripe_only_semantics():
    assert grants_paid_access("pro", "active")
    assert grants_paid_access("scale", "trialing")
    assert grants_paid_access("scale", "past_due")
    assert not grants_paid_access("scale", "unpaid")
    assert not grants_paid_access("free", "active")
    assert not grants_paid_access("early_bird", "active")


def _early_bird_service(rows, *, enabled=True, limit=300):
    service = BillingService(_FakeSession(rows))  # type: ignore[arg-type]
    service.config.self_host = False
    service.config.monetization_enabled = True
    service.config.early_bird_enabled = enabled
    service.config.early_bird_minute_limit = limit
    service.config.early_bird_youtube_max_video_duration = 3600
    service.config.max_video_duration = 5400
    service.config.pro_plan_minute_limit = 600
    service.config.scale_plan_minute_limit = 1500
    service.config.pro_youtube_max_video_duration = 5400
    service.config.scale_youtube_max_video_duration = 10800
    return service


@pytest.mark.asyncio
async def test_early_bird_user_can_create_task_and_gets_early_bird_entitlements():
    service = _early_bird_service([_billing_row("free", "inactive"), _usage_row(2, 120)])

    summary = await service.get_usage_summary("user-1")

    assert summary["monetization_enabled"] is True
    assert summary["plan"] == "early_bird"
    assert summary["minute_limit"] == 300
    assert summary["usage_minutes"] == 120
    assert summary["remaining_minutes"] == 180
    assert summary["output_short_side"] == 720
    assert summary["can_schedule_posts"] is True
    assert summary["can_create_task"] is True
    assert summary["upgrade_required"] is False
    assert summary["reason"] is None
    assert summary["max_youtube_duration_seconds"] == 3600
    assert summary["max_upload_duration_seconds"] == 5400
    # The window is the calendar month, not a stale billing period.
    assert summary["period_start"].day == 1
    assert await _can_assert(service)


async def _can_assert(service):
    service.db.rows.extend([_billing_row("free", "inactive"), _usage_row(2, 120)])
    result = await service.assert_can_create_task("user-1", 60 * 100)
    return result["plan"] == "early_bird"


@pytest.mark.asyncio
async def test_early_bird_applies_to_lapsed_paid_users_with_stale_period():
    service = _early_bird_service([_billing_row("pro", "canceled"), _usage_row(1, 299)])

    summary = await service.get_usage_summary("user-1")

    assert summary["plan"] == "early_bird"
    assert summary["remaining_minutes"] == 1
    assert summary["can_create_task"] is True


@pytest.mark.asyncio
async def test_early_bird_exhausted_allowance_requires_upgrade():
    service = _early_bird_service([_billing_row("free", "inactive"), _usage_row(5, 300)])

    summary = await service.get_usage_summary("user-1")

    assert summary["plan"] == "early_bird"
    assert summary["remaining_minutes"] == 0
    assert summary["can_create_task"] is False
    assert summary["upgrade_required"] is True
    assert summary["reason"] == "You've used this month's early-bird minutes."

    service.db.rows.extend([_billing_row("free", "inactive"), _usage_row(5, 300)])
    with pytest.raises(BillingLimitExceeded):
        await service.assert_can_create_task("user-1")


@pytest.mark.asyncio
async def test_early_bird_rejects_a_video_longer_than_the_remaining_minutes():
    service = _early_bird_service([_billing_row("free", "inactive"), _usage_row(1, 290)])

    with pytest.raises(BillingLimitExceeded) as exc:
        await service.assert_can_create_task("user-1", 11 * 60)

    assert exc.value.summary["required_minutes"] == 11
    assert exc.value.summary["upgrade_required"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("plan,limit", [("pro", 600), ("scale", 1500)])
async def test_paid_users_are_unchanged_when_early_bird_is_enabled(plan, limit):
    service = _early_bird_service([_billing_row(plan), _usage_row(3, 100)])

    summary = await service.get_usage_summary("user-1")

    assert summary["plan"] == plan
    assert summary["minute_limit"] == limit
    assert summary["remaining_minutes"] == limit - 100
    assert summary["can_schedule_posts"] is (plan == "scale")
    assert summary["output_short_side"] == (720 if plan == "pro" else 1080)
    assert summary["max_youtube_duration_seconds"] == (5400 if plan == "pro" else 10800)


@pytest.mark.asyncio
async def test_disabling_early_bird_restores_the_paid_plan_requirement():
    service = _early_bird_service([_billing_row("free", "inactive"), _usage_row(0, 0)], enabled=False)

    summary = await service.get_usage_summary("user-1")

    assert summary["plan"] == "free"
    assert summary["can_create_task"] is False
    assert summary["upgrade_required"] is True
    assert summary["can_schedule_posts"] is False
    assert summary["reason"] == "Choose a paid plan to process videos."
    assert summary["max_youtube_duration_seconds"] == 5400


@pytest.mark.asyncio
async def test_unlimited_early_bird_limit_never_blocks():
    service = _early_bird_service([_billing_row("free", "inactive"), _usage_row(9, 9999)], limit=0)

    summary = await service.get_usage_summary("user-1")

    assert summary["minute_limit"] is None
    assert summary["remaining_minutes"] is None
    assert summary["can_create_task"] is True


def test_early_bird_youtube_cap_follows_the_toggle():
    from src.config import Config

    config = Config()
    config.max_video_duration = 5400
    config.early_bird_youtube_max_video_duration = 3600
    config.early_bird_enabled = True
    assert config.max_youtube_video_duration_for_plan("early_bird", "inactive") == 3600
    config.early_bird_enabled = False
    assert config.max_youtube_video_duration_for_plan("early_bird", "inactive") == 5400


class _ScalarSession:
    def __init__(self, used):
        self.used = used

    async def execute(self, *_args, **_kwargs):
        return type("R", (), {"scalar_one": lambda _self: self.used})()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "used,enabled,allowed,limit",
    [(2, True, True, 5), (5, True, False, 5), (0, False, False, 0)],
)
async def test_ai_edit_allowance_covers_early_bird(monkeypatch, used, enabled, allowed, limit):
    from types import SimpleNamespace

    from src.services.ai_edit_allowance_service import AIEditAllowanceService

    async def free_row(_self, _user_id):
        return {
            "plan": "free", "subscription_status": "inactive",
            "billing_period_start": None, "billing_period_end": None,
        }

    monkeypatch.setattr(BillingService, "_load_user_billing_row", free_row)
    config = SimpleNamespace(monetization_enabled=True, early_bird_enabled=enabled)
    usage = await AIEditAllowanceService(_ScalarSession(used), config).summary("user-1")

    assert usage["plan"] == ("early_bird" if enabled else "free")
    assert usage["limit"] == limit
    assert usage["allowed"] is allowed
