# Game Plan: Re-architecting the Framework Into a Demand-Driven, Transferable Transit Network Design Pipeline

*Generated 2026-06-14. Companion to `docs/critical_review_decisions.md`. Decisions locked with the author: (1) full rework — the thesis cannot have gaps; (2) deliver **both** R1 (new routes) and R2 (existing-route optimality); (3) demand layer must be **transferable to Mexican cities that lack an OD survey**, while using survey data where it exists. Every step lists Objective / Instructions / Outcome / Sources.*

---

## The core design decision (read this first)

The audit showed the pipeline scores *places* but the objective is about *flows* and *optimality*. The fix is a **demand-driven, two-tier architecture**:

- **Tier 1 — always-available data** (INEGI census, DENUE, OSM, GTFS): produces a *modeled* transit-demand surface, an *observed* supply/accessibility surface, and the gap between them. This tier runs in **any** Mexican/LatAm city.
- **Tier 2 — where an OD survey exists** (Guadalajara EOD 2022 in-repo; CDMX/ZMVM EOD 2017 from INEGI): used to **calibrate and validate** the Tier-1 demand model — never as a hard dependency.

This directly answers the transferability concern: the production model needs only Tier-1 data; surveys make it *more* accurate where available and provide external validation. Mexico's survey coverage is genuinely patchy — INEGI fielded a full household OD survey for the [Valle de México (CDMX) in 2017](https://www.inegi.org.mx/programas/eod/2017/), Guadalajara's EOD 2022 is a separate state product, and most metros have none — so a survey-independent core is not optional, it is required for the thesis's generalization claim.

The work is organized as **9 workstreams (W0–W8)** mapped to thesis chapters. Dependencies are stated; W0–W3 are foundational and largely sequential, W4–W6 are the analytical core, W7–W8 are validation and generalization.

---

## W0 — Remediation: close the integrity gaps before building on top

**Objective.** Remove the known data-integrity and reporting defects so nothing downstream inherits them.

**Instructions.**
1. Diagnose `v_ntl_median` (all-zero across 2,068 AGEBs). Check the VIIRS raster ingestion for a CRS/nodata/zonal-stats failure. Either repair it or formally drop it and restate "Vitality" as a single-proxy dimension. Do not ship a dead feature into the new pipeline.
2. Fix the Phase 5 report's all-zero "Phase 3 Weight" column (broken join) and **remove the 1.0000 cluster-recovery accuracy as a headline metric** — it is a tautology (predicting K-Means labels from the features that generated them), not predictive skill.
3. Re-examine the global Min-Max scaling on right-skewed indicators (e.g., `p_employment_proxy` mean 0.0385); switch to log/robust scaling and re-run CRITIC/EWM and K-Means sensitivity.

**Outcome.** A clean feature table, a corrected synthesis/errata note documenting what changed and why, and a scaling-sensitivity appendix. This is the "no gaps" baseline.

