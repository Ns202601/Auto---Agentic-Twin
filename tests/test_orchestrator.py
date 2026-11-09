"""Tests for the twinorch orchestrator: graph routing, human review, scaffolding, API, Claude adapter."""

from __future__ import annotations

import json
import py_compile
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from twinorch.api.app import create_app
from twinorch.config import Settings
from twinorch.domain.models import (
    Blueprint, Classification, DomainTag, IdeaIn, ProjectKind, ReviewDecision,
)
from twinorch.llm.base import LLMError, strict_schema
from twinorch.llm.offline import OfflineLLM
from twinorch.research import assess_data
from twinorch.service import Conflict, OrchestratorService

ROOT = Path(__file__).resolve().parents[1]

IDEAS = {
    "agent": IdeaIn(title="Technician fault-code copilot",
                    problem="Field technicians lose time searching manuals for BS6 fault codes and procedures.",
                    outcome="An assistant that answers fault-code questions with cited manual steps"),
    "ml": IdeaIn(title="DPF blockage early warning",
                 problem="Trucks get forced DPF regenerations and derates without warning.",
                 outcome="Predict DPF blockage and failure risk days ahead"),
    "pipeline": IdeaIn(title="VAHAN registrations pipeline",
                       problem="Market registration data is pulled by hand into spreadsheets every month.",
                       outcome="A scheduled pipeline that ingests registrations into a warehouse with data quality checks"),
}


@pytest.fixture
def svc(tmp_path):
    s = OrchestratorService(Settings(llm_provider="offline", data_dir=tmp_path / "var",
                                     projects_dir=tmp_path / "projects", max_revisions=3))
    yield s
    s.close()


def run_to_review(svc, idea):
    run = svc.submit_idea(idea, wait=True)
    assert run["status"] == "awaiting_review", run.get("error")
    return run


# -- graph routing -------------------------------------------------------------
def test_agent_skips_data_assessment(svc):
    run = run_to_review(svc, IDEAS["agent"])
    assert run["kind"] == "llm_agent"
    assert "assess_data" not in run["visited"]
    assert run["pending"] == ["review"]


def test_ml_idea_assesses_data_and_finds_gaps(svc):
    run = run_to_review(svc, IDEAS["ml"])
    assert run["kind"] == "ml_model"
    assert "assess_data" in run["visited"]
    data = run["state"]["data"]
    assert data["readiness"] in ("ready", "partial")
    assert "dpf_differential_pressure" in data["gaps"]


def test_kind_hint_overrides_classifier(svc):
    idea = IDEAS["agent"].model_copy(update={"kind_hint": ProjectKind.data_pipeline})
    run = run_to_review(svc, idea)
    assert run["kind"] == "data_pipeline"


def test_approve_scaffolds_and_registers(svc):
    run = run_to_review(svc, IDEAS["pipeline"])
    done = svc.review(run["id"], ReviewDecision(action="approve"), wait=True)
    assert done["status"] == "completed"
    project = svc.list_projects()[0]
    files = svc.project_files(project["slug"])["files"]
    assert "README.md" in files and "blueprint.json" in files
    assert "VAHAN" in svc.read_file(project["slug"], "README.md")


def test_revise_loops_back_to_plan_with_feedback(svc):
    run = run_to_review(svc, IDEAS["ml"])
    run = svc.review(run["id"], ReviewDecision(action="revise", comment="Add a drift monitor"), wait=True)
    assert run["status"] == "awaiting_review"
    assert run["revision"] == 2
    assert "Add a drift monitor" in run["state"]["blueprint"]["summary"]


def test_reject_ends_run(svc):
    run = run_to_review(svc, IDEAS["agent"])
    run = svc.review(run["id"], ReviewDecision(action="reject", comment="Not now"), wait=True)
    assert run["status"] == "rejected"
    assert svc.list_projects() == []


