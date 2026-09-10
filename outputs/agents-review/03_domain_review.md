## Reviewer Role
Peer Reviewer 2 (Domain)

## Reviewer Identity
Urban planning scholar working in the Node-Place tradition and Latin American BRT/transit-oriented-development literature, familiar with Bertolini's Node-Place model, CRITIC/EWM objective-weighting methods, and the transit-desert / social-need-gap literatures.

## Overall Assessment
### Recommendation
Major Revision

### Confidence (1-5)
4

### Summary Assessment
This is a technically ambitious thesis with a genuinely good methodological instinct: it identifies the "has-a-stop" circularity that plagues much ML-based transit-siting work, builds an independent demand-versus-supply diagnostic, and is unusually honest about what it does and does not validate (the Question-A/Question-B distinction is a real conceptual contribution). However, from a Node-Place/domain-theory standpoint, several of the thesis's own methodological choices are framed as more theoretically settled than they are. First, the collapse of "NPP-V" to "NPP" is argued almost entirely from a single city's data limitation, not a theoretical reassessment of vitality's role, and Node-Place literature coverage is thin (missing at least Papa & Bertolini's own accessibility-based extension). Second, the "no expert weighting" claim for CRITIC/EWM is oversold — indicator selection, dimension taxonomy, normalization-method splitting, and the ensemble/alpha defaults are all undisclosed analyst choices, and the thesis's own documented equity-index sign-inversion bug is direct internal evidence of how much these "objective" outputs depend on upstream choices. Third, the equity term is empirically robustness-tested but not substantively argued against the transport-justice sources it cites. Fourth, the "research gap" claim under-cites at least two adjacent literatures.

## Strengths

### S1 — Honest separation of "reproduction" from "merit" validation
`thesis/en/chapters/07_discussion.tex`, `sec:disc-twoquestions`, `sec:disc-reconstruction`.

### S2 — Transparent disclosure of an equity-index sign inversion
`thesis/en/chapters/03_study_area_data.tex`, `sec:area-integrity`, lines 126–131.

### S3 — Out-of-sample corroboration via a genuine natural experiment
`thesis/en/chapters/07_discussion.tex`, `sec:disc-diagnostic`; `thesis/en/chapters/08_conclusions.tex`, RQ2.

## Weaknesses

### W1 — The NPP-V → NPP renaming is argued as a data artifact, not a theoretical revision
**Problem:** `sec:lit-nodeplace` moves directly from "our municipality-level ridership proxy is broken" to renaming the entire adopted framework, without engaging whether vitality *in principle* belongs in a demand-driven Node-Place variant or whether an AGEB-resolution alternative exists.
**Evidence Anchor:** `thesis/en/chapters/02_literature_review.tex`, `sec:lit-nodeplace`, lines 31–40.
**Severity:** Major. **Confidence:** 4/5.
**Suggestion:** Argue explicitly why vitality is dispensable in principle, or keep the "NPP-V" name and report vitality as "excluded from this application."

### W2 — Two theoretically load-bearing citations are unverified placeholder entries [VERIFIED]
**Problem:** `references.bib` contains, verbatim: `@article{liu2024nprv, author = {Liu, and others}, ..., note = {Placeholder entry -- complete with final citation details}}` and an identical placeholder for `niu2023rf`. `liu2024nprv` is the paper the thesis's own "NPP" naming is explicitly modeled on; `niu2023rf` anchors the random-forest siting claim.
**Evidence Anchor (file):** `thesis/common/references.bib`, lines 27–42.
**Severity:** Critical. **Confidence:** 5/5.
**Suggestion:** Verify and complete both entries (or substitute confirmed real papers) before defense/submission.

### W3 — "No expert weighting" is oversold; CRITIC/EWM launders analyst judgment rather than eliminating it
**Problem:** The literature review addresses only the final weight-assignment step while leaving earlier discretionary choices (which 14 indicators enter; Node/Place/People taxonomy; log1p+minmax vs. plain minmax split; 50/50 CRITIC-EWM ensemble average) unacknowledged as analyst choices. The thesis's own errata show how consequential this is: correcting the marginalization index's sign/imputation shifted mean equity score from 0.527 to 0.227 and mean final score from 0.506 to 0.413 — a swing driven entirely by an upstream data-handling choice.
**Evidence Anchor:** `thesis/en/chapters/02_literature_review.tex`, `sec:lit-mcda`, lines 95–104; cross-checked against `03_study_area_data.tex` lines 126–131 and `04_methodology.tex` `sec:w4`.
**Severity:** Major. **Confidence:** 4/5.
**Suggestion:** Reframe as "data-driven given a fixed, documented indicator set and normalization scheme" rather than "expert-free"; cite a critical MCDA source.

