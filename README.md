# GEMSDOESASS3 — read first

## Current decision · 2026-10-31 UTC

# NO CURRENT TIFF IS APPROVED FOR SUBMISSION

**Do not upload any file from this repository as the result of this review.** No submission slot was used. No new TIFF was generated. The latest existing candidate checked here fails the prompt's uniqueness gate, and the file previously labeled as upload-approved has no organizer acceptance receipt and contains NaN outside its footprint. See the full [repo review and nine-site executive summary](docs/research/repo-review-20261031.md), [machine-readable negative run card](evidence/run_card_20261031_review.json), and [current local status feed](docs/research/FEED.md).

| Current artifact | Evidence | Decision |
|---|---|---|
| `docs/downloads/gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif` | A fresh exact-byte validation fails the portal's global `[0,1]` test: 7,111,787 outside-footprint NaNs. Score 0.3687 is a model estimate, not an organizer score. | **NOT CLEARED** |
| `docs/downloads/gemsdoesass3-lane70-consensus-55000-20261030T073000Z-c4d19b7e-safe.tif` | Existing receipt: HOLDOUT-DTI `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives, 0.078939 [0.068692, 0.089185]. Surface binned |ρ| max 0.983609; 1,909 registry rasters exceed 0.90. Literal overlap with the calibration lattice is 99.5182%. | **NEGATIVE — protocol stop** |

The lane-70 candidate's 69.5273% overlap result was produced after excluding the calibration lattice. The user protocol says **any** registry raster; the exclusion is not an approved exception. The pre-placement correlation field in that candidate's run card is null. See the receipts linked in the review.

## Same-day modelling lane · 2026-10-31 UTC — H-CELLDISTILL run, verdict negative, blockers explained

The review above ran without the feature cache and generated nothing. A second lane the same day restored the data
(`scripts/download_competition_data.sh` → 28 SHA-verified official files), executed the one hypothesis
[`docs/research/leaderboard-inversion-20261030.md`](docs/research/leaderboard-inversion-20261030.md) recorded as
**“not run — highest-value next step”** (so the lane is documented, not invented), and produced a unique, gated raster.
Its verdict is **negative for submission**, so it is published as evidence, not as an offer. The assigned lane and the
three-experiment/two-hour cap came from the operator's own message in that session, recorded verbatim in the standing brief.

| Item | Value |
|---|---|
| Download (inspection only) | `docs/downloads/gemsdoesass3-cdist-52000-20261031T1200Z-zeros.tif` (+ `.zip`) |
| Submission name / note | `gemsdoesass3-cdist-52000-20261031T1200Z-zeros` · `cell-credit distillation, 52000 dots, unique 47% overlap; screening-only, slot NOT cleared` (90 / 140 chars) |
| Format gates | **all pass**, recomputed from the saved bytes: values ∈ {0,1} in the footprint, **no NaN anywhere**, EPSG:32611, 3730×3292 @ 100 m, 52,000 dots |
| Uniqueness | worst 3 px overlap **47.0 %** over 511 registry rasters (repo cap 65 %, protocol 70 %); **lift 1.33×** over the binding raster's own 35.3 % footprint coverage; 1.07 M positive cells no published raster touches |
| Holdout floor (HOLDOUT-DTI) | **0.0461** [0.0394, 0.0533] (GEMSDOE32-HIDE-RECOVER-v3.0, 22,232 withheld positives) · **0.0804** [0.0707, 0.0894] (GEMSDOE32-SGMC-CAL-v3.0, 62,703) — below the published family, hence no slot |
| Score | **not priced.** No estimator in this repo can certify a value above 0.2778; any number here would be invented |
| Run card | [`evidence/run_card_cellcredit_20261031.json`](evidence/run_card_cellcredit_20261031.json) · method [`docs/research/cellcredit-20261031.md`](docs/research/cellcredit-20261031.md) |

**The portal-range blocker in the table above is now explained, and it is ours, not the competition's.** Page 967 allows
“null or nan” outside the bounds, but the upload form range-tests *every stored cell*, so any `…-nanoutside.tif` fails with
“Predicted values must be in range [0, 1]” — reproduced on our files, 7,111,787 violations. The **zeros** variant carries the
identical in-footprint assertion with `0.0` outside, passes the gate, and is provably accepted by the organizer's scorer (the
GEMSDOE32 champion at 0.2778 is itself a `-zeros` file). Every candidate now ships both encodings, **zeros is the default
download**, and `scripts/validate_submission_tif.py` reports `portal_range_test_all_cells` separately from the repo's NaN
convention so the two can never be conflated again. (`IR-31-02`.)

**The 0.3687 estimate in that same table is retired outright, not merely caveated.** `scripts/compare_estimators_20261031.py`
scores every estimator on the only fair unit — withholding *whole families* of near-duplicate rasters (132 files → 110 clusters).
Bag-mean channel model **RMSE 0.0586**, ρ **0.746**; predict-the-mean baseline 0.0818; the corpus inversion behind 0.3687 **0.1364** —
i.e. it loses to a constant. Its earlier leave-one-*file*-out 0.0533 leaked through the 20-file family. A bag model can rank files
but cannot price an emission: field-sum pricing of our own top-of-field scored 0.0806 (ρ 0.30) and an unbounded version implied a
score of **493**, caught before publication. What ships instead is a **screen**: rank candidate rasters with the validated bag
estimator *before* any slot is considered. (`IR-31-01`.)

**Why the champion wins, and what it would take to beat it.** Under α = 0.2, β = 0.8 with binary rasters the index is
`TP/(TP + 0.2 FP + 0.8 FN)` and the corpus work inverts the surrogate `TP/(0.2 D + 0.8 N)`, so a score is *recall per unit emitted
mass*; 37,654 off-catalogue dots (0.73 % of the footprint) is the best such set published, and `-zeros` is a fill convention, not
an empty submission. The live board is #1 **0.4544** / #5 **0.3642** (ORGANIZER-PUBLISHED page, 2026-10-31), so the gap to the
published family is a **localisation** gap. Five ranked next hypotheses — headed by 1 m DEM scarp steps restricted to the 1.07 M
off-corpus cells this session's field nominates, and relay-bridge scoring between catalogue tips — are in
[`docs/research/cellcredit-20261031.md`](docs/research/cellcredit-20261031.md) §5. Focus-site table:
[`evidence/focus9_verdict_table_20261031.json`](evidence/focus9_verdict_table_20261031.json).


## Read the project brief every session

Before research or implementation, read [`docs/research/standing-prompt-as-recorded-20261027.md`](docs/research/standing-prompt-as-recorded-20261027.md) and the latest [`docs/research/repo-review-20261031.md`](docs/research/repo-review-20261031.md). The standing brief requires: focus on the nine listed GEMSDOE sites; evidence labels for every score; the shared buffered holdout and feature-alone leakage canaries; the exact surface-and-final-dot uniqueness gates; no more than three experiments or two hours; and a separate selector decision before any real submission slot. The exact method/lane paragraph referenced by the protocol has not been found in the recorded prompt, so do not invent a lane.

### Standing brief (read before every project session)

Review this repository before changing it. **MUST GENERATE A UNIQUE TIFF SUBMISSION** only when it is independently built and clears every gate; never copy or resubmit a historical file as a new result. Build an auditable, practical system for the DOE GEMS fault-discovery competition; focus the comparative review on GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36. Identify the strongest historical file on each site, but never copy or resubmit one as a new result. Every numeric claim must be labelled as OWNER-REPORT, HOLDOUT-DTI (evaluator version, withheld-positive count and 95% CI), ORGANIZER-CONFIRMED (receipt), or ESTIMATE; an estimate is never a score. Keep a table showing file, evidence-classed score/estimate, uniqueness, and explicit download/submission verdict. No automated result may rely on human inspection.

Before implementing a geology idea, propose 3–5 distinct hypotheses naming the layers, target physical signature, rationale for an unmapped fault, difference from existing code, likely non-fault mimic, expected improvement rank and cost. Check official-source availability for any external data. Validate an authorized candidate with the shared spatial holdout and feature-alone leakage canaries before considering any submission. Use the project template/cache, evaluator and writer—not a private fork. Enforce the assigned lane: stop if absolute rank correlation exceeds 0.90 or more than 70% of candidate dots are within 3 px of any registry raster; check the continuous surface before placement and final dots. Stop after three experiments or two hours. A real weekly slot is a separate selector decision; do not spend one here.

Deliver a simple executive summary and downloadable TIFF only when the exact saved bytes pass automated format, range, CRS/grid, footprint, holdout, leakage and strict uniqueness gates. Make “OK to download and submit” or “DO NOT SUBMIT” unmistakable; provide a unique submission name and a note ≤140 characters. If evidence or inputs are missing, fail closed, report the blocker, and retain negative results. Answer why the GEMSDOE32 0.2778 is best only to the extent the available evidence supports—do not infer causality from a score. Use official verified sources and preserve links for review. Uphold **Maximize P(Win)** and **Own the Outcome**.

The full user-supplied project request is summarized in this section and the dated audit in [`docs/research/repo-review-20261031.md`](docs/research/repo-review-20261031.md); the earlier protocol transcript is [`docs/research/standing-prompt-as-recorded-20261027.md`](docs/research/standing-prompt-as-recorded-20261027.md).

## Core values

- **Maximize P(Win).** Protect scarce submission opportunities. Promote only on robust, same-version validation; an estimate is never a score.
- **Own the Outcome.** Correct unsafe claims, preserve negative results, and make data/validation limitations explicit.

## Nine-site executive result

The highest listed file is GEMSDOE32's `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, **OWNER-REPORT 0.2778**, not an organizer-confirmed receipt in this checkout. The requested 0.3195 is not the current public leaderboard high: the official leaderboard fetched 2026-10-31 UTC showed **0.4544** at #1 (and 0.3934 at #2). The per-site scores remain owner-reported; the official page does not supply receipts linking these names/hashes to those scores.

