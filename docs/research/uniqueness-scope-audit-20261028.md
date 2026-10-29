# Uniqueness scope audit and download decision — 2026-10-28

## Answer

**No file is OK to download and submit.** Both archived files fail the literal Protocol Rule 1 (no more than 70% of dots within 3 px of any registry raster, including the calibration lattice).

| File (archived, not approved) | Holdout proxy (HOLDOUT-DTI) | Estimated leaderboard score | Submissions-only rule | Calibration-lattice rule | OK to download and submit? |
|---|---|---|---|---|---|
| `gemsdoesass3-lwst-geoconduit-dual37654-…-a9ad3386-zeros.tif` (SHA-256 `bc9109d9…`) | 0.065702 [0.058992, 0.071240], evaluator `GEMSDOE32-SGMC-CAL-v3.0`, 62,703 off-catalogue positive pixels. Paired delta vs champion [-0.005523, 0.008911] includes zero. | Not estimated | PASS, max 66.53% (`GEMSDOE32 h49-cgtd-noisyor-axial28`), max abs ρ 0.135 | FAIL, 99.78% vs `13gems_20261001_r13-lattice-s5_v2_nan-outside.tif` | **NO** |
| `gemsdoesass3-gsdhua3-sar-deconf-37654-…-74f544e862fd-zeros.tif` (SHA-256 `250b22ea…`) | 0.072018 [0.057412, 0.087631], evaluator `gems57-pooled-hide-v2`, 22,893 withheld positives | Not estimated | FAIL, 76.26% vs `GEMSDOE30 gemsdoe30-g30s20-disc-60000dots` (15 rasters above 70%) | FAIL, 99.97% | **NO** |

No leaderboard estimate is written. The holdout proxy is on a different scale from the owner-reported leaderboard values (about 0.06–0.07 vs 0.22–0.28). The earlier concordance (Spearman 0.869 on n = 21) is a rank statement, not a score mapping, and a projected score is never written as a score under the protocol.

## What would change the verdict

1. **Owner ruling on the lattice.** If calibration lattices are outside Rule 1, the LWST file passes the submissions-only rule at 66.53%. That is a policy decision, not a technical result. No exemption has been applied.
2. **A new literal-compliant file.** The footprint has 6,649 pixels more than 3 px from any lattice dot (measured here). Since 30% of dots must fall outside the buffer, a file of at most about 22,000 dots could pass the lattice rule in principle. Its score would be unknown. It must be validated on the holdout before any slot is used, and it must also pass the submissions-only rule.

## Method (reproducible)

1. **Registry fetch.** `gh api` listed the HEAD commit of each focus repository. The commits are in `~/.cache/gems_registry/commits.txt` and in the manifest below. `codeload.github.com` tarballs were downloaded at those commits and only `*.tif` was extracted. The cache is outside Git.
   - Manifest: `registry/sibling_registry_manifest_20261028.json` (460 TIFs: 454 submission-scope, 6 calibration; SHA-256 and byte size per file).
   - Commits: GEMSDOE24 `5e3fa8ff`, GEMSDOE25 `fb1db372`, GEMSDOE27 `6704fa2a`, GEMSDOE28 `9509b73e`, GEMSDOE30 `31696c65`, GEMSDOE31 `06930b9d`, GEMSDOE32 `97597a06`, GEMSDOE33 `3eaf85ef`, GEMSDOE36 `e280188a`.
2. **Scope.** `scripts/independent_uniqueness_audit.py::scope_of` classifies each raster:
   - `submission`: under `docs/downloads/` or `archive/legacy_candidates/`.
   - `calibration`: under `inputs/calibration/`.
   - `other`: everything else (feature layers such as `data/external/*`). These are listed, not gated.
3. **Metrics.** Dots are finite values > 0. For each registry raster, the audit reports the fraction of candidate dots within 3 px of that raster's dots, and Spearman ρ on 300,000 fixed-seed uniform pixels. Rule 1 is applied to submission + calibration.
4. **Reproduce.**
   ```
   python scripts/independent_uniqueness_audit.py docs/downloads/<candidate>.tif ~/.cache/gems_registry --out evidence/<out>.json
   python scripts/verify_all_gates.py --expect-blocked
   ```
   The sibling tarballs must be re-fetched at the commits above. Runtime is about 9 minutes per candidate.

