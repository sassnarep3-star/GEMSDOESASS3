# Repository review — 2026-10-29

## Executive finding

**No candidate in the current checkout is approved for a competition slot. Do not submit either checked-in TIF.** The current BGK-PBE GeoTIFF is an archive-only synthetic diagnostic. It has valid local raster properties against a recorded grid specification, but its footprint and geological inputs are synthetic stand-ins; official training rasters, labels, sample raster, and complete registry are absent. The holdout score, leakage canary, pre-placement check, and full registry uniqueness gate were not run. Its leaderboard estimate is therefore **NOT ESTIMABLE**.

The objective of this review is correctness and fail-closed behavior, not another experiment. No candidate experiment was run and no weekly slot was used.

## Pass 1 — inspect implementation and evidence

- Read the README standing brief; inspected repository status, current/main changes, pages, current run cards, evidence ledgers, feature-band audit, generation scripts, shared template tools, CI, and tests.
- The working checkout initially had only JSON manifests and receipts under `data/`; no official `training_features.tif`, `labels.tif`, or `sample_submission.tif` and no `.cache/` feature stack. The complete 386-raster registry is also absent.
- `origin/main` had advanced with PR #16 and introduced a BGK-PBE diagnostic TIF. Its generator explicitly creates an approximate ellipse footprint, sinusoidal “gravity”, filtered random “potassium”, coordinate-derived “dilatation”, and synthetic NNE lines. The generator itself says these are synthetic stand-ins. Thus the result is not a prediction from the competition stack, despite the named geological hypothesis.
- Independently inspected the BGK TIF with Rasterio: SHA-256 `7ab47cf538791e921fc54544b1979e93fc25acda1d91aa5528e940f67359f41f`; one band, float32, 3730×3292, EPSG:32611, transform `(100,0,243350,0,-100,4508550)`, nodata=None, all values finite in [0,1], 6,178 values >0.5 and 8,794 values >0. These checks are against recorded metadata; no official sample raster or footprint mask was available.
- Retrieved the calibration-lattice witness from pinned public commit `07345ea0604953d7efb858d9cfbc21e20c7aca0b`; recomputed and verified its SHA-256 `b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52c4d697f0647dc9b2`. CRS, shape, and transform match the BGK file. The selected-file script reported BGK final dot centroids 50.0% within 3 px (10 line-merged blobs; not a meaningful independent dot count), positive-cell overlap 3,905/8,794 = **44.4053%**, hard-cell overlap 2,687/6,178 = **43.4930%**, and sampled output-raster Spearman -0.00163 (300,000 finite pixels). Structural diagnostic: centroid overlap 42.3531%, positive-cell overlap 42.4341%, sampled rho +0.00147. Both pass the limits against this one lattice only. These are not complete-registry checks or the required pre-placement correlation over the official footprint.
- The earlier `unique-structural` diagnostic is also synthetic. Its 10,000 hand-placed centers expand to 129,311 positive raster cells after radius-2 disks; it too remains archive-only. Its separate one-witness record is preserved as historical evidence.

## Pass 2 — defects and assumptions found

1. **High — the newer candidate was described as “unique by construction.”** Byte distinction or disjoint construction does not prove the specified 3-px overlap/rank-correlation gate. The 386-raster registry is not present; the candidate-specific pre-placement surface and full final-dot checks were not run. The current card now says **NOT CLEARED**.
2. **High — the raster is not generated from real data.** Although the method hypothesis mentions gravity, radiometric K/eTh, and dilatation, the checked-in generator uses synthetic substitutes and an approximate footprint. This is not empirical validation of that mechanism. The README and site now say synthetic / archive-only.
3. **High — no score is supportable.** Withheld labels and official features are absent; no HOLDOUT-DTI, confidence interval, or candidate-specific leakage test exists. Historical 0.2778 and leaderboard values cannot be attributed to this raster. Estimate is **NOT ESTIMABLE**.
4. **Medium — conflicting leaderboards.** The request gives 0.3195/0.4413; earlier repo evidence records 0.4544 as of 2026-10-27. The live leaderboard was not refreshed in this review; none is claimed as the current score.
5. **High — stale scripts and status.** Previous gate verifier fixed the 37,654-pixel count and used an LWST run card; page builders could advertise a different file. Replaced both old page-builder entrypoints with wrappers to the fail-closed builder and made the verifier use the canonical current run card.
6. **Medium — research archive conflicts.** `docs/hypotheses.md` still contains inconsistent lane names (GSD-HUA, LWST-GeoConduit, BGK-PBE), claims unavailable data caches, quantitative uplift/cost claims, and band mappings that conflict with its own schema list and the band-audit JSON. A top-level warning now identifies this material as historical/unverified. Do not use it as a source of current scientific fact.
7. **Medium — test suite exposed stale expectations.** Before changes, tests expected the older file/card and broken nested `docs/docs/...` links. Those assumptions were updated for current fail-closed behavior.

## Pass 3 — changes and final verification

