"""Settings from environment variables, with safe local defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "research").is_dir():
            return parent
    return Path.cwd()


@dataclass(frozen=True)
class Settings:
    repo_root: Path = field(default_factory=_repo_root)
    # auto: use Claude when credentials are present, else the offline rules engine
    llm_provider: str = field(default_factory=lambda: os.getenv("TWIN_LLM", "auto"))
    model: str = field(default_factory=lambda: os.getenv("TWIN_MODEL", "claude-opus-5-5"))
    classify_effort: str = field(default_factory=lambda: os.getenv("TWIN_CLASSIFY_EFFORT", "low"))
    plan_effort: str = field(default_factory=lambda: os.getenv("TWIN_PLAN_EFFORT", "high"))
    max_revisions: int = field(default_factory=lambda: int(os.getenv("TWIN_MAX_REVISIONS", "5")))
    data_dir: Path | None = None
    projects_dir: Path | None = None

    @property
    def db_path(self) -> Path:
        base = self.data_dir or Path(os.getenv("TWIN_DATA_DIR", self.repo_root / "var"))
        return Path(base) / "orchestrator.db"

    @property
    def checkpoint_path(self) -> Path:
        return self.db_path.with_name("checkpoints.db")

    @property
    def output_dir(self) -> Path:
        return Path(self.projects_dir or os.getenv("TWIN_PROJECTS_DIR", self.repo_root / "projects"))

    def resolved_provider(self) -> str:
        if self.llm_provider in ("anthropic", "offline"):
            return self.llm_provider
        has_creds = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
        return "anthropic" if has_creds else "offline"
