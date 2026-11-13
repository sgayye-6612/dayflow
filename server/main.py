"""DayFlow server (free voice calls with Gemini Live).

- Serves the DayFlow app at http://localhost:8000
- Relays a live voice call between your browser and Google's Gemini Live API.
  Your Gemini API key stays here on the server; the browser never sees it.

Run (from inside the server folder):  uvicorn main:app --reload
"""
import asyncio
import hmac
import json
import os
import time
from collections import defaultdict, deque
from pathlib import Path

import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

BASE = Path(__file__).resolve().parent
# Look for the settings file next to .env.example (or in this folder). Windows sometimes
# saves it as ".env.txt" when file extensions are hidden, so accept that too.
ENV_FILES = [BASE.parent / ".env", BASE / ".env", BASE.parent / ".env.txt", BASE / ".env.txt"]
for f in ENV_FILES:
    if f.is_file():
        load_dotenv(f)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.8-live").strip()
VOICE = os.getenv("GEMINI_VOICE", "Aoede").strip()
ACCESS_CODE = os.getenv("DAYFLOW_ACCESS_CODE", "").strip()
CALLS_PER_10_MIN = int(os.getenv("DAYFLOW_CALLS_PER_10_MIN", "10"))
STATIC = BASE.parent / "static"
LIVE_URL = os.getenv("GEMINI_LIVE_URL", "wss://generativelanguage.googleapis.com/ws/"
                     "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent")

app = FastAPI(title="DayFlow", docs_url=None, redoc_url=None)

found = [str(f) for f in ENV_FILES if f.is_file()]
if GEMINI_API_KEY:
    print(f"DayFlow: Gemini key: found (from {found[0] if found else 'environment'}). Voice calls are ready. Model: {MODEL}")
else:
    print("DayFlow: Gemini key: NOT found. Voice calls are off.")
    print(f"  Put a line GEMINI_API_KEY=your-key in {BASE.parent / '.env'} and restart the server.")
    if found:
        print(f"  (I found {', '.join(found)}, but it has no GEMINI_API_KEY line.)")
_recent_calls: dict[str, deque] = defaultdict(deque)


def _allowed(ip: str) -> bool:
    """Simple safety limit: at most CALLS_PER_10_MIN calls per 10 minutes per address."""
    now = time.time()
    q = _recent_calls[ip]
    while q and now - q[0] > 600:
        q.popleft()
    if len(q) >= CALLS_PER_10_MIN:
        return False
    q.append(now)
    return True


async def _refuse(ws: WebSocket, message: str) -> None:
    await ws.send_text(json.dumps({"error": message}))
    await ws.close(code=1008)


@app.get("/api/health")
def health():
    return {"voice": bool(GEMINI_API_KEY), "provider": "gemini", "model": MODEL, "protected": bool(ACCESS_CODE)}


@app.websocket("/api/live")
async def live(ws: WebSocket):
    await ws.accept()
    if not GEMINI_API_KEY:
        return await _refuse(ws, "Voice calls are not set up yet: add GEMINI_API_KEY to the .env file and restart the server.")
    if ACCESS_CODE and not hmac.compare_digest(ws.query_params.get("code", "").encode(), ACCESS_CODE.encode()):
        return await _refuse(ws, "Wrong access code.")
    if not _allowed(ws.client.host if ws.client else "unknown"):
        return await _refuse(ws, "Too many calls in a short time. Wait a few minutes and try again.")

    try:
        # 1. The browser's first message is the call setup (Flo's instructions, functions, captions).
        first = json.loads(await ws.receive_text())
        setup = first.get("setup") or {}
        # The server decides the model and voice, so nobody can change them from the browser.
        setup["model"] = f"models/{MODEL}"
        gen = setup.setdefault("generationConfig", {})
        gen["responseModalities"] = ["AUDIO"]
        gen["speechConfig"] = {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}

        # 2. Open the live session with Google and relay messages both ways.
        async with websockets.connect(f"{LIVE_URL}?key={GEMINI_API_KEY}", max_size=None,
                                      ping_interval=20, open_timeout=15) as google:
            await google.send(json.dumps({"setup": setup}))

            async def google_to_browser():
                async for msg in google:
                    await ws.send_text(msg.decode("utf-8") if isinstance(msg, bytes) else msg)

            async def browser_to_google():
                while True:
                    await google.send(await ws.receive_text())

            tasks = [asyncio.create_task(google_to_browser()), asyncio.create_task(browser_to_google())]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
            for t in done:
                t.exception()  # already handled below; this just marks it as seen

            # If Google closed the session with a problem, tell the browser why.
            code, reason = google.close_code, (google.close_reason or "")
            if code and code not in (1000, 1001):
                await ws.send_text(json.dumps({"error": f"Gemini ended the call: {reason or 'code ' + str(code)}"}))
    except WebSocketDisconnect:
        return
    except (OSError, asyncio.TimeoutError):
        try:
            await _refuse(ws, "The server couldn't reach Google. Check its internet connection and try again.")
        except Exception:
            pass
        return
    except websockets.exceptions.WebSocketException as e:
        try:
            await _refuse(ws, f"Gemini refused the call ({e}). Check that GEMINI_API_KEY is correct.")
        except Exception:
            pass
        return
    try:
        await ws.close()
    except Exception:
        pass


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})
