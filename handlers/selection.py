from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot import build_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "<b>📚 Dars jadvali botiga xush kelibsiz.</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:\n"
        "• O‘qituvchi bo‘yicha\n"
        "• Guruh bo‘yicha\n"
        "• Bugungi darslar\n"
        "• Haftalik jadval\n"
        "• Oylik dars jadvali"
    )
    await message.answer(text, reply_markup=build_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer("Yordam: /start - bosh menyu, /today - bugungi darslar, /weekly - haftalik jadval, /monthly - oylik jadval, /admin - admin paneli.")


@router.callback_query(F.data == "help_menu")
async def help_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text("Yordam: /start bosh menyu, /monthly oylik jadval, /admin admin paneli.")


@router.callback_query(F.data == "search_menu")
async def search_menu(callback: CallbackQuery) -> None:
    await callback.answer("Qidiruv funksiyasi uchun o‘qituvchi yoki guruh tanlang.")


__all__ = ["router"]
