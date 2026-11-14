"""Real-time voice calls with Flo (Gemini Live).

Browser  <-WebSocket->  this server  <-WebSocket->  Google Gemini Live
The Gemini API key stays on the server; the browser never sees it.
The browser must send its login token (?token=...) so only logged-in users can call.
"""
import asyncio
import hmac
import json
import time
from collections import defaultdict, deque

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import (CALLS_PER_10_MIN, DAYFLOW_ACCESS_CODE as ACCESS_CODE, GEMINI_API_KEY,
                      GEMINI_LIVE_MODEL as MODEL, GEMINI_LIVE_URL as LIVE_URL, GEMINI_VOICE as VOICE)
from ..database import SessionLocal
from ..models import User
from ..security import read_token

router = APIRouter(tags=["Voice"])

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


def _logged_in(token: str) -> bool:
    uid = read_token(token) if token else None
    if not uid:
        return False
    with SessionLocal() as db:
        return db.get(User, uid) is not None


async def _refuse(ws: WebSocket, message: str) -> None:
    await ws.send_text(json.dumps({"error": message}))
    await ws.close(code=1008)


@router.websocket("/api/live")
async def live(ws: WebSocket):
    await ws.accept()
    if not GEMINI_API_KEY:
        return await _refuse(ws, "Voice calls are not set up yet: add GEMINI_API_KEY to the .env file and restart the server.")
    if not _logged_in(ws.query_params.get("token", "")):
        return await _refuse(ws, "Please log in again to call Flo.")
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
