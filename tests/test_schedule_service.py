from __future__ import annotations

from services.schedule_service import build_monthly_summary, get_today_schedule, get_weekly_schedule


def test_today_schedule_has_records():
    rows = get_today_schedule(123)
    assert len(rows) >= 1
    assert rows[0]["subject"]


def test_weekly_schedule_has_multiple_days():
    rows = get_weekly_schedule(123)
    assert len(rows) >= 2


def test_monthly_summary_works():
    rows = get_today_schedule(123)
    summary = build_monthly_summary(rows)
    assert "Jami" in summary
