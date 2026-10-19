"""SQLite access: the ARCHITECTURE section 2 schema, a tiny migration step, and small typed helpers.

One shared connection guarded by a lock. The server is single-user, so simple beats fast.
Columns named `*_json` hold JSON text; `decode` adds a parsed sibling key without the suffix.
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Row = dict[str, Any]

SCHEMA_V1 = """
CREATE TABLE player (id TEXT PRIMARY KEY, name TEXT NOT NULL, pronouns TEXT, avatar_json TEXT, created_at TEXT);
CREATE TABLE employment (id TEXT PRIMARY KEY, player_id TEXT, company_id TEXT, role TEXT, level TEXT,
  started_at TEXT, status TEXT);
CREATE TABLE persona (id TEXT PRIMARY KEY, company_id TEXT, name TEXT, role TEXT, color TEXT, model TEXT,
  sheet_path TEXT);
CREATE TABLE channel (id TEXT PRIMARY KEY, company_id TEXT, kind TEXT, name TEXT, topic TEXT, members_json TEXT);
CREATE TABLE message (id TEXT PRIMARY KEY, channel_id TEXT, author TEXT, body_md TEXT, thread_root_id TEXT,
  attachments_json TEXT, created_at TEXT);
CREATE INDEX message_channel ON message(channel_id);
CREATE TABLE ticket (id TEXT PRIMARY KEY, company_id TEXT, title TEXT, type TEXT, level TEXT, size_hours REAL,
  status TEXT, stage TEXT, assignee TEXT, kit_path TEXT, started_at TEXT, done_at TEXT);
CREATE TABLE pull_request (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT, repo TEXT, ticket_id TEXT,
  title TEXT, author TEXT, base TEXT, head TEXT, description_md TEXT, status TEXT);
CREATE TABLE review_comment (id TEXT PRIMARY KEY, pr_id INTEGER, author TEXT, path TEXT, line INTEGER, side TEXT,
  body_md TEXT, severity TEXT, parent_id TEXT, created_at TEXT);
CREATE TABLE review_submission (id TEXT PRIMARY KEY, pr_id INTEGER, verdict TEXT, body_md TEXT, score_json TEXT,
  created_at TEXT);
CREATE TABLE quiz_attempt (id TEXT PRIMARY KEY, ticket_id TEXT, answers_json TEXT, score_json TEXT, created_at TEXT);
CREATE TABLE explain_turn (id TEXT PRIMARY KEY, ticket_id TEXT, author TEXT, body_md TEXT, created_at TEXT);
CREATE TABLE stage_result (id TEXT PRIMARY KEY, ticket_id TEXT, stage TEXT, passed INTEGER, detail_json TEXT,
  created_at TEXT);
CREATE TABLE debrief (id TEXT PRIMARY KEY, ticket_id TEXT, stage TEXT, body_md TEXT, created_at TEXT);
CREATE TABLE persona_memory (persona_id TEXT PRIMARY KEY, company_id TEXT, memory_md TEXT, session_id TEXT,
  updated_at TEXT);
CREATE TABLE governor (id INTEGER PRIMARY KEY CHECK (id = 1), five_hour_util REAL, seven_day_util REAL,
  resets_at TEXT, mode TEXT, updated_at TEXT);
INSERT INTO governor (id, five_hour_util, seven_day_util, resets_at, mode, updated_at)
  VALUES (1, 0, 0, NULL, 'normal', NULL);
"""

MIGRATIONS = [SCHEMA_V1]  # index + 1 = the schema version that migration produces
_IDENT = re.compile(r"^[a-z_]+$")


def new_id() -> str:
    return uuid.uuid4().hex[:16]


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def decode(row: Row | None) -> Row | None:
    """Adds a parsed copy of every `*_json` column under the key without the suffix."""
    if row is None:
        return None
    out = dict(row)
    for key, value in row.items():
        if key.endswith("_json"):
            out[key[:-5]] = json.loads(value) if value else None
    return out


class Database:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        with self._lock:
            version = self._conn.execute("PRAGMA user_version").fetchone()[0]
            for target, script in enumerate(MIGRATIONS, start=1):
                if target > version:
                    self._conn.executescript(script)
                    self._conn.execute(f"PRAGMA user_version = {target}")
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- raw helpers --------------------------------------------------------------------------

    def run(self, sql: str, args: tuple[Any, ...] = ()) -> None:
        with self._lock:
            self._conn.execute(sql, args)
            self._conn.commit()

    def one(self, sql: str, args: tuple[Any, ...] = ()) -> Row | None:
        with self._lock:
            row = self._conn.execute(sql, args).fetchone()
        return dict(row) if row else None

    def all(self, sql: str, args: tuple[Any, ...] = ()) -> list[Row]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, args).fetchall()]

    # -- table helpers (names come from our code, never from requests) -----------------------

    def insert(self, table: str, **values: Any) -> Row:
        self._check(table, *values)
        cols = ", ".join(values)
        marks = ", ".join("?" for _ in values)
        with self._lock:
            cur = self._conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(values.values()))
            self._conn.commit()
            row = self._conn.execute(f"SELECT * FROM {table} WHERE rowid = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    def update(self, table: str, key: Any, key_col: str = "id", **values: Any) -> Row | None:
        self._check(table, key_col, *values)
        sets = ", ".join(f"{c} = ?" for c in values)
        with self._lock:
            self._conn.execute(f"UPDATE {table} SET {sets} WHERE {key_col} = ?", (*values.values(), key))
            self._conn.commit()
        return self.get(table, key, key_col)

    def get(self, table: str, key: Any, key_col: str = "id") -> Row | None:
        self._check(table, key_col)
        return self.one(f"SELECT * FROM {table} WHERE {key_col} = ?", (key,))

    def where(self, table: str, order: str = "rowid", **eq: Any) -> list[Row]:
        self._check(table, order, *eq)
        clause = " AND ".join(f"{c} = ?" for c in eq) or "1"
        return self.all(f"SELECT * FROM {table} WHERE {clause} ORDER BY {order}", tuple(eq.values()))

    @staticmethod
    def _check(*names: str) -> None:
        for name in names:
            if not _IDENT.match(name):
                raise ValueError(f"bad identifier {name!r}")
