"""DayFlow API server.

Run (from inside the `server` folder):   uvicorn app.main:app --reload
Then open http://localhost:8000          (the app)
      and http://localhost:8000/docs     (all API endpoints, try them in the browser)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import CORS_ORIGINS, DATABASE_URL, DAYFLOW_ACCESS_CODE, GEMINI_API_KEY, GEMINI_LIVE_MODEL, STATIC_DIR
from .database import Base, engine, get_db
from .routers import auth, data, images, voice

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dayflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # creates the tables the first time
    log.info("Database: %s", DATABASE_URL.split("@")[-1])  # never print the password
    log.info("Voice calls: %s", "ready" if GEMINI_API_KEY else "off (add GEMINI_API_KEY to .env)")
    yield


app = FastAPI(
    title="DayFlow API",
    description="Personal productivity app: accounts, tasks, planner events, reminders, notes, "
                "vision boards, chat with Flo, and real-time voice calls.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["System"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))  # proves the database is reachable
    return {
        "status": "ok",
        "database": engine.dialect.name,
        "accounts": True,
        "voice": bool(GEMINI_API_KEY),
        "provider": "gemini",
        "model": GEMINI_LIVE_MODEL,
        "protected": bool(DAYFLOW_ACCESS_CODE),
    }


# Order matters: specific routes (auth, images, data, health) before the generic /api/{collection} ones.
app.include_router(auth.router)
app.include_router(images.router)
app.include_router(voice.router)
app.include_router(data.router)


@app.get("/", include_in_schema=False)
def index():
    # The same index.html also works on its own (saving in the browser). When the server
    # serves it, we switch on "API mode": login + saving to the database.
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("<!--DAYFLOW_SERVER-->", "<script>window.DAYFLOW_API=true</script>", 1)
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})