### W4 — The equity term's grounding in cited transport-justice literature is asserted, not argued
**Problem:** Martens (2016) argues for a sufficientarian accessibility floor (constraint-like), while the thesis operationalizes equity as a linear additive blend (α=0.20) — closer to the utilitarian-aggregation approach that literature partly reacts against. A Spearman-robustness statistic substitutes for this substantive discussion; top-50 list churn (~a quarter turning over across α values, per project notes) is not reported in the manuscript text.
**Evidence Anchor:** `thesis/en/chapters/02_literature_review.tex`, `sec:lit-mcda`, lines 104–110; `04_methodology.tex` `sec:w4`; `07_discussion.tex` `sec:disc-equity`.
**Severity:** Major. **Confidence:** 4/5.
**Suggestion:** Justify the additive-blend choice against the sufficientarian/egalitarian/utilitarian typology, or report top-N churn as a concrete finding.

### W5 — The claimed research gap likely under-states existing adjacent literatures
**Problem:** Verified via search (2026-09-09) that Foth, Manaugh & El-Geneidy (2013, *Journal of Transport Geography*, transit accessibility vs. social need in Toronto) and Camporeale, Caggiani & Ottomanelli (2019, *Transportation Research Part A*, equity in public transport network design) build closely related constructs to what the thesis calls novel, and are absent from `references.bib` despite close relatives (`jiao2013deserts`, `currie2010gaps`) being cited. Papa & Bertolini (2015, *Journal of Transport Geography*, accessibility + TOD across European metros) is Bertolini's own accessibility extension of Node-Place and is also absent.
**Evidence Anchor (absence):** Checked `sec:lit-gap`, `sec:lit-accessibility`, `sec:lit-nodeplace`, `sec:lit-network`, and the complete `references.bib`; none found.
**Severity:** Major. **Confidence:** 3/5 (existence/topical relevance verified via search; not read in full, so exact degree of overlap needs author comparison).
**Suggestion:** Cite and distinguish from these (or equivalents) in `sec:lit-gap`, narrowing the novelty claim to the specific combination not present in prior work.

### W6 — Node-Place lineage coverage is thin beyond the missing Papa & Bertolini link
**Problem:** Possible additional omission: Zemp et al. (2011) station-classification-with-clustering extension of Reusser's method (a direct antecedent to the K-means typology retained here) — flagged as recalled-not-freshly-verified, treat as a lead not a confirmed omission.
**Severity:** Minor. **Confidence:** 3/5.

## Questions for Authors

1. Was an AGEB-resolution vitality alternative considered and rejected, and on what grounds?
2. How do the authors reconcile the equity_score sensitivity to the marginalization-index fix (0.527→0.227) with the "expert-free" CRITIC/EWM framing?
3. Why an additive equity blend rather than a floor constraint, given Martens's sufficientarian argument?
4. Were Foth et al. (2013) and/or Camporeale et al. (2019) considered and excluded from `sec:lit-gap`, and why?

## Criterion-Bound Judgements

| Dimension | Judgement | Evidence anchor(s) | Rationale | Uncertainty/scope limit | Decision bearing? |
|---|---|---|---|---|---|
| Literature Integration | PARTLY_MEETS | `sec:lit-nodeplace`, `sec:lit-mcda`, `sec:lit-gap`; `references.bib` | Core mechanics accurately described; two load-bearing citations are placeholders; adjacent literatures under-cited. | Existence of 3 candidate papers verified via search; not read in full. | Yes |
| Originality | PARTLY_MEETS | `sec:intro-contributions`, `sec:lit-gap`, `sec:disc-generative` | Real, defensible combination + engineering contribution; "integrative pipeline" framing broader than lit review supports once adjacent work considered; NPP relabeling argued as branding for a data expedient. | Chapters 5-6 not read in full by this seat. | Yes |
| Methodological Rigor | NOT_ASSESSED | — | Out of scope. | — | No |
| Evidence Sufficiency | NOT_ASSESSED | — | Out of scope. | — | No |
| Writing Quality | NOT_ASSESSED | — | Out of scope. | — | No |
| Significance & Impact | NOT_ASSESSED | — | Out of scope. | — | No |
