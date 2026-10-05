import sys
from pathlib import Path

# Add repository root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Export FastAPI app for Vercel Serverless Functions
from api import app
