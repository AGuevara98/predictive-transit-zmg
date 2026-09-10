# Deep-Research Synthesis (2026-09-09) — 5 Sub-Questions on Methodological Correctness

Phase 1 (scoping) confirmed with the user; Phase 2–3 (search + synthesis) executed as a
targeted literature pass (not a full PRISMA systematic review — disproportionate for this
scope), per the RQ Brief. One finding led to an actual empirical test against the live
data (SQ3); one led to a **correction of an earlier, too-hasty finding** from the prior
informal pass (SQ5).

---

## SQ1 — Is demand/accessibility the dominant coverage-gap formulation, or are there materially different alternatives?

**Finding: dominant formulation confirmed; one strong new precedent found.** The
"needs-gap" framework (compare a need index against an accessibility index) is the
standard approach, consistent with Al Mamun & Lownes (2011, already cited) and Foth et al.
(2013, already cited). Alternative formulations do exist — a directional latent-demand
index using observed-to-expected flow ratios (Poisson regression), population-match
indices, Gini/Theil-based equity measures — but these are supplementary lenses, not
competitors to the ratio-based approach this thesis uses.

**New citation added**: **Rathod, Joshi & Arkatkar (2024)**, "Evaluation of Spatiotemporal
Transit Accessibility: Weighted Indexing Using the CRITIC-MCDM Approach and Performance
Gap Analysis" (*Journal of Advanced Transportation*, DOI 10.1155/2024/6343594) — a 2024,
peer-reviewed, near-exact structural precedent: CRITIC-MCDM weighting paired with a
transit-accessibility gap analysis, in Surat, India. This is closer to this thesis's own
W3/W4 pairing than anything found in the prior pass. **Added to Ch.2 §2.4.**

## SQ2 — Is there transportation-specific literature naming the circularity problem directly (not just cross-domain analogy)?

**Finding: no — confirmed by a second, more targeted search.** Found general-ML
self-fulfilling-prophecy work (Ganin et al.-style "Mirror, Mirror on the Wall," *Information
Systems Research* 2023) but nothing specific to transportation/transit siting under this
name. This is useful negative information: the four citations already added in the
previous pass (Kaufman 2012, Lakkaraju et al. 2017, Lum & Isaac 2016, Ensign et al. 2018,
Flynn et al. 2022) remain the best available grounding, and the thesis is correct that
this is a cross-domain analogy rather than an established transit-planning-literature
term. **No further thesis change** — the existing citations were already the right ones.

## SQ3 — What does the CRITIC/Entropy failure-mode literature say about *when* these methods fail, and can the thesis check its own data against that?

**Finding: yes, a concrete diagnostic exists, and I ran it.** The literature is specific:
CRITIC's weight formula discounts a criterion for correlating with others; the Entropy
Weight Method does not. An ensemble average of the two (as this thesis uses) only
partially corrects for indicator redundancy. **I computed the actual correlation matrix
of the thesis's 14 live indicators** (`features.nppv_features`): 3 of 91 pairs exceed the
conventional $|r|>0.8$ multicollinearity threshold (POI density↔retail density, r=0.93;
intersections↔street density, r=0.828; population↔population density, r=0.812), against a
mean absolute off-diagonal correlation of 0.335. None is surprising — each pairs
conceptually adjacent variables — and CRITIC's own formula already discounts them. **Added
to Ch.2 §2.4** as the concrete diagnostic the failure-mode literature calls for, reported
honestly as "checked, not alarming" rather than either omitted or oversold as a defect.

## SQ4 — Does a systematic search confirm no precedent for reconstruction-based validation of *generative* network-design methods?

**Finding: confirmed, more confidently than the first pass.** Standard TNDP validation
practice uses small benchmark instances (the Mandl 15-node network is the field's
standard testbed) and comparative algorithm performance against known heuristics/exact
solutions — not masking real existing infrastructure and testing whether a generator
reconstructs it. Generative-design literature outside transit (GANs for topology
optimization, network-representation generation) validates on synthetic or held-out
*design* instances, not on masked *real* infrastructure either. This is a second,
independent search confirming the earlier verdict: **the thesis's masked-reconstruct
backtest has no established precedent** — it is original, which is fine, and is already
honestly framed that way in Ch.7's "Question A vs. Question B" discussion. **No further
thesis change needed.**

## SQ5 — Is a fixed-weight composite "a step behind" current TNDP practice, or still common/defensible?

**Finding: the prior pass's verdict was too hasty, and I corrected it.** The literature is
clear that weighted-sum scalarization remains the *dominant applied practice* specifically
because Pareto fronts are hard for practitioners to act on and don't adapt flexibly as
priorities shift (Silva, Finamore & Henriques 2022, arXiv:2201.11616) — the same source
explicitly argues single- and multi-objective approaches are best combined
**synergistically**, not that one supersedes the other. This directly describes what this
thesis's W5 function already does (weighted composite *and* Pareto rank, both reported).

**Correction made**: the previous literature-review pass's claim that this hybrid is "a
step behind the field's more recent weight-free methods" has been **rewritten** in Ch.2
§2.6 to reflect the more accurate, evidence-backed position: the hybrid is consistent
with, not behind, current practice — with one added caveat, informed by this session's
own Pareto-dominance finding, that having both a composite score and a Pareto rank is
only useful if they *agree*, which for this thesis's own candidate set they demonstrably
do not (W6_G03 is Pareto-rank-1 and composite-score-top; W6_G02, the corridor the thesis's
prose emphasizes, is neither).

---

## Bibliography changes this pass

- **Added**: `rathod2024critic` (Journal of Advanced Transportation, 2024, verified DOI),
  `silva2022mo` (arXiv:2201.11616, verified).
- **No deletions this pass** (the one prior deletion, `liu2024nprv`, was already handled).

## What this pass demonstrates about the review process itself

Two of five sub-questions changed something concrete: one added a real citation and a
real empirical check (SQ1/SQ3), one **reversed a prior finding** rather than merely
confirming it (SQ5). The other three (SQ2, SQ4, and the "no alternative gap formulations
displace the current one" half of SQ1) returned confirmatory negative results — valuable
because they were actually checked, not assumed, but requiring no thesis edit.
Recompiled and verified clean throughout (62 pages, zero unresolved references).
