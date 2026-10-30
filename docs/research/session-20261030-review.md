# Session review, 2026-10-30: what is verified, what is blocked, what to do next

Scope: review the repo, verify the competition rules and metric from official pages, fix the shared validator, make the submission status obvious, and rank the next hypotheses. No new holdout experiment was run (labels are absent, see §4). Every number below carries a label: **OFFICIAL** (organizer page), **RECEIPT** (a repo file), **OWNER-REPORT** (typed in the request, not an organizer receipt), or **HOLDOUT-DTI** (repo evaluator, named with its version).

## 1. Short answers

| Question | Answer |
|---|---|
| Which file can be downloaded? | `docs/downloads/gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.tif` (SHA-256 `7035c254…fe49a`). **Analysis copy only.** Competition download: **NO** (owner decision, IR-SASS3-71). |
| Is it OK to submit? | **NO.** The holdout and leakage-canary gates were not run, because the labels are not in this workspace (IR-SASS3-73). |
| Estimated leaderboard score? | **None can be given.** The only number is a HOLDOUT-DTI proxy of 0.042851 [0.038871, 0.046157], below the champion's proxy. It is not a leaderboard estimate. |
| Is it unique? | YES on the literal rule, per the 2026-10-29 receipt: worst lattice overlap 68.9987% (limit 70%). Not re-run this session (IR-SASS3-77). |
| Why did 0.2778 score highest? | Not established. See §5 (mechanistic hypotheses only). |
| Can a higher score be reached from this repo? | Not shown. No holdout result in the repo beats the champion's proxy. Labels are required to test anything. |
| Leaderboard top? | **0.4544** (xiaofanhu), live page, fetched 2026-10-30. The 0.4413 and 0.3195 figures in the request do not match the page (IR-SASS3-75). |

## 2. Official sources checked line by line

