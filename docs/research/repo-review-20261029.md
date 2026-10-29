# Repository review — 2026-10-29

## Executive decision

**No submission is approved. Do not upload either checked-in TIFF.** The 2026-10-29 “unique-structural” file has only an unverified sidecar; no reference sample, footprint, labels, or registry data are present in this checkout. The earlier LWST TIFF has a historical literal registry-overlap failure. No leaderboard score or score projection is supported for the new raster.

This is a documentation and static-source review, not a fresh scientific experiment. It deliberately does not claim that past metrics were reproduced. The provided prompt asks for at most three experiments; this review ran zero experiments and used no submission slot.

## What was checked

- Repository status and tracked file inventory; current branch is `arena/9b81fdbe-gemsdoesass3`.
- README, run cards, uniqueness audit/irregularity ledger, page-builder and gate-verifier source, workflow configuration, and available raster artifact sidecars.
- `python -m compileall -q scripts src vendor` completed successfully (syntax check only; it does not execute imports or validate results).
- `python -m pytest -q` could not run: `pytest` is not installed.
- `python scripts/verify_all_gates.py` could not run: `numpy` is not installed. The absence of rasterio and the official reference TIFFs also prevents a new independent raster validation in this checkout.

## Findings (ordered by risk)

1. **Critical — newest download has not passed uniqueness or official-grid validation.** The sidecar `docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-audit.json` explicitly records that its registry overlap and footprint/sample match could not be checked. It describes generated NNE corridors, not output from the requested cached-feature/holdout pipeline. Its “unique” filename and prior README wording overstated what is established. README now labels it analysis-only and says not to submit.
2. **Critical — legacy run card/verifier target a different artifact.** `evidence/current_run_card.json` names the LWST TIFF, whose historical card sets `ok_to_submit: false`; `scripts/verify_all_gates.py` checks that named file and historical JSON, not the newest structural TIFF. Thus even a successful verifier run would not validate the newest TIFF. It also returns success under `--expect-blocked` for its one expected literal lattice finding, which is a CI assertion of a known blocked state—not approval to submit.
3. **High — absent source data prevents the requested experiment.** `data/` contains small audit/manifest JSON only, not competition rasters, labels, official sample, or the cached feature stack. Consequently no new HOLDOUT-DTI estimate, confidence interval, leakage canary, candidate-vs-registry correlation, or dot overlap can be recomputed here. The user's score values are inputs/owner reports, not organizer receipts unless a receipt is present.
4. **High — conflicting and stale evidence needs a single source of truth.** `README.md`, `docs/data/current_run_card.json`, `docs/data/run_card.json`, `evidence/current_run_card.json`, and generated pages describe different submissions and historic states. The legacy `scripts/build_docs_pages.py` reads a schema requiring `submission_zip_name` and nested `registry_correlation_overlap`; the checked-in current card has neither. It is inconsistent with the current schema and should not be used. The active conservative renderer is `scripts/build_review_site.py`, but it writes pages at import time rather than behind a `main()` guard, making it unsafe to import in tests or other tools.
5. **High — gate suite has assumptions that are not candidate-generic.** `verify_all_gates.py` hardcodes 37,654 positives and loads legacy checks from evidence JSON. A different valid candidate cannot be evaluated by this verifier without edits. It should derive expected properties from a manifest and independently compute all candidate-specific checks against the official sample and complete registry; missing inputs should fail closed.
6. **Medium — test/CI reproducibility.** Local test execution is blocked by missing `pytest` and `numpy`; CI installs several geospatial libraries but not a pinned dependency set. The workflow command `--expect-blocked` currently tests for a specific historical blocked condition, not a general “safe to submit” contract. CI status was not available from the local checkout.
7. **Medium — scientific claims in artifact provenance exceed their evidence.** A deterministic sparse line pattern can be unique by construction but cannot be presumed predictive. The current audit sidecar gives no holdout evidence and no independent validation; do not call its pattern a geologically-informed predictor or infer a leaderboard estimate from dot count or morphology.
8. **Medium — discovery hypotheses are hypotheses, not results.** The 2026-10-28 review already lists candidate H-SASS3-F (multivariate geophysical mixture-component boundaries), H-SASS3-G (anisotropic earthquake point-pattern clustering), and H-SASS3-H (geodetic dilatation ridges), with H-SASS3-E recorded as negative. These ideas have not been tested in this checkout. Keep them preregistered candidates; do not describe expected improvement as a score.

