# Editorial Decision — Thesis Review (2026-09-09)

Simulated 5-perspective academic review (Journal-Fit / Methodology / Domain / Perspective /
Devil's Advocate) of the complete English thesis (`thesis/en/`), run via the
`academic-paper-reviewer` skill's methodology. Each seat was a fresh, independently-dispatched
subagent reading the thesis directly, blind to the other seats' output at commit time.

**Provenance caveat:** this session did not have the skill's full sprint-contract /
cryptographic panel-provenance tooling wired (no `scripts/check_phase_conformance.py`, no JSON
contract templates, no SHA-256 provenance artifact). Role-separation and blindness across the
five seats are real; cross-model diversity and machine-verified provenance are not — treat
cross-seat corroboration as convergent independent readings, not proof of independent error
processes.

Two Devil's Advocate CRITICAL findings and one Domain-reviewer CRITICAL finding were
independently verified by the orchestrating session directly against primary sources
(`references.bib` and the project's own `CLAUDE.md` W8 records), not merely taken on the
sub-reviewer's word.

---

## Decision: **Major Revision**

## Blocking Issues (3, in order of committee/desk-review salience)

| # | Blocking issue | Source(s) | Evidence anchor | Verified? |
|---|---|---|---|---|
| 1 | Two of the most theoretically load-bearing bibliography entries (`liu2024nprv` — the paper the thesis's entire NP-RV→NPP renaming is built on; `niu2023rf` — anchors the RF-siting claim) are literal unfinished placeholders: `author = {Liu, and others}`, `note = {Placeholder entry -- complete with final citation details}`. | Domain reviewer (W2) | `thesis/common/references.bib` lines 27–42 | **Yes — confirmed verbatim by the orchestrating session.** |
| 2 | The flagship generated corridor (W6_G02), presented in the abstract/results/discussion/conclusions as the single result redeeming the entire generative layer, is reported as "non-redundant" using only the AGEB-set Jaccard figure (0.18). The project's own W8 record shows a second redundancy metric — 42% shape-proximity overlap with existing premium route MP-C03 — internally flagged as warranting "a mild caveat on the 'unique corridor' framing," undisclosed anywhere in the thesis text. | Devil's Advocate (CRITICAL #4) | `absence:` ch. 5 §5.6 — checked §5.6, ch. 7 §7.3, ch. 8 RQ3; no mention of the 42% figure | **Yes — confirmed against the project's own W8 records (CLAUDE.md).** |
| 3 | The abstract/RQ4 headline claim ("genuinely portable rather than bespoke to ZMG") is not fully supported by Ch. 6 on its own terms: no local β calibration, one of three W8 validation legs (the hold-out backtest) categorically does not run for either transfer city, and all three cities draw on the same national (Mexico-only) data ecosystem. | Journal-Fit (W1), Devil's Advocate (#9, #10), Perspective (implicit) | `text:` abstract "genuinely portable" vs. `text:` ch. 6 §6.5 "does not transfer to a bus-only network" | Cross-checked directly against thesis text; converged on independently by three seats. |

## Reviewer Summary

| Reviewer | Recommendation | Confidence |
|---|---|---|
| Journal-Fit (EIC) | Major Revision | 4/5 |
| R1 — Methodology | Minor Revision | 4/5 |
| R2 — Domain | Major Revision | 4/5 |
| R3 — Perspective | Minor Revision | 4/5 |
| Devil's Advocate | N/A (findings only) — 4 CRITICAL, 8 MAJOR, 3 MINOR | — |

## Consensus Analysis

**CONSENSUS-4/5 — genuine strengths, cited independently by every seat:**
1. The diagnostic layer's out-of-sample corroboration (SITEUR Line 4) and the honest
   Question-A/Question-B distinction (agreement-with-built-lines is a weak proxy for merit) are
   real, citable methodological contributions.
2. The thesis's self-disclosure of its own history (the retired "essentially negative" generator
   verdict, the data-integrity errata) is unusually candid.

**CONSENSUS-4/5 — the claim-calibration problem, converged on independently from four angles:**
The abstract/introduction/conclusions state claims more confidently than the body supports:
transferability ("genuinely portable" — EIC W1, DA #9/#10), the generator's redemption
narrative (built on n=1 clearly-passing corridor plus one degenerate stub — R1 W4, R3 W4, DA
#5/#6, EIC W2), and novelty framing (R2 W1/W5).

## Points of Disagreement

**Disagreement 1 — does the frontier-anchor/connectivity-gain-factor design readmit the
circularity RQ3 claims to eliminate?**
- DA (CRITICAL #1): anchors restricted to within 400m of existing stops + 2.5x objective credit
  for connecting to the existing network is the same circularity the introduction claims to break.
- **Editor's resolution:** Partially validated. The DA's framing conflates *physical connectivity*
  (an engineering requirement — new lines need a boarding/transfer point) with *route-level
  redundancy* (does the corridor spatially duplicate an existing one — screened by the Jaccard
  test, which the merit-passing corridor scores low on, 0.18). The real defect is that the thesis
  never distinguishes these two senses in the text, not that circularity has silently returned.
  **Downgraded to Major**: add the distinguishing paragraph + a one-sided sensitivity check on
  how much the κ credit shifts corridor selection.

**Disagreement 2 — is using route-overlap as confirmatory evidence in both directions
(low overlap = good in the benchmark; overlap-or-no-overlap = weak evidence either way in the
reconstruction discussion) an inconsistency or two legitimately different tests?**
- DA (CRITICAL #2): same evidence class, contradictory epistemic treatment.
- **Editor's resolution:** These are technically two different sub-tests (spatial-overlap-with-
  premium-routes vs. recall-of-masked-routes), which softens the direct-self-contradiction charge.
  The underlying point survives in weaker form: no *ex ante* criterion is stated for what result
  would count as adverse evidence for either test. **Downgraded to Major**: state the ex-ante
  falsification criterion for each validation leg.

**Disagreement 3 — overall severity band.** R1/R3 said Minor, EIC/R2 said Major, DA raised 4
CRITICALs. **Resolution: Major Revision** — two of the DA's CRITICALs were independently
confirmed by the orchestrating session against primary sources, which is blocking regardless of
R1/R3's narrower-scoped recommendations.

## Decision Rationale

The diagnostic layer (W1–W4, corroborated out-of-sample by Line 4) is a genuinely strong,
well-evidenced contribution that no reviewer disputed and that should not be substantially
reworked. Major (not Minor) Revision is required because three independently-checkable defects
were confirmed directly by the orchestrating session rather than taken on any single seat's
word: two central citations are unfinished placeholders, the flagship generated corridor's
"non-redundant" claim omits a contrary metric the project's own pipeline already computed, and
the transferability claim in the abstract is calibrated well above what Chapter 6's own stated
caveats support. None require new data collection or a redesigned pipeline — they are
disclosure, citation-completion, and claim-calibration fixes — but are exactly what a defense
committee or journal desk review would flag first.

## Required Revisions (Must Fix)

| Ref | Item | Source | Severity |
|---|---|---|---|
| R1 | Complete/replace the `liu2024nprv` and `niu2023rf` bibliography entries with verified citation details. | Domain, verified | Critical |
| R2 | Disclose the 42% MP-C03 shape-overlap figure for W6_G02 alongside the 0.18 Jaccard figure; soften "unique corridor" framing accordingly. | Devil's Advocate, verified | Critical |
| R3 | Rescope abstract/introduction/conclusions transferability language to what Ch. 6 actually supports. | EIC, DA, Perspective | Major |
| R4 | Distinguish "must connect to the network" from "must not duplicate the network"; report a sensitivity check on the κ=0.50/0.20 connectivity credit. | Devil's Advocate (adjudicated) | Major |
| R5 | Report the CV/train-test split methodology for the coverage-gap retrain; add an ablation/baseline isolating the population↔demand mechanical-link concern. | R1, DA #12 | Major |
| R6 | Report R² for the β=2.0 baseline in the calibration table (currently only RMSE), and n; contextualize R²=0.2498. | R1, DA #13 | Major |
| R7 | Report anchor-directness vs. endpoint-detour side by side for the full candidate set (ZMG + transfer cities). | R1, R3, DA #6/#7 | Major |
| R8 | Add a capital-cost/ROW proxy, or explicitly narrow the "feasibility-study-ready" language in Ch. 8. | Perspective (W1) | Major |
| R9 | Provide a theoretical (not only data-availability) justification for NPP-V→NPP, or revert the name. | Domain (W1) | Major |
| R10 | Cite and distinguish from the closest adjacent literature (candidates: Foth, Manaugh & El-Geneidy 2013; Camporeale, Caggiani & Ottomanelli 2019; Papa & Bertolini 2015 — verify before citing). | Domain (W5) | Major |
| R11 | Test whether "equity and diagnostic priority are aligned" replicates in the transfer cities, or scope the claim to ZMG. | Perspective (W3) | Major |
| R12 | Add an uncertainty qualifier to the Line 4 out-of-sample claim (n=1, no CI/significance test given). | Devil's Advocate #3 | Major |

## Suggested Revisions (Should Fix)

- S1: Report top-N list churn across α (not only aggregate Spearman ≥0.98).
- S2: Report $w_e, w_p, w_r$ attraction weights explicitly.
- S3: Add sensitivity/derivation notes for other fixed thresholds (gap quintile cutoffs, stop
  spacing, mode-assignment demand thresholds).
- S4: Quantify demand/coverage discarded by the diameter-trunk shaper vs. a full Steiner/TSP
  alternative.
- S5: Acknowledge route-redundancy rationalization in concessioned systems is a political-economy
  problem, not only a scheduling one.
- S6: Add one sentence up front distinguishing new constructions from recombined established
  techniques among the four contributions.

## Revision Roadmap

- [ ] R1 — Critical — complete/replace two placeholder bib entries
- [ ] R2 — Critical — disclose W6_G02's 42% MP-C03 overlap
- [ ] R3 — Major — rescope transferability language
- [ ] R4 — Major — distinguish connectivity from redundancy; sensitivity-check κ
- [ ] R5 — Major — report CV/split methodology + leakage ablation
- [ ] R6 — Major — report baseline R² and n in calibration table
- [ ] R7 — Major — anchor-directness vs. endpoint-detour, full candidate set
- [ ] R8 — Major — add cost/ROW proxy or narrow deployment claim
- [ ] R9 — Major — justify or reverse the NPP-V→NPP rename
- [ ] R10 — Major — cite/distinguish from adjacent integrative literature
- [ ] R11 — Major — test equity/gap alignment in transfer cities
- [ ] R12 — Major — quantify uncertainty on the Line 4 corroboration
- [ ] S1–S6 — should-fix items above
