from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from typing import Any, Dict, List

from openpyxl import load_workbook

WEEKDAY_ALIASES = {
    "dushanba": 0,
    "seshanba": 1,
    "chorshanba": 2,
    "payshanba": 3,
    "juma": 4,
    "shanba": 5,
    "yakshanba": 6,
}

HEADER_ALIASES = {
    "date": {"sana", "kun", "date", "day", "sanasi"},
    "day_of_week": {"haftakuni", "hafta", "dayofweek", "weekday"},
    "teacher": {"oqituvchi", "oqituvchiismi", "o'qituvchi", "teacher", "ustoz", "mudarris"},
    "group_name": {"guruh", "group", "groupname", "klass"},
    "pair_number": {"juftlik", "juftlikraqami", "pair", "pairnumber"},
    "time_range": {"darsvaqti", "time", "timerange", "vaqt"},
    "subject": {"fan", "fannomi", "subject"},
    "lesson_type": {"dars turi", "lessontype", "type", "lesson"},
    "room": {"xona", "room"},
}


@dataclass
class ParsedRow:
    row_number: int
    teacher: str = ""
    group_name: str = ""
    day_of_week: str = ""
    lesson_date: str = ""
    pair_number: int | None = None
    time_range: str = ""
    subject: str = ""
    lesson_type: str = ""
    room: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    valid_rows: List[ParsedRow]
    invalid_rows: List[Dict[str, Any]]
    duplicate_rows: List[Dict[str, Any]]
    total_rows: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    warnings: List[str] = field(default_factory=list)


def normalize_header(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def normalize_weekday(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if text.isdigit() and 1 <= int(text) <= 7:
        return list(WEEKDAY_ALIASES.keys())[int(text) - 1]
    for weekday, _ in WEEKDAY_ALIASES.items():
        if weekday in text or text in weekday:
            return weekday
    for weekday in list(WEEKDAY_ALIASES.keys()):
        if weekday.startswith(text):
            return weekday
    return text


def parse_date_value(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def map_headers(row: List[Any]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for idx, header in enumerate(row):
        key = normalize_header(header)
        for canonical, aliases in HEADER_ALIASES.items():
            if key in aliases or key == canonical:
                mapping[canonical] = idx
                break
    return mapping


def validate_and_parse_excel(file_bytes: bytes, year: int, month: int) -> ValidationResult:
    workbook = load_workbook(filename=BytesIO(file_bytes), data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return ValidationResult([], [], [], total_rows=0, valid_count=0, invalid_count=0, duplicate_count=0)

    headers = map_headers(rows[0])
    if not headers:
        return ValidationResult([], [{"row": 1, "error": "Ustun nomlari aniqlanmadi."}], [], total_rows=0, valid_count=0, invalid_count=0, duplicate_count=0)

    valid_rows: List[ParsedRow] = []
    invalid_rows: List[Dict[str, Any]] = []
    duplicate_rows: List[Dict[str, Any]] = []
    seen_keys = set()

    for idx in range(1, len(rows)):
        row = rows[idx]
        if not any(str(value or "").strip() for value in row):
            continue

        raw = {key: row[col] if col < len(row) else "" for key, col in headers.items()}
        teacher = str(raw.get("teacher") or "").strip()
        group_name = str(raw.get("group_name") or "").strip()
        day_of_week = normalize_weekday(raw.get("day_of_week") or "")
        time_range = str(raw.get("time_range") or "").strip()
        subject = str(raw.get("subject") or "").strip()
        lesson_type = str(raw.get("lesson_type") or "").strip()
        room = str(raw.get("room") or "").strip()
        pair_number = raw.get("pair_number")
        try:
            pair_number = int(pair_number) if pair_number not in (None, "") else None
        except (TypeError, ValueError):
            pair_number = None

        lesson_date = parse_date_value(raw.get("date"))
        if lesson_date is None:
            # If there is no date column, allow month-level weekly schedule import.
            if "date" not in headers:
                lesson_date = date(year, month, 1)
            else:
                lesson_date = None

        errors: List[str] = []
        if not teacher:
            errors.append("O‘qituvchi bo‘sh")
        if not group_name:
            errors.append("Guruh bo‘sh")
        if not subject:
            errors.append("Fan nomi bo‘sh")
        if not lesson_type:
            errors.append("Dars turi bo‘sh")
        if not room:
            errors.append("Xona bo‘sh")
        if not time_range:
            errors.append("Dars vaqti bo‘sh")
        if lesson_date is None:
            errors.append("Sana topilmadi")
        elif lesson_date.year != year or lesson_date.month != month:
            errors.append("Sana tanlangan oy ichida emas")
        if day_of_week and lesson_date:
            expected = list(WEEKDAY_ALIASES.keys())[lesson_date.weekday()]
            if day_of_week != expected:
                errors.append("Hafta kuni va sana mos kelmadi")

        if errors:
            invalid_rows.append({"row": idx + 1, "errors": errors, "raw": raw})
            continue

        key = (teacher, group_name, lesson_date.isoformat(), pair_number, subject)
        if key in seen_keys:
            duplicate_rows.append({
                "row": idx + 1,
                "teacher": teacher,
                "group_name": group_name,
                "date": lesson_date.isoformat(),
                "pair_number": pair_number,
            })
            continue

        seen_keys.add(key)
        valid_rows.append(
            ParsedRow(
                row_number=idx + 1,
                teacher=teacher,
                group_name=group_name,
                day_of_week=day_of_week,
                lesson_date=lesson_date.isoformat(),
                pair_number=pair_number,
                time_range=time_range,
                subject=subject,
                lesson_type=lesson_type,
                room=room,
                raw=raw,
            )
        )

    return ValidationResult(
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        duplicate_rows=duplicate_rows,
        total_rows=len(rows) - 1,
        valid_count=len(valid_rows),
        invalid_count=len(invalid_rows),
        duplicate_count=len(duplicate_rows),
        warnings=["Tekshiruv yakunlandi."],
    )


__all__ = ["validate_and_parse_excel", "ValidationResult", "ParsedRow", "normalize_weekday", "parse_date_value"]