## Candidate research plan (not executed)

The existing review ranks these ideas. They are viable only if their listed layers are actually available in the restored official/verified feature stack and can be hidden/recovered without leakage:

| Rank | Hypothesis | Layers and targeted signal | Why potentially off-catalogue | Main mimic / risk | Cost |
|---|---|---|---|---|---|
| 1 | H-SASS3-F | TMI high-gradient, isostatic-gravity high-gradient, geodetic shear-rate, conductivity surface; boundaries of multivariate Gaussian-mixture components | Targets coincident geophysical-domain boundaries not explicitly in the fault catalogue | Lithologic contacts, playa-margin conductivity; mixture labels can be unstable | Medium |
| 2 | H-SASS3-G | `ieq_n100a15`, `deq_n100a15`; anisotropic Ripley-K / linear clustering of seismic events | Seismic lineaments may reveal unmapped active structures | Aftershock sequences and induced seismicity; event catalog selection bias | Medium-high |
| 3 | H-SASS3-H | `geod_dilaterate`; Otsu-thresholded coherent dilatation ridges | A broad deformation signal may expose uncharted structures | Subsidence, thermal expansion, groundwater extraction; weakly fault-specific | Low-medium |

H-SASS3-E, basement-surface minimum-curvature ridges, is reported as **negative** in the historical review; do not rerun or promote it without a reasoned change to the preregistered method. No hypothesis here has a valid projected score. First restore the official data, verify provenance, test each feature alone for leakage, and run the exact blocked holdout with visible-only catalogue features. Stop at the user's three-experiment/two-hour budget.

## Next actions

1. Obtain official competition files (`sample_submission.tif`, labels/training rasters and feature stack) through authorized competition access; verify hashes and provenance. Keep raw inputs out of Git.
2. Make one canonical candidate manifest/run card. Have the writer and validator consume it; fail closed if any expected reference/registry input is missing.
3. Replace the two page builders with one tested renderer. Add a test asserting pages never display “OK TO SUBMIT” unless the exact linked TIFF hash is checked and every required gate passes.
4. Re-run unit tests and format/holdout/leakage/registry gates against the exact downloadable artifact; include evidence files and evaluator version, withheld-positive count, and 95% CI.
5. Only then decide whether an eligible file exists. Promotion and submission-slot selection remain separate; disclose generative-AI use as required by competition rules.

## Trusted references already recorded in the repository

- Competition overview/rules: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Problem description: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Competition data (login may be required): https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- Official reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- USGS GeoDAWN data: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- Existing detailed audit and caveats: [independent review](independent-review-20261028.md), [irregularity ledger](../../evidence/irregularities_ledger.json), [new artifact sidecar](../downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-audit.json).

## Run card (this review)

```json
{
  "hypothesis": "Repository audit only; no candidate experiment",
  "mechanism": "Static inspection of repository files, metadata and scripts",
  "named_non_fault_mimic": "Not applicable; no geological predictor evaluated",
  "holdout_dti": "Not run; no labels/cached stack present in checkout",
  "correlation_overlap_vs_registry": "Not run for newest raster; complete registry unavailable",
  "raster_sha256": "Not independently recomputed in this environment",
  "validator_output": "Not run; numpy/rasterio and official sample raster unavailable",
  "submission_name": "gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif",
  "submission_note": "Analysis-only; not approved for competition submission",
  "verdict": "negative"
}
```
