from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from services.schedule_service import get_today_schedule, get_weekly_schedule

router = Router()


@router.callback_query(F.data == "today_schedule")
async def today_schedule(callback: CallbackQuery) -> None:
    rows = get_today_schedule(callback.from_user.id)
    text = "📅 Bugungi darslar\n\n"
    if not rows:
        text += "Bugungi kun uchun dars jadvali mavjud emas."
    else:
        for row in rows:
            text += (
                f"• {row['lesson_date']} / {row['day_of_week']}\n"
                f"  {row['time_range']} | {row['subject']}\n"
                f"  {row['lesson_type']} | {row['group_name']} | {row['room']}\n"
            )
    await callback.answer()
    await callback.message.edit_text(text)


@router.callback_query(F.data == "weekly_schedule")
async def weekly_schedule(callback: CallbackQuery) -> None:
    rows = get_weekly_schedule(callback.from_user.id)
    text = "🗓 Haftalik jadval\n\n"
    for row in rows:
        text += (
            f"• {row['lesson_date']} | {row['day_of_week']}\n"
            f"  {row['time_range']} | {row['subject']} | {row['group_name']}\n"
        )
    await callback.answer()
    await callback.message.edit_text(text)


__all__ = ["router"]
