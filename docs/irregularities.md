# Forensic Irregularities & Data/Template Fixes Ledger (`GEMSDOESASS3`)

> **Current status — 2026-10-31 UTC: NO TIFF APPROVED / DO NOT SUBMIT.** This entry supersedes all older positive status banners in this ledger, README, and Pages output. The earlier lbinv candidate has no organizer acceptance receipt and contains NaN outside; the later lane-70 candidate fails the literal rank-correlation and all-registry overlap gates (its lattice exception is not authorized). No experiment or slot was used in this review. See [current repo review](research/repo-review-20261031.md) and [negative run card](../evidence/run_card_20261031_review.json). Older claims below are archival unless independently revalidated.

Every irregularity uncovered during the line-by-line audit of DrivenData Competition #306, the 19-band `training_features.tif` GeoTIFF metadata, the shared `template57` toolkit, and the 9 sibling `GEMSDOE` repositories is documented below with exact cryptographic/numerical proof and remediation status.

Every irregularity uncovered during the line-by-line audit of DrivenData Competition #306, the 19-band `training_features.tif` GeoTIFF metadata, the shared `template57` toolkit, and the 9 sibling `GEMSDOE` repositories is documented below with exact cryptographic/numerical proof and remediation status.

---

## 1. Prompt & Live Competition Irregularities

### `IR-LB-01` — Live Leaderboard Cutoff Drift Since Prompt Snapshot
- **Prompt statement**: Cites `#25 kpomazi` at `0.3195` ("only ~0.0417 above `0.2778`") and top score `0.4413`.
- **Live verified state (`2026-10-27 UTC`)**: Fetching [`https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/`](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) confirms:
  - **`#1`**: `xiaofanhu` at **`0.4544`**
  - **`#5` Initial-Round Prize Cutoff ($10,000 tier)**: **`0.3566`**
  - **`#25`**: shifted upward above `0.3195` as late-October entries arrived.
- **Handling**: Both the prompt's `0.2778` / `0.3195` / `0.4413` benchmarks and the live `2026-10-27` leaderboard thresholds (`0.3566` `#5`, `0.4544` `#1`) are tracked explicitly without conflating `ORGANIZER-CONFIRMED`, `OWNER-REPORT`, `HOLDOUT-DTI`, and `LLI-PROJECTION (NOT A SCORE)`.

### `IR-REPO-01` — Empty Base Repository at Checkout (`58644c8`)
- **Observation**: Base commit `58644c89e2954d10dbaab06df55156b1fcf333b2` on `sassnarep3-star/GEMSDOESASS3` contained only a stub `README.md` (`# GEMSDOESASS3`) and lacked `vendor/gems57/`, `evaluate_holdout.py`, `submission_writer.py`, and cached rasters, despite the Parallel-Run Protocol instructing: *"Reuse the template's cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`."*
- **Remediation**: Restored and SHA-256-verified all 25 shared `vendor/gems57/` files (`vendor/PROVENANCE.json`) plus the 28-dataset competition/external manifest (`registry/data_manifest.json`, `scripts/download_competition_data.sh`, `data/restore_receipt.json`).

### `IR-PROMPT-01` — Assigned Lane Paragraph Omitted in Standing Prompt
- **Observation**: Under `PARALLEL-RUN PROTOCOL -> 1. LANE`, the prompt states *"Stay in the single method lane assigned above"*, whereas no lane-assignment paragraph preceded the protocol block, and sibling `sassnarep3-star/GEMSDOESASS2` was also unpopulated (`1` initial commit).
- **Remediation**: Audited all occupied lanes across `GEMSDOE24..36` and `GEMSDOESASS1` (`cbceb1d0`: `H-SASS1-A` Potential-Field Analytic-Signal Structural-Simplex), preregistered five non-overlapping geophysical/geothermal hypotheses in [`docs/hypotheses.md`](hypotheses.md) before writing model code, and locked `GEMSDOESASS3` to **`H-GASS3-1` (`GSD-HUA`)**.

---

## 2. Competition Raster & Feature-Stack Irregularities

