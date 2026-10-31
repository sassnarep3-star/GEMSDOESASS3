# GEMSDOESASS3 current status feed

Generated 2026-10-31T04:54:45+00:00 from the 2026-10-31 review card and local checkout.

## Decision: NO-GO — do not submit

This feed is fail-closed. It does not select a weekly slot or certify portal acceptance.
The public leaderboard snapshot and all owner-reported per-site scores have distinct evidence classes.

Branch: `arena/a4b6bc6f-gemsdoesass3` · HEAD: `db0ce4f` · Candidate: `gemsdoesass3-lane70-consensus-55000-20261030T073000Z-c4d19b7e-safe` (archival, negative).

| Status | Check | Evidence class | Detail | Next action |
|---|---|---|---|---|
| **FAIL** | uniqueness | REGISTRY-MEASUREMENT (recorded; not re-run by this script) | `{"max_abs_binned_spearman": 0.983609033618752, "references_over_0p90": 1909, "strict_max_overlap_3px": 0.995182, "max_overlap_excluding_lattice": 0.6952727272727273, "preplacement_surface_check": null}` | Fail candidate; do not exclude the lattice or claim a pass. |
| **MISSING** | inputs | LOCAL-CHECK | `{"verified_manifest_files_present": 0, "manifest_files": 28, "cache_root": ".cache/gems_data"}` | Restore the authorized official feature/label cache. |
| **MISSING** | runtime | LOCAL-CHECK | `{"numpy": false, "rasterio": false, "scipy": false, "sklearn": false, "pytest": false}` | Install project dependencies in a reproducible environment before geospatial revalidation. |
| **NEGATIVE** | decision | REPOSITORY-REVIEW | `{"verdict": "negative", "ok_to_submit": false, "new_tif_generated": false, "slots_spent": 0}` | Do not upload; satisfy the documented blockers before proposing a candidate. |
| **RECEIPT-CLAIMS-PASS-NOT-PORTAL-CONFIRMED** | format | FORMAT-RECEIPT (recorded; not re-run by this script) | `{"crs": "EPSG:32611", "shape": [3730, 3292], "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0], "no_nan_inside_footprint": true, "stored_values_in_range_0_1": true, "organizer_portal_acceptance_receipt": false, "artifact_sha256": "e2e4380991586b99c9b9da1abc3272782d3562134515891469fa882ba02c7f8d"}` | Re-run exact-byte checks and capture the portal's acceptance receipt before any submit claim. |
| **RECORDED-NOT-RERUN** | holdout | HOLDOUT-DTI | `{"evaluator_version": "GEMSDOE32-HIDE-RECOVER-v3.0", "n_withheld_positives": 22232, "dti": 0.07893860428429801, "ci95": [0.06869196481136113, 0.08918496004671007], "use": "Not interpreted as leaderboard performance; target is not equivalent to the competition's expert-mapped off-catalogue test labels."}` | Restore data and reproduce with shared evaluator; do not treat as leaderboard score. |
| **SNAPSHOT** | leaderboard | ORGANIZER-CONFIRMED | `{"source": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/", "fetched_utc": "2026-10-31", "top_rows": [{"rank": 1, "participant": "xiaofanhu", "public_score": 0.4544}, {"rank": 2, "participant": "cfld__", "public_score": 0.3934}, {"rank": 3, "participant": "Batik Shirt Brothers", "public_score": 0.3917}, {"rank": 4, "participant": "BrandenKMurray", "public_score": 0.386}, {"rank": 5, "participant": "op01", "publi…` | Refresh manually from official public leaderboard before making a current leaderboard claim. |
| **OK** | scope | BUDGET-RECORD | `{"experiments_used_this_review": 0, "submission_slots_spent": 0, "lane_assignment_available": false}` | Recover the assigned method paragraph; the protocol says not to invent it. |

## Refresh policy

`python scripts/status_feed.py` refreshes local state only. Refresh the official public leaderboard from [DrivenData](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) separately; this tool never reports per-submission organizer scores unless a receipt is explicitly saved.
