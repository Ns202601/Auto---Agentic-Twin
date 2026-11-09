"""Write an approved blueprint to disk as a starter project."""

from __future__ import annotations

import json
import re
from pathlib import Path
from string import Template

from twinorch.domain.catalog import KIND_LABELS
from twinorch.domain.models import Blueprint, Classification, DataAssessment, IdeaIn, ProjectKind
from twinorch.scaffold.templates import COMMON, KIND_DEPENDENCIES, KIND_FILES


def _tool_stubs(tools: list[str]) -> str:
    out = []
    for name in tools or ["lookup_fault_code"]:
        fn = re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_") or "tool"
        if fn[0].isdigit():
            fn = "t_" + fn
        out.append(
            f'@tool\ndef {fn}(query: str) -> dict:\n'
            f'    """{name.replace("_", " ").capitalize()}. TODO: connect to the real system."""\n'
            f'    return {{"query": query, "result": "stub", "source": None}}\n'
        )
    return "\n\n".join(out)


def _readme(idea: IdeaIn, c: Classification, data: DataAssessment, bp: Blueprint) -> str:
    lines = [
        f"# {idea.title}",
        "",
        f"**Kind:** {KIND_LABELS[c.kind]} · **Domains:** {', '.join(t.value for t in c.domain_tags)}",
        "",
        "## Problem",
        idea.problem,
        "",
        "## Outcome",
        idea.outcome,
        "",
        "## Blueprint",
        bp.summary,
        "",
        "| Component | Layer | Purpose |",
        "|---|---|---|",
        *[f"| {x.name} | {x.layer} | {x.purpose} |" for x in bp.components],
        "",
        "## Milestones",
        *[f"{i + 1}. **{m.title}** ({m.est_days} d): {m.deliverable}" for i, m in enumerate(bp.milestones)],
        "",
        "## Success metrics",
        *[f"- {m}" for m in bp.eval_metrics],
        "",
        "## Risks",
        *[f"- {r}" for r in bp.risks],
    ]
    if data.applicable:
        lines += ["", f"## Data ({data.readiness})", data.notes, ""]
        lines += [f"- `{m.dataset_id}` {m.name}: {m.reason}" + (f" {m.link}" if m.link else "") for m in data.matches]
        if data.gaps:
            lines += ["", "Fields that need permission or are not public: " + ", ".join(f"`{g}`" for g in data.gaps)]
    lines += ["", "## Getting started", "```bash", "python -m venv .venv && .venv/bin/pip install -e '.[dev]'",
              ".venv/bin/python -m pytest -q", "```", "",
              "_Scaffolded by the Agentic Twin orchestrator. Edit freely._", ""]
    return "\n".join(lines)


def unique_dir(base: Path, slug: str) -> tuple[Path, str]:
    candidate, n = slug, 2
    while (base / candidate).exists():
        candidate, n = f"{slug}-{n}", n + 1
    return base / candidate, candidate


def write_project(out_dir: Path, slug: str, idea: IdeaIn, c: Classification,
                  data: DataAssessment, bp: Blueprint) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    root, slug = unique_dir(out_dir, slug)
    pkg = re.sub(r"[^a-z0-9_]", "_", slug.replace("-", "_")) or "project"
    if pkg[0].isdigit():
        pkg = "p_" + pkg
    kind = c.kind
    deps = KIND_DEPENDENCIES[kind]
    values = {
        "slug": slug,
        "pkg": pkg,
        "title": idea.title.replace('"', "'"),
        "dependencies": ", ".join(f'"{d}"' for d in deps),
        "tool_stubs": _tool_stubs(bp.agent_tools if kind in (ProjectKind.llm_agent, ProjectKind.hybrid) else []),
        "dataset_lines": "\n".join(f"- {m.dataset_id}: {m.name} {m.link}".rstrip() for m in data.matches)
        or "- none matched; see the research inventory",
    }

    files = {**COMMON, **KIND_FILES[kind]}
    written = []
    for rel_tpl, body_tpl in files.items():
        rel = Template(rel_tpl).substitute(values)
        path = (root / rel).resolve()
        if root.resolve() not in path.parents:
            raise ValueError(f"refusing to write outside the project: {rel}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(Template(body_tpl).substitute(values), encoding="utf-8")
        written.append(rel)

    (root / "README.md").write_text(_readme(idea, c, data, bp), encoding="utf-8")
    (root / "blueprint.json").write_text(json.dumps({
        "idea": idea.model_dump(mode="json"),
        "classification": c.model_dump(mode="json"),
        "data": data.model_dump(mode="json"),
        "blueprint": bp.model_dump(mode="json"),
    }, indent=2) + "\n", encoding="utf-8")
    written += ["README.md", "blueprint.json"]
    return {"slug": slug, "path": str(root), "files": sorted(written)}
