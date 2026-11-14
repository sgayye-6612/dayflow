"""All settings in one place. Values come from the .env file or the environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

SERVER_DIR = Path(__file__).resolve().parent.parent  # .../server
ROOT_DIR = SERVER_DIR.parent                          # .../dayflow
STATIC_DIR = ROOT_DIR / "static"

# Look for .env in the project folder or the server folder. Windows sometimes saves it as ".env.txt".
for f in (ROOT_DIR / ".env", SERVER_DIR / ".env", ROOT_DIR / ".env.txt", SERVER_DIR / ".env.txt"):
    if f.is_file():
        load_dotenv(f)


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip().strip('"').strip("'")


# Database: PostgreSQL in production. With no DATABASE_URL we fall back to a local SQLite file,
# so the app still runs on a laptop without installing PostgreSQL.
DATABASE_URL = env("DATABASE_URL") or f"sqlite:///{SERVER_DIR / 'dayflow.db'}"
# Use the psycopg (v3) driver for PostgreSQL. Render gives "postgres://..." URLs, so fix those too.
for prefix in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(prefix):
        DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len(prefix):]

# JWT (login tokens)
SECRET_KEY = env("SECRET_KEY") or "dev-only-secret-change-me-please-32-chars-min"
ACCESS_TOKEN_DAYS = int(env("ACCESS_TOKEN_DAYS", "7"))

# CORS: which other websites may call this API (comma separated). Same-origin needs nothing.
CORS_ORIGINS = [o.strip() for o in env("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

# Voice calls (Gemini Live)
GEMINI_API_KEY = env("GEMINI_API_KEY")
GEMINI_LIVE_MODEL = env("GEMINI_LIVE_MODEL", "gemini-3.8-live")
GEMINI_VOICE = env("GEMINI_VOICE", "Aoede")
GEMINI_LIVE_URL = env(
    "GEMINI_LIVE_URL",
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent",
)
DAYFLOW_ACCESS_CODE = env("DAYFLOW_ACCESS_CODE")
CALLS_PER_10_MIN = int(env("DAYFLOW_CALLS_PER_10_MIN", "10"))
