## Reviewer Role
Peer Reviewer 1 (Methodology)

## Reviewer Identity
Transportation modeler specializing in gravity-model calibration, Furness/IPF balancing, and machine-learning validation design (leakage detection, SHAP interpretation) for spatial ML pipelines.

## Overall Assessment
### Recommendation
Minor Revision

### Confidence (1-5)
4

### Summary Assessment
This is a methodologically self-aware thesis that does something rare in the ML-for-transit-siting literature: it names its own weakest inferential move (Question A vs. Question B) and reports results that cut against the authors' preferred narrative (W6_G00/G01 as "lower-efficiency connectors," the Toluca backtest collapsing to zero re-proposed corridors). The demand-estimation (W1), calibration (W2), and diagnostic (W3/W4) chain is competently specified, and the three-city transfer (Ch. 6) is a genuine and fairly executed test of RQ4. That said, four specific claims are asserted with more confidence than the presented evidence supports: (1) the calibration "improves fit on every metric" when the comparison table only reports RMSE for the prior model, not R²; (2) "no leakage" in the coverage-gap retrain is stated rather than demonstrated against the specific channel by which the target's construction overlaps with a top-ranked predictor (employment/population); (3) the mask-and-reconstruct backtest works in exactly one of three cities studied; (4) anchor-directness replaces endpoint-detour on the strength of a single worked example (W6_G02). None invalidate the thesis's central claims, but each should be substantiated further or the surrounding language softened.

## Strengths

### S1 — Explicit, falsifiable distinction between reconstruction and merit validity
`text:` Ch. 7 §"Two questions, two layers" (`sec:disc-twoquestions`).

### S2 — Genuine out-of-sample corroboration
`text:` Ch. 5 §"Out-of-sample corroboration" (`sec:res-w8`); `text:` Ch. 8 RQ2 answer.

### S3 — Honest, non-cherry-picked reporting of mixed corridor results
`table:` `tab:corridors`; `text:` Ch. 5 §`sec:res-w6` final paragraph.

### S4 — Reported sensitivity analysis for the equity weight
`equation:` `eq:final`; `text:` Ch. 5 §`sec:res-w4`.

### S5 — Transparent documentation of upstream data-integrity defects
`text:` Ch. 3 §`sec:area-integrity`.

### S6 — Full-pipeline transfer through one parameterized code path
`table:` `tab:transfer-diag`; `text:` Ch. 6 §`sec:transf-diagnosis`.

## Weaknesses

### W1 — "Improves fit on every metric" is not verifiable from the presented comparison
**Problem:** Table `tab:calibration` reports R² only for the calibrated model (baseline row shows "--"), so the "every metric" framing cannot be checked from the table given. R²=0.2498 also means roughly three-quarters of log-space variance in observed zonal flows is unexplained, a fact not discussed in terms of what it implies for everything built on top of the demand surface. Sample size (n zone pairs) is not reported.
**Evidence Anchor:** `table:tab:calibration`; `text:` Ch. 4 §`sec:w2`; `text:` Ch. 5 §`sec:res-w2`.
**Severity:** Major. **Confidence:** 4/5.
**Suggestion:** Report R² for the β=2.0 prior, report n, and contextualize R²=0.25 against typical gravity-model calibration fits.

### W2 — "No leakage" is asserted, not demonstrated against the specific plausible channel
**Problem:** Employment density is present, in different guises, on both sides of the target's construction (accessibility denominator via `eq:accessibility`, attraction/demand numerator via `eq:attractions`) and among the 14 predictors (`p_employment_proxy`, a top-3 SHAP driver). The stated exclusion (dropping `route_km_800m`, `stops_*`) addresses only the most obvious leakage form, not this subtler structural echo. No ablation, permutation-importance check, or spatial-vs-random split methodology is reported.
**Evidence Anchor:** `equation:eq:gap,eq:accessibility,eq:attractions`; `table:tab:retrain`; `text:` Ch. 4 §`sec:w3`; `text:` Ch. 7 §`sec:disc-diagnostic`.
**Severity:** Major. **Confidence:** 4/5.
**Suggestion:** Report the CV/split scheme, an ablation isolating the employment-proxy SHAP contribution, and ideally a spatially-blocked re-evaluation of PR-AUC/ROC-AUC.

