"""PostgreSQL store (Supabase). Same interface as the SQLite Store.

Tables live in the private `twin` schema (created by the Supabase migration
`twin_orchestrator_schema`; `ensure_schema` creates them on other Postgres
servers). Connections set search_path=twin, so LangGraph's checkpoint tables
land there too and stay out of Supabase's public API.
"""

from __future__ import annotations

import uuid

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DDL = """
CREATE SCHEMA IF NOT EXISTS twin;
CREATE TABLE IF NOT EXISTS twin.ideas (id text PRIMARY KEY, title text NOT NULL, payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS twin.runs (id text PRIMARY KEY, idea_id text NOT NULL REFERENCES twin.ideas(id),
    title text NOT NULL, status text NOT NULL, kind text, current_node text, revision integer NOT NULL DEFAULT 0,
    provider text NOT NULL, model text NOT NULL, error text,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS twin.events (id bigserial PRIMARY KEY, run_id text NOT NULL REFERENCES twin.runs(id),
    ts timestamptz NOT NULL DEFAULT now(), node text NOT NULL, level text NOT NULL, message text NOT NULL);
CREATE TABLE IF NOT EXISTS twin.projects (slug text PRIMARY KEY, run_id text NOT NULL REFERENCES twin.runs(id),
    title text NOT NULL, kind text NOT NULL, path text NOT NULL, file_count integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS twin.project_files (slug text NOT NULL REFERENCES twin.projects(slug) ON DELETE CASCADE,
    path text NOT NULL, content text NOT NULL, PRIMARY KEY (slug, path));
"""

RUN_COLS = "id, idea_id, title, status, kind, current_node, revision, provider, model, error, created_at, updated_at"
UPDATABLE = {"status", "kind", "current_node", "revision", "error"}


def make_pool(url: str, max_size: int = 5) -> ConnectionPool:
    # prepare_threshold=None keeps it compatible with Supabase's transaction pooler (port 6543)
    return ConnectionPool(url, min_size=1, max_size=max_size, open=True, kwargs={
        "autocommit": True, "prepare_threshold": None, "row_factory": dict_row, "client_encoding": "utf8",
        "options": "-c search_path=twin",
    })


def _iso(row: dict) -> dict:
    return {k: (v.isoformat(timespec="seconds") if hasattr(v, "isoformat") else v) for k, v in row.items()}


class PgStore:
    def __init__(self, pool: ConnectionPool, ensure_schema: bool = True):
        self.pool = pool
        if ensure_schema:
            with pool.connection() as c:
                c.execute(DDL)

    def _all(self, sql: str, args=()) -> list[dict]:
        with self.pool.connection() as c:
            return [_iso(r) for r in c.execute(sql, args).fetchall()]

    def _one(self, sql: str, args=()) -> dict | None:
        rows = self._all(sql, args)
        return rows[0] if rows else None

    def _exec(self, sql: str, args=()) -> None:
        with self.pool.connection() as c:
            c.execute(sql, args)

    # -- ideas & runs --------------------------------------------------------
    def create_run(self, idea: dict, provider: str, model: str) -> str:
        from psycopg.types.json import Jsonb
        idea_id, run_id = uuid.uuid4().hex[:12], uuid.uuid4().hex[:12]
        with self.pool.connection() as c, c.transaction():
            c.execute("INSERT INTO twin.ideas (id, title, payload) VALUES (%s,%s,%s)", (idea_id, idea["title"], Jsonb(idea)))
            c.execute("INSERT INTO twin.runs (id, idea_id, title, status, provider, model) VALUES (%s,%s,%s,'queued',%s,%s)",
                      (run_id, idea_id, idea["title"], provider, model))
        return run_id

    def update_run(self, run_id: str, **fields) -> None:
        fields = {k: v for k, v in fields.items() if k in UPDATABLE}
        if not fields:
            return
        cols = ", ".join(f"{k} = %s" for k in fields)
        self._exec(f"UPDATE twin.runs SET {cols}, updated_at = now() WHERE id = %s", (*fields.values(), run_id))

    def get_run(self, run_id: str) -> dict | None:
        return self._one(f"SELECT {RUN_COLS} FROM twin.runs WHERE id = %s", (run_id,))

    def list_runs(self, limit: int = 200) -> list[dict]:
        return self._all(f"SELECT {RUN_COLS} FROM twin.runs ORDER BY updated_at DESC LIMIT %s", (limit,))

    # -- events --------------------------------------------------------------
    def add_event(self, run_id: str, node: str, message: str, level: str = "info") -> None:
        self._exec("INSERT INTO twin.events (run_id, node, level, message) VALUES (%s,%s,%s,%s)", (run_id, node, level, message))

    def events(self, run_id: str) -> list[dict]:
        return self._all("SELECT id, run_id, ts, node, level, message FROM twin.events WHERE run_id = %s ORDER BY id", (run_id,))

    # -- projects ------------------------------------------------------------
    def add_project(self, slug, run_id, title, kind, path, file_count) -> None:
        self._exec(
            "INSERT INTO twin.projects (slug, run_id, title, kind, path, file_count) VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (slug) DO UPDATE SET run_id = excluded.run_id, title = excluded.title, kind = excluded.kind, "
            "path = excluded.path, file_count = excluded.file_count",
            (slug, run_id, title, kind, path, file_count))

    def list_projects(self) -> list[dict]:
        return self._all("SELECT * FROM twin.projects ORDER BY created_at DESC")

    def get_project(self, slug: str) -> dict | None:
        return self._one("SELECT * FROM twin.projects WHERE slug = %s", (slug,))

    def add_files(self, slug: str, files: dict[str, str]) -> None:
        with self.pool.connection() as c, c.transaction():
            with c.cursor() as cur:
                cur.executemany(
                    "INSERT INTO twin.project_files (slug, path, content) VALUES (%s,%s,%s) "
                    "ON CONFLICT (slug, path) DO UPDATE SET content = excluded.content",
                    [(slug, p, body) for p, body in files.items()])

    def list_files(self, slug: str) -> list[str]:
        return [r["path"] for r in self._all("SELECT path FROM twin.project_files WHERE slug = %s ORDER BY path", (slug,))]

    def read_file(self, slug: str, path: str) -> str | None:
        row = self._one("SELECT content FROM twin.project_files WHERE slug = %s AND path = %s", (slug, path))
        return row["content"] if row else None
