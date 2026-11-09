"""Data checks for the research repository.

Each check returns CheckResult objects. Severity:
  error - the data is broken and must be fixed
  warn  - suspicious or incomplete, review it
  info  - a measurement, never fails the run
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Expected structure of each CSV
# ---------------------------------------------------------------------------
SOURCES_CSV = "research/sources_directory.csv"
INVENTORY_CSV = "research/data/dataset_inventory.csv"
DICTIONARY_CSV = "research/data/data_dictionary.csv"
SCHEMA_SQL = "research/data/schema_postgres.sql"

EXPECTED_COLUMNS = {
    SOURCES_CSV: [
        "id", "company", "document_or_page_title", "source_url", "publication_date",
        "information_available", "relevant_data_fields", "potential_project_application",
        "downloadable_or_webpage", "verification_status",
    ],
    INVENTORY_CSV: [
        "dataset_id", "dataset_name", "source_org", "access_link", "format", "records",
        "columns", "key_features", "target_variable", "real_or_synthetic",
        "license_and_restrictions", "recommended_project", "verification_status",
    ],
    DICTIONARY_CSV: [
        "field", "group", "plain_english_meaning", "unit_typical", "availability_code",
        "availability_meaning", "public_evidence", "best_open_proxy", "notes",
    ],
}
KEY_COLUMN = {SOURCES_CSV: "id", INVENTORY_CSV: "dataset_id", DICTIONARY_CSV: "field"}

# Source id prefix -> company name used in the sources directory
PREFIX_COMPANY = {
    "TM": "Tata Motors",
    "MH": "Mahindra",
    "VE": "VECV (Eicher)",
    "AL": "Ashok Leyland",
    "CU": "Cummins",
}
AVAILABILITY_CODES = {"A", "B", "C", "D", "E"}
PLACEHOLDER_LINK = re.compile(r"^NOT (RETRIEVED|VERIFIED)\b")
URL_RE = re.compile(r"^https?://[^\s]+$")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
DS_ID_RE = re.compile(r"\bDS-\d{2}\b")
# Accepted date shapes: 2026, 2026-06, 2026-06-06, 2025-08/09, 2022-23, 2022–23,
# optionally followed by a note in brackets, or 'n/d'
DATE_RE = re.compile(
    r"^(n/d|\d{4}(-\d{2}(-\d{2}|/\d{2})?)?([–-]\d{2,4})?)(\s*\(.*\))?$"
)


@dataclass
class CheckResult:
    check: str
    target: str
    severity: str  # error | warn | info
    passed: bool
    detail: str = ""
    failed_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _short(items: list[str], limit: int = 10) -> list[str]:
    return items[:limit] + ([f"... and {len(items) - limit} more"] if len(items) > limit else [])


# ---------------------------------------------------------------------------
# Generic CSV checks
# ---------------------------------------------------------------------------
def check_csv_structure(root: Path, rel: str) -> list[CheckResult]:
    path = root / rel
    if not path.exists():
        return [CheckResult("file_exists", rel, "error", False, "file is missing")]

    header, rows = _read_csv(path)
    out = [CheckResult("file_exists", rel, "error", True, f"{len(rows)} data rows")]

    expected = EXPECTED_COLUMNS[rel]
    missing = [c for c in expected if c not in header]
    extra = [c for c in header if c not in expected]
    out.append(CheckResult(
        "expected_columns", rel, "error", not missing,
        f"missing={missing} extra={extra}" if (missing or extra) else "all expected columns present",
        missing,
    ))

    ragged = [f"row {i + 2}: {len(r)} cols" for i, r in enumerate(rows) if len(r) != len(header)]
    out.append(CheckResult(
        "consistent_column_count", rel, "error", not ragged,
        f"{len(ragged)} rows with wrong column count" if ragged else f"all rows have {len(header)} columns",
        _short(ragged),
    ))

    blank_rows = [f"row {i + 2}" for i, r in enumerate(rows) if not any(c.strip() for c in r)]
    out.append(CheckResult("no_blank_rows", rel, "warn", not blank_rows,
                           f"{len(blank_rows)} blank rows", _short(blank_rows)))

    key = KEY_COLUMN[rel]
    if key in header:
        idx = header.index(key)
        keys = [r[idx].strip() for r in rows if len(r) > idx]
        empty = [f"row {i + 2}" for i, k in enumerate(keys) if not k]
        seen, dups = set(), []
        for k in keys:
            if k and k in seen:
                dups.append(k)
            seen.add(k)
        out.append(CheckResult(f"unique_key:{key}", rel, "error", not dups and not empty,
                               f"{len(dups)} duplicate, {len(empty)} empty keys",
                               _short(dups + empty)))

    # whitespace hygiene: leading/trailing spaces in any cell
    padded = [
        f"row {i + 2} col '{header[j]}'"
        for i, r in enumerate(rows)
        for j, c in enumerate(r[: len(header)])
        if c != c.strip()
    ]
    out.append(CheckResult("no_padded_cells", rel, "warn", not padded,
                           f"{len(padded)} cells with leading/trailing spaces", _short(padded)))
    return out


# ---------------------------------------------------------------------------
# File-specific checks
# ---------------------------------------------------------------------------
def check_sources(root: Path) -> list[CheckResult]:
    rel = SOURCES_CSV
    path = root / rel
    if not path.exists():
        return []
    header, rows = _read_csv(path)
    col = {name: i for i, name in enumerate(header)}
    out: list[CheckResult] = []

    bad_url, placeholder = [], []
    for r in rows:
        url = r[col["source_url"]].strip()
        if PLACEHOLDER_LINK.match(url):
            placeholder.append(r[col["id"]])
        elif not URL_RE.match(url):
            bad_url.append(f"{r[col['id']]}: {url!r}")
    out.append(CheckResult("url_format", rel, "error", not bad_url,
                           f"{len(bad_url)} malformed URLs", _short(bad_url)))
    out.append(CheckResult("url_not_retrieved", rel, "warn", not placeholder,
                           f"{len(placeholder)} sources without a retrieved link", placeholder))

    urls = [r[col["source_url"]].strip() for r in rows]
    dup_urls = sorted({u for u in urls if urls.count(u) > 1 and URL_RE.match(u)})
    out.append(CheckResult("duplicate_urls", rel, "warn", not dup_urls,
                           f"{len(dup_urls)} URLs listed more than once", _short(dup_urls)))

    bad_dates = [f"{r[col['id']]}: {r[col['publication_date']]!r}"
                 for r in rows if not DATE_RE.match(r[col["publication_date"]].strip())]
    out.append(CheckResult("date_format", rel, "warn", not bad_dates,
                           f"{len(bad_dates)} dates in an unrecognised shape", _short(bad_dates)))

    undated = [r[col["id"]] for r in rows if r[col["publication_date"]].strip().startswith("n/d")]
    out.append(CheckResult("dated_sources", rel, "info", True,
                           f"{len(rows) - len(undated)} of {len(rows)} sources have a date; "
                           f"{len(undated)} are n/d", undated))

    mismatch = []
    for r in rows:
        sid, company = r[col["id"]], r[col["company"]]
        prefix = sid.split("-")[0]
        if prefix in PREFIX_COMPANY and PREFIX_COMPANY[prefix] != company:
            mismatch.append(f"{sid}: company={company!r}, expected {PREFIX_COMPANY[prefix]!r}")
    out.append(CheckResult("id_prefix_matches_company", rel, "error", not mismatch,
                           f"{len(mismatch)} mismatches", mismatch))

    no_status = [r[col["id"]] for r in rows if not r[col["verification_status"]].strip()]
    out.append(CheckResult("verification_status_present", rel, "error", not no_status,
                           f"{len(no_status)} rows without verification status", no_status))

    counts: dict[str, int] = {}
    for r in rows:
        counts[r[col["company"]]] = counts.get(r[col["company"]], 0) + 1
    out.append(CheckResult("sources_per_company", rel, "info", True,
                           ", ".join(f"{k}: {v}" for k, v in counts.items())))
    return out


def check_inventory(root: Path) -> list[CheckResult]:
    rel = INVENTORY_CSV
    path = root / rel
    if not path.exists():
        return []
    header, rows = _read_csv(path)
    col = {name: i for i, name in enumerate(header)}
    out: list[CheckResult] = []

    bad_ids = [r[col["dataset_id"]] for r in rows if not re.fullmatch(r"DS-\d{2}", r[col["dataset_id"]])]
    out.append(CheckResult("dataset_id_format", rel, "error", not bad_ids,
                           f"{len(bad_ids)} ids not shaped DS-NN", bad_ids))

    bad_links = []
    unverified = []
    for r in rows:
        link = r[col["access_link"]].strip()
        if PLACEHOLDER_LINK.match(link):
            unverified.append(r[col["dataset_id"]])
        elif not URL_RE.match(link):
            bad_links.append(f"{r[col['dataset_id']]}: {link!r}")
    out.append(CheckResult("access_link_format", rel, "error", not bad_links,
                           f"{len(bad_links)} malformed links", bad_links))
    out.append(CheckResult("datasets_without_link", rel, "warn", not unverified,
                           f"{len(unverified)} datasets have no verified link", unverified))

    unknown_licence = [r[col["dataset_id"]] for r in rows
                       if re.search(r"not verified|unclear|verify", r[col["license_and_restrictions"]], re.I)]
    out.append(CheckResult("licence_confirmed", rel, "warn", not unknown_licence,
                           f"{len(unknown_licence)} datasets need licence confirmation", unknown_licence))

    unknown_size = [r[col["dataset_id"]] for r in rows
                    if re.search(r"not (confirmed|verified)", r[col["records"]], re.I)]
    out.append(CheckResult("record_count_known", rel, "warn", not unknown_size,
                           f"{len(unknown_size)} datasets with unconfirmed record counts", unknown_size))
    return out


def check_dictionary(root: Path) -> list[CheckResult]:
    rel = DICTIONARY_CSV
    path = root / rel
    if not path.exists():
        return []
    header, rows = _read_csv(path)
    col = {name: i for i, name in enumerate(header)}
    out: list[CheckResult] = []

    bad_codes = [f"{r[col['field']]}: {r[col['availability_code']]!r}" for r in rows
                 if r[col["availability_code"]].strip() not in AVAILABILITY_CODES]
    out.append(CheckResult("availability_code_valid", rel, "error", not bad_codes,
                           f"{len(bad_codes)} invalid codes", bad_codes))

    inconsistent = [r[col["field"]] for r in rows
                    if r[col["availability_code"]].strip() in AVAILABILITY_CODES
                    and not r[col["availability_meaning"]].startswith(r[col["availability_code"]].strip() + " -")]
    out.append(CheckResult("code_matches_meaning", rel, "error", not inconsistent,
                           f"{len(inconsistent)} rows where code and meaning disagree", inconsistent))

    bad_names = [r[col["field"]] for r in rows if not re.fullmatch(r"[a-z][a-z0-9_]*", r[col["field"]])]
    out.append(CheckResult("field_name_snake_case", rel, "warn", not bad_names,
                           f"{len(bad_names)} field names not snake_case", bad_names))

    # The schema's core.field_availability.field_group only allows these values,
    # so dictionary groups must map to one of them before loading.
    schema_groups = {"engine", "after_treatment", "vehicle", "maintenance", "fleet", "market"}
    def to_schema_group(g: str) -> str:
        return g.strip().lower().replace("after-treatment", "after_treatment").replace(" (open)", "")
    unloadable = sorted({r[col["group"]] for r in rows if to_schema_group(r[col["group"]]) not in schema_groups})
    out.append(CheckResult("group_loadable_into_schema", rel, "warn", not unloadable,
                           f"{len(unloadable)} group values do not match the schema's field_group list "
                           f"{sorted(schema_groups)}", unloadable))

    dist: dict[str, int] = {}
    for r in rows:
        dist[r[col["availability_code"]]] = dist.get(r[col["availability_code"]], 0) + 1
    out.append(CheckResult("availability_distribution", rel, "info", True,
                           ", ".join(f"{k}: {dist[k]}" for k in sorted(dist))))
    return out


def check_cross_references(root: Path) -> list[CheckResult]:
    """Every DS-NN mentioned anywhere must exist in the dataset inventory."""
    inv = root / INVENTORY_CSV
    if not inv.exists():
        return []
    _, rows = _read_csv(inv)
    known = {r[0] for r in rows}

    out: list[CheckResult] = []
    targets = [DICTIONARY_CSV] + [str(p.relative_to(root)) for p in sorted((root / "research").rglob("*.md"))]
    for rel in targets:
        text = (root / rel).read_text(encoding="utf-8")
        refs = sorted(set(DS_ID_RE.findall(text)))
        unknown = [d for d in refs if d not in known]
        if refs:
            out.append(CheckResult("dataset_refs_resolve", rel, "error", not unknown,
                                   f"{len(refs)} DS refs, {len(unknown)} unknown", unknown))
    return out


def check_markdown(root: Path) -> list[CheckResult]:
    out: list[CheckResult] = []
    src = root / SOURCES_CSV
    directory_urls: set[str] = set()
    if src.exists():
        header, rows = _read_csv(src)
        i = header.index("source_url")
        directory_urls = {r[i].strip() for r in rows}

    for path in sorted((root / "research").rglob("*.md")):
        rel = str(path.relative_to(root))
        text = path.read_text(encoding="utf-8")
        links = MD_LINK_RE.findall(text)
        # A '[' followed by '](' without http: a broken or relative link
        broken = re.findall(r"\]\((?!https?://)([^)]*)\)", text)
        out.append(CheckResult("markdown_links_wellformed", rel, "error", not broken,
                               f"{len(links)} links; {len(broken)} non-http link targets", _short(broken)))
        if "companies" in rel and directory_urls:
            not_in_dir = sorted({u for _, u in links if u not in directory_urls})
            out.append(CheckResult("links_in_source_directory", rel, "info", True,
                                   f"{len(not_in_dir)} of {len(set(u for _, u in links))} unique links "
                                   "are not in sources_directory.csv", _short(not_in_dir, 5)))
    return out


def check_schema_text(root: Path) -> list[CheckResult]:
    """Static checks on the SQL file (no database needed)."""
    rel = SCHEMA_SQL
    path = root / rel
    if not path.exists():
        return [CheckResult("file_exists", rel, "error", False, "file is missing")]
    sql = path.read_text(encoding="utf-8")
    body = re.sub(r"--[^\n]*", "", sql)
    tables = re.findall(r"CREATE TABLE IF NOT EXISTS\s+([a-z_]+\.[a-z_]+)", body)
    views = re.findall(r"CREATE OR REPLACE VIEW\s+([a-z_]+\.[a-z_]+)", body)
    out = [CheckResult("schema_objects", rel, "info", True,
                       f"{len(tables)} tables, {len(views)} views")]
    dup = sorted({t for t in tables if tables.count(t) > 1})
    out.append(CheckResult("no_duplicate_tables", rel, "error", not dup, f"{len(dup)} duplicates", dup))
    balanced = body.count("(") == body.count(")")
    out.append(CheckResult("balanced_parentheses", rel, "error", balanced,
                           f"( = {body.count('(')}, ) = {body.count(')')}"))
    refs = set(re.findall(r"REFERENCES\s+([a-z_]+\.[a-z_]+)", body))
    missing = sorted(refs - set(tables))
    out.append(CheckResult("foreign_keys_resolve", rel, "error", not missing,
                           f"{len(refs)} referenced tables, {len(missing)} undefined", missing))
    return out


def run_all(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    for rel in EXPECTED_COLUMNS:
        results += check_csv_structure(root, rel)
    results += check_sources(root)
    results += check_inventory(root)
    results += check_dictionary(root)
    results += check_cross_references(root)
    results += check_markdown(root)
    results += check_schema_text(root)
    return results
