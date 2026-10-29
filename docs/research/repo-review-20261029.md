# Repository review — 2026-10-29

## Executive finding

**No candidate in this checkout is approved for a competition slot.** The newest downloadable GeoTIFF is a diagnostic pattern, not a validated model prediction. Its format properties were recomputed from the file, but the checkout lacks the official sample, feature and label rasters, and complete sibling registry. The right outcome is a negative run card and a conspicuous archive-only link—not a claim of a unique high-scoring submission.

## Pass 1 — implementation and evidence review

- Read the README standing brief and checked the current branch/worktree, repository layout, run-card artifacts, site generator, validator, tests, and data inventory.
- `data/` contains only JSON manifests/audits/restore receipts. It does not contain `training_features.tif`, `labels.tif`, or `sample_submission.tif`; `.cache/` is absent. Historic JSON measurements cannot be independently reproduced without the source rasters.
- The two older `gemsdoesass3-*37654*.tif` files are format-valid but historic uniqueness evidence blocks at least one literal comparison: `evidence/lattice_overlap_downloads_20261028.json` reports 99.97%/99.78% within 3 px of the calibration lattice. They are not eligible.
- The newest structural candidate file exists and its SHA-256 is `ae1626fcbf89ca4f11ea46d3267642592bc9080ad11412d02367637279a39e2e`. Recomputed rasterio properties: one band; float32; 3730 x 3292; EPSG:32611; transform `(100, 0, 243350, 0, -100, 4508550)`; nodata=None; all cells finite; values in [0,1]. These grid values match the checked-in prepared manifest, not a fresh comparison to the absent official sample.
- Its generator states 10,000 centers; radius-2 disks expand these to **129,311 positive cells**. Placement is synthetic hand-coded geometry, not derived from the feature stack. No holdout, score estimate, or candidate-specific feature canary can be supported.
- Downloaded the calibration-lattice witness from the pinned public GitHub commit `07345ea0604953d7efb858d9cfbc21e20c7aca0b` and verified SHA-256 `b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52c4d697f0647dc9b2`. Its CRS, shape and transform match the candidate. Independently recomputed positive-dot overlap: **54,872 / 129,311 = 0.4243413167** within 3 px. This is below the threshold for that one witness only; it is not a complete registry uniqueness pass. The generator has no pre-placement continuous surface, so the surface check was not performed.

## Pass 2 — defects and assumptions found

1. **Misleading download approval (high severity).** README and Pages called the newest synthetic pattern a “unique submission” and offered an unqualified download despite no holdout, full uniqueness scan, or official sample comparison. Corrected to archive-only and “DO NOT SUBMIT.”
2. **False precision and stale status (high severity).** README/site artifacts mixed an earlier LWST candidate's numbers with the newer structural raster. Historic current-run cards and `verify_all_gates.py` still expected the LWST file, fixed 37,654 positive pixels, and score improvements. Replaced the active card with an explicit negative run card for the actual newest file; historic score claims are not transferred to it.
3. **Generated-page link bug.** The previous docs page used paths such as `docs/research/...` from inside `docs/`, resolving to `docs/docs/research/...`. Rebuilt with page-relative links.
4. **Test-suite baseline was stale.** First `pytest` run: 16 passed, 2 skipped, 3 failed. Failures exposed README synchronization and broken relative-link assumptions; they did not establish a raster/model failure. Tests are being updated to assert current fail-closed behavior.
5. **Conflicting historical leaderboard figures.** The request has 0.3195/0.4413 snapshots; checked-in older evidence describes 0.4544 as of 2026-10-27. The current live board was not fetched for this review. None is stated as the present current top.
6. **No estimable score.** HOLDOUT-DTI and organizer result are unavailable for the synthetic candidate. The 0.2778 value is a supplied historical result; the available analysis gives a plausible family/metric explanation, not causality.
7. **Historical hypothesis archive is internally inconsistent.** `docs/hypotheses.md` names both H-GASS3-1/GSD-HUA and H-SASS3-A/LWST-GeoConduit as the lane, claims caches absent in this checkout, and later maps bands as `B01=dem`, `B05=slope`, etc., inconsistent with its own metadata-audit list and `data/feature_bands_audit.json`. Added a warning banner; do not treat the detailed plan, predicted uplift, compute estimates, or band mappings as verified current science.

