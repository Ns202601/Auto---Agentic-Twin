from __future__ import annotations

from twinorch.config import Settings
from twinorch.llm.base import LLM


def make_llm(settings: Settings) -> LLM:
    if settings.resolved_provider() == "anthropic":
        from twinorch.llm.anthropic_llm import AnthropicLLM
        return AnthropicLLM(settings.model, settings.classify_effort, settings.plan_effort)
    from twinorch.llm.offline import OfflineLLM
    return OfflineLLM()
