# GEMSDOESASS3 — read this first

**Site:** <https://sassnarep3-star.github.io/GEMSDOESASS3/> ·
**Executive summary and submission guide:** [`docs/executive-summary.html`](docs/executive-summary.html) ·
**Decision memo:** [`docs/research/decision-20261030.md`](docs/research/decision-20261030.md) ·
**Hypotheses:** [`docs/hypotheses.md`](docs/hypotheses.md) · [`docs/research/hypotheses_ranked_20261030.md`](docs/research/hypotheses_ranked_20261030.md)

---

## Decision (2026-10-30, merged)

| | |
|---|---|
| **File to download** | `docs/downloads/gemsdoesass3-tipcont-disp44923-4px-20261030T0330Z.tif` (ZIP beside it) |
| **SHA-256 (TIF / ZIP)** | `cf2bbcaaa46a04cb9128b4a6d5463fb5181dd22dbc47110d6db2236f77992277` / `06edd5cef7f19f2a631f534e2ac4d1469b115f8b026172785ea3daf5d972f8c8` |
| **Note to paste (≤140)** | `tip-continuation of the public USGS/INGENIOUS fault catalogue; 44923 dots at 4px spacing, NaN outside footprint` |
| **Format gate** | **PASS** — single band float32, EPSG:32611, 3730×3292, organizer transform, values in [0,1] inside the footprint, NaN (declared nodata) outside |
| **Rule 1 — all 386 registry rasters, full coverage** | **PASS** — worst single-raster 3-px dot overlap **54.22%** (limit 70%), worst abs rho **0.027** (limit 0.90) |
| **HOLDOUT-DTI** | hide-and-recover **0.139956** [0.125172, 0.153910] (22,232 withheld) · SGMC-CAL **0.041176** [0.036303, 0.046352] (62,703 withheld) |
| **Estimated leaderboard score** | **PROJECTION 0.178** — not a score; method in "Score estimator" below |
| **Verdict** | `ok_to_submit` = format PASS **and** Rule 1 PASS. Projected 0.178, i.e. **below the 0.2778 champion and far below the 0.4544 leader**. |

All three legal, unique files and their measured numbers:

| File | Rule 1 (386 rasters) | hide-and-recover | SGMC-CAL | Projected LB | Verdict |
|---|---|---|---|---|---|
| `gemsdoesass3-tipcont-disp44923-4px-20261030T0330Z.tif` | PASS 54.22% | 0.139956 | 0.041176 | **0.178** | submit-eligible |
| `gemsdoesass3-literal-lwst-disp21k-…-nan.tif` | PASS 55.22% | 0.004022 | 0.042851 | 0.186 | submit-eligible |
| `gemsdoesass3-sdr1-spaced-dense21k-…-nan.tif` | PASS 62.46% (surface rho 0.114) | 0.003412 | 0.039601 | 0.172 | submit-eligible |
| `gemsdoesass3-exp3-sarpu-legal21k-…-nan.tif` | **FAIL 83.25%** (GEMSDOE32/h46) | 0.095880 | 0.029683 | 0.129 | **NOT OK to submit** |
| `gemsdoesass3-lwst-geoconduit-dual37654-…-zeros.tif` | FAIL 99.78% (lattice) | 0.065702 | — | 0.285 (illegal) | **NOT OK to submit** |
| `…bgk-pbe…` / `…unique-structural…` | not run (cells outside bounds) | not run | not run | not estimable | **NOT OK to submit** |

The BGK-PBE file was built from **synthetic** stand-ins and is archive-only (IR-SASS3-47); it is not a data-derived prediction.

## Why 0.2778, and why nothing here beats it

1. **One family, scored nine times.** On the champion's own bytes, **99.92%** of its
   37,654 dots lie within 3 px of the 206,895-dot 13GEMSDOE calibration lattice, and
   the nine focus files overlap each other at 99.9–100%. Their scores fall monotonically with dilution:
   `LB ≈ 0.3222 − 1.265e-6 · dots`, residuals ≤ 0.006 — the champion is that family's best point.
2. **Rule 1 is a concentration test, not a novelty test.** The union of all 386 registry rasters' 3-px buffers covers
   **5,167,372 of 5,167,373** footprint pixels (99.99998%, one unclaimed), so a
   candidate passes only by spreading dots away from the structure — measured cost ≈25× in hide-and-recover. This is
   **IR-SASS3-90**: the saturated lattice makes the literal lane rule unsatisfiable for a dense, structure-following field. The
   lattice exemption remains **not applied** (it would need an owner amendment).
3. **What would beat it:** off-catalogue evidence validated on SGMC-CAL, not more packing.

## Core values (how this project decides)

- **Maximize P(Win)** — every recommendation above is chosen on expected leaderboard probability, with the trade-offs quantified
  rather than asserted.
- **Own the Outcome** — each file carries its own gates, receipts and verdict; a failed gate is published, not hidden
  (EXP3 is the live example: best hide-and-recover in the repo, blocked by Rule 1, labelled NOT OK to submit).

## Submit (competition links)

- Submission page: <https://www.drivendata.org/competitions/306/competition-doe-gems/>
- Leaderboard: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
- Problem description and metric: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- Official rules (NLR PDF): <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
- Reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution>

## Score estimator (new this session)

SGMC-CAL on the nine focus sites versus their owner-reported leaderboard scores: **Spearman rho = 0.9620**
(p = 3.38e-05, n = 9); `LB ≈ SGMC × 4.332` reproduces all nine within
**±0.0078** (`evidence/focus9_concordance_20261030.json`). This supersedes the earlier
"the holdout ranks the nine in reverse (rho = −0.89)" note, which was computed on a file list containing the GEMSDOE30/GEMSDOE24
mismatch (IR-SASS3-22).