| Site | Highest listed historical file | Score evidence | Score estimate for a new candidate | Unique among these nine? |
|---|---|---|---|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5…nan.tif` | OWNER-REPORT 0.2477 | Not defensible | No — 100.00% max 3-px overlap; already reported submitted |
| GEMSDOE25 | `dotted-h19-5-d2-8…zeros.tif` | OWNER-REPORT 0.2600 | Not defensible | No — pixel-identical positive set to GEMSDOE30 |
| GEMSDOE27 | `topo-gap-closure…allfinite.tif` | OWNER-REPORT 0.2449 | Not defensible | No — 98.02% max 3-px overlap; already reported submitted |
| GEMSDOE28 | `h36-1-rung30-blind-r1…allfinite.tif` | OWNER-REPORT 0.2710 | Not defensible | No — 100.00% max 3-px overlap; already reported submitted |
| GEMSDOE30 | `d28-poisson300m-offcat…tif` | OWNER-REPORT 0.2600 | Not defensible | No — pixel-identical positive set to GEMSDOE25 |
| GEMSDOE31 | `h27-4-solo-d28…allfinite.tif` | OWNER-REPORT 0.2708 | Not defensible | No — 100.00% max 3-px overlap; already reported submitted |
| GEMSDOE32 | `h33-h33-2-b2…zeros.tif` | OWNER-REPORT 0.2778 (highest) | Not defensible | No — 100.00% max 3-px overlap; already reported submitted |
| GEMSDOE33 | `h33d-analog-tip-stepover…tif` | OWNER-REPORT 0.2632 | Not defensible | No — 99.71% max 3-px overlap; already reported submitted |
| GEMSDOE36 | `anderson-geothermal-pinn…zeros.tif` | OWNER-REPORT 0.2750 | Not defensible | No — 97.58% max 3-px overlap; contains all GEMSDOE32 dots plus 1,200 |

Files are linked with their hash, exact holdout labels, pair identity and source in the [detailed nine-site table](docs/research/repo-review-20261031.md#executive-summary-the-nine-focus-sites). Historical TIFs are for audit/education only; do not submit them again.

## Why GEMSDOE32 scored highest — and what we can infer

Only the ordering/score claim is known from the owner's list. The exact reason for 0.2778 cannot be determined from the score alone. The historical submissions are highly overlapping variants, and GEMSDOE36 contains every GEMSDOE32 positive dot while its owner-reported score is slightly lower (0.2750); this rules out a simple “more dots means higher score” explanation. The official task targets expert-identified faults absent from the public USGS fault database. Catalogue hide-and-recover therefore tests a different target and cannot explain the contest score. A credible score estimate requires a validated transfer estimator, and the existing 0.369 lbinv number is not reliable enough to recommend.

## Hypothesis slate (not yet tested in this review)

1. **1 m DEM paired-scarp profile asymmetry** — likely highest potential, high implementation cost; needs 1 m DEM link file and data tile coverage confirmation.
2. **Scale-dependent gravity–magnetic edge phase lag** — moderate potential, medium/high cost; uses contest GeoDAWN features and differs from scalar gradient/edge maps.
3. **Signed geodetic dilatation zero-crossing networks** — low/moderate potential, low/medium cost; tests signed boundaries rather than existing dilation magnitude features.
4. **Gravity edge plus basement-depth change point, with magnetic-negative control** — low/moderate potential, medium cost; overlaps existing gravity hypotheses, so least novel.

These are qualitative research priorities, not score projections. Layer details, named non-fault mimics, the official sources and blockers are in the [review](docs/research/repo-review-20261031.md#candidate-hypothesis-slate--proposals-only-not-tested). No experiment was started because the assigned method lane, official raster/cache inputs, and spatial validation materials are unavailable; no slot was used.

## What blocks a valid downloadable TIF

- `data/` holds JSON manifests only; `.cache/gems_data/` and the competition feature/label rasters are absent in this checkout. The old restore receipt documents another environment/state, not the present one.
- A local `.venv` was created for this review, but it is ignored/untracked; a fresh checkout must install dependencies before testing. The competition feature/label cache is still absent, so cache-dependent holdout and full-registry checks cannot be reproduced here.
- Fresh exact-byte validation confirms the lbinv artifact fails the portal-wide elementwise `[0,1]` test on 7,111,787 stored outside-footprint NaNs. A different finite/masked encoding has not been tested by the actual portal.
- The protocol's referenced method paragraph, official competition rasters/cache, and a complete live registry are not available as reproducible inputs here.

To reproduce the available tests in a clean checkout: `python -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m pytest -q`. Cache-dependent tests remain skipped until authorized data is restored.

## Submission procedure — only after a later explicit GO decision

1. Read the current run card and confirm `verdict: promote`, all required validation gates pass on the exact TIF bytes, and no completeness flags are open.
2. Download the precise approved `.tif`; verify its SHA-256. Do not download/submit an archive-only or negative artifact.
3. Open the [competition submission page](https://www.drivendata.org/competitions/306/competition-doe-gems/), create a new submission, select the TIFF, enter the unique name and note (≤140 characters) printed in the approved run card, and disclose AI use as required by the official rules.
4. Check the portal's own validation and save the submission receipt. The receipt is the only evidence that the organizer accepted the file and links a score to it.

There is **no download button for a cleared submission** on the Pages site at present. The site's [executive summary](docs/executive-summary.html) and [review archive](docs/research/repo-review-20261031.md) make this explicit.

## Official sources

- [Competition problem, metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Live public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Competition data (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official rules (NLR PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN data release, DOI 10.5066/P93LGLVQ](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project and Great Basin data references](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611 — WGS 84 / UTM zone 11N](https://epsg.io/32611)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
