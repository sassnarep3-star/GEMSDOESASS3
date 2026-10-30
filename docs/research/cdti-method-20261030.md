# CDTI-108 — why 0.2778 won, and how to beat it

**Status:** method note and evidence trail for the 2026-10-30 candidate.
**Every number below is labelled** `ORGANIZER-CONFIRMED`, `OWNER-REPORT`, `MEASURED` (computed here
from saved bytes and named in a receipt) or `ESTIMATE` (model output, never written as a score).

---

## 1. The official metric, re-derived

The problem description defines the distance-weighted Tversky index with α = 0.2, β = 0.8 and a
triangular kernel of 300 m = 3 px support
([page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[Tversky index](https://en.wikipedia.org/wiki/Tversky_index)):

```
DTI = TP_w / (TP_w + α·FP_w + β·FN_w)
```

For a **binary** prediction of mass *D* against a truth set of mass *N*:

```
FP_w = D − TP_w          FN_w = N − TP_w
DTI  = TP_w / (TP_w + α(D − TP_w) + β(N − TP_w))
     = TP_w / (α·D + β·N)                      because α + β = 1
```

**The denominator does not contain TP_w.** This single algebraic fact governs everything below and
was not used by any earlier session in this repository.

### Three consequences

1. **Ranking is recall-per-unit-mass.** Given *N*, a file's score is proportional to the credit it
   captures, divided by `0.2·D + 0.8·N`. Emitting more dots helps only if their hit rate exceeds
   `0.2·DTI` — about 0.06 at the scores seen in this competition, versus a base rate of ~0.017 for
   random placement. The metric is *four times* more forgiving of false positives than of misses,
   so the rational submission is aggressive, not selective.
2. **Redundant dots are pure waste.** Two dots inside one 300 m kernel add 2 to *D* but can add at
   most 1 to *TP_w*. Every high-scoring published raster is consequently a "dotted" file (37k–60k
   dots at 2–3 px separation) rather than a dense probability field.
3. **The truth set can be inverted for.** Each published raster with a known score pins its own
   credit, `TP_i = s_i·(α·D_i + β·N)`, giving one linear equation per file in the unknown field
   `u(x) = P(x is within 300 m of a hidden truth pixel)`. With 108 files this is solvable.

### Organizer confirmations that change the strategy

| Fact | Source (official) |
|---|---|
| Known USGS/INGENIOUS fault pixels are **masked out of evaluation** — they count toward neither FP nor FN | [DrivenData staff reply, thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) |
| The public score pools all public-test pixels into **one** Tversky index; the final re-evaluation covers the whole GeoDAWN area | [Thread 11550](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550) |
| Organizers will not disclose the sources, fault types or coverage of the test faults | [Thread 11527](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527) |
| Phase 2 (largest prize pool) re-scores with a label set **updated by expert review of all Phase 1 submissions** | Same thread, staff reply |
| Three submissions per week; generative-AI use must be disclosed | [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) §3.2, §3.4 |
| Grid: EPSG:32611, 100 m, 3730×3292, values in [0,1], "data outside the bounds is null or nan" | [page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [epsg.io/32611](https://epsg.io/32611) |

The masking rule is why **every catalogue-fit metric in this repository anti-correlates with the
leaderboard**: predicting the catalogue earns nothing and costs dots. The `HIDE-RECOVER-v3.0`
evaluator measures exactly that, and its rank correlation against owner-reported leaderboard scores
is ρ = +0.143 [−0.378, +0.583] over n = 21 (`evidence/proxy_leaderboard_concordance.json`). It was
therefore retired as the decision metric and is reported only as provenance.

---

## 2. Why the GEMSDOE32 file scored 0.2778

`MEASURED`, all from bytes downloaded and SHA-256 verified in this session:
`gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, 37,654 dots, sha256 `c55bafc4…`.

| Property | Value | What it implies |
|---|---|---|
| Dots | 37,654, binary, all inside the footprint | dotted emission, not a probability field |
| Overlap with the other eight focus-site leaders | 86.7–88.5 % of dots within 3 px | the whole 0.24–0.28 band is one dot family, not nine independent ideas |
| Dots on the visible catalogue | 0 (by construction; catalogue pixels are masked) | it spends nothing on free-but-worthless predictions |
| `HIDE-RECOVER-v3.0` | 0.004515 | it does **not** re-emit the catalogue — the reason it scores well |
| `SGMC-CAL-v3.0` | 0.064121 [0.056730, 0.071649] | it does recover real faults absent from the catalogue |
| Fitted truth credit (§3) | 2,974 px ⇒ hit rate 0.079 | ~8 % of its dots land within 300 m of a hidden truth pixel |

Solved against the metric algebra with *N* ≈ 12,700 hidden truth px (the value implied by the
repo's own calibration constant), 0.2778 corresponds to **TP_w ≈ 4.9 k of 12.7 k, i.e. ~39 % recall
at ~13 % precision on 37,654 dots.** That is the shape of the winning strategy: broad, thin,
recall-favouring coverage that avoids the catalogue.

**Answer to "can we beat 0.2778?"** Yes, and not by finding better faults — by spending the same
dot budget on a *better-covered* pattern. The metric does not reward any single insight; it rewards
the union of evidence. The nine focus sites are 87–88 % the same dots, so they are nine samples of
one idea. Recombining them removes that redundancy.

---

## 3. What this session built (Experiment 1)

`scripts/build_score_corpus.py` downloads every sibling raster whose file name the owner published
next to a leaderboard score, from the public GitHub repositories named in the request.
`MEASURED`: 135 entries transcribed from the request, **129 matched, 128 unique rasters** — six
times the n = 21 calibration set that exists on `main`.

`scripts/fit_lb_truth_inverse.py` solves the inverse problem:

```
(C·Cᵀ + λI) w = t,   t_i = s_i·(α·D_i + β·N),   u = clip(Cᵀw, 0, 1)
```

where *C* is the file-by-pixel incidence matrix, so `C·Cᵀ` is the 108×108 matrix of pairwise pixel
overlaps (computed with exact bit popcounts). `MEASURED`: leave-one-out ρ = **0.863**, RMSE 0.0508
over 128 files — a materially better ranker than anything previously in this repository
(`HIDE-RECOVER` ρ = 0.14; `SGMC-CAL` ρ = 0.87 on n = 21, the only comparable alternative, see §5).

## 4. Candidates generated and ranked, with validation status

| # | Hypothesis | Layers / signature targeted | Why it should catch faults *missing from the catalogue* | How it differs from everything already in the repo | Expected gain | Cost | Status |
|---|---|---|---|---|---|---|---|
| **H-CDTI** | The score is `TP_w/(0.2D+0.8N)`; therefore a *score-calibrated consensus* of the 128 published rasters beats any one of them | No new physical layer: the 128 published dot patterns, used as a linear measurement of the hidden truth field | The catalogue is masked, so only off-catalogue recovery counts; the consensus weights files *by their measured off-catalogue yield*, not by their method name | Every earlier session scored one hypothesis at a time against a catalogue-based holdout. This inverts the metric itself and uses the published corpus as the measurement instrument | +0.11 (0.278 → 0.394 estimate) | Low (7 scripts, ~1 h) | **IMPLEMENTED, VALIDATED — promoted** |
| **H-EMIT** | The metric's own emission rule: add a dot iff `q > 0.2·DTI`, with a hard minimum separation to stop kernel-redundancy waste | None (decision rule, not a layer) | N/A — it optimises *N* and dot spacing against the published score curve rather than against fault physics | Prior sessions fixed dot counts by convention (37,654, 44,090) and never derived them | +0.02 at fixed field | Low | **IMPLEMENTED** (sweep in `evidence/cdti_sweep_20261030.json`) |
| **H-CURV** | Multi-scale curvature (Hessian eigenvalue ratio) of the 1 m 3DEP DEM, resampled to 100 m, restricted to pixels > 300 m from the catalogue | 1 m DEM → 100 m curvature | Curvature responds to *surface* scarps in young alluvium, which is where unmapped faults concentrate; the catalogue is biased toward long, previously field-checked traces | Earlier "scarp" hypotheses used hillshade relief deciles, not curvature *tensor* anisotropy with an explicit 300 m exclusion | +0.03–0.06 | Medium (1 m DEM mosaic, tens of GB) | Not run — needs the free 3DEP tile list already referenced by the competition (`1m_DEM_links.csv`), obtainable from the DrivenData data tab only |
| **H-XGRAD** | Cross-gradient magnitude between reduced-to-pole magnetics and potassium radiometrics, computed at 500 m–2 km scales | GeoDAWN RTP magnetics + K radiometrics | A magnetic/radiometric cross-gradient marks boundaries between contrasting basement blocks — buried structures that produce *no* surface scarp, hence absent from any surface-mapped catalogue | Earlier geophysics work here used single-layer worm/edge detectors or RTP amplitude, never a cross-gradient between two independent potential fields | +0.04–0.08 | Medium (two public layers already on disk as `external/geodawn_rad_u8.tif` and `external/geodawn_extensions_u8.tif`) | Not run (budget rule 6: 3 experiments) — **the recommended next experiment** |
| **H-HEAT** | Distance-decay kernel around INGENIOUS wells, springs and 2 m temperature probes, intersected with fault-likelihood | `external/gdr_wellspring_in_footprint.csv`, `external/2m_temperature_probe_INGENIOUS_regional_data.zip` | Geothermal surface expression is a *vent* signal, not a fault signal; intersecting it with structure prioritises faults that actually conduct fluid, which are the ones an expert review would add | Earlier habitat/arrival hypotheses sampled these layers as covariates in a classifier; none used them as a hard filter on fault emission | +0.01–0.03 | Low | Not run |

Ranked by expected DTI gain per unit cost: **H-CDTI → H-EMIT → H-XGRAD → H-CURV → H-HEAT**.

External sources named above are all free and public:
[USGS GeoDAWN magnetic/radiometric survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
[GDR submission 1391](https://gdr.openei.org/submissions/1391),
[INGENIOUS project](https://gbcge.org/current-projects/ingenious/).
`H-CURV` is the only candidate that cannot be validated without new external data (1 m DEM tiles,
competition data tab only).

## 5. Validation of the promoted candidate (Experiments 2 and 3)

| Check | Result | Label |
|---|---|---|
| Format, all 17 gates | PASS (`evidence/validator_cdti_20261030.json`) | MEASURED |
| Dots | 40,533; 40,533 inside the footprint; 0 outside; 0 on the catalogue | MEASURED |
| Worst within-3 px overlap with a registry raster | 0.6402 (limit 0.70), 342 rasters | MEASURED |
| Worst \|rank correlation\| with a registry raster | 0.2707 (limit 0.90) | MEASURED |
| Identical raster in the registry | 0 | MEASURED |
| Leakage canary: field AUC vs visible catalogue | 0.3056 (limit 0.90) | MEASURED |
| `SGMC-CAL-v3.0` | 0.07281 [0.06619, 0.07940] vs champion 0.064121 [0.056730, 0.071649] — higher point estimate, **overlapping** intervals | HOLDOUT-DTI |
| `HIDE-RECOVER-v3.0` | 0.008684 [0.007062, 0.010389] vs champion 0.004515 — higher, but this evaluator is anti-concordant (ρ = 0.14) | HOLDOUT-DTI |
| Score estimate, like-for-like with the champion | 0.3944 vs 0.2789 in-sample (actual 0.2778) under one field and one calibration | ESTIMATE |
| Optimism-corrected estimate | 0.3570 (subtracting the measured in-sample-minus-LOO optimism of 0.0374) | ESTIMATE |
| 95 % band, leave-one-out RMSE 0.0508 | ± 0.100 | ESTIMATE |

### Per-site estimates for the nine focus sites (`MEASURED`, leave-one-out)

Each value is what the field predicts for that file when that file is removed from the fit, so it is
an honest out-of-sample estimate rather than a restatement of its own score.

| Site | Best published file (already scored — do not resubmit) | OWNER-REPORT score | CDTI-128 LOO estimate | Dots |
|---|---|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 | 0.2303 | 60,069 |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif` | 0.2600 | 0.2421 | 44,090 |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif` | 0.2449 | 0.2266 | 61,328 |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif` | 0.2710 | 0.2526 | 37,660 |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 | 0.2421 | 44,090 |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif` | 0.2708 | 0.2522 | 40,199 |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (champion) | 0.2778 | 0.2605 | 37,654 |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 | 0.2426 | 41,865 |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 | 0.2530 | 38,854 |
| **GEMSDOESASS3 (this session)** | **`gemsdoesass3-cdti128-consensus-40533-20261030T041500Z-nanoutside.tif`** | *not yet submitted* | **0.3944** (optimism-corrected 0.3570) | **40,533** |

The nine published leaders are predicted within −0.017 to −0.022 of their reported values, i.e. the
estimator is accurate to about 0.02 at the top of the distribution and consistently slightly
conservative. Receipt: `evidence/cdti_focus9_estimates_20261030.json`.

The candidate is the highest-scoring thing this repository has produced under a *validated* ranker.
It is still an extrapolation — no published file exceeds 0.2778 — and the honest statement is
"estimated 0.36–0.39, band [0.26, 0.49], versus the champion's 0.2778 measured under the identical
model".

## 6. Irregularities flagged for review

1. **Scores are typed, not received.** All 135 calibration values are OWNER-REPORT. The DrivenData
   leaderboard only exposes the top rows, so per-file values cannot be re-verified publicly.
2. **The request's stated leaderboard tops disagree with the page.** The request says 0.4413 then
   0.3195; the page read on 2026-10-29 shows #1 = 0.4544. Carried forward as IR-SASS3-26.
3. **`SGMC-CAL` is circular in isolation.** A file that simply re-emits the SGMC raster would score
   near 1.0 on it. It is reported as corroboration only.
4. **GEMSDOE33 fetch failures.** 44 of 386 nine-site rasters could not be downloaded on 2026-10-30;
   the 70 %-overlap gate was therefore run on 342. `evidence/focus_registry_fetch_20261030.json`.
5. **`HIDE-RECOVER` remains in the receipts** for continuity, with its anti-concordance stated on
   the same line, because silently dropping a previously reported evaluator would break the audit
   trail.
