# Independent review of the archived LWST GeoTIFF — 2026-10-28

> **Decision: DO NOT SUBMIT.** The archived file is available to download for research only. Its literal registry uniqueness gate fails on the archived lattice measurement, current source rasters are missing, and no new candidate was generated or cleared in this review.

## Executive summary

- **Download:** Yes, for archive/research only. The file is `docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif`.
- **Upload/submission:** **NO**. Archived lattice overlap exceeds the 70% limit; current full-registry uniqueness and pre-placement surface comparisons are not available to rerun. No calibration-lattice exemption is applied.
- **New unique GeoTIFF:** None created in this review. Repackaging or renaming the old file would not make it unique. Generating another raster is blocked by the missing feature stack/registry/sample, the unresolved method lane, and the exhausted prior lane budget.
- **Slot:** None spent; no promotion decision was made by a selector.

## 1. Evidence status and submission gates

| Check | Result | Evidence and freshness |
|---|---|---|
| Local raster format/range | PASS | Fresh local checks: one float32 band, EPSG:32611, 3730 x 3292, recorded transform, finite values in [0,1], 37,654 positives. Official sample comparison available: **False**. |
| Historical submitted-download comparison | **ARCHIVED ONLY — not a current clearance** | archived subset scan over 451 downloads: 66.53% max within 3 px; max sampled |Spearman| 0.135; archived subset-only pass=True. Sibling raster files are absent, and this final-dot scan does not verify the required pre-placement surface for the current registry. |
| Literal rule including calibration lattice | **FAIL CLOSED** | 99.78% within 3 px vs 70% limit; archived prior verification; witness absent from this checkout. Witness hash: `b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2`. |
| Current all-registry surface and final-dot gates | **NOT VERIFIED** | No complete current registry is present. Surface scan freshness=ARCHIVED prior run-card result; not rechecked; final-dot scan freshness=ARCHIVED subset-only result; not a current full-registry clearance. |
| Download for analysis / upload to competition | **YES / NO** | Archive download only; no organizer receipt or submission approval exists. |

### Archived lattice coverage check

The prior witness analysis reports 99.90% of the footprint within 3 px, leaving 5,379 pixels outside the buffer. At 37,654 dots, at least 11,297 would need to be outside to meet the 70% cap, so the archived coverage calculation says the gate is unsatisfiable at that dot count. This is a prior verified calculation, not a fresh measurement in this checkout.

## 2. Score provenance and what can be concluded

No organizer submission-page receipt for the candidate or the nine site files is present in this checkout. All site scores below are **OWNER-REPORT** values copied from the archived audit. **HOLDOUT-DTI** is a local proxy evaluation, not a leaderboard estimate or organizer score. **LLI-PROJECTION** is a model-only estimate with a leave-one-out-error band, not a confidence interval and not a score.

The archived LWST record reports:

- HOLDOUT-DTI 0.006130 [0.005175, 0.007123]; evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives, B_visible=2.0 px. Archived; not rerun here.
- HOLDOUT-DTI 0.065702 [0.058992, 0.071240]; evaluator `GEMSDOE32-SGMC-CAL-v3.0`, 62,703 withheld positives. Archived; not rerun here.
- Archived SGMC-CAL comparator: champion point 0.064121; paired delta +0.001581 [-0.005523, 0.008911]. The paired interval includes zero.
- **Outperformance status: NOT DEMONSTRATED.** These are archived HOLDOUT-DTI proxies, not organizer scores or leaderboard predictions.

The earlier 0.111062 HIDE-RECOVER claim is withdrawn as the shipped raster's score: it was an OOF/per-fold result using a mislabeled parent baseline. The archived static-file evaluation above is the relevant proxy record, and still does not predict a competition score. The task prompt gives conflicting 0.3195 and 0.4413 leaderboard snapshots; later repository notes record a 0.4544 public-board read. This review did not fetch the live leaderboard, so none is asserted as today's value, and no public-board snapshot is an organizer receipt for a particular site file.

### Nine-site executive summary

The maximum pairwise overlap column compares each historical leader against the other eight historical leaders only. It is not a full-registry uniqueness test. The LWST comparison is a separate archived pairwise scan, not a fresh clearance.

