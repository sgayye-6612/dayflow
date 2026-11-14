"""Tasks, events, reminders, notes, vision boards, chat and history.

Two ways to use these endpoints:

1. REST, one item at a time (great for other clients and for /docs):
     GET    /api/tasks?done=false&category=Work
     POST   /api/tasks
     PATCH  /api/tasks/{id}
     DELETE /api/tasks/{id}

2. Sync, a whole list at once (what the DayFlow web app uses):
     GET /api/data            -> everything for the logged-in user, in one request
     PUT /api/data/tasks      -> "this is my full task list now": the server inserts new
                                 items, updates changed ones and deletes removed ones,
                                 all in ONE database transaction.

Every query filters by user_id taken from the JWT, never from the request body,
so one user can never read or change another user's data.
"""
import time
import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..collections_def import COLUMNS, MODELS, Collection
from ..database import get_db
from ..deps import get_current_user
from ..models import Settings, User

router = APIRouter(prefix="/api", tags=["Data"])

MAX_ITEMS = 5000


def _clean(item: Any) -> dict:
    if not isinstance(item, dict):
        raise HTTPException(422, "Each item must be an object.")
    iid = item.get("id")
    if not isinstance(iid, str) or not (0 < len(iid) <= 64):
        raise HTTPException(422, "Each item needs an 'id' (text, up to 64 characters).")
    return item


def _apply(row, col: Collection, item: dict, position: int):
    row.data = item
    row.position = position
    for k, v in COLUMNS[col](item).items():
        setattr(row, k, v)


def _list(db: Session, user: User, col: Collection) -> list[dict]:
    model = MODELS[col]
    rows = db.scalars(select(model).where(model.user_id == user.id).order_by(model.position))
    return [r.data for r in rows]


def _settings(db: Session, user: User) -> Settings:
    s = db.get(Settings, user.id)
    if not s:
        s = Settings(user_id=user.id, data={})
        db.add(s)
    return s


# ---------- whole-account endpoints ----------

@router.get("/data", summary="Everything for the logged-in user")
def get_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    out: dict[str, Any] = {"settings": _settings(db, user).data or {}}
    for col in Collection:
        out[col.value] = _list(db, user, col)
    db.commit()
    return out


@router.get("/settings")
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = _settings(db, user).data or {}
    db.commit()
    return data


@router.put("/settings")
@router.put("/data/settings", include_in_schema=False)
def put_settings(body: dict = Body(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _settings(db, user)
    s.data = body
    db.commit()
    return body


@router.put("/data/{col}", summary="Replace a whole list (sync)")
def sync_list(col: Collection, items: list[Any] = Body(...),
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if len(items) > MAX_ITEMS:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"At most {MAX_ITEMS} items.")
    model = MODELS[col]
    existing = {r.id: r for r in db.scalars(select(model).where(model.user_id == user.id))}
    seen = set()
    for pos, raw in enumerate(items):
        item = _clean(raw)
        if item["id"] in seen:  # ignore accidental duplicates
            continue
        seen.add(item["id"])
        row = existing.get(item["id"])
        if row is None:
            row = model(user_id=user.id, id=item["id"])
            db.add(row)
        if row.data != item or row.position != pos:
            _apply(row, col, item, pos)
    for iid, row in existing.items():
        if iid not in seen:
            db.delete(row)
    db.commit()  # one transaction: all of it is saved, or none of it
    return {"saved": len(seen)}


@router.delete("/data", status_code=status.HTTP_204_NO_CONTENT, summary="Delete all my data (keeps the account)")
def wipe(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for model in MODELS.values():
        db.query(model).filter(model.user_id == user.id).delete()
    _settings(db, user).data = {}
    db.commit()


# ---------- REST, one item at a time ----------

@router.get("/{col}", summary="List items")
def list_items(col: Collection,
               done: bool | None = Query(None, description="Tasks only: true or false"),
               category: str | None = Query(None, description="Tasks, events, notes: e.g. Work"),
               date: str | None = Query(None, description="Events/reminders: YYYY-MM-DD; tasks: due date"),
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    model = MODELS[col]
    q = select(model).where(model.user_id == user.id)
    if done is not None and hasattr(model, "done"):
        q = q.where(model.done == done)
    if category and hasattr(model, "category"):
        q = q.where(model.category == category)
    if date:
        if hasattr(model, "due_date"):
            q = q.where(model.due_date == date)
        elif hasattr(model, "date"):
            q = q.where(model.date == date)
    return [r.data for r in db.scalars(q.order_by(model.position))]


@router.post("/{col}", status_code=status.HTTP_201_CREATED, summary="Add one item")
def create_item(col: Collection, item: dict = Body(...),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    model = MODELS[col]
    item = dict(item)
    item.setdefault("id", uuid.uuid4().hex[:12])
    item.setdefault("created", int(time.time() * 1000))
    _clean(item)
    if db.get(model, (user.id, item["id"])):
        raise HTTPException(status.HTTP_409_CONFLICT, "An item with this id already exists.")
    last = db.scalar(select(func.max(model.position)).where(model.user_id == user.id))
    row = model(user_id=user.id, id=item["id"])
    _apply(row, col, item, (last or 0) + 1)
    db.add(row)
    db.commit()
    return item


def _get_or_404(db: Session, model, user: User, item_id: str):
    row = db.get(model, (user.id, item_id))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    return row


@router.get("/{col}/{item_id}", summary="Get one item")
def get_item(col: Collection, item_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_or_404(db, MODELS[col], user, item_id).data


@router.patch("/{col}/{item_id}", summary="Change some fields of one item")
def update_item(col: Collection, item_id: str, changes: dict = Body(...),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = _get_or_404(db, MODELS[col], user, item_id)
    changes.pop("id", None)  # the id can't be changed
    _apply(row, col, {**row.data, **changes}, row.position)
    db.commit()
    return row.data


@router.delete("/{col}/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete one item")
def delete_item(col: Collection, item_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_get_or_404(db, MODELS[col], user, item_id))
    db.commit()