## Pass 3 — corrections and re-check

- README rewritten as the standing charter and current status page, including nine requested sites, source links, score-labeling discipline, parallel-run protocol, and clear no-submission decision.
- Pages rebuilt so the first screen says no approved submission and labels the only TIF as archive-only. The per-site table distinguishes historical OWNER-REPORT results from candidate score estimates.
- `evidence/current_run_card.json`, `evidence/run_card.json`, and `docs/data/current_run_card.json` synchronized for the actual candidate. It records no score, no canary, no complete uniqueness clearance, the measured one-witness result, validator limits, short note, and negative verdict.
- One-witness audit stored in `evidence/uniqueness_audit_current_candidate_20261029.json`; this explicitly says not a complete uniqueness certificate.
- No experiment was run and no competition slot was used. Existing 2026-10-28 holdout numbers are historical claims and were not relabeled as this candidate's scores.

## Research hypotheses to consider after data restoration

The existing review describes the following *proposals*, not validated gains. Their relative ranking is qualitative and no numeric uplift is asserted:

| Rank | Candidate idea | Cached layers / signature | Why potentially uncatalogued | Main mimic and distinction | Cost / data gate |
|---:|---|---|---|---|---|
| 1 | H-SASS3-F, multivariate geophysical facies boundaries | `tmi_hg`, `iso_grav_anom_hg`, `geod_shearrate`, `cond_surf`; standardized multivariate Gaussian-mixture component boundaries and lineation | May expose sharp subsurface physical-property transitions under cover rather than reproduce mapped trace geometry | Lithologic contacts and playa-margin conductivity; differs from the repo's tree-based detector and simple single-band edges | Medium; cached stack and labels required; stack absent now |
| 2 | H-SASS3-G, anisotropic earthquake clustering | `ieq_n100a15`, `deq_n100a15`; directional Ripley's K / point-pattern anisotropy | Linear event clustering may mark active damage corridors absent from surface catalogue | Aftershock sequences / induced seismicity; differs from existing geodetic or fault-tip priors | Medium-high; competition layers may be insufficient; official relocated-event data must be obtained if bands do not carry required event locations |
| 3 | H-SASS3-H, strain-boundary candidates | `geod_dilaterate`; Otsu-thresholded, connected dilatation ridges | Candidate deformation boundaries could indicate active structures not in mapped inventory | Subsidence and thermal-expansion strain; differs from multi-feature corridor models | Low-medium; cached stack and spatial holdout required |
| 4 | Basal-surface curvature | `depth_to_base_surf`; local Hessian curvature/relief ridges | Concealed basement discontinuities beneath basin fill could evade surface mapping | Sedimentary onlap and paleochannel incision | Low implementation cost, but prior E1 is recorded negative; do not rerun without a preregistered reason and correct data |

All depend on local feature/label data that are not present in this checkout, so none can be validated now. No external-data-dependent idea is declared viable. For a future external seismicity branch, the official USGS ANSS ComCat/FDSN source must first be checked for access, spatial coverage and suitable event metadata; no such check was performed here.

## Current status and next actions

- **TIF:** archive-only diagnostic. Not OK to submit.
- **Estimated score:** not estimable.
- **Uniqueness:** one pinned witness is below 70%; complete registry and pre-placement checks are missing; therefore not cleared.
- **Highest-scoring requested site result:** GEMSDOE32 0.2778, OWNER-REPORT only; no causal claim and no new candidate shown to exceed it.
- **Needed:** restore authenticated competition rasters; reproduce band/footprint/sample metadata; run shared evaluator and per-feature leakage tests; source the complete registry; test pre-placement surface and final dots; only then prepare a selector packet.

## Review limitations

This is a repository and artifact audit, not geological field validation or a competition score report. GitHub-hosted sibling records are owner-controlled artifacts. The public competition data tab may require login. The source links are provided for manual provenance review; no credentials or organizer receipts were available here.