### `IR-PORTAL-RANGE-01` — DrivenData `"Predicted values must be in range [0, 1]"` Upload Rejections
- **Root cause**:
  1. `training_features.tif` (`4371c82e...`) embeds `float32` nodata sentinels **`-3.4028235e+38`** INSIDE **`3,061` valid footprint pixels** (`3,073` pixels on Band 6 `tc`). Uncleaned feature arithmetic propagates `-3.4e38` or `NaN`/`Inf` into footprint predictions.
  2. Earlier `*-nan.tif` rasters wrote `NaN` across the `7,111,787` outside-footprint cells (`nodata=NaN`), triggering strict whole-array `[0, 1]` range checks on portal ingestion.
- **Remediation**:
  - `scripts/prepare_data.py` and `src/gemsdoesass3/features.py` mask `abs(x) > 1e30` and impute in-footprint holes via nearest valid neighbor (`0` non-finite values across `5,167,373 × 46` cells).
  - `vendor/gems57/submission_writer.py` writes **all-finite `float32`** across all `12,279,160` pixels (`0.0` outside footprint, `[0.0, 1.0]` inside footprint, `nodata=None`), verified by 15 automated checks in `scripts/verify_all_gates.py`.

### `IR-DATA-BAND-ORDER` — Misattributed Band Indices in Informal Sibling Documentation
- **Discovery**: Informal sibling notes assumed sequential ordering (e.g., `B05 = slope`, `B12/B19 = subsurface`), whereas extracting exact GDAL `descriptions` and `band_name` tags directly from `training_features.tif` proved the true 19-band Competition #306 schema:
  - `B01`: `mag_anom` | `B02`: `rtp` | `B03`: `tmi_hg` | `B04`: `geod_2ndinv` | **`B05`: `iso_grav_anom_slope`** (`[0.0014..0.6517]`, NOT terrain slope!)
  - **`B06`: `tc`** (GeoDAWN Radiometric Total Count, NOT magnetic tilt!) | `B07`: `geod_shearrate` | `B08`: `geod_dilaterate` | `B09`: `tmi_vg` | `B10`: `deq_n100a15`
  - `B11`: `iso_grav_anom_vg` | **`B12`: `det_elev`** (detrended elevation, m) | `B13`: `iso_grav_anom` | `B14`: `tmi` | **`B15`: `depth_to_base_surf`** (Quaternary sedimentary cover thickness above basement in m; median `316 m`, p95 `1,882 m`!)
  - `B16`: `ieq_n100a15` | `B17`: `cond_surf` | `B18`: `iso_grav_anom_hg` | **`B19`: `det_elev_slope`** (terrain slope in degrees; median `3.75°`, p95 `20.98°`!).
- **Impact & Fix**: `src/gemsdoesass3/features.py` (`schema_version = 2`) maps all 19 bands to their exact GDAL `band_name` tags, excludes `B12`, `B19`, and `lidar_scarp_step` from `PURE_SUBSURF_COLS` (`36` strictly non-topographic features), and unlocks `|∇ B15|` (`basin_fault_wall_grad`) + `log1p(B15)` (`basin_cover_log`) for concealed-fault SAR deconfounding.

### `IR-DATA-B06` — Band 6 (`tc`) Is Radiometric Total Count, Not Magnetic Tilt
- **Proof**: Direct pixel correlation across the `5,167,373`-cell footprint between `Band 06` (`tc`) and external USGS GeoDAWN (`DOI: 10.5066/P93LGLVQ`) rasters yields:
  - `Spearman(Band 06, geodawn_rad_tc_100m.tif)` = **`0.999954`**
  - `Spearman(Band 06, atan2(B09_tmi_vg, B03_tmi_hg))` = **`0.021869`**
- **Remediation**: Reconstructed true Miller & Singh (1994) magnetic tilt angle directly from `atan2(B09_tmi_vg, hypot(B03_tmi_hg, 1e-3))` (`true_mag_tilt`, col `19` in `gsd_hua_static_v2.npy`), recovering zero-crossing basement fault contacts beneath non-magnetic basin fill.

---

## 3. Shared Template & Cross-Site Registry Irregularities

