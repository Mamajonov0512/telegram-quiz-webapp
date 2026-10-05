import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Admin Telegram IDs (comma-separated, e.g. "12345678,87654321")
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Vercel / Webhook / Web App URLs
VERCEL_URL = os.getenv("VERCEL_URL", "").strip()
default_domain_url = f"https://{VERCEL_URL}" if VERCEL_URL else ""

raw_web_app_url = os.getenv("WEB_APP_URL", default_domain_url).strip()
if raw_web_app_url and not raw_web_app_url.startswith("http://") and not raw_web_app_url.startswith("https://"):
    raw_web_app_url = f"https://{raw_web_app_url}"
WEB_APP_URL = raw_web_app_url

raw_webhook_url = os.getenv("WEBHOOK_URL", WEB_APP_URL or default_domain_url).strip()
if raw_webhook_url and not raw_webhook_url.startswith("http://") and not raw_webhook_url.startswith("https://"):
    raw_webhook_url = f"https://{raw_webhook_url}"
WEBHOOK_URL = raw_webhook_url

# Admin secret key for web dashboard login
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "admin12345").strip()

# Test defaults
DEFAULT_TEST_QUESTIONS_COUNT = int(os.getenv("TEST_QUESTIONS_COUNT", "50"))
DEFAULT_TEST_DURATION_MINUTES = int(os.getenv("TEST_DURATION_MINUTES", "50"))

# Supabase / PostgreSQL Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("SUPABASE_DB_URL", "")).strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", os.getenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))).strip()

# Database path (SQLite fallback for local development)
DB_PATH = BASE_DIR / "quiz_app.db"
