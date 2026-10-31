from __future__ import annotations

from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from config import DATABASE_URL, SUPABASE_KEY, SUPABASE_URL


class DatabaseError(RuntimeError):
    pass


def get_supabase_client() -> Optional[Client]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:  # pragma: no cover
        raise DatabaseError(f"Supabase client creation failed: {exc}") from exc


def _safe_get(response: Any) -> List[Dict[str, Any]]:
    if response is None:
        return []
    data = getattr(response, "data", None)
    return list(data) if isinstance(data, list) else []


def ensure_user(user_id: int, full_name: str | None = None, username: str | None = None) -> Dict[str, Any]:
    payload = {
        "user_id": int(user_id),
        "full_name": full_name or "",
        "username": username or "",
        "selected_type": "teacher",
        "selected_teacher": "",
        "selected_group": "",
        "is_admin": False,
    }
    client = get_supabase_client()
    if client is None:
        return payload
    try:
        response = client.table("users").upsert(payload, on_conflict="user_id").execute()
        rows = _safe_get(response)
        return rows[0] if rows else payload
    except Exception as exc:  # pragma: no cover
        raise DatabaseError(f"User save failed: {exc}") from exc


def get_user(user_id: int) -> Dict[str, Any]:
    client = get_supabase_client()
    if client is None:
        return {
            "user_id": int(user_id),
            "selected_type": "teacher",
            "selected_teacher": "",
            "selected_group": "",
            "is_admin": False,
        }
    try:
        response = client.table("users").select("*").eq("user_id", user_id).limit(1).execute()
        rows = _safe_get(response)
        return rows[0] if rows else {"user_id": int(user_id), "selected_type": "teacher"}
    except Exception as exc:  # pragma: no cover
        raise DatabaseError(f"Fetch user failed: {exc}") from exc


def save_user_selection(user_id: int, selected_type: str, selected_teacher: str = "", selected_group: str = "") -> Dict[str, Any]:
    payload = {
        "user_id": int(user_id),
        "selected_type": selected_type,
        "selected_teacher": selected_teacher,
        "selected_group": selected_group,
    }
    client = get_supabase_client()
    if client is None:
        return payload
    try:
        response = client.table("users").upsert(payload, on_conflict="user_id").execute()
        rows = _safe_get(response)
        return rows[0] if rows else payload
    except Exception as exc:  # pragma: no cover
        raise DatabaseError(f"Selection save failed: {exc}") from exc


def list_teachers() -> List[str]:
    client = get_supabase_client()
    if client is None:
        return ["Abdulla Abdullaev", "Dilshod Karimov", "Nargiza Tursunova"]
    try:
        response = client.table("schedules").select("teacher").neq("teacher", "").execute()
        rows = _safe_get(response)
        return sorted({row.get("teacher") for row in rows if row.get("teacher")})
    except Exception:
        return []


def list_groups() -> List[str]:
    client = get_supabase_client()
    if client is None:
        return ["101-A", "101-B", "202-S", "305-K"]
    try:
        response = client.table("schedules").select("group_name").neq("group_name", "").execute()
        rows = _safe_get(response)
        return sorted({row.get("group_name") for row in rows if row.get("group_name")})
    except Exception:
        return []


def get_monthly_schedule(year: int, month: int, teacher: str | None = None, group_name: str | None = None) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    if client is None:
        return [
            {
                "teacher": teacher or "Abdulla Abdullaev",
                "group_name": group_name or "101-A",
                "day_of_week": "Dushanba",
                "lesson_date": f"{year}-{month:02d}-01",
                "subject": "Matematika",
                "lesson_type": "Nazariy",
                "time_range": "09:00-10:30",
                "room": "B-12",
                "pair_number": 1,
            }
        ]
    try:
        query = client.table("schedules").select("*")
        if teacher:
            query = query.eq("teacher", teacher)
        if group_name:
            query = query.eq("group_name", group_name)
        response = query.execute()
        rows = _safe_get(response)
        return [row for row in rows if row.get("lesson_date") and row.get("lesson_date")[:4] == str(year)]
    except Exception:
        return []


def is_admin_user(user_id: int) -> bool:
    return user_id in ADMIN_IDS if ADMIN_IDS else False


def create_period(year: int, month: int, source_filename: str, uploaded_by: int) -> Dict[str, Any]:
    payload = {
        "year": int(year),
        "month": int(month),
        "status": "draft",
        "source_filename": source_filename,
        "uploaded_by": uploaded_by,
    }
    client = get_supabase_client()
    if client is None:
        return payload
    try:
        response = client.table("schedule_periods").insert(payload).execute()
        rows = _safe_get(response)
        return rows[0] if rows else payload
    except Exception as exc:  # pragma: no cover
        raise DatabaseError(f"Period creation failed: {exc}") from exc


def insert_schedules(rows: List[Dict[str, Any]]) -> int:
    client = get_supabase_client()
    if client is None or not rows:
        return 0
    try:
        response = client.table("schedules").insert(rows).execute()
        return len(_safe_get(response))
    except Exception as exc:  # pragma: no cover
        raise DatabaseError(f"Schedule insert failed: {exc}") from exc


__all__ = [
    "DatabaseError",
    "ensure_user",
    "get_user",
    "save_user_selection",
    "list_teachers",
    "list_groups",
    "get_monthly_schedule",
    "is_admin_user",
    "create_period",
    "insert_schedules",
]
