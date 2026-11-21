"""Bang moi cua agent trong memory.db: `events` (B1) va `decisions` (B6). Chi CREATE TABLE IF NOT EXISTS -
khong sua bang cu (tuong thich nguoc, migration-map §4)."""
from __future__ import annotations

import json
import pathlib
import sqlite3
import threading

from aowbot.application.decide import Decision
from aowbot.domain.events import Event, EventStatus, EventType

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  key TEXT PRIMARY KEY, account INTEGER NOT NULL, type TEXT NOT NULL, subject TEXT, due_at REAL NOT NULL,
  source TEXT, status TEXT NOT NULL, created REAL, updated REAL, note TEXT);
CREATE INDEX IF NOT EXISTS events_due ON events(status, due_at);
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY, at REAL NOT NULL, account INTEGER NOT NULL, event_key TEXT, action TEXT,
  next_eval_at REAL, why TEXT, detail TEXT, dry_run INTEGER, outcome TEXT);
CREATE INDEX IF NOT EXISTS decisions_acc ON decisions(account, at);
"""


def _event(row: tuple[object, ...]) -> Event:
    account, type_, subject, due_at, source = row
    return Event(int(str(account)), EventType(str(type_)), str(subject), float(str(due_at)), str(source))


class SqliteAgentStore:
    """EventStore + DecisionLog. Moi luong 1 ket noi (nhu bot.memory.Memory)."""

    def __init__(self, path: str | pathlib.Path) -> None:
        self._path = str(path)
        self._local = threading.local()
        self._conn().executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        c: sqlite3.Connection | None = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(self._path, timeout=10, isolation_level=None)
            c.execute("PRAGMA busy_timeout=10000")
            self._local.c = c
        return c

    # ---------- EventStore ----------
    def add(self, event: Event, now: float) -> bool:
        cur = self._conn().execute(
            "INSERT OR IGNORE INTO events(key, account, type, subject, due_at, source, status, created, updated) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (event.key, event.account, event.type.value, event.subject, event.due_at, event.source,
             EventStatus.PENDING.value, now, now))
        return cur.rowcount == 1

    def _select(self, where: str, args: tuple[object, ...]) -> list[Event]:
        rows = self._conn().execute(f"SELECT account, type, subject, due_at, source FROM events WHERE {where}",
                                    args).fetchall()
        return [_event(r) for r in rows]

    def due(self, now: float, limit: int) -> list[Event]:
        return self._select("status=? AND due_at<=? ORDER BY due_at LIMIT ?", (EventStatus.PENDING.value, now, limit))

    def pending_for(self, account: int) -> list[Event]:
        return self._select("status=? AND account=?", (EventStatus.PENDING.value, account))

    def claimed_before(self, t: float) -> list[Event]:
        return self._select("status=? AND updated<?", (EventStatus.CLAIMED.value, t))

    def set_status(self, key: str, status: EventStatus, now: float, note: str = "") -> None:
        self._conn().execute("UPDATE events SET status=?, updated=?, note=? WHERE key=?",
                             (status.value, now, note[:500], key))

    def status(self, key: str) -> EventStatus | None:
        r = self._conn().execute("SELECT status FROM events WHERE key=?", (key,)).fetchone()
        return EventStatus(r[0]) if r else None

    # ---------- DecisionLog ----------
    def log_decision(self, d: Decision, dry_run: bool, outcome: str | None = None) -> int:
        cur = self._conn().execute(
            "INSERT INTO decisions(at, account, event_key, action, next_eval_at, why, detail, dry_run, outcome) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (d.at, d.account, d.event_key, d.action.value if d.action else None, d.next_eval_at, d.why,
             json.dumps(d.to_dict(), ensure_ascii=False, default=str), int(dry_run), outcome))
        return int(cur.lastrowid or 0)

    def set_outcome(self, decision_id: int, outcome: str) -> None:
        self._conn().execute("UPDATE decisions SET outcome=? WHERE id=?", (outcome[:500], decision_id))
