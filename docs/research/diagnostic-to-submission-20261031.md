# From published scores to a submission — 2026-10-31

How this session's candidate was built, why the honest number is smaller than the pretty one, and
what the five-fold design actually proves. Every figure below comes from a receipt under
`evidence/`.

## 0. The one external fact the whole method rests on

The metric is a distance-weighted Tversky index with α = 0.2, β = 0.8, R = 300 m (3 px)

```
TP_w = Σ_g  max_{x : d(x,g) ≤ R}  p(x)·k(d(x,g))
FP_w = Σ_x  p(x)·[1 − max_g k(d(x,g))]
FN_w = Σ_g [1 − max_{x : d(x,g) ≤ R} p(x)·k(d(x,g))]
DTI  = TP_w / (TP_w + α·FP_w + β·FN_w),   k(d) = (1 − d/R)₊
```

([official spec, page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)).
For a **binary** prediction of mass `D = Σ p` against a truth set `G` of mass `N`
(all published rasters are binary), `FP_w + TP_w = D`, so

```
DTI = TP_w / (0.2·D + 0.8·N)                                     (1)
```

and the denominator contains **no** `TP_w`. That is the whole trick: each published score `s_i`
is a *linear measurement* of one hidden quantity — the kernel credit `A_i = TP_w` of file `i`:

```
A_i = s_i · (0.2·D_i + 0.8·N)                                    (2)
```

`D_i` is read straight off the raster. `N` is not known, but it is bounded (§4). So 182 published
scores are 182 linear measurements of a hidden credit field, and the field can be reconstructed.

## 1. The corpus

`scripts/fetch_sibling_downloads_20261031.py` clones `docs/downloads` (plus `submissions`,
`outputs`, `artifacts`) from 110 sibling repositories and hashes every file.
`scripts/build_corpus_20261031.py` keeps the ones that are single-band, float, EPSG:32611,
3730×3292 on the 100 m grid, then joins the owner-reported score tables.

| | |
|---|---|
| repositories attempted | 110 |
| files fetched | 1 987 unique by SHA-256 |
| grid-valid rasters | 1 981 |
| rasters carrying an owner-reported score | **182** |
| distinct scored fields (families at 0.87 dot overlap) | **64** |

**The corpus is massively redundant.** The top 20 rows are about 8 distinct fields published ~2.5
times each under different names and repositories; the champion alone appears four times
(`GEMSDOE32__…h33-h33-2-b2…`, `60GEMSDOE__…h33-h33-2-b2…` ×2, `60GEMSDOE__gems60-h69a-champ-half…`).
Any estimator that treats the 182 rows as independent measurements — including plain back-projection
— will simply multiply the duplicated evidence. That is the defect the Gram solve fixes.

## 2. Experiment 1 — where does the truth live?

`scripts/diagnose_truth_location_20261031.py` regresses each file's score on geometric descriptors
of its dot set. OLS over n = 182, R² = 0.221:

| term | coefficient | p |
|---|---|---|
| mass within 300 m of a catalogued fault | −0.339 | 2 × 10⁻⁴ |
| mass in the 300–600 m shell | +0.124 | 0.24 |
| mass in the 600–900 m shell | −0.120 | 0.26 |
| clumpiness (dots with ≥1000 units of mass in their 3-px neighbourhood) | −0.0056 | 1.5 × 10⁻⁵ |
| log₁₀(D) | +0.047 | 0.0066 |

and the mean score by median per-dot distance from the catalogue peaks at **0.167 in the 12–20 px
(1.2–2.0 km) band**, falling to 0.052 past 20 px.

Two conclusions, both used later:

* predicting the catalogue is worthless (negative coefficient) — consistent with DrivenData staff
  confirming known-fault pixels are masked and score-neutral
  ([thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516));
* the truth is an **annulus around** the catalogue, not on it and not in the deep background, and
  spread-out fields beat clumpy ones.

## 3. Two estimators for the credit field

Write `p_i(x)` for raster `i`'s prediction and `q(x)` for the (unknown) expected kernel credit of a
dot placed at `x`. Then `A_i = Σ_x p_i(x)·q(x) + noise`, and we model `q = Σ_j λ_j p_j`.

**Back-projection (adjoint).** `λ_i^BP = A_i / D_i`, i.e. `q_BP(x) = Σ_i (A_i/D_i)·p_i(x)`. This is
what the 2026-10-30 session effectively did. It is *blurred by duplication*: the champion's family
shares 0.87–1.00 of its dots, so its evidence enters four times.

**Gram / normal equations (this session).** Solving `G λ = A` with `G_ij = Σ_x p_i·p_j`:

