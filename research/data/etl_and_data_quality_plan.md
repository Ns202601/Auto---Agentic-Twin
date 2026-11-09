# Dataset collection plan, ETL/ELT pipeline and data-quality checks

Companion to `research/data/schema_postgres.sql` (validated on PostgreSQL 16 in this session) and `research/data/dataset_inventory.csv`.

**Scope rule:** store only public facts, open datasets, and provenance. Never store private OEM telemetry, customer records or vehicle identifiers from non-public sources.

---

## 1. Data layers (what goes where)

| Layer | What it holds | Example in this project | Schema location |
|---|---|---|---|
| **Raw** | Files exactly as downloaded, with checksum and licence | APS Failure ZIP, VAHAN CSVs | `raw.source_file` + object storage |
| **Cleaned** | Typed, trimmed, deduplicated, missing values coded | APS rows with `na` → NULL | `staging.*` |
| **Structured** | Conformed tables for analysis | `core.engine_spec`, `core.vehicle_model` | `core.*` |
| **Time-series** | Monthly or per-cycle values | VAHAN registrations by month; C-MAPSS cycles | `core.registration_monthly`, `staging.turbofan_rul` |
| **Master** | Stable entities | `core.company`, `core.source_organisation` | `core.company`, `core.source_organisation` |
| **Transactional** | Event records | Company announcements, deliveries, launches (as events) | `core.fact_claim`, `core.fleet_metric_claim` |
| **Reference** | Lookup and standards | BS norm list, A–E availability codes, GVW classes | `core.field_availability`, `core.dataset_field` |

---

## 2. Pipeline architecture

```
 Sources (web press, open portals, UCI/NASA downloads)
        │  (manual + scripted fetch, respects robots.txt and licence)
        ▼
 Object storage  (raw/…  e.g. S3 / GCS bucket, versioned)      ← raw layer
        │  sha256 + size + licence logged to raw.source_file
        ▼
 Python / Pandas / NumPy  (parse, type, clean)                  ← staging
        │  quality gates (Section 4) write to audit.dq_check_result
        ▼
 PostgreSQL  (staging → core via SQL MERGE/INSERT … ON CONFLICT)
        │
        ▼
 Analytics / ML  (notebooks, feature tables, dashboards)
```

**Orchestration:** Apache Airflow DAG per source, scheduled weekly for monthly open data (VAHAN) and on demand for press/static sources.

---

## 3. Tooling and responsibilities

| Tool | Role |
|---|---|
| Python | Downloaders, parsers, orchestration glue |
| Pandas | Tabular cleaning, joins, type coercion, dedupe |
| NumPy | Vectorised numeric checks (ranges, NaN handling, z-scores) |
| SQL | Upserts, reconciliations, views |
| PostgreSQL | Warehouse, constraints, indexes |
| Airflow | Scheduling, retries, task dependencies, alerts on failed DQ |
| Cloud storage | Immutable raw files, versioned by sha256 |

### 3a. Ingestion pattern (ELT preferred for raw, ETL for cleaning)
1. **Extract:** download to a new run folder `raw/<source_key>/<yyyy-mm-dd>/`, compute SHA-256, write a row to `raw.source_file`. If the hash exists, skip (idempotent).
2. **Load raw:** keep the file as-is. Do not edit raw files.
3. **Transform (Pandas):** read with explicit dtypes; trim strings; convert `na` / empty to NULL; enforce units; split wide to long where needed.
4. **Validate:** run DQ checks (Section 4). Stop the load on `error` severity; log `warn`.
5. **Load core:** `INSERT … ON CONFLICT (natural key) DO UPDATE` (idempotent re-runs).
6. **Record:** update `audit.ingestion_run` with rows read and loaded.

---

## 4. Validation, cleaning, de-duplication, missing values and DQ checks

### 4a. Validation rules (examples)
| Dataset | Rule | Severity |
|---|---|---|
| APS Failure (DS-01) | `class` ∈ {pos, neg}; 171 attributes present; train 60,000 and test 16,000 rows (per UCI) | error |
| C-MAPSS (DS-03) | `cycle` ≥ 1; cycles increasing per unit; RUL ≥ 0 | error |
| VAHAN (DS-05–08) | `registrations` ≥ 0; month within coverage; state code in list | error |
| Claims (`fact_claim`) | `category` set; `source_url` begins with http(s) | error |
| Claims | percentage metrics between 0 and 100 | warn |

