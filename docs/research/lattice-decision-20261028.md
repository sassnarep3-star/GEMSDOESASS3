# Decision memo: the calibration-lattice block (2026-10-28)

Status: **OPEN — owner decision required.** Nothing in this memo has been applied to any gate, run card, or
protocol. No experiment ran in this session (experiment budget 0 of 3). No submission slot was used.

## 1. Bottom line

- **No focus-site file is cleared for submission.** The LWST archive is available for download for review only
  (`ok_to_download: true`, `ok_to_submit: false`).
- The block is geometric. The 13GEMSDOE 5-px calibration lattice (206,895 dots, owner-reported 0.0904) covers
  99.87% of the 5,167,373-cell footprint within 3 px. Only 6,649 cells lie outside that buffer, and 90.3% of them are
  within 2 px of the footprint boundary. Under the literal rule, a file with 37,654 dots can have at most 22,163 dots
  that are not within 3 px of a lattice dot. The 37,654 dots fail on every convention tested. The cap is
  `floor(6,649 / 0.30)`.
- **All 18 measured focus-site files fail the literal rule** (9 historical, 9 latest). The lattice overlap is 99.05%
  or more for every one. So the decision below governs the whole focus set, not just the LWST file.
- **Official rules:** The NLR Official Rules contain no uniqueness, overlap, or dot-count rule. The 70% limit is a
  project protocol rule, not a competition rule.

Source for the rules: <https://docs.nlr.gov/docs/fy26osti/96647.pdf> (all segments read 2026-10-28; §3.2 three
submissions per week; §3.4 one final submission per entity; §3.5 a single submission chosen across both rounds;
generative-AI use disclosed in the narrative).

Source for the scoring design: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>.
The Initial Prize Round uses a private set of new faults; the Final Prize Round rescores the same submissions against
an expanded label set that adds faults verified by experts after reviewing submissions.

## 2. Measured numbers (reproducible)

| Quantity | Value | Source (reproduce with) |
|---|---|---|
| Footprint cells | 5,167,373 | `scripts/lattice_bound_audit.py` → `evidence/lattice_bound_audit_20261028.json` |
| Cells within 3 px of lattice (Euclidean ≤ 3) | 5,160,724 (99.8713%) | same |
| Cells outside buffer (primary convention) | 6,649 | same |
| Cells outside buffer (strict <3 px) / (7×7 square) | 7,992 / 1,846 | same |
| Largest passing dot count (primary / strict / 7×7) | 22,163 / 26,640 / 6,153 | same |
| Uncovered cells within 2 px of footprint edge | 90.3% | same |
| LWST forward overlap with lattice | 0.997849 (81 dots on uncovered cells) | same |
| Focus-site files: lattice overlap | 99.05% to 100.00% (18 of 18 fail) | `scripts/focus_site_candidate_audit.py` → `evidence/focus_site_candidate_audit_20261028.json` |
| Latest candidates: like-for-like max overlap vs the ten references | 61.60% (GEMSDOE36 latest) | same |
| Latest candidates: sampled |Spearman| vs lattice and LWST | max 0.114 (GEMSDOE32 latest) | same |

Correction: the review and ledger entry IR-SASS3-19 gave 5,379 uncovered cells and a 99.90% footprint coverage. Those
values did not reproduce under any convention tested. The recomputed values above replace them. The conclusion is
unchanged. See IR-SASS3-20 in `evidence/irregularities_ledger.json`.

## 3. Options for the owner

### Option A — like-for-like reading (recommended)

Adopt, by a dated amendment, the reading the shared template already implements: a halo-saturated lattice (more than
90% of footprint cells within 3 px, `HALO_SATURATION_FRACTION = 0.90` in `vendor/gems57/uniqueness.py`) is excluded
from the dot-overlap test. Rank correlation still applies to every raster, and the dot-overlap test still applies to
every other registry raster.

- **Why recommended:** the literal test measures geometry, not lane. Any dense dot field fails it, so the test cannot
  separate lanes, which is the purpose of Rule 1.
- **What it unlocks:** the LWST archive (max 66.53% against 451 genuine downloads, per the independent review, not
  re-run here) and the nine latest candidates (max 61.6% against the ten references measured here).
- **What it does not unlock:** any historical focus file (already submitted; duplicates its family), and any file
  that fails rank correlation.
- Draft amendment text: `docs/research/protocol-amendments.md` (status PROPOSED, not applied).

### Option B — keep the literal rule