**Sources.** [Itasca/TLUMP data & modeling chapter](https://uta.pressbooks.pub/oertransportlanduse/chapter/chapter-9-introduction-to-transportation-modeling-travel-demand-modeling-and-data-collection/); critique doc §2.1–2.3, §3.3.

---

## W1 — Demand estimation layer (the missing core of R1 and R2)

**Objective.** Replace the circular "has-a-stop" target with an explicit, modeled **travel-demand** estimate that does not depend on existing transit supply. This is the single most important addition.

**Instructions.**
1. **Trip generation (productions/attractions per AGEB).** Productions from census population, households, and demographic structure (you already have `pe_*` indicators); attractions from DENUE employment and POIs by SCIAN sector (you already have `p_employment_proxy`, `p_service_density`, etc.). This is the first step of the classic four-step model and uses only Tier-1 data.
2. **Trip distribution (AGEB×AGEB OD matrix).** Apply a **doubly-constrained gravity model** with a distance-decay function on network travel time (from OSM). Output a modeled OD flow matrix between AGEBs.
3. **Mode/transit-propensity weighting.** Down-weight demand in high private-vehicle-ownership zones using census/EOD vehicle-ownership data ("Tenencia de vehículos", "Automóviles particulares por vivienda") to approximate *transit-relevant* demand and captive ridership.
4. Aggregate the OD matrix to an **AGEB-level transit-demand surface** (total transit-relevant trip ends), which becomes the demand input everywhere downstream.

**Outcome.** (a) A modeled AGEB×AGEB transit OD matrix; (b) an AGEB transit-demand surface — both reproducible from Tier-1 data alone.

**Sources.** Four-step model & trip distribution: [TLUMP trip-distribution chapter](https://uta.pressbooks.pub/oertransportlanduse/chapter/chapter-11-second-step-of-four-step-modeling-trip-distribution/), [Wikipedia: Trip distribution](https://en.wikipedia.org/wiki/Trip_distribution). Gravity calibration: [Calibrating a trip-distribution gravity model (Alexandria)](https://www.researchgate.net/publication/263316297_Calibrating_a_trip_distribution_gravity_model_stratified_by_the_trip_purposes_for_the_city_of_Alexandria). Data-driven gravity enhancement: [arXiv 2506.01964](https://arxiv.org/pdf/2506.01964). Gravity vs. radiation accessibility: [arXiv 1802.06421](https://arxiv.org/pdf/1802.06421).

---

## W2 — Survey calibration & cross-city validation of the demand model (Tier 2)

**Objective.** Make the Tier-1 gravity model defensible by calibrating its distance-decay against **observed** OD flows, and prove it transfers by validating on a *different* city's survey.

**Instructions.**
1. **Calibrate on Guadalajara.** Extract the EOD 2022 "Líneas de deseo" (desire-line) tables already in the repo — these are observed OD flows. Fit the gravity model's decay parameter(s) to reproduce them. Note the **spatial-resolution mismatch**: desire lines are at survey-zone level, not AGEB; calibrate at the survey's zone resolution, then apply the calibrated decay at AGEB resolution and document the disaggregation assumption.
2. **External validation on CDMX.** Re-run the *uncalibrated-structure* model on the ZMVM and compare against the INEGI EOD 2017 OD data. Report transfer error (e.g., flow RMSE / R² on held-out OD pairs). This is the evidence that the model works where you only have Tier-1 inputs.
3. Decide and document the production stance: **the thesis's production model uses Tier-1 only; surveys are calibration/validation instruments, not inputs.** This reconciles R3 (no subjective inputs) with using measured demand data — an OD survey is a measurement, not an expert opinion (critique doc §4.6).

**Outcome.** A calibrated, externally-validated, survey-independent demand model + a quantified transfer-error statement that underwrites the transferability claim.

**Sources.** [INEGI EOD ZMVM 2017](https://www.inegi.org.mx/programas/eod/2017/); [WRI adjusted EOD 2017 database](https://es.wri.org/publicaciones/base-de-datos-ajustada-de-la-encuesta-origen-destino-para-la-zona-metropolitana-del); gravity calibration sources from W1.

---

## W3 — Supply & coverage-gap layer (redefine the target)

**Objective.** Build an *independent* measure of existing transit supply and define the **coverage gap** that replaces the old circular label.

**Instructions.**
1. **Supply via accessibility, not stop counts.** From GTFS, compute a **cumulative-opportunities accessibility** metric per AGEB: number of jobs (DENUE) reachable by public transit within a travel-time threshold (e.g., 30/45 min), using frequency/headway-weighted routing. This captures *service quality*, not mere stop presence.
2. **Coverage-gap index.** Define gap = high transit demand (W1) **and** low transit accessibility (W3.1). This supply–demand gap index is the new dependent variable — it points at *underserved, high-demand* areas, exactly what R1 targets. Crucially, the gap's "supply" term is computed from GTFS accessibility, **not** from `route_km_800m`, breaking the circularity flagged in critique §3.2.
3. Recompute any supervised model (the old Phase 2/5) to predict this **external** gap/demand target, so SHAP interpretability finally explains something real rather than recovering its own clusters.

**Outcome.** An AGEB **Coverage-Gap Index** and a transit-accessibility surface; the supervised layer re-pointed at a meaningful target.

**Sources.** Cumulative accessibility & GTFS: [Boisjoly & El-Geneidy / accessibility-measure-choice, J. Transport Geography](https://www.sciencedirect.com/science/article/abs/pii/S0966692322002319); jobs-accessibility equity: [Evaluating equity and accessibility to jobs by public transport across Canada](https://www.sciencedirect.com/science/article/pii/S0966692318303442); transit supply–demand gap index (TGI) & GTFS equity: [GTFS-based transit equity, TRID](https://trid.trb.org/view/1669972).

---

## W4 — Reposition NPP-V as the prioritization/equity layer (not the target)

**Objective.** Keep the genuinely strong parts (NPP-V indicators, CRITIC/EWM objective weighting, equity variables) but give them their correct, defensible role.

**Instructions.**
1. Reframe NPP-V explicitly as a **multi-criteria prioritization/diagnostic** index — its native purpose in Bertolini's tradition — used to *rank* gap areas and to *score* candidate corridors, not to define demand. State this framing in the methods chapter to preempt the "node-place is a diagnostic, not a generator" objection.
2. Keep CRITIC + EWM weighting (this is what correctly satisfies R3's "no expert weighting"). Fold the equity indicators (`marginación`, `rezago`) in here as a transparent equity weight on prioritization.
3. Retain SHAP, but on the W3 external target, for interpretability of *why* an area is high-gap/high-demand.

**Outcome.** A defensible NPP-V prioritization score with an explicit equity component, decoupled from the demand estimate.

**Sources.** Node-place as diagnostic/classification: [Zhang et al. 2019, J. Transport Geography](https://discovery.ucl.ac.uk/id/eprint/10079372/); [node-place, accessibility & ridership 2023](https://www.sciencedirect.com/science/article/pii/S0966692323002119); equity weighting: [Park et al. 2022, J. Advanced Transportation](https://onlinelibrary.wiley.com/doi/10.1155/2022/5887985).

---

## W5 — Define "optimal": the multi-objective function (spine of R1 and R2)

**Objective.** Make "optimal" a written, falsifiable criterion. Nothing in R1/R2 can be answered without this.

**Instructions.**
1. Specify a **multi-objective function** with terms standard in the TNDP literature: maximize demand-weighted coverage / accessibility gain; minimize operator cost (route-km, fleet/frequency); minimize user cost (in-vehicle time + wait + transfer penalty); plus an equity term (W4).
2. Specify constraints: maximum detour ratio, stop-spacing standards (different for BRT vs. local bus), minimum demand threshold per segment, and a budget/route-length cap.
3. Decide single- vs. multi-objective handling: recommend a **Pareto/NSGA-II-style multi-objective** treatment so trade-offs are explicit rather than hidden in one weighted scalar; report the Pareto front.

**Outcome.** A formal optimality definition + constraint set, reused identically by W6 (new routes) and W7 (existing routes). This is what lets the thesis *defend* any claim that a route is or isn't optimal.

**Sources.** [Mumford et al., Multi-objective TNDP, arXiv 2201.11616](https://arxiv.org/abs/2201.11616); [Park et al. 2022 (variable demand + equity)](https://onlinelibrary.wiley.com/doi/10.1155/2022/5887985); single-metric pitfalls: [demand-driven TNDP heuristic, MDPI Sustainability 2022](https://www.mdpi.com/2071-1050/14/17/11097).

---

## W6 — R1: Demand-driven new-corridor generation

**Objective.** Generate and rank candidate new corridors (subway/BRT tier + bus tier) that the objective function (W5) actually optimizes.

**Instructions.**
1. **Anchor selection (data-driven, not magic numbers).** Choose terminal/anchor AGEBs from the W3 coverage-gap surface using a defensible cutoff (quantile or Jenks natural breaks, with a sensitivity table), and use **population-weighted centroids** snapped to the OSM graph — replacing the arbitrary 0.75/0.55 score thresholds and geometric centroids (critique §3.1).
2. **Candidate corridors.** Use Steiner/MST on the OSM drive graph **only as a connectivity scaffold** to propose how anchors could link, then **evaluate and refine candidates against the W5 objective** (demand captured, accessibility gain, cost, equity). Optionally run a metaheuristic (e.g., NSGA-II) over corridor variants and report the Pareto front. Steiner Tree is a sub-routine, not the optimizer.
3. **Mode assignment by demand volume, not score percentile.** Assign BRT/light-rail vs. local bus based on corridor demand volume vs. mode capacity ranges (cite ZMG/LatAm BRT capacity bands), not a threshold on a composite index.

**Outcome.** Ranked new-corridor candidates (two tiers) as GeoJSON, each with its objective-function score, demand captured, accessibility gain, and equity score.

**Sources.** TNDP heuristics & demand-based generation: [MDPI Sustainability 2022](https://www.mdpi.com/2071-1050/14/17/11097); learned/modern heuristics: [Holliday & Dudek 2025, Transportmetrica B](https://www.tandfonline.com/doi/full/10.1080/21680566.2025.2561863); OD-capture network design: [rapid transit network design for OD-demand capture](https://www.researchgate.net/publication/256088103_Rapid_transit_network_design_for_optimal_cost_and_origin-destination_demand_capture).

---

## W7 — R2: Existing-route audit and modification

**Objective.** Answer "are current routes optimal, and what to modify" — by scoring SITEUR routes against the *same* W5 objective.

**Instructions.**
1. **Audit.** Load SITEUR routes from GTFS shapes. Score each route and segment on the W5 terms: demand served per km, accessibility contribution, network overlap/redundancy, directness/detour, and equity of population served. Produce a route/segment scorecard.
2. **Diagnose sub-optimal segments.** Flag segments that are low-demand-served, highly redundant with parallel routes, or highly indirect — relative to the objective, so "sub-optimal" is defined, not asserted.
3. **Propose modifications.** For flagged segments, generate alternatives via **demand-weighted shortest paths** under the W5 detour/stop-spacing constraints, and **re-score before/after**. Frame as route rationalization / corridor restructuring with explicit constraints (max detour ratio, minimum segment demand).

**Outcome.** An existing-route audit table + concrete modification proposals, each with before/after objective scores and the constraints respected.

**Sources.** Route restructuring under multi-objective/equity demand: [Park et al. 2022](https://onlinelibrary.wiley.com/doi/10.1155/2022/5887985); transfer/transfer-penalty trade-offs: [MDPI Sustainability 2022](https://www.mdpi.com/2071-1050/14/17/11097); OD-capture redesign: [rapid-transit OD-capture](https://www.researchgate.net/publication/256088103_Rapid_transit_network_design_for_optimal_cost_and_origin-destination_demand_capture).

---

## W8 — Validation strategy (surrogate, since future routes are unknown)

**Objective.** Make the results academically bulletproof (C2) despite having no ground-truth "correct" future network.

**Instructions.**
1. **Backtest / network recovery.** Mask a portion of the existing high-ridership network and test whether the method (demand + gap + W6 generation) re-proposes those known-good corridors. Report recovery rate.
2. **External benchmark.** Compare W6 candidates against **announced/under-construction ZMG expansions** (e.g., Mi Macro Periférico, Línea 4/5) as an independent sanity check; report overlap.
3. **Quantitative metrics.** Coverage rate, population-served-per-route-km, job-accessibility gain, demand captured, and an **equity assessment via Gini/Lorenz** on the accessibility distribution before/after.
4. **Cross-city external validity** carries over from W2 (CDMX transfer error).

**Outcome.** A validation chapter with recovery rate, benchmark overlap, accessibility/equity deltas, and cross-city transfer error — concrete defensibility for the committee.

**Sources.** Accessibility/equity metrics & Gini: [Evaluating equity & jobs accessibility, Canada](https://www.sciencedirect.com/science/article/pii/S0966692318303442); accessibility-measure choice in project evaluation: [J. Transport Geography 2022](https://www.sciencedirect.com/science/article/abs/pii/S0966692322002319); GTFS equity/gap evaluation: [TRID](https://trid.trb.org/view/1669972).

---

## W9 — Transferability protocol & second-city demonstration

**Objective.** Substantiate the "framework generalizes to Mexican/LatAm cities" claim concretely (you said you can get more data — use that).

**Instructions.**
1. Publish a **tiered data-requirements table**: Tier 1 (census/INEGI, DENUE, OSM, GTFS) = mandatory and pan-Mexican; Tier 2 (OD survey) = optional calibration/validation. Map which Mexican metros have Tier 2 (ZMVM 2017 yes; others case-by-case).
2. Provide a **city-onboarding checklist** (data sources, CRS, zoning, GTFS availability).
3. **Demonstrate on a second city** with Tier-1 data only (and Tier-2 validation if available, e.g., CDMX) to show the pipeline runs end-to-end without a local survey.

**Outcome.** A reproducible onboarding protocol + a worked second-city demonstration — turning "transferable" from a claim into a result.

**Sources.** Survey availability: [INEGI EOD 2017](https://www.inegi.org.mx/programas/eod/2017/); GTFS-as-demand/supply substitute: [arXiv 2506.01964](https://arxiv.org/pdf/2506.01964), [TRID GTFS equity](https://trid.trb.org/view/1669972).

---

## Sequencing, dependencies, and how this maps to your existing phases

**Critical path:** W0 → W1 → W3 → W5 → (W6 ‖ W7) → W8. W2 runs alongside W1; W4 alongside W3; W9 last.

| Existing phase | Fate under this plan |
|---|---|
| Phase 1 (data acquisition) | **Keep**; extend with EOD ingestion (W2) and GTFS frequency parsing (W3). |
| Phase 2 (binary suitability) | **Replace target.** Re-point from "has-stop" label to W3 coverage-gap/demand. Keep the engineering. |
| Phase 3 (CRITIC/EWM weights) | **Keep, reposition** as W4 prioritization weighting. |
| Phase 4 (K-Means typologies) | **Keep as descriptive** segmentation only; not a predictive target. |
| Phase 5 (RF/XGBoost + SHAP) | **Re-point** to the external W3 target; drop the 1.0000 framing. |
| Phase 6 (synthesis) | **Rewrite** after W8. |
| Phase 7 (Steiner Tree) | **Subsume** into W5+W6: Steiner becomes a scaffold inside a demand-driven, multi-objective design, not the optimizer. |

**What this buys you against the objective:** W1–W3 make R1 answer "where is unmet demand," not "where transit already is." W5 gives "optimal" a definition so R2 is answerable at all. W6/W7 deliver both R1 and R2 against that definition. W2/W8/W9 make it transferable and defensible — the three things the committee will probe hardest.

---

## Consolidated sources

- Multi-objective TNDP — Mumford et al., arXiv:2201.11616. https://arxiv.org/abs/2201.11616
- Variable-demand TNDP with equity — Park et al. 2022, J. Advanced Transportation. https://onlinelibrary.wiley.com/doi/10.1155/2022/5887985
- Demand-driven TNDP heuristic — MDPI Sustainability 14(17):11097, 2022. https://www.mdpi.com/2071-1050/14/17/11097
- Learned heuristics for transit network design — Holliday & Dudek 2025, Transportmetrica B. https://www.tandfonline.com/doi/full/10.1080/21680566.2025.2561863
- Rapid transit network design for OD-demand capture. https://www.researchgate.net/publication/256088103_Rapid_transit_network_design_for_optimal_cost_and_origin-destination_demand_capture
- Four-step model / trip distribution — TLUMP OER. https://uta.pressbooks.pub/oertransportlanduse/chapter/chapter-11-second-step-of-four-step-modeling-trip-distribution/
- Travel demand modeling & data — TLUMP OER. https://uta.pressbooks.pub/oertransportlanduse/chapter/chapter-9-introduction-to-transportation-modeling-travel-demand-modeling-and-data-collection/
- Trip distribution overview — Wikipedia. https://en.wikipedia.org/wiki/Trip_distribution
- Gravity model calibration (Alexandria). https://www.researchgate.net/publication/263316297_Calibrating_a_trip_distribution_gravity_model_stratified_by_the_trip_purposes_for_the_city_of_Alexandria
- Data-driven gravity models for trip demand — arXiv:2506.01964. https://arxiv.org/pdf/2506.01964
- Accessibility via gravity & radiation models — arXiv:1802.06421. https://arxiv.org/pdf/1802.06421
- INEGI EOD ZMVM 2017. https://www.inegi.org.mx/programas/eod/2017/
- WRI adjusted EOD 2017 database. https://es.wri.org/publicaciones/base-de-datos-ajustada-de-la-encuesta-origen-destino-para-la-zona-metropolitana-del
- Cumulative vs gravity accessibility in project evaluation — J. Transport Geography 2022. https://www.sciencedirect.com/science/article/abs/pii/S0966692322002319
- Equity & jobs accessibility by transit (Canada) — J. Transport Geography. https://www.sciencedirect.com/science/article/pii/S0966692318303442
- GTFS-based transit equity evaluation — TRID. https://trid.trb.org/view/1669972
- Node-Place-Design classification — Zhang et al. 2019, J. Transport Geography. https://discovery.ucl.ac.uk/id/eprint/10079372/
- Node-place, accessibility & ridership — J. Transport Geography 2023. https://www.sciencedirect.com/science/article/pii/S0966692323002119
- Generated traffic & induced travel (latent demand) — Litman, VTPI. https://www.vtpi.org/gentraf.pdf
