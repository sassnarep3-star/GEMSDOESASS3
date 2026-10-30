# New hypotheses ranked for the next slots — 2026-10-30 (post-H-SASS3-I)

Context: H-SASS3-I (λ-greedy emission) is complete and **negative for promotion** — see
`docs/research/lane-H-SASS3-I-20261030.md`. What it established, and what these five hypotheses build on:

* the metric's per-truth-pixel credit is a **maximum** that **saturates**, so score comes from covering truth
  pixels at all, not from grading or from dot counts (121,131 dots → 0.1922 vs 37,654 dots → 0.2778, OWNER-REPORT);
* the truth-density structure inverted from 34 live scores is *robust at band level, not at multiplier level*:
  1 px off the H19-5 ridge is 580–1398× the prior, catalogue distance 20–50 px is 18.7× vs ≤ 0.38× at 1–5 px,
  but individual stratum multipliers move by an order of magnitude between fits (λ capped at exp(5));
* any design tuned to one density loses 0.07–0.13 under the other two ⇒ **every candidate now faces a
  three-density maximin gate** (`scripts/project_candidate.py`, ~4 min, `local_convex` refit LOO MAE 0.0212).

Expected gain below is a **projected ΔDTI bracket against the 0.2778 champion** (LLI-v1 projections, instrument
LOO error ±0.02), never a score forecast. Cost: S ≈ ≤ 30 min of compute on what is already in the repo;
M ≈ needs one public file or a new surface; L ≈ needs the login-walled stack.

| Rank | ID | Mechanism | Expected ΔDTI vs champion (projection) | Cost | Gate before a slot |
|---|---|---|---|---|---|
| 1 | **H-SASS3-N** | organizers' U-Net + MC-CV reference path on the real feature stack, output binarised by λ-weighted coverage | unknown sign today; the only route with public evidence of the 0.4+ region (public #1 = 0.4544, OWNER-REPORT/leaderboard) | L (blocked on `training_features.tif`) | three-density maximin **and** a spatially-blocked holdout, which this data also unblocks |
| 2 | **H-SASS3-J** | density-averaged ensemble emission: rank cells under each of the three λ fields, emit the union of per-density top-k; expected-credit objective instead of worst-case | −0.02 … +0.06 (E5, the closest measured construction, was −0.0195 … +0.0624) | S | three-density maximin |
| 3 | **H-SASS3-L** | scarp-foot colluvial channelisation: flow-accumulation × slope ridges restricted to catalogue distance 5–50 px, i.e. the inversion's hot band, with a 1–2 px offset off the H19-5 ridge | −0.05 … +0.04; the band is hot but so is the sibling pool there | M | maximin **+** duplicate test, because the target band is where ≥ 1 pool raster is positive everywhere |
| 4 | **H-SASS3-K** | coverage-only emission (no λ): greedy first-dot-per-uncovered-truth-prediction on the H19-5 halo only, to measure whether the 0.28 plateau is a *coverage* limit or a *prior* limit | ~0 by construction, but it is the experiment that tells us whether to keep spending on placement at all | S | none (diagnostic, not a submission candidate) |
| 5 | **H-SASS3-M** | re-emit the rejected BGK-PBE gravity/dilatation surface restricted to the λ-hot 1 px off-ridge band | −0.10 … +0.01; the parent surface already scored 0.0 on the catalogue diagnostic and 99.59 % lattice overlap | M | maximin + duplicate test; low prior, keep last |

## Per-hypothesis detail

**H-SASS3-N — reference-path re-fit (the one that can actually move the number).** The organizers'
`unet-mc-cv-reference-solution.ipynb` reads `data/numeric_features.tif` (19 float32 bands; our mirror is
`registry/data_manifest.json`'s `training_features.tif`, 418,912,844 B, sha `4371c82e…`), sets `y[y<1]=0`,
clips sentinels `< −1e38` to NaN then min/max-scales to [0,1], and writes a single-band float32 prediction with
the labels file's CRS and transform and **no masking outside the footprint** (`y_out = np.zeros(...)`). Its
visualisation threshold is > 0.1. Two things follow: (a) the portal-safe zeros-outside convention used by our
packager is the reference solution's own convention; (b) a trained model's graded output is worth binarising
under the coverage rule rather than thresholding at 0.5, because only the max matters to the metric.
Mimic risk: none specific — the risk is that a model trained on `labels.tif` (the *catalogue*) learns the
catalogue, which the reference notebook is explicit about; the fix is to train on off-catalogue positives only,
which is what the repo's `evaluate_holdout.py` hides.

**H-SASS3-J — density-averaged ensemble.** Stop choosing a density. Build `w_d` for d ∈ {published S0,
published S3, local_convex}, rank cells by their *worst* rank across densities (or emit the union of per-density
top-k with a ρ = 4-cell separation), so no single fit owns the answer. E5 (champion ∪ our dots, 56,295 cells,
Δ = +0.0624 / +0.0097 / −0.0195) is the existence proof that a density-agnostic superset can be non-losing.
Its duplicate risk is real and must be measured, not assumed away.

**H-SASS3-L — scarp-foot colluvial channelisation.** Geology: a degrading scarp exports colluvium into
channelised wedges at its foot; those wedges mark the trace even where the fault is buried, and they are the
one landform that produces the 5–50 px off-catalogue, 1–2 px off-ridge combination the inversion rewards.
Compute: `flow_accum × slope` ridges (both in the prepared stack), opened along-strike, restricted to the hot
distance bands, thinned to ρ = 4 cells. Mimic: alluvial fan heads and debris-flow channels that are not
fault-controlled — test by checking whether the same ridges appear on the *reverse* (fault-north) side of each
scarp, where a structural control predicts symmetry and a depositional process does not.

**H-SASS3-K — coverage-only control (diagnostic).** Emit greedily to cover predicted-truth mass without any λ
(the halo is the prior). If the projection lands at the champion's level, the plateau is a *coverage* limit of
the H19-5-derived geometry and placement work is finished; if it lands far below, the λ band genuinely carries
information. Cost is one run of the existing harness. Negative results here save the most slots.

**H-SASS3-M — BGK re-emission (keep last).** The gravity-kernel-dilatation surface failed its own promotion test
and scored 0.0 against catalogue labels; restricting it to the λ-hot band is a small, well-instrumented tweak,
but the prior is low and the uniqueness exposure is high. Do not spend a slot before J/L/K are exhausted.

## Standing blocker on promotion

No candidate from this lane can be *promoted* (only *downloaded*) while the spatially-blocked holdout is
unrunnable, and the two catalogue holdouts in the sibling repositories rank the live-scored focus files in the
opposite order to the leaderboard. That is recorded as IR-SASS3-74 (blocked holdout) and IR-SASS3-75
(NaN-outside vs the portal's [0,1] range check). The three-density maximin harness is a **screen**, documented
as insufficient for promotion; it is not a holdout and is never labelled one.
