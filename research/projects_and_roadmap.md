# Projects, roadmap and the AI problem map

Built on the verified public data in `research/data/dataset_inventory.csv`. Every project below either uses a verified open dataset or is explicitly marked as needing your own data.

**Key rule for your portfolio:** Say which data is real, which is a public proxy, and which is simulated. Interviewers check this first.

---

## Part A — Top 10 real-world AI/ML problems in commercial vehicles

| # | Problem | Real business problem | Required data | Possible ML algorithms | Expected output | Business impact | Difficulty | Public data sufficient? |
|---|---|---|---|---|---|---|---|---|
| 1 | Diesel engine failure prediction | Unplanned breakdowns on routes, towing cost, lost revenue | Engine sensor history, fault codes, repair records | Logistic regression, gradient boosting (XGBoost/LightGBM), anomaly detection (Isolation Forest) | Probability of failure in next N days per vehicle | High: fewer breakdowns, better uptime | Medium | **Partial.** UCI APS Failure (DS-01) is the closest public proxy: real Scania truck sensor histograms, component-failure label, but anonymised and not an engine-specific log |
| 2 | Turbocharger failure detection | Turbo failure is costly and often late-stage | Boost pressure, exhaust temp, oil pressure, RPM | Residual-based anomaly detection, LSTM autoencoder, one-class SVM | Anomaly score and alert | Medium-high | Medium-high | **No.** No public turbo sensor data. Simulate or use own OBD-II logs |
| 3 | DPF blockage prediction | Forced regen, derate, workshop visits | DPF ΔP, exhaust temp, regen events, duty cycle | Regression on ΔP trend; survival model for time-to-blockage | Days until DPF cleaning needed | High: fewer workshop visits | Medium | **No.** DPF signals are not public. Use simulation or own data |
| 4 | SCR system malfunction detection | DEF/SCR faults stop trucks or cause derate | SCR temp, NOx before/after, DEF level, dosing | Rule-based plus classifier; multivariate anomaly | Fault class and risk score | High (compliance and uptime) | High | **No.** Use spec and standards as reference only |
| 5 | NOx sensor anomaly detection | Out-of-range NOx causes compliance risk and fines | NOx readings, SCR inlet/outlet, ambient | Time-series anomaly detection (STL residuals, Isolation Forest) | Alert on drift or stuck sensor | High (regulatory) | High | **No.** CPCB and BS standards are public; sensor data is not |
| 6 | Fuel consumption prediction | Fuel is the largest cost for fleets | Speed, load, gradient, GVW, route, idle time, fuel used | Gradient boosting, linear regression with features | Predicted L/100 km per trip | Very high (fuel is 30–40% of cost, typical industry estimate: verify) | Medium | **Partial.** Use VAHAN spec-like features and your own trip logs; no public trip data |
| 7 | Predictive maintenance scheduling | Calendar-based service wastes money and misses faults | Service history, failure history, usage | Survival analysis, classification, schedule optimisation (greedy or ILP) | Optimised service date per vehicle | High | Medium-high | **Partial.** APS (DS-01) for failure modelling; scheduling logic is generic |
| 8 | Remaining Useful Life (RUL) estimation | Decide replacement before failure | Run-to-failure sensor series | LSTM/GRU, CNN, gradient boosting on degradation features | RUL in cycles or hours | High | Medium | **Yes, for method development.** NASA C-MAPSS (DS-03) gives run-to-failure turbofan data (aviation, not trucks) |
| 9 | Vehicle downtime prediction | Downtime is the top cost metric for fleets | Fault history, service events, operating hours, failure events | Classification (time-to-downtime), survival models | Probability of downtime in next 7 days | Very high | Medium | **No** at vehicle level. Company downtime figures are claims (Cummins 45+ h per engine; Mahindra 48-h guarantee) |
| 10 | Fleet fuel-efficiency optimisation | Route and driver choices drive fuel | Trip logs, route, driver, load | Optimisation (route cost model), clustering of driving styles | Ranked recommendations per driver or route | Very high | Medium-high | **Partial.** Simulation plus your own logs; company claims (Mileage Sarathi 4.8–7%) are a benchmark to test against |

**Bonus items from your list (short):**
- **Driver behaviour analysis:** harsh braking/acceleration from OBD or phone sensors; clustering; public datasets not verified; use your own logs.
- **Battery health (SoH) for electric trucks:** NASA battery ageing dataset is a common proxy (**not verified in this session**; see DS-10).

---

## Part B — Three data-engineering projects (beginner to intermediate)

### DE-1. VAHAN registrations pipeline and dashboard
- **Data:** VAHAN monthly registrations by maker, category, fuel, norm (DS-05 to DS-08, via India Data Portal mirror; verify on Parivahan or data.gov.in).
- **Build:** Airflow DAG: download → SHA-256 → raw store → Pandas clean → PostgreSQL `core.registration_monthly` → SQL views → Matplotlib/Seaborn dashboard.
- **Skills:** Python, Pandas, SQL, PostgreSQL, Airflow, DQ checks, idempotent loads.
- **Portfolio proof:** the DQ log (`audit.dq_check_result`) and a rerun-safe load.
- **Story:** "Which makers are gaining share, and where is the EV and CNG shift happening?"

