"""Build the Data Lab HTML artifact from the latest check report and processed tables."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cvtwin import __version__
from cvtwin.checks import DICTIONARY_CSV, INVENTORY_CSV, SOURCES_CSV

BRYTHON_VERSION = "3.14.3"
TEMPLATE = Path(__file__).with_name("templates") / "data_lab.html"

# Runs once when Python starts in the browser. Helpers go on builtins so every later run sees them.
PRELUDE = r'''
import sys, csv, io, builtins
from browser import window

class _Out:
    def __init__(self, err):
        self.err = err
    def write(self, s):
        window.labErr(self.err)
        window.labWrite(str(s))
        window.labErr(False)
    def flush(self):
        pass

sys.stdout = _Out(False)
sys.stderr = _Out(True)

FILES = str(window.labFiles()).split("\n")

def read_text(name):
    """Return the text of a preloaded repository file."""
    text = window.labFile(name)
    if text is None:
        raise FileNotFoundError(f"{name!r} is not preloaded. Available: {', '.join(FILES)}")
    return str(text)

def read_csv(name):
    """Return a preloaded CSV file as a list of dicts (one per row)."""
    return list(csv.DictReader(io.StringIO(read_text(name))))

def show(rows, cols=None, limit=20, width=40):
    """Print rows as a plain-text table."""
    rows = list(rows)
    if not rows:
        print("(no rows)")
        return
    cols = cols or list(rows[0].keys())
    cut = lambda v: (str(v) if len(str(v)) <= width else str(v)[: width - 1] + "…")
    body = [[cut(r.get(c, "")) for c in cols] for r in rows[:limit]]
    w = [max(len(c), *(len(b[i]) for b in body)) for i, c in enumerate(cols)]
    print("  ".join(c.ljust(w[i]) for i, c in enumerate(cols)))
    print("  ".join("-" * w[i] for i in range(len(cols))))
    for b in body:
        print("  ".join(b[i].ljust(w[i]) for i in range(len(cols))))
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more rows")

for _f in (read_text, read_csv, show):
    setattr(builtins, _f.__name__, _f)
builtins.FILES = FILES
'''

EXAMPLES = [
    ("Sources by company", '''from collections import Counter

rows = read_csv("sources_directory.csv")
print(len(rows), "sources\\n")
for company, n in Counter(r["company"] for r in rows).most_common():
    print(f"{company:<38} {n:>3}  " + "#" * n)
'''),
    ("Undated sources to fix", '''rows = read_csv("sources_directory.csv")
undated = [r for r in rows if r["publication_date"].startswith("n/d")]
print(len(undated), "of", len(rows), "sources have no visible date\\n")
show(undated, ["id", "company", "document_or_page_title"])
'''),
    ("Dataset readiness", '''rows = read_csv("dataset_inventory_clean.csv")
ready = [r for r in rows if r["ready_to_use"] == "True"]
print(f"{len(ready)} of {len(rows)} datasets are ready to use\\n")
show(rows, ["dataset_id", "dataset_name", "has_verified_link", "licence_needs_check", "ready_to_use"])
'''),
    ("Fields that need permission", '''rows = read_csv("data_dictionary.csv")
closed = [r for r in rows if r["availability_code"] in ("D", "E")]
print(f"{len(closed)} of {len(rows)} fields are not public (D) or need permission (E)\\n")
show(closed, ["field", "group", "availability_code", "best_open_proxy"], limit=40, width=34)
'''),
    ("Source years", '''from collections import Counter

rows = read_csv("sources_clean.csv")
years = Counter(r["year"] or "no date" for r in rows)
for year in sorted(years, key=str):
    print(f"{year:>8}  {years[year]:>3}  " + "#" * years[year])
'''),
    ("Scratch pad", '''# Files you can read: print(FILES)
# read_csv(name) -> list of dicts, read_text(name) -> str, show(rows, cols)
import statistics

rows = read_csv("company_summary.csv")
pct = [float(r["dated_pct"]) for r in rows]
print("Median share of dated sources:", statistics.median(pct), "%")
'''),
]


def build_data_lab(root: Path, out_path: Path) -> Path:
    art = root / "artifacts"
    proc = art / "processed"
    report_path = art / "data_check_report.json"
    if not report_path.exists() or not (proc / "company_summary.csv").exists():
        raise FileNotFoundError("Run `python -m cvtwin check` and `python -m cvtwin process` first.")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    read = lambda p: pd.read_csv(p, dtype=str, keep_default_na=False)
    company = read(proc / "company_summary.csv")
    avail = read(proc / "availability_matrix.csv")
    datasets = read(proc / "dataset_inventory_clean.csv")

    files = {
        "sources_directory.csv": (root / SOURCES_CSV).read_text(encoding="utf-8"),
        "dataset_inventory.csv": (root / INVENTORY_CSV).read_text(encoding="utf-8"),
        "data_dictionary.csv": (root / DICTIONARY_CSV).read_text(encoding="utf-8"),
        "sources_clean.csv": (proc / "sources_clean.csv").read_text(encoding="utf-8"),
        "company_summary.csv": (proc / "company_summary.csv").read_text(encoding="utf-8"),
        "dataset_inventory_clean.csv": (proc / "dataset_inventory_clean.csv").read_text(encoding="utf-8"),
    }
    data = {
        "version": __version__,
        "report": report,
        "counts": {
            "sources": len(read(root / SOURCES_CSV)),
            "datasets": len(datasets),
            "fields": len(read(root / DICTIONARY_CSV)),
        },
        "company_summary": company.to_dict(orient="records"),
        "availability": avail.to_dict(orient="records"),
        "datasets": datasets[["dataset_id", "dataset_name", "source_org", "access_link", "is_synthetic",
                              "has_verified_link", "ready_to_use"]].to_dict(orient="records"),
        "files": files,
        "prelude": PRELUDE,
        "examples": [{"title": t, "code": c} for t, c in EXAMPLES],
    }
    # Escape '</' so the JSON cannot close its <script> tag early.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__LAB_DATA__", payload).replace("__BRYTHON_VERSION__", BRYTHON_VERSION)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