| Site | Best file in archived audit | OWNER-REPORT (no receipt) | ORGANIZER-CONFIRMED file score | LLI-v1-S0 projection (NOT a score) | HOLDOUT-DTI proxy | Max 3-px overlap vs other 8 historic leaders | Archived LWST overlap vs this file |
|---|---|---:|---|---|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 (OWNER-REPORT) | No per-file receipt | 0.267242; LOO-MAE band [0.2452, 0.2893] (not a CI) | HOLDOUT-DTI 0.096653 [0.085535, 0.107455]; gems57-pooled-hide-v2; n=22,893 | 100.00% vs GEMSDOE25 (ARCHIVE) | 48.31% (ARCHIVE) |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif` | 0.2600 (OWNER-REPORT) | No per-file receipt | 0.271090; LOO-MAE band [0.2490, 0.2932] (not a CI) | HOLDOUT-DTI 0.100926 [0.090081, 0.111684]; gems57-pooled-hide-v2; n=22,893 | 100.00% vs GEMSDOE24 (ARCHIVE) | 46.85% (ARCHIVE) |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif` | 0.2449 (OWNER-REPORT) | No per-file receipt | 0.264800; LOO-MAE band [0.2427, 0.2869] (not a CI) | HOLDOUT-DTI 0.096395 [0.085284, 0.107090]; gems57-pooled-hide-v2; n=22,893 | 98.02% vs GEMSDOE24 (ARCHIVE) | 48.64% (ARCHIVE) |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif` | 0.2710 (OWNER-REPORT) | No per-file receipt | 0.279079; LOO-MAE band [0.2570, 0.3011] (not a CI) | HOLDOUT-DTI 0.028218 [0.024626, 0.031798]; gems57-pooled-hide-v2; n=22,893 | 100.00% vs GEMSDOE24 (ARCHIVE) | 44.08% (ARCHIVE) |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 (OWNER-REPORT) | No per-file receipt | 0.271090; LOO-MAE band [0.2490, 0.2932] (not a CI) | HOLDOUT-DTI 0.100926 [0.090081, 0.111684]; gems57-pooled-hide-v2; n=22,893 | 100.00% vs GEMSDOE24 (ARCHIVE) | 46.85% (ARCHIVE) |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif` | 0.2708 (OWNER-REPORT) | No per-file receipt | 0.280062; LOO-MAE band [0.2580, 0.3021] (not a CI) | HOLDOUT-DTI 0.029707 [0.026054, 0.033232]; gems57-pooled-hide-v2; n=22,893 | 100.00% vs GEMSDOE24 (ARCHIVE) | 44.50% (ARCHIVE) |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 (OWNER-REPORT) | No per-file receipt | 0.285977; LOO-MAE band [0.2639, 0.3080] (not a CI) | HOLDOUT-DTI 0.003885 [0.003316, 0.004478]; gems57-pooled-hide-v2; n=22,893 | 100.00% vs GEMSDOE24 (ARCHIVE) | 41.53% (ARCHIVE) |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 (OWNER-REPORT) | No per-file receipt | 0.279729; LOO-MAE band [0.2577, 0.3018] (not a CI) | HOLDOUT-DTI 0.052964 [0.046931, 0.058741]; gems57-pooled-hide-v2; n=22,893 | 99.71% vs GEMSDOE24 (ARCHIVE) | 45.42% (ARCHIVE) |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 (OWNER-REPORT) | No per-file receipt | 0.283854; LOO-MAE band [0.2618, 0.3059] (not a CI) | HOLDOUT-DTI 0.004001 [0.003431, 0.004593]; gems57-pooled-hide-v2; n=22,893 | 97.58% vs GEMSDOE27 (ARCHIVE) | 42.38% (ARCHIVE) |

**Cross-site reading:** the archived leader-to-leader overlaps are all above the 70% threshold, so those historical leaders are not unique relative to one another under the specified 3-pixel comparison. The separate old LWST/download scan cannot clear the new/current full registry.

## 3. Prior experiment E1 — negative result

Archived H-SASS3-E (Basement-relief minimum-curvature ridges (depth_to_base_surf) weighted by |grad z|) was marked **NEGATIVE**, with no slot spent. Its metrics were:

