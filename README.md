# GEMSDOESASS3 — read first

## Standing project brief (read at the start of every session)

**MUST GENERATE A UNIQUE TIF SUBMISSION** only after scientific, holdout, format, and complete uniqueness gates pass; otherwise publish a clearly labeled negative / archive-only result. Build an auditable, useful system for the DOE GEMS geothermal fault-mapping competition. Focus on the nine requested repositories: **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36**. Maintain a clear per-site executive summary; investigate promising, genuinely distinct geological hypotheses; validate them with the shared spatially blocked holdout before any submission-slot decision; produce a correctly formatted GeoTIFF only when all required gates pass; and make the download / submission status unmistakable.

Core values: **Maximize P(Win)** and **Own the Outcome**. Prefer honest negative results to unsupported promotions. Do not invent a score, estimate, source verification, or uniqueness claim. Do not copy a prior raster for submission. Separate historical reports, HOLDOUT-DTI, projections, and ORGANIZER-CONFIRMED receipts. Keep experiments within the parallel-run cap.

### PARALLEL-RUN PROTOCOL (binding)

1. **One assigned method lane.** Before placement and on final dots, check rank correlation against every registry raster (limit 0.90) and fraction of candidate dots within 3 px of each registry raster (limit 70%). Any exceedance is a duplicate: log it and stop. Missing registry coverage or missing pre-placement surface means uniqueness is **not cleared**.
2. **Reuse shared tools.** Use the shared cached features, `evaluate_holdout.py`, and `submission_writer.py`. Hide whole fault segments with a buffer; derive catalogue features only from visible faults; mask visible faults pixel-exactly; evaluate pooled DTI (alpha 0.2, beta 0.8; 300 m triangular kernel). Fix shared-tool bugs in the template rather than keeping a private fork.
3. **Label every score.** Report HOLDOUT-DTI with evaluator version, withheld-positive count, and 95% CI, or ORGANIZER-CONFIRMED with the submission receipt. A projection is never a score.
4. **Leakage canary.** Test every feature alone on holdout before trusting it; AUC above 0.90 is leakage until proven otherwise.
5. **Run card.** Record hypothesis, mechanism, plausible non-fault mimic, holdout result and CI, registry correlation/overlap, raster SHA-256, validator output, unique name, <=140-character note, and promote/negative verdict.
6. **Budget and selector.** Stop at 3 experiments or 2 hours. Do not pick a submission or consume a weekly slot from an experiment; promotion is a separate selector decision using the current competition cap.

Before new implementation, compare 3–5 candidate hypotheses by layer, physical signature, why it could identify uncatalogued structures, method novelty, non-fault mimic, expected direction (not invented numeric uplift), cost, and data requirements. Validate the top candidate before spending a slot. If required data cannot be validated as obtainable, do not claim viability.

## Current executive decision — 2026-10-29

> **NO submission is currently approved. Do not submit any TIF in this repository.**

An archive-only diagnostic GeoTIFF exists at [`docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif`](docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif). It is **not a scientifically validated prediction**: it was produced by a hand-coded corridor pattern, not by the competition feature stack. Its local file-format checks pass against a grid recorded in `data/prepared_manifest.json`, but the official sample raster is absent for direct comparison. No holdout score, leakage canary for this raster, or complete registry uniqueness audit is available. A pinned lattice check found **54,872 / 129,311 = 42.4341%** of its positive pixels within 3 px of that one witness; this single comparison does not clear uniqueness against the registry. The generator targeted 10,000 centers but radius-2 disks yield 129,311 positive raster pixels.

**Verdict: NEGATIVE / ARCHIVE ONLY — NOT OK to submit.** SHA-256: `ae1626fcbf89ca4f11ea46d3267642592bc9080ad11412d02367637279a39e2e`.

| Candidate file | Estimate of competition score | Unique against all listed sites/registry? | Download / submit decision |
|---|---:|---|---|
| `gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif` | **NOT ESTIMABLE** — no valid HOLDOUT-DTI or organizer receipt | **NOT CLEARED** — one lattice comparison only; full registry and pre-placement surface missing | Archive download for analysis only. **DO NOT SUBMIT.** |

The exact current run card is [`evidence/current_run_card.json`](evidence/current_run_card.json); the independently recorded one-witness overlap is [`evidence/uniqueness_audit_current_candidate_20261029.json`](evidence/uniqueness_audit_current_candidate_20261029.json). Current note (91 characters): `Archive-only synthetic corridor raster; no holdout or full-registry uniqueness clearance.` The old LWST run card and its claims are historical records, not the status of an approved candidate.

## Nine-site historical executive summary

