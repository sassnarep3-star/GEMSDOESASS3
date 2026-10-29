# Independent review of the shipped LWST submission (2026-10-28)

Every number is labelled **HOLDOUT-DTI** (evaluator named), **ORGANIZER-CONFIRMED** (none used except the leaderboard top), or **OWNER-REPORT** (typed in the task prompt, not an organizer receipt). Gate results are recomputed from the rasters by `scripts/independent_review.py`, not copied from pipeline JSON.

## 1. Answers

| Question | Answer | Basis (label) |
|---|---|---|
| Is the file OK to download and upload? | **NO** (literal registry-overlap rule fails; format-valid archive only) | Recomputed from the raster (programmatic) |
| Format valid? | PASS | single band float32, EPSG:32611, 3730 rows x 3292 cols, sample geotransform, values in {0,1}, no NaN, 37,654 dots |
| Unique on the 451 submitted downloads? | PASS | max within-3 px overlap 66.53% vs 70% limit; max sampled abs Spearman 0.135 vs 0.90 |
| Unique under the literal rule (any registry raster, incl. calibration lattice)? | **FAIL** | lattice witness `inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif` (SHA-256 verified): 99.78% of dots within 3 px vs 70% limit |
| Beats the 0.2778 champion? | **NOT DEMONSTRATED** | LWST SGMC-CAL HOLDOUT-DTI 0.065702 [0.058992, 0.071240] vs champion 0.064121 (same evaluator). The CI contains the champion point. |
| Beats the 0.4544 leader? | **NOT DEMONSTRATED** | No organizer score exists for this file. ORGANIZER-CONFIRMED leader 0.4544 (xiaofanhu). |
| Promote to a real slot? | **NO** | Protocol Rule 6: promotion is a separate selector step. |

The earlier statement that the file "beats 0.2778 on both metrics" is withdrawn. Its HIDE-RECOVER figure (0.111062) was a per-fold OOF value compared with a mislabelled D2.8 parent. Section 3 has the details.

## 2. Per-site executive summary (focus sites)

Each file is already scored or belongs to a scored family, so none should be resubmitted. The score column is OWNER-REPORT and is not an estimate for the new file.

| Site | Best owner-reported file | Estimated score (label) | Uniqueness of new LWST vs this file | Holdout SGMC-CAL (label) | Use |
|---|---|---|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` (60,069 dots) | OWNER-REPORT 0.2477 (already scored; not an estimate) | overlap 0.4831 (within 3 px, LWST dots near this file) | HOLDOUT-DTI 0.057932 | DO NOT RESUBMIT (already scored; duplicates the family) |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif` (44,090 dots) | OWNER-REPORT 0.2600 (already scored; not an estimate) | overlap 0.4685 (within 3 px, LWST dots near this file) | HOLDOUT-DTI 0.060592 | DO NOT RESUBMIT (already scored; duplicates the family) |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif` (61,328 dots) | OWNER-REPORT 0.2449 (already scored; not an estimate) | overlap 0.4864 (within 3 px, LWST dots near this file) | HOLDOUT-DTI 0.058262 | DO NOT RESUBMIT (already scored; duplicates the family) |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif` (37,660 dots) | OWNER-REPORT 0.2710 (already scored; not an estimate) | overlap 0.4408 (within 3 px, LWST dots near this file) | HOLDOUT-DTI 0.062967 | DO NOT RESUBMIT (already scored; duplicates the family) |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` (44,090 dots) | OWNER-REPORT 0.2600 (already scored; not an estimate) | overlap 0.4685 (within 3 px, LWST dots near this file) | HOLDOUT-DTI 0.060592 | DO NOT RESUBMIT (already scored; duplicates the family) |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif` (40,199 dots) | OWNER-REPORT 0.2708 (already scored; not an estimate) | overlap 0.4450 (within 3 px, LWST dots near this file) | HOLDOUT-DTI 0.063010 | DO NOT RESUBMIT (already scored; duplicates the family) |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (37,654 dots) | OWNER-REPORT 0.2778 (already scored; not an estimate) | overlap 0.4153 (within 3 px, LWST dots near this file) | HOLDOUT-DTI 0.064121 | DO NOT RESUBMIT (already scored; duplicates the family) |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` (41,865 dots) | OWNER-REPORT 0.2632 (already scored; not an estimate) | overlap 0.4542 (within 3 px, LWST dots near this file) | HOLDOUT-DTI 0.062551 | DO NOT RESUBMIT (already scored; duplicates the family) |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` (38,854 dots) | OWNER-REPORT 0.2750 (already scored; not an estimate) | overlap 0.4238 (within 3 px, LWST dots near this file) | HOLDOUT-DTI 0.064444 | DO NOT RESUBMIT (already scored; duplicates the family) |