| # | Claim | Source (fetched 2026-10-30) | Status |
|---|---|---|---|
| 1 | Metric = distance-weighted Tversky, α=0.2, β=0.8, triangular kernel with R = 300 m (3 px); TP_w = Σ_g max_x p(x)k, FP_w = Σ_x p(x)[1 − max_g k], FN_w = Σ_g [1 − max_x p k] | [Problem description, page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | **OFFICIAL.** Matches `src/gems32/metric.py` term by term; equivalence tests added (`tests/test_official_metric_and_validator.py`). |
| 2 | Predictions are probabilities in [0, 1]; single float32 layer; EPSG:32611; 100 m; same bounds; **data outside the bounds is null or nan** | page 967, "Submission format" | **OFFICIAL.** Zeros outside are not compliant. Validator now enforces this (IR-SASS3-74, 78). |
| 3 | Known USGS/INGENIOUS fault pixels are masked from scoring, so they neither add nor remove credit | [DrivenData forum thread 11516, staff reply of Sep 16](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) (year not shown on the fetched page) | **OFFICIAL (staff statement).** Consequence: zeroing catalogue traces (as `submission_writer.py` does) is neutral for scoring. |
| 4 | Three submissions per week | [NLR Official Rules PDF §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | **OFFICIAL.** |
| 5 | Labels come from the USGS Quaternary Fault and Fold Database and from expert-labelled new faults (NLR/USGS) | Rules PDF §2 | **OFFICIAL.** The database is a free public source. |
| 6 | Training data and labels require a DrivenData profile | Rules PDF §3.1 | **OFFICIAL.** Labels cannot be fetched by this agent. |
| 7 | Generative-AI use must be disclosed in the narrative | Rules PDF §3.2 | **OFFICIAL.** Required in any submission narrative. |
| 8 | Leaderboard, best public DW-Tversky: #1 xiaofanhu 0.4544; #2 cfld__ 0.3916; #3 Batik Shirt Brothers 0.3911; #4 BrandenKMurray 0.3841; #5 op01 0.3642 | [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | **OFFICIAL (public board).** The README's older #4 (0.3724) and #5 (0.3635) are stale. |
| 9 | Reference solution: U-Net with Tversky loss (α 0.2, β 0.8); the notebook has no scoring code | [gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution), commit `aebe92f7` (2026-06-16), cloned to `/tmp` | **OFFICIAL (code).** The notebook's own "Known Faults" plot and thresholding note are not a metric. |
| 10 | GEMSDOE32 champion, 0.2778 | [GEMSDOE32 site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | **OWNER-REPORT.** The site itself says no receipt links the raster to the score. |
| 11 | Nine focus-site scores (24, 25, 27, 28, 30, 31, 32, 33, 36) | Request text | **OWNER-REPORT.** `registry/owner_reported_scores_focus.json` matches all 21 typed values. |
| 12 | Rules say 0.4413 and 0.3195 are the top score | Request text | **CONFLICT** with the live page (IR-SASS3-75). |

## 3. Repo checks run this session (reproducible)

- `pytest -q`: all tests pass, including 10 new regression tests (see README for the count).
- `scripts/verify_all_gates.py`: `ok_to_download` false, `ok_to_download_for_analysis` true, `ok_to_submit` false. The holdout and canary gates fail, as designed.
- `scripts/validate_submission_tif.py` on the candidate: **all hard checks pass**, receipt `evidence/validator_candidate_20261030.json`. 0 finite cells outside the footprint, 0 NaN cells inside, 21,012 positives, values {0, 1}, EPSG:32611, 3730×3292, transform matches.
- Footprint recovered from the committed `evidence/organizer_footprint_mask.npz` (5,167,373 cells, sample SHA `2176d08e…` matches `data/restore_receipt.json`).

## 4. Blocked items (and why)

| Item | Status | Evidence |
|---|---|---|
| `labels.tif`, `training_features.tif` | **Absent.** `data/restore_receipt.json` says "restored" into `.cache/gems_data`, but that directory does not exist (IR-SASS3-73). | `ls -la .cache` → no such directory; `find / -name labels.tif` → nothing |
| DrivenData data page | **Not reachable** from this sandbox (login-walled; host not on the allowlist). | `curl` → HTTP 000 |
| USGS fault database (free, official) | **Not reachable** from this sandbox. | `curl https://www.usgs.gov` → HTTP 000 |
| GitHub | Reachable (`github.com` 200). Used only for the reference-solution clone. | `curl https://github.com` → HTTP 200 |

## 5. Why 0.2778 scored highest (what the evidence supports, and what it does not)

Supported by the repo's receipts:
- 0.2778 is OWNER-REPORT only (IR-SASS3-76).
- Overlap within 3 px between the nine historical focus-site files: 72 pairs, range 86.7%–100% (`evidence/focus_site_candidate_audit_20261028.json`, RECEIPT, recomputed 2026-10-30). The README's "99.9–100%" does not match this receipt (IR-SASS3-79).
- SGMC-CAL HOLDOUT-DTI (`GEMSDOE32-SGMC-CAL-v3.0`, n = 62,703 withheld off-catalogue positives): champion 0.064121 [0.056730, 0.071649]; GEMSDOE36 0.064444 [0.057087, 0.071958] (`evidence/proxy_leaderboard_concordance.json`, RECEIPT). Ranked over all 21 owner-scored rows of that receipt, the champion is second; the top row is GEMSDOE36 (owner 0.275), with overlapping intervals.
- HIDE-RECOVER ordering does not reproduce the leaderboard: Spearman ρ = −0.8896 (p = 0.0006), Kendall τ = −0.7674, n = 10; the champion has the second-lowest holdout DTI (`evidence/holdout_vs_leaderboard_concordance_20261029.json`, RECEIPT). The static holdout therefore cannot explain the owner scores.

Mechanistic hypotheses (**not verified**; each needs labels to test):
- H-A: the score comes from kernel coverage. A 37,654-dot file that spreads mass over many fault-like ridges collects 300 m credit from many new segments, because TP_w rewards any pixel within 3 px of a truth pixel. This is a property of the official metric, not evidence about this file.
- H-B: the champion lies in a family of near-duplicate placements, so its score is the family's score. Testable only with the public-board scores of each family member.
- H-C: the public-test chunks contain fault families the repo's holdout does not model (for example, scarps the USGS catalogue omits). The leaderboard is public-test only, so this cannot be ruled out.

What would settle it: an organizer receipt for the champion, and labels for the holdout.

## 6. Hypotheses (ranked; **all UNTESTED**, none can be promoted)

Each candidate was checked against the repo's feature set (`src/gemsdoesass3/features.py`, `src/gems32/features.py`, `data/feature_bands_audit.json`) before being ranked. Expected gain is qualitative. No number is claimed.

| Rank | ID | Layer(s) | Physical signature | Why it could catch an off-catalogue fault | Non-fault mimic | Overlap with repo | Expected gain / cost | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | **H-S30-2** Gravity–magnetic edge offset as a dip signature | band 13 `iso_grav_anom` (horizontal gradient, band 18) and band 3 `tmi_hg` (magnetic horizontal gradient) | Horizontal-gradient maxima of gravity and magnetics (Blakely & Simpson 1986, [DOI 10.1190/1.1442197](https://www.usgs.gov/publications/approximating-edges-source-bodies-magnetic-or-gravity-anomalies)) are offset horizontally when a dipping fault juxtaposes units with different density and susceptibility. The offset grows with depth. | A buried fault with no surface trace still juxtaposes units. The USGS catalogue only lists traced faults, so the offset is a signal the catalogue cannot supply. | Lithologic contacts with different dips or remanence; terrain-correction residuals. | Gradients are used separately (`tmi_hg`, `iso_grav_anom_hg`). A pairwise offset test between them is **not** in `features.py`. Novelty check still required. | Medium gain if the dip signature holds; medium cost (needs a per-pixel offset estimate). | UNTESTED |
| 2 | **H-S30-1** Dilatation-rate zero-crossing lines | band 8 `geod_dilaterate` | Sign change (extension ↔ contraction) of a smoothed dilatation field, traced as 1-px lines where the gradient is high. | Strain-regime boundaries mark normal-fault blocks and transfer zones, which can be unmapped. | Interpolation and coverage edges of the geodetic product. Mask them with the band's no-data pattern before tracing. | `features.py` uses the **magnitude** of `dilate_z` in slip-dilation (line ~381). The zero-crossing operator is **not** implemented. | Lower gain (strain is coarse); low cost. | UNTESTED |
| — | Rejected: soft-probability emission | — | — | — | — | `src/gems32/emitter.py` already applies the metric's marginal rule (`marginal_inclusion_threshold`, `alpha * DTI`). Not new. | — | Rejected (duplicate) |
| — | Rejected: basement-step lines from depth-to-base | band 15 | — | — | — | `basin_fault_wall_grad` (features.py ~65) is already this. | — | Rejected (duplicate) |
| — | Rejected: seismicity-ratio anomaly | bands 10, 16 | — | — | — | `seismic_strain_coupling` (features.py ~405) already combines these. | — | Rejected (duplicate) |

**Validation plan (not run):** feature-only leakage canary (AUC ≤ 0.90 required), then buffered hide-and-recover on the spatially-blocked holdout, then a paired CI against the champion's control. Nothing is promoted without a CI above the control. Blocked until labels are available (§4).

## 7. What is needed to go further (in order)

1. **Owner:** download `training_features.tif` and `labels.tif` from the DrivenData data page with your account (rules §3.1). Place them in `.cache/gems_data/` and re-run `scripts/restore_data.py`. Compare the SHA-256 of your download with the pins in `data/restore_receipt.json`. If they differ, the pins are wrong (IR-SASS3-73).
2. **Owner or network allowance:** the USGS Quaternary Fault and Fold Database (free, official, rules §2) via ScienceBase/usgs.gov. This sandbox cannot reach it (§4). Once reachable, the SGMC proxy can be rebuilt from the official source instead of a mirror.
3. **Owner decision:** download authorization (IR-SASS3-71), the lattice question (decision memo), and the zeros-versus-NaN question for the owner-scored files (IR-SASS3-78). The portal's handling of zero-filled files can be checked on the submission page.
4. **Then, in the next session:** run H-S30-2 (rank 1) through the validation plan above. Run H-S30-1 only if H-S30-2 fails.
5. **Re-check uniqueness** of the chosen file against the live registry (`scripts/fetch_registry_rasters.py`, GitHub access is allowed). Do not reuse the 2026-10-29 receipt for a new file (IR-SASS3-77).
6. **Disclose** generative-AI use in the submission narrative (rules §3.2).

## 8. Irregularities raised this session

IR-SASS3-73 (labels absent; restore receipt contradicts disk), 74 (validator bug, resolved), 75 (leaderboard figures, resolved in the docs), 76 (0.2778 is owner-reported), 77 (uniqueness not re-run), 78 (zeros-versus-NaN convention), 79 (README overlap range does not match the receipt), 80 (file-name suffixes differ between the request and the registry). Full text: `evidence/irregularities_ledger.json`.

## 9. Sources used in this document

- [Problem description, page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [NLR Official Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Forum thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)
- [Reference solution repository](https://github.com/drivendataorg/gems-prize-reference-solution)
- [Blakely & Simpson 1986, USGS](https://www.usgs.gov/publications/approximating-edges-source-bodies-magnetic-or-gravity-anomalies)
- [GEMSDOE32 site (champion)](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)
- Repo receipts: `evidence/run_card_20261030.json`, `evidence/validator_candidate_20261030.json`, `evidence/literal_candidates_sgmc.json`, `evidence/run_card_literal.json`, `registry/owner_reported_scores_focus.json`
