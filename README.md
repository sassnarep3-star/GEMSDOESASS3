# GEMSDOESASS3 — GEMS fault-mapping research

> **Current release decision: NO-GO.** This checkout contains no competition rasters, scored submission rasters, cached feature stack, evaluator, or writer. No new GeoTIFF has been generated or validated. **There is currently no file here that is approved to download or submit.** A valid-format file alone would not establish scientific quality or permission to spend a competition slot.

## Start here every session

Before changing code or proposing a submission, read the [Executive Summary and Research Gate](docs/EXECUTIVE_SUMMARY.md). It records the standing mission, evidence limits, best results reported for the requested sites, ranked research hypotheses, official sources, and the machine-verification gates. The summary is deliberately explicit about unverified claims.

## Standing project charter

The objective is to develop an auditable, scientifically defensible method for identifying previously unmapped geothermal-region faults for the DOE GEMS competition. Prioritize expected competition value (“maximize P(Win)”) and own outcomes end-to-end. Do not confuse a reported leaderboard score, an internal estimate, a holdout score, and an organizer receipt.

### Non-negotiable research and submission protocol

1. **One pre-registered method lane per run.** Check its raster rank-correlation against every available registry raster and the fraction of predicted dots within three pixels of each registry raster, both before placement and after final placement. Correlation above 0.90 or overlap above 70% means duplicate/drift: record it and stop.
2. **Reuse shared tools and cached features.** Use the designated template's cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`; do not maintain a private fork. Hold out complete fault segments with a buffer, derive catalogue-based features only from visible faults, mask visible faults pixel-exactly, and compute pooled distance-weighted Tversky (alpha 0.2, beta 0.8; 300 m triangular kernel). Fix a shared-tool defect in its source template and report it. This checkout currently lacks those tools and data; do not silently replace them with an unverified implementation.
3. **Label results and provenance.** A score is either `HOLDOUT-DTI` (evaluator/version, withheld positives, 95% CI) or `ORGANIZER-CONFIRMED` (copied from a submission receipt). Anything else must be explicitly labeled unverified and must not be described as a score estimate or confirmed result.
4. **Leakage canary.** Test every feature independently on the spatial holdout. AUC above 0.90 is presumptive leakage until resolved.
5. **Run card.** End experiments with JSON containing hypothesis, mechanism, a named non-fault mimic, holdout DTI and CI, registry correlation/overlap, raster SHA-256, validator results (footprint NaN check, range, CRS/shape/transform), submission filename, a note no longer than 140 characters, and `promote` or `negative` verdict. A negative result is a valid deliverable.
6. **Hard budget and selector separation.** Stop at three experiments or two hours, whichever comes first. Research does not choose or consume a real submission slot; a separate selector must apply the weekly cap and approval gates.
7. **Never fabricate or copy a submission.** Only publish a generated TIF when its bytes, provenance, uniqueness, and format have been verified. If evidence is missing, say so and fail closed.

## Submission eligibility

The organizer's problem description requires a single-layer float32 GeoTIFF on the training grid (UTM zone 11N / EPSG:32611, 100 m, matching bounds), with predictions in [0, 1] and null/NaN outside the study bounds. The competition evaluates distance-weighted Tversky, with alpha 0.2, beta 0.8, and a triangular 300 m distance kernel. A successful writer/validator check is a **format gate only**; it does not mean the result is scientifically good, unique, or approved for upload.

**Current blockers:** this checkout is only an initial commit with a 14-byte README. It has no `data/`, source code, test suite, feature cache, template evaluator/writer, registry rasters, or candidate TIFFs. The competition data page is access-controlled; no DrivenData session is available in this environment. Consequently, no genuine holdout score, confidence interval, uniqueness comparison, or competition-ready TIFF can be produced from this checkout. Do not substitute a blank raster or a TIF copied from another site.

## Official references

- [DrivenData GEMS problem description, datasets, metric, and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition overview and rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (dynamic; the executive summary records a dated snapshot rather than treating an old value as current)
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3DEP products and services](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)

## Executive summary / GitHub Pages

Open [`docs/index.html`](docs/index.html) for the clear, public-facing status page and [`docs/EXECUTIVE_SUMMARY.md`](docs/EXECUTIVE_SUMMARY.md) for the full comparison, research hypotheses, caveats, and next steps.