**New file (LWST, `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif`):** estimated score **not available**. Its SGMC-CAL value lies above the maximum of the 21 owner-scored rasters (0.0644), so any number would be an extrapolation and is not reported.

## 3. Corrections to earlier claims

| # | Earlier claim | Status | Evidence |
|---|---|---|---|
| C1 | LWST beats 0.2778 on both HOLDOUT-DTI metrics | WRONG (overstated) | SGMC-CAL CI contains the champion point; HR for the catalogue-built champion is not leak-free (Rule 2). |
| C2 | 0.111062 [0.098423, 0.123755] is the shipped file's HIDE-RECOVER value | WRONG | It is a per-fold OOF value. `evaluate_holdout.py` on the shipped file gives 0.006130 [0.005175, 0.007123]. |
| C3 | 0.099202 is the 0.2778 champion baseline | WRONG | It is the D2.8 parent e56ea318af89 (owner-reported 0.2600). The true champion e5eb6e7e gives static HR 0.004515. Code fixed in `scripts/run_lwst_experiments.py` (IR-SASS3-08). Artifacts still carry the old value until the pipeline is rerun. |
| C4 | Sibling repos at sassnarep3-star/GEMSDOE* | WRONG (404) | Rewritten to buffedlizard55-lab. 18 unique targets, all resolved in the sibling checkouts (IR-SASS3-09). The owner should confirm the mapping. |
| C5 | Uniqueness max 63.27% across 385 rasters | STALE | Current audit: 66.53% across 451 submitted rasters (vs gemsdoe32-h49, newer). Still under 70% on downloads; see C9 for the literal rule. |
| C9 | This review: file OK to upload, uniqueness PASS | WRONG (corrected) | The audit excluded `inputs/calibration`. That raster is a registry raster under the literal rule. It has 99.78% overlap, which fails the 70% limit. Main's review (`docs/research/review-20261028.md`) reaches the same block. |
| C6 | Root cause of the portal error is NaN outside the footprint | UNVERIFIED | No portal log exists. The file passes the format gate, so it is safe under the stated rule. |
| C7 | verify_all_gates 30/30 PASS = independent verification | OVERSTATED | It reads JSON the pipeline wrote. The recomputed gates are in `scripts/independent_review.py` (IR-SASS3-15). |
| C8 | Leaderboard progression 0.4413 to 0.4544 | CORRECT | Live public top: xiaofanhu 0.4544 (ORGANIZER-CONFIRMED). Public scores may differ from the private final (Rules 3.2). |

Irregularities, including the open items, are in `evidence/irregularities_ledger.json` (IR-SASS3-01..18).

## 4. Proxy validation (concordance with owner scores, n = 21)

| Proxy (HOLDOUT-DTI) | Spearman vs OWNER-REPORT | 95% bootstrap CI |
|---|---|---|
| SGMC-CAL (calibrated off-catalogue) | 0.869 | [0.606, 0.980] |
| SGMC raw | 0.550 | [0.050, 0.878] |
| HIDE-RECOVER | 0.143 | [-0.378, 0.583] |

Reading: SGMC-CAL ranks the owner scores well, so it is the more useful proxy. HIDE-RECOVER does not rank them, and it should not be used for selection.

## 5. Holdout comparison (same evaluator, B_visible = 2 px)

