"""Write check results to JSON and Markdown artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from cvtwin.checks import CheckResult


def summarise(results: list[CheckResult]) -> dict:
    failed = [r for r in results if not r.passed]
    return {
        "checks_run": len(results),
        "passed": sum(r.passed for r in results),
        "errors": sum(1 for r in failed if r.severity == "error"),
        "warnings": sum(1 for r in failed if r.severity == "warn"),
    }


def write_reports(results: list[CheckResult], out_dir: Path, extra: dict | None = None) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = summarise(results)

    json_path = out_dir / "data_check_report.json"
    json_path.write_text(json.dumps(
        {"generated_at": generated, "summary": summary, **(extra or {}),
         "results": [r.to_dict() for r in results]},
        indent=2, ensure_ascii=False,
    ) + "\n", encoding="utf-8")

    def icon(r: CheckResult) -> str:
        if r.passed:
            return "PASS"
        return "FAIL" if r.severity == "error" else ("WARN" if r.severity == "warn" else "INFO")

    lines = [
        "# Data check report",
        "",
        f"Generated: {generated}",
        "",
        f"**{summary['checks_run']} checks · {summary['passed']} passed · "
        f"{summary['errors']} errors · {summary['warnings']} warnings**",
        "",
    ]
    if extra:
        for k, v in extra.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    order = {"error": 0, "warn": 1, "info": 2}
    problems = sorted([r for r in results if not r.passed], key=lambda r: order[r.severity])
    if problems:
        lines += ["## Needs attention", "", "| Result | Check | File | Detail | Items |", "|---|---|---|---|---|"]
        for r in problems:
            items = "; ".join(r.failed_items[:6]).replace("|", "\\|")
            lines.append(f"| {icon(r)} | {r.check} | `{r.target}` | {r.detail} | {items} |")
        lines.append("")

    lines += ["## All checks", "", "| Result | Severity | Check | File | Detail |", "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {icon(r)} | {r.severity} | {r.check} | `{r.target}` | {r.detail.replace('|', '/')} |")
    md_path = out_dir / "data_check_report.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
