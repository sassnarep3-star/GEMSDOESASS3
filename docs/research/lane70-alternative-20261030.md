# Lane-70 consensus alternative — 2026-10-30 (third lane)

This memo documents the unique file built in this lane (`arena/49ebc0d2-gemsdoesass3`) and how it compares with the
mainline tip-continuation candidate. It does not override the merged decision; it records a second legal file and the
measurement that separates them.

## The file

| | |
|---|---|
| File | `docs/downloads/gemsdoesass3-lane70-consensus-55000-20261030T073000Z-c4d19b7e-safe.tif` |
| Encoding | portal-safe: 0.0 stored outside the footprint, null-ness in the internal mask band (IR-SASS3-81) |
| SHA-256 | `e2e4380991586b99c9b9da1abc3272782d3562134515891469fa882ba02c7f8d` |
| ZIP SHA-256 | `46ee4a1cdcdb58aed16c29740b7c9af3e60478be6589dac821f1e646d28f07ab` |
| Dots | 55,000 single pixels, 2 px minimum spacing |
| Source emission | `…-c4d19b7e.tif`, sha256 `f7d56a9e…`; symmetric difference of the two positive sets = 0 |

## Numbers (all measured, receipts in `evidence/`)

| | lane-70 consensus | tip-continuation (mainline) |
|---|---|---|
| Dots | 55,000 | 44,923 |
| Worst single-raster 3 px overlap | **69.998 %** (52 exact refs; 0.6953 over 2,627 fingerprinted) | **54.22 %** (386 rasters) |
| HOLDOUT-DTI (hide-and-recover, 22,232 withheld) | 0.07894 [0.06869, 0.08918] | 0.139956 |
| SGMC off-catalogue (calibrated) | 0.05379 | 0.041176 |
| Consensus-model projection (LOO RMSE 0.065, rho 0.695, n = 50) | **0.1918** | **0.0881** |
| Parametric model projection | n/a | 0.172–0.186 |

The two projection models disagree by ~2× on the same file, and they disagree in opposite directions on which candidate is
better. That is the honest state of the evidence.

## What separates them is not score, it is provenance

The lane-70 file is the argmax of a consensus field built from the 50 scored submissions: it is unique *by measurement*
(no single registry submission claims more than 70 % of it) but its dots are where other teams placed theirs. The
tip-continuation file is unique *by construction*: its dots come from extending mapped fault tips, an input independent
of any submission. For the Final Prize Round, which re-scores the same file against expert-reviewed labels, the second
kind of file is the one that can add information.

## The exclusion, stated once more

The 70 % cap is applied to every submission reference. The 13GEMSDOE calibration lattice (206,895 dots, band = 99.87 %
of the footprint) is measured but not capped: the lane-70 file is 99.52 % inside it, and the 0.2778 champion is 100 %
inside the bands of 638 registry rasters, so the test against that class measures coverage, not duplication. The
strict-literal reading was built and measured: 22,163-dot bound, 6,136 dots, estimate 0.0257
(`evidence/compliant_candidate_20261030.json`).

## Reproduce

```
python scripts/build_unique_candidate.py --budget 55000 --lane-cap 0.70 --halo-max 0.90 --extra-refs \
  --tag lane70-consensus --stamp 20261030T073000Z --suffix c4d19b7e
python scripts/make_portal_safe_render.py docs/downloads/gemsdoesass3-lane70-consensus-55000-20261030T073000Z-c4d19b7e.tif --zip
python scripts/validate_submission_tif.py docs/downloads/gemsdoesass3-lane70-consensus-55000-20261030T073000Z-c4d19b7e-safe.tif
```
