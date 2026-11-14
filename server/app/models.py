"""Database tables.

Every item table (tasks, events, ...) follows the same pattern:
- user_id + id together are the primary key, so each user's data is kept separate
  (the id is created in the browser, like "lq3k9x2ab").
- A few important fields get their OWN columns (title, due_date, done ...) so we can
  filter and sort with SQL, e.g. "all unfinished Work tasks".
- The full item is also kept in `data` (JSON / JSONB in PostgreSQL) for flexible extras
  such as subtasks, tags or board positions.
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    settings: Mapped["Settings"] = relationship(back_populates="user", cascade="all, delete-orphan")


class ItemMixin:
    """Columns shared by every item table."""
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)  # keeps the order the user sees
    data: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Task(ItemMixin, Base):
    __tablename__ = "tasks"
    title: Mapped[str] = mapped_column(String(300), default="")
    category: Mapped[str] = mapped_column(String(50), default="Personal", index=True)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    due_date: Mapped[str] = mapped_column(String(10), default="", index=True)  # "YYYY-MM-DD" or ""
    done: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Event(ItemMixin, Base):
    __tablename__ = "events"
    title: Mapped[str] = mapped_column(String(300), default="")
    date: Mapped[str] = mapped_column(String(10), default="", index=True)
    start_time: Mapped[str] = mapped_column(String(5), default="")
    end_time: Mapped[str] = mapped_column(String(5), default="")
    category: Mapped[str] = mapped_column(String(50), default="Personal")


class Reminder(ItemMixin, Base):
    __tablename__ = "reminders"
    title: Mapped[str] = mapped_column(String(300), default="")
    date: Mapped[str] = mapped_column(String(10), default="", index=True)
    time: Mapped[str] = mapped_column(String(5), default="")
    status: Mapped[str] = mapped_column(String(20), default="upcoming", index=True)


class Note(ItemMixin, Base):
    __tablename__ = "notes"
    title: Mapped[str] = mapped_column(String(300), default="")
    category: Mapped[str] = mapped_column(String(50), default="Personal")
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)


class Board(ItemMixin, Base):
    """Vision boards. Their cards (text, images, positions) live in `data`."""
    __tablename__ = "boards"
    name: Mapped[str] = mapped_column(String(100), default="")


class ChatMessage(ItemMixin, Base):
    """Messages between the user and Flo (the AI assistant)."""
    __tablename__ = "chat_messages"
    role: Mapped[str] = mapped_column(String(10), default="user")


class HistoryEntry(ItemMixin, Base):
    """What happened to reminders (done, snoozed ...)."""
    __tablename__ = "history"
    action: Mapped[str] = mapped_column(String(30), default="")


class Settings(Base):
    """One row per user: name, theme, categories, daily routine ..."""
    __tablename__ = "settings"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONType, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    user: Mapped[User] = relationship(back_populates="settings")


class Image(Base):
    """Pictures for vision boards and voice-note audio, stored as data URLs."""
    __tablename__ = "images"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    src: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
