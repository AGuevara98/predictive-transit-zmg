# Literature Review — Is the Methodology Applied Correctly? (2026-09-09)

Follow-up to the 5-perspective review (`00_editorial_decision.md` and seat reports in this
directory). Scope: for each major methodological component of the thesis, find real,
comparable published work and assess whether the thesis's application is consistent with
established practice, a defensible variant, or an unsupported/novel claim. All citations
below were verified via web search before being added to `thesis/common/references.bib`
and cited in the thesis text; none are invented.

**Action taken per the user's instruction:** `liu2024nprv` (the "NP-RV" citation) could not
be verified against any real paper matching its title/author/venue/year after an extended
search. It has been **deleted** from `references.bib` and from both in-text citations
(literature review §2.1 and §2.5), replaced by two verified real papers covering the same
conceptual ground.

---

## 1. Demand estimation (doubly-constrained gravity model, Furness IPF)

**Verdict: Correctly applied, textbook standard.** The four-step tradition
(McNally 2000, Ortúzar & Willumsen 2011), Wilson's (1971) entropy-maximizing gravity form,
and Furness (1965) iterative proportional fitting were already correctly cited. No new
literature changes this assessment — this is the single most conventionally/soundly
applied component of the pipeline. (The separate, real problem found earlier — the
calibration's non-reproducibility on re-run — is a data/engineering issue, not a
methodological-correctness one; see `00_editorial_decision.md` R6 and the Ch.7 limitations
entry.)

## 2. Coverage-gap / demand-vs-supply "need index" diagnostic

**Verdict: Correctly applied and well-grounded in an established sub-literature — better
grounded than the original text let on.** Found:
- **Al Mamun & Lownes (2011)**, "Measuring Service Gaps: Accessibility-Based Transit Need
  Index" (*Transportation Research Record* 2217) — a near-exact structural antecedent: a
  transit-need index compared against an accessibility index at fine spatial resolution to
  identify gaps. This is closer to the thesis's construction than either of the two sources
  already cited (Jiao 2013 "transit deserts"; Currie 2010 social-need gaps), and was
  missing. **Added** to §2.3 (`sec:lit-accessibility`).
- This confirms the "need index vs. accessibility index → gap" comparison structure is
  standard practice, not novel. The thesis's actual contribution here (correctly
  identified in Ch.2's own research-gap section, strengthened per the R10 fix from the
  prior review round) is feeding the resulting gap forward as a supervised-learning
  target, not the gap construction itself.

## 3. The "circularity" critique of ML-based transit siting

**Verdict: The critique is correct and important, but was previously self-contained and
under-cited — this is the most valuable finding of this pass.** No transit-planning
literature was found that names this exact failure mode under a specific term (the thesis
appears to be arguing it somewhat originally within this sub-field). However, the
*identical logical structure* — a model trained on where an intervention already occurred
reproduces that pattern rather than detecting genuine underlying need — is rigorously
formalized in the predictive-policing/algorithmic-fairness literature:
- **Lum & Isaac (2016)**, "To Predict and Serve?" (*Significance* 13(5)) — first
  widely-cited demonstration.
- **Ensign, Friedler, Neville, Scheidegger & Venkatasubramanian (2018)**, "Runaway
  Feedback Loops in Predictive Policing" (PMLR 81) — formal urn-model treatment proving
  the mechanism and its severity as a function of area-level disparity.

**Added** to Ch.1 §1.2 (`sec:intro-circularity`) and Ch.2 §2.5 (`sec:lit-ml`). This
materially strengthens the thesis's central methodological argument by anchoring it in a
mature, rigorously-formalized literature rather than leaving it as an ad hoc observation
about this one pipeline's own history.

## 4. CRITIC + Entropy Weight Method combined objective weighting

**Verdict: Correctly applied as a recognized combination — but the prior review's "oversold
objectivity" concern is independently confirmed by real critical literature.** Found
multiple real papers combining CRITIC + Entropy for MCDA (particularly in transport-
sustainability evaluation), confirming this is an established, not idiosyncratic,
combination. More importantly, found:
- **Mukhametzyanov (2021)**, "Specific Character of Objective Methods for Determining
  Weights of Criteria in MCDM Problems: Entropy, CRITIC, SD" (*Decision Making: Applications
  in Management and Engineering* 4(2)) — a direct comparative critique showing these
  "objective" methods are not always well-behaved.

**Added** to §2.4 (`sec:lit-mcda`), directly supporting the qualification already added
to that section in the previous review round (that CRITIC/EWM removes expert judgment from
the final aggregation step only, not from the upstream indicator/normalization/taxonomy
choices).

## 5. Node-Place extension with an added dimension (the deleted `liu2024nprv`)

