import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager

from config import BOT_TOKEN, HOST, PORT
import database as db
from api import app
from bot import get_bot, dp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("main")

async def run_bot():
    bot = get_bot()
    if not bot:
        logger.warning("BOT_TOKEN ko'rsatilmagan. Telegram bot ishga tushirilmadi. Faqat Web App / API ishlaydi.")
        return
    logger.info("Telegram Bot ishga tushirilmoqda (polling)...")
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Bot polling to'xtatildi.")
    except Exception as e:
        logger.error(f"Botda xatolik yuz berdi: {e}")

async def run_server():
    config = uvicorn.Config(app=app, host=HOST, port=PORT, log_level="info")
    server = uvicorn.Server(config)
    logger.info(f"Veb-server ishga tushirilmoqda: http://{HOST}:{PORT}")
    await server.serve()

async def main():
    # 1. Initialize SQLite Database
    db.init_db()

    # 2. Check if questions exist, if not seed sample
    if db.get_questions_count() == 0:
        from seed_data import seed_database, create_sample_files
        seed_database()
        create_sample_files()

    # 3. Concurrently run FastAPI server and Telegram Bot
    bot_task = None
    if BOT_TOKEN:
        bot_task = asyncio.create_task(run_bot())
    else:
        print("\n" + "="*60)
        print("DIQQAT: .env faylida BOT_TOKEN ko'rsatilmagan.")
        print(f"Ilova brauzerda http://localhost:{PORT} manzilida ishlaydi.")
        print("Telegram botdan to'liq foydalanish uchun .env faylida BOT_TOKEN ni kiriting!")
        print("="*60 + "\n")

    server_task = asyncio.create_task(run_server())

    try:
        await asyncio.gather(server_task, *( [bot_task] if bot_task else [] ))
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Ilova to'xtatilmoqda...")
    finally:
        if bot_task:
            bot_task.cancel()
        if server_task:
            server_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDastur to'xtatildi.")