def test_revision_limit_stops_run(svc):
    run = run_to_review(svc, IDEAS["agent"])
    for _ in range(3):
        run = svc.review(run["id"], ReviewDecision(action="revise", comment="again"), wait=True)
    assert run["status"] == "rejected"
    assert any("revisions" in e["message"] for e in run["events"])


def test_review_requires_waiting_run(svc):
    run = run_to_review(svc, IDEAS["agent"])
    svc.review(run["id"], ReviewDecision(action="reject"), wait=True)
    with pytest.raises(Conflict):
        svc.review(run["id"], ReviewDecision(action="approve"))


def test_llm_error_marks_run_failed(tmp_path):
    class Broken(OfflineLLM):
        def plan(self, *a, **k):
            raise LLMError("The model declined this request (category: cyber).")

    s = OrchestratorService(Settings(llm_provider="offline", data_dir=tmp_path / "v", projects_dir=tmp_path / "p"),
                            llm=Broken())
    try:
        run = s.submit_idea(IDEAS["agent"], wait=True)
        assert run["status"] == "failed"
        assert "declined" in run["error"]
    finally:
        s.close()


def test_state_survives_restart(tmp_path):
    settings = Settings(llm_provider="offline", data_dir=tmp_path / "v", projects_dir=tmp_path / "p")
    a = OrchestratorService(settings)
    run_id = a.submit_idea(IDEAS["agent"], wait=True)["id"]
    a.close()
    b = OrchestratorService(settings)  # new process, same databases
    try:
        done = b.review(run_id, ReviewDecision(action="approve"), wait=True)
        assert done["status"] == "completed"
    finally:
        b.close()


# -- scaffold ------------------------------------------------------------------
@pytest.mark.parametrize("kind", list(ProjectKind))
def test_every_kind_scaffolds_compilable_python(svc, kind):
    idea = IDEAS["ml"].model_copy(update={"kind_hint": kind, "title": f"Scaffold {kind.value}"})
    run = run_to_review(svc, idea)
    svc.review(run["id"], ReviewDecision(action="approve"), wait=True)
    slug = svc.list_projects()[0]["slug"]
    root = Path(svc.project_files(slug)["path"])
    py_files = list(root.rglob("*.py"))
    assert py_files
    for f in py_files:
        py_compile.compile(str(f), doraise=True)


# -- research adapter ----------------------------------------------------------
def test_assess_data_blocked_without_matching_dataset():
    c = Classification(kind=ProjectKind.ml_model, domain_tags=[DomainTag.driver_behaviour],
                       rationale="", confidence=0.5, project_name="x")
    a = assess_data(ROOT, c)
    assert a.readiness == "blocked" and a.matches == []


# -- strict schema -------------------------------------------------------------
def test_strict_schema_is_closed_and_inlined():
    schema = strict_schema(Blueprint)
    text = json.dumps(schema)
    assert "$ref" not in text and "$defs" not in text
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    item = schema["properties"]["components"]["items"]
    assert item["additionalProperties"] is False


# -- Claude adapter (fake client: no network, no spend) -------------------------
class FakeMessages:
    def __init__(self, response):
        self.response, self.calls = response, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def make_adapter(response):
    from twinorch.llm.anthropic_llm import AnthropicLLM
    adapter = AnthropicLLM.__new__(AnthropicLLM)
    adapter.model, adapter.classify_effort, adapter.plan_effort = "claude-opus-5-5", "low", "high"
    fake = FakeMessages(response)
    adapter.client = SimpleNamespace(beta=SimpleNamespace(messages=fake))
    return adapter, fake


def text_response(payload: dict, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, stop_details=None,
                           content=[SimpleNamespace(type="text", text=json.dumps(payload))])


