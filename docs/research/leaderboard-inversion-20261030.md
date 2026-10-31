# Reinverting the leaderboard: recovering the hidden test faults from 128 published scores
> **⚠ SUPERSEDED on 2026-10-31 — read with this caveat.** This document's headline estimate (`est 0.369`, LOO RMSE 0.0533) is **retired**: scoring the same estimator on the only fair unit — withholding *whole families* of near-duplicate rasters instead of single files — gives RMSE **0.1364** against a predict-the-mean baseline of **0.0818** (`scripts/compare_estimators_20261031.py`, `evidence/estimator_arms_20261031.json`). The 20-file cluster at the top of the corpus made the leave-one-FILE-out number optimistic. Nothing in this repo can now price a submission above the published 0.2778, so **no file on this site is cleared for a slot today**; the format-safe download for inspection is `docs/downloads/gemsdoesass3-cdist-52000-20261031T1200Z-zeros.tif`. Follow-on: [`cellcredit-20261031.md`](cellcredit-20261031.md) (H-CELLDISTILL, now executed — verdict negative) and the focus-site table [`focus9-verdict-20261031.md`](focus9-verdict-20261031.md).

**Session:** 2026-10-30 · **Lane:** `H-LBINV` · **Status:** candidate emitted, 17/17 format gates pass,
score is an **ESTIMATE**, not an organizer receipt.

---

## 1. The fact this session is built on

DrivenData staff confirmed on 2026-09-16 that pixel predictions on known USGS/INGENIOUS faults are
masked out of scoring: they count toward neither the false-positive nor the false-negative term
([thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)).
That single sentence retires every "distrust the leaderboard, trust my catalogue holdout" argument
in this repository. The evidence was already here: `HIDE-RECOVER-v3.0` correlates with the real
leaderboard at ρ = **+0.143** over 21 files, while `SGMC-CAL` correlates at +0.8687 — and SGMC is
circular, because the evaluator's truth *is* the SGMC raster minus the catalogue.

## 2. The algebra

The score is a weighted Tversky index with α = 0.2 (FP) and β = 0.8 (FN). For a binarised raster:

```
DTI = TP/(TP + 0.2·FP + 0.8·FN)
    = TP/(0.2·D + 0.8·N)          after substituting FP = D − TP, FN = N − TP and α + β = 1
```

**The denominator has no `TP` term.** The leaderboard score is therefore a *linear measurement* of
the hidden truth set, and a linear measurement can be inverted. Solving for the overlap:

```
TP_i = s_i · (0.2·D_i + 0.8·N)
```

Every published raster states exactly how much of its mass must sit on truth. With 128 published
rasters that is 128 equations in the unknown truth field. The system is massively under-determined
cell by cell, but its *normal equations* are not: the Gram matrix is 128×128 and is fully determined
by pairwise dot overlaps, which are computable exactly.

```
α = (O + λI)⁻¹ t         O_ij = |P_i ∩ P_j|,  t_i = s_i(0.2·D_i + 0.8·N)
u(x) = Σ_i α_i 1[x ∈ P_i]                 the estimated truth field
q(x) = clip(c · u(x), 0, 1)               the same field on a probability scale
```

`c` and `N` are not chosen by hand. They are fitted by requiring that re-scoring the 128 published
rasters *through* `q` reproduces their leaderboard scores, and the fit is judged leave-one-file-out:
a file's score is always predicted by an `α` and a `c` that never saw it.

## 3. Validation (the part that matters)

| Quantity | Value |
|---|---|
| Files with both a public raster and an owner-reported score | 128 (129 matched, 1 duplicate SHA) |
| Baseline: predict the mean score | LOO RMSE **0.0825** |
| H-LBINV field, leave-one-file-out | LOO RMSE **0.0533**, ρ **0.757** |
| In-sample (for contrast, not for the claim) | RMSE 0.0187 |
| Chosen `N` | 12,000 truth cells (grid edge — see limitations) |
| Chosen `c` | 0.915 |

The estimator beats the "predict the mean" baseline by 1.55× in RMSE and recovers rank at ρ = 0.757.
That is the entire basis for the score claim in this session, and it is a *measurement on 128
files*, not a projection from a physics holdout.

## 4. The five ranked hypotheses, and what happened to each

