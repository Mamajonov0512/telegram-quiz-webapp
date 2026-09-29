import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Admin Telegram IDs (comma-separated, e.g. "12345678,87654321")
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
WEB_APP_URL = os.getenv("WEB_APP_URL", "")

# Admin secret key for web dashboard login
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "admin12345")

# Test defaults
DEFAULT_TEST_QUESTIONS_COUNT = int(os.getenv("TEST_QUESTIONS_COUNT", "50"))
DEFAULT_TEST_DURATION_MINUTES = int(os.getenv("TEST_DURATION_MINUTES", "50"))

# Database path
DB_PATH = BASE_DIR / "quiz_app.db"
