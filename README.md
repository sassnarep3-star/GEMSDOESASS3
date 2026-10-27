# GEMSDOESASS3

> **Current decision — 2026-10-27:** **NO TIFF was generated; DO NOT DOWNLOAD OR SUBMIT a file from this checkout.** At the start of this review, the repository contained only this README. There are still no competition rasters, labels, cached feature stack, evaluator, writer, registry, validator, or assigned method lane. Inventing a TIFF or a score would be unsafe and scientifically indefensible.

## Project charter (read before every project session)

This project aims to discover faults relevant to geothermal resources in the DOE GEMS challenge and produce an auditable, technically valid GeoTIFF only when evidence supports promotion. Optimize the probability of a defensible result; own the outcome and report failures as useful evidence. Do not treat a model projection or a locally reported score as a score receipt.

### Non-negotiable protocol

1. **Stay in the explicitly assigned method lane.** Before placement and again on final predictions, compare each raster's rank-correlation and 3-pixel dot overlap against the complete registry. Stop and record a negative result if `|Spearman| > 0.90` or more than `70%` of dots fall within `3 px` of any one registered raster. Do not evade a duplicate gate by moving dots.
2. **Reuse shared tools.** Use the template's cached features and shared hide-and-recover evaluator and submission writer. Hold out whole fault segments with a buffer; derive catalogue features only from visible faults; mask visible labels pixel-exactly; evaluate pooled distance-weighted Tversky (alpha `0.2`, beta `0.8`, triangular kernel support `300 m`). Fix shared tools in the shared template, not in a private fork.
3. **Label every result by evidence class.** Distinguish `HOLDOUT-DTI` (evaluator version, withheld-positive count, and 95% CI), `ORGANIZER-CONFIRMED` (only when copied from a submission-page receipt), owner-reported/unverified claims, and public-leaderboard observations. A projection is never a score.
4. **Run feature-alone leakage canaries.** Test each feature on the holdout before trusting it; AUC above `0.90` is a leakage alarm until proven otherwise.
5. **Fail closed on file quality.** Reopen the exact output bytes and validate one-band `float32`, EPSG:32611, 100 m resolution, exact sample-template bounds/shape/transform, footprint handling, and finite prediction values in `[0,1]`. A local format pass is not proof of organizer acceptance or scientific value.
6. **Use a machine-readable run card.** Record hypothesis, mechanism, a named non-fault mimic, holdout result and CI, registry correlation/overlap, SHA-256, validator result, filename, submission note (at most 140 characters), and `promote` or `negative` verdict. A negative result is a deliverable.
7. **Budget:** at most 3 experiments or 2 hours per lane. Do not select a competition slot from this research step; slot selection is a separate decision under the live weekly cap.
8. **No copying submissions.** A new filename or byte encoding does not make a copied/near-duplicate raster unique. Never call a TIF submission-ready unless all scientific, uniqueness, format, evidence, and separate selector gates pass.

### Submission gate shown first

**Available competition-ready download: NONE.** No TIF currently exists in this repository, so there is no file, estimated score, uniqueness result, or upload permission to offer. Do not rename/download a historical site artifact as a new submission. See [`docs/EXECUTIVE_SUMMARY.md`](docs/EXECUTIVE_SUMMARY.md) for the nine-site review and blockers.

### Project brief to carry forward

- Review the GEMS challenge rules, problem description, scoring, official data sources, and reference solution. Keep an auditable source inventory and an up-to-date feed of verified project evidence.
- Focus the initial comparison on GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36. Identify the best **reported** historical result at each site, but do not confuse it with an organizer receipt, a holdout result, or an authorized submission.
- Before implementing a new idea, rank 3–5 geological hypotheses with named input layers, physical signature, why it might identify catalogue-missing faults, differences from prior methods, expected direction of value (not a numerical score forecast), cost, data source, and non-fault mimics. Verify novelty against a complete registry; do not claim an idea is untried when the record is incomplete.
- Validate the top candidate with spatially blocked hide-and-recover before any weekly submission slot. Require an improvement over the frozen, same-evaluator holdout best with a paired uncertainty interval that supports the decision; do not extrapolate a leaderboard score without calibration evidence.
- Make a valid TIF easy to find only after all gates pass. Provide the unique submission name, a short note, exact download, validator receipt, and click-by-click submission guide. Explain that DrivenData expects a single-band float32 GeoTIFF with predictions in `[0,1]` and matching CRS, resolution, bounds, and grid; format validity alone is not authorization.
- Use free, public, official data where possible, verify license/coverage/access before proposing a data-dependent experiment, and identify any login, compute, data, or registry blockers honestly. Do not claim autonomous access to private competition data or submission receipts.
- Keep results and useful scientific knowledge organized for reuse. Cite official sources and flag conflicts, stale values, missing artifacts, and contradictions for review. Do not claim a result is hallucination-free without reproducing the underlying bytes and calculations.

## Verified primary references

- [DrivenData problem description and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (dynamic; record access date with any quoted observation)
- [DrivenData competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (login may be required)
- [DrivenData / DOE GEMS reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [DOI 10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)
- [INGENIOUS project, Great Basin Center for Geothermal Energy](https://gbcge.org/current-projects/ingenious/)
- [Challenge rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

## Repository state

The baseline checkout at the start of this review was a single-commit repository containing only this file. This review adds a static homepage and executive/submission guide, but no training, validation, data-download, or TIF-generation system exists. GitHub Pages deployment is not configured or verified here. Do not run training or claim a TIF is ready until the required data, shared template/tooling, and assigned lane are present and inspected. The first next step is to obtain the official competition files through an authorized route, then build/reuse and test a shared pipeline—not to manufacture a placeholder submission.
