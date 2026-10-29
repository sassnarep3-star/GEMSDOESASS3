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

## Start here — status as of 2026-10-29

| Question | Answer |
|---|---|
| Is there a file I can download? | **Yes, for review only:** `docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif` (format-valid, already published in this repo). |
| Is it unique under the protocol? | **Not cleared.** The literal Rule-1 check FAILS because one dense sibling raster (`GEMSDOE48/gemsdoe48-ds48-mtheta.tif`, positive in every cell) makes every candidate dot "within 3 px". The sparse-only check passes. **Owner decision pending.** |
| Can I submit it? | **NO.** No holdout score exists (labels are not in this workspace), the expected leaderboard score is unknown, and failing uniqueness is never permission to submit. |
| Best existing file | GEMSDOE32 `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, owner-reported **0.2778**. Already submitted, so not eligible for resubmission. |
| Leaderboard top (live, 2026-10-29) | **0.4544** (xiaofanhu). Gap from 0.2778: 0.1766. The prompt's 0.4413 and 0.3195 do not match the live page (IR-2029-01). |

Full executive summary (the Pages site has the same content): `docs/executive-summary.html`
(also at the site root `executive-summary.html`). Overview: `docs/index.html`.

---

## File to download — unique structural GeoTIFF (review only)

- File: `docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif`
- SHA-256: `ae1626fcbf89ca4f11ea46d3267642592bc9080ad11412d02367637279a39e2e` (193,208 bytes)
- Note (108 chars): "GEMSDOESASS3 unique structural prior 10k dots; UNVALIDATED - download for review, do not submit (no holdout)"
- Grid: EPSG:32611, 3730 × 3292, float32, single band, nodata none, values 0 or 1. The transform matches the prepared grid spec in `data/prepared_manifest.json`. **It was not compared with `sample_submission.tif`, which is not in this workspace.** The footprint is therefore unverified.
- Content: 10,000 dot centres along six NNE-trending corridors, radius-2 px disks, no label or feature read. Regenerated exactly from seed `0x5EED` by `scripts/generate_unique_submission.py`. Result: 129,311 positive cells in 9,664 connected blobs.
- Run card: `evidence/structural_candidate_card.json`. Audit: `evidence/structural_uniqueness_fullpool_20261029.json`.

### Format checks (recomputed from the raster by `scripts/build_structural_card.py`)

All nine checks PASS: single band, float32, EPSG:32611, shape 3730 × 3292, transform equal to the prepared grid, nodata none, no NaN, all finite, values in [0, 1].

### Uniqueness (Protocol Rule 1), recomputed from pixels

| Test | Rasters | Max within-3 px | Max \|ρ\| (sampled) | Result |
|---|---|---|---|---|
| Literal rule, all rasters | 2,862 | 100.00 % `GEMSDOE48/gemsdoe48-ds48-mtheta.tif` (dense, 12,279,160 positive cells) | 0.0766 | **FAIL** |
| Sparse (dot-type) rasters | 2,827 | 42.43 % (`13GEMSDOE` calibration lattice) | 0.0766 | PASS |
| Dense rasters (>10 % of grid positive) | 35 | 42.67 % excluding GEMSDOE48; 100 % for GEMSDOE48 | 0.0087 | 1 over 70 % |

The pool is every `.tif` in the 104 GEMSDOE repositories named on the leaderboard list (`registry/sibling_repos.txt`, status in `registry/sibling_repo_status_20261029.txt`), plus the focus-9 registry (`registry/focus_registry_manifest.json`, 378 rasters SHA-matched). Rebuild with `scripts/fetch_sibling_registry.py`. Coverage limits are in IR-2029-06 and IR-2029-14. The repo's own published copy of this file (`sassnarep3-star/GEMSDOESASS3`) is excluded.

**Decision needed (owner):** keep the literal rule (no sparse file can then pass while that raster is in the pool), exclude dense rasters from the overlap test and keep the rank test on all rasters (this variant passes), or redefine dots for dense rasters and rerun. Until the owner chooses, the file is not cleared as unique.

---

## Nine focus sites — best file per site

Owner-reported scores are typed in the user's prompt and are not organizer receipts. HOLDOUT-DTI values are the historical records in `evidence/nine_sites_executive_audit.json` (evaluator `gems57-pooled-hide-v2`, 22,893 withheld). They were **not re-run** here. Every file name below was matched by SHA-256 to its GitHub copy (`evidence/focus9_file_table.json`). The file names come from the owner registry; the prompt label is shown where it differs.

| Site | File (exact GitHub name) | Owner-reported score | HOLDOUT-DTI [95% CI] (historical) | Unique? |
|---|---|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 | 0.096653 [0.085535, 0.107455] | No — already submitted |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif` (prompt label `…-nan`) | 0.2600 | 0.100926 [0.090081, 0.111684] | No — already submitted. **Pixel-identical to GEMSDOE30** (IR-2029-11) |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif` (prompt label `…-nan`) | 0.2449 | 0.096395 [0.085284, 0.107090] | No — already submitted |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif` (prompt label `…-nan`) | 0.2710 | 0.028218 [0.024626, 0.031798] | No — already submitted |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 | 0.100926 [0.090081, 0.111684] | No — already submitted. Pixel-identical to GEMSDOE25 |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif` (prompt label `…-nan`) | 0.2708 | 0.029707 [0.026054, 0.033232] | No — already submitted |
| **GEMSDOE32** | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | **0.2778** (best) | 0.003885 [0.003316, 0.004478] | No — already submitted |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 | 0.052964 [0.046931, 0.058741] | No — already submitted |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 | 0.004001 [0.003431, 0.004593] | No — already submitted |

Notes:
- The HOLDOUT-DTI and owner score columns do not agree in rank order (for example GEMSDOE32 has the top owner score and a very low HOLDOUT-DTI). That disagreement is itself a warning that holdout and organizer scores measure different things. Do not read the holdout column as a predictor of rank.
- The GEMSDOE32 explanation (official masking, zero on-catalogue dots in the audit) is on the executive-summary page. The catalogue layer is not in this workspace, so it is not re-verified.
- The earlier README table disagreed with the evidence JSON (IR-2029-03). This table is now read from the JSON.

---

## Blocked candidate — LWST (DO NOT SUBMIT)

`gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` (SHA-256 `bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a`) fails the literal registry rule: 99.7849 % of its dots fall within 3 px of the 13GEMSDOE calibration lattice (limit 70 %). The lattice hash was verified this session against `b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2`. At 37,654 dots, only 5,379 footprint cells lie outside the lattice buffer, and at least 11,297 would be needed there. **NOT OK to submit.** Reviewer verdict: negative. Historical note: "GEMSDOESASS3 LWST-GeoConduit EXP3: 3D SPI+WijnsTheta+DualHGB300m 37654d B=2 HR=0.1111 SGMC=0.0657".

Run card: `evidence/run_card.json` and `evidence/current_run_card.json` (identical for these fields). Review: [independent-review-20261028.md](docs/research/independent-review-20261028.md).

---

## Research notes

- Next candidate hypotheses (not validated, no score): [docs/research/next-hypotheses-20261029.md](docs/research/next-hypotheses-20261029.md). These use the official feature names. Four ideas are ranked qualitatively. None can be validated without labels.
- Metric: `src/gems32/metric.py` implements the official DTI (verified formula, see the file docstring). `marginal_inclusion_threshold` in that file gives the break-even rule (a pixel helps only if its kernel credit exceeds 0.2 × current DTI). That rule is already implemented; it is not a new result.

---

## Irregularities

Full ledger: [docs/irregularities.md](docs/irregularities.md), section 5 (IR-2029-01 to IR-2029-15). The most important items:
- **IR-2029-02 / -15:** competition inputs (`labels.tif`, `sample_submission.tif`, and others) are publicly committed in sibling repos. Hashes match this workspace's restore receipt. Not used. Owner decision needed.
- **IR-2029-11:** GEMSDOE25 and GEMSDOE30 best files are pixel-identical, though each has a different owner score (0.2600 each). Owner must confirm.
- **IR-2029-12:** the literal uniqueness rule is degenerate against dense rasters.
- **IR-2029-01:** the prompt's leaderboard figures do not match the live page.

---

## What is not done, and why

1. **No holdout validation.** The labels are not in this workspace (`data/restore_receipt.json` points to `.cache/gems_data`, which does not exist here). Without labels, no candidate can be scored, so no new candidate can be promoted.
2. **No new candidate.** Generating more candidates without a validation gate would spend submission budget on guesses.
3. **Footprint not verified** against `sample_submission.tif` (not used; see IR-2029-02).
4. **Pool gaps:** two historical rasters have no GitHub copy (IR-2029-06); 52 files were skipped (dtype, empty, or symlink stubs, IR-2029-14).
5. **Dense-raster decision** (above) is pending the owner.

---

## How to submit (only for a file that is cleared)

1. Run the full holdout evaluator and the leakage canary (AUC ≤ 0.90). Report the version, withheld count, and spatial-block CI. Beat the current holdout best without using a weekly slot. Blocked here: no labels.
2. Run the lane check against every accessible registry raster with no exclusions. Fail closed on incomplete coverage. Rank correlation ≤ 0.90 and ≤ 70 % of dots within 3 px.
3. Validate the GeoTIFF: single band, float32, EPSG:32611, 3730 × 3292, transform matching `sample_submission.tif`, values in [0, 1], no NaN, nodata none. Use a distinct filename and a note of at most 140 characters.
4. Write the run card JSON with all metrics, CIs, gates and the promotion decision.
5. Only a separate selector may promote a file. The competition selects **one** submission for both prize rounds ([problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)). Check the weekly cap on the [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/), then upload via "New submission".

---

## PARALLEL-RUN PROTOCOL (binding)

Rules 1–6: lane checks (rank correlation ≤ 0.90, ≤ 70 % of dots within 3 px), reuse of the template tools (`evaluate_holdout.py`, `submission_writer.py`), numbers labelled HOLDOUT-DTI or ORGANIZER-CONFIRMED only, leakage canary, run card JSON, budget of 3 experiments / 2 hours. A failed uniqueness gate is never permission to submit. No copying of previous submissions.

---

## Reproduce

- Install: `numpy scipy scikit-learn rasterio pytest` (in a venv; the system Python is externally managed).
- Rebuild the sibling pool: `python scripts/fetch_sibling_registry.py --out /tmp/full_pool --manifest registry/sibling_pool_manifest.json` (the fetch was not timed; the uniqueness audit over the 2,915-file pool took about 45 minutes on 2 CPUs).
- Uniqueness audit: `python scripts/independent_uniqueness_audit.py docs/downloads/<structural>.tif /tmp/full_pool --out evidence/structural_uniqueness_fullpool_20261029.json`.
- Run card: `python scripts/build_structural_card.py --audit evidence/structural_uniqueness_fullpool_20261029.json`.
- Focus-9 table: `python scripts/build_focus9_file_table.py --pool <pool> --repo-root <checkouts>`.
- Pages: `python scripts/build_review_site.py`.
- Gates: `python scripts/verify_all_gates.py` (nonzero exit expected while blocked). Tests: `pytest -q`.

---

## Sources (official or verified)

- [Competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) and [problem description (metric, format, one-submission rule)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), fetched 2026-10-29.
- [Live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), fetched 2026-10-29.
- [DrivenData forum: known faults masked when scoring (staff reply)](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516), fetched 2026-10-29.
- [Reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- [NLR format document](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — listed in the task; not fetched in this session.
- [EPSG:32611](https://epsg.io/32611) — listed in the task; not fetched in this session.
- [USGS GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — listed; not fetched in this session.

Raw data and caches are not in this checkout. The restore receipt is historical, and mirror hashes do not authenticate organizer provenance.