### 4b. Cleaning
- **Missing values:** APS uses `na`. Convert to NULL. Report the null rate per column. Drop a column if null rate > 80% (document why). Impute only for modelling, never in core tables.
- **Units:** hp ↔ kW (1 hp ≈ 0.7457 kW); t vs kg; km vs miles. Store the unit next to the value.
- **Text:** trim, collapse spaces, canonical maker names (e.g. "Tata Motors" vs "TATA MOTORS").
- **Conflicting values** (e.g. Prima E.55S range, e-ZEO range): store **both** with their source IDs; do not overwrite.

### 4c. De-duplication
- **Files:** SHA-256 on the raw bytes. Identical hashes are skipped.
- **Rows:** natural keys (see schema): `(subset, split, unit_id, cycle)` for turbofan; the unique index on registrations for VAHAN.
- **Claims:** the same claim can appear in several articles. Deduplicate on (company, topic, claim_text normalised, as_of_date) and keep every source link in `core.fact_claim`.
- **Cross-dataset duplicates:** DS-01 (UCI 421) and DS-02 (UCI 414, IDA 2016) contain the same challenge data. Load **one** copy and mark the other as an alias. Otherwise train/test leakage is possible.

### 4d. Quality checks (run after every load)
| Check | How | Pass condition |
|---|---|---|
| Row count | Compare to documented count (UCI, NASA, VAHAN) | Matches; else `warn` |
| Schema drift | Column names and types vs expected | Exact match; else `error` |
| Null rate | Per column, from profiling | Recorded; alarm if > threshold |
| Uniqueness | Natural key counts | 0 duplicates |
| Referential integrity | `fact_claim.source_id` ∈ `source_document` | 0 orphans |
| Value ranges | e.g. `registrations` ≥ 0; `cycle` ≥ 1 | 0 violations |
| Freshness | Latest `reg_month` vs today | Warn if > 60 days behind |
| Reconciliation | Sum of VAHAN by maker by month vs by category | Equal within tolerance |

Write each result to `audit.dq_check_result`.

---

## 5. Airflow DAG outline (no code run; design only)

```
dag: cv_research_ingest  (schedule: @weekly)
  ├─ fetch_vahan_resources  →  hash_and_register  →  parse_vahan  →  dq_vahan  →  load_registration_monthly
  ├─ fetch_uci_aps          →  hash_and_register  →  parse_aps    →  dq_aps    →  load_scania_aps
  ├─ fetch_nasa_cmapss      →  hash_and_register  →  parse_cmapss →  dq_cmapss →  load_turbofan_rul
  └─ refresh_claims (manual trigger; source list is curated)  →  dq_claims  →  load_fact_claim
  all  →  publish_report  (on success) / alert (on failure)
```

Retries: 3 per task, exponential backoff. Alerts: email or chat on any `error`.

---

## 6. Sketch of the core transform (Pandas, untested; for design review)

```python
import pandas as pd
import numpy as np

def load_aps(path: str, split: str) -> pd.DataFrame:
    # UCI APS file uses 'na' for missing values; read as strings first
    df = pd.read_csv(path, na_values=["na"], low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    df["split"] = split
    # class: pos/neg; keep as category
    df["class"] = df["class"].astype("category")
    # numeric coercion for all attribute columns
    attr_cols = [c for c in df.columns if c not in ("class", "split")]
    df[attr_cols] = df[attr_cols].apply(pd.to_numeric, errors="coerce")
    # DQ: null rate report
    null_rate = df[attr_cols].isna().mean().sort_values(ascending=False)
    return df, null_rate
```

Treat this as a starting sketch. Test it on the downloaded file before use.

---

## 7. Governance and licences
- Record licence per dataset (`open_dataset.licence`). UCI APS: CC BY 4.0 (attribution). NASA turbofan: licence unclear; cite and check. VAHAN mirror: ODC Attribution per listing; verify on the primary portal.
- Respect robots.txt and site terms. Use APIs or bulk downloads where offered. Do not scrape pages that block automated access.
- Keep a provenance column on every row (`source_id` or `file_id`).