## Corrections to earlier figures

- **Scope bug (IR-SASS3-54).** The earlier audit counted feature layers. `tiger_road_distance_m.tif` produced a false 100% overlap. Fixed in the shared tool; both candidates rerun.
- **sar-deconf 67.4% (IR-SASS3-55).** That figure came from a 42-raster inventory. The full submitted set reaches 76.26%.
- **Registry index incomplete (IR-SASS3-56).** `evidence/registry_index.json` lists 43 rasters; the pinned repositories contain 454 submission-scope TIFs.
- **Lattice footprint count (IR-SASS3-57).** Measured 6,649, not 5,379. The conclusion is unchanged at 37,654 dots.

## Coverage notes

- The only submission-scope TIF not compared is `GEMSDOE36/docs/downloads/GEMS36_FORMAT_TEST_NOT_SUBMISSION.tif`. The audit skipped it for its grid, and its name says it is not a submission.
- 14 rasters are `other` and are not gated. They include `data/external/*` feature layers, which are not submissions.

## Official sources checked

- [DrivenData competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/). Not reachable from this sandbox (`drivendata.org` is outside the allowed hosts). Not verified here.
- [Official reference solution README](https://github.com/drivendataorg/gems-prize-reference-solution/blob/main/README.md). Setup only; no submission or uniqueness rules.
- [Official reference notebook](https://github.com/drivendataorg/gems-prize-reference-solution/blob/main/unet-mc-cv-reference-solution.ipynb). Its output step writes a single-band `float32` GeoTIFF with the CRS and transform of `labels.tif`. This supports the repo's format checks (EPSG:32611, 3730 × 3292, 100 m). It contains no uniqueness rule, so the 70% and 0.90 thresholds come from the user's protocol and are not verified as competition rules.
- [EPSG:32611](https://epsg.io/32611): UTM zone 11N, the CRS used by the grid.

## Irregularities for review

IR-SASS3-54 to IR-SASS3-59 in `evidence/irregularities_ledger.json`. Key items:

- **IR-SASS3-58.** The lane method paragraph referred to by the protocol does not appear in the request or the recorded prompt. The feature stack is absent, so the holdout cannot be reproduced here. No new experiment or raster was generated in this session.
- **IR-SASS3-59.** The leaderboard figures in the request (0.3195, 0.4413, 0.4544) conflict and cannot be checked from this sandbox. Treat them as unverified.

## Next steps for the next session

1. Owner decides whether calibration lattices count under Rule 1 (IR-SASS3-19 and this note).
2. Owner supplies the lane paragraph and authorises restoring the cached feature stack (`scripts/restore_data.py`; mirror pins are not organizer-authenticated).
3. If a literal-compliant file is wanted, generate one with at most about 22,000 dots, validate its holdout with the pinned evaluator and a leakage canary, and rerun the scoped audit against all 454 submission-scope TIFs.
4. Paste the current DrivenData leaderboard and submission-page receipts so that any score can be labelled ORGANIZER-CONFIRMED.

## Newer archived files on `main` (rechecked the same day)

The `main` branch added two synthetic TIFs after this branch was cut. Both were recomputed with the same scoped auditor against the same 453 submitted rasters and 6 calibration lattices (`evidence/uniqueness_scoped_bgk_pbe_20261029.json`, `evidence/uniqueness_scoped_unique_structural_20261029.json`).

| File | Dots | Submissions max within-3 px | Calibration-lattice max | Literal rule | Holdout | OK to submit? |
|---|---|---|---|---|---|---|
| `gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-…-af121062-zeros.tif` (SHA-256 `7ab47cf5…`) | 8,794 | 18.90% (GEMSDOE31 `rbu31-regimeunion`) | 44.41% | PASS | NOT MEASURED (synthetic placeholder) | NO |
| `gemsdoesass3-unique-structural-…-e3ecb47c-zeros.tif` (SHA-256 `ae1626fc…`) | 129,311 | 13.33% (GEMSDOE30 `sgmc-hedge-d10-85k`) | 42.43% | PASS | NOT MEASURED (random corridors, no signal) | NO |

Uniqueness passing does not make either file submittable. The protocol also requires a passing holdout and a leakage canary, and `main`'s verifier requires both before approval. Neither file has them. Both were generated without the geological or feature inputs, so they are archive-only.
