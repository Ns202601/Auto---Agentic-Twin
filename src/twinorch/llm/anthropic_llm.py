"""Claude adapter: structured JSON outputs via the Anthropic SDK.

Uses `output_config.format` (JSON schema) so the reply is guaranteed-valid JSON,
then validates it with the pydantic model. Server-side refusal fallbacks are on by
default (`fallbacks="default"`); a refusal or truncation raises LLMError so the
graph can record it instead of crashing.
"""

from __future__ import annotations

import json

import anthropic
from pydantic import BaseModel, ValidationError

from twinorch.domain.catalog import DEFAULT_STACK, KIND_DESCRIPTIONS, TAG_KEYWORDS
from twinorch.domain.models import Blueprint, Classification, DataAssessment, IdeaIn
from twinorch.llm.base import LLMError, idea_brief, strict_schema

FALLBACK_BETA = "server-side-fallback-2026-07-01"

CLASSIFY_SYSTEM = (
    "You triage project ideas for a commercial-vehicle engineering team (trucks, buses, diesel and "
    "electric powertrains, after-treatment, fleets, field service). Decide which kind of project fits "
    "best:\n"
    + "\n".join(f"- {k.value}: {v}" for k, v in KIND_DESCRIPTIONS.items())
    + "\nPick domain tags only from the allowed list. Prefer the simplest kind that delivers the outcome: "
    "choose hybrid only when the idea clearly needs both a trained model and an agent. "
    "Domain keyword hints: "
    + "; ".join(f"{t.value}: {', '.join(w)}" for t, w in TAG_KEYWORDS.items())
)

PLAN_SYSTEM = (
    "You are a senior engineer writing a build blueprint for a small team. Be concrete and specific "
    "to commercial vehicles. Use real metric names with target values. Keep milestones small "
    "(1-10 days each, 4-7 milestones). Only list datasets and data fields that the data assessment "
    "supports; where data is missing, plan a simulation or a data-access step instead of assuming it "
    "exists. For agent projects, list the tools the agent needs; for ML projects, list model families "
    "to compare. Address every reviewer comment explicitly."
)


class AnthropicLLM:
    provider = "anthropic"

    def __init__(self, model: str = "claude-opus-5-5", classify_effort: str = "low", plan_effort: str = "high"):
        self.model = model
        self.classify_effort = classify_effort
        self.plan_effort = plan_effort
        self.client = anthropic.Anthropic()

    # -- core call -----------------------------------------------------------
    def _structured(self, system: str, user: str, out: type[BaseModel], effort: str) -> BaseModel:
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                betas=[FALLBACK_BETA],
                fallbacks="default",
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={
                    "effort": effort,
                    "format": {"type": "json_schema", "schema": strict_schema(out)},
                },
            )
        except anthropic.BadRequestError as e:
            raise LLMError(f"Request rejected by the API: {e.message}") from e
        except anthropic.AuthenticationError as e:
            raise LLMError("Claude credentials are missing or invalid. Set ANTHROPIC_API_KEY or use TWIN_LLM=offline.") from e
        except anthropic.RateLimitError as e:
            raise LLMError("Rate limited by the API after retries. Try again shortly.") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"API error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("Could not reach the Claude API. Check the network.") from e

        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None) if response.stop_details else None
            raise LLMError(f"The model declined this request (category: {category or 'unspecified'}).")
        if response.stop_reason == "max_tokens":
            raise LLMError("The model's answer was cut off (max_tokens). Shorten the idea or retry.")

        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise LLMError("The model returned no text block.")
        try:
            return out.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as e:
            raise LLMError(f"The model's JSON did not match the expected shape: {e}") from e

    # -- use-cases -----------------------------------------------------------
    def classify(self, idea: IdeaIn) -> Classification:
        result = self._structured(CLASSIFY_SYSTEM, idea_brief(idea), Classification, self.classify_effort)
        result.confidence = max(0.0, min(1.0, result.confidence))
        return result

    def plan(self, idea: IdeaIn, classification: Classification, data: DataAssessment,
             feedback: list[str]) -> Blueprint:
        sections = [
            idea_brief(idea),
            f"\nProject kind: {classification.kind.value}. Default stack: {', '.join(DEFAULT_STACK[classification.kind])}.",
            f"Domain tags: {', '.join(t.value for t in classification.domain_tags)}.",
            "\nData assessment (from the team's research repository):",
            data.model_dump_json(indent=2),
        ]
        if feedback:
            sections.append("\nReviewer comments to address in this revision:")
            sections += [f"{i + 1}. {c}" for i, c in enumerate(feedback)]
        return self._structured(PLAN_SYSTEM, "\n".join(sections), Blueprint, self.plan_effort)
