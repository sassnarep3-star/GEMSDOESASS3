# Why 0.2778 was the best published score, and what it would take to beat it

**Session:** 2026-10-31 · **Lane:** `H-CELLDISTILL` · **Verdict: negative — no slot promoted.**

---

## 1. The champion, measured rather than narrated

`GEMSDOE32 · gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, published score **0.2778**
(OWNER-REPORT; the score the owner read off the submission page — there is no public per-file receipt).

Measured from the raster bytes this session:

| property | value |
|---|---|
| positive pixels inside the footprint | 37,654 |
| of those, inside the *scored* domain (footprint minus catalogue) | 37,654 |
| mass as a share of the footprint | 0.73 % |
| values | {0, 1} float32, NaN… → the `-zeros` variant fills 0.0 outside the footprint |
| implied truth credit under the metric's linear form | `TP = 0.2778 x (0.2 x 37,654 + 0.8 x N)` |

**The `-zeros` suffix is a fill convention, not an empty submission.** The same raster family appears on
this owner's list as `…-nan` and `…-zeros` with identical scores (e.g. GEMSDOE12 `0.1294` and
`…_allfinite 0.1294`; GEMSDOE68 `0.0437` twice), which is only possible if the fill outside the
footprint is ignored by the scorer. Nobody beat the leaderboard by predicting nothing; the file
carries 37,654 assertions.

## 2. Why that family wins the metric

The organizer's index is

    DTI = TP / (TP + 0.2 FP + 0.8 FN)      TP = sum_g max_x p(x)k,  FP = sum_x p(x)(1 - max_g k),  FN = N - TP

Because alpha + beta = 1 and predictions are binary, the corpus work in this repo inverts the
**surrogate** `DTI ~ TP / (0.2 D + 0.8 N)` (mass D = number of emitted dots). `tests/test_cellcredit_distillation.py`
pins when that is exact — every dot owning a distinct labelled pixel, no two truth pixels sharing a dot —
and pins the regime where it flatters a file worth nothing. It is a ranking device, not a price; that is a
third reason no estimate is published today.

Verified against the organizer's own equations on [page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric)
and implemented with a brute-force cross-check in `src/gems32/metric.py`. Three consequences, all
measured on the 132-file corpus this session:

1. **Ranking is recall per unit emitted mass.** Under the surrogate, a dot is worth adding iff its
   credit exceeds `0.2 x DTI` (~0.055 at these scores), which is why every good file sits in a narrow band of
   37k-60k dots: below it, uncovered truth dominates; above it, the FP term eats the gain.
2. **Predicting the catalogue is worthless.** Known USGS/INGENIOUS fault pixels are masked out of
   scoring ([thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2),
   ORGANIZER statement). The corpus' best files are *off-catalogue* by construction — `offcat`,
   `gap-closure`, `blind`, `topo-gap` are in eight of the twelve names.
3. **Score pooling is one Tversky index over the whole public subset**
   ([thread 11550](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2),
   ORGANIZER statement), so there is no per-chunk gaming to exploit.

So 0.2778 is not a modelling triumph: it is *the best-sited 37,654 dots among the published
attempts*. And 20 of the 132 published rasters — including the six highest scores — are one
near-duplicate family (Jaccard of dot sets >= 0.35), which is why nine sites produce nine
"site leaders" that are the same idea.

## 3. What this session tried, and what the numbers say

The 2026-10-30 session ranked five hypotheses and left one unexecuted: **H-CELLDISTILL**, a
cell-level model of credit. It is now executed, on 28 channels (the 19 official GeoDAWN bands plus 9
structural transforms: white-tophat scarp steps at two scales, Hessian ridge on detrended elevation,
magnetic and gravity lineament ridges, conductivity and depth-to-base edges, and two strain-ratio
kink measures).

Because the metric is linear in credit, and credit is modelled linearly in features, the whole
5.17-million-cell inverse problem collapses **exactly** to a weighted regression on the 132 published
rasters' *mean* feature vector. Nothing is hand-tuned: `N` and the ridge penalty are picked by
leave-cluster-out, and the loss is the leaderboard-score MSE itself.

| estimator of a file's score | validation | RMSE | rho |
|---|---|---|---|
| predict the corpus mean | — | 0.0818 | 0 |
| **bag-mean channel model (this session)** | **leave-cluster-out** | **0.0586** | **0.746** |
| field-sum pricing of the same model | leave-cluster-out | 0.0806 | 0.302 |
| corpus inversion (the site's 2026-10-30 headline, `est 0.369`) | leave-cluster-out | **0.1364** | n/a |

* The bag model **beats the mean baseline by 1.4x on a validation unit that removes whole families of
  near-duplicates.** It is a genuine, reusable asset: a screen that ranks a candidate raster before a
  slot is spent.
* The same test **retires the site's published 0.369 estimate**: the incumbent inversion's
  leave-one-file-out number (0.0533) was an artefact of withholding one copy from a family of twenty.
* Pricing our own emission by the field sum produced a mean credit of 0.21 per dot where the corpus'
  best files achieve 0.07 — the winner's curse of extrapolating a bag-mean model into the top 1% of
  its own field. The first candidate priced this way returned **493**, an impossible score, caught by
  the range logic in `scripts/build_cellcredit_candidate_20261031.py` before publication. We therefore
  publish **no score** for the candidate: no estimator in this repo can honestly certify > 0.2778.

Leakage canary: every channel's single-feature AUC against "within 400 m of a mapped fault" is in
0.30-0.57 (`evidence/cellcredit_distillation_20261031.json`) — no channel is a catalogue look-up,
so the fit is not relearning the mask.

## 4. The unique TIF this session generated

`gemsdoesass3-cdist-52000-20261031T1200Z-zeros.tif` — 52,000 dots, single-band float32, EPSG:32611,
3730x3292 at 100 m, values exactly {0,1}, **no NaN anywhere** (the zeros variant is what passes the
portal's `Predicted values must be in range [0, 1]` gate; the `-nanoutside` sibling fails it and is
kept only for the diff).

* worst 3 px overlap with any of 511 registry rasters: **47.0 %** (repo cap 65 %, protocol 70 %);
  the binding raster covers 35.3 % of the footprint, so the lift is 1.33x — this is not a copy;
* 1.07M field cells with positive credit lie outside *every* published raster's dots;
* holdout floor (shared harness, not a score): HIDE-RECOVER pooled DTI **0.0461** [0.0394, 0.0533]
  on 22,232 withheld positives; SGMC-CAL prevalence-calibrated **0.0804** [0.0707, 0.0894] on 62,703.
  The corpus family is far above that on the same harness, so this candidate is *worse*, which is the
  honest reason it is not promoted.

**Gate verdict: OK to download, NOT OK to submit.** A submission slot is a weekly-budgeted resource;
spending one on a raster that loses the floor test and cannot be priced above the champion would be
an own goal.

## 5. Ranked hypotheses for the next session (nothing here has been tried in this repo)

| # | hypothesis | layer(s) / signature | why it finds an *unmapped* fault | delta vs this repo | cost |
|---|---|---|---|---|---|
| 1 | **H-GAPLIDAR** — scarps in the 1 m 3DEP/GeoDAWN LiDAR DEM restricted to the 1.07M off-corpus cells this session's field nominates | hill-shaded slope + tophat step at 1 m, then a 200-400 m along-strike continuity filter | the new labels were drawn by experts from high-resolution topography, so a *visible* unbroken step where the catalogue is silent is the highest-precision evidence available; the corpus' 100 m features cannot resolve steps under basin fill or alluvium | every prior session ran the scarp filter over the *whole* grid and at 100 m; nobody has used the model's own off-corpus cells as the search domain | medium — DEM links are already registered in `registry/data_manifest.json` |
| 2 | **H-RELAY** — stepover/relay ramps between catalogue tips: dilate-tip pairs 0.8-3 km apart, anti-parallel, with a contraction or extension bridge between them | strain-rate invariants (`geod_dilaterate`, `geod_shearrate`) integrated over the bridge polygon | unmapped linking traces are exactly what a relay demands, and a relay is invisible to a per-pixel detector because its signal is the *pair* | `GEMSDOE33`'s tip-stepover and this repo's H-TIPCONT extrapolate a single tip; neither scores the *bridge* between two tips | low — all inputs cached |
| 3 | **H-CONDUITSEAM** — geothermal-fluid seam: conductivity low-high step coincident with a scarp step AND a radon/alteration proxy | `cond_surf`, `depth_to_base_surf` edge, `geodawn_rad_u8` (Th/K ratio) | fault-guided fluid flow alters and seals near the fault, so the conductivity step persists where the scarp is buried; the target is the *buried* half of the label set | `GEMSDOE71/75/36` used thermal/geometry separately; none conditioned a fault proposal on a radometric *ratio* crossing a structural step | medium |
| 4 | **H-FLIGHTLINEGUARD** (protective, not additive) — remove candidates aligned with the flight azimuth whose only support is a magnetic/gravity edge | local orientation vs the survey lineation; drop if support is edge-only | the classic false-positive for lineament detectors is the sensor, not the crust (see the mimic named in the run card) — removing it raises precision, which is what the 0.2 D term pays for | no session in this repo has modelled the artifact at all | low |
| 5 | **H-CELLDISTILL-BAG2LIST** — replace the linear bag model with a *listwise* one: train the ranking of files (not their scores) on bag features, then emit by pairwise-dominance rather than by field tops | same 28 channels + bag spacing/continuity statistics | ranking is identified even where magnitude is not; the winner's-curse failure above is a magnitude problem | the 2026-10-30 negative card "file-level features" fitted magnitudes and failed; nobody fitted an ordered ranking objective | medium |

Ranking is by expected DTI gain per hour: 1 and 3 target recall (the only way past the family), 2 is
cheap and orthogonal, 4 buys precision, 5 fixes the estimator before it is used again.

## 6. Files

`scripts/distill_cellcredit_20261031.py` (fit + canary) · `scripts/compare_estimators_20261031.py`
(arm A/B/blend, leave-cluster-out) · `scripts/calibrate_fieldsum_20261031.py` (the negative on
field-sum pricing) · `scripts/build_cellcredit_candidate_20261031.py` (emit + gate) ·
receipts `evidence/{cellcredit_distillation,estimator_arms,fieldsum_calibration,focus9_verdict_table,
holdout_cellcredit,run_card}_20261031.json`.
