# Repository review — 2026-10-31

## Executive finding

**No submission is cleared for a competition slot by the evidence currently present in this checkout.** The 2026-10-30 leaderboard-inversion GeoTIFF is a real, format-valid artifact and can be retained for audit, but the site's unconditional “OK TO SUBMIT” banner is not supported by the required protocol gates. Do not submit it based on the current repo state. No new candidate was generated, no candidate was selected, and no leaderboard score is claimed in this review.

## Findings (ordered by severity)

### P0 — Public pages recommend a candidate without required holdout validation

`README.md`, `docs/index.html`, and `docs/executive-summary.html` say to submit `gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif`. The candidate-specific receipt `evidence/validator_lbinv_20261030.json` is a format/estimate validator, not the required holdout run card. It contains no whole-segment hide-and-recover HOLDOUT-DTI, no withheld-positive count or CI, and no per-feature leakage-canary result. The repository's `evidence/current_run_card.json` is for a different, older LWST raster and records primary hide-and-recover as `NOT RUN`, leakage canary as `NOT RUN`, uniqueness as `NOT CLEARED`, and verdict `negative`.

The user protocol also requires uniqueness checks on the continuous surface before placement and on final dots. The lbinv build receipt has no correlation result or pre-placement surface result. Its recorded worst overlap (0.65) is not enough to certify both checks. The method paragraph that is supposed to define the single experiment lane is absent; the README itself notes this omission. These missing gates are blockers, not evidence of a pass.

### P1 — Conflicting “current” records make the decision non-reproducible

The root README and Pages promote lbinv. `evidence/current_run_card.json` and its `docs/data` copy instead identify the 2026-10-29 LWST candidate and mark it negative. Other dated run cards name different candidates and branches. A reviewer cannot identify one authoritative current card from the existing filenames alone. In particular, historical run cards from different branches must not be treated as current validation.

### P1 — The 0.369 figure is an estimate, not validated performance

The lbinv artifact's build receipt records an **ESTIMATE** of 0.3687, based on an inverse model fitted to owner-reported scores. The LOO diagnostics assess score reconstruction on that reported-score corpus; they are not a spatially blocked, whole-segment hide-and-recover test of this candidate and do not establish a public leaderboard score. The 95% band shown on the old pages is not a substitute for the required HOLDOUT-DTI CI. The high score for GEMSDOE32 is also only owner-reported in the supplied evidence; its causal explanation remains unproven.

### P1 — Uniqueness documentation is incomplete for the protocol

The build receipt records maximum overlap 0.65 against a registry entry, but does not record a rank-correlation value or preserve a candidate-specific audit receipt with the full tested registry inventory and surface-stage check. Other artifacts for different candidates cannot fill that evidence gap. Exact non-duplication and protocol uniqueness for lbinv are therefore **not certified by this review**.

### P2 — Tests pass but core evidence checks are skipped on a clean checkout

Final validation run: **98 passed, 8 skipped, 1 warning** after installing the declared `requirements.txt` in an isolated temporary environment and running `pytest -q`. The lbinv tests that rederive its footprint/estimate skip when `.cache/distill_q.npz` and `.cache/gems_data/sample_submission.tif` are absent. Those inputs are not present in this checkout; `data/` contains manifests/audits rather than the competition rasters. Thus the clean-checkout test result must not be described as an end-to-end validation of the candidate.

A separate direct byte inspection in the same temporary environment confirmed the lbinv file is a one-band float32 GeoTIFF, EPSG:32611, shape 3730×3292, transform 100 m with origin (243350, 4508550), finite in-footprint values exactly 0/1, NaN outside, and 84,262 positive cells. Its SHA-256 matches the build receipt (`8f6188763af694dccb400bad7a2549fcaccdfb0b37b6981adfff286e2698ebd1`); the adjacent ZIP contains one byte-identical TIFF and matches its recorded hash. Its finite mask exactly matches the committed packed footprint mask. This verifies file format and consistency with that stored mask, **not** a competition score or the missing protocol gates.

### P2 — No declared reproducible Python environment

There is no `requirements.txt`, `pyproject.toml`, or equivalent at the repository root. A bare environment did not have pytest, rasterio, or scipy. The test run required a temporary venv and manually installed dependencies. CI or a user cannot reproduce the claimed test command from repository instructions alone.

## Tests and commands

- `pytest -q` in temporary venv: **96 passed, 8 skipped, 1 warning**.
- `python scripts/verify_all_gates.py --expect-blocked`: expected fail-closed receipt for the older current card: `ok_to_submit: false`; missing primary holdout, canary and complete uniqueness gates. This command does **not** certify lbinv, because it reads `evidence/current_run_card.json`, which names LWST.
- Direct lbinv file inspection: format and ZIP integrity confirmed as described above.
- No experiment was run: required label/cache inputs and the declared lane are unavailable; the budget is not spent and no promotion decision is made.

## Required work before any candidate can be called submit-ready

1. Obtain authorized competition training labels/features and sample submission through the allowed account process; place data in the documented location and verify hashes. This workspace cannot fetch the login-gated data.
2. Restore the lane paragraph, then use the shared cached-feature, holdout and writer tools—not a private fork. Hold out whole segments with a buffer, derive catalogue features from visible faults only, and mask visible faults pixel-exactly.
3. Run the requested single-feature leakage canary before trusting a feature; report evaluator version, withheld-positive count and spatial-block 95% CI for every HOLDOUT-DTI value.
4. Recompute pre-placement surface correlation/overlap and final-dot overlap against a stated, complete registry pool. Stop if rank correlation exceeds 0.90 or >70% of dots fall within 3 px of any one registry raster.
5. Emit one authoritative run card and have the validator fail closed unless all required gates pass. Synchronize README and Pages from that card. Keep any estimate clearly labeled **ESTIMATE**, never “score.”
6. Only after a candidate beats the required holdout baseline should a separate selector consider a weekly slot. Do not submit or spend a slot on the lbinv artifact based on its current evidence.

## Sources and provenance

This review is based on tracked repository files and local tests, not a live DrivenData receipt. The official competition-format reference linked by the repository is [DrivenData problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/); its competition data tab is login-gated according to the repository's data-access notes. Score assertions from sibling sites remain `OWNER-REPORT` unless backed by an organizer receipt. See `evidence/validator_lbinv_20261030.json`, the candidate build JSON, `evidence/current_run_card.json`, and `scripts/verify_all_gates.py` for the exact local artifacts reviewed.
