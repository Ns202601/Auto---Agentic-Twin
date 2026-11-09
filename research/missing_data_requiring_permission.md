# Missing data that needs company permission or authorised access

These fields are needed for strong commercial-vehicle projects. None is publicly available, so each one needs an agreement, a partner programme, or a data owner's consent. **This project does not seek or use any of them without authorisation.**

Field codes follow `research/data/data_dictionary.csv`: **E** = requires company permission or authorised access; **D** = not publicly available.

## 1. Engine and powertrain telemetry (E)

| Field | Why it matters | Who could provide it legitimately | Route to request |
|---|---|---|---|
| Coolant temperature, oil pressure, boost pressure, exhaust temperature, engine load | Core inputs for engine-failure and turbo models | OEM (Tata, Mahindra, VECV, Ashok Leyland) under a data-sharing or research agreement; fleet owners for their own vehicles | Academic or industry research proposal to the OEM's connected-vehicle or digital team; fleet owner's written consent |
| Engine RPM, engine hours, battery voltage (12 V and HV pack) | Duty-cycle and wear features | Same as above | Same |
| DPF differential pressure, DPF regeneration events | Blockage prediction | OEM or fleet with telematics | Same; request anonymised, aggregated data |
| SCR temperature, NOx readings, DEF consumption, EGR performance, after-treatment fault codes | SCR and NOx anomaly detection | OEM or aftertreatment supplier (e.g. Tata Cummins GES, Cummins) | Supplier research-partnership programme |

## 2. Maintenance and reliability records (E or D)

| Field | Why it matters | Who could provide it | Route |
|---|---|---|---|
| Service date, repair history, replacement component | Labels for maintenance and failure models | Dealer network or fleet maintenance system (with consent) | Fleet or dealer data-sharing agreement; anonymise vehicle IDs |
| Component failure labels with root cause | Supervised failure models | OEM quality and warranty team | Research agreement; the OEM's own failure codes |
| Fault codes (DTCs) with timestamps | Diagnostic models | Telematics platform owner (OEM or fleet) | Same as above |
| Maintenance cost and downtime (per vehicle) | Business-impact modelling | Fleet operators (finance and maintenance) | Fleet-level aggregated figures under NDA |

## 3. Fleet and operations data (E)

| Field | Why it matters | Who could provide it | Route |
|---|---|---|---|
| Route information, vehicle speed, distance, idle hours | Fuel and route optimisation | Fleet operators; OEM telematics platforms | Fleet partnership; anonymised trip logs with consent |
| Vehicle utilisation, route performance, delivery time, operating cost | Fleet KPI models | Fleet operators | Same |
| Driver behaviour events (harsh braking, idling) | Driver-coaching models | Fleet and driver with consent | Consent-based pilot; personal-data rules apply (DPDP Act, India) |
| Fleet-level fuel efficiency (per vehicle) | Benchmarking claims such as Mileage Sarathi's 4.8–7% | Tata's Mileage Sarathi customers, or a published audit | Ask Tata for the methodology and an independent evaluation |

## 4. Company-level data that is partly public (B or E)

| Field | Status | What is needed |
|---|---|---|
| Connected-vehicle counts by product line | Public as totals (Tata >1 M; Eicher 460k+; AL ~170k) | Breakdown by segment and region: request from investor relations |
| EV unit volumes by model | Partly public | Monthly volumes by model: investor-relations request |
| PrevenTech and iMAXX results (downtime, fuel) | Company claims only | Measurement methodology and audit reports |
| Battery state-of-health telemetry for Prima E.55S and Pro X EV | Not found | Fleet or OEM telemetry agreement |

## 5. Routes that are acceptable

1. **Public data first.** Use the open datasets and public filings in `research/data/dataset_inventory.csv`.
2. **Partner programmes.** Apply through OEM or supplier research programmes, or university-industry collaborations. Send a written proposal stating the purpose, data minimisation, retention and publication plan.
3. **Consent-based pilots.** Work with a fleet owner who gives written consent for an anonymised dataset.
4. **Simulation.** Generate synthetic data from published specs and standards, clearly labelled as synthetic.

## 6. What this project will not do
- Access OEM, fleet or dealer systems without authorisation.
- Scrape restricted pages or bypass logins.
- Use confidential information from prior employment (for example, internal Cummins service data). Your own field knowledge can shape features and labels, but the data itself must be public or authorised.
