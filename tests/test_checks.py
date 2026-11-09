"""Tests for the data checks: the real repo must pass, and broken inputs must be caught."""

import shutil
from pathlib import Path

import pytest

from cvtwin.checks import (
    DICTIONARY_CSV, INVENTORY_CSV, SOURCES_CSV,
    check_csv_structure, check_cross_references, check_dictionary,
    check_schema_text, check_sources, run_all,
)

ROOT = Path(__file__).resolve().parents[1]


def errors(results):
    return [r for r in results if not r.passed and r.severity == "error"]


def test_repository_has_no_error_level_failures():
    failed = errors(run_all(ROOT))
    assert not failed, "\n".join(f"{r.check} {r.target}: {r.detail} {r.failed_items}" for r in failed)


@pytest.fixture
def repo_copy(tmp_path):
    shutil.copytree(ROOT / "research", tmp_path / "research")
    return tmp_path


def _edit(path: Path, old: str, new: str):
    text = path.read_text(encoding="utf-8")
    assert old in text, f"fixture text not found: {old!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_duplicate_source_id_is_caught(repo_copy):
    _edit(repo_copy / SOURCES_CSV, "TM-02,", "TM-01,")
    assert any(r.check == "unique_key:id" for r in errors(check_csv_structure(repo_copy, SOURCES_CSV)))


def test_bad_url_is_caught(repo_copy):
    _edit(repo_copy / SOURCES_CSV, "https://www.tatamotors.com/?p=27012", "tatamotors dot com")
    assert any(r.check == "url_format" for r in errors(check_sources(repo_copy)))


def test_company_prefix_mismatch_is_caught(repo_copy):
    _edit(repo_copy / SOURCES_CSV, "TM-01,Tata Motors", "TM-01,Mahindra")
    assert any(r.check == "id_prefix_matches_company" for r in errors(check_sources(repo_copy)))


def test_invalid_availability_code_is_caught(repo_copy):
    _edit(repo_copy / DICTIONARY_CSV, "engine_id,Engine,Unique engine identifier (anonymised),-,C,",
          "engine_id,Engine,Unique engine identifier (anonymised),-,Z,")
    assert any(r.check == "availability_code_valid" for r in errors(check_dictionary(repo_copy)))


def test_unknown_dataset_reference_is_caught(repo_copy):
    _edit(repo_copy / "research/projects_and_roadmap.md", "(DS-01)", "(DS-99)")
    assert any("DS-99" in r.failed_items for r in errors(check_cross_references(repo_copy)))


def test_ragged_row_is_caught(repo_copy):
    with (repo_copy / INVENTORY_CSV).open("a", encoding="utf-8") as f:
        f.write("DS-99,only,three\n")
    assert any(r.check == "consistent_column_count" for r in errors(check_csv_structure(repo_copy, INVENTORY_CSV)))


def test_undefined_foreign_key_is_caught(repo_copy):
    _edit(repo_copy / "research/data/schema_postgres.sql",
          "REFERENCES core.company(company_id),\n    org_id", "REFERENCES core.nope(company_id),\n    org_id")
    assert any(r.check == "foreign_keys_resolve" for r in errors(check_schema_text(repo_copy)))
