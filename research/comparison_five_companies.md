# Five-company comparison — commercial vehicles (as of 9 Nov 2026)

Tags: **[C]** confirmed launch/implementation · **[A]** announced or in progress · **[CL]** company claim (not independently verified) · **[NF]** not found in public sources.
Every cell traces to a file in `research/companies/` where the source URL is given.

| Dimension | Tata Motors (CV) | Mahindra (Truck & Bus / SML Mahindra) | VECV (Eicher) | Ashok Leyland | Cummins (+ Tata Cummins JV) |
|---|---|---|---|---|---|
| **Core CV products** | 7–55 t range incl. Prima, Ultra EV, Prima E.55S (17 trucks, Jan 2026) [C] | BLAZO X (BS6) [C]; BLAZO i-TRK, 320 hp, Aug 2026 [C]; e-ZEO light EV [C] | Eicher trucks and buses 4.9–55 t (EUTECH6) [C]; Pro X SCV (EV, CNG, diesel) [C] | MHCV, LCV, buses; Switch Mobility EVs [C] | Engines (X15, L10, QSK60, B6.7H); gensets [C]; supplied to Tata and others |
| **Engine technology** | BS6 SCR / EGR+SCR (2020) [C]; 3.8 L NA CNG, 3-way cat (2019) [C]; H2-ICE and FCEV trials (2025) [C] | mPOWER / FuelSmart 7.2 L, 206 kW (Blazo X) [C]; SCR + DOC + DPF + EGR on CRDe [C]; airless SCR [CL] | Euro VI base engines from VEPT (Pithampur), Volvo-linked [C]; SCR-based BS VI [C] | A6 380 hp CRS, H6 H2/flex, H6 CEV, P15, H4 [C] (EXCON 2025); H2-ICE truck with Reliance (2023) [C] | Single Module ATS, no-EGR options [C]; SCR cuts NOx up to 99% [CL]; H2-ICE X15H concept [C] |
| **AI initiatives** | Mileage Sarathi (fuel AI, 6–7% claimed; figures disagree) [CL]; AI across design, quality, after-sales (TMPV side) [A] | MATRIX plant AI and Uptime.AI (plant side) [C]; on-vehicle AI for power mode (i-TRK) [CL] | Uptime NXT and Service One GenAI for technicians (13 Oct 2026) [C] | AI-driven prognostics [CL]; Syncron ML prognostics [A]; autonomous tie-ups with Minus Zero and Aidrivers [A] | AI on 80 M data points (QSK60, 50 trucks) [CL]; Axion AI for uptime and warranty [CL] |
| **Telematics** | Fleet Edge: >1 M connected (June 2026) [CL]; 12 PB data claim [CL]; ₹1,292/veh/yr [CL] | iMAXX (2020) → iMAXX 2.0 (2026): diagnostics, driver behaviour, remote ignition inhibit [C] | My Eicher: 460,000+ vehicles [CL]; Eicher LIVE: 100% of new vehicles connected since 2020 [C]; iTriangle JV [C] | i-ALERT 3.0 [C]; DigitAL Nxt platform [C]; ~170k connected MHCVs (May 2025 report) [CL] | Connected Solutions (2027): predictive insights, remote diagnostics [C]; Acumen module [C]; Platform Science VHI [C] |
| **Predictive maintenance** | Stated as rebuilt "agentic" workflow [A]; fault-code trends (Priority tier, unverified) [NF] | Predictive diagnostics on iMAXX 2.0 [CL]; no model published [NF] | Predictive uptime in My Eicher [CL]; Uptime NXT diagnostics [C] | Uptime Solution Centre (Ennore): predictive analytics + aftersales [C]; Syncron CMS failure detection [A] | PrevenTech (mining): 45+ h downtime avoided per engine, $70k/engine (2024 sites) [CL] |
| **EV development** | Prima E.55S (450 kWh, up to 350 km), BillionE order 250; 1st deliveries Apr 2026 [C]; EV volumes +59% FY26 [CL] | e-ZEO (21.3 kWh, 120–160 km, sources differ) [C]; e-bus FY27 [A]; e-truck, no date [A] | Pro X EV (32/40 kWh, 206–249 km), Bhopal, deliveries Feb 2025 [C] | Switch: 1,530 e-buses FY26 (+238%), e-LCV ~1,600 (+56%) [CL]; in-house packs by H1 FY28 [A] | No CV EV product line found; supplies engines and after-treatment for ICE and H2 [NF for EV] |
| **Emission technologies** | SCR, EGR+SCR, 3-way cat (CNG), H2-ICE [C]; DPF not found [NF] | SCR + DOC + DPF + EGR, low AdBlue claim [C] | SCR (duty-cycle based) for BS VI; DPF not named [C] | Compact Flex EATS (EXCON 2025) [C]; SCR details [NF] | Single Module ATS; SCR (up to 99% NOx) [CL]; CPCB IV+ gensets [C] |
| **Publicly accessible datasets** | None raw. Financial filings, press metrics, product specs [C] | None raw. Brochures, IAR, iMAXX press [C] | None raw. Sales, Pro X specs, FY26 FS PDFs [C] | None raw. Filings, press metrics [C] | None raw. Product pages and press [C] |
| **Potential AI/ML project opportunities** | Fleet fuel-efficiency model (validate Mileage Sarathi claim on public data); EV range/SoH prediction from public specs; sales forecasting from filings | Blazo spec-to-performance model; uptime claim analysis; fleet registration forecasting using VAHAN maker data | Pro X range prediction from spec data; service-demand forecasting from sales milestones; GenAI diagnostics evaluation (public text) | Connected-fleet growth time-series; EV profitability and volume forecasting; EV battery-pack plan tracking | Engine-health project using NASA C-MAPSS as a proxy; NOx/SCR anomaly detection on open data; BS VI spec analysis |

---

## Cross-company patterns

1. **Every company claims connected or predictive capability, but none publishes operational data.** The public record is product claims and press. That gap is the biggest constraint on your projects.
2. **Electrification is concentrated in light and mid segments and in buses.** Heavy electric trucks are still early. Hydrogen is in trials, MoUs and concept engines.
3. **Telematics scale is the most-quoted metric.** Tata: >1 M; Eicher: 460k+; Ashok Leyland: ~170k; Cummins and Mahindra report by product line. Compare them only with the caveat that definitions differ.
4. **Fuel-efficiency claims are common, but figures vary.** Tata 4.8–7%; Mahindra >10% (BS4 fleets); i-TRK +10% (vs previous model).
5. **After-treatment is SCR-led in BS VI.** DPF and EGR appear in configurations, but public DPF and NOx data does not exist.

## Who to watch (open items)
- Tata: Iveco close (Q2 FY27 target), 12 PB claim, Priority tier.
- Mahindra: SML Mahindra truck-bus transfer (FY27), e-bus.
- VECV: Uptime NXT adoption, Pro X volumes.
- Ashok Leyland: H1 FY28 battery plant, in-house packs, hydrogen timing.
- Cummins: X15H and H2-ICE production timing; India after-treatment roadmap.
