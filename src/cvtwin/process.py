"""Process the research CSVs into clean, analysis-ready tables (pandas)."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from cvtwin.checks import DICTIONARY_CSV, INVENTORY_CSV, SOURCES_CSV

_DATE_PARTS = re.compile(r"^(?P<y>\d{4})(?:-(?P<m>\d{2}))?(?:-(?P<d>\d{2}))?")


def _parse_date(text: str) -> tuple[pd.Timestamp | None, str]:
    """Return (date, precision). Precision: day | month | year | none.

    Partial dates map to the first day of the period, so '2026-06' -> 2026-06-01.
    """
    if not isinstance(text, str):
        return None, "none"
    m = _DATE_PARTS.match(text.strip())
    if not m:
        return None, "none"
    y, mo, d = m.group("y"), m.group("m"), m.group("d")
    # '2025-08/09' gives month 08; '2022-23' gives a two-digit "month" 23 -> treat as year only
    if mo and not 1 <= int(mo) <= 12:
        mo, d = None, None
    try:
        ts = pd.Timestamp(year=int(y), month=int(mo or 1), day=int(d or 1))
    except ValueError:
        return None, "none"
    return ts, "day" if d else "month" if mo else "year"


def _verification_class(status: str) -> str:
    s = (status or "").lower()
    if s.startswith("primary"):
        return "primary"
    if "vendor" in s or "sponsored" in s:
        return "vendor_or_sponsored"
    if "confirmed" in s or "listing" in s:
        return "listing_confirmed"
    if "secondary" in s:
        return "secondary"
    if "company" in s:
        return "company_material"
    return "other"


def clean_sources(root: Path) -> pd.DataFrame:
    df = pd.read_csv(root / SOURCES_CSV, dtype=str, keep_default_na=False)
    df = df.apply(lambda s: s.str.strip())
    parsed = df["publication_date"].map(_parse_date)
    df["date_start"] = pd.to_datetime([p[0] for p in parsed])
    df["date_precision"] = [p[1] for p in parsed]
    df["year"] = df["date_start"].dt.year.astype("Int64")
    df["is_placeholder_link"] = df["source_url"].str.match(r"^NOT (RETRIEVED|VERIFIED)")
    df["domain"] = np.where(
        df["is_placeholder_link"], "",
        df["source_url"].str.extract(r"^https?://(?:www\.)?([^/]+)", expand=False).fillna(""),
    )
    df["is_pdf"] = df["source_url"].str.lower().str.contains(r"\.pdf(?:$|\?)", regex=True)
    df["verification_class"] = df["verification_status"].map(_verification_class)
    return df


def company_summary(sources: pd.DataFrame) -> pd.DataFrame:
    g = sources.groupby("company", sort=False)
    summary = pd.DataFrame({
        "sources": g.size(),
        "dated_sources": g["date_start"].count(),
        "pdf_documents": g["is_pdf"].sum(),
        "earliest_year": g["year"].min(),
        "latest_year": g["year"].max(),
        "distinct_domains": g["domain"].nunique(),
    })
    summary["dated_pct"] = (100 * summary["dated_sources"] / summary["sources"]).round(1)
    by_class = pd.crosstab(sources["company"], sources["verification_class"])
    return summary.join(by_class).reset_index()


def clean_inventory(root: Path) -> pd.DataFrame:
    df = pd.read_csv(root / INVENTORY_CSV, dtype=str, keep_default_na=False)
    df = df.apply(lambda s: s.str.strip())
    df["has_verified_link"] = df["access_link"].str.match(r"^https?://")
    df["is_synthetic"] = df["real_or_synthetic"].str.lower().map(
        lambda s: True if s.startswith(("synthetic", "simulated")) else (False if s.startswith("real") else pd.NA)
    )
    df["licence_needs_check"] = df["license_and_restrictions"].str.contains(
        r"not verified|unclear|verify", case=False, regex=True)
    df["ready_to_use"] = df["has_verified_link"] & ~df["licence_needs_check"]
    return df


def availability_matrix(root: Path) -> pd.DataFrame:
    df = pd.read_csv(root / DICTIONARY_CSV, dtype=str, keep_default_na=False)
    m = pd.crosstab(df["group"], df["availability_code"], margins=True, margins_name="total")
    return m.reset_index()


def profile_csv(path: Path) -> pd.DataFrame:
    """Column-level profile: non-empty share, distinct values, longest value."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows = []
    for c in df.columns:
        s = df[c].str.strip()
        non_empty = s.ne("") & ~s.str.lower().isin(["n/d", "-", "none", "not verified", "not confirmed"])
        rows.append({
            "file": path.name,
            "column": c,
            "rows": len(s),
            "filled_pct": round(100 * non_empty.mean(), 1) if len(s) else 0.0,
            "distinct": s.nunique(),
            "max_len": int(s.str.len().max()) if len(s) else 0,
        })
    return pd.DataFrame(rows)


def run_processing(root: Path, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    sources = clean_sources(root)
    outputs = {
        "sources_clean": sources.assign(date_start=sources["date_start"].dt.strftime("%Y-%m-%d")),
        "company_summary": company_summary(sources),
        "dataset_inventory_clean": clean_inventory(root),
        "availability_matrix": availability_matrix(root),
        "column_profile": pd.concat(
            [profile_csv(root / p) for p in (SOURCES_CSV, INVENTORY_CSV, DICTIONARY_CSV)],
            ignore_index=True,
        ),
    }
    paths = {}
    for name, frame in outputs.items():
        p = out_dir / f"{name}.csv"
        frame.to_csv(p, index=False)
        paths[name] = p
    return paths
