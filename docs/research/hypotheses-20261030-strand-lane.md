# Hypotheses update 2026-10-30 — strand lanes and the LiDAR-coverage prior (H-N5, H-N6)

Companion to `next-hypotheses-20261029.md` (H-N1 &hellip; H-N4, still untested). This pass adds the two
hypotheses that the live-calibrated &lambda; field and the E1/E2/E3 experiments actually produced, records
their validation status, and corrects a premise that is now stale.

**Stale premise corrected.** The 2026-10-29 file says "the competition labels are not in this workspace, so
the spatially-blocked hide-and-recover evaluator cannot run". That is no longer true: `scripts/restore_data.py`
rebuilds `labels.tif`, `existing_faults.tif`, the SGMC truth and the external rasters into
`.cache/gems_data/` (SHA-256 verified against `registry/data_manifest.json`; receipt
`data/restore_receipt.json`), and every experiment below ran through the repo's own
`GEMSDOE32-SGMC-CAL-v3.0` and `GEMSDOE32-HIDE-RECOVER-v3.0` evaluators. Use the holdout; it works.

---

## Ranking (expected gain measured on the two local instruments; cost = work to implement)

| Rank | ID | Named layers | Physical signature | Why it can catch an off-catalogue fault | Difference from existing repo code | Expected gain | Cost | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | **H-N5** strand-lane emission | `training_features` b19 `det_elev_slope`, b03/b09 TMI h/v gradients, b07/b08 geodetic shear & dilation, + `external/lidar_scarp_features_u8.tif` step/ex_max/lapneg/upface | **curvature ridge of the *level* fields sampled along a lane that runs 1.4&ndash;2 px off an existing emission trace and 5&ndash;50 px off the catalogue**, i.e. an along-strike offset strand rather than a perpendicular collar | the live-fit &lambda; table (40 strata, 111 owner rasters) puts the highest per-pixel credit in exactly that stratum (&lambda;&asymp;0.118 vs 0.042 at 1.0 px and 2.4e-3 inside 3 px of the catalogue): expert mappers extend a known trace onto a *parallel* strand they can see in the LiDAR, they do not re-draw the catalogue line | `scripts/run_selection_sweep.py` selects by &lambda; strata; the shipped `ocm.py`+`emitter` pipeline ranks by intensity inside a collar and never models the *distance-to-previous-emission* axis, which is the axis &lambda; actually turns on | LLI 0.2916 [0.2696, 0.3137] at 44,090 px (champion 0.2860); SGMC-CAL 0.0463 [0.0406, 0.0523] (champion 0.0641) | M | **LANE-BLOCKED**: 0.9326 of its pixels sit within 3 px of the family control's dots &rarr; protocol = log duplicate, STOP. Its &lambda;-band also contains 0.2778, so no improvement is established even before the lane rule |
| 2 | **H-N6** LiDAR-coverage exclusion + wide-lane emission | same, plus `lidar_valid` (band 12 of the external raster) used as a *hard* gate | emit only where `lidar_valid == 0` is false, i.e. restrict to terrain the scarp derivatives can actually see, then take the widest &lambda;-compliant lane | the family's own dots avoid non-LiDAR cells (AUC 0.191 &rarr; ~0.81 the other way): the missing-fault label set is densest where the scarp is *visible*, so scoring a candidate on invisible terrain buys FP only | `ocm.py` returns `valid` but nothing in the repo gates emission on it; `build_candidate.py` is the first place it becomes a selection constraint | LLI 0.1626 [0.1405, 0.1847]; SGMC-CAL **0.0654 [0.0580, 0.0718]** &mdash; above the champion's 0.0641 [0.0567, 0.0716] on the CI-overlapping band, i.e. equal | S | **TESTED, NOT PROMOTED**: passes the lane rule (worst 0.4467 over 451 sibling submissions) and the format gate, but no instrument says it beats 0.2778 |

Both are **negative or neutral as built**. That is a deliverable, not a shortfall: the honest reading of
E1+E2+E3+E3b is that ranking surfaces made from the 19 official bands plus the pinned 100 m scarp
derivative are at their ceiling around SGMC-CAL 0.065, and that the 0.24&ndash;0.28 plateau of the nine focus
sites (0.2449&ndash;0.2778 across 37,654&ndash;61,328 dots, all within 0.017 of a common LLI estimate) is a
**discovery ceiling**, not a tuning gap.

## The free official data that can break the ceiling

Ranked by expected information gain per unit of effort, all no-login:

1. **`great_basin_q_volcanics.zip` + `10.5066/P9YL58W6` (Quaternary slip & dilation tendency)** &mdash; gives a
   *structural* prior per Quaternary segment. Target: segments with high dilation tendency whose trace is absent
   from `existing_faults.tif`; emit the along-strike continuation. Free, small, vector, and directly testable
   against the SGMC truth without a slot.
2. **`wellspringdata.gdb.zip`** (authoritative spring temperatures/chemistry, `temp_c` up to 296.5 &deg;C in the
   extract) &mdash; only useful as a **negative** filter: 46.3% of Hot-class springs are within 1 km of a
   catalogue trace, so the spring halo is where the organizer *does not score*. See `geothermal-vents.md` §3.
3. **1 m 3DEP lidar point clouds over the GeoDAWN/3DEP extents**
   (`https://catalog.data.gov/dataset/geodawn-west-central-nevada-earthmri-data`) &mdash; the only source with
   resolution above the pinned 100 m derivative. Rebuilding step/curvature at 1 m is the one route to a
   ranking that the E1 AUCs cannot reach; cost is days, and the download is bulk but public.
4. **`qfaults_ingenious_nad83conus117_2023-06-27.zip` (v2)** &mdash; supersedes v1; the repo's current
   `gdr_qfaults_traces.csv` (1,126 traces with slip rate + recency) derives from the v1-era compilation, so a
   re-derivation may add traces the labels miss.

## What must be true before any of this gets a slot

Per the binding protocol: (i) run the two holdouts and the leakage canary on the *new* mechanism, not on the
support filter; (ii) lane-test the final dot set against all 451 pinned sibling submissions **and** the six
calibration lattices, and report both scopes; (iii) `portal_range_test_all_cells` must pass on the exact bytes
being uploaded (`scripts/validate_submission_tif.py`, exit code 0); (iv) emit one run card. Nothing in this
file satisfies (i)&ndash;(iv) for a promotable candidate today.
