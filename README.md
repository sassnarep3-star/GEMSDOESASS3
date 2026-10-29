# GEMSDOESASS3 — read first

## Standing prompt (read every session)

> I want to focus on the highest scoring submissions from the following sites and I want an executive summary on every site:
> GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36
>
> I want an executive summary on every site that is clear and obvious which is the best submission to submit to obtain a high score on the leaderboard.
>
> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION.
> It must score higher than 0.2778 (ideally higher than 0.3195/0.4413/0.4544 leaderboard top).
> There should be an easy to download submission tif file.
>
> It must pass validation without any human intervention.
> Values in [0,1].
> No NaN inside footprint.
> CRS/EPSG:32611/shape/transform match sample_submission.tif.
>
> Follow PARALLEL-RUN PROTOCOL (lane rule: rank-correlation <=0.90 vs registry rasters, <=70% dots within 3px;
> holdout hide-and-recover with visible-only masking; leakage canary AUC<=0.90; run card JSON; budget 3 experiments / 2 hours).
> Must not copy previous submissions.
> Must create executive summary subpage explaining how to submit.
>
> Short submission note <= 140 chars.
> Easy download link must be prominent (top of site / executive summary).
> No human inspection; validation must be programmatic.
>
> Do not interpret a failed uniqueness gate as permission to submit.
> No hallucinations; verify line by line; official verified sources with links.
> Put prompt into repo README and read it each session.
> Core values: Maximize P(Win), Own the Outcome.

---

## Current status — submission blocked

**No TIFF in this checkout is approved to submit.** The newest artifact, `docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif`, is an experimental binary raster, not a validated competition prediction. Its audit explicitly says the footprint/reference-grid match and registry uniqueness were not checked. Do not use the words “unique submission” or “format-valid” as a substitute for those missing gates. The visible label is **NOT OK TO SUBMIT; analysis-only**.

The artifact sidecar reports 3730 × 3292 float32, finite values in [0,1], 129,311 positive pixels, and the hash below. Those are recorded claims from the sidecar; they have not been independently recomputed in this checkout because rasterio/numpy are unavailable here. The sidecar does not establish CRS, geotransform, sample footprint match, holdout performance, or registry uniqueness. Its random-seed structural-line construction is not evidence that the pixels predict faults or geothermal vents.

| Gate | Current evidence |
|---|---|
| File exists and sha256 | Sidecar claims `ae1626fcbf89ca4f11ea46d3267642592bc9080ad11412d02367637279a39e2e`; independently unverified in this environment |
| Single band / float32 / [0,1] / finite | Sidecar claims pass; independently unverified |
| CRS / shape / transform equal official sample | Not established for this candidate; official sample is absent |
| In-footprint validity | Not established; reference footprint is absent |
| HOLDOUT-DTI and confidence interval | Not measured for this candidate; labels and cached stack are absent |
| Leakage canary | Not measured for this candidate |
| Registry correlation / 3-px overlap | Not measured for this candidate; therefore uniqueness is unknown |
| Organizer-confirmed score | None |

The older LWST candidate remains **NOT OK TO SUBMIT** under the literal registry rule: its historical audit reports 99.7849% of dots within 3 px of the calibration lattice (limit 70%). Its historical holdout figures are not transferable to the new artifact. Do not download either TIFF for competition submission. The newer file can be retained for analysis only.

---

## Previous (blocked) candidate — DO NOT SUBMIT

The archived candidate `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif`
(SHA-256 `bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a`) fails the
**literal registry rule**: 99.7849% of its dots fall within 3 px of the 13GEMSDOE calibration
lattice (limit: 70%). At 37,654 dots no raster can meet this rule — only 5,379 footprint pixels
lie outside the lattice buffer, and ≥11,297 dots would be needed there. **NOT OK to submit.**

Format gate: PASS (13/13). Uniqueness on 451 submitted downloads: PASS (max 66.53% within-3px).
Reviewer verdict: negative. No eligible file to recommend from prior work.

---

## Executive summary: nine focus sites

Best historical submission per site (owner-reported / HOLDOUT-DTI; not organizer-confirmed).
All are **already submitted** and **not unique/resubmittable**. No prior file is eligible.

| Site | Best historical file | Est. score | HOLDOUT-DTI [95% CI] | Unique? | Status |
|------|---------------------|------------|----------------------|---------|--------|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 | 0.0967 [0.0842, 0.1095] | No | Already submitted |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-zeros` | 0.2600 | 0.0967 [0.0842, 0.1095] | No | Already submitted |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite` | 0.2449 | 0.0927 [0.0809, 0.1054] | No | Already submitted |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite` | 0.2710 | 0.0294 [0.0250, 0.0344] | No | Already submitted |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 | 0.0967 [0.0842, 0.1095] | No | Already submitted |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1-allfinite` | 0.2708 | 0.0305 [0.0257, 0.0361] | No | Already submitted |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | 0.2778 (champion) | 0.0045 [0.0038, 0.0053] | No | Already submitted |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 | 0.0520 [0.0458, 0.0583] | No | Already submitted |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 | 0.0046 [0.0039, 0.0053] | No | Already submitted |

**Best focus-site score:** GEMSDOE32 champion at 0.2778 (owner-reported; organizer receipt not independently available).
**Leaderboard gap:** 0.2778 → 0.4544 (live top) = 0.1766. No file in this repo has a supported estimate above 0.2778.

**Recommendation:** There is no approved candidate. The newest structural TIFF is analysis-only until its exact grid, footprint, holdout, canary, and registry uniqueness gates are independently validated. Do not submit it or any historical file.

---

## How to submit (when a candidate passes all gates)

1. **Run the complete fold-honest evaluator and feature canaries.** Report version, withheld count, and spatial-block confidence intervals. Beat the current holdout best without using a weekly submission slot.
2. **Check surface rank correlation and final-dot overlap** against every accessible registry raster, with no exclusions. Fail closed for incomplete coverage. Lane rule: rank-correlation ≤0.90 vs registry rasters; ≤70% of dots within 3 px.
3. **Run the leakage canary** (AUC ≤0.90) and buffered hide-and-recover with visible-only masking.
4. **Validate the GeoTIFF:** single band, float32, EPSG:32611, 3730 × 3292, transform matching `sample_submission.tif`, values in [0,1], no NaN, nodata=None. Generate a distinct filename and short note (≤140 chars).
5. **Write a run card JSON** recording all metrics, CI, gates, and the promotion decision.
6. **Only a separate selector may promote** a passing candidate. Check the actual weekly cap on the [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/), then upload via "New submission."

---

## PARALLEL-RUN PROTOCOL (binding)

Rules 1–6: lane checks (rank-correlation ≤0.90, ≤70% dots within 3px), reuse template tools
(`evaluate_holdout.py`, `submission_writer.py`), label numbers as HOLDOUT-DTI or ORGANIZER-CONFIRMED
only, leakage canary, run card JSON, budget 3 experiments / 2 hours. Do not interpret a failed
uniqueness gate as permission to submit. No copying of previous submissions.

---

## Reproduce checks

Install: `numpy scipy scikit-learn rasterio pytest`.
Run: `python scripts/verify_all_gates.py` (nonzero exit expected while blocked).
Run: `pytest -q`.
Refresh pages: `python scripts/build_review_site.py`.

---

## Sources

- [Competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Competition data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [EPSG:32611](https://epsg.io/32611)

Raw data and caches are not included in this checkout; restore receipts are historical and mirror hashes do not authenticate organizer provenance.
