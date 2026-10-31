from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from excel_handler import ValidationResult, validate_and_parse_excel


@dataclass
class ImportPreview:
    year: int
    month: int
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    preview: List[Dict[str, Any]] = field(default_factory=list)
    result: ValidationResult | None = None


def preview_monthly_import(file_bytes: bytes, year: int, month: int) -> ImportPreview:
    result = validate_and_parse_excel(file_bytes, year=year, month=month)
    return ImportPreview(
        year=year,
        month=month,
        total_rows=result.total_rows,
        valid_rows=result.valid_count,
        invalid_rows=result.invalid_count,
        duplicate_rows=result.duplicate_count,
        preview=[{
            "teacher": row.teacher,
            "group_name": row.group_name,
            "date": row.lesson_date,
            "subject": row.subject,
        } for row in result.valid_rows[:10]],
        result=result,
    )


__all__ = ["ImportPreview", "preview_monthly_import"]