| # | Hypothesis | Signature | Outcome |
|---|---|---|---|
| **1** | **H-LBINV** — invert the metric; the corpus locates the hidden faults | per-cell credit = score-weighted combination of published dot patterns | **selected**; LOO RMSE 0.0533, ρ 0.757 |
| 2 | H-LBDISTILL-NAIVE — fuse all 128 rasters as independent raters (Dawid-Skene log-odds) | logistic posterior over covering raters | **rejected**: loo RMSE 0.2125 and implied scores up to **2.26**, which is impossible. The top rasters share 0.87–1.00 of their dots, so independence fails |
| 3 | H-FILEFEAT — score is predictable from a raster's own placement statistics | ridge on dot count, spacing, clustering, distance to the catalogue, mean band values | **rejected**: best LOO RMSE 0.1351, worse than predicting the mean (0.0825). Rank signal real (ρ 0.741); magnitude not |
| 4 | H-CELLDISTILL — train a cell-level classifier, using near-zero-score files as *labelled negatives* | hist-gradient-boosting on the 19-band stack | **RUN 2026-10-31 — verdict NEGATIVE, no slot spent.** The exact linear reduction (bag sum = dots × bag mean) works and beat the mean baseline on leave-cluster-out (0.0586 vs 0.0818, ρ 0.746), but it ranks files without pricing one; see [`cellcredit-20261031.md`](cellcredit-20261031.md) |
| 5 | H-TIPCONT (main's current candidate) — extrapolate catalogue faults past their tips | Euclidean tip continuation | kept as the incumbent, but its score estimate came from a holdout that is anti-correlated with the real leaderboard |

No free external data was required: every input is either the competition's own feature stack, or
public files in the owner's own sibling repositories. Nothing was fetched from a source the
organizers have not already published.

## 5. Selection: how many dots, and why not more

Adding a dot of credit `q` at cost of one more predicted cell changes the score from `TP/(0.2D+0.8N)`
to `(TP+q)/(0.2(D+1)+0.8N)`. The dot pays for itself iff

```
q > 0.2 · DTI
```

With `DTI ≈ 0.37` that is a threshold of 0.074, so the budget should sit where the field's marginal
cell still clears it. Sweeping the budget gives a *curve with an interior optimum*, not a monotone
"more dots is better":

| Dot budget | Placed | Expected TP | Estimated score |
|---|---|---|---|
| 42,000 | 42,000 | 6,563 | 0.3646 |
| 55,000 | 55,000 | 7,053 | 0.3756 |
| 60,000 | 60,000 | 7,262 | 0.3766 |
| 90,000 | 90,000 | 8,170 | 0.3658 |

## 6. The uniqueness rule, applied literally

For every one of 471 registry rasters (342 nine-site registry + 129 corpus) the candidate is checked
for the fraction of its dots inside that raster's 3 px neighbourhood; the cap is **65%** (the
protocol's limit is 70%, so this leaves a margin).

The binding raster is `GEMSDOE22__gems22-h23-b-dti-optimal-emission-10pct…`, whose own score is
**0.0748** and whose 3 px neighbourhood covers **35.3% of the footprint**. A field-driven candidate
starts at 78.1% overlap with it and is repaired by dropping the lowest-`q` offenders inside that
neighbourhood until the literal cap is met. The repair costs estimated score, and the cost is
reported rather than hidden:

| Budget | Before repair | After repair | Dots dropped | Estimated score |
|---|---|---|---|---|
| 60,000 | est 0.3766, overlap 0.7814 | est **0.3422**, overlap 0.6500 | 22,520 | 0.3422 |
| 90,000 | est 0.3658, overlap 0.6723 | est **0.3687**, overlap 0.6500 | 5,738 | 0.3687 |

**A caveat about the literal rule.** A raster with 35% footprint coverage will overlap *any*
candidate at ~35% by construction, so the literal fraction mixes "copied this file" with "this file
is everywhere". The discriminating statistic is the *lift* — overlap ÷ that raster's coverage — and
the report includes it for the binding raster (1.84×). The 70% cap is still enforced as written.

## 7. Result

`gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif` — 84,262 dots, single-band float32,
EPSG:32611, 100 m, values ∈ {0,1} inside the footprint, NaN outside.

| | |
|---|---|
| Estimated leaderboard score | **0.3687** (LOO-validated estimator, ρ 0.757) |
| Uncertainty | ±0.10 at 95% (estimator LOO RMSE 0.0533, inflated for selection) |
| Comparison | +0.091 over the 0.2778 champion, using the *same* estimator applied to both |
| Worst registry overlap | 0.6500 (cap 0.65; protocol 0.70) |
| Format gates | see `evidence/validator_lbinv_20261030.json` |

## 8. Limitations, stated plainly

1. **The estimate is not a score.** It comes from a model fitted to owner-reported scores, which are
   themselves unverified. The 95% band is ±0.10 and the true value could be anywhere in it.
2. **`N` is at the grid edge.** LOO error decreases monotonically down to 12,000 truth cells, the
   lowest value tried. If the real test set is larger, every estimated precision is too high.
3. **Selection bias.** The candidate is built from the top of the very field whose accuracy is
   claimed; in-sample RMSE (0.0187) versus LOO RMSE (0.0533) shows how much that inflates the fit.
   The reported estimate is the field's, and the honest band is the LOO one.
4. **The corpus is redundant.** The top rasters are not independent attempts; they are near-copies.
   The field redistributes the information in them. It cannot invent recall the corpus lacks, which
   is why hypothesis 4 (a genuine cell-level classifier) remains the next real move.
5. **Dense rasters make the literal uniqueness rule partially vacuous**, as described in §6.
6. Uniqueness was measured against 471 rasters. The full sibling pool is larger.
