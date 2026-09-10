# Addendum: W6_G02 is Pareto-Dominated Under the Thesis's Own W5 Objective (2026-09-09)

Discovered while answering the user's question "what are the ramifications of moving to
weight-free Pareto exploration, and can we test it?" — not found by the original 5-seat
review panel, and more consequential than most of what was.

## What was found

Querying `features.route_candidates` for the raw W5 objective values ($f_1$ demand gain,
$f_2$ route km, $f_3$ equity) and independently recomputing Pareto dominance by hand
(cross-checked against the stored `pareto_rank` column — matched exactly):

| Corridor | $f_1$ | $f_2$ (km) | $f_3$ | Pareto rank | Feasible |
|---|---|---|---|---|---|
| W6_G00 | 0.301 | 7.32 | 0.338 | 2 | Yes |
| W6_G01 | 0.270 | 23.00 | 0.347 | 2 | Yes |
| **W6_G02** | **0.164** | 12.13 | **0.265** | **3** | Yes |
| **W6_G03** | **0.357** | **2.44** | **0.349** | **1** | Yes |
| W6_G05 | 0.125 | 5.40 | 0.271 | 2 | No |

**W6_G03 strictly dominates every other candidate — feasible or not — on all three
objectives simultaneously** (higher demand gain, shorter route, higher equity). **W6_G02
— the corridor the thesis repeatedly calls "the stand-out result" and builds its RQ3
answer around — is dominated twice over** (by W6_G00 and by W6_G03) and ranks *last*
among the four feasible corridors.

A full sweep of 231 alternative non-negative weight combinations for the composite score
(`composite = w1*f1_scaled + w2*efficiency + w3*f3`, 0.05 simplex grid) found **W6_G03
top-scoring under every single combination tested** — this is not a weight-sensitivity
question at all; it follows directly from strict Pareto dominance and would hold under
any monotonic weighting.

## Why this stayed invisible

`composite_score`, `total_score`, and `pareto_rank` are computed and stored in the
database, but **were never once shown or cited in the thesis's narrative text** before
this fix — not in the corridor table, not in the Pareto figure caption, not in the
"stand-out result" paragraph. The "stand-out" framing was based entirely on the separate,
threshold-based W8 merit tests (High-gap share, Jaccard non-redundancy, demand/km
percentile against the *existing network*), which measure genuinely different things than
the W5 objective functions they nominally sit alongside.

## Why it happens (mechanism, not a bug)

$f_1$ is a demand-*weighted average* unserved fraction over a corridor's served AGEBs — a
rate, not a total. W6_G03's five anchors are apparently uniformly high-gap, giving it a
high average despite carrying a fraction of W6_G02's absolute demand (35,784 vs. 192,357
trips/day). W6_G02 serves a demand-weighted *mix* of gap levels across 25 AGEBs, pulling
its average down even though it addresses far more total unmet demand. Whether a
per-unit-demand targeting rate or an absolute-coverage total is the right objective is a
genuine, previously unstated value choice — not an error in either metric individually.

## What was changed in the thesis

- **Ch.5 §5.6 (Results)**: added `tab:pareto-w5` (the table above) and a full disclosure
  of the disagreement between the merit tests and the W5 Pareto ranking, including the
  mechanism (rate vs. total) and the weight-sweep result.
- **Ch.7 §7.3 (Discussion, "generative layer" section)**: rewrote to state the disagreement
  explicitly as a second, independent limitation on top of the already-documented
  architectural one, and named the two ways to resolve it honestly (revise $f_1$ toward
  an absolute-coverage term, or present both corridors under their respective favored
  lens rather than picking one silently).
- **Ch.8 RQ3 answer**: added the same disclosure, softened "its single headline corridor"
  to "either of its headline corridors."
- Recompiled and verified clean (61 pages, zero unresolved references).

## What was *not* changed

