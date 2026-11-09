# Auto — Agentic Twin

Research and data tooling for commercial-vehicle AI/ML projects (Tata Motors, Mahindra, VECV, Ashok Leyland, Cummins).

| Folder | What it holds |
|---|---|
| `research/` | Company reports, source directory, dataset inventory, data dictionary, PostgreSQL schema |
| `src/cvtwin/` | Python package that checks and processes the research data |
| `tests/` | Unit tests (pytest) |
| `artifacts/` | Generated outputs: check reports, clean tables, the Data Lab page |
| `scripts/setup_env.sh` | Creates `.venv` and installs everything |

## Quick start

```bash
make setup     # create .venv (Python 3.10+), install pandas, numpy, pytest
make all       # compile -> test -> check -> process -> artifact
```

Individual steps:

| Command | What it does | Output |
|---|---|---|
| `make compile` | Byte-compiles all Python code (catches syntax errors) | console |
| `make test` | Runs 12 unit tests | console |
| `make check` | Validates the research CSVs, Markdown links and SQL schema | `artifacts/data_check_report.md`, `.json` |
| `make process` | Builds clean, analysis-ready tables with pandas | `artifacts/processed/*.csv` |
| `make artifact` | Builds the Data Lab page (report + in-browser Python) | `artifacts/data_lab.html` |

`check` exits with code 1 if any error-level check fails, so it can gate CI.

### Optional: live PostgreSQL schema test
Loads `research/data/schema_postgres.sql` inside a transaction and rolls it back, so nothing is left behind:

```bash
.venv/bin/python -m cvtwin check --pg-host localhost --pg-port 5432 --pg-user postgres --pg-db postgres
```

## What the checks cover
- CSV structure: expected columns, consistent row width, unique keys, blank rows, padded cells
- Sources: URL format, duplicate URLs, date format, ID prefix matches company, verification status present
- Datasets: ID format, link present, licence and record count confirmed
- Data dictionary: valid A–E codes, code matches meaning, groups loadable into the schema
- Cross-references: every `DS-NN` mentioned in the docs exists in the inventory
- Markdown: link targets are well formed
- SQL schema: no duplicate tables, balanced parentheses, all foreign keys resolve

## Data Lab page
`artifacts/data_lab.html` shows the latest check results and includes a Python 3 console (Brython, runs in the browser) preloaded with the repository's CSV files. Helpers: `read_csv(name)`, `read_text(name)`, `show(rows, cols)`.
