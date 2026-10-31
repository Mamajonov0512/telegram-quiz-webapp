from __future__ import annotations

import asyncio
import logging

import uvicorn
from aiogram import Bot

from api.index import app
from bot import create_bot, dp
from config import BOT_TOKEN, HOST, PORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main")


async def run_bot() -> None:
    bot = create_bot()
    if not bot:
        logger.warning("BOT_TOKEN ko'rsatilmagan. Polling boshlanmaydi.")
        return
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Bot polling to'xtatildi.")
    except Exception as exc:  # pragma: no cover - runtime guard
        logger.exception("Bot polling xatosi: %s", exc)


async def run_server() -> None:
    config = uvicorn.Config(app=app, host=HOST, port=PORT, log_level="info")
    server = uvicorn.Server(config)
    logger.info("FastAPI server ishga tushirilmoqda: http://%s:%s", HOST, PORT)
    await server.serve()


async def main() -> None:
    if BOT_TOKEN:
        await run_bot()
    else:
        await run_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Ilova tugadi.")
