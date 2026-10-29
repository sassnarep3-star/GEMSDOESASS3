# GEMSDOESASS3 — read first

## Standing project brief (read at the start of every session)

**MUST GENERATE A UNIQUE TIF SUBMISSION** only after scientific, holdout, format, and complete uniqueness gates pass; otherwise publish a clearly labeled negative/archive-only result. Focus on the nine requested sites: **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36**. Maintain a clear executive summary for each site, investigate distinct and scientifically grounded hypotheses, validate them on the shared spatial holdout before any submission-slot decision, and make the download/submit decision unmistakable.

Core values: **Maximize P(Win)** and **Own the Outcome**. Prefer honest negative results to unsupported promotions. Do not invent scores, estimates, source verification, or uniqueness claims. Do not copy a prior raster for submission. Distinguish historical owner reports, HOLDOUT-DTI, projections, and ORGANIZER-CONFIRMED receipts.

### PARALLEL-RUN PROTOCOL (binding)

1. **One assigned method lane.** Before placement and on final dots, check rank correlation against every registry raster (limit 0.90) and fraction of candidate dots within 3 px of each registry raster (limit 70%). Any exceedance is a duplicate: record and stop. Missing registry coverage or pre-placement surface means uniqueness is **not cleared**.
2. **Reuse shared tools.** Use the cached features, `evaluate_holdout.py`, and `submission_writer.py`. Hide whole fault segments with a buffer; derive catalogue-based features only from visible faults; mask visible faults pixel-exactly; score pooled DTI (alpha 0.2, beta 0.8; 300 m triangular kernel). Fix shared-tool bugs in the template, not in a private fork.
3. **Label every score.** Report HOLDOUT-DTI with evaluator version, withheld-positive count, and 95% CI, or ORGANIZER-CONFIRMED with a submission-page receipt. A projection is never a score.
4. **Leakage canary.** Test each feature alone on holdout; AUC above 0.90 is leakage until proven otherwise.
5. **Run card.** Record hypothesis, mechanism, named non-fault mimic, holdout DTI/CI, registry correlation/overlap, raster SHA-256, validator output, unique name, <=140-character note, and promote/negative verdict.
6. **Budget and selector.** Stop after 3 experiments or 2 hours. Do not select or consume a submission slot from an experiment; promotion is a separate selector decision within the current weekly cap.

Before implementation, compare 3–5 hypotheses by layers, physical signature, why they can find faults missing from the catalogue, novelty versus this repo, non-fault mimic, qualitative expected direction, cost, and data needs. Validate the top candidate before spending a slot. Do not present an unvalidated score projection as a score.

## Current executive decision — 2026-10-29

> **NO FILE IS APPROVED FOR COMPETITION SUBMISSION. DO NOT SUBMIT EITHER CHECKED-IN TIF.**

The current archive is [`gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif`](docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif). It is a **synthetic diagnostic, not a prediction**: the generator uses an approximate ellipse as a placeholder footprint, invented sinusoidal pseudo-gravity, filtered random pseudo-potassium, and coordinate-derived pseudo-dilatation. It did not read official training features or USGS GeoDAWN values. The proposed geological mechanism is untested.

| Candidate file | Estimated competition score | Unique against all listed sites/registry? | Decision |
|---|---:|---|---|
| `gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif` | **NOT ESTIMABLE** — no valid HOLDOUT-DTI or organizer receipt | **NOT CLEARED** — one calibration-lattice witness only; full registry and pre-placement correlation missing | Archive download for analysis only. **DO NOT SUBMIT.** |

Local file-format inspection: one band, float32, EPSG:32611, 3730×3292, transform `(100, 0, 243350, 0, -100, 4508550)`, nodata=None, all values finite in [0,1]. This matches the checked-in grid specification, **not a direct comparison to the absent official `sample_submission.tif`**. There are 6,178 hard cells (`>0.5`) and 8,794 positive cells (`>0`). The exact current run card is [`evidence/current_run_card.json`](evidence/current_run_card.json).

A pinned public lattice check found 50.0% of 10 connected-component centroids and 3,905/8,794 = 44.4053% of all positive cells within 3 px (2,687/6,178 = 43.4930% of hard cells); sampled output-raster Spearman is -0.00163 on 300,000 pixels. That is below the limits for this one witness but **does not clear uniqueness** against the full registry or constitute the required pre-placement/full-footprint test. Receipt: `evidence/lattice_lane_check_selected_20261029.json`. No continuous pre-placement comparison, complete registry comparison, holdout DTI, or candidate-specific leakage canary was performed. The competing structural diagnostic (`gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif`) is also synthetic and archive-only; details are in `evidence/uniqueness_audit_structural_diagnostic_20261029.json`.