- LWST: HIDE-RECOVER HOLDOUT-DTI 0.006130 [0.005175, 0.007123] (GEMSDOE32-HIDE-RECOVER-v3.0, B_visible=2 px, n_withheld 22,232); SGMC-CAL HOLDOUT-DTI 0.065702 [0.058992, 0.071240] (GEMSDOE32-SGMC-CAL-v3.0).
- Champion e5eb6e7e: HIDE-RECOVER HOLDOUT-DTI 0.004515 (static; NOT leak-free under Rule 2 because the champion was built from the full catalogue); SGMC-CAL HOLDOUT-DTI 0.064121 (same evaluator, same process as the LWST receipt); OWNER-REPORT 0.2778.
- LWST SGMC-CAL 95% CI [0.059, 0.071] contains the champion point 0.064121: the difference is not significant.

## 6. Why the 0.2778 file scored highest, and what this means (PhD-level reading)

The evidence supports a narrower answer than the prompt implies:

1. The 0.2778 file is the best member of a near-duplicate family. Its neighbours overlap 86.7-100% within 3 px (IR-SASS3-02, from the repo's earlier audit). Its owner-reported score is the highest of the 21 known files.
2. Across all 21 owner-scored files, SGMC-CAL ranks the owner scores well (rho 0.87). This is consistent with an off-catalogue advantage, but that is an inference, not a test. HIDE-RECOVER does not rank them (rho 0.14), so the static HR value cannot explain the score.
3. The gap to the leader (0.2778 to 0.4544) is 0.1766. Nothing in this repo shows a route to that gap. The most promising route is probably a different family of method. That is an open question for the user, not a result.

## 7. Experiment E1 (H-SASS3-E, basement minimum-curvature ridges)

- Hypothesis: Basement-relief minimum-curvature ridges (depth_to_base_surf) weighted by |grad z|.
- HIDE-RECOVER HOLDOUT-DTI 0.001576 [0.000263, 0.003255]; SGMC-CAL HOLDOUT-DTI 0.000914 [0.00033, 0.001634].
- Single-feature canary: symmetric AUC 0.602 (pass, <= 0.90).
- Pre-registered criteria failed. Verdict: **NEGATIVE**. Slot spent: False.
- The E1 candidate was not run against the calibration lattice. The verdict is negative on the holdout, so the lattice check is moot for E1. It would be required before any promotion.
- Evidence: `evidence/hypothesis_h_sass3_e_experiment.json`, produced by `scripts/hypothesis_h_sass3_e_basement_curvature.py`.

## 8. Ranked untried hypotheses (3 to 5)

Ranking is by expected DTI improvement and implementation cost. "Untried" means not found by a keyword screen of this repo and of the 882 Markdown files in the nine sibling checkouts. It is not exhaustive.

| Rank | ID | Status | Layer(s) | Physical signature | Non-fault mimic | Why new |
|---|---|---|---|---|---|---|
| 1 | H-SASS3-E | TESTED - NEGATIVE (experiment E1, 1 of 3 budget; no slot spent) | depth_to_base_surf (cached feature stack) | narrow ridges of the most-negative Hessian eigenvalue, weighted by local relief |grad z| of the basement surface | sedimentary onlap and paleochannel incision along the basement | The phrase 'minimum curvature' and 'watershed' have no hits in the repo or the sibling docs (keyword screen). 'Hessian' is common (119 sibling files), so the novelty is the layer and statistic pairing, not the Hessian itself. |
| 2 | H-SASS3-F | UNTESTED (candidate for experiment E2) | tmi_hg, iso_grav_anom_hg, geod_shearrate, cond_surf (cached stack) | sharp, lineated boundaries between Gaussian-mixture components of the standardised multi-layer geophysical vector | lithologic contacts and playa-margin conductivity changes | The term 'Gaussian mixture' has no hit in the sibling docs (keyword screen). The repo's EXP1 is an unsupervised tree model, not a mixture boundary. |
| 3 | H-SASS3-G | UNTESTED | ieq_n100a15, deq_n100a15 (cached stack) | anisotropic point-pattern clustering (Ripley's K) of earthquake epicentres that aligns into linear clusters | aftershock sequences and induced seismicity | Ripley's K has no hit in the sibling docs. Partial overlap with H-SASS3-D (plane fitting of relocated seismicity), so treat it as a variant. |
| 4 | H-SASS3-H | UNTESTED (lowest priority) | geod_dilaterate (cached stack) | Otsu-thresholded ridges of geodetic dilatation | subsidence and thermal-expansion strain | Otsu has no hit in the sibling docs. Weak physical link to faults; rank last. |

## 9. Official sources (status in this session)

| Source | Status | Use |
|---|---|---|
| https://docs.nlr.gov/docs/fy26osti/96647.pdf (GEMS Prize Official Rules, Sept 2026) | Fetched 2026-10-28 | Single GeoTIFF, 100 m; three submissions per week; public vs private scoring; generative-AI disclosure |
| https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | Fetched 2026-10-28 (earlier session) | Metric (distance-weighted Tversky, alpha 0.2, beta 0.8, 300 m kernel); format |
| https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | Fetched 2026-10-28 (earlier session) | Leader 0.4544 (ORGANIZER-CONFIRMED) |
| https://github.com/drivendataorg/gems-prize-reference-solution (commit aebe92f) | Cloned | Metric is not in the notebook |
| https://github.com/buffedlizard55-lab/GEMSDOE{24,25,27,28,30,31,32,33,36} | Tarballs downloaded and checked | Sibling submissions; champion SHA-256 matches the sibling audit |
| https://github.com/sassnarep3-star/GEMSDOE* | 404 | Not usable (C4) |
| https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif (lattice witness) | Checked in the sibling checkout; SHA-256 b4570b40... matches main's pin | Literal registry rule (C9) |

| USGS GeoDAWN (doi 10.5066/P93LGLVQ, cited in the Rules), epsg.io/32611, Tversky index wiki, gbcge.org INGENIOUS, USGS ANSS | NOT fetched in this session | Listed for manual review |

## 10. Limitations

1. The literal registry rule blocks this file (C9). 99.90% of the footprint lies within 3 px of a lattice positive, leaving 5,379 footprint pixels outside the buffer. Passing needs at least 11,297 of the 37,654 dots there. Literal rule is unsatisfiable at this dot count: the uncovered footprint pixels are fewer than the dots needed outside the 3 px buffer. The owner must decide whether the synthetic calibration lattice counts under Rule 1. This review applies no exemption.
1a. No organizer score for the new file. Only the upload itself can show whether it is accepted or what it scores.
2. Holdout values are proxies. The HIDE-RECOVER proxy is not leak-free for catalogue-built masks, and it does not rank the owner scores.
3. Owner scores come from the task prompt, not from organizer receipts.
4. Uniqueness was checked on final dots only. The surface check that Rule 1 also requires was not re-run. The downloads audit excludes non-download rasters; the literal gate adds the lattice only.
5. Zeros fill the area outside the footprint. The organizer sample uses NaN nodata. Both are in [0,1], but whether the portal treats them identically is unconfirmed.
6. Public and private leaderboard scores can differ (Rules 3.2).
7. Generative-AI use must be disclosed in the submission narrative (Rules 3.2, IR-SASS3-11). This is an owner action.
8. Training data comes from an owner mirror, not from organizer-authenticated downloads (IR-SASS3-14).
9. The sibling checkouts are a snapshot taken 2026-10-28. Newer rasters are not covered.
10. The GitHub Pages site cannot be checked from this sandbox. The local build reproduces the committed pages, but the live site updates only after the merge is published.
11. `scripts/build_docs_pages.py` is broken and not used (IR-SASS3-10).
12. Artifacts from `run_lwst_experiments.py` still show the old baseline until the pipeline is rerun (IR-SASS3-08).

## 11. Run card (Protocol Rule 5, review and experiment E1)

```json
{
  "review": "independent_review_20261028",
  "hypothesis": "H-SASS3-E basement minimum-curvature ridges (E1). Review of the shipped LWST file.",
  "mechanism": "Hessian minimum eigenvalue of depth_to_base_surf weighted by relief (E1)",
  "non_fault_mimic": "sedimentary onlap / paleochannel incision",
  "holdout_dti": {
    "E1_hide_recover": "HOLDOUT-DTI 0.001576 [0.000263, 0.003255]",
    "E1_sgmc_cal": "HOLDOUT-DTI 0.000914 [0.00033, 0.001634]",
    "label": "HOLDOUT-DTI"
  },
  "correlation_overlap_vs_registry": {
    "lwst_max_within3": 0.665348,
    "lwst_max_abs_spearman": 0.135425,
    "limit_within3": 0.7,
    "limit_spearman": 0.9
  },
  "raster_sha256": "bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a",
  "validator": {
    "single_band": true,
    "dtype_float32": true,
    "crs_epsg_32611": true,
    "shape_rows_cols_3730x3292": true,
    "shape_matches_organizer_sample": true,
    "geotransform_matches_sample": true,
    "all_finite": true,
    "values_in_0_1": true,
    "dot_count_expected": true,
    "zero_or_one_only": true
  },
  "submission_name": "gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros",
  "submission_note": "LWST GeoConduit dual-37654 zeros; format and uniqueness gates only",
  "verdict": "negative for H-SASS3-E; review: OK to upload (format+uniqueness), not promoted to a slot"
}
```

## Erratum and status update (2026-10-29)

The sections above are kept as written. The corrections below supersede them where they conflict.

- **C10 — lattice gap count.** The 5,379 footprint pixels outside the 3 px lattice buffer (section "lattice_gate_literal") do not reproduce. Recomputed from the lattice raster: 6,649 pixels (≤3 px), 7,992 (<3 px), 6,514 (≤3 px, after excluding catalogue labels). The conclusion stands: a 37,654-dot file cannot pass the literal rule, and the maximum compliant dot count is about 21,713. Source: `evidence/lattice_gap_check.json`, from `scripts/lattice_gap_check.py`.
- **C11 — two measures of lattice coverage.** `footprint_fraction_within_3px_of_lattice` (0.99896) is footprint coverage. The dot-level figure for the 37,654-dot file is 99.7849% (`evidence/literal_audit_lwst_baseline.json`). The gate uses the dot-level figure.
- **C12 — holdout gates (IR-SASS3-20).** The two holdout gates previously passed on withdrawn baselines. They now require the reproduced HIDE-RECOVER value (0.006130) and paired CIs that exclude zero. Expected blockers are unchanged: HIDE-RECOVER, SGMC, and the literal lattice rule.
- **C13 — card contradiction (IR-SASS3-21).** `ok_to_download` in the archived 37,654-dot card is now `false`, matching the gate. The verdict is unchanged: NOT OK to submit.
- **New candidate.** `docs/downloads/gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-zeros.tif` (21,012 dots, SHA-256 `d84217d5c59ffc7ec06c3f2bbbf390ae764b26bf96810dca6bfe7ab7fd752fdb`) passes the literal rule (lattice 68.9987%, non-lattice max 55.2%, |Spearman| 0.150). Its HOLDOUT-DTI is 0.042851 [0.038871, 0.046157], below the champion control 0.064121 [0.056730, 0.071649] with disjoint CIs. Verdict: **OK to download; NOT recommended for a leaderboard slot.** Run card: `evidence/run_card_literal.json`.
- **Open:** the owner's decision on whether the synthetic calibration lattice counts as a registry raster (IR-SASS3-22); `scripts/independent_review.py` still cannot run in this checkout (IR-SASS3-25); the leaderboard figures in the request conflict with the live page (IR-SASS3-26).
- **Experiment budget (IR-SASS3-28).** The run card records 3 literal candidate experiments (dense, random, dispersed), with controls not counted. E1 (H-SASS3-E) is a separate lane and was recorded as "1 of 3". If the 3-experiment cap applies to all lanes together, the total is 4 and the cap was exceeded by one. The owner must decide whether E1 counts. No further experiments run without that decision.
