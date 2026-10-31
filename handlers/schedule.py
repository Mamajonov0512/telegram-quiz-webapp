from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from database import list_groups, list_teachers, save_user_selection

router = Router()


@router.callback_query(F.data == "teacher_menu")
async def teacher_menu(callback: CallbackQuery) -> None:
    teachers = list_teachers()
    text = "📚 O‘qituvchilar ro‘yxati\n\n" + "\n".join(f"{i + 1}. {name}" for i, name in enumerate(teachers[:10]))
    await callback.answer()
    await callback.message.edit_text(text)


@router.callback_query(F.data == "group_menu")
async def group_menu(callback: CallbackQuery) -> None:
    groups = list_groups()
    text = "👥 Guruhlar ro‘yxati\n\n" + "\n".join(f"{i + 1}. {name}" for i, name in enumerate(groups[:10]))
    await callback.answer()
    await callback.message.edit_text(text)


@router.message(lambda message: message.text and message.text.startswith("teacher:"))
async def save_teacher_choice(message: Message) -> None:
    teacher = message.text.split(":", 1)[1].strip()
    save_user_selection(message.from_user.id, "teacher", selected_teacher=teacher)
    await message.answer(f"Tanlangan o‘qituvchi: {teacher}")


@router.message(lambda message: message.text and message.text.startswith("group:"))
async def save_group_choice(message: Message) -> None:
    group_name = message.text.split(":", 1)[1].strip()
    save_user_selection(message.from_user.id, "group", selected_group=group_name)
    await message.answer(f"Tanlangan guruh: {group_name}")


__all__ = ["router"]
