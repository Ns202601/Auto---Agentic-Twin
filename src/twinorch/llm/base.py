"""The single interface every LLM adapter implements."""

from __future__ import annotations

from typing import Protocol

from twinorch.domain.models import Blueprint, Classification, DataAssessment, IdeaIn


class LLMError(RuntimeError):
    """Raised when the model cannot return a usable answer (refusal, truncation, invalid JSON)."""


class LLM(Protocol):
    provider: str
    model: str

    def classify(self, idea: IdeaIn) -> Classification: ...

    def plan(
        self,
        idea: IdeaIn,
        classification: Classification,
        data: DataAssessment,
        feedback: list[str],
    ) -> Blueprint: ...


def strict_schema(model_cls) -> dict:
    """Pydantic JSON schema -> strict schema for structured outputs.

    Inlines $defs, drops titles/defaults, and marks every object closed with all
    properties required (the structured-output contract).
    """
    schema = model_cls.model_json_schema()
    defs = schema.pop("$defs", {})

    def resolve(node):
        if isinstance(node, list):
            return [resolve(x) for x in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            target = resolve(defs[node["$ref"].rsplit("/", 1)[-1]])
            extra = {k: resolve(v) for k, v in node.items() if k not in ("$ref", "title", "default")}
            return {**target, **extra}
        out = {k: resolve(v) for k, v in node.items() if k not in ("title", "default")}
        if out.get("type") == "object" and "properties" in out:
            out["additionalProperties"] = False
            out["required"] = list(out["properties"].keys())
        return out

    return resolve(schema)


def idea_brief(idea: IdeaIn) -> str:
    parts = [
        f"Title: {idea.title}",
        f"Problem: {idea.problem}",
        f"Desired outcome: {idea.outcome}",
    ]
    if idea.data_notes:
        parts.append(f"Data available: {idea.data_notes}")
    if idea.constraints:
        parts.append(f"Constraints: {idea.constraints}")
    if idea.kind_hint:
        parts.append(f"The requester wants this built as: {idea.kind_hint.value}")
    return "\n".join(parts)
