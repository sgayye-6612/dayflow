"""Which data collections DayFlow has, and how one item (a dict from the browser)
fills the typed columns of its table."""
from enum import Enum

from .models import Board, ChatMessage, Event, HistoryEntry, Note, Reminder, Task


class Collection(str, Enum):
    tasks = "tasks"
    events = "events"
    reminders = "reminders"
    notes = "notes"
    boards = "boards"
    chat = "chat"
    history = "history"


def _s(v, n: int) -> str:
    """Safe short string for a column."""
    return str(v or "")[:n]


MODELS = {
    Collection.tasks: Task,
    Collection.events: Event,
    Collection.reminders: Reminder,
    Collection.notes: Note,
    Collection.boards: Board,
    Collection.chat: ChatMessage,
    Collection.history: HistoryEntry,
}

# item dict -> values for the typed columns
COLUMNS = {
    Collection.tasks: lambda d: dict(title=_s(d.get("title"), 300), category=_s(d.get("cat") or "Personal", 50),
                                     priority=_s(d.get("prio") or "medium", 10), due_date=_s(d.get("due"), 10),
                                     done=bool(d.get("done"))),
    Collection.events: lambda d: dict(title=_s(d.get("title"), 300), date=_s(d.get("date"), 10),
                                      start_time=_s(d.get("start"), 5), end_time=_s(d.get("end"), 5),
                                      category=_s(d.get("cat") or "Personal", 50)),
    Collection.reminders: lambda d: dict(title=_s(d.get("title"), 300), date=_s(d.get("date"), 10),
                                         time=_s(d.get("time"), 5), status=_s(d.get("status") or "upcoming", 20)),
    Collection.notes: lambda d: dict(title=_s(d.get("title"), 300), category=_s(d.get("cat") or "Personal", 50),
                                     pinned=bool(d.get("pinned"))),
    Collection.boards: lambda d: dict(name=_s(d.get("name"), 100)),
    Collection.chat: lambda d: dict(role=_s(d.get("r") or d.get("role") or "user", 10)),
    Collection.history: lambda d: dict(action=_s(d.get("action"), 30)),
}
