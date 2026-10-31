from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from services.schedule_service import get_monthly_schedule_for_view

router = Router()


@router.callback_query(F.data == "monthly_schedule")
async def monthly_schedule(callback: CallbackQuery) -> None:
    rows = get_monthly_schedule_for_view(2026, 11)
    text = "📆 Oylik dars jadvali (2026-11)\n\n"
    for row in rows:
        text += (
            f"• {row['lesson_date']} | {row['day_of_week']}\n"
            f"  {row['time_range']} | {row['subject']} | {row['group_name']} | {row['room']}\n"
        )
    await callback.answer()
    await callback.message.edit_text(text)


__all__ = ["router"]
