"""File templates per project kind. `$name` placeholders are filled by the writer."""

from __future__ import annotations

from twinorch.domain.models import ProjectKind

COMMON = {
    "pyproject.toml": '''[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "$slug"
version = "0.1.0"
description = "$title"
requires-python = ">=3.10"
dependencies = [$dependencies]

[project.optional-dependencies]
dev = ["pytest>=7"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
''',
    "src/$pkg/__init__.py": '''"""$title"""

__version__ = "0.1.0"
''',
    "src/$pkg/config.py": '''"""Settings from environment variables."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    data_dir: str = field(default_factory=lambda: os.getenv("DATA_DIR", "data"))
    model: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-opus-5-5"))
''',
    ".gitignore": ".venv/\n__pycache__/\n*.pyc\ndata/raw/\n",
}

LLM_AGENT = {
    "src/$pkg/tools.py": '''"""Tool adapters the agent can call. Replace the stubs with real integrations."""

from __future__ import annotations

from typing import Callable

TOOLS: dict[str, Callable[..., dict]] = {}


def tool(fn: Callable[..., dict]) -> Callable[..., dict]:
    TOOLS[fn.__name__] = fn
    return fn

$tool_stubs
''',
    "src/$pkg/prompts.py": '''"""System prompt for the agent. Keep it short and specific."""

SYSTEM = (
    "You help commercial-vehicle technicians and fleet engineers. "
    "Answer only from tool results, cite the source of every step, "
    "and say so plainly when no source covers the question."
)
''',
    "src/$pkg/agent.py": '''"""LangGraph agent: Claude decides which tool to call, the graph runs it, Claude answers."""

from __future__ import annotations

import json
from typing import TypedDict

import anthropic
from langgraph.graph import END, START, StateGraph

from $pkg.config import Settings
from $pkg.prompts import SYSTEM
from $pkg.tools import TOOLS

TOOL_SPECS = [
    {
        "name": name,
        "description": (fn.__doc__ or name).strip(),
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }
    for name, fn in TOOLS.items()
]


class AgentState(TypedDict):
    messages: list
    final: str


def call_model(state: AgentState) -> dict:
    settings = Settings()
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=settings.model,
        max_tokens=16000,
        system=SYSTEM,
        tools=TOOL_SPECS,
        messages=state["messages"],
    )
    if response.stop_reason == "refusal":
        return {"final": "The model declined this request.", "messages": state["messages"]}
    messages = state["messages"] + [{"role": "assistant", "content": response.content}]
    if response.stop_reason != "tool_use":
        text = "".join(b.text for b in response.content if b.type == "text")
        return {"messages": messages, "final": text}
    return {"messages": messages}


def run_tools(state: AgentState) -> dict:
    last = state["messages"][-1]["content"]
    results = []
    for block in last:
        if getattr(block, "type", None) != "tool_use":
            continue
        fn = TOOLS.get(block.name)
        try:
            output = fn(**block.input) if fn else {"error": f"unknown tool {block.name}"}
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output)})
        except Exception as exc:  # report tool failures back to the model
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(exc), "is_error": True})
    return {"messages": state["messages"] + [{"role": "user", "content": results}]}


def route(state: AgentState) -> str:
    return END if state.get("final") else "tools"


def build_agent():
    g = StateGraph(AgentState)
    g.add_node("model", call_model)
    g.add_node("tools", run_tools)
    g.add_edge(START, "model")
    g.add_conditional_edges("model", route, {"tools": "tools", END: END})
    g.add_edge("tools", "model")
    return g.compile()


def ask(question: str) -> str:
    result = build_agent().invoke({"messages": [{"role": "user", "content": question}], "final": ""})
    return result["final"]


if __name__ == "__main__":
    import sys
    print(ask(" ".join(sys.argv[1:]) or "What does fault code P20EE mean?"))
''',
    "evals/cases.jsonl": '''{"question": "What does fault code P20EE indicate on a BS6 truck?", "must_mention": ["SCR", "NOx"]}
{"question": "Steps to force a DPF regeneration?", "must_mention": ["regeneration"]}
''',
    "tests/test_tools.py": '''from $pkg.tools import TOOLS


def test_tools_are_registered():
    assert TOOLS, "no tools registered"


def test_tools_return_dicts():
    for name, fn in TOOLS.items():
        assert isinstance(fn(query="test"), dict), name
''',
}