- HOLDOUT-DTI 0.001576 [0.000263, 0.003255]; `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives, B_visible=2.0 px.
- HOLDOUT-DTI 0.000914 [0.000330, 0.001634]; `GEMSDOE32-SGMC-CAL-v3.0`, 62,703 withheld positives.
- Single-feature canary: symmetric AUC 0.602103 vs 0.90 limit; pass=True. This is the experiment-specific scalar canary, not the separate 51-channel report.
- This negative historical result is not a reason to start another experiment: the H-SASS3-A ledger records 3/3 experiments and the current checkout's task brief does not identify the active method lane.

## 4. Ranked geological hypotheses — planning only

Ranks are qualitative expected-value/cost priorities, not measured gains. None is approved or validated; expected DTI improvement is unquantified. The cached feature stack is missing. The official sources below were not checked for current coverage or downloadable files, so these ideas are not currently viable experimental plans.

| Rank | Candidate | Status | Layers | Physical signature / why it may reveal uncatalogued faults | Non-fault mimic | Difference from existing repo work | Cost and data availability |
|---:|---|---|---|---|---|---|---|
| 1 | H-SASS3-PLAN-1 | PLANNING ONLY — not implemented or validated | Official GeoDAWN magnetic field plus radiometric K and Th; requires source rasters | Robust paired-flank local residual contrast across a lineament, retained after upward continuation | Lithologic contacts, remanent magnetic bodies, and radiometric facies boundaries | Targets asymmetric alteration around buried fluid pathways rather than scalar SPI/Theta ridge strength or simple ratio fusion. Novelty is a code-inventory hypothesis, not established across sibling repositories. | Moderate; raster alignment, paired-profile statistic, then buffered whole-segment validation. USGS GeoDAWN is the named official source; coverage/download availability was not verified, so not currently viable. Unquantified; qualitative priority only, not a score or projection. |
| 2 | H-SASS3-PLAN-2 | PLANNING ONLY — not implemented or validated | Competition-provided DEM and gravity anomaly; requires the official data package | Scale-dependent cross-slope asymmetry around gravity-gradient lineaments, evaluated on both basin flanks | Alluvial-fan margins, basin stratigraphy, and asymmetric erosional slopes | Tests a paired basin-flank response rather than existing piedmont/gravity score fusion; any distinction from related repository code still needs a code-level audit. | Moderate; multiscale derivatives and controls, then the shared blocked evaluator. The competition data page is the named official source; local package/cache is absent and external availability was not verified, so not currently viable. Unquantified; qualitative priority only, not a score or projection. |
| 3 | H-SASS3-PLAN-3 | PLANNING ONLY — not implemented or validated | Multi-height upward continuations of the official GeoDAWN magnetic field | Direction and magnitude of magnetic gradient-ridge migration across continuation heights | Dipping intrusive contacts and depth-varying lithologic boundaries | Focuses on displacement direction of a ridge through scale, not only its persistence or an Euler-style depth cluster; novelty remains unverified outside this checkout. | High; requires trusted grids at multiple heights, synthetic depth controls, and a leakage-safe holdout. USGS GeoDAWN is the named official source; coverage/download availability was not verified, so not currently viable. Unquantified; lowest priority due data and implementation cost; not a score or projection. |

## 5. Current blockers, provenance, and official sources

- Lane/budget: active method lane is unresolved. Prior ledger `H-SASS3-A: LWST-GeoConduit` records 3 of 3 experiments (elapsed 297.64 seconds); no new experiment was run.
- Data: cached feature stack present=False; official sample present=False; local sibling registry present=False. No current full-registry uniqueness or surface scan is possible from these files.
- Sibling links on the reviewed public pages: 0 targets; local resolution complete=True; all resolved=True. No sibling file targets were present on the reviewed pages; there was nothing to resolve locally.

| Official/reference source | Status in this review | Intended use |
|---|---|---|
| [GEMS Official Rules (PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Cited in the archived review; not fetched again for this edit | File format, scoring disclosure, submission rules; confirm against current organizer page before upload. |
| [Competition problem/data page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [data download](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Not checked in this review; cache absent | Official training data and metric. |
| [Competition leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Not checked in this review; prompt values conflict | No current leaderboard value asserted. An organizer receipt is needed for a per-submission score. |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Named in planning only; coverage and download access not verified | Potential official geophysical layers for hypotheses 1 and 3. |
| [Reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) | Repository is cited in the archived work; not reaudited in this review | Evaluator and submission conventions; use shared `vendor/gems57` tools where appropriate. |
| [Archived lattice witness source](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif) | Previously pinned/hash-checked; local witness missing now | Explains the archived literal uniqueness failure; not a fresh local recheck. |

## 6. Limitations and required next steps

1. Do not submit or spend a slot. First resolve the lane and whether the synthetic calibration raster is in scope without silently changing the protocol.
2. Restore authenticated official data, the sample GeoTIFF, cached feature stack, and a complete current registry. Re-run surface correlation and final-dot overlap against every in-scope registry raster; keep archived results separate.
3. Only after that, and only if the lane budget permits, use the shared `vendor/gems57` evaluator/writer, whole-segment buffered hide-and-recover, single-feature leakage canaries, and report evaluator, withheld positives and 95% CI. No new experiment is authorized by this review.
4. Generate and validate a distinct GeoTIFF only after its method clears the protocol. Check exact CRS, shape, transform, finite [0,1] range and unique name; write a <=140-character truthful note. A selector—not this report—makes any slot promotion decision.
5. Preserve negative results. Do not turn OWNER-REPORT, HOLDOUT-DTI, or model projections into organizer-confirmed scores.

## 7. Run card (Protocol Rule 5)

```json
{
  "review_date": "2026-10-28",
  "review_scope": "Conservative review of an archived candidate; no new experiment or submission was run.",
  "branch": "arena/16f75a44-gemsdoesass3",
  "lane_id": null,
  "assigned_lane_status": "UNRESOLVED: the supplied brief does not identify this checkout's single method paragraph.",
  "historical_lane_record": "GEMSDOESASS3-H-SASS3-A-LWST-GeoConduit",
  "hypothesis": "Review-only. The archived LWST-GeoConduit candidate is not re-proposed or promoted. The most recent separate candidate record is H-SASS3-E and is negative.",
  "mechanism": "No mechanism implemented in this review. Historical candidate descriptions are retained in the archived run card for provenance only.",
  "non_fault_mimic": "The historical H-SASS3-E test lists sedimentary onlap and paleochannel incision; this is not a validation of the archived LWST candidate.",
  "holdout_dti": {
    "archived_lwst_hide_and_recover": {
      "score_label": "HOLDOUT-DTI",
      "evaluator_version": "GEMSDOE32-HIDE-RECOVER-v3.0",
      "withheld_positive_pixels": 22232,
      "b_visible_px": 2.0,
      "pooled_dti": 0.006129822099392871,
      "ci95": [
        0.0051747367243663595,
        0.007122668787303196
      ],
      "evidence_status": "ARCHIVED evaluator record; not recomputed in this review"
    },
    "archived_lwst_sgmc_cal": {
      "score_label": "HOLDOUT-DTI",
      "evaluator_version": "GEMSDOE32-SGMC-CAL-v3.0",
      "withheld_positive_pixels": 62703,
      "prevalence_calibrated_dti": 0.06570231430849702,
      "ci95": [
        0.05899206995492947,
        0.07124034012798368
      ],
      "evidence_status": "ARCHIVED evaluator record; not recomputed in this review"
    },
    "experiment_E1_hide_and_recover": {
      "score_label": "HOLDOUT-DTI",
      "evaluator_version": "GEMSDOE32-HIDE-RECOVER-v3.0",
      "withheld_positive_pixels": 22232,
      "b_visible_px": 2.0,
      "pooled_dti": 0.0015759679413580936,
      "ci95": [
        0.00026254042010033306,
        0.003255123916317332
      ],
      "evidence_status": "ARCHIVED negative experiment E1; no slot spent"
    },
    "experiment_E1_sgmc_cal": {
      "score_label": "HOLDOUT-DTI",
      "evaluator_version": "GEMSDOE32-SGMC-CAL-v3.0",
      "withheld_positive_pixels": 62703,
      "prevalence_calibrated_dti": 0.0009137119668211215,
      "ci95": [
        0.0003304935857405475,
        0.0016341427069920557
      ],
      "evidence_status": "ARCHIVED negative experiment E1; no slot spent"
    },
    "organizer_score": null,
    "organizer_score_status": "No submission-page receipt for the reviewed candidate is in this checkout."
  },
  "leakage_canary": {
    "E1_single_feature": {
      "feature": "depth_to_base_surf curvature score",
      "auc_vs_withheld_sgmc": 0.3978966518074437,
      "symmetric_auc": 0.6021033481925563,
      "threshold": 0.9,
      "passed": true,
      "evidence_status": "ARCHIVED; this is the experiment-specific single-feature canary, not a current rerun"
    },
    "historical_51_channel_report": {
      "channels_tested": 51,
      "withheld_positive_samples": 11172,
      "negative_samples": 100000,
      "worst_channel": "curv_s2",
      "worst_symmetric_auc": 0.588299,
      "all_passed": true,
      "evidence_status": "ARCHIVED; separate prior report, not a fresh validation of this checkout"
    }
  },
  "registry_correlation_and_overlap": {
    "recomputed_this_run": false,
    "thresholds": {
      "within3_max_fraction": 0.7,
      "absolute_spearman_max": 0.9,
      "buffer_px": 3
    },
    "archived_preplacement_surface_scan": {
      "registry_rasters_checked": 386,
      "max_abs_spearman": 0.125538,
      "closest_raster": "GEMSDOE24:docs/downloads/24gems-gapfill-near-fault-20261026T203338Z-1b2b4ccc37b0-zeros.tif",
      "evidence_status": "ARCHIVED prior run-card result; not rechecked"
    },
    "archived_final_dot_scan_451_downloads": {
      "submitted_rasters_compared": 451,
      "max_within3_fraction": 0.665348,
      "max_abs_sampled_spearman": 0.135425,
      "archived_subset_pass": true,
      "evidence_status": "ARCHIVED subset-only result; not a current full-registry clearance"
    },
    "archived_literal_lattice_result": {
      "within3_fraction": 0.997849,
      "limit": 0.7,
      "pass": false,
      "witness_sha256": "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2",
      "available_in_this_checkout": false,
      "recomputed_this_run": false,
      "evidence_status": "archived prior verification; not re-run"
    },
    "current_registry_clearance": false,
    "preplacement_surface_currently_cleared": false,
    "final_dots_currently_cleared": false
  },
  "raster_sha256": "bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a",
  "zip_sha256": "d93ad7f6278e89247a24ee74d0a64b40c45314f8bb5acc00f58c0f24bfe33e16",
  "validator_output": {
    "all_local_checks_passed": true,
    "organizer_sample_comparison_available": false,
    "crs": "EPSG:32611",
    "shape_rows_cols": [
      3730,
      3292
    ],
    "transform": [
      100.0,
      0.0,
      243350.0,
      0.0,
      -100.0,
      4508550.0
    ],
    "dtype": "float32",
    "finite_range": [
      0.0,
      1.0
    ],
    "positive_pixels": 37654,
    "checks": {
      "single_band": true,
      "dtype_float32": true,
      "crs_epsg_32611": true,
      "shape_rows_cols_3730x3292": true,
      "geotransform_matches_recorded_reference": true,
      "all_finite": true,
      "values_in_0_1": true,
      "dot_count_expected": true,
      "zero_or_one_only": true
    },
    "evidence_status": "Local raster checks freshly rerun; official sample comparison unavailable."
  },
  "submission_name": "gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif",
  "submission_note": "Archive only: format checked; literal registry uniqueness fails the 3-px rule. Do not submit.",
  "download_path": "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif",
  "new_candidate_generated_this_review": false,
  "ok_to_download": true,
  "download_status": "YES for research/archive only; this is not an approved submission.",
  "ok_to_submit": false,
  "status_reason": "Blocked: the calibration-lattice overlap is 99.78% (>70%; archived measurement; witness unavailable for recheck); the all-registry uniqueness clearance is also unavailable. No slot was promoted.",
  "verdict": "negative",
  "promote_to_real_slot": false,
  "slot_spent": false,
  "budget": {
    "prior_lane": "H-SASS3-A: LWST-GeoConduit",
    "prior_lane_experiments": 3,
    "prior_lane_budget_cap": 3,
    "prior_lane_elapsed_seconds": 297.64,
    "new_experiments_this_review": 0,
    "current_lane_resolved": false,
    "reason_no_new_experiment": "Prior lane budget is exhausted; the current task does not identify an assigned method paragraph."
  },
  "official_data_availability": {
    "cached_feature_stack_present": false,
    "official_sample_present": false,
    "local_sibling_registry_present": false,
    "official_external_data_checked_this_review": false,
    "status": "Required inputs are absent; no new candidate can be validated or cleared in this checkout."
  }
}
```
