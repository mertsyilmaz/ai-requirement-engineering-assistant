import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)


class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