This finding does not overturn the diagnostic layer (W1–W4) or the transferability
results, and does not mean W6_G02 is a *bad* corridor — it still passes the merit tests on
its own terms, and 192k trips/day of absolute demand addressed is not nothing. What it
does mean is that the thesis's own formal multi-objective function, if taken at face
value, recommends a different corridor (the 2.4 km stub) than the one the thesis's prose
has been building its central generative-layer claim around — and the thesis did not
previously disclose this, because it never showed the reader the objective values that
would have revealed it.

## Follow-up (same session): the disagreement is now diagnosed and resolved, not just disclosed

The user asked "if they don't agree, which is best to select?" — tested rather than
argued. $f_1$ is a demand-weighted **average** unserved fraction (a rate); this
mechanically favors small, homogeneous corridors over larger ones spanning heterogeneous
territory, independent of actual merit. The tell: W6_G03 won under **every one** of 231
tested objective weightings — a genuine multi-objective trade-off should not produce a
candidate that dominates outright regardless of weights.

**Implemented and tested** (not just argued): added an additive `f1_total` field to
`ObjectiveResult` (`src/w5_types.py`, `src/w5_objective.py` — the absolute, un-normalized
version of the same numerator, `weighted_gain` before dividing by total demand). Re-ran
the real `evaluate_objective`/`build_route_candidate` code path (not a reimplementation)
against the live corridor geometries. Result: **the unanimous winner disappears** — all
four feasible corridors become mutually Pareto-non-dominated under the absolute-coverage
formulation ($f_1^{\text{tot}}$ = 19,873 / 26,100 / 31,608 / 12,791 for G00/G01/G02/G03).

This is a better resolution than either "pick a winner" or "leave it unresolved": the
real choice the generator presents is a **scale-versus-targeting-purity trade-off** —
G02/G01 address far more absolute unmet demand; G03 is the most demand-efficient per km
but on a corridor an order of magnitude smaller. Recommending G02 as the headline result
remains defensible (absolute impact is the more decision-relevant criterion for a single
flagship capital investment) but the thesis now says so explicitly instead of leaving an
uninspected rate metric implying the two evaluation lenses simply agreed.

**Thesis updated**: Ch.4 (`eq:f1-total`, formal definition), Ch.5 (`sec:res-w6`, the real
test numbers and Pareto-front result), Ch.7 (`sec:disc-generative`, mechanism +
recommendation), Ch.8 (RQ3 answer, from "not yet reconciled" to "now reconciled").
Verified: 57/57 existing W5/W7 tests still pass (the new field is additive with a default,
does not touch `f1_demand_gain`, `composite_score`, or any W7 audit threshold). Recompiled
clean (62 pages, zero unresolved references).

## Circularity citations (separate, smaller fix per the same request)

Deepened the circularity argument (Ch.1 §1.2, Ch.2 §2.5) with three additional verified
citations spanning three literatures:
- **Kaufman, Rosset, Perlich & Stitelman (2012)**, "Leakage in Data Mining" — the
  data-mining-native term for exactly this failure mode, grounding the thesis's own
  repeated "no leakage" language.
- **Lakkaraju, Kleinberg, Leskovec, Ludwig & Mullainathan (2017)**, "The Selective Labels
  Problem" — the precise statistical formalization: an outcome observed only conditional
  on a prior decision cannot be used to recover the counterfactual for the alternative
  decision. The single most on-point citation found for this argument.
- **Flynn, Guha, Majumdar, Srivastava & Zhou (2022)**, "Towards Algorithmic Fairness in
  Space-Time" — a spatio-temporal-fairness position paper (arXiv, explicitly flagged as
  not peer-reviewed) naming the same risk for spatial infrastructure allocation
  specifically.
- Retained Lum & Isaac (2016) and Ensign et al. (2018) (predictive policing) as the
  closest applied precedent.

The thesis's circularity argument now spans: the general ML term (leakage) → the precise
statistical formalization (selective labels) → the closest applied domain analogy
(predictive policing) → a spatial-infrastructure-specific framing (Flynn et al.). This is
a substantively stronger grounding than the single loose predictive-policing analogy from
the previous pass.
