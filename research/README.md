# Commercial vehicle research: Tata Motors, Mahindra, VECV, Ashok Leyland, Cummins

Research date: **9 Nov 2026**. Built from public sources for a portfolio of data-engineering and AI/ML projects.

## Read this first: what was verified and what was not

- **Primary company and government sites could not be opened from the research environment.** The egress proxy blocked tatamotors.com, Mahindra, Eicher, Ashok Leyland, Cummins and Indian government domains (HTTP 403 or no route). Facts come from **search-result snippets** of company press releases, trade press (Autocar Pro, Motorindia, TrucksBuses, Rushlane and others), NSE filing titles, and two open-data mirrors.
- Each factual row names its source URL and publication date where one was visible. "n/d" means the date was not visible.
- **Before you cite any number externally, open the source and confirm it.** Figures that conflict between sources are flagged in the company files and not resolved.
- No dataset was downloaded or profiled. Record counts marked "verify" come from dataset documentation as commonly published, not from a file in this repo.
- Tags used throughout: **[C]** confirmed launch or implementation · **[A]** announced or in progress · **[CL]** company claim, unverified · **[NF]** not found.

## Contents

| Path | What it is |
|---|---|
| `companies/01_tata_motors.md` | Tata Motors (CV focus, with TMPV items labelled) |
| `companies/02_mahindra.md` | Mahindra Truck & Bus / SML Mahindra |
| `companies/03_vecv_eicher.md` | VECV (Eicher Trucks & Buses) |
| `companies/04_ashok_leyland.md` | Ashok Leyland and Switch Mobility |
| `companies/05_cummins.md` | Cummins and Tata Cummins JV, with India focus |
| `comparison_five_companies.md` | Side-by-side comparison of the five companies |
| `sources_directory.csv` | 93 sources with URL, date, information, fields, project use, download status and verification status |
| `data/dataset_inventory.csv` | 11 datasets: verified ones and clearly marked unverified candidates |
| `data/data_dictionary.csv` | 42 engine, after-treatment, vehicle, maintenance, fleet and market fields, each classed A–E |
| `data/schema_postgres.sql` | PostgreSQL schema for collected facts, sources and open datasets (run and tested on PostgreSQL 16) |
| `data/etl_and_data_quality_plan.md` | Collection layers, pipeline, cleaning, de-duplication, DQ checks, Airflow outline |
| `projects_and_roadmap.md` | Top 10 AI problems, 3 data-engineering projects, 3 AI/ML projects, step-by-step roadmap |
| `missing_data_requiring_permission.md` | Fields that need OEM, fleet or dealer permission, and acceptable routes to ask |

## Five-line summary

1. **Tata Motors:** Fleet Edge connects over 1 million vehicles (company, June 2026). Electric launch of 17 trucks (Jan 2026) includes the Prima E.55S, now delivering to BillionE. Hydrogen trials since March 2025 (H2-ICE and fuel cell). Iveco deal is pending final close.
2. **Mahindra:** iMAXX telematics (2020) became iMAXX 2.0 with the BLAZO i-TRK (Aug 2026, 320 hp, 48-hour uptime guarantee). Electric is early: e-ZEO is live; an e-bus is due in FY27; the e-truck has no date. The truck and bus business is moving into SML Mahindra.
3. **VECV:** 100,000 vehicles sold in FY26 (first time). Pro X EV launched Jan 2025 (206–249 km range, sources differ). Uptime NXT and Service One (generative-AI tool for technicians) launched 13 Oct 2026.
4. **Ashok Leyland:** 2023 H2-ICE truck with Reliance; Switch Mobility e-bus growth (1,530 e-buses in FY26, company figure); in-house battery packs planned by H1 FY28; i-ALERT 3.0 and Uptime Solution Centre; Syncron predictive-maintenance partnership (announced).
5. **Cummins:** Connected Solutions for 2027 engines (predictive insights, remote diagnostics); PrevenTech for mining; CPCB IV+ gensets (EXCON 2025); TCPL GES makes H2-ICE engines in Jamshedpur. **No NVIDIA or Microsoft digital-twin partnership was found for Cummins**; that story is Caterpillar's.

## Key limits to keep in mind
- **No company publishes raw operational data.** Every project must use public proxies (UCI APS Failure, NASA C-MAPSS, VAHAN registrations) or simulation, and say so.
- Telemetry, DPF, NOx and battery-health data need permission (see `missing_data_requiring_permission.md`).

## How to reproduce the CSVs
The CSVs were generated from Python lists and checked for consistent column counts. The schema was loaded into a local PostgreSQL 16 cluster and a natural-key constraint was tested.
