"""Command line.

    python -m twinorch serve [--port 8000]          # API + UI
    python -m twinorch run --title ... --problem ... --outcome ... [--approve]
"""

from __future__ import annotations

import argparse
import json


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="twinorch")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run the API and UI")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)

    r = sub.add_parser("run", help="run one idea from the terminal")
    r.add_argument("--title", required=True)
    r.add_argument("--problem", required=True)
    r.add_argument("--outcome", required=True)
    r.add_argument("--data-notes", default="")
    r.add_argument("--kind", choices=["llm_agent", "ml_model", "data_pipeline", "hybrid"])
    r.add_argument("--approve", action="store_true", help="approve the first blueprint automatically")
    args = p.parse_args(argv)

    if args.cmd == "serve":
        import uvicorn
        from twinorch.api.app import create_app
        uvicorn.run(create_app(), host=args.host, port=args.port)
        return 0

    from twinorch.domain.models import IdeaIn, ReviewDecision
    from twinorch.service import OrchestratorService

    svc = OrchestratorService()
    try:
        idea = IdeaIn(title=args.title, problem=args.problem, outcome=args.outcome,
                      data_notes=args.data_notes, kind_hint=args.kind)
        run = svc.submit_idea(idea, wait=True)
        for e in run["events"]:
            print(f"[{e['node']:>11}] {e['message']}")
        if run["status"] == "awaiting_review":
            print(json.dumps(run["state"]["blueprint"], indent=2))
            if args.approve:
                run = svc.review(run["id"], ReviewDecision(action="approve"), wait=True)
                print(f"\nStatus: {run['status']}  project: {run['state'].get('project', {}).get('path')}")
            else:
                print(f"\nRun {run['id']} is waiting for review. Approve it in the UI or rerun with --approve.")
        return 0 if run["status"] in ("awaiting_review", "completed") else 1
    finally:
        svc.close()
