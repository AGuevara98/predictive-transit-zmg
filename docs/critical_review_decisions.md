# Critical Review: Do the Project's Decisions Serve the Stated Objective?

*Independent methodological audit — generated 2026-06-14. Grounded in the actual repo artifacts (synthesis report, source code, phase outputs) and transit-planning literature. No claim here is asserted without either a verified code/output reference or a cited source.*

---

## 0. The objective, restated as testable requirements

The stated goal has three parts and three constraints:

- **(R1)** Determine **where a new subway/bus route should be placed.**
- **(R2)** Determine **whether existing routes are optimal, and which segments to modify.**
- **(R3)** Inputs must be **entirely data** — no expert opinion or surveys.
- **(C1)** First test case: **Guadalajara / Latin-American context.**
- **(C2)** Must be **academically bulletproof** (Master's thesis).

Everything below is judged against these. The short verdict: the **data engineering and the objective-weighting machinery are solid**, but the pipeline as built answers a *different question* than the objective asks. It predicts **"where does transit already exist"** and **"which AGEBs resemble served areas,"** not **"where is there unmet demand"** or **"is this route optimal."** R1 is only partially served, R2 is essentially unaddressed (and undefined), and the one phase that would address them (Phase 7) rests on an algorithm — Steiner Tree — that optimizes the wrong thing.

---

## 1. Structural problems (these threaten the thesis core)

### 1.1 The Phase 2 target is circular: the model learns "where transit is," not "where it should be"

This is the single most important issue. In `src/balanced_station_selection.py`, the training labels are defined as:

- **Positive (label = 1, "suitable")** = AGEBs that **currently contain transit stops**.
- **Negative (label = 0, "unsuitable")** = **underserved** AGEBs (few/no stops).

So the supervised signal is, literally, *existing supply*. The model is trained to reproduce the current network's footprint. CLAUDE.md describes a "leakage fix" — dropping `stops_400m`, `stops_800m`, `min_stop_dist_m` as **features** — but that does not touch the deeper problem: the **label itself** is existing supply. Removing stop counts from the feature vector while keeping "has a stop" as the target only hides the tautology; it doesn't remove it.

Why this defeats R1: the objective wants to find **underserved, high-demand** areas. In this label scheme those areas are, by construction, the **negative class** — the model is being taught they are *unsuitable*. A high `score_rf` therefore means "looks like an already-served area," which is the opposite of a coverage gap. Using existing supply/ridership to infer where service *should* go is a known circularity that biases toward the status quo and is blind to **suppressed/latent demand** — demand that doesn't appear in the data precisely because no service exists to reveal it ([Litman, *Generated Traffic and Induced Travel*, VTPI](https://www.vtpi.org/gentraf.pdf); [latent-demand overview, ScienceDirect](https://www.sciencedirect.com/topics/engineering/latent-demand)).

**This needs to change.** The target must be decoupled from current supply (see §4.1).

### 1.2 "Optimal" is never defined — so R2 cannot be answered

R2 asks whether existing routes are *optimal*. Optimality is meaningless without an explicit objective function. The transit-network-design literature is unambiguous that this function is multi-objective: total user cost (in-vehicle time, wait, transfers), operator cost, and demand/coverage captured ([Multi-objective TNDP, arXiv 2201.11616](https://arxiv.org/abs/2201.11616); [Park et al. 2022, *J. Advanced Transportation*](https://onlinelibrary.wiley.com/doi/10.1155/2022/5887985)). Nowhere in Phases 1–6 is any optimality criterion, cost function, or demand-satisfaction metric defined. The Phase 7 plan proposes "inverse-suitability Dijkstra re-routing," but that is a heuristic move, not a definition of optimal. Without a formal objective, any claim that a segment is "sub-optimal" is unfalsifiable — a fatal problem for C2.

**Change:** write the objective function down first (§4.2). It is the spine R2 hangs on.

### 1.3 The pipeline scores *places*, but a route is about *flows between places*

Phases 2–5 produce a **static per-AGEB suitability surface**. Transit demand is a **flow** — an origin-destination (OD) problem. A route exists to connect O's to D's; a per-cell score in isolation cannot tell you *what to connect to what*. The TNDP is formulated on an OD matrix for exactly this reason ([Laporte/Mesa rapid-transit OD-capture](https://www.researchgate.net/publication/256088103_Rapid_transit_network_design_for_optimal_cost_and_origin-destination_demand_capture); [Park et al. 2022](https://onlinelibrary.wiley.com/doi/10.1155/2022/5887985)). The project has, in `data/encuesta_origen_destino/`, an OD survey it is deliberately not using (see §3.3). The result is a **site-suitability study wearing the label of a network-design study.** These are different problem classes, and the gap is where a committee will push hardest on C2.

### 1.4 Ridership dominates the model and is itself endogenous to existing service

In Phase 3, `v_ridership_annual_n` carries the **largest ensemble weight (0.20)** and is the **top SHAP driver** in both Phase 2 and Phase 5. But ridership only exists where service exists. The Phase 4 typology table makes this concrete: ridership is `0.0000` for Typologies A and C and `1.0000` for B — i.e., the "Vitality" dimension largely separates *"has SITEUR ridership records"* from *"doesn't."* The model's strongest signal is therefore a near-proxy for the current network. This compounds §1.1: the most influential variable cannot, by its nature, reveal demand in unserved areas — the very areas R1 targets.

### 1.5 Steiner Tree (Phase 7) optimizes construction cost, not transit quality

The planned route-synthesis step minimizes a Steiner Tree over the OSM graph. A Steiner Tree minimizes **total edge length to connect chosen terminals** — it is a *minimum-connection-cost* structure. It models **no passenger flows, no transfers, no frequencies, no OD satisfaction** — precisely the quantities that define a good transit network ([transfers/Pareto trade-offs in TNDP heuristics, MDPI Sustainability 2022](https://www.mdpi.com/2071-1050/14/17/11097); [multi-objective TNDP, arXiv](https://arxiv.org/abs/2201.11616)). Two further mismatches: (a) a tree is acyclic, but real networks need redundancy/loops; (b) the result is entirely determined by *which terminals you pick and what edge cost you assign* — and both of those (§3.1, §1.1) are the weakest, most arbitrary parts of the design. Steiner Tree can legitimately serve as a **connectivity sub-component**, but presenting it as *the optimizer* invites the committee to ask why an established demand-driven TNDP formulation (genetic algorithms, multi-objective heuristics, or the newer learned heuristics in [Holliday & Dudek 2025](https://www.tandfonline.com/doi/full/10.1080/21680566.2025.2561863)) was not used.

---

## 2. Serious methodological problems

### 2.1 Phase 5's perfect accuracy is a tautology, and is being reported as a success

Phase 5 reports RandomForest **Accuracy = 1.0000** (Precision/Recall/F1 all 1.0) and XGBoost ≈ 0.999. This is **not** evidence of a good model. The target is the **K-Means cluster label**, and the classifier is fed **the same features that generated those clusters.** Recovering a deterministic partition of its own inputs is expected — it demonstrates nothing about generalization or real-world predictive power. Presenting 1.0000 as a headline result in the synthesis report is a liability: a committee reads a perfect score as either leakage or a meaningless target. (Relatedly, the report's SHAP table shows the entire "Phase 3 Weight" column as `0.0000`, which looks like a broken join — a second integrity flag in the same table.)

**Change:** either drop the cluster-recovery framing, or repredict something *external* (e.g., held-out observed ridership, or a future network state) so the metric means something.

### 2.2 A dead indicator survived all the way to the synthesis report

`v_ntl_median_n` (VIIRS nighttime-lights median) is **mean 0.0000, std 0.0000, max 0.0000** across all 2,068 AGEBs (Phase 2 table) and `0.0000` for every typology (Phase 4 table). The feature is null/broken — it carries zero information and zero weight. Because it is **one of only two "Vitality" indicators**, the V dimension effectively collapses to ridership alone (which has its own problems, §1.4). So the advertised "16-indicator NPP-V framework" is, in practice, **15 indicators with a single-indicator Vitality axis.** This is a data-integrity failure that propagated through Phases 2–6 unflagged.

**Change:** repair the VIIRS ingestion (likely a raster CRS/nodata or join issue) or drop the feature honestly and restate the framework as having a one-proxy Vitality dimension.

### 2.3 The Node-Place framework is a *diagnostic*, not a route generator

Bertolini's Node-Place model (1996, 1999) was designed to **classify and diagnose the supply-demand balance of *existing* station areas** — it is an accessibility/equilibrium descriptor, not a network-design method ([Zhang et al. 2019, *J. Transport Geography*](https://discovery.ucl.ac.uk/id/eprint/10079372/7/Zhang_Network%20Criticality%20and%20the%20Node-Place-Design%20Model.%20Classifying%20metro%20station%20areas%20in%20Greater%20London_AAM.pdf); [node-place & ridership, ScienceDirect 2023](https://www.sciencedirect.com/science/article/pii/S0966692323002119)). Extending it to People + Vitality is reasonable and has precedent, but the framework's native job is *to classify places that already have transit*. Using NPP-V as the backbone of a system that *invents new corridors* is a conceptual stretch that the thesis must defend head-on, not assume. (The literature also notes NP's rail-centric bias and neglect of local modes — relevant because ZMG is bus-dominated.)

---

## 3. Moderate problems and arbitrary choices

### 3.1 Terminal selection and mode split are unjustified magic numbers
Phase 7 picks corridor terminals at `score_rf ≥ 0.75` (subway/BRT) and `≥ 0.55` (bus), using **AGEB centroids**. Two issues: (a) the thresholds have no stated derivation — the thesis will need a quantile/sensitivity justification (your own `phase7_research_prompt.md` flags this); (b) splitting **BRT vs. bus by a score threshold on a single surface has no capacity or ridership basis** — mode choice in practice follows corridor demand volume and cost, not a percentile of a composite index. Also prefer **population-weighted centroids** over geometric centroids, since AGEBs vary in size and internal population distribution.

### 3.2 The coverage filter is circular by the project's own admission
The plan excludes already-served AGEBs using `route_km_800m` — which is simultaneously the **top SHAP feature** of the suitability model. Using the same variable to both score suitability and define "already served" risks a closed loop. Your research prompt already names this; it needs an independent coverage definition (e.g., GTFS-derived headway/frequency access, not the model's own input).

### 3.3 Global Min-Max scaling on heavily skewed data
Phase 2 uses global Min-Max normalization. Several features are extremely right-skewed (e.g., `p_employment_proxy_n` mean 0.0385, `p_poi_density_n` mean 0.0380 — means far below the midpoint with max 1.0), meaning a handful of CBD outliers compress everyone else toward zero. This distorts **distance-based K-Means** and the **variance-based CRITIC/EWM weights** downstream. Consider log/robust scaling and report sensitivity.

---

## 4. What to change — prioritized

1. **Redefine the target away from existing supply.** Replace "has a stop / underserved" labels with a **demand-and-gap** target: estimate trip demand per AGEB (or AGEB pair), then define opportunity = *high demand ∧ low current supply*. Demand can come from the OD survey you already hold, or a gravity/accessibility model built from population, employment (DENUE), and land-use — explicitly **not** from current ridership. (Addresses §1.1, §1.4.)
2. **Write the objective function before doing anything else in Phase 7.** Something explicit and multi-objective: maximize demand-weighted coverage, minimize operator cost and transfer penalty, subject to detour/stop-spacing constraints. Only then can existing routes be *scored* and R2 answered ([arXiv 2201.11616](https://arxiv.org/abs/2201.11616); [Park 2022](https://onlinelibrary.wiley.com/doi/10.1155/2022/5887985)).
3. **Reframe Phase 7 as a (simplified) TNDP, not a Steiner Tree.** Keep Steiner/MST only as a connectivity scaffold; let the demand-driven objective from step 2 do the selecting. If keeping a heuristic, cite and contrast genetic-algorithm and learned-heuristic TNDP approaches so the choice is defended, not assumed.
4. **Fix data integrity now:** repair or drop `v_ntl_median`; fix the all-zero "Phase 3 Weight" column in the Phase 5 report. State the true number of live indicators. (Addresses §2.2, §2.1.)
5. **Stop reporting cluster-recovery as predictive skill.** Re-aim Phase 5 at an external target or reframe it honestly as a descriptive interpretability step. (Addresses §2.1.)
6. **Re-examine the "no surveys" constraint (R3).** Separate two things you are currently conflating: *subjective expert weighting* (rightly excluded — your CRITIC/EWM step is a genuine strength here) versus *measured travel-demand data*. An **Origin-Destination survey is a revealed-behavior measurement, not an opinion**, and OD data is the standard demand input across the entire TNDP literature. Banning it discards the most valid demand signal you have while keeping a circular ridership proxy. I'd relax R3 to "no subjective/expert-judgment inputs" and use the OD survey. If the constraint must stay, the thesis needs an explicit, defensible argument for why measured OD data is excluded.
7. **Define a validation strategy.** Ground truth for "future routes" doesn't exist, so adopt surrogate validation: backtest against the existing network (does the method recover known good corridors?), compare against **announced ZMG expansions** (Mi Macro Periférico / Línea 4/5), and report coverage and *population-served-per-km* metrics. Decide this *before* generating corridors, or §1.2 reappears at the defense.

---

## 5. What genuinely works — keep it

- **Data engineering and reproducibility.** Canonical CRS (EPSG:6372), GIST indexing, the raw→base→features schema separation, and single-source config are clean, professional, and replicable — strong support for C1's transferability claim.
- **Objective weighting (CRITIC + EWM).** This is the part of the project that *correctly* satisfies R3: indicator weights are derived from data structure, not expert judgment. Well chosen and well executed.
- **Leakage awareness exists.** Label-shuffle sanity checks and the (incomplete) feature-leakage fix show the right instincts — they just need to be pushed up to the label level (§1.1).
- **Equity is built into demand.** Including `marginación`/`rezago` means the framework rewards serving underserved populations — methodologically defensible and highly relevant to the Latin-American context (C1).
- **Appropriate open-data stack.** OSM, DENUE, INEGI census, GTFS, VIIRS are all replicable across LatAm cities, supporting the framework's portability ambition.

---

## 6. Bottom line

The project is a **well-built site-suitability and classification pipeline** that has been **framed as a route-optimization framework**. Those are different problems. As it stands it leans toward answering R1 weakly (biased toward the existing network) and does **not** answer R2 (no optimality definition). The fixes are not cosmetic but they are tractable: decouple the target from existing supply, introduce real (OD-based) demand, define an explicit objective function, and treat Phase 7 as a demand-driven network-design problem in which Steiner Tree is at most a sub-routine. Do those four things and the strong engineering foundation underneath actually becomes capable of supporting the objective the thesis claims.

---

## Sources

- Mumford et al. (2022). *On the Role of Multi-Objective Optimization to the Transit Network Design Problem.* arXiv:2201.11616. https://arxiv.org/abs/2201.11616
- Park, Kim & Sohn (2022). *Multiobjective Approach to the Transit Network Design Problem with Variable Demand considering Transit Equity.* J. Advanced Transportation. https://onlinelibrary.wiley.com/doi/10.1155/2022/5887985
- Laporte & Mesa et al. *Rapid transit network design for optimal cost and origin–destination demand capture.* https://www.researchgate.net/publication/256088103_Rapid_transit_network_design_for_optimal_cost_and_origin-destination_demand_capture
- Holliday & Dudek (2025). *Learning heuristics for transit network design and improvement with deep reinforcement learning.* Transportmetrica B. https://www.tandfonline.com/doi/full/10.1080/21680566.2025.2561863
- Demand-driven transit network design heuristic (2022). MDPI Sustainability 14(17):11097. https://www.mdpi.com/2071-1050/14/17/11097
- Litman, T. *Generated Traffic and Induced Travel.* Victoria Transport Policy Institute. https://www.vtpi.org/gentraf.pdf
- *Latent Demand — an overview.* ScienceDirect Topics. https://www.sciencedirect.com/topics/engineering/latent-demand
- Zhang et al. (2019). *Network Criticality and the Node-Place-Design Model: Classifying metro station areas in Greater London.* J. Transport Geography 79:102485. https://discovery.ucl.ac.uk/id/eprint/10079372/
- *The node-place model, accessibility, and station-level transit ridership* (2023). J. Transport Geography. https://www.sciencedirect.com/science/article/pii/S0966692323002119