ML_MODEL = {
    "src/$pkg/data.py": '''"""Load and validate the training data.

Candidate open datasets (from the research inventory):
$dataset_lines
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS: list[str] = []  # fill in once the dataset is chosen


def load(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, na_values=["na", "NA", ""])
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    return df


def null_report(df: pd.DataFrame) -> pd.Series:
    return df.isna().mean().sort_values(ascending=False)
''',
    "src/$pkg/features.py": '''"""Feature engineering: rolling statistics and lags per unit (vehicle or engine)."""

from __future__ import annotations

import pandas as pd


def rolling_features(df: pd.DataFrame, unit: str, time: str, cols: list[str], window: int = 5) -> pd.DataFrame:
    df = df.sort_values([unit, time]).copy()
    grouped = df.groupby(unit)
    for c in cols:
        df[f"{c}_mean_{window}"] = grouped[c].transform(lambda s: s.rolling(window, min_periods=1).mean())
        df[f"{c}_delta"] = grouped[c].diff().fillna(0.0)
    return df
''',
    "src/$pkg/train.py": '''"""Train a baseline and a gradient-boosting model; pick the threshold on business cost."""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupShuffleSplit

FN_COST, FP_COST = 500.0, 10.0  # a missed failure costs far more than a false alarm


def best_threshold(y_true: np.ndarray, proba: np.ndarray) -> tuple[float, float]:
    best = (0.5, float("inf"))
    for t in np.linspace(0.01, 0.99, 99):
        pred = proba >= t
        cost = FN_COST * np.sum(~pred & (y_true == 1)) + FP_COST * np.sum(pred & (y_true == 0))
        if cost < best[1]:
            best = (float(t), float(cost))
    return best


def train(df: pd.DataFrame, target: str, group: str) -> dict:
    X = df.drop(columns=[target, group]).select_dtypes("number").fillna(0.0)
    y = df[target].to_numpy()
    tr, te = next(GroupShuffleSplit(test_size=0.25, random_state=7).split(X, y, df[group]))
    report = {}
    for name, model in {
        "logistic_baseline": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "gradient_boosting": HistGradientBoostingClassifier(class_weight="balanced"),
    }.items():
        model.fit(X.iloc[tr], y[tr])
        proba = model.predict_proba(X.iloc[te])[:, 1]
        threshold, cost = best_threshold(y[te], proba)
        report[name] = {"pr_auc": float(average_precision_score(y[te], proba)), "threshold": threshold, "cost": cost}
    return report


if __name__ == "__main__":
    frame = pd.read_csv(sys.argv[1])
    print(json.dumps(train(frame, target=sys.argv[2], group=sys.argv[3]), indent=2))
''',
    "configs/train.json": '''{"target": "label", "group": "unit_id", "fn_cost": 500, "fp_cost": 10}
''',
    "tests/test_features.py": '''import pandas as pd

from $pkg.features import rolling_features


def test_rolling_features_per_unit():
    df = pd.DataFrame({"unit": [1, 1, 2], "t": [1, 2, 1], "x": [1.0, 3.0, 5.0]})
    out = rolling_features(df, "unit", "t", ["x"], window=2)
    assert out.loc[out.unit == 1, "x_mean_2"].tolist() == [1.0, 2.0]
    assert out.loc[out.unit == 2, "x_delta"].tolist() == [0.0]
''',
}

DATA_PIPELINE = {
    "src/$pkg/extract.py": '''"""Extract: download raw files once, keyed by checksum.

Candidate sources (from the research inventory):
$dataset_lines
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
''',
    "src/$pkg/transform.py": '''"""Transform: type, trim and deduplicate."""

from __future__ import annotations

import pandas as pd


def clean(df: pd.DataFrame, key: list[str]) -> pd.DataFrame:
    df = df.copy()
    for c in df.select_dtypes("object"):
        df[c] = df[c].str.strip()
    return df.drop_duplicates(subset=key, keep="last")
''',
    "src/$pkg/quality.py": '''"""Quality gates: fail the run on error-level problems."""

from __future__ import annotations

import pandas as pd


def check(df: pd.DataFrame, key: list[str], non_negative: list[str]) -> list[str]:
    problems = []
    if df.duplicated(subset=key).any():
        problems.append("duplicate keys")
    for c in non_negative:
        if (df[c] < 0).any():
            problems.append(f"negative values in {c}")
    return problems
''',
    "src/$pkg/pipeline.py": '''"""Run extract -> transform -> quality -> load."""

from __future__ import annotations

import sys

import pandas as pd

from $pkg.quality import check
from $pkg.transform import clean


def run(path: str, key: list[str], non_negative: list[str]) -> pd.DataFrame:
    df = clean(pd.read_csv(path), key)
    problems = check(df, key, non_negative)
    if problems:
        raise SystemExit("quality gate failed: " + "; ".join(problems))
    return df


if __name__ == "__main__":
    print(run(sys.argv[1], key=sys.argv[2].split(","), non_negative=[]).head())
''',
    "sql/schema.sql": '''-- Target table for $title
CREATE TABLE IF NOT EXISTS staging_records (
    record_id   BIGSERIAL PRIMARY KEY,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload     JSONB NOT NULL
);
''',
    "tests/test_quality.py": '''import pandas as pd

from $pkg.quality import check


def test_duplicate_keys_fail():
    df = pd.DataFrame({"id": [1, 1], "v": [1, 2]})
    assert "duplicate keys" in check(df, ["id"], ["v"])
''',
}

KIND_FILES = {
    ProjectKind.llm_agent: LLM_AGENT,
    ProjectKind.ml_model: ML_MODEL,
    ProjectKind.data_pipeline: DATA_PIPELINE,
    ProjectKind.hybrid: {**ML_MODEL, **LLM_AGENT},
}

KIND_DEPENDENCIES = {
    ProjectKind.llm_agent: ["anthropic", "langgraph"],
    ProjectKind.ml_model: ["pandas", "numpy", "scikit-learn"],
    ProjectKind.data_pipeline: ["pandas", "psycopg[binary]"],
    ProjectKind.hybrid: ["anthropic", "langgraph", "pandas", "numpy", "scikit-learn"],
}
