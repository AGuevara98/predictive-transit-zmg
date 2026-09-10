## Devil's Advocate Review

**What the thesis does well, briefly:** the data-integrity chapter's willingness to publish its own errata is unusually candid for a thesis, and the transfer chapter's honest report of the Toluca backtest collapsing to zero re-proposed corridors is genuine good practice. That candor, however, is precisely what this review argues has been mistaken for methodological rigor.

### Strongest Counter-Argument

The thesis's rhetorical architecture depends on an epistemic rule stated once and then applied selectively. Chapter 7 states it explicitly: because built infrastructure reflects "political, financial, and land-availability constraints," agreement with what was built "corroborates" while disagreement is merely "faint evidence of error." That rule is invoked exactly once in the direction that protects the generator (explaining away zero-overlap with Lines 1–3 and 0.05 recall on Line 4) and never in the direction that would discipline the diagnostic's own headline evidence. The Line 4 result — a single natural experiment showing 1.6× a base rate that a model flagging one-fifth of the metro as "High-gap" would be expected to hit reasonably often by chance — is asymmetrically promoted to "the strongest validation," "the firmest and most citable contribution," with no confidence interval anywhere. Compounding this, the "generative" layer that Chapter 1 promises will judge corridors "rather than on agreement with the existing network" is architected so that candidate anchors must sit within 400m of existing stops and the objective function gives 2.5× credit for connecting to the existing network — the very circularity the introduction claims to have eliminated has been readmitted, one layer up.

### Issue List

#### CRITICAL

| # | Issue Description | Evidence Anchor | Confidence |
|---|---|---|---|
| 1 | RQ3 promises corridors evaluated "rather than on agreement with the existing network," but W6's anchor pool is filtered to within 400m of existing stops, and W5's objective gives 2.5x more credit (κ=0.50 vs 0.20) to corridors connecting to the existing network. Architectural, not fixable by rewording. | text: ch:introduction §1.3 / text: ch:methodology §4.6 / equation: Eq. (objectives) | High |
| 2 | Internal tension on what "overlap with existing routes" means as evidence: low overlap is "expected and desired" in Results, while agreement/disagreement with built lines is "weak evidence either way" in Discussion. | text: ch:results §5.8 / text: ch:discussion §7.1 | High |
| 3 | The Line 4 out-of-sample validation (1.6x) is reported as a bare ratio with no CI, significance test, or naive-baseline comparison, yet escalated to "the strongest validation" and the abstract's lead sentence. | text: ch:results §5.8 / text: ch:discussion §7.2 / absence: no CI or significance test; checked §5.8, §7.2, RQ2 | High |
| 4 | The flagship corridor W6_G02 is reported as "non-redundant" using only Jaccard=0.18; the project's own W8 benchmark computed a 42% shape-proximity overlap with premium route MP-C03, internally flagged as needing "a mild caveat on the 'unique corridor' framing," never disclosed in the thesis text. | absence: ch:results §5.6 — expected disclosure of the 42% overlap; checked §5.6, ch:discussion §7.3, ch:conclusions RQ3 | Medium-High (independently confirmed by the orchestrating session against the project's own records) |

#### MAJOR

