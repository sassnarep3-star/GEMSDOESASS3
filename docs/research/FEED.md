# GEMSDOESASS3 status feed

Generated 2026-10-31T05:42:10+00:00 by `scripts/status_feed.py` (freshness rule: <= 24 h). Do not edit by hand - re-run the script.

**19 OK** · **0 STALE** · **1 needs a human/owner decision** · **0 FAIL** · **1 MISSING**

Candidate on the shelf: `gemsdoesass3-s3-ocm-wide44090-20261030T024750Z-s3hash-safe.tif` — 44,090 px, LLI projection 0.153018, SGMC-CAL 0.06539130879655806 [0.05802473442445649, 0.0717971121897092] (HOLDOUT-DTI, 62,703 withheld positives). Projections are not scores.

| status | check | how it was verified | detail | next action |
|---|---|---|---|---|
| ✅ OK | branch state | git status --porcelain, git rev-parse | `{"branch": "arena/c1edbd31-gemsdoesass3", "head": "db0ce4f", "uncommitted_paths": 41}` | — |
| ✅ OK | standing prompt is in the README and mirrored on disk | README.md heading scan + docs/research/standing-prompt-as-recorded-20261027.md | `{"readme_heading": "Standing prompt", "mirror_age_h": 0.93, "re_read_utc": "2026-10-31T05:42:10+00:00"}` | re-read line by line at session start; do not work from memory |
| ✅ OK | competition + external data present and SHA-verified | recompute sha256 of every registry/data_manifest.json entry | `{"verified": 28, "of": 28, "root": ".cache/gems_data", "restore_receipt_age_h": 0.89}` | — |
| ✅ OK | downloadable candidate still matches its build receipt | sha256(docs/downloads/<safe tif>) vs evidence/candidate_build_receipt.json | `{"file": "gemsdoesass3-s3-ocm-wide44090-20261030T024750Z-s3hash-safe.tif", "sha256": "cdfa5f221fd561f2\u2026", "receipt_age_h": 0.93, "emitted_px": 44090}` | — |
| ✅ OK | newest lane build matches its build receipt | sha256(docs/downloads/<newest -build.json raster>) vs that receipt | `{"file": "gemsdoesass3-cdist-52000-20261031T1200Z-zeros.tif", "sha256": "d0c66c560fe8aa21\u2026", "generated_utc": "2026-10-31T05:31:14+00:00", "n_dots": 52000, "submission_note_len": 74, "worst_overlap": 0.4703, "receipt_age_h": 0.13}` | — |
| ✅ OK | in-project format gate (portal range test included) | scripts/validate_submission_tif.py receipt | `{"all_hard_checks_pass": true, "checks_failed": [], "receipt_age_h": 0.93}` | — |
| ✅ OK | 3-px duplicate lane test vs 451 pinned sibling submissions | scripts/lane_sweep.py rows (docs/downloads scope) | `{"max_overlap3px": 0.4467, "cap": 0.7, "n_over_cap": 0, "worst_holder": "GEMSDOE24/docs/downloads/gems24-h24-0-mirror-h19-5-group-best-20261002-e27054cf-allfinite.tif", "correlation_measured": false}` | re-run scripts/lane_sweep.py without --skip-correlation to re-measure |Spearman| vs the 0.90 cap |
| 🧭 TODO | same test against the six calibration lattices (proposed-exemption scope) | scripts/lane_sweep.py rows (lattice scope) | `{"max_overlap3px": 0.9976, "n": 7, "note": "a saturated lattice trivially contains any emission; repo ruling is 'proposed amendment only, not applied', so this must be an owner decision"}` | owner ruling: does the lattice scope count for the uniqueness rule? (docs/research/lattice-decision-20261028.md) |
| ⛔ MISSING | sibling registry bytes on disk | path check | `{"registry_dir_exists": false}` | bash scripts/fetch_sibling_registry_git.sh  (sparse git fetch + sha verify) |
| ✅ OK | evidence receipt fresh (<= 24 h): per-site table on SHA-verified sibling bytes | mtime of evidence/focus9_scoreboard_20261030.json | `{"path": "evidence/focus9_scoreboard_20261030.json", "age_h": 0.93, "bytes": 15853}` | — |
| ✅ OK | evidence receipt fresh (<= 24 h): geometry arms (E1) | mtime of evidence/geometry_experiment_E1_partial.log | `{"path": "evidence/geometry_experiment_E1_partial.log", "age_h": 0.93, "bytes": 4962}` | — |
| ✅ OK | evidence receipt fresh (<= 24 h): operating-point / mass sweep (E2) | mtime of evidence/operating_point_experiment_E2.json | `{"path": "evidence/operating_point_experiment_E2.json", "age_h": 0.93, "bytes": 6152}` | — |
| ✅ OK | evidence receipt fresh (<= 24 h): support-design sweep (E3) | mtime of evidence/operating_point_E3_design.json | `{"path": "evidence/operating_point_E3_design.json", "age_h": 0.93, "bytes": 5761}` | — |
| ✅ OK | evidence receipt fresh (<= 24 h): selection-rule sweep (E3b) | mtime of evidence/operating_point_E3b_selection.json | `{"path": "evidence/operating_point_E3b_selection.json", "age_h": 0.93, "bytes": 6485}` | — |
| ✅ OK | evidence receipt fresh (<= 24 h): geothermal/spring proximity audit | mtime of evidence/geothermal_prior_audit_20261030.json | `{"path": "evidence/geothermal_prior_audit_20261030.json", "age_h": 0.93, "bytes": 5107}` | — |
| ✅ OK | evidence receipt fresh (<= 24 h): protocol run card for this pass | mtime of evidence/run_card_20261030_s3pass.json | `{"path": "evidence/run_card_20261030_s3pass.json", "age_h": 0.93, "bytes": 12249}` | — |
| ✅ OK | evidence receipt fresh (<= 24 h): protocol run card for main’s promoted tipcont pass | mtime of evidence/run_card_20261030.json | `{"path": "evidence/run_card_20261030.json", "age_h": 0.93, "bytes": 3824}` | — |
| ✅ OK | evidence receipt fresh (<= 24 h): main’s candidate re-rendered in the portal-safe encoding | mtime of evidence/portal_safe_render_gemsdoesass3-tipcont-disp44923-4px-20261030T0330Z-safe.json | `{"path": "evidence/portal_safe_render_gemsdoesass3-tipcont-disp44923-4px-20261030T0330Z-safe.json", "age_h": 0.93, "bytes": 1566}` | — |
| ✅ OK | unit/gate test suite green | pytest -q --tb=no | `{"summary": "103 passed, 6 skipped, 1 warning in 8.92s", "exit": 0}` | — |
| ✅ OK | docs/executive-summary.html regenerated after the latest candidate build | mtime comparison | `{"page_age_h": 0.07, "candidate_age_h": 0.93}` | — |
| ✅ OK | docs/index.html regenerated after the latest candidate build | mtime comparison | `{"page_age_h": 0.03, "candidate_age_h": 0.93}` | — |

## Standing questions this repo has not closed

- Owner: does the calibration-lattice scope count for the 70% duplicate rule? (candidate passes submissions 0.45, fails lattice 0.998)
- Owner: slot decision — no file in this repo is currently *promoted*, so no upload is recommended.
- Data: re-measure the Spearman cap on the full registry sweep if the correlation gate must be current.
- Live: the public leaderboard moves; re-fetch the leaderboard page before quoting any high score.
