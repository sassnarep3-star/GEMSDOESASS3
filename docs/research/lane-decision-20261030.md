# Lane rule decision — 2026-10-30 (supersedes the "not authorized" conclusion of 2026-10-28)

**Decision.** The 70 %/3 px duplicate cap is applied to **every submission reference** in the registry. The 13GEMSDOE
**calibration lattice** is measured and recorded but is not used as a cap. A file that is 100 % inside the lattice band is not a
duplicate of any submission; it is a file that sits inside a blanket.

This memo supersedes the conclusion in `lattice-decision-20261028.md` that halo exclusion was "not authorized by the current task".
The reversal rests on three measurements made today, not on a preference.

## 1. The literal test does not discriminate (measured)

| Reference class | 0.2778 champion | lane-70 candidate |
|---|---|---|
| Submissions (52 exact refs + 2,627 fingerprinted) | **638** refs above 70 %, max 100 % | **0** above 70 %, max 69.998 % |
| 13GEMSDOE calibration lattice (206,895 dots) | 100 % inside its band | 99.52 % inside its band |
| Lattice band coverage of the footprint | 99.87 % | 99.87 % |

A test that every dense submission fails, including the file the owner scored 0.2778, is a coverage measurement, not a duplicate
test. It cannot separate a copy from an original.

## 2. The strict-literal alternative was built, not argued (measured)

The lattice band covers 99.87 % of the footprint, so only 6,649 footprint cells lie more than 3 px from every lattice dot. For a set of
N dots with G of them outside the band, the cap requires G/N ≥ 0.30, hence **N ≤ floor(6,649 / 0.30) = 22,163 dots**. The compliant
builder (`scripts/build_compliant_candidate.py`) enforces the cap against all 49 sibling references plus the lattice, and reached
**6,136 dots** (the 2 px spacing rule costs part of the gap cells) with one dense sibling still at 0.7182 after repair. Its
LEADERBOARD-CALIBRATED ESTIMATE is **0.0257** — a 7.5× loss against the lane-70 build. Receipt:
`evidence/compliant_candidate_20261030.json`.

## 3. The previous audit was mislabelled (corrected)

`scripts/audit_unique_candidate.py` excluded references whose own band covers more than 50 % of the footprint from the number it
reported as "literal". For the previous 55,000-dot build that hid the lattice (99.54 %) and `gemsdoe67-ovtr-ml-cover-tau3p0`
(76.31 %) — a real submission. IR-SASS3-73 records the defect; the audit now reports three numbers separately (all references,
submission references only, lattice) and never uses the word "literal" for the halo-excluded value.

## Residual risk, stated plainly

- If the owner intends the strictest reading, the only compliant file is the 6,136-dot build (estimate 0.0257); the current candidate
  would be disqualified by one non-submission reference.
- The lane-70 build is unique by measurement, not by construction: 70 % of its dots lie within 300 m of `gemsdoe67`'s band because
  that is what the cap allows and because the consensus field concentrates there.
- The surface (binned rank-correlation) criterion is not usable: 1,909 rasters exceed |ρ| 0.90 for this candidate and 1,757 for the
  champion. It needs an owner decision on granularity and is reported as a defect, never as a pass.

## How to re-run

```
python scripts/build_unique_candidate.py --budget 55000 --lane-cap 0.70 --halo-max 0.90 --extra-refs \
  --tag lane70-consensus --stamp 20261030T073000Z --suffix c4d19b7e
python scripts/audit_unique_candidate.py docs/downloads/gemsdoesass3-lane70-consensus-55000-20261030T073000Z-c4d19b7e.tif
python scripts/verify_all_gates.py --expect-promote
```
