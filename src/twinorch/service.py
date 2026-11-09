"""Application service: the use-cases the API (and CLI) call.

Runs execute on a small thread pool. Each run is a LangGraph thread
(thread_id = run_id); its state is checkpointed in SQLite, so a run waiting for
review survives a server restart.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from twinorch.config import Settings
from twinorch.domain.catalog import DEFAULT_STACK, KIND_DESCRIPTIONS, KIND_LABELS
from twinorch.domain.models import IdeaIn, ProjectKind, ReviewDecision, RunStatus
from twinorch.graph.build import NODE_LABELS, NODE_ORDER, Deps, build_graph, describe_update
from twinorch.llm.base import LLM, LLMError
from twinorch.llm.factory import make_llm
from twinorch.store.db import Store

log = logging.getLogger("twinorch")


class NotFound(LookupError):
    pass


class Conflict(RuntimeError):
    pass


class OrchestratorService:
    def __init__(self, settings: Settings | None = None, llm: LLM | None = None, workers: int = 4):
        self.settings = settings or Settings()
        self.llm = llm or make_llm(self.settings)
        self._pool = None
        self._ckpt_conn = None
        if self.settings.database_url:
            from langgraph.checkpoint.postgres import PostgresSaver
            from twinorch.store.pg import PgStore, make_pool
            self._pool = make_pool(self.settings.database_url)
            self.store = PgStore(self._pool)
            self.checkpointer = PostgresSaver(self._pool)
            self.checkpointer.setup()
        else:
            self.store = Store(self.settings.db_path)
            self._ckpt_conn = sqlite3.connect(self.settings.checkpoint_path, check_same_thread=False)
            self.checkpointer = SqliteSaver(self._ckpt_conn)
        self.graph = build_graph(
            Deps(llm=self.llm, repo_root=self.settings.repo_root,
                 projects_dir=self.settings.output_dir, max_revisions=self.settings.max_revisions),
            checkpointer=self.checkpointer,
        )
        self._workers = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="twin-run")
        self._locks: dict[str, threading.Lock] = {}
        if self.settings.seed_demo:
            from twinorch.demo import seed_demo
            seed_demo(self)

    # -- use-cases -----------------------------------------------------------
    def submit_idea(self, idea: IdeaIn, wait: bool = False) -> dict:
        run_id = self.store.create_run(idea.model_dump(mode="json"), self.llm.provider, self.llm.model)
        self.store.add_event(run_id, "intake", "Run queued")
        payload = {"run_id": run_id, "idea": idea.model_dump(mode="json")}
        self._dispatch(run_id, payload, wait)
        return self.get_run(run_id)

    def review(self, run_id: str, decision: ReviewDecision, wait: bool = False) -> dict:
        run = self.store.get_run(run_id)
        if not run:
            raise NotFound(run_id)
        if run["status"] != RunStatus.awaiting_review.value:
            raise Conflict(f"Run is {run['status']}, not awaiting review.")
        self.store.update_run(run_id, status=RunStatus.running.value)
        self.store.add_event(run_id, "review", f"Decision submitted: {decision.action}", level="decision")
        self._dispatch(run_id, Command(resume=decision.model_dump()), wait)
        return self.get_run(run_id)

    # -- execution -----------------------------------------------------------
    def _dispatch(self, run_id: str, payload, wait: bool) -> None:
        if wait or self.settings.sync_runs:
            self._execute(run_id, payload)
            return
        future = self._workers.submit(self._execute, run_id, payload)
        if wait:
            future.result()

    def _execute(self, run_id: str, payload) -> None:
        lock = self._locks.setdefault(run_id, threading.Lock())
        config = {"configurable": {"thread_id": run_id}}
        with lock:
            self.store.update_run(run_id, status=RunStatus.running.value, error=None)
            try:
                for chunk in self.graph.stream(payload, config, stream_mode="updates"):
                    for node, update in chunk.items():
                        if node == "__interrupt__":
                            continue
                        self._record(run_id, node, update)
                snapshot = self.graph.get_state(config)
                values = snapshot.values
                if snapshot.next:
                    nxt = snapshot.next[0]
                    self.store.update_run(run_id, status=RunStatus.awaiting_review.value, current_node=nxt)
                    self.store.add_event(run_id, nxt, "Waiting for your review", level="decision")
                elif values.get("outcome") == "completed":
                    self.store.update_run(run_id, status=RunStatus.completed.value, current_node="register")
                else:
                    reason = "Rejected by reviewer"
                    if values.get("decision", {}).get("action") == "revise":
                        reason = f"Stopped after {self.settings.max_revisions} revisions"
                    self.store.update_run(run_id, status=RunStatus.rejected.value, current_node="review")
                    self.store.add_event(run_id, "review", reason, level="decision")
            except LLMError as e:
                self._fail(run_id, str(e))
            except Exception as e:  # keep the worker alive; surface the error in the UI
                log.exception("run %s failed", run_id)
                self._fail(run_id, f"{type(e).__name__}: {e}")

    def _record(self, run_id: str, node: str, update: dict | None) -> None:
        update = update or {}
        fields = {"current_node": node}
        if node == "classify":
            fields["kind"] = update.get("classification", {}).get("kind")
        if node == "plan":
            fields["revision"] = update.get("revision", 0)
        self.store.update_run(run_id, **fields)
        self.store.add_event(run_id, node, describe_update(node, update))
        if node == "scaffold" and update.get("project"):
            p = update["project"]
            run = self.store.get_run(run_id)
            self.store.add_project(p["slug"], run_id, run["title"], run["kind"] or "", p["path"], len(p["files"]))
            root = Path(p["path"])
            self.store.add_files(p["slug"], {f: (root / f).read_text(encoding="utf-8") for f in p["files"]})

    def _fail(self, run_id: str, message: str) -> None:
        self.store.update_run(run_id, status=RunStatus.failed.value, error=message)
        self.store.add_event(run_id, "error", message, level="error")

    # -- queries -------------------------------------------------------------
    def get_run(self, run_id: str) -> dict:
        run = self.store.get_run(run_id)
        if not run:
            raise NotFound(run_id)
        snapshot = self.graph.get_state({"configurable": {"thread_id": run_id}})
        values = dict(snapshot.values or {})
        values.pop("run_id", None)
        visited = [e["node"] for e in self.store.events(run_id) if e["node"] in NODE_ORDER and e["level"] == "info"]
        return {**run, "state": values, "events": self.store.events(run_id), "visited": visited,
                "pending": list(snapshot.next or [])}

    def list_runs(self) -> list[dict]:
        return self.store.list_runs()

    def list_projects(self) -> list[dict]:
        return self.store.list_projects()

    def project_files(self, slug: str) -> dict:
        project = self.store.get_project(slug)
        if not project:
            raise NotFound(slug)
        return {**project, "files": self.store.list_files(slug)}

    def read_file(self, slug: str, rel: str) -> str:
        project = self.store.get_project(slug)
        if not project:
            raise NotFound(slug)
        content = self.store.read_file(slug, rel)
        if content is None:
            raise NotFound(rel)
        return content[:200_000]

    def meta(self) -> dict:
        g = self.graph.get_graph()
        return {
            "provider": self.llm.provider,
            "model": self.llm.model,
            "kinds": [{"id": k.value, "label": KIND_LABELS[k], "description": KIND_DESCRIPTIONS[k],
                       "stack": DEFAULT_STACK[k]} for k in ProjectKind],
            "nodes": [{"id": n, "label": NODE_LABELS[n]} for n in NODE_ORDER],
            "edges": [{"source": e.source, "target": e.target, "conditional": e.conditional} for e in g.edges],
        }

    def close(self) -> None:
        self._workers.shutdown(wait=True)
        if self._ckpt_conn:
            self._ckpt_conn.close()
        if self._pool:
            self._pool.close()
