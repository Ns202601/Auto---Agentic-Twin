"""The orchestration graph.

    START -> intake -> classify --(agent)--------------------> plan -> review --approve--> scaffold -> register -> END
                                 \\--(ml / pipeline / hybrid)-> assess_data -^      |  ^
                                                                                   |  '--revise (comments)--'
                                                                                   '--reject--> END

`review` pauses the graph with `interrupt()` until a person approves, asks for
changes, or rejects. State is checkpointed (SQLite) so a run survives restarts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from twinorch.domain.catalog import KINDS_NEEDING_DATA
from twinorch.domain.models import (
    Blueprint, Classification, DataAssessment, IdeaIn, ProjectKind, ReviewDecision,
)
from twinorch.llm.base import LLM
from twinorch.llm.offline import slugify
from twinorch.research import assess_data
from twinorch.scaffold.writer import write_project


class OrchestratorState(TypedDict, total=False):
    run_id: str
    idea: dict
    classification: dict
    data: dict
    blueprint: dict
    feedback: list[str]
    revision: int
    decision: dict
    project: dict
    outcome: str  # completed | rejected


@dataclass
class Deps:
    llm: LLM
    repo_root: Path
    projects_dir: Path
    max_revisions: int = 5


NODE_ORDER = ["intake", "classify", "assess_data", "plan", "review", "scaffold", "register"]
NODE_LABELS = {
    "intake": "Intake",
    "classify": "Classify",
    "assess_data": "Assess data",
    "plan": "Plan",
    "review": "Human review",
    "scaffold": "Scaffold",
    "register": "Register",
}


def build_graph(deps: Deps, checkpointer=None):
    # -- nodes ---------------------------------------------------------------
    def intake(state: OrchestratorState) -> dict:
        idea = IdeaIn.model_validate(state["idea"])  # re-validate at the graph boundary
        clean = idea.model_copy(update={k: getattr(idea, k).strip() for k in
                                        ("title", "problem", "outcome", "data_notes", "constraints")})
        return {"idea": clean.model_dump(mode="json"), "feedback": [], "revision": 0}

    def classify(state: OrchestratorState) -> dict:
        idea = IdeaIn.model_validate(state["idea"])
        result = deps.llm.classify(idea)
        if idea.kind_hint and result.kind != idea.kind_hint:
            result = result.model_copy(update={
                "kind": idea.kind_hint,
                "rationale": result.rationale + f" Overridden to {idea.kind_hint.value} by the requester.",
            })
        result.project_name = slugify(result.project_name or idea.title)
        return {"classification": result.model_dump(mode="json")}

    def assess(state: OrchestratorState) -> dict:
        c = Classification.model_validate(state["classification"])
        return {"data": assess_data(deps.repo_root, c).model_dump(mode="json")}

    def plan(state: OrchestratorState) -> dict:
        idea = IdeaIn.model_validate(state["idea"])
        c = Classification.model_validate(state["classification"])
        data = DataAssessment.model_validate(state.get("data") or
                                             {"applicable": False, "readiness": "not_applicable"})
        bp = deps.llm.plan(idea, c, data, state.get("feedback", []))
        return {"blueprint": bp.model_dump(mode="json"), "revision": state.get("revision", 0) + 1,
                "data": data.model_dump(mode="json")}

    def review(state: OrchestratorState) -> dict:
        answer = interrupt({
            "question": "Approve this blueprint, request changes, or reject it.",
            "revision": state.get("revision", 1),
            "blueprint": state["blueprint"],
        })
        decision = ReviewDecision.model_validate(answer)
        update: dict[str, Any] = {"decision": decision.model_dump()}
        if decision.action == "revise":
            note = decision.comment.strip() or "Tighten the plan."
            update["feedback"] = [*state.get("feedback", []), note]
        if decision.action == "reject":
            update["outcome"] = "rejected"
        return update

    def scaffold(state: OrchestratorState) -> dict:
        project = write_project(
            deps.projects_dir,
            Classification.model_validate(state["classification"]).project_name,
            IdeaIn.model_validate(state["idea"]),
            Classification.model_validate(state["classification"]),
            DataAssessment.model_validate(state["data"]),
            Blueprint.model_validate(state["blueprint"]),
        )
        return {"project": project}

    def register(state: OrchestratorState) -> dict:
        return {"outcome": "completed"}

    # -- routing -------------------------------------------------------------
    def after_classify(state: OrchestratorState) -> str:
        kind = ProjectKind(state["classification"]["kind"])
        return "assess_data" if kind in KINDS_NEEDING_DATA else "plan"

    def after_review(state: OrchestratorState) -> str:
        action = state["decision"]["action"]
        if action == "approve":
            return "scaffold"
        if action == "revise" and state.get("revision", 0) < deps.max_revisions:
            return "plan"
        return END

    g = StateGraph(OrchestratorState)
    g.add_node("intake", intake)
    g.add_node("classify", classify)
    g.add_node("assess_data", assess)
    g.add_node("plan", plan)
    g.add_node("review", review)
    g.add_node("scaffold", scaffold)
    g.add_node("register", register)

    g.add_edge(START, "intake")
    g.add_edge("intake", "classify")
    g.add_conditional_edges("classify", after_classify, {"assess_data": "assess_data", "plan": "plan"})
    g.add_edge("assess_data", "plan")
    g.add_edge("plan", "review")
    g.add_conditional_edges("review", after_review, {"scaffold": "scaffold", "plan": "plan", END: END})
    g.add_edge("scaffold", "register")
    g.add_edge("register", END)
    return g.compile(checkpointer=checkpointer)


def describe_update(node: str, update: dict | None) -> str:
    """One human-readable line per node update, for the run timeline."""
    u = update or {}
    if node == "intake":
        return f"Idea received: {u.get('idea', {}).get('title', '')}"
    if node == "classify":
        c = u.get("classification", {})
        return (f"Classified as {c.get('kind', '?').replace('_', ' ')} "
                f"({round(100 * float(c.get('confidence', 0)))}% confidence); "
                f"domains: {', '.join(c.get('domain_tags', []))}")
    if node == "assess_data":
        d = u.get("data", {})
        return (f"Data {d.get('readiness')}: {len(d.get('matches', []))} candidate datasets, "
                f"{len(d.get('gaps', []))} fields not public")
    if node == "plan":
        b = u.get("blueprint", {})
        return (f"Blueprint v{u.get('revision')}: {len(b.get('components', []))} components, "
                f"{len(b.get('milestones', []))} milestones")
    if node == "review":
        d = u.get("decision", {})
        comment = f": {d.get('comment')}" if d.get("comment") else ""
        return f"Review decision: {d.get('action')}{comment}"
    if node == "scaffold":
        p = u.get("project", {})
        return f"Scaffolded {len(p.get('files', []))} files into projects/{p.get('slug')}"
    if node == "register":
        return "Project registered"
    return node
