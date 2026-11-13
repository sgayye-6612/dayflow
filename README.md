# DayFlow with free real-time voice calls (Gemini Live)

This is your DayFlow app plus **Call Flo**: a real-time voice call with an AI. It runs on Google's **Gemini Live API**, whose free tier needs no credit card.

- It listens all the time while the call is open.
- You can interrupt it just by talking, and it stops and listens.
- It answers in a natural voice.
- It knows your tasks, calendar, reminders, routine and birthdays, and can add or change them while you talk.

## How it works

```
Your browser  ⇄  your DayFlow server (FastAPI)  ⇄  Google Gemini Live
   mic audio (16 kHz)  ──────────▶          ──────────▶
   Flo's voice (24 kHz) ◀──────────          ◀──────────
```

- Your **Gemini API key stays on your server**. The browser never sees it.
- Audio streams continuously both ways over WebSockets. Gemini decides when you've finished speaking and stops talking the moment you interrupt.

## What's in the folder

| File | What it is |
|---|---|
| `server/main.py` | The small FastAPI server. It serves DayFlow and relays the live call to Gemini. |
| `server/requirements.txt` | The Python packages the server needs. |
| `static/index.html` | The whole DayFlow app, including the call screen. |
| `.env.example` | A template for your settings. You copy it to `.env`. |

---

## Part 1: Run it on your computer (Windows + VS Code)

### Step 1. Open the folder in VS Code
**File › Open Folder…** and pick the `dayflow-voice` folder that holds `server`, `static` and `.env.example`.

### Step 2. Open a terminal and go into `server`
**Terminal › New Terminal**, then:
```
cd server
```

### Step 3. Create and turn on the environment (first time only)
```
python -m venv .venv
.venv\Scripts\Activate.ps1
```
You'll see `(.venv)` at the start of the line.

If you get **"running scripts is disabled"**, run this once, type `Y`, then run the second line again:
```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Step 4. Install the packages
```
pip install -r requirements.txt
```

### Step 5. Get your free Gemini API key
1. Go to **https://aistudio.google.com/apikey** and sign in with your Google account.
2. Click **Create API key**. If asked, pick or create a project.
3. Copy the key. It usually starts with `AIza`.

You don't need to add billing. Without billing you stay on the free tier.

### Step 6. Create your `.env` file
1. In the VS Code sidebar, right-click `.env.example` › **Copy**, then right-click the top folder › **Paste**.
2. Rename the copy to exactly `.env`.
3. Paste your key after `GEMINI_API_KEY=`, with no spaces or quotes:
   ```
   GEMINI_API_KEY=AIza...your key...
   ```
4. Press **Ctrl+S** to save. Never share this file.

### Step 7. Start the server
```
uvicorn main:app --reload
```
Wait for `Uvicorn running on http://127.0.0.1:8000`.

### Step 8. Call Flo
1. Open **http://localhost:8000** in **Chrome** or **Edge**.
2. Click **Call Flo**. It's on the Home page, on the AI Assistant page, and as a phone icon in the chat bubble.
3. Allow the microphone. Flo picks up and says hi.

**During a call**
- Talk over Flo at any time to interrupt her.
- **Mute** (or press `M`) turns your mic off.
- **End** (or `Esc`) hangs up.
- **Captions** shows or hides the words on screen.
- The conversation is saved in your chat afterwards.
- Use **headphones** if Flo starts hearing herself through laptop speakers.

### Next time
```
cd server
.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```
To stop the server, press **Ctrl+C** in the terminal.

---

## Free tier: what to know

- **Limits:** Google sets free-tier limits (requests per minute and per day). If you hit one, the call ends with a message from Gemini. Wait a bit and call again.
- **Long calls:** a single live session lasts roughly 10–15 minutes. Flo tells you before it ends, and you can call again right away.
- **Privacy:** on the free tier, Google may use what you send to improve its products. Avoid saying anything you'd want kept private during calls, or add billing later to move to the paid tier.

---

## Part 2: Put it online (optional)

Browsers only allow the microphone on **https** sites (or `localhost`). To use it on your phone, deploy to a host with https, such as **Render** (free plan available).

1. Push the `dayflow-voice` folder to GitHub. `.env` stays out automatically.
2. On Render: **New › Web Service** › pick the repo.
3. Set **Root directory** to `server`.
4. Set **Build command** to `pip install -r requirements.txt`.
5. Set **Start command** to `uvicorn main:app --host 0.0.0.0 --port $PORT`.
6. Under **Environment**, add `GEMINI_API_KEY` = your key.
7. Also add `DAYFLOW_ACCESS_CODE` = a code only you know. Do this before you share the link, or others could use up your free limits.

---

## Settings (in `.env`)

| Setting | Default | What it does |
|---|---|---|
| `GEMINI_API_KEY` | (required) | Your free key from Google AI Studio. |
| `DAYFLOW_ACCESS_CODE` | empty | When set, the app asks for this code before a call. |
| `GEMINI_LIVE_MODEL` | `gemini-3.8-live` | The voice model. `gemini-3.1-flash-live-preview` is an alternative. |
| `GEMINI_VOICE` | `Aoede` | Flo's voice. Other voices include `Kore`, `Leda`, `Zephyr`, `Puck` and `Charon`. |
| `DAYFLOW_CALLS_PER_10_MIN` | `10` | A safety limit on how many calls can start in 10 minutes. |

After changing `.env`, restart the server: **Ctrl+C**, then `uvicorn main:app --reload`.

## If something goes wrong

| What you see | What to do |
|---|---|
| No **Call Flo** button | Open the app through the server (`http://localhost:8000`), not by double-clicking the HTML file. Check `GEMINI_API_KEY` is saved in `.env`, then restart the server. |
| "Microphone access is blocked" | Click the lock icon in the address bar › allow Microphone › call again. |
| "Gemini refused the call…" or "Gemini ended the call: …" | Usually the key is wrong, or the free limit was reached. Check the key, wait a minute, and try again. If it mentions the model, set `GEMINI_LIVE_MODEL=gemini-3.1-flash-live-preview`. |
| "The server couldn't reach Google" | Check your internet connection. |