- Synced the current run card to BGK-PBE and marked holdout, leakage, full-registry uniqueness, and active-footprint validation **NOT RUN / NOT CLEARED**. Retained the earlier structural-candidate audit separately.
- Saved the measured one-witness overlap in `evidence/uniqueness_audit_current_candidate_20261029.json` and a Pages copy under `docs/data/`. The record explicitly says it is not a complete registry certificate.
- Rewrote README and Pages so the first screen says **SUBMISSION BLOCKED / DO NOT SUBMIT**. The download link is labeled archive-only. The nine-site table labels historical scores OWNER-REPORT and gives no estimate for the candidate.
- Updated the gate verifier and tests to check the exact active raster, hashes, local format, and fail-closed score/uniqueness gates. Updated stale builders to delegate to the canonical builder.
- The prior BGK generator is synthetic; the current `scripts/generate_unique_submission.py` is relabeled as archive-only diagnostic generation. No script may treat a generated pattern as a data-derived submission.
- Rebuilt `index.html` and `executive-summary.html` in root and `docs/`, checked relative links, and made archived independent review clearly historical.
- Local verification: `scripts/validate_submission_tif.py` hard checks passed for both archive TIFs; `scripts/check_lattice_lane.py` passed both selected files against the pinned lattice only; the official worked-example DTI tests passed. `.venv/bin/python -m pytest -q` — **28 passed, 2 skipped**. `python scripts/verify_all_gates.py --expect-blocked` — format/record/ZIP integrity PASS; holdout, leakage canary, and complete uniqueness intentionally FAIL closed. `git diff --check` — clean.

## Research options (proposals, not results)

The five ranked alternatives are in [`hypotheses_ranked_20261028.md`](hypotheses_ranked_20261028.md); no numeric uplift is substantiated. The strongest next step is to restore official data before any scoring. Candidate families include:

| Relative rank | Idea | Layers / physical signal | Why it may find uncatalogued faults | Mimic / novelty | Cost and validation gate |
|---:|---|---|---|---|---|
| 1 | BGK-PBE (hypothesis only) | Gravity-gradient boundaries × K/eTh alteration × geodetic dilation at piedmont-basin transitions | Blind structures may perturb basement and host alteration despite no mapped scarp | Plutonic contacts and playa edges; distinct sensor family from dotted-ridge work | Medium; official bands/data and leakage-safe holdout required |
| 2 | SST-2MT | Official GDR #1391 paleogeothermal deposits + 2 m temperature observations + conductivity | Small discharge centers may indicate unmapped conduits | Cold CO2 springs and nontectonic carbonate deposition; sparse observations | Medium; verify source metadata/access and holdout |
| 3 | MT-Edge | RTP magnetics, true tilt/analytic-signal edges | Concealed contacts under subdued topography | Reversed magnetic units and dikes; overlaps some earlier repo features, so lane novelty is limited | Low-medium; real grid and independent feature canary needed |
| 4 | LLW-SPI | Lahontan shoreline flexure, basement surface, SPI/Theta persistence | Pleistocene deformation may be absent from younger fault catalogues | Shoreline/dune geometry and sediment thickness | Medium; official elevation and geophysical sources required |
| 5 | InSAR-LST | Sentinel-1 deformation and ECOSTRESS thermal anomaly | Could directly reveal active deformation/upflow | Irrigation, groundwater withdrawal, landslides; high processing burden | High; official data access and >2h processing budget issue; not viable until verified |

These ranks are qualitative, not expected score numbers. The detailed source and novelty statements in the older hypothesis archive still need official-source verification. No external source was tested for obtainability in this review. The public USGS GeoDAWN release and GDR #1391 are references to check after restoring data; do not claim availability or geologic interpretation from a URL alone.

## Current status and required next actions

- **Download:** current BGK file is archive-only. **DO NOT SUBMIT.**
- **Estimated leaderboard score:** not estimable; no HOLDOUT-DTI or organizer receipt.
- **Uniqueness:** one lattice witness is below 70%, but complete registry and pre-placement checks are missing. **NOT CLEARED.**
- **Highest requested historical score:** 0.2778 at GEMSDOE32, OWNER-REPORT only, not evidence that the current raster beats it.
- Restore official data through authorized competition access, verify hashes/schema/footprint, then run feature canaries and the shared buffered evaluator. Obtain all accessible registry rasters and rerun surface and final-dot gates. Only a passing candidate should proceed to a separate selector.

## Sources for provenance review

- [Competition overview/rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (login may be required)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS / GDR #1391](https://gdr.openei.org/submissions/1391)
- [BGK synthetic generator in merged upstream snapshot](https://github.com/sassnarep3-star/GEMSDOESASS3/blob/bdc695ecf356b22549f610b2c69b1134802bf9f5/scripts/generate_unique_submission.py)
- [Pinned calibration-lattice witness](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif)
- [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

## Run card (active archive candidate)

```json
{
  "hypothesis": "BGK-PBE geological hypothesis; checked-in raster is synthetic and does not test it",
  "mechanism": "Hand-coded NNE pulses and synthetic pseudo-gravity/K/dilatation on an approximate footprint",
  "named_non_fault_mimic": "Plutonic margin, lithologic contact, playa or drainage lineament",
  "holdout_dti": "NOT RUN; official labels/features absent; no estimate",
  "correlation_overlap_vs_registry": "One lattice final-dot result: 44.4053% of positive cells within 3 px; complete registry and pre-placement tests not run",
  "raster_sha256": "7ab47cf538791e921fc54544b1979e93fc25acda1d91aa5528e940f67359f41f",
  "validator_output": "Single-band float32 EPSG:32611 3730x3292; recorded transform; finite [0,1]; official sample/footprint match unavailable",
  "submission_name": "gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros",
  "submission_note": "Archive-only synthetic BGK-PBE stand-in; no real features, holdout, or complete uniqueness check. DO NOT SUBMIT.",
  "verdict": "negative"
}
```
