-- =====================================================================
-- Commercial vehicle research warehouse: PostgreSQL schema (v1)
-- Purpose: store PUBLIC research facts, source provenance, and open
-- datasets. It does NOT store private or OEM operational data.
-- Target: PostgreSQL 14+ (tested on PostgreSQL 16).
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS raw;      -- files as received, untouched
CREATE SCHEMA IF NOT EXISTS staging;  -- typed, trimmed, deduplicated
CREATE SCHEMA IF NOT EXISTS core;     -- conformed master + reference + facts
CREATE SCHEMA IF NOT EXISTS audit;    -- pipeline runs and data-quality results

-- ---------------------------------------------------------------------
-- audit: pipeline runs and DQ results
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit.ingestion_run (
    run_id          BIGSERIAL PRIMARY KEY,
    pipeline_name   TEXT        NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running','success','failed','partial')),
    rows_read       BIGINT,
    rows_loaded     BIGINT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS audit.dq_check_result (
    check_id        BIGSERIAL PRIMARY KEY,
    run_id          BIGINT      REFERENCES audit.ingestion_run(run_id),
    table_name      TEXT        NOT NULL,
    check_name      TEXT        NOT NULL,   -- e.g. 'not_null:class', 'unique:source_id'
    severity        TEXT        NOT NULL CHECK (severity IN ('info','warn','error')),
    passed          BOOLEAN     NOT NULL,
    failed_rows     BIGINT      NOT NULL DEFAULT 0,
    checked_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- raw: file landing (one row per file received)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.source_file (
    file_id         BIGSERIAL PRIMARY KEY,
    source_key      TEXT        NOT NULL,   -- e.g. 'uci_421', 'vahan_maker'
    file_name       TEXT        NOT NULL,
    storage_uri     TEXT        NOT NULL,   -- s3://... or gs://... or local path
    sha256          CHAR(64)    NOT NULL,   -- de-dupe identical downloads
    byte_size       BIGINT      NOT NULL CHECK (byte_size >= 0),
    downloaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    licence         TEXT,
    UNIQUE (source_key, sha256)
);

-- ---------------------------------------------------------------------
-- core: master / reference data
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.company (
    company_id      SERIAL PRIMARY KEY,
    company_name    TEXT NOT NULL UNIQUE,      -- 'Tata Motors', 'Mahindra', 'VECV', 'Ashok Leyland', 'Cummins'
    legal_entity    TEXT,                       -- e.g. 'Tata Motors Limited (CV)', 'SML Mahindra Limited'
    country         TEXT NOT NULL DEFAULT 'India',
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS core.source_organisation (
    org_id          SERIAL PRIMARY KEY,
    org_name        TEXT NOT NULL UNIQUE,     -- 'MoRTH', 'NASA', 'UCI', 'Company press'
    org_type        TEXT NOT NULL CHECK (org_type IN
                    ('government','company','academic','open_data_portal','vendor','press','other'))
);

CREATE TABLE IF NOT EXISTS core.source_document (
    source_id       TEXT PRIMARY KEY,           -- e.g. 'TM-07' (from sources_directory.csv)
    company_id      INT  REFERENCES core.company(company_id),
    org_id          INT  REFERENCES core.source_organisation(org_id),
    title           TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    publication_date DATE,                      -- NULL when not visible
    date_text       TEXT,                       -- original text, e.g. '2026 (exact n/d)'
    downloadable    BOOLEAN,
    verification    TEXT NOT NULL CHECK (verification IN
                    ('primary_opened','primary_snippet','secondary_snippet','vendor_claim','unverified')),
    CONSTRAINT source_url_format CHECK (source_url ~ '^https?://' OR source_url LIKE 'NOT RETRIEVED%')
);

CREATE TABLE IF NOT EXISTS core.fact_claim (
    claim_id        BIGSERIAL PRIMARY KEY,
    company_id      INT  NOT NULL REFERENCES core.company(company_id),
    source_id       TEXT NOT NULL REFERENCES core.source_document(source_id),
    topic           TEXT NOT NULL CHECK (topic IN
                    ('product','ev','hydrogen','engine','after_treatment','telematics',
                     'predictive_maintenance','ai','digital_twin','partnership','financial','esg','other')),
    claim_text      TEXT NOT NULL,
    claim_value     NUMERIC,                    -- numeric where applicable
    claim_unit      TEXT,
    category        TEXT NOT NULL CHECK (category IN
                    ('confirmed_implementation','announced','company_claim','unverified','not_found')),
    as_of_date      DATE
);

CREATE TABLE IF NOT EXISTS core.vehicle_model (
    model_id        SERIAL PRIMARY KEY,
    company_id      INT  NOT NULL REFERENCES core.company(company_id),
    model_name      TEXT NOT NULL,
    segment         TEXT CHECK (segment IN ('HCV','MHCV','LCV','ICV','SCV','bus','off_highway','other')),
    powertrain      TEXT CHECK (powertrain IN ('diesel','cng','lng','electric','hydrogen_ice','fuel_cell','flex','other')),
    gvw_tonnes_min  NUMERIC(5,2),
    gvw_tonnes_max  NUMERIC(5,2),
    launch_date     DATE,
    source_id       TEXT REFERENCES core.source_document(source_id),
    UNIQUE (company_id, model_name)
);

CREATE TABLE IF NOT EXISTS core.engine_spec (
    engine_spec_id  SERIAL PRIMARY KEY,
    company_id      INT  NOT NULL REFERENCES core.company(company_id),
    engine_name     TEXT NOT NULL,              -- e.g. 'mPOWER 7.2L', 'A6 380 hp CRS'
    displacement_l  NUMERIC(4,2),
    power_kw        NUMERIC(6,1),
    torque_nm       NUMERIC(7,1),
    emission_std   TEXT,                        -- 'BS6', 'CPCB IV+', ...
    after_treatment TEXT,                       -- 'SCR', 'SCR+DOC+DPF+EGR', 'SCR+ASC', '3-way catalyst'
    source_id       TEXT REFERENCES core.source_document(source_id),
    UNIQUE (company_id, engine_name)
);

-- ---------------------------------------------------------------------
-- core: open-data facts (time series)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.registration_monthly (
    -- VAHAN open data (MoRTH / Parivahan) - aggregated monthly
    reg_id          BIGSERIAL PRIMARY KEY,
    reg_month       DATE    NOT NULL,           -- first day of month
    state_code      TEXT    NOT NULL,
    rto_code        TEXT,
    maker_name      TEXT    NOT NULL,
    vehicle_class   TEXT,
    fuel_type       TEXT,
    emission_norm   TEXT,
    registrations   BIGINT  NOT NULL CHECK (registrations >= 0),
    source_id       TEXT    REFERENCES core.source_document(source_id),
    file_id         BIGINT  REFERENCES raw.source_file(file_id)
);
-- natural key enforced with an expression index (NULL-safe via COALESCE)
CREATE UNIQUE INDEX IF NOT EXISTS ux_reg_natural_key ON core.registration_monthly
    (reg_month, state_code, COALESCE(rto_code,''), maker_name,
     COALESCE(vehicle_class,''), COALESCE(fuel_type,''), COALESCE(emission_norm,''));
CREATE INDEX IF NOT EXISTS ix_reg_maker_month ON core.registration_monthly (maker_name, reg_month);

CREATE TABLE IF NOT EXISTS core.fleet_metric_claim (
    -- company-published fleet counts and KPIs (claims, not measurements)
    company_id      INT  NOT NULL REFERENCES core.company(company_id),
    metric_name     TEXT NOT NULL CHECK (metric_name IN
                    ('connected_vehicles','fuel_saving_pct','uptime_guarantee_hours',
                     'downtime_hours_avoided','maintenance_cost_avoided','rd_spend_inr_cr',
                     'revenue_inr_cr','sales_units','ev_units')),
    as_of_date      DATE    NOT NULL,
    metric_value    NUMERIC NOT NULL,
    unit            TEXT    NOT NULL,
    claim_type      TEXT    NOT NULL CHECK (claim_type IN ('company_claim','filing','press_release','trade_press')),
    source_id       TEXT    NOT NULL REFERENCES core.source_document(source_id),
    PRIMARY KEY (company_id, metric_name, as_of_date, source_id)
);

-- ---------------------------------------------------------------------
-- core: open ML datasets (catalogue + field dictionary)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.open_dataset (
    dataset_id      TEXT PRIMARY KEY,           -- e.g. 'DS-01' (from dataset_inventory.csv)
    name            TEXT NOT NULL,
    org_id          INT  REFERENCES core.source_organisation(org_id),
    access_link     TEXT,
    file_format     TEXT,
    record_count    BIGINT,                     -- NULL until verified
    column_count    INT,
    target_column   TEXT,
    is_synthetic    BOOLEAN,                    -- NULL = not verified
    licence         TEXT,
    verification    TEXT NOT NULL CHECK (verification IN ('confirmed_listing','file_downloaded','file_profiled','unverified'))
);

CREATE TABLE IF NOT EXISTS core.dataset_field (
    dataset_id      TEXT NOT NULL REFERENCES core.open_dataset(dataset_id),
    field_name      TEXT NOT NULL,
    field_type      TEXT,                       -- 'numeric','categorical','datetime','label','text'
    unit            TEXT,
    description     TEXT,
    is_target       BOOLEAN NOT NULL DEFAULT FALSE,
    null_pct        NUMERIC(6,3),               -- filled by profiling step
    PRIMARY KEY (dataset_id, field_name)
);

-- ---------------------------------------------------------------------
-- core: data-availability dictionary (A-E codes from the research)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.field_availability (
    field_name      TEXT PRIMARY KEY,           -- e.g. 'coolant_temperature'
    field_group     TEXT NOT NULL CHECK (field_group IN
                    ('engine','after_treatment','vehicle','maintenance','fleet','market')),
    availability    CHAR(1) NOT NULL CHECK (availability IN ('A','B','C','D','E')),
    best_open_proxy TEXT                        -- dataset_id or NULL
);

-- ---------------------------------------------------------------------
-- staging: typed copies of raw inputs, deduplicated
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.turbofan_rul (
    unit_id         INT     NOT NULL,
    cycle           INT     NOT NULL CHECK (cycle >= 1),
    subset          TEXT    NOT NULL CHECK (subset IN ('FD001','FD002','FD003','FD004')),
    split           TEXT    NOT NULL CHECK (split IN ('train','test')),
    op_setting_1   NUMERIC, op_setting_2 NUMERIC, op_setting_3 NUMERIC,
    sensor_01 NUMERIC, sensor_02 NUMERIC, sensor_03 NUMERIC, sensor_04 NUMERIC,
    sensor_05 NUMERIC, sensor_06 NUMERIC, sensor_07 NUMERIC, sensor_08 NUMERIC,
    sensor_09 NUMERIC, sensor_10 NUMERIC, sensor_11 NUMERIC, sensor_12 NUMERIC,
    sensor_13 NUMERIC, sensor_14 NUMERIC, sensor_15 NUMERIC, sensor_16 NUMERIC,
    sensor_17 NUMERIC, sensor_18 NUMERIC, sensor_19 NUMERIC, sensor_20 NUMERIC,
    sensor_21 NUMERIC,
    file_id         BIGINT  REFERENCES raw.source_file(file_id),
    PRIMARY KEY (subset, split, unit_id, cycle)
);

CREATE TABLE IF NOT EXISTS staging.scania_aps (
    row_id          BIGSERIAL PRIMARY KEY,
    split           TEXT    NOT NULL CHECK (split IN ('train','test')),
    class_label     TEXT    NOT NULL CHECK (class_label IN ('pos','neg')),
    attributes      JSONB   NOT NULL,           -- 171 anonymised attributes; 'na' stored as NULL
    file_id         BIGINT  REFERENCES raw.source_file(file_id)
);

-- ---------------------------------------------------------------------
-- Helpful views
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW core.v_registrations_by_maker_year AS
SELECT maker_name,
       EXTRACT(YEAR FROM reg_month)::INT AS reg_year,
       SUM(registrations)                AS total_registrations
FROM core.registration_monthly
GROUP BY maker_name, EXTRACT(YEAR FROM reg_month);

CREATE OR REPLACE VIEW core.v_claims_by_company AS
SELECT c.company_name, f.claim_text, f.topic, f.category, s.source_url, s.publication_date
FROM core.fact_claim f
JOIN core.company c         ON c.company_id = f.company_id
JOIN core.source_document s ON s.source_id  = f.source_id;