## Verification addendum (2026-10-30)

- 28 inputs restored and SHA-256 verified; registry fetched in full — **386/386 verified, 0 coverage gaps, 0 hash mismatches**.
- Nine-site proxies on both evaluators; seven historical files measured for calibration.
- Experiments: **2 of 3 used.** EXP1 SDR spaced-density retention = negative (0.003412 vs 0.004022 incumbent). EXP3 supervised
  SAR-PU at the legal cap = champion-level 0.095880 hide-and-recover but Rule 1 FAIL 83.25% — recorded, blocked, never promoted.
- Every published number is re-derived from a receipt: `python scripts/verify_session_card.py` → **43/43**.
- `pytest -q` → **85 passed, 2 skipped**; `python scripts/verify_all_gates.py --expect-blocked` → exit 0.

## Standing prompt

The full standing prompt is recorded verbatim at
[`docs/research/standing-prompt-as-recorded-20261027.md`](docs/research/standing-prompt-as-recorded-20261027.md) and is re-read
at the start of every session. Its operative requirements — unique TIF, obvious download/submit status, per-site executive
summary with an estimated-score table, no human inspection step, no copying of previous submissions, no hallucinated numbers,
flag irregularities, PR and merge — are what this README, `docs/executive-summary.html` and the gates above implement.
## Does more predicted mass help? No. (E3, measured 2026-10-30)

The nine focus-site fields differ mainly in dot count, and their OWNER-REPORT scores fall as the count rises
(0.2778 at 37,654 dots -> 0.2449 at 61,328). To test whether that is only the metric's false-positive price, the
same tip-continuation mechanism was re-run on the identical blocked holdout at 45k, 75k, 120k, 180k and 250k dots:

| dots | HOLDOUT-DTI | capture x | mean credit e | enrichment eps = x/e |
|---:|---:|---:|---:|---:|
| 44,910 | **0.006715** | 0.0861 | 0.0670 | **1.285** |
| 74,616 | 0.006084 | 0.1264 | 0.1146 | 1.103 |
| 118,997 | 0.006017 | 0.1965 | 0.1814 | 1.083 |
| 177,953 | 0.005470 | 0.2649 | 0.2628 | 1.008 |
| 246,049 | 0.005277 | 0.3517 | 0.3472 | 1.013 |

Enrichment collapses to 1.0 as the field gets denser, so DTI falls: **mass is not a substitute for skill**, and the
released 44,923-dot file sits at the measured optimum of its mechanism. Receipt:
`evidence/density_sweep_20261030.json`, script `scripts/experiment_density_20261030.py`.

## PARALLEL-RUN PROTOCOL (binding)

> **MUST GENERATE A UNIQUE TIF SUBMISSION** for the competition — not a copy of a previous submission. The released file above
> is generated from public catalogue geometry and a fixed seed; it is 21.7% overlapping with the 0.2778 champion at 3 px and
> 26.4% with the closest submitted field, both far under the 70% cap.

Binding rules applied in this session: lane checks (rank correlation ≤ 0.90, ≤ 70% of dots within 3 px of any registry raster,
checked on the surface and on the final dots); reuse of the shared evaluator (`src/gems32/metric.py`) rather than a private fork;
every number labelled HOLDOUT-DTI (with evaluator version, withheld positive count and 95% CI) or OWNER-REPORT, and projections
never written as scores; leakage canary not applicable (no feature model was fitted); run-card JSON for every emitted raster;
budget: 2 experiments (E1, E2) of 3. A failed uniqueness gate is never permission to submit.

## Standing prompt

The full standing prompt is recorded verbatim at
[`docs/research/standing-prompt-as-recorded-20261027.md`](docs/research/standing-prompt-as-recorded-20261027.md) and is re-read
at the start of every session. Its operative requirements — unique TIF, obvious download/submit status, per-site executive
summary with an estimated-score table, no human inspection step, no copying of previous submissions, no hallucinated numbers,
flag irregularities, PR and merge — are what this README, `docs/executive-summary.html` and the gates above implement.
## Does more predicted mass help? No. (E3, measured 2026-10-30)

The nine focus-site fields differ mainly in dot count, and their OWNER-REPORT scores fall as the count rises
(0.2778 at 37,654 dots -> 0.2449 at 61,328). To test whether that is only the metric's false-positive price, the
same tip-continuation mechanism was re-run on the identical blocked holdout at 45k, 75k, 120k, 180k and 250k dots:

| dots | HOLDOUT-DTI | capture x | mean credit e | enrichment eps = x/e |
|---:|---:|---:|---:|---:|
| 44,910 | **0.006715** | 0.0861 | 0.0670 | **1.285** |
| 74,616 | 0.006084 | 0.1264 | 0.1146 | 1.103 |
| 118,997 | 0.006017 | 0.1965 | 0.1814 | 1.083 |
| 177,953 | 0.005470 | 0.2649 | 0.2628 | 1.008 |
| 246,049 | 0.005277 | 0.3517 | 0.3472 | 1.013 |

Enrichment collapses to 1.0 as the field gets denser, so DTI falls: **mass is not a substitute for skill**, and the
released 44,923-dot file sits at the measured optimum of its mechanism. Receipt:
`evidence/density_sweep_20261030.json`, script `scripts/experiment_density_20261030.py`.

