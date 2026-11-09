"""SQLite persistence for ideas, runs, timeline events and projects.

One short-lived connection per operation keeps it safe across worker threads.
Graph state itself lives in the LangGraph checkpointer (a separate database).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS ideas (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    idea_id TEXT NOT NULL REFERENCES ideas(id),
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    kind TEXT,
    current_node TEXT,
    revision INTEGER NOT NULL DEFAULT 0,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_runs_updated ON runs(updated_at DESC);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(id),
    ts TEXT NOT NULL,
    node TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('info', 'decision', 'error')),
    message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_run ON events(run_id, id);
CREATE TABLE IF NOT EXISTS projects (
    slug TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    file_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS project_files (
    slug TEXT NOT NULL REFERENCES projects(slug) ON DELETE CASCADE,
    path TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (slug, path)
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- ideas & runs --------------------------------------------------------
    def create_run(self, idea: dict, provider: str, model: str) -> str:
        idea_id, run_id, ts = uuid.uuid4().hex[:12], uuid.uuid4().hex[:12], now()
        with self._conn() as c:
            c.execute("INSERT INTO ideas VALUES (?,?,?,?)", (idea_id, idea["title"], json.dumps(idea), ts))
            c.execute(
                "INSERT INTO runs (id, idea_id, title, status, provider, model, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (run_id, idea_id, idea["title"], "queued", provider, model, ts, ts),
            )
        return run_id

    def update_run(self, run_id: str, **fields) -> None:
        if not fields:
            return
        fields["updated_at"] = now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        with self._conn() as c:
            c.execute(f"UPDATE runs SET {cols} WHERE id = ?", (*fields.values(), run_id))

    def get_run(self, run_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            return dict(row) if row else None

    def list_runs(self, limit: int = 200) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM runs ORDER BY updated_at DESC LIMIT ?", (limit,))]

    # -- events --------------------------------------------------------------
    def add_event(self, run_id: str, node: str, message: str, level: str = "info") -> None:
        with self._conn() as c:
            c.execute("INSERT INTO events (run_id, ts, node, level, message) VALUES (?,?,?,?,?)",
                      (run_id, now(), node, level, message))

    def events(self, run_id: str) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM events WHERE run_id = ? ORDER BY id", (run_id,))]

    # -- projects ------------------------------------------------------------
    def add_project(self, slug: str, run_id: str, title: str, kind: str, path: str, file_count: int) -> None:
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO projects VALUES (?,?,?,?,?,?,?)",
                      (slug, run_id, title, kind, path, file_count, now()))

    def list_projects(self) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM projects ORDER BY created_at DESC")]

    def get_project(self, slug: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM projects WHERE slug = ?", (slug,)).fetchone()
            return dict(row) if row else None

    # -- project files (kept in the database so serverless hosts can serve them) --
    def add_files(self, slug: str, files: dict[str, str]) -> None:
        with self._conn() as c:
            c.executemany("INSERT OR REPLACE INTO project_files VALUES (?,?,?)",
                          [(slug, p, body) for p, body in files.items()])

    def list_files(self, slug: str) -> list[str]:
        with self._conn() as c:
            return [r[0] for r in c.execute("SELECT path FROM project_files WHERE slug = ? ORDER BY path", (slug,))]

    def read_file(self, slug: str, path: str) -> str | None:
        with self._conn() as c:
            row = c.execute("SELECT content FROM project_files WHERE slug = ? AND path = ?", (slug, path)).fetchone()
            return row[0] if row else None