**Verdict: NEGATIVE / ARCHIVE ONLY — NOT OK to submit.** SHA-256: `7ab47cf538791e921fc54544b1979e93fc25acda1d91aa5528e940f67359f41f`.

Current note (112 characters): `Archive-only synthetic BGK-PBE stand-in; no real features, holdout, or complete uniqueness check. DO NOT SUBMIT.`

## Nine-site historical executive summary

The results below are **OWNER-REPORT / user-provided historical scores**, not independently verified submission receipts and not estimates for either archive raster. These files have already been submitted; do not re-submit them.

| Site | Highest historical file reported | Historical result (OWNER-REPORT) | Unique / eligible as a new submission? |
|---|---|---:|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 | No — already submitted |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 | No — already submitted |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 | No — already submitted |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 | No — already submitted |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 | No — already submitted |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/) | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 | No — already submitted |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/) | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | **0.2778** | No — already submitted |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 | No — already submitted |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/) | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 | No — already submitted |

**Why did GEMSDOE32 report 0.2778?** Available repository analysis describes the B=2 raster as related to the D2.8/H19-5 family with a catalogue collar removed. Removing mapped catalogue pixels may plausibly favor uncatalogued targets and match a distance-weighted metric, but that is a hypothesis, not causal proof. Historical evidence contains conflicting score-status metadata; an organizer receipt was not checked in this review. No current candidate is shown to exceed 0.2778.

The request contains conflicting leaderboard snapshots (0.3195 and 0.4413); older repository evidence reported 0.4544 as of 2026-10-27. The live leaderboard was not refreshed in this review, so none is asserted to be the current top score.

## Submission instructions (for a future approved file)

1. Download only a file explicitly marked **OK TO SUBMIT** in its current run card and page. The link above is archive-only and not approved.
2. On DrivenData, choose **New submission**, select the single-band GeoTIFF (or a ZIP containing exactly one GeoTIFF), and enter the approved unique name and <=140-character comment.
3. Check CRS, dimensions, and geotransform directly against the official sample. Validate finite predictions in [0,1]. Do not assume outside-footprint fill conventions; use the official sample and competition validator rules.
4. Check the actual submission cap before upload. Disclose generative-AI use as required by the rules. Record an organizer receipt before claiming a score.

The standalone how-to page is [`docs/executive-summary.html`](docs/executive-summary.html).

## Findings and next steps

- This checkout contains no official `training_features.tif`, `labels.tif`, `sample_submission.tif`, 386-raster registry, or cached feature stack. JSON receipts do not replace raster inputs for fresh independent evaluation.
- The older LWST candidate has a historical literal 70% overlap failure against the calibration lattice (99.7849% within 3 px); its prior promotion claim was retracted.
- The BGK-PBE idea is listed as a distinct research hypothesis, but the raster uses synthetic placeholder fields and footprint. No geological model experiment or submission slot was used in this review.
- Research proposals, caveats, and ranked alternatives: [`docs/research/hypotheses_ranked_20261028.md`](docs/research/hypotheses_ranked_20261028.md), [`docs/hypotheses.md`](docs/hypotheses.md), [`docs/research/independent-review-20261028.md`](docs/research/independent-review-20261028.md), and [`docs/research/repo-review-20261029.md`](docs/research/repo-review-20261029.md). These are hypotheses, not validated gains. The legacy hypothesis document is internally inconsistent and has a warning banner.
- Irregularities: [`docs/irregularities.md`](docs/irregularities.md).

Immediate actions: restore the authenticated competition rasters; verify file provenance and exact band schema; run the shared fold-honest evaluator and single-feature canaries; compare pre-placement and final dots against the complete accessible registry; only then produce a submission candidate and selector packet.

## Official and primary references

- [Competition overview/rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Data tab (login may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS Great Basin project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)
- [Tversky index background](https://en.wikipedia.org/wiki/Tversky_index) (secondary reference; competition definition takes precedence)

## Reproduce checks

```bash
python -m pip install numpy scipy scikit-learn rasterio pytest
python scripts/verify_all_gates.py --expect-blocked
python -m pytest -q
```

The gate verifier should pass format/record integrity but keep holdout, canary, and complete uniqueness gates blocked while evidence is missing. That is the correct fail-closed result—not a submission clearance.
