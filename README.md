# DayFlow 🌸

**A personal productivity app with an AI assistant you can talk to.**
Tasks, a daily planner and calendar, reminders, notes (including voice notes), vision boards, and **Flo**, an assistant you can chat with or call in real time.

**Full stack:** HTML/CSS/JavaScript frontend · **FastAPI** (Python) backend · **PostgreSQL** · **JWT** login · **Gemini Live** real-time voice over WebSockets · **Docker** · **pytest**

---

## ✨ Features

- **Accounts:** register and log in with email + password. Passwords are stored as bcrypt hashes, and logins use JWT tokens.
- **Tasks** with categories, priorities, due dates, repeats and subtasks
- **Planner & calendar** (day, week, month) with events
- **Reminders** with snooze and history
- **Notes** with tags, pins and voice recordings
- **Vision boards** with images you can drag around
- **Flo, the AI assistant:** chat, or press **Call Flo** for a real-time voice call. You can interrupt Flo, and she can add tasks, events and reminders while you talk.
- Everything is saved to **your account in the database**, so it's the same on every device.

---

## 🏗️ How it works

```
 Browser (static/index.html)                FastAPI server (server/app)                 PostgreSQL
 ───────────────────────────                ───────────────────────────                 ──────────
 Login screen  ── POST /api/auth/login ──▶  check bcrypt hash, return JWT
 App loads     ── GET  /api/data ───────▶   all of this user's data  ◀──── SELECT ───── users, tasks, events,
 You add a task── PUT  /api/data/tasks ─▶   insert / update / delete ───── one ───────▶ reminders, notes, boards,
                                            in ONE transaction          transaction     chat_messages, history,
 Call Flo      ══ WebSocket /api/live ══▶   relay audio  ⇄  Google Gemini Live          settings, images
```

- Every request sends the token in a header: `Authorization: Bearer <JWT>`.
- The server reads the **user id from the token**, never from the request body, and every query filters by it. So one user can never see another user's data.
- The browser saves a list about half a second after your last change (debounced), so typing doesn't send a request per key.
- The Gemini API key stays on the server. The browser never sees it.

### Database tables

| Table | What's in it | Typed columns (for SQL filters) |
|---|---|---|
| `users` | accounts | email (unique), name, password_hash |
| `tasks` | to-dos | title, category, priority, due_date, done |
| `events` | planner events | title, date, start_time, end_time, category |
| `reminders` | reminders | title, date, time, status |
| `notes` | notes | title, category, pinned |
| `boards` | vision boards | name |
| `chat_messages` | chat with Flo | role |
| `history` | what happened to reminders | action |
| `settings` | one row per user (name, theme, routine …) | — |
| `images` | board pictures, voice-note audio | key |

Each item table uses **(user_id, id)** as the primary key, plus a JSON column (`data`, JSONB in PostgreSQL) for flexible details such as subtasks or a card's position on a board.

### API (try them all at **http://localhost:8000/docs**)

| Method | Path | What it does |
|---|---|---|
| POST | `/api/auth/register` | Create an account, returns a token |
| POST | `/api/auth/login` | Log in, returns a token |
| GET | `/api/auth/me` | Who am I |
| DELETE | `/api/auth/me` | Delete my account and all my data |
| GET | `/api/data` | Everything for the logged-in user |
| PUT | `/api/data/{tasks\|events\|…}` | Save a whole list (used by the app) |
| GET | `/api/tasks?done=false&category=Work` | List with filters |
| POST / PATCH / DELETE | `/api/tasks`, `/api/tasks/{id}` | One item at a time (same for events, reminders, notes, boards, chat, history) |
| GET / PUT | `/api/settings` | User settings |
| PUT / GET / DELETE | `/api/images/{key}` | Pictures and recordings |
| WebSocket | `/api/live?token=…` | Real-time voice call with Flo |
| GET | `/api/health` | Server + database check |

---

## 🚀 Run it on your computer (Windows + VS Code)

You need **Python 3.10+**. PostgreSQL is optional: without it the app uses a local SQLite file.

### 1. Open the folder and a terminal
In VS Code: **File › Open Folder…** › pick `dayflow`. Then **Terminal › New Terminal**.

### 2. Create the Python environment (first time only)
```
cd server
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
If you see **"running scripts is disabled"**, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, type `Y`, and try again.

### 3. Create your `.env` file
Copy `.env.example` (in the main `dayflow` folder) to a new file named exactly `.env`, then:
- **Using PostgreSQL?** Create the database once: `psql -U postgres -c "CREATE DATABASE dayflow;"`, then put your password in `DATABASE_URL`.
- **No PostgreSQL?** Delete the `DATABASE_URL` line. The app will use `server/dayflow.db` (SQLite).
- Set `SECRET_KEY` to any long random text.
- For voice calls, paste your free Gemini key from https://aistudio.google.com/apikey into `GEMINI_API_KEY`.

### 4. Start the server
```
uvicorn app.main:app --reload
```
Open **http://localhost:8000**, click **Create an account**, and you're in.
API docs: **http://localhost:8000/docs**

### Next time
```
cd server
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### Run the tests
```
cd server
python -m pytest -v
```
The tests use a temporary database, so your data is safe. They cover sign-up and login, wrong passwords, filters, saving lists, users not seeing each other's data, settings, images, and deleting an account.

---

## 🐳 Run with Docker (app + PostgreSQL together)

Install Docker Desktop, then from the `dayflow` folder:
```
docker compose up --build
```
Open **http://localhost:8000**. The database is kept in a Docker volume between restarts.

## ☁️ Put it online (Render, free)

1. Push this folder to GitHub (`.env` is ignored automatically).
2. On https://render.com: **New › Blueprint** › pick the repo. `render.yaml` creates the web service **and** a PostgreSQL database.
3. In the web service's **Environment**, add `GEMINI_API_KEY` (and optionally `DAYFLOW_ACCESS_CODE`).
4. Open the link Render gives you.

Browsers only allow the microphone on **https** sites (or `localhost`), and Render gives you https.

---

## 🗂️ Project structure

```
dayflow/
├── static/
│   └── index.html            # the whole frontend (HTML, CSS, JS): screens, login, voice call UI
├── server/
│   ├── app/
│   │   ├── main.py           # creates the FastAPI app, serves index.html, /api/health
│   │   ├── config.py         # settings from .env
│   │   ├── database.py       # SQLAlchemy engine + session per request
│   │   ├── models.py         # database tables
│   │   ├── security.py       # bcrypt password hashing, JWT create/read
│   │   ├── deps.py           # get_current_user (reads the token)
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── collections_def.py# which lists exist + their typed columns
│   │   └── routers/
│   │       ├── auth.py       # register, login, me, delete account
│   │       ├── data.py       # tasks/events/... (REST + sync)
│   │       ├── images.py     # pictures and recordings
│   │       └── voice.py      # WebSocket relay to Gemini Live
│   ├── tests/test_api.py     # pytest
│   └── requirements.txt
├── Dockerfile, docker-compose.yml, render.yaml
└── .env.example
```

> **Without the server:** opening `static/index.html` directly still works. DayFlow then saves to the browser (localStorage) with no login, the way it did before the backend existed.

## Voice call notes (free Gemini tier)
- A single live session lasts about 10–15 minutes; call again to continue.
- Free-tier limits apply. If you hit one, wait a bit.
- On the free tier Google may use what you send to improve its products, so avoid private details during calls.