### W3 — The strongest validation instrument works in only one of three studied cities, and overlap is interpreted favorably in both directions
**Problem:** The mask-and-reconstruct backtest runs in ZMG (15.0% overlap, "expected and desired") but collapses in Toluca and is N/A in Aguascalientes. Separately, the benchmark test is read as favorable when overlap is low (ZMG 10.5%: under-served areas identified) and also favorable when overlap is high (Toluca 75.0%, Aguascalientes 54.3%: "revealed-preference corroboration"). No ex-ante criterion states what overlap would count as adverse evidence.
**Evidence Anchor:** `text:` Ch. 6 §`sec:transf-validation`; `text:` Ch. 7 §`sec:disc-reconstruction`.
**Severity:** Major. **Confidence:** 4/5.
**Suggestion:** State explicitly that the backtest's operative n is 1/3 cities; state ex-ante what overlap range would be adverse for the benchmark, or reframe it as descriptive.

### W4 — Anchor-directness as a feasibility metric is justified by a single worked example
**Problem:** The switch from endpoint-detour to anchor-directness is motivated entirely through one corridor (W6_G02), the same corridor that becomes the thesis's headline generative result. No broader comparison across the full candidate set (including transfer cities, where the raw material already exists per `tab:transfer-corridors`) demonstrates general superiority rather than a metric that happens to reclassify this specific case. The denominator ($\ell_{\text{span}}$) is also endogenous to the same pipeline's anchor-selection step.
**Evidence Anchor:** `text:` Ch. 7 §`sec:disc-generative`; `equation:eq:constraints`; `text:` Ch. 4 §`sec:w6`.
**Severity:** Major. **Confidence:** 4/5.
**Suggestion:** Report anchor-directness vs. endpoint-detour side-by-side for the full candidate set across all three cities.

### W5 — Trip-generation constants and attraction weights are asserted, not calibrated, despite survey data that could calibrate them
**Problem:** $\tau=2.5$, $\gamma=0.10$, and $w_e,w_p,w_r$ are fixed constants; the EOD survey appears to carry information (zone-level productions/attractions) that could check them, but calibration is reported for β only.
**Evidence Anchor:** `equation:eq:productions,eq:attractions`; `text:` Ch. 3 §`sec:area-sources`.
**Severity:** Minor. **Confidence:** 3/5.

### W6 — Several structural thresholds lack derivation or sensitivity analysis
**Problem:** Gap-category quintile cutoffs, W5 constraint constants, and W6 mode-assignment thresholds are fixed values with no cited empirical basis, in contrast to the reported α and directness-cap sensitivity checks.
**Evidence Anchor:** `text:` Ch. 4 §`sec:w3`; `equation:eq:constraints`; `text:` Ch. 4 §`sec:w6`.
**Severity:** Minor. **Confidence:** 3/5.

## Questions for Authors

1. What is n underlying R²=0.2498, and what is the corresponding R² for the β=2.0 baseline?
2. Was the coverage-gap retrain's train/test split spatial or random, and what specific check substantiates "no supply-side leakage" beyond excluding explicit route/stop columns?
3. Was anchor-directness benchmarked against endpoint-detour across the full candidate set, including transfer cities?
4. What would a bus-only-network-compatible hold-out design look like, given the Toluca/Aguascalientes backtest failure?

## Criterion-Bound Judgements

| Dimension | Judgement | Evidence anchor(s) | Rationale | Uncertainty/scope limit | Decision bearing? |
|---|---|---|---|---|---|
| Methodological Rigor | PARTLY_MEETS | `equation:eq:gravity,eq:furness`; `table:tab:calibration`; `text:Ch.7 sec:disc-generative`; `text:Ch.4 sec:w3` | Core IPF mechanics sound; several load-bearing claims rest on incomplete or single-example evidence relative to prose. | Text-only assessment; code/DB not inspected. | Yes |
| Evidence Sufficiency | PARTLY_MEETS | `text:Ch.5 sec:res-w8`; `table:tab:transfer-diag`; `text:Ch.6 sec:transf-validation`; `text:Ch.7 sec:disc-reconstruction` | Diagnostic layer's evidence is strong; generative layer's evidence thinner than its framing suggests in three specific places. | Same bound. | Yes |
| Originality | NOT_ASSESSED | — | Out of scope. | — | — |
| Literature Integration | NOT_ASSESSED | — | Out of scope. | — | — |
| Writing Quality | NOT_ASSESSED | — | Out of scope. | — | — |
| Significance & Impact | NOT_ASSESSED | — | Out of scope. | — | — |