No amendment. Protocol Rule 1 says log the duplicate and stop. Nothing is eligible. Experiments are also blocked,
because their output could not be submitted.

### Option C — meet the letter with edge cells (not produced, not recommended)

A file could satisfy the literal count by placing at least 30% of its dots on the 6,649 uncovered cells, at most
22,163 dots in total. Those cells lie mostly on the footprint boundary, where no mapped fault exists. This meets the
letter of the rule by placing dots where no geology is mapped, which lowers the expected score and defeats the rule's
purpose. I did not generate such a file.

## 4. Why no file was generated or promoted

- The literal gate fails for every candidate, so generating a new file would not produce a submittable result.
- Promotion to a weekly slot is a separate selector step (a person or an explicitly-signed selector), not a
  property of a file.
- The HOLDOUT-DTI values in this repo do not agree with each other. See the next section.

## 5. Holdout proxies: two evaluators disagree

| Evaluator | Champion GEMSDOE32 (owner 0.2778) | GEMSDOE24 (owner 0.2477) | Concordance with owner scores (n = 21) |
|---|---|---|---|
| SGMC-CAL (review §4) | 0.064121 | 0.057932 | Spearman 0.869, 95% CI [0.606, 0.980] |
| SGMC raw (review §4) | not in this memo | not in this memo | Spearman 0.550, CI [0.050, 0.878] |
| HIDE-RECOVER (review §4) | 0.004515 (not leak-free under Rule 2) | not in this memo | Spearman 0.143, CI [-0.378, 0.583] |
| gems57-pooled-hide-v2 (nine-site audit) | 0.003885 [0.003316, 0.004478] | 0.096653 [0.085535, 0.107455] | not computed |

The pooled-hide-v2 evaluator reverses the GEMSDOE24 / GEMSDOE32 ordering that SGMC-CAL and the owners give. Until the
evaluators are reconciled, no HOLDOUT-DTI value here estimates an organizer score. The latest-candidate values in the
nine-site table use pooled-hide-v2 only. They have no SGMC-CAL value yet.

## 6. Why 0.2778 scored highest (evidence and open questions)

1. **Family, not outlier.** The champion's dots lie within 3 px of the historical files of other focus sites at
   99.9% to 100% (measured). The nine historical files form one dot-field family.
2. **Narrow score band.** The nine owner scores run 0.2449 to 0.2778. The initial round scores against a private set,
   and the public leaderboard shows only the public split (competition page 967). A 0.01 to 0.02 gap can flip under a
   different split. This cannot be quantified because the split is not published.
3. **Best proxy ranks it high.** SGMC-CAL ranks the champion 2nd of the nine focus files (behind GEMSDOE36) (range 0.057932 to 0.064444).
   The pooled-hide-v2 evaluator ranks it near the bottom. The two disagree, so neither is established.
4. **Mechanism to test (not proven).** The test labels are new faults that expert panels mapped and that are not in the
   USGS fault database (competition page 967). Our holdouts withhold catalogue faults. Only an organizer receipt tests
   the mechanism.

## 7. Can we beat 0.2778?

Not demonstrated. The live leaderboard top is 0.4544 (xiaofanhu, rank 1). Rank 27 is 0.3195 (kpomazi). Rank 48 is
0.2897. The 0.4413 figure in the request is superseded by the live page (fetched 2026-10-28). No repo file has an
organizer receipt.

## 8. Hypotheses (status)

The review (`docs/research/independent-review-20261028.md` §7) records H-SASS3-E as tested and negative (basement
minimum-curvature ridges, one of three experiment slots). H-SASS3-F, G and H are untested. They are carried over, not
newly generated or validated in this session. Their ranking is in the review table. No experiment was run here, so no
hypothesis has passed the spatially-blocked holdout.

## 9. Next steps

1. Owner records Option A, B or C. Only Option A unlocks any file, and only by recording the amendment.
2. If Option A is recorded: re-run `scripts/verify_all_gates.py` (the literal gate will then be replaced by the recorded
   reading, and the gate output must say so). A selector then picks one file within the weekly cap.
3. Reconcile the two holdout evaluators (pooled-hide-v2 vs SGMC-CAL) on the owner-scored set before using any holdout
   value to select a file.
4. Compute the SGMC-CAL proxy for the nine latest candidates (not done in this session).
5. Run experiments F, G and H only after the owner decision, within the budget of 3 experiments or 2 hours. The
   holdout must be spatially blocked, and the lane rule applies.
