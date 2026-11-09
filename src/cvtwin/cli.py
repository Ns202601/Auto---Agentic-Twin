"""Command-line entry point.

    python -m cvtwin compile   # byte-compile all Python code (syntax check)
    python -m cvtwin check     # validate research data -> artifacts/data_check_report.*
    python -m cvtwin process   # build clean tables -> artifacts/processed/*.csv
    python -m cvtwin artifact  # build the Data Lab page -> artifacts/data_lab.html
    python -m cvtwin all       # compile + check + process + artifact

Exit code is 1 when any error-level check fails, so it can gate CI.
"""

from __future__ import annotations

import argparse
import compileall
import sys
from pathlib import Path

from cvtwin.checks import run_all
from cvtwin.report import summarise, write_reports


def repo_root() -> Path:
    # src/cvtwin/cli.py -> repo root is two levels above src/
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "research").is_dir():
            return parent
    return Path.cwd()


def cmd_compile(root: Path) -> int:
    targets = [p for p in (root / "src", root / "tests", root / "scripts") if p.exists()]
    ok = all(compileall.compile_dir(str(t), quiet=1, force=True) for t in targets)
    print(f"compile: {'OK' if ok else 'FAILED'} ({', '.join(t.name for t in targets)})")
    return 0 if ok else 1


def cmd_check(root: Path, args: argparse.Namespace) -> int:
    results = run_all(root)
    extra = {}
    if args.pg_host:
        from cvtwin.pgcheck import check_schema_live
        results.append(check_schema_live(root, args.pg_host, args.pg_port, args.pg_user, args.pg_db))
        extra["postgres"] = f"{args.pg_host}:{args.pg_port}/{args.pg_db}"
    out = root / "artifacts"
    json_path, md_path = write_reports(results, out, extra)
    s = summarise(results)
    print(f"check: {s['checks_run']} checks, {s['passed']} passed, "
          f"{s['errors']} errors, {s['warnings']} warnings")
    for r in results:
        if not r.passed and r.severity in ("error", "warn"):
            print(f"  [{r.severity.upper()}] {r.check} ({r.target}): {r.detail}")
    print(f"  reports: {md_path.relative_to(root)}, {json_path.relative_to(root)}")
    return 1 if s["errors"] else 0


def cmd_process(root: Path) -> int:
    from cvtwin.process import run_processing
    paths = run_processing(root, root / "artifacts" / "processed")
    for name, p in paths.items():
        print(f"process: {name} -> {p.relative_to(root)}")
    return 0


def cmd_artifact(root: Path) -> int:
    from cvtwin.site import build_data_lab
    path = build_data_lab(root, root / "artifacts" / "data_lab.html")
    print(f"artifact: {path.relative_to(root)} ({path.stat().st_size // 1024} KB)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cvtwin", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["compile", "check", "process", "artifact", "all"])
    parser.add_argument("--root", type=Path, default=None, help="repository root (auto-detected)")
    parser.add_argument("--pg-host", help="optional: run a live schema test on this PostgreSQL host/socket dir")
    parser.add_argument("--pg-port", type=int, default=5432)
    parser.add_argument("--pg-user", default="postgres")
    parser.add_argument("--pg-db", default="postgres")
    args = parser.parse_args(argv)
    root = (args.root or repo_root()).resolve()

    if args.command == "compile":
        return cmd_compile(root)
    if args.command == "check":
        return cmd_check(root, args)
    if args.command == "process":
        return cmd_process(root)
    if args.command == "artifact":
        return cmd_artifact(root)
    rc = cmd_compile(root)
    rc |= cmd_check(root, args)
    rc |= cmd_process(root)
    rc |= cmd_artifact(root)
    return rc


if __name__ == "__main__":
    sys.exit(main())