The scores below are **OWNER-REPORT / user-provided historical results**, not estimates for the archive-only candidate and not independently verified submission-page receipts. These historical files are already submitted; do not re-submit them. A historical site score does not establish that a new file is unique or likely to score similarly.

| Site | Highest historical file reported | Historical score (OWNER-REPORT) | Unique / eligible as a new submission? |
|---|---|---:|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 | No — historical, already submitted |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 | No — historical, already submitted |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 | No — historical, already submitted |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 | No — historical, already submitted |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 | No — historical, already submitted |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/) | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 | No — historical, already submitted |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/) | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | **0.2778** | No — historical, already submitted |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 | No — historical, already submitted |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/) | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 | No — historical, already submitted |

**Why did GEMSDOE32 report 0.2778?** The available repository analysis describes its B=2 raster as related to the D2.8/H19-5 family with a catalogue collar removed. That is a plausible metric-alignment explanation: removing already mapped catalogue pixels may direct positives toward the challenge's uncatalogued target, while the spatial allocation may match its distance-weighted scoring kernel. It is not a causal proof. The available artifacts also contain conflicting score-status metadata; no organizer receipt was independently checked for this review. Therefore 0.2778 remains OWNER-REPORT, not a verified causal result. No candidate here has evidence for a score above it. The request contains conflicting leaderboard snapshots (0.3195, 0.4413, and older repository evidence of 0.4544); the current live leaderboard was not verified in this review.

## Submission instructions

When a candidate is eventually promoted by the separate selector:

1. Download the promoted single-band GeoTIFF only after the page labels it **OK TO SUBMIT**. An archive-only link is not approval.
2. On DrivenData's competition page, choose **New submission** and select the `.tif` (or a `.zip` with exactly one GeoTIFF).
3. Confirm single band and exact CRS, shape, and geotransform match to the official `sample_submission.tif`; validate the full array in `[0,1]` and finite as required by the portal. Do not assume outside-footprint NaN handling; test against the provided sample and validation requirements.
4. Enter the unique submission name and <=140-character note shown in the approved run card. Disclose generative-AI use as required by the official rules.
5. Check the actual weekly submission cap on the submission page. Uploading is an owner action; this project does not claim a submission receipt or score until one is recorded.

A standalone how-to page is at [`docs/executive-summary.html`](docs/executive-summary.html).

## Review findings and research queue

- The repo contains historical experiment/evaluator artifacts, but this checkout has **no** official `training_features.tif`, `labels.tif`, `sample_submission.tif`, 386-raster registry, or cached feature stack. Existing JSON receipts do not replace source rasters for a fresh independent recomputation.
- One earlier LWST candidate is blocked by the literal 70% overlap rule: its 3-px overlap with the pinned lattice was recorded as 99.7849%. Its prior dashboard language claiming promotion was retracted. Do not use its old report as current approval.
- A previous experimental hypothesis `H-SASS3-E` (basement-depth curvature) is recorded negative. The next hypotheses and their data needs are documented in [`docs/research/independent-review-20261028.md`](docs/research/independent-review-20261028.md) and [`docs/hypotheses.md`](docs/hypotheses.md). They are proposals, not validated gains. No new model experiment or submission-slot use was performed during this review.
- Irregularities and conflicting historical labels are tracked in [`docs/irregularities.md`](docs/irregularities.md).

### Immediate work needed

1. Restore the competition data from the authenticated DrivenData data tab into the documented `data/` location; authenticate locally, never place credentials in the repo. Run `python scripts/prepare_data.py` and verify official file hashes/metadata.
2. Obtain and audit the complete registry rasters needed by the literal uniqueness protocol. Recompute overlap and surface correlation against all accessible files, including calibration rasters; missing inputs must fail closed.
3. Run candidate generation only from a pre-registered scientific hypothesis and cached feature stack; run per-feature canaries, buffered hide-and-recover and independent checks with correctly labeled confidence intervals.
4. Fix/replace the stale generated-page and gate scripts so they read the current run card and cannot advertise any candidate whose holdout or uniqueness gate is missing.
5. Refresh the executive summary and live feed only from dated, traceable receipts and source links. Verify the current leaderboard and weekly cap directly before any selector decision.

## Official and primary references

- [Competition overview/rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition data tab (login may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [GEMS Prize rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS Great Basin project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)
- [Tversky index background](https://en.wikipedia.org/wiki/Tversky_index) (secondary reference; competition metric definition takes precedence)

## Reproduce local checks

```bash
python -m pip install numpy scipy scikit-learn rasterio pytest
python scripts/verify_all_gates.py --expect-blocked
python -m pytest -q
```

The gate command is expected to report a negative/non-promoted candidate while the required data and full registry are absent. That is the correct fail-closed outcome, not a successful submission clearance.
