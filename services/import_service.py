from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from config import TZ_NAME


def _today_local() -> date:
    tz = ZoneInfo(TZ_NAME)
    return datetime.now(tz).date()


def get_today_schedule(user_id: int, teacher: str | None = None, group_name: str | None = None) -> List[Dict[str, Any]]:
    today = _today_local()
    return [{
        "teacher": teacher or "Abdulla Abdullaev",
        "group_name": group_name or "101-A",
        "day_of_week": "Dushanba",
        "lesson_date": today.isoformat(),
        "time_range": "09:00-10:30",
        "subject": "Matematika",
        "lesson_type": "Nazariy",
        "room": "B-12",
        "pair_number": 1,
    }]


def get_weekly_schedule(user_id: int, teacher: str | None = None, group_name: str | None = None) -> List[Dict[str, Any]]:
    return [
        {
            "teacher": teacher or "Abdulla Abdullaev",
            "group_name": group_name or "101-A",
            "day_of_week": "Dushanba",
            "lesson_date": "2026-11-02",
            "time_range": "09:00-10:30",
            "subject": "Matematika",
            "lesson_type": "Nazariy",
            "room": "B-12",
            "pair_number": 1,
        },
        {
            "teacher": teacher or "Abdulla Abdullaev",
            "group_name": group_name or "101-A",
            "day_of_week": "Seshanba",
            "lesson_date": "2026-11-03",
            "time_range": "11:00-12:30",
            "subject": "Fizika",
            "lesson_type": "Laboratoriya",
            "room": "C-5",
            "pair_number": 2,
        },
    ]


def get_monthly_schedule_for_view(year: int, month: int, teacher: str | None = None, group_name: str | None = None) -> List[Dict[str, Any]]:
    return [
        {
            "teacher": teacher or "Abdulla Abdullaev",
            "group_name": group_name or "101-A",
            "day_of_week": "Dushanba",
            "lesson_date": f"{year}-{month:02d}-02",
            "time_range": "09:00-10:30",
            "subject": "Matematika",
            "lesson_type": "Nazariy",
            "room": "B-12",
            "pair_number": 1,
        },
        {
            "teacher": teacher or "Abdulla Abdullaev",
            "group_name": group_name or "101-A",
            "day_of_week": "Seshanba",
            "lesson_date": f"{year}-{month:02d}-03",
            "time_range": "11:00-12:30",
            "subject": "Fizika",
            "lesson_type": "Laboratoriya",
            "room": "C-5",
            "pair_number": 2,
        },
    ]


def build_monthly_summary(rows: List[Dict[str, Any]]) -> str:
    return f"Jami {len(rows)} ta dars qayd etildi."


__all__ = [
    "get_today_schedule",
    "get_weekly_schedule",
    "get_monthly_schedule_for_view",
    "build_monthly_summary",
]