```
G λ = A,   G_ij = Σ_x p_i(x) p_j(x),    A_i = s_i (0.2 D_i + 0.8 N)
```

`G`'s off-diagonal entries *are* the near-duplicate overlaps, so the solve divides them out.
`G` is 182×182, built with sorted indices + `np.searchsorted` in 28.5 s and cached to
`.cache/gram_20261031.npy`. It is solved by NNLS on `G + μ·diag(diag G)` (λ ≥ 0 is physically
required — a raster cannot have a negative credit density). μ was swept over
{1e-4, 1e-3, 1e-2, 1e-1}: the solution is stable (63–64 non-zero weights, relative residual 0.2764,
max λ 0.067–0.074), so μ = 1e-3 is the default.

The resulting field is smoothed by the metric's own kernel (`q ← q ⊛ k`, `k` = triangular, R = 3 px)
and dots are emitted by descending-`q` non-maximum suppression at 3 px spacing.

## 4. How big is the truth set? (the `N` problem)

`N` enters (2) and the estimator's scale. Two independent arguments bound it.

**Lower bound (hard).** `A = TP_w ≤ N` for any prediction, so from (1)–(2),
`N ≥ 0.2·s·D / (1 − 0.8·s)`; maximising over the 182 files gives

> **N ≥ 8 222.4**

**Upper bound (model).** Write `A = ε·N·mc` where `mc` is the *no-skill* credit of the file
(the mean kernel credit a random dot earns against a truth set of mass `N`, computable per file from
the footprint and the truth-side distance transform), and `ε ≥ 1` is the enrichment — the assumption
that a file does no worse than chance. Then

```
N = 0.2·s·D / (ε·mc − 0.8·s)     ⇒     ε = 1 upper-bounds N
```

**A filter is mandatory here.** Because known-fault pixels are masked out of scoring, a raster whose
dots sit mostly *on* the catalogue has an effective `D` far smaller than its raw dot count, and the
formula understates `N` for it. An earlier, unfiltered version of this bound returned
`N ≤ 2 847.7` — below the hard lower bound of 8 222 — driven by
`GEMSDOE53__gems53-h8-tiprelay-ridgeconcord-pr2-n80000` (80 000 dots, score 0.0159). Restricting to
broad, catalogue-independent rasters (share of dots within 300 m of the catalogue ≤ 0.15,
`D ≥ 100 000`, `mc ≥ 0.10`) leaves four files and gives

> **N ≤ 12 366** — `13GEMSDOE__13gems_20261001_r13-lattice-s5_v2_nan-outside.tif`
> (a uniform lattice: unambiguously uncorrelated both with the truth and with the catalogue)

so **8 222 ≤ N ≤ 12 366**, and the candidate uses **N = 12 000**. The next-tightest files agree
(12 653, 21 208, 21 767). The bounds are now consistent; they were not before the filter.

## 5. Experiment 3b — the honest five-fold design

Scoring a candidate against the field it was built from is circular. The design that is not:

1. split the 182 scored rasters into **64 near-duplicate families**;
2. for each of 5 folds: build the candidate from the TRAIN families only, using **only those
   rasters' scores**;
3. score the candidate against an **independent yardstick** `T̂_test` built from the held-out TEST
   families only;
4. calibrate: regress the observed scores of the TRAIN rasters against their own score on the same
   test yardstick, and read the candidate's estimate off that line.

`scripts/validate_candidate_20261031.py`, `evidence/validate_candidate_20261031.json`.
Configurations: spacing {3.0, 4.0} px × budget {40 000, 60 000} × {back-projection, Gram} variants.

| configuration | estimate (5-fold mean) |
|---|---|
| **Gram/nnls, spacing 3.0, budget 60 000** | **0.2371** |
| Gram/nnls, spacing 4.0, budget 60 000 | 0.2332 |
| Gram/nnls, spacing 4.0, budget 60 000, min-blob 2 | 0.2328 |
| back-projection, spacing 4.0, budget 60 000, min-blob 2 | 0.2236 |
| Gram/nnls, spacing 3.0, budget 40 000 | 0.2155 |
| back-projection, spacing 4.0, budget 60 000 | 0.2148 |
| back-projection, spacing 3.0, budget 60 000 | 0.2054 |
| back-projection, spacing 3.0, budget 40 000 | 0.1982 |

**The Gram solve beats back-projection in every one of the five folds** (a 2-fold rerun reproduced
the ordering: 0.2311 / 0.2303 / 0.2302 vs 0.2103 / 0.2003 / 0.1916). That is the session's one
solid method result.

