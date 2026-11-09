"""Domain models shared by every layer. No I/O here."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ProjectKind(str, Enum):
    llm_agent = "llm_agent"          # an LLM agent with tools (e.g. technician copilot)
    ml_model = "ml_model"            # a trained predictive model (e.g. failure classifier)
    data_pipeline = "data_pipeline"  # ingest / clean / load / report
    hybrid = "hybrid"                # an agent that calls a trained model


class DomainTag(str, Enum):
    engine_health = "engine_health"
    after_treatment = "after_treatment"
    turbocharger = "turbocharger"
    fuel_efficiency = "fuel_efficiency"
    driver_behaviour = "driver_behaviour"
    fleet_operations = "fleet_operations"
    maintenance = "maintenance"
    remaining_useful_life = "remaining_useful_life"
    ev_battery = "ev_battery"
    market_registrations = "market_registrations"
    emissions_compliance = "emissions_compliance"
    service_operations = "service_operations"
    documents_knowledge = "documents_knowledge"
    general = "general"


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    awaiting_review = "awaiting_review"
    completed = "completed"
    rejected = "rejected"
    failed = "failed"


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
class IdeaIn(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    problem: str = Field(min_length=10, max_length=4000, description="What hurts today, in plain words")
    outcome: str = Field(min_length=5, max_length=2000, description="What good looks like when it works")
    data_notes: str = Field(default="", max_length=2000, description="Data you have or expect to use")
    constraints: str = Field(default="", max_length=2000, description="Budget, latency, privacy, tooling")
    kind_hint: ProjectKind | None = Field(default=None, description="Force a project kind; leave empty for auto")


class ReviewDecision(BaseModel):
    action: Literal["approve", "revise", "reject"]
    comment: str = Field(default="", max_length=2000)


# ---------------------------------------------------------------------------
# LLM outputs (kept free of numeric/length constraints so they map to strict JSON schema)
# ---------------------------------------------------------------------------
class Classification(BaseModel):
    kind: ProjectKind = Field(description="Which kind of project best fits the idea")
    domain_tags: list[DomainTag] = Field(description="1-4 commercial-vehicle domains the idea touches")
    rationale: str = Field(description="Two or three sentences on why this kind fits")
    confidence: float = Field(description="0.0 to 1.0")
    project_name: str = Field(description="Short lowercase name, words joined by hyphens")


class Component(BaseModel):
    name: str
    layer: str = Field(description="One of: data, features, model, agent, tools, api, ui, ops")
    purpose: str


class Milestone(BaseModel):
    title: str
    deliverable: str
    est_days: int = Field(description="Working days, 1 to 30")


class Blueprint(BaseModel):
    summary: str = Field(description="One paragraph: what will be built and for whom")
    components: list[Component]
    milestones: list[Milestone]
    eval_metrics: list[str] = Field(description="How success is measured, with target values where possible")
    risks: list[str]
    agent_tools: list[str] = Field(description="Tool names the agent needs; empty for non-agent projects")
    model_candidates: list[str] = Field(description="Model families to try; empty for non-ML projects")


# ---------------------------------------------------------------------------
# Deterministic results (computed from the repository, not by an LLM)
# ---------------------------------------------------------------------------
class DatasetMatch(BaseModel):
    dataset_id: str
    name: str
    ready: bool
    reason: str
    link: str = ""


class DataAssessment(BaseModel):
    applicable: bool = True
    readiness: Literal["ready", "partial", "blocked", "not_applicable"]
    matches: list[DatasetMatch] = []
    gaps: list[str] = []
    notes: str = ""
