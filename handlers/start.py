from __future__ import annotations

from aiogram import Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import BOT_TOKEN
from handlers.admin import router as admin_router
from handlers.monthly_schedule import router as monthly_router
from handlers.schedule import router as schedule_router
from handlers.selection import router as selection_router
from handlers.start import router as start_router
from handlers.upload import router as upload_router


def create_bot():
    from aiogram import Bot

    if not BOT_TOKEN:
        return None
    return Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def register_commands(bot):
    commands = [
        BotCommand(command="start", description="Bosh menyu"),
        BotCommand(command="today", description="Bugungi darslar"),
        BotCommand(command="weekly", description="Haftalik jadval"),
        BotCommand(command="monthly", description="Oylik jadval"),
        BotCommand(command="admin", description="Administrator paneli"),
    ]
    if bot:
        bot.set_my_commands(commands)


dp = Dispatcher()
for router in [
    start_router,
    selection_router,
    schedule_router,
    monthly_router,
    admin_router,
    upload_router,
]:
    dp.include_router(router)


def build_menu():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 O‘qituvchi bo‘yicha", callback_data="teacher_menu")],
        [InlineKeyboardButton(text="👥 Guruh bo‘yicha", callback_data="group_menu")],
        [InlineKeyboardButton(text="📅 Bugungi darslar", callback_data="today_schedule")],
        [InlineKeyboardButton(text="🗓 Haftalik jadval", callback_data="weekly_schedule")],
        [InlineKeyboardButton(text="📆 Oylik dars jadvali", callback_data="monthly_schedule")],
        [InlineKeyboardButton(text="🔎 Qidirish", callback_data="search_menu")],
        [InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help_menu")],
    ])
    return keyboard


__all__ = ["create_bot", "dp", "register_commands", "build_menu"]