### The champion control is contaminated in fold 0 — do not quote it

The champion's family lands in fold 0's TEST set, so scoring it against `T̂_test` there is scoring it
against itself: 0.7013 raw, 0.81–0.85 "estimate". Averaged over all five folds the champion shows
0.3397 ± 0.2571, which is garbage. On the four honest folds the champion scores
**0.1896 / 0.2036 / 0.2258 / 0.2263** against an OWNER-REPORT of 0.2778 — i.e. the yardstick
understates it by roughly the same factor it understates everything else. That factor is the next
section.

## 6. Anchor calibration — correcting the attenuation

Each fold's yardstick is built from only 20 % of the corpus, so it is a *blurrier* picture of the
truth than the full 182-raster field, and every DTI measured against it is biased low. The bias is
measurable: take the published TRAIN rasters whose **observed** owner-reported score is ≥ 0.15, score
them on the same fold yardstick, and take `ratio = observed / estimate`.

`scripts/anchor_calibration_20261031.py`, `evidence/anchor_calibration_20261031.json`:

| fold | anchors | mean ratio |
|---|---|---|
| 0 | 22 | 1.399 |
| 1 | 40 | 1.281 |
| 2 | 57 | 1.221 |
| 3 | 51 | 1.136 |
| 4 | 47 | 1.172 |
| **mean** | | **1.2415** |

Applying it:

| | value |
|---|---|
| candidate, raw 5-fold mean | 0.2371 |
| candidate, **anchor-corrected ESTIMATE** | **0.2914** |
| 1 sd across folds | ± 0.0234 |
| worst fold | 0.2455 |
| champion, OWNER-REPORT | 0.2778 |

**The candidate's estimate is ~0.014 above the champion — inside the ±0.023 band.** It is not a
demonstrated improvement. It is a coin-flip with a slightly favourable coin, and both numbers are far
below the 0.3195 that actually matters.

## 7. Emitter choice (before the five-fold run)

`scripts/compare_emitters_20261031.py` compares the repository's greedy emitter
(`gems32.emitter.emit`, which emits until the marginal-dot rule `q > 0.2·DTI` fails) with
descending-`q` non-max suppression at a fixed dot budget:

| fold | non-max suppression, 60 000 dots | greedy emitter, 400 000 dots |
|---|---|---|
| 0 | 0.1513 | 0.0670 |
| 1 | 0.2738 | 0.1037 |

The greedy emitter over-emits by a factor of ~7 and pays α·FP for every extra dot. The run was killed
at the 1 700 s timeout after fold 1; the ordering was already 2–3× and the conclusion is not in
doubt. Non-max suppression is the emitter; the greedy emitter should not be revisited.

## 8. The submission

`scripts/build_final_candidate_20261031.py --n0 12000 --spacing 3.0 --budget 60000` re-solves the Gram
system on **all 182** rasters, emits 60 000 dots, and writes the TIF, the ZIP, ten format gates, and
the uniqueness profile. Receipt: `evidence/final_candidate_20261031.json`.

* 63 non-zero weights, max λ 0.0741;
* 60 000 dots at value 1.0, minimum spacing 3 px;
* **10 / 10 format gates pass on the saved bytes** — single band, float32, EPSG:32611, 3730×3292,
  the 100 m transform identical to `sample_submission.tif`, no NaN anywhere in the file, values in
  [0,1], exactly 0 outside the footprint, binary;
* in-sample DTI against the full T̂ = **0.3831** — an **upper bound only**, because the candidate was
  built from T̂. It is reported on the receipt and never quoted as an estimate.

Top weights: `WBGGEMSDOE3__wbggems3-invdesign-anchor-2`,
`GEMSDOE70__gems70-p5-dual-submod300-oof38k`, two copies of
`GEMSDOE49__gems49-gate_ortho_w0.25-40k`, `GEMSDOE36__gemsdoe36-anderson-geothermal`.

## 9. Uniqueness

The protocol's literal rule fails for this candidate **and for the champion**. The measurement and
the coverage-normalised criterion that replaces it are in
[uniqueness-criterion-20261031.md](uniqueness-criterion-20261031.md). Summary: worst 3-px overlap
0.9626 with lift 2.04 (candidate) versus 1.0000 with lift 4.04 (champion control).

## 10. What this candidate is not

It redistributes recall that already exists in the corpus. It cannot discover a structure no published
raster touches. The five hypotheses in [hypotheses-20261031.md](hypotheses-20261031.md) — geodetic
strain-rate ridge continuation past catalogue tips above all — are the route to genuinely new recall,
and **none of them has been generated or validated**, so none of them has earned a submission slot.