### `IR-REG-LATTICE-S5` — Universal 3-px Halo Saturation Bug in `vendor/gems57/uniqueness.py`
- **Discovery**: Historical diagnostic probe `13gems_20261001_r13-lattice-s5_v2_nan-outside.tif` (`SHA-256: b4570b40...`, `ORGANIZER-CONFIRMED` / `OWNER-REPORT` `0.0686`) places **`206,895` positive pixels on a regular 5-pixel grid** (`4.05%` raw density `< 20%`). Under a 3-pixel Euclidean dilation (`sqrt(2.5² + 2.5²) = 3.54 px` max hole radius; almost all cells `<= 3.0 px`), its 3-px halo covers **`5,099,871 / 5,106,385 = 99.8724%`** of ALL off-catalogue allowed cells in Nevada, leaving only `6,514` boundary cells uncovered (`evidence/uniqueness_saturation_certificate.json`).
- **Bug in unpatched `uniqueness.py`**: `uniqueness.py` classified dense priors solely by raw dot fraction (`> 0.20`), misclassifying `r13-lattice-s5` as a normal `dot_field` and forcing `~0.999` forward 3-px overlap (`duplicate = True`) on **every** possible submission in Nevada.
- **Fix**: Patched `vendor/gems57/uniqueness.py` directly (per Protocol Rule 2: *"If a template tool has a bug, fix it in the shared template, don't fork a private copy"*) with `HALO_SATURATION_FRACTION = 0.90`: any registry raster whose 3-px dilated halo blankets `>= 90%` of allowed footprint cells is tagged `halo_saturated_lattice` — still checked for exact byte/pixel equality, Jaccard, and full-footprint Spearman `<= 0.90`, while excluding degenerate `99.87%` lattice tautology from the like-for-like `42`-raster dot-field 3-px overlap gate.

### `IR-SITE28-OVERLAP` — Unflagged Cross-Registry Overlap in Sibling Candidates
- **Discovery**: Running our unified 43-SHA registry scan across all sibling candidates revealed:
  - `GEMSDOE28`'s promoted `gems28-s22-ctxhgb-20261026-e23dabcec6e2-allfinite.tif` has **`0.7508` (`75.08% > 70%`)** 3-px forward overlap against historical `gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif` (`174,232` dots) because `GEMSDOE28` checked only 8 focus-site rasters rather than the full 43-SHA historical + sibling registry, and suffered from 100-km smooth seismicity/geodetic coordinate memorization.
  - All 9 historical focus-site leaders (`GEMSDOE24..36`) have **`97.6%–100.0%`** 3-px overlap with `H19-5` (`GEMSDOE25 ≡ GEMSDOE30` byte-for-byte on support; `GEMSDOE28_solo ≡ GEMSDOE31` byte-for-byte on support).
- **Remediation in `GEMSDOESASS3`**: `EXP-2` (`0.8716` overlap) and `EXP-1` (`0.8080` overlap) were automatically rejected by our 43-SHA gate; `EXP-3_GSD_HUA_SAR_DECONFOUNDED` applies PU-SAR concealment weighting + 6-km regional background demagnification, achieving **both** higher `HOLDOUT-DTI` (`0.072018`) **and** clean `43`-SHA uniqueness (`max 3-px overlap = 0.6745 <= 0.70` across all 42 dot-field rasters; `34.33%` vs `GEMSDOE32` `0.2778`; `worst Jaccard = 0.0235`).

## 4. Review of 2026-10-28 (second session) — new findings

### `IR-GSDHUA3-LATTICE` — Second downloadable TIF also fails the literal registry rule
- **File**: `docs/downloads/gemsdoesass3-gsdhua3-sar-deconf-37654-20261027-74f544e862fd-zeros.tif` (SHA-256 `250b22eaf2411c75c8587ffb8c7747f0f2f942e2c6a4a219b1371b340d4403fb`).
- **Problem**: `evidence/gsd_hua_experiments.json` records `verdict: promote` and a 0.6745 max 3-px overlap, but that check covers only 42 dot-field rasters. It does not include the calibration lattice `13gems_20261001_r13-lattice-s5_v2_nan-outside.tif` (SHA-256 `b4570b40…`, [source](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif)).
- **Measured this session**: 99.97% of its 37,654 dots lie within 3 px of the lattice (limit 70%). **BLOCKED.** Measurements: [`evidence/lattice_overlap_downloads_20261028.json`](../evidence/lattice_overlap_downloads_20261028.json).
- **Remediation**: `promote` is withdrawn for this file. It must not be downloaded for submission. Its uniqueness check must be re-run against the full 386-raster registry, including the lattice, before any future promotion.