| # | Issue Description | Evidence Anchor | Confidence |
|---|---|---|---|
| 5 | The redemption narrative for RQ3 rests on 1 of 4 feasible corridors (G02) fully passing, plus a second "pass" (G03) that is a 2.4km/5-AGEB stub of essentially the same character as the "degenerate short stub" dismissed under the prior architecture. | text: ch:discussion §7.3 vs. text: ch:results §5.6 | High |
| 6 | The endpoint-detour-to-anchor-directness metric swap is justified almost entirely by reference to the exact corridor (G02) it later rescues as the flagship success, without disclosing this. | text: ch:methodology §4.6 / absence: expected disclosure; checked §4.6, §7.3, ch:literature §2.6 | Medium |
| 7 | The 1.8 anchor-directness cap is a bare constant, undeived/uncited, yet is the sole binding constraint on essentially every rejected corridor in ZMG and transfer cities. | equation: Eq. (constraints) / absence: expected derivation or sensitivity; checked §4.5, §4.6, §5.6 | Medium-High |
| 8 | The α-sensitivity claim ("Spearman ≥ 0.98") is reported only in aggregate; project records show top-50 overlap only 36-37/50 and quintile churn 14-16%, absent from the manuscript. | text: ch:methodology §4.4 / absence: expected top-N disclosure; checked §4.4, §5.4, §7.5 | Medium |
| 9 | "Genuinely portable rather than bespoke to ZMG" is contradicted by the framework's own scope statement restricting Tier-1 data to "any Mexican city" — testing within one country's data ecosystem, not general transferability. | text: ch:data §3.3 vs. text: abstract | High |
| 10 | Several load-bearing constants (1.8 directness cap, stop-spacing band, demand thresholds, untransferred β) are carried unchanged to transfer cities, yet RQ4 claims transfer "without bespoke re-engineering"; Toluca's 0-feasible-routes result is directly attributable to one such ZMG-tuned constant. | text: ch:transferability §6.4 / text: ch:introduction §1.3 | Medium-High |
| 11 | Claiming an uncalibrated β transfer is low-risk "because...ratios...are insensitive to this choice" is in tension with the thesis's own finding that recalibrating β within ZMG produced a "markedly weaker decay" that reshaped demand's internal geography. | text: ch:transferability §6.1 vs. text: ch:results §5.2 | Medium |
| 12 | "No leakage" addresses only supply-side leakage; it does not address that population (top SHAP driver) mechanically constructs the demand numerator of the very target being predicted. No baseline-model comparison is reported. | equation: Eq. (productions) / text: ch:methodology §4.3 / absence: expected baseline comparison; checked §4.3, §5.3, §7.2 | Medium |

#### MINOR

| # | Issue Description | Evidence Anchor | Confidence |
|---|---|---|---|
| 13 | Calibration reported as a clear win without engaging that R²=0.2498 is a weak absolute fit inherited by every downstream layer. | table: Table (calibration) | Medium |
| 14 | "Equity and need are largely aligned" may restate a known demographic correlation (young, dense, poor peripheries) rather than an independent validation. | text: ch:discussion §7.5 | Low-Medium |
| 15 | No mention of running (or not running) a sensitivity sweep over the 1.8 cap in the main text. | absence: §4.5/§5.6 | Medium |
| 16 | No discussion of construction/displacement/political-economy costs of "retire"/"shortcut" proposals. | text: ch:conclusions §8.2 | Low-Medium |

### Ignored Alternative Explanations/Paths

1. A naive baseline (population density alone) might reproduce both the Line 4 corroboration and the SHAP "top drivers" finding equally well.
2. Low corridor–existing-route overlap could reflect the generator drawing through terrain/land-tenure/cost obstacles real planners deliberately avoided, not evidence of superior overlooked corridors.
3. Line 4's elevated High-gap signal could partly reflect reverse causality (pre-construction planning/land speculation already underway before the GTFS snapshot).
4. The generator's failure to reconstruct any rail line could indicate a genuine structural blind spot of the frontier-anchor architecture, not merely a weak-test artifact.
5. The 0.98 Spearman robustness claim could coexist with substantively different top-of-list winners across α values, unexplored for its planning implications.

### Missing Stakeholder Perspectives

- Concessioned bus operators (Toluca's ~30, with 431/622 routes flagged "Redundant").
- Transit planning agencies (SITEUR, IMEPLAN) — no expert-elicitation cross-check beyond the single Line 4 case.
- Current riders on flagged "Indirect"/"Redundant" routes who may rely on the circuitous alignment for specific access needs.
- Non-commute travelers (elderly, disabled, caregivers, informal workers) — trip generation is tuned toward standard commute patterns.
- Residents potentially displaced or affected by new corridor construction.

### Observations (Non-Defects)

- The re-architected anchor-directness metric still rejects corridors in both ZMG (G05, 1.93) and Aguascalientes (G03, 2.03) — evidence against a purely permissive redefinition.
- The data-integrity chapter's transparent disclosure of its own corrections is genuinely creditable practice.
- The transfer chapter's honest reporting of the Toluca backtest's degenerate collapse, rather than omission, is a real point in the thesis's favor.