### DE-2. Public claims knowledge base with source tracking
- **Data:** the 93 sources in `research/sources_directory.csv` and the claims in `research/companies/*.md`.
- **Build:** Structured tables (`core.fact_claim`, `core.source_document`), reconciliation of conflicting figures (e.g. Mileage Sarathi 4.8% vs 6–7%; e-ZEO 120 vs 160 km), and a view of each claim with its source URL and date.
- **Skills:** data modelling, provenance, SQL, referential integrity, data-quality rules.
- **Portfolio proof:** every claim links to a source; conflicting values are kept, not overwritten.

### DE-3. Engine-sensor lakehouse (public data)
- **Data:** NASA C-MAPSS FD001–FD004 (DS-03) and UCI APS Failure (DS-01), with the licence caveat noted.
- **Build:** raw → staging → core layout; per-cycle time-series table; schema validation; drift checks between train and test subsets; a reproducible Airflow DAG.
- **Skills:** time-series modelling in SQL and Pandas, partitioning, data contracts.
- **Portfolio proof:** schema tests and a DQ report for each load.

---

## Part C — Three AI/ML engineer projects

### ML-1. Engine-failure classification with cost-sensitive learning (APS Failure)
- **Data:** UCI APS Failure at Scania Trucks (DS-01; CC BY 4.0).
- **Problem:** Heavy class imbalance (about 1,000 positives in 60,000 train rows, per UCI). The challenge cost is 10 per false positive and 500 per false negative.
- **Method:** Baseline logistic regression → gradient boosting with class weights → tune the decision threshold on the **challenge cost function** (not accuracy). Compare with the published benchmark.
- **Deliverable:** notebook with cost curves, PR-AUC, calibration, and a short write-up on threshold choice.
- **Difficulty:** Intermediate. The imbalance and cost framing are real-world and interview-friendly.

### ML-2. Remaining Useful Life with sequence models (C-MAPSS)
- **Data:** NASA turbofan degradation (DS-03). Licence unclear; cite Saxena & Goebel (2008) and check before redistributing.
- **Method:** Feature engineering from sensor trends and rolling statistics → gradient boosting baseline → GRU/LSTM on sliding windows. Evaluate with the **NASA asymmetric score** (late predictions penalised more than early ones) and RMSE.
- **Deliverable:** notebook, error-by-cycle plot, and a comparison with a baseline.
- **Difficulty:** Intermediate-advanced.

### ML-3. Registration and EV-share forecasting (VAHAN)
- **Data:** VAHAN monthly registrations by maker and fuel (DS-05, DS-07).
- **Method:** Seasonal baseline (SARIMA or Prophet) → gradient boosting with lag and calendar features → hierarchical forecast (maker → total) → backtest on a holdout window.
- **Deliverable:** forecast with prediction intervals, error table, and the EV-share story.
- **Difficulty:** Intermediate. Strong link to commercial vehicle market analysis.

---

## Part D — Step-by-step implementation roadmap

Assumes about 10–12 hours a week. Adjust to your pace.

| Phase | Weeks | Work | Output |
|---|---|---|---|
| **0. Setup** | 1 | Python env (NumPy, Pandas, Matplotlib, Seaborn); PostgreSQL 16 locally; Git repo structure | Working env; schema loaded (`schema_postgres.sql`) |
| **1. Data collection** | 2–3 | Download DS-01, DS-03, DS-05 (confirm licences). Store raw files with SHA-256 | Raw layer populated; `raw.source_file` filled |
| **2. Data engineering** | 4–6 | Build DE-1 (VAHAN) pipeline; DQ checks; first dashboard | Working pipeline and DQ log |
| **3. Exploration** | 7 | EDA on APS and C-MAPSS. Missing-value report; class imbalance; sensor drift plots | EDA notebook |
| **4. ML-1** | 8–9 | APS classifier with cost-sensitive learning | Notebook and write-up |
| **5. ML-2** | 10–12 | C-MAPSS RUL: baseline and GRU | Notebook; NASA score table |
| **6. ML-3** | 13–14 | VAHAN forecast with backtest | Forecast notebook |
| **7. Portfolio** | 15–16 | README per project; architecture diagram; limitations section; one-page summary | Public GitHub portfolio |
| **8. Interview prep** | 17+ | Explain each project using your automotive experience (fault codes, DPF, service intervals) | Talk track |

**Checkpoints:** end of each phase, update `research/data/dataset_inventory.csv` with any verified record count or licence change.

---

## Part E — Notes on your background
- Your Cummins field service experience gives you the fault-code and service-workflow context most data scientists lack. Use it to define labels (for example, what counts as a "failure" event) and to sanity-check results.
- Keep every project within public data. Do not use anything you saw in the field that is confidential to Cummins or customers.
