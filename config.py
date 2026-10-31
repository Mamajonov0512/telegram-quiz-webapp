import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = [
    int(item.strip())
    for item in os.getenv("ADMIN_IDS", "").split(",")
    if item.strip().isdigit()
]

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").strip().lower() == "true"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
VERCEL_URL = os.getenv("VERCEL_URL", "").strip()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
TZ_NAME = os.getenv("TZ_NAME", "Asia/Tashkent")

DEFAULT_YEAR = int(os.getenv("DEFAULT_YEAR", "2026"))
DEFAULT_MONTH = int(os.getenv("DEFAULT_MONTH", "11"))