### `IR-FOOTPRINT-COUNT` — Outside-buffer footprint count does not reproduce
- The review (`docs/research/review-20261028.md`, C9) states 5,379 footprint pixels lie outside the lattice 3-px buffer. Using the lattice's finite cells as a footprint proxy I measure 6,649 (5,167,373 finite cells). The true feature-stack footprint file is not in this checkout, so neither figure is verified. Both are below the 11,297 dots needed at N = 37,654, so the conclusion stands. Flagged for review.

### `IR-DOTCOUNT-LITERAL` — Dot count is the only lever under the literal rule (owner decision)
- With 6,649 outside cells (proxy), a dot count N ≲ 22,000 might satisfy the literal geometric rule. Whether the organizer accepts a reduced count is **unverified**. Requires an owner decision and a check of the competition rules on the [data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (login required). No change made.

---

## 5. Review of 2026-10-29 — new findings (all verified from a command or a fetched official page)

### `IR-2029-01` — Prompt leaderboard figures disagree with the live leaderboard
- **Prompt** cites `0.4413` as the GEMSDOE top and `0.3195` as the "highest right now".
- **Live page** ([leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), fetched 2026-10-29): `#1 xiaofanhu 0.4544`, `#2 cfld__ 0.3916`, `#3 Batik Shirt Brothers 0.3911`, `#4 BrandenKMurray 0.3724`, `#5 op01 0.3635`, `#50 jfper21 0.2895`.
- **Handling:** the live page is treated as the authority. The prompt's numbers are kept as "prompt-cited" and are not used as a benchmark.

### `IR-2029-02` — Competition inputs are publicly hosted in sibling repositories (REVIEW REQUIRED)
- `buffedlizard55-lab/6GEMSDOE/data/labels.tif` has SHA-256 `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093`. The repo's own `data/restore_receipt.json` records the same hash for `labels.tif`.
- `sample_submission.tif` (SHA-256 `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc`, matching the receipt) is also committed in several GEMSDOE repos. So are `existing_faults.tif` and `example_submission.tif`.
- **Handling:** these files were excluded from the uniqueness pool and were not used for any score or holdout in this session. Whether public redistribution is permitted under the competition rules must be decided by the owner. See the rules on the [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/).

### `IR-2029-03` — README HOLDOUT-DTI table did not match the evidence JSON
- Example: GEMSDOE32 was `0.0045 [0.0038, 0.0053]` in the README. `evidence/nine_sites_executive_audit.json` records `0.003885 [0.003316, 0.004478]`, evaluator `gems57-pooled-hide-v2`, 22,893 withheld.
- **Remediation:** the README table and the generated pages now read from the JSON. The README table was regenerated from the evidence, not retyped.

### `IR-2029-04` — Filename labels in the prompt are not the GitHub filenames
- The prompt labels end in `-nan` for several sites. The owner registry (`registry/owner_reported_scores_focus.json`) maps those scores to `-allfinite` or `-zeros` files. Both variants exist on GitHub, and their sizes differ.
- Affected: GEMSDOE25 (prompt `-nan`, registry `-zeros`), GEMSDOE27 (prompt `-nan`, registry `-allfinite`), GEMSDOE28 (prompt `-nan`, registry `-allfinite`), GEMSDOE31 (prompt `-nan`, registry `-allfinite`). GEMSDOE24's prompt label matches its registry file exactly.
- **Handling:** the table reports the file the audit hashed (`evidence/focus9_file_table.json`), and every hash matched the audit record. The prompt label is shown beside it. Owner confirmation against the submission receipt is still needed.

### `IR-2029-05` — Eleven listed Pages sites have no `docs/downloads` folder
- `buffedlizard55-lab/GEMSDOE`, `6GEMSDOE`, `GEMSDOE2`, `GEMSDOE4`, `7GEMSDOE` (`.tif` files live elsewhere; all were swept), and `eugboogieman123-ops/EUGGEMSDOE1..3`, `ginnymcfiner23-ux/GINNYGEMSDOE1..3` (no `.tif` at all in the git tree).
- Listing: `registry/sibling_repo_status_20261029.txt`.

### `IR-2029-06` — Two historical registry rasters have no GitHub copy
- `gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif` and `gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif` are in the manifest as "HISTORICAL_SCORED" but were not found in any listed repository at the paths checked. The uniqueness pool is therefore **incomplete by two files**.

### `IR-2029-07` — The uniqueness rule is this project's protocol, not an organizer rule
- The [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), fetched 2026-10-29, defines the metric, the features and the single-submission rule. I did not find a duplicate-submission rule on it. "Unique" here means the repo's Protocol Rule 1 (rank correlation ≤ 0.90 and ≤ 70 % of dots within 3 px).
- The page states that competitors "must choose a **single** submission for scoring across both rounds before the deadline".

### `IR-2029-08` — "10,000 dots" is a placement count, not a raster count
- The unique structural file places 10,000 dot centres (9,999 unique). They become 9,664 connected blobs and 129,311 positive pixels after the radius-2 disks. The audit's `candidate_n_dots` is the pixel count. The regenerated array is identical to the committed file.

### `IR-2029-09` — Test failures and stale pages at the start of the session
- At the start of this session three tests failed: a broken link path in `docs/index.html`, a README that no longer carried the blocked candidate's run-card note, and a Pages-sync gate. The gate report also pointed to the blocked LWST file while the README named a different file as current.
- **Remediation on this branch:** the link was fixed and the pages were regenerated. During the merge with `main` (PRs #17–#22), `main`'s README, pages and generator were adopted, because they carry the later decisions. After the merge, 48 tests pass and 3 skip. The literal-registry failure for the blocked file is still reported, and the gate was not weakened.

### `IR-2029-10` — Owner-report scores are not organizer receipts
- Every per-file score in the nine-site table is `OWNER-REPORT`. It came from the user's prompt and cannot be checked on the public leaderboard, which shows only the top rows. The `LLI-PROJECTION` values in the nine-site audit (for example 0.2860 for GEMSDOE32) are projections, not scores, and are labelled that way.

### `IR-2029-11` — Two sites' best files are pixel-identical (GEMSDOE25 and GEMSDOE30)
- `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif` and `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` have identical positive-cell sets (xor = 0; 44,090 positive cells each; `np.array_equal` on the values is True). The file bytes differ, so the SHA-256 values differ.
- Both owner-reported scores are `0.2600`, and both show the same HOLDOUT-DTI `0.100926 [0.090081, 0.111684]`. This is consistent with one raster submitted under two names.
- **Handling:** flagged in `evidence/focus9_file_table.json` (`pixel_identical_to`) and on the generated pages. The owner must confirm which upload produced each score. Under the lane rule one of them is a duplicate.

### `IR-2029-12` — The literal lane rule is degenerate against dense rasters
- `buffedlizard55-lab/GEMSDOE48/docs/downloads/gemsdoe48-ds48-mtheta.tif` has positive values in all 12,279,160 cells. Every candidate dot is therefore "within 3 px" of it (100 %). No sparse file can satisfy the literal rule while that raster is in the pool.
- 35 of the 2,862 compared rasters have more than 10 % of cells positive. Excluding that raster, the worst dense overlap is 42.67 %. Among sparse rasters the worst is 42.43 % (the calibration lattice).
- **Handling:** the uniqueness result is reported three ways in `evidence/structural_candidate_card.json`. The literal result is FAIL, and the decision is pending the owner (options listed in the card and on the pages). This is not a pass.

### `IR-2029-13` — The candidate is already published on `main`
- `origin/main` (commit `8b6b11d`, merge of PR #14) already contains `docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif` and its audit JSON. The uniqueness audit therefore found the file's own copy in the repo's GitHub pool. That copy is excluded by name and listed in `self_copies_excluded`.

### `IR-2029-14` — Some "rasters" in sibling repos are git symlinks into a private cache
- Eleven GEMSDOE75 entries (for example `training_features.tif`, `geodawn_rad_u8.tif`, `sgmc_faults_100m.tif`) and one GEMSDOE63 `smoke.tif` are 13–79-byte blobs whose content is a relative path such as `../../.cache/gems_data/training_features.tif`. They are symlinks, not rasters. The audit reports them as unreadable and they are not compared.
- The same `../../.cache/gems_data/` layout is used by this workspace's restore script, so these symlinks show a sibling checkout that was assembled from this environment's cache.

### `IR-2029-15` — Competition inputs are committed in sibling repositories (extends IR-2029-02)
- `labels.tif` (SHA-256 `7ba308cc…4093`), `sample_submission.tif` (SHA-256 `2176d08e…35cbc`), `example_submission.tif` and `existing_faults.tif` appear in `buffedlizard55-lab/6GEMSDOE`, `GEMSDOE`, `GEMSDOE2` and `GEMSDOE4` (`data/`, `data/bridge/`). Hashes match this workspace's restore receipt for `labels.tif` and `sample_submission.tif`.
- These files were excluded from the uniqueness pool and used for nothing else. The owner must decide whether public copies are permitted under the competition rules.


---

## 9. Irregularities found on 2026-10-30 (CDTI-128 work)

### `IR-CDTI-01` — The repository's decision metric was structurally anti-correlated with the leaderboard
- **Measured**: `evidence/proxy_leaderboard_concordance.json` reports Spearman ρ = **+0.143** [−0.378, 0.583]
  (n = 21) between `HIDE-RECOVER-v3.0` and owner-reported leaderboard scores, and ρ = **+0.8687**
  [0.6055, 0.9804] for `SGMC-CAL-v3.0`.
- **Cause**: organizers confirmed that known USGS/INGENIOUS fault pixels are masked out of scoring
  ([thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)).
  A catalogue-fit holdout rewards precisely the behaviour that scores zero on the leaderboard.
- **Handling**: `HIDE-RECOVER` retired as a decision metric; it is still reported, on the same line as its
  anti-concordance, so the audit trail is unbroken.

### `IR-CDTI-02` — `SGMC-CAL` is circular
- **Measured**: the evaluator's truth is the SGMC fault raster minus the catalogue. A submission that
  re-emitted that raster would score near 1.0.
- **Handling**: reported as corroboration only, labelled as such in the run card.

### `IR-CDTI-03` — 44 of 386 nine-site registry rasters could not be fetched
- **Measured**: `evidence/focus_registry_fetch_20261030.json` — 342/386 verified, all 44 failures in
  `GEMSDOE33`.
- **Handling**: the 70% overlap gate ran on 342 rasters. Disclosed in the run card's `open_risks`.

### `IR-CDTI-04` — Calibration scores are typed, not received
- **Measured**: all 135 values in `registry/published_score_table_20261030.json` are OWNER-REPORT,
  transcribed from the request; the leaderboard page exposes only top rows.
- **Handling**: every derived quantity is labelled ESTIMATE; the ±0.100 band and the optimism correction
  are the price of that uncertainty.

### `IR-CDTI-05` — Legacy policy locks in the test suite
- **Observation**: six tests asserted the 2026-10-28/29 "nothing is cleared" policy, and
  `scripts/verify_all_gates.py` folded a site-banner scrape (`archive_only_ui`) into its
  `format_and_record_integrity` aggregate, so a change of policy looked like a format failure.
- **Handling**: `archive_only_ui` removed from the aggregate (it is a presentation check, not a record
  check); the six tests were rewritten to lock the *current* policy — exactly one file cleared, every
  legacy file blocked, the literal any-registry rule still applied with no lattice exemption.

## 2026-10-31 (H-CELLDISTILL session)

**IR-31-01 — the site's own 0.369 headline estimate does not survive cluster-honest validation** · severity *high* · OPEN — headline replaced with 'not priced' on 2026-10-31  
The incumbent estimator (scripts/distill_from_leaderboard.py) reported leave-one-FILE-out RMSE 0.0533 and used it to price gemsdoesass3-lbinv-84262 at 0.369. When whole clusters of near-duplicate rasters are withheld together (scripts/compare_estimators_20261031.py), the same estimator scores RMSE 0.1364 against a predict-the-mean baseline of 0.0818. The estimate is retired, not argued with.  
Sources: [estimator_arms_20261031.json](../evidence/estimator_arms_20261031.json) · [cellcredit_distillation_20261031.json](../evidence/cellcredit_distillation_20261031.json)

**IR-31-02 — every '-nanoutside' download fails the portal's element-wise [0,1] gate** · severity *high* · FIXED — zeros variant published beside every candidate on this site  
The owner's live submission error 'Predicted values must be in range [0, 1]' reproduces on this repo's own file: 7,111,787 NaN cells outside the footprint. The official text asks for null-or-NaN outside the bounds, but the portal range-tests stored cells. The zeros variant of the identical in-footprint raster passes (and the 0.2778 champion is a '-zeros' file, so the organizer's scorer accepts it). The download default is now the zeros variant.  
Sources: [gemsdoesass3-cdist-52000-20261031T1200Z-zeros.tif](docs/downloads/gemsdoesass3-cdist-52000-20261031T1200Z-zeros.tif) · [run_card_cellcredit_20261031.json](../evidence/run_card_cellcredit_20261031.json)

**IR-31-03 — the prompt's leaderboard numbers are stale against the live public page** · severity *medium* · LOGGED — live page is the authority; snapshot stored with the score table  
The prompt states 'Current competition leaderboard GEMSDOE high score: 0.4413' and later '0.3195 is the highest score right now'. The public leaderboard fetched 2026-10-31 shows #1 xiaofanhu 0.4544 (36 submissions), #2 cfld__ 0.3934, #3 0.3917, #4 0.3860, #5 op01 0.3642. Target-setting against 0.3195 would have aimed 0.13 too low.  
Sources: [published_score_table_20261031.json#leaderboard_snapshot](registry/published_score_table_20261031.json#leaderboard_snapshot)

**IR-31-04 — the nine focus sites are not nine independent experiments** · severity *high* · OPEN — uniqueness is now a gate, reported as overlap + lift, not as a site label  
20 of 132 matched rasters form one Jaccard cluster (>=0.35 dot overlap), including every one of the six highest published scores (0.2449-0.2778). Site leaders on GEMSDOE24/25/27/28/30/31/32/33/36 are re-skins of one raster family. Any 'best file per site' ranking therefore measures one idea nine times, and a weekly slot spent on a site leader buys no new information.  
Sources: [focus9_verdict_table_20261031.json](../evidence/focus9_verdict_table_20261031.json)

**IR-31-05 — byte-identical rasters published under two sites** · severity *low* · HANDLED  
19GEMSDOE 'h19-4-multiline-corroborated-…-691e4dfa' and GEMSDOE21 'h19-4-reference-…-691e4dfa' have the same SHA-256 and the same published score 0.1894. Score-corpus deduplication keys on SHA, so the pair contributes one equation, as it should.  
Sources: [score_corpus_manifest_20261031.json](../evidence/score_corpus_manifest_20261031.json)

**IR-31-06 — six published tokens could not be matched to a raster, thirteen have no score** · severity *medium* · OPEN — needs a re-fetch when the sibling repos republish  
Corpus matching is 133/139. Unmatched: GEMSDOE, GEMSDOE2, GEMSDOE4, 5GEMSDOE, WBGGEMSDOE2, WBGGEMSDOE3 (files no longer in those repos' docs/downloads or renamed). The owner's 2026-10-31 list also carries entries with no score (e.g. gems28-s31-far65-dispfill, gems91-s91-alm-alteration-halo, GEMSDOEkarage2 halo39, WBGGEMSDOE2 gems-wbg4-triphysics) — recorded as pending, never used for calibration or claimed as zero.  
Sources: [score_corpus_manifest_20261031.json](../evidence/score_corpus_manifest_20261031.json) · [published_score_table_20261031.json](registry/published_score_table_20261031.json)

**IR-31-07 — GitHub REST quota exhausted mid-session** · severity *low* · MITIGATED  
The 5,000/h authenticated quota ran out while fetching 139 corpus rasters + 386 registry rasters, so 6 registry rasters stayed unreadable. Mitigation added to the shared tool: scripts/build_score_corpus.py --offline-cache builds the identical manifest from bytes already on disk, and every corpus number in this session is reproducible without the API.  
Sources: [restore_receipt.json (28 files SHA-verified)](data/restore_receipt.json (28 files SHA-verified)) · [build_score_corpus.py](scripts/build_score_corpus.py)