**Verdict: fixed per instruction.** No real "Liu et al. (2024)" NP-RV paper could be
located. Two verified real substitutes, covering the same "augment Node-Place with an
outcome variable + interpretable ML" pattern, were identified and added:
- **Su, Wang, Li & Kang (2022)**, *Journal of Transport Geography* 104 — extended
  Node-Place + SHAP + ridership (closest match to the deleted citation's conceptual claim).
- **Amini Pishro et al. (2022)**, *Scientific Reports* 12 — a Node-Place-Ridership-**Time**
  (not Vitality) framework, K-means/Cube classification.

Neither paper uses a "vitality" term specifically alongside ridership, so the thesis's
§2.1 framing was rewritten (not merely re-cited) to describe what these two real papers
actually do, rather than asserting an unverified third formulation existed.

## 6. MST/Steiner-tree corridor-generation heuristic

**Verdict: Correctly applied, standard heuristic family, with continued real-world
precedent.** Takahashi (1980) and Kou-Markowsky-Berman (1981), already cited, are exactly
the classical Steiner-tree approximation family the thesis draws on; this is textbook
network-design heuristics, correctly characterized as NP-complete-with-heuristics in
Ch.2. Found one additional, current data point:
- **Sugiura et al. (2026)**, "Urban Transit Network Design Using Spanning Tree: A Case
  Study of Canberra Transit Network" (arXiv preprint) — a tabu-search-refined spanning
  tree applied to a real bus network in 2026, confirming the heuristic family remains in
  active use. **Cited explicitly as a preprint**, not a peer-reviewed authority, since
  that is what it is.
- **Kepaptsoglou & Karlaftis (2009)**, "Transit Route Network Design Problem: Review"
  (*Journal of Transportation Engineering* 135(8)) — the canonical TNDP review, missing
  from the original bibliography alongside the two reviews already cited (Guihaire & Hao
  2008; Farahani et al. 2013). **Added** as the standard classification reference for the
  thesis's own W5/W6 approach.

## 7. Multi-objective evaluation function (weighted composite + Pareto ranking)

**Verdict: A defensible but somewhat dated hybrid relative to current best practice — a
real, citable gap, not previously flagged.** The TNDP literature has moved increasingly
toward many-objective Pareto exploration that avoids imposing fixed weights on the
objectives at all. This thesis's W5 function still computes a fixed-weight composite score
($0.50 f_1 + 0.25\,\text{efficiency} + 0.25 f_3$) *alongside* genuine Pareto ranking, rather
than relying on the Pareto front alone. This is not wrong — both are reported, and a fixed
composite is easier to communicate to a planning agency — but it is a step behind the
field's more recent weight-free formulations. **Added** as an explicit positioning note in
§2.6 (`sec:lit-network`), so the thesis states its own position on this axis rather than
implying its approach is at the frontier of multi-objective TNDP methodology.

## 8. Validation methodology (masked-reconstruct backtest, benchmark overlap, before/after)

**Verdict: No established precedent found — this appears to be a genuinely original
validation design, which is fine, but should be read as exactly that.** Searches for
hold-out or masked-reconstruction validation designs specifically for *generative* transit
network design (as opposed to standard train/test splits for predictive models, which are
common and unrelated) turned up nothing resembling this thesis's specific design (mask an
existing premium tier, recompute the diagnostic without it, re-run the generator, measure
shape overlap with the masked-out routes). This is consistent with — and reinforces — the
thesis's own Ch.7 "Question A vs. Question B" framing, which already argues this kind of
reconstruction test is a weak, self-invented proxy for corridor merit rather than an
externally validated methodology. **No thesis change made here**: the existing Ch.7 framing
already characterizes this honestly; this literature-review pass simply confirms there was
nothing missing to cite because there is no established methodology of this kind to cite
against.

---

## Overall Assessment

The **diagnostic layer** (demand estimation, coverage-gap construction, the circularity
critique, CRITIC/EWM weighting) is correctly applied relative to established practice in
every component checked, and in one respect (the circularity argument) was previously
*under*-supported by citation rather than incorrect — it is now grounded in a more
rigorous, mature analogous literature (predictive-policing feedback loops) than the
thesis originally drew on. The **generative layer** (MST/Steiner corridor generation) uses
a correctly-characterized, standard heuristic family with continuing real-world precedent,
though its multi-objective scoring is a defensible hybrid rather than a state-of-the-art
weight-free formulation, now noted explicitly. The **validation layer**'s masked-backtest
design has no established precedent in the literature searched — it is original to this
thesis, which is consistent with, not contradicted by, the thesis's own already-honest
framing of that design's limits.

**Bibliography changes:** 1 unverifiable entry deleted (`liu2024nprv`); 7 new verified
entries added (`aminipishro2022nprt`, `ensign2018runaway`, `lum2016predict`,
`mukhametzyanov2021critic`, `almamun2011servicegaps`, `kepaptsoglou2009review`,
`suguira2026spanningtree`), all with DOIs/arXiv IDs where available and explicit
preprint-status flagging where applicable (`suguira2026spanningtree`).

**Recompiled and verified:** `thesis/en/main.tex` builds cleanly after all changes (56
pages, zero unresolved citations/references in the final pass).
