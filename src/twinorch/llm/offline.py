"""Offline rules engine: deterministic classify/plan with no API key.

Good enough to exercise the whole pipeline end to end (and for tests); swap in
Claude for real planning quality.
"""

from __future__ import annotations

import re

from twinorch.domain.catalog import DEFAULT_STACK, KIND_KEYWORDS, TAG_KEYWORDS
from twinorch.domain.models import (
    Blueprint, Classification, Component, DataAssessment, DomainTag, IdeaIn, Milestone, ProjectKind,
)


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:max_len].rstrip("-")) or "project"


def _score(text: str, words: list[str]) -> int:
    return sum(text.count(w) for w in words)


class OfflineLLM:
    provider = "offline"
    model = "rules-v1"

    def classify(self, idea: IdeaIn) -> Classification:
        text = f" {idea.title} {idea.problem} {idea.outcome} {idea.data_notes} ".lower()
        scores = {k: _score(text, w) for k, w in KIND_KEYWORDS.items()}
        agent, ml, pipe = scores[ProjectKind.llm_agent], scores[ProjectKind.ml_model], scores[ProjectKind.data_pipeline]

        if idea.kind_hint:
            kind = idea.kind_hint
        elif agent and ml and min(agent, ml) >= max(agent, ml) / 2:
            kind = ProjectKind.hybrid
        else:
            kind = max(scores, key=lambda k: (scores[k], k == ProjectKind.ml_model))
            if not any(scores.values()):
                kind = ProjectKind.llm_agent

        tag_scores = {t: _score(text, w) for t, w in TAG_KEYWORDS.items()}
        tags = [t for t, s in sorted(tag_scores.items(), key=lambda kv: -kv[1]) if s][:4] or [DomainTag.general]

        total = sum(scores.values()) or 1
        top = scores.get(kind, 0) if kind != ProjectKind.hybrid else agent + ml
        confidence = 0.95 if idea.kind_hint else round(min(0.9, 0.4 + 0.5 * top / total), 2)
        rationale = (
            f"Keyword signals: agent {agent}, ML {ml}, pipeline {pipe}. "
            + ("Kind set by the requester. " if idea.kind_hint else "")
            + f"Main domains: {', '.join(t.value for t in tags)}."
        )
        return Classification(kind=kind, domain_tags=tags, rationale=rationale,
                              confidence=confidence, project_name=slugify(idea.title))

    def plan(self, idea: IdeaIn, classification: Classification, data: DataAssessment,
             feedback: list[str]) -> Blueprint:
        kind = classification.kind
        tags = ", ".join(t.value.replace("_", " ") for t in classification.domain_tags)
        datasets = [m for m in data.matches]
        ready = [m for m in datasets if m.ready]

        components = [Component(name="Config and settings", layer="ops", purpose="Environment-driven settings, secrets kept out of code")]
        milestones: list[Milestone] = []
        metrics: list[str] = []
        risks: list[str] = []
        tools: list[str] = []
        models: list[str] = []

        if kind in (ProjectKind.ml_model, ProjectKind.data_pipeline, ProjectKind.hybrid):
            src = ", ".join(f"{m.dataset_id} {m.name}" for m in (ready or datasets)[:3]) or "a simulated dataset"
            components += [
                Component(name="Data loader", layer="data", purpose=f"Load and validate {src}"),
                Component(name="Quality checks", layer="data", purpose="Schema, null-rate and range checks before training or loading"),
            ]
            milestones.append(Milestone(title="Data access and profiling", deliverable=f"Profiled copy of {src}", est_days=3))
            if data.gaps:
                risks.append(f"Fields not publicly available: {', '.join(data.gaps[:5])}. Plan a fleet data-sharing request or simulation.")
            if not ready:
                risks.append("No dataset is ready to use yet; confirm licences before building on it.")

        if kind in (ProjectKind.ml_model, ProjectKind.hybrid):
            components += [
                Component(name="Feature builder", layer="features", purpose="Rolling statistics, lags and duty-cycle features"),
                Component(name="Trainer and evaluator", layer="model", purpose="Baseline vs gradient boosting with time-aware validation"),
            ]
            models = ["Logistic regression baseline", "LightGBM / gradient boosting", "Isolation Forest (anomaly)"]
            if DomainTag.remaining_useful_life in classification.domain_tags:
                models.append("GRU sequence model for RUL")
            metrics += ["PR-AUC >= 0.80 on held-out vehicles", "Cost-weighted error vs baseline (false negative 50x false positive)",
                        "Calibration: Brier score reported per vehicle segment"]
            milestones += [
                Milestone(title="Baseline model", deliverable="Logistic regression with documented metrics", est_days=3),
                Milestone(title="Improved model", deliverable="Gradient boosting with threshold tuned on business cost", est_days=5),
            ]
            risks.append("Label leakage across time; split by vehicle and date, not by row.")

        if kind == ProjectKind.data_pipeline:
            components += [
                Component(name="Loader", layer="data", purpose="Idempotent upserts into PostgreSQL"),
                Component(name="Report", layer="ui", purpose="Summary tables and charts for the operations team"),
            ]
            metrics += ["0 error-level data-quality failures per run", "Reruns produce identical row counts (idempotent)",
                        "Data freshness under 24 hours"]
            milestones += [
                Milestone(title="Pipeline skeleton", deliverable="Extract, transform, quality and load steps with tests", est_days=4),
                Milestone(title="Scheduling and alerts", deliverable="Daily schedule and failure alerts", est_days=2),
            ]

        if kind in (ProjectKind.llm_agent, ProjectKind.hybrid):
            tools = ["search_service_manual", "lookup_fault_code", "get_vehicle_history", "create_job_card"]
            if kind == ProjectKind.hybrid:
                tools.append("predict_failure_risk")
            components += [
                Component(name="Agent graph", layer="agent", purpose="LangGraph loop: understand, call tools, answer with sources"),
                Component(name="Tool adapters", layer="tools", purpose="Typed wrappers around manuals, fault codes and history"),
                Component(name="Evaluation set", layer="ops", purpose="Real technician questions with expected answers"),
            ]
            metrics += ["Answer accuracy >= 85% on a 50-question eval set", "Every answer cites a source document",
                        "p90 response time under 20 s"]
            milestones += [
                Milestone(title="Tool adapters", deliverable="Fault-code lookup and manual search with tests", est_days=4),
                Milestone(title="Agent loop", deliverable="LangGraph agent answering eval questions", est_days=4),
                Milestone(title="Evaluation", deliverable="Scored eval report and failure review", est_days=3),
            ]
            risks.append("Hallucinated procedures; require citations and refuse when no source is found.")

        components.append(Component(name="API", layer="api", purpose="HTTP endpoint for other tools to call"))
        milestones.append(Milestone(title="Pilot", deliverable="Two-week pilot with one fleet or workshop, with a results write-up", est_days=10))

        summary = (
            f"{DEFAULT_STACK[kind][0]} project for {tags or 'general'}: {idea.outcome.rstrip('.')}. "
            f"Built as a {kind.value.replace('_', ' ')} on {', '.join(DEFAULT_STACK[kind][1:])}."
        )
        if feedback:
            summary += " Revision addresses: " + "; ".join(feedback) + "."
            milestones.insert(0, Milestone(title="Reviewer changes", deliverable="; ".join(feedback)[:200], est_days=1))

        return Blueprint(summary=summary, components=components, milestones=milestones,
                         eval_metrics=metrics, risks=risks, agent_tools=tools, model_candidates=models)
