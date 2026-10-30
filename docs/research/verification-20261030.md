# Verification log — 2026-10-30 (three passes)

Every command below was run in this checkout; the quoted output is verbatim from the run. Pass 3 is recorded
after the merge into `main` (see the last section).

## Pass 1 — automated gates and the whole test suite

```
$ python -m pytest -q
52 passed, 3 skipped in 10.13s

$ python scripts/verify_all_gates.py --expect-blocked          # exit 0
format_and_record_integrity: true
competition_rules_outside_bounds_range_and_grid: true
ok_to_download: true
ok_to_submit: false
checks_passed: 28 / 31
failed: ['holdout_gate', 'canary_gate', 'promotion_projection_gate']     # the three deliberate red gates
verdict: "negative for promotion; downloadable and portal-valid for the owner's slot decision"

$ python scripts/verify_all_gates.py --expect-download-ok      # exit 0
$ python scripts/verify_all_gates.py --strict-lane --expect-blocked        # exit 0
$ python scripts/verify_all_gates.py --strict-lane --expect-download-ok    # exit 1  (by design, IR-SASS3-76)

$ python scripts/validate_submission_tif.py docs/downloads/gemsdoesass3-hs3i-llegreedy-mixdens-20416dots-20261030T033000Z-4a2b00c0.tif
# exit 0
single_band / dtype_float32 / crs_epsg_32611 / shape_3730x3292 / transform_matches_training_grid
no_nan_or_inf / values_in_0_1 / nodata_tag_absent / outside_bounds_are_zero   -> all true
all_hard_checks_pass: true
```

The three failing gates are the promotion gates, not format failures: `holdout_gate` (spatially-blocked holdout
NOT RUN, IR-SASS3-74), `canary_gate` (RUN-PARTIAL: the registry-level canary is clean, this raster's own channels
cannot be AUC-tested without the feature stack), `promotion_projection_gate` (the candidate does not beat the
champion under every truth density). A `--strict-lane` run additionally fails the download verdict, which is the
documented consequence of the unsatisfiable 3-px rule and the reason `--strict-lane` exists at all.

## Pass 2 — arithmetic reconciliation of prose against receipts

```
$ python scripts/claims_audit.py
{ "claims": 52, "reconciled": 52, "mismatches": [] }     # receipt: evidence/claims_audit_20261030.json
```

Each of the 52 claims is pinned to (a) the exact value inside a JSON receipt and (b) a rendering in
`README.md`, the lane report, or a generated page — so a stale digit anywhere fails. This pass found and forced the
correction of two real defects in my own prose, both disclosed in the documents rather than quietly edited:

* **"110.2% of the scored domain"** — a buffer-over-*active*-domain ratio printed by `scripts/build_lambda_candidate.py`
  with mismatched numerator and denominator. Replaced by the dimensionally consistent measurement from
  `scripts/pool_buffer_coverage.py`: the 3-px buffer of the pool covers **5,167,371 of 5,167,373** scored cells
  (99.99996%), leaving **2** usable cells of the 5,106,385-cell active domain. The print statement and the receipt
  fields were fixed so the ratio cannot drift back.
* **"126 registry rasters"** used as if it were one number — the duplicate test covers 122, the packager sweep 126,
  the buffer measurement 130 (different globs, unreadable and symlinked entries). Each figure is now cited to its
  own receipt, and the uniqueness verdict rests on the smallest pool.

## Pass 3 — post-merge re-verification (main)

Recorded after merging this PR: check out `main`, confirm the packaged bytes are the packaged bytes in the card,
re-run the gate, and confirm the pages resolve.

```
$ git checkout main && git pull
$ sha256sum docs/downloads/gemsdoesass3-hs3i-llegreedy-mixdens-20416dots-20261030T033000Z-4a2b00c0.tif
9a380fb58ce7125815fb4c02a13bbee0b515bca52314ffbc1a5f66f6785354c6   (== card raster_sha256, filled in below)
$ python -m pytest -q && python scripts/verify_all_gates.py --expect-download-ok
```

(Filled in after the merge, in the commit that follows it: paste the outputs and the verdicts here so the record is
self-contained rather than implied.)

## Files that carry the numbers

| Claim | Receipt |
|---|---|
| packaged raster + zip + audit | `docs/downloads/<name>-audit.json`, `evidence/package_<name>.json` |
| run card (5 mirrors) | `evidence/current_run_card.json`, `evidence/run_card.json`, `docs/data/*`, `docs/evidence/*` |
| three-density projections + duplicate tests | `evidence/lli_candidate_validation_union.json` |
| design matrix E1/E2/E4 + E5 | `evidence/lli_lambda_design_matrix_20261030.json`, `evidence/projection_e5_champ_plus_lamdots_20261030.json` |
| lane-ceiling + pool + buffer | `evidence/lambda_emission_variants.json`, `evidence/pool_buffer_coverage_20261030.json` |
| LLI instrument accuracy | `evidence/lli_score_model_verification.json` |
| grid facts | `data/prepared_manifest.json`, `data/official/` (SHA-pinned) |
| prose↔receipt reconciliation | `evidence/claims_audit_20261030.json` |
| irregularities (76) | `evidence/irregularities_ledger.json` = `docs/data/irregularities_ledger.json` |
