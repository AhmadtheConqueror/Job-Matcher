import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _csv_env(name):
    return {
        value.strip().lower()
        for value in os.getenv(name, "").split(",")
        if value.strip()
    }


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'career_assistant.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "instance" / "uploads"))
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_API_MODE = os.getenv("GEMINI_API_MODE", "interactions")
    GEMINI_TIMEOUT_MS = _int_env("GEMINI_TIMEOUT_MS", 60000)
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
    ADMIN_EMAILS = _csv_env("ADMIN_EMAILS")
    ALLOWED_CV_EXTENSIONS = {"pdf", "docx", "txt"}
