"""Research adapter: assess an idea's data needs against the repository's research CSVs.

Deterministic on purpose: the same tags always give the same answer, so the
assessment can be trusted and tested. Reads research/data/dataset_inventory.csv
and research/data/data_dictionary.csv.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from twinorch.domain.catalog import KINDS_NEEDING_DATA, TAG_DATASETS, TAG_FIELD_GROUPS
from twinorch.domain.models import Classification, DataAssessment, DatasetMatch

INVENTORY = "research/data/dataset_inventory.csv"
DICTIONARY = "research/data/data_dictionary.csv"


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _is_ready(row: dict) -> bool:
    link_ok = row.get("access_link", "").startswith(("http://", "https://"))
    licence_open = not re.search(r"not verified|unclear|verify", row.get("license_and_restrictions", ""), re.I)
    return link_ok and licence_open


def assess_data(repo_root: Path, classification: Classification) -> DataAssessment:
    if classification.kind not in KINDS_NEEDING_DATA:
        return DataAssessment(applicable=False, readiness="not_applicable",
                              notes="Agent projects plan their data through tools; no dataset check needed.")

    inventory = {r["dataset_id"]: r for r in _rows(repo_root / INVENTORY)}
    dictionary = _rows(repo_root / DICTIONARY)

    matches: list[DatasetMatch] = []
    seen: set[str] = set()
    for tag in classification.domain_tags:
        for ds_id in TAG_DATASETS.get(tag, []):
            row = inventory.get(ds_id)
            if not row or ds_id in seen:
                continue
            seen.add(ds_id)
            ready = _is_ready(row)
            reason = (
                f"Matches '{tag.value}'. "
                + ("Verified link and licence." if ready else "Needs licence or link confirmation before use.")
                + f" {row.get('real_or_synthetic', '').split('(')[0].strip()}."
            )
            link = row["access_link"] if row.get("access_link", "").startswith("http") else ""
            matches.append(DatasetMatch(dataset_id=ds_id, name=row["dataset_name"], ready=ready,
                                        reason=reason, link=link))

    groups = {g for tag in classification.domain_tags for g in TAG_FIELD_GROUPS.get(tag, [])}
    gaps = sorted({
        r["field"] for r in dictionary
        if r.get("availability_code") in ("D", "E") and any(g.lower() in r.get("group", "").lower() for g in groups)
    })

    if any(m.ready for m in matches):
        readiness = "ready"
    elif matches:
        readiness = "partial"
    else:
        readiness = "blocked"

    notes = {
        "ready": "At least one open dataset can be used today.",
        "partial": "Candidate datasets exist but need licence or link confirmation.",
        "blocked": "No open dataset covers this domain; plan simulation or a data-sharing agreement.",
    }[readiness]
    if gaps:
        notes += f" {len(gaps)} needed fields are not public."
    return DataAssessment(readiness=readiness, matches=matches, gaps=gaps, notes=notes)
