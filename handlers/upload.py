from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_IDS

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def admin_command(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Kechirasiz, bu buyruq faqat administrator uchun mavjud.")
        return
    await message.answer(
        "🛡 Administrator paneli\n\n"
        "- Oylik jadvalni boshqarish\n"
        "- Excel yuklash\n"
        "- Importni tekshirish\n"
        "- Faol oyni ko‘rish"
    )


__all__ = ["router", "is_admin"]
