from pathlib import Path

import pandas as pd

from cvtwin.process import _parse_date, clean_inventory, clean_sources, run_processing

ROOT = Path(__file__).resolve().parents[1]


def test_parse_date_precision():
    assert _parse_date("2026-06-06") == (pd.Timestamp("2026-06-06"), "day")
    assert _parse_date("2026-04") == (pd.Timestamp("2026-04-01"), "month")
    assert _parse_date("2026 (exact n/d)") == (pd.Timestamp("2026-01-01"), "year")
    assert _parse_date("2022-23 (n/d exact)") == (pd.Timestamp("2022-01-01"), "year")
    assert _parse_date("n/d") == (None, "none")


def test_clean_sources_columns():
    df = clean_sources(ROOT)
    assert {"date_start", "date_precision", "domain", "verification_class"} <= set(df.columns)
    assert df["id"].is_unique
    assert (df.loc[~df["is_placeholder_link"], "domain"] != "").all()


def test_inventory_flags():
    df = clean_inventory(ROOT)
    # a dataset with a placeholder link can never be "ready to use"
    assert not df.loc[~df["has_verified_link"], "ready_to_use"].any()


def test_run_processing_writes_files(tmp_path):
    paths = run_processing(ROOT, tmp_path)
    for p in paths.values():
        assert p.exists() and p.stat().st_size > 0
