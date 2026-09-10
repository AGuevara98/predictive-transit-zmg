## Reviewer Role
Peer Reviewer 3 (Perspective / Cross-disciplinary)

## Reviewer Identity
Operations-research-trained transport-equity practitioner with network-design implementation experience at transit agencies in the Global South; brings a "would an agency actually use this" practical lens plus a Steiner-tree/network-design algorithmic angle.

## Overall Assessment
### Recommendation
Minor Revision

### Confidence (1-5)
4

### Summary Assessment
This is an unusually self-critical thesis for the genre: it documents its own generator's original failure mode, distinguishes reconstruction-of-built-lines from corridor-merit, and reports a transfer exercise honestly enough to flag where a backtest mechanism cannot transfer (bus-only networks). From my vantage point as an agency practitioner, four things give me pause: (1) the multi-objective function and mode-assignment logic have no capital-cost or right-of-way term; (2) the "diameter-trunk" shaper discards non-trunk MST branches by an unquantified magnitude; (3) the "equity and diagnostic priority are aligned" finding is a single-city result never re-tested where the transfer chapter's own caveat says the equity input is weaker; (4) the "hypotheses to be studied, not final alignments" hedge appears once while the specific "stand-out corridor" claim recurs at every level of the document with full numeric precision.

## Strengths

### S1 — The Question A/Question B distinction is a substantive epistemological contribution
`thesis/en/chapters/07_discussion.tex`, `sec:disc-twoquestions`.

### S2 — Transparent reporting of the generator's own negative history
`thesis/en/chapters/07_discussion.tex`, `sec:disc-generative`.

### S3 — The three-axis merit test (need, non-redundancy, demand/km) is operationally close to real corridor screening
`thesis/en/chapters/05_results.tex`, `sec:res-w6`.

### S4 — Honest identification of a precondition for the mask-and-reconstruct backtest, discovered via transfer rather than asserted a priori
`thesis/en/chapters/06_transferability.tex`, `sec:transf-validation`.

## Weaknesses

### W1 — No capital-cost or right-of-way dimension anywhere in the objective function or mode assignment
**Problem:** The multi-objective function scores on demand gain, route length, and equity; mode assignment is a pure demand-threshold rule. No proxy for construction cost, land acquisition, or grade-separation requirements appears anywhere.
**Evidence Anchor:** `equation:eq:objectives,eq:constraints`; Ch. 4 §4.6.
**Severity:** Major. **Confidence:** 4/5.
**Suggestion:** Add a coarse capital-cost/ROW proxy, or narrow Ch. 8's "defensible starting point for a feasibility study" language to say the framework informs *where*/*roughly what capacity*, leaving mode/alignment/cost to the feasibility study.

### W2 — The diameter-trunk shaper's demand/coverage trade-off is understated as "architectural" rather than quantified
**Problem:** Ch. 7 calls the residual limitation architectural and "now measured," and Ch. 8 says a hybrid shaper would "marginally improve coverage" — but no number is given anywhere for how much served-AGEB count or demand is discarded relative to a fuller Steiner/TSP solution.
**Evidence Anchor:** Ch. 7 §7.3; Ch. 8 §8.3.
**Severity:** Major. **Confidence:** 4/5.
**Suggestion:** Report the coverage/demand differential per generated group; consider engaging prize-collecting Steiner tree (PCST) formulations as the natural OR framing of this exact trade-off.

### W3 — "Equity and diagnostic priority are aligned" is a single-city finding never re-tested where the equity input is admittedly weaker
**Problem:** Ch. 7 §7.5 concludes ZMG's equity term and coverage gap "largely aligned," while Ch. 6 §6.5 separately notes the transfer cities' equity input is "an ordinal approximation... granularity coarser." No equivalent alignment check is reported for Toluca/Aguascalientes despite the machinery existing.
**Evidence Anchor:** Ch. 7 §7.5 vs. Ch. 6 §6.5; no corresponding statistic in §6.2-§6.3.
**Severity:** Major. **Confidence:** 4/5.
**Suggestion:** Compute and report the equity-score vs. coverage-gap correlation for both transfer cities, or scope the Ch. 7 conclusion to ZMG only.

### W4 — The "hypotheses to be studied" hedge is rhetorically contained to one sentence while the specific corridor claim is repeated at full precision
**Problem:** The hedge appears once (Ch. 8 §8.2); the W6_G02 numbers (12.1 km, 25 AGEBs, 192,357 trips/day, 56%, 73rd-percentile) recur in the abstract, Ch. 5, Ch. 7, and Ch. 8's RQ3 answer without a comparable local qualifier each time.
**Evidence Anchor:** Abstract para 3; Ch. 5 §5.5 "stand-out result"; Ch. 7 §7.3; Ch. 8 RQ3; Ch. 8 §8.2 (hedge, singular).
**Severity:** Major (by decision-impact — this is exactly the failure mode the recommendations section warns against). **Confidence:** 5/5.
**Suggestion:** Round headline demand figures where cited outside the results table; attach the qualifier the first time G02 is named in the abstract and in Ch. 7/8, not only in the recommendations.

### W5 — The route-audit-to-agency-action pathway understates the political economy of consolidating concessioned routes
**Problem:** Ch. 8's recommendation to use the route audit to flag routes "for review" reads as a direct engineering to-do list, but Toluca's 431/622 flagged routes sit within a ~30-operator concession system, where consolidation is typically a multi-year negotiation/buy-out problem.
**Evidence Anchor:** Ch. 8 §8.2; Ch. 6 §6.4 (30-operator system).
**Severity:** Minor. **Confidence:** 4/5.

## Questions for Authors

1. Have you computed an equity-score vs. coverage-gap alignment check for Toluca/Aguascalientes using the ordinal proxy already built for W4? If not run, would the ordinal compression preserve, weaken, or reverse the alignment?
2. Do you have a quantified figure — across all five generated groups — for how much served-AGEB coverage or demand the diameter-trunk shaper sacrifices relative to a full-terminal Steiner/TSP solution?
3. Was the 1.8 anchor-directness threshold validated against any external benchmark, or chosen to keep the observed feasible set stable?
4. Was any consideration given to how the "Redundant" flag's practical remedy differs between publicly-owned (SITEUR) and concessioned (Toluca) networks?

## Criterion-Bound Judgements

| Dimension | Judgement | Evidence anchor(s) | Rationale | Uncertainty/scope limit | Decision bearing? |
|---|---|---|---|---|---|
| Significance & Impact | PARTLY_MEETS | Ch. 4 §4.5-4.6; Ch. 8 §8.2 | Diagnostic layer's out-of-sample corroboration and transfer are genuinely significant; real-world agency impact bounded by absent cost/ROW dimension and a recommendations chapter that doesn't fully reckon with capital-planning/concession-politics realities. | Chapters 1-3 not reviewed by this seat. | Yes |
| Argument Coherence | PARTLY_MEETS | Ch. 7 §7.1-7.4; Abstract vs. Ch. 8 §8.2 | Core argument internally consistent; tonal incoherence between confidently repeated headline corridor claim and its single late-appearing hedge. | Full document not reviewed by this seat. | Yes |
| Methodological Rigor | NOT_ASSESSED | — | Out of scope. | — | No |
| Evidence Sufficiency | NOT_ASSESSED | — | Out of scope. | — | No |
| Literature Integration | NOT_ASSESSED | — | Out of scope. | — | No |
| Writing Quality | NOT_ASSESSED | — | Out of scope. | — | No |
| Originality | NOT_ASSESSED | — | Out of scope. | — | No |