def test_anthropic_adapter_request_shape_and_parse():
    payload = {"kind": "llm_agent", "domain_tags": ["service_operations"], "rationale": "r",
               "confidence": 1.4, "project_name": "copilot"}
    adapter, fake = make_adapter(text_response(payload))
    result = adapter.classify(IDEAS["agent"])
    assert result.kind == ProjectKind.llm_agent and result.confidence == 1.0
    call = fake.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default" and "server-side-fallback-2026-07-01" in call["betas"]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["output_config"]["effort"] == "low"


def test_anthropic_adapter_refusal_raises():
    refusal = SimpleNamespace(stop_reason="refusal", stop_details=SimpleNamespace(category="cyber"), content=[])
    adapter, _ = make_adapter(refusal)
    with pytest.raises(LLMError, match="cyber"):
        adapter.classify(IDEAS["agent"])


def test_anthropic_adapter_truncation_raises():
    adapter, _ = make_adapter(text_response({}, stop="max_tokens"))
    with pytest.raises(LLMError, match="cut off"):
        adapter.classify(IDEAS["agent"])


# -- HTTP API ------------------------------------------------------------------
def test_api_end_to_end(svc, tmp_path):
    client = TestClient(create_app(service=svc, ui_dist=tmp_path / "no-ui"))
    with client:
        assert client.get("/api/health").json()["provider"] == "offline"
        meta = client.get("/api/meta").json()
        assert [n["id"] for n in meta["nodes"]][:2] == ["intake", "classify"]
        assert client.post("/api/ideas", json={"title": "x"}).status_code == 422
        r = client.post("/api/ideas", json=IDEAS["agent"].model_dump(mode="json"))
        assert r.status_code == 201
        run_id = r.json()["id"]
        for _ in range(200):  # the run executes on a worker thread; poll like the UI does
            if client.get(f"/api/runs/{run_id}").json()["status"] == "awaiting_review":
                break
            time.sleep(0.025)
        assert client.get(f"/api/runs/{run_id}").json()["status"] == "awaiting_review"
        assert client.post(f"/api/runs/{run_id}/review", json={"action": "maybe"}).status_code == 422
        assert client.get("/api/runs/nope").status_code == 404


# -- Postgres (Supabase) backend: runs only when TWIN_TEST_DATABASE_URL is set --
import os


@pytest.mark.skipif(not os.getenv("TWIN_TEST_DATABASE_URL"), reason="set TWIN_TEST_DATABASE_URL to test Postgres")
def test_postgres_backend_end_to_end(tmp_path):
    settings = Settings(llm_provider="offline", database_url=os.environ["TWIN_TEST_DATABASE_URL"],
                        sync_runs=True, projects_dir=tmp_path / "p", data_dir=tmp_path / "v")
    s = OrchestratorService(settings)
    try:
        run = s.submit_idea(IDEAS["ml"])
        assert run["status"] == "awaiting_review", run.get("error")
        run = s.review(run["id"], ReviewDecision(action="revise", comment="add drift monitor"))
        assert run["revision"] == 2
        run = s.review(run["id"], ReviewDecision(action="approve"))
        assert run["status"] == "completed"
        slug = run["state"]["project"]["slug"]
        assert "README.md" in s.project_files(slug)["files"]
        assert "DPF" in s.read_file(slug, "README.md")
    finally:
        s.close()
    s2 = OrchestratorService(settings)  # fresh process: data must come back from Postgres
    try:
        assert any(r["id"] == run["id"] and r["status"] == "completed" for r in s2.list_runs())
    finally:
        s2.close()


def test_demo_seed_fills_empty_store_once(tmp_path):
    settings = Settings(llm_provider="offline", data_dir=tmp_path / "v", projects_dir=tmp_path / "p", seed_demo=True)
    s = OrchestratorService(settings)
    try:
        statuses = sorted(r["status"] for r in s.list_runs())
        assert statuses == ["awaiting_review", "awaiting_review", "completed"]
    finally:
        s.close()
    s = OrchestratorService(settings)  # second start must not duplicate
    try:
        assert len(s.list_runs()) == 3
    finally:
        s.close()
