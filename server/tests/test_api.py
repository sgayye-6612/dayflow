"""API tests. Run from the `server` folder:   python -m pytest -v
They use a temporary SQLite database, so your real data is never touched."""
import os
import tempfile

os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db"))
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-1234"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def signup(client, email, name="Sahithi"):
    r = client.post("/api/auth/register", json={"name": name, "email": email, "password": "secret123"})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_register_login_and_me(client):
    signup(client, "a@example.com")
    assert client.post("/api/auth/register", json={"name": "x", "email": "a@example.com", "password": "secret123"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-pass"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": "A@example.com", "password": "secret123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": "Bearer " + token})
    assert me.json()["email"] == "a@example.com"


def test_needs_login(client):
    assert client.get("/api/tasks").status_code == 401
    assert client.get("/api/data", headers={"Authorization": "Bearer fake.token.here"}).status_code == 401


def test_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"name": "x", "email": "b@example.com", "password": "123"})
    assert r.status_code == 422


def test_task_crud_and_filters(client):
    h = signup(client, "tasks@example.com")
    r = client.post("/api/tasks", json={"title": "Apply for jobs", "cat": "Work", "prio": "high", "due": "2026-11-20"}, headers=h)
    assert r.status_code == 201
    tid = r.json()["id"]
    client.post("/api/tasks", json={"title": "Walk with Scooby", "cat": "Personal"}, headers=h)

    assert len(client.get("/api/tasks", headers=h).json()) == 2
    work = client.get("/api/tasks?category=Work", headers=h).json()
    assert [t["title"] for t in work] == ["Apply for jobs"]

    client.patch(f"/api/tasks/{tid}", json={"done": True}, headers=h)
    assert client.get(f"/api/tasks/{tid}", headers=h).json()["done"] is True
    assert len(client.get("/api/tasks?done=false", headers=h).json()) == 1

    assert client.delete(f"/api/tasks/{tid}", headers=h).status_code == 204
    assert client.get(f"/api/tasks/{tid}", headers=h).status_code == 404


def test_sync_insert_update_delete(client):
    h = signup(client, "sync@example.com")
    items = [{"id": "a1", "title": "One"}, {"id": "b2", "title": "Two"}, {"id": "c3", "title": "Three"}]
    assert client.put("/api/data/tasks", json=items, headers=h).json() == {"saved": 3}
    # change one, remove one, reorder
    items = [{"id": "c3", "title": "Three!"}, {"id": "a1", "title": "One"}]
    client.put("/api/data/tasks", json=items, headers=h)
    data = client.get("/api/data", headers=h).json()
    assert [t["title"] for t in data["tasks"]] == ["Three!", "One"]
    assert client.put("/api/data/tasks", json=[{"title": "no id"}], headers=h).status_code == 422


def test_users_cannot_see_each_other(client):
    h1 = signup(client, "u1@example.com")
    h2 = signup(client, "u2@example.com")
    client.put("/api/data/notes", json=[{"id": "n1", "title": "Private note"}], headers=h1)
    client.put("/api/data/notes", json=[{"id": "n1", "title": "Other note"}], headers=h2)  # same id is fine
    assert client.get("/api/notes", headers=h1).json()[0]["title"] == "Private note"
    assert client.get("/api/notes", headers=h2).json()[0]["title"] == "Other note"
    assert client.get("/api/notes/n1", headers=h2).json()["title"] == "Other note"


def test_settings_and_images(client):
    h = signup(client, "set@example.com", name="Sahi")
    assert client.get("/api/settings", headers=h).json()["name"] == "Sahi"
    client.put("/api/settings", json={"name": "Sahithi", "theme": "dark"}, headers=h)
    assert client.get("/api/data", headers=h).json()["settings"]["theme"] == "dark"

    assert client.put("/api/images/pic1", json={"src": "data:image/png;base64,AAAA"}, headers=h).status_code == 204
    assert client.get("/api/images/pic1", headers=h).json()["src"].startswith("data:image/png")
    assert client.put("/api/images/pic2", json={"src": "http://evil"}, headers=h).status_code == 422
    client.delete("/api/images/pic1", headers=h)
    assert client.get("/api/images/pic1", headers=h).status_code == 404


def test_wipe_and_delete_account(client):
    h = signup(client, "bye@example.com")
    client.put("/api/data/events", json=[{"id": "e1", "title": "Interview", "date": "2026-11-20"}], headers=h)
    assert client.get("/api/events?date=2026-11-20", headers=h).json()[0]["title"] == "Interview"
    assert client.delete("/api/data", headers=h).status_code == 204
    assert client.get("/api/events", headers=h).json() == []
    assert client.delete("/api/auth/me", headers=h).status_code == 204
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_app_page_switches_on_api_mode(client):
    r = client.get("/")
    assert r.status_code == 200 and "window.DAYFLOW_API=true" in r.text
