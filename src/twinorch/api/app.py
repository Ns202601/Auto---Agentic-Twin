"""FastAPI layer. Thin: validate input, call the service, map errors to HTTP codes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from twinorch import __version__
from twinorch.domain.models import IdeaIn, ReviewDecision
from twinorch.service import Conflict, NotFound, OrchestratorService


def create_app(service: OrchestratorService | None = None, ui_dist: Path | None = None) -> FastAPI:
    holder: dict[str, OrchestratorService] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        holder["svc"] = service or OrchestratorService()
        yield
        if service is None:
            holder["svc"].close()

    app = FastAPI(title="Agentic Twin Orchestrator", version=__version__, lifespan=lifespan)

    def svc() -> OrchestratorService:
        return holder["svc"]

    @app.get("/api/health")
    def health():
        s = svc()
        return {"status": "ok", "version": __version__, "provider": s.llm.provider, "model": s.llm.model}

    @app.get("/api/meta")
    def meta():
        return svc().meta()

    @app.post("/api/ideas", status_code=201)
    def submit(idea: IdeaIn):
        return svc().submit_idea(idea)

    @app.get("/api/runs")
    def runs():
        return svc().list_runs()

    @app.get("/api/runs/{run_id}")
    def run(run_id: str):
        try:
            return svc().get_run(run_id)
        except NotFound:
            raise HTTPException(404, "Run not found")

    @app.post("/api/runs/{run_id}/review")
    def review(run_id: str, decision: ReviewDecision):
        try:
            return svc().review(run_id, decision)
        except NotFound:
            raise HTTPException(404, "Run not found")
        except Conflict as e:
            raise HTTPException(409, str(e))

    @app.get("/api/projects")
    def projects():
        return svc().list_projects()

    @app.get("/api/projects/{slug}")
    def project(slug: str):
        try:
            return svc().project_files(slug)
        except NotFound:
            raise HTTPException(404, "Project not found")

    @app.get("/api/projects/{slug}/file", response_class=PlainTextResponse)
    def project_file(slug: str, path: str = Query(min_length=1)):
        try:
            return svc().read_file(slug, path)
        except NotFound:
            raise HTTPException(404, "File not found")

    # Serve the built UI (single-page app) when it exists
    dist = ui_dist or Path(__file__).resolve().parents[3] / "ui" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            candidate = (dist / full_path).resolve()
            if full_path and dist.resolve() in candidate.parents and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app
