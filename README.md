# GEMS Fieldnotes

**Decision: DO NOT SUBMIT. No new submission GeoTIFF was created or uploaded.**

An evidence-led research and review workspace for the DOE GEMS Prize. The [GitHub Pages dashboard](https://sassnarep3-star.github.io/GEMSDOESASS3/) presents the decision, nine-site comparison, sources, and [executive summary and submission guide](executive-summary.html). Its research snapshot is dated **27 October 2026**; the official leaderboard may change. The site does not scrape DrivenData.

## Standing project request and principles

The user's standing brief, condensed and de-duplicated from the supplied repeated prompts (the conversation is the authoritative verbatim record):

> Be a creative scientific assistant for a blind geothermal/fault-mapping competition. Research whether existing geoscience and engineering methods can be combined to find genuinely unmapped geothermal faults and improve performance. Review the highest reported submissions from GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36, explain the reported GEMSDOE32 0.2778 result, and create executive summaries with official references. Make the website readable on desktop and mobile, with a clear file download, submission verdict, instructions, unique submission name and short note when a candidate actually exists. Distinguish user reports, holdouts, estimates and verified organizer receipts. Keep working autonomously, avoid hallucinations, document irregularities and access needs, review three times, and open and merge a pull request when permitted.
>
> In parallel use the assigned single-method lane, the shared cached feature stack, `evaluate_holdout.py` and `submission_writer.py`. Hide and recover whole fault segments with a buffer, derive catalogue features from visible faults only, mask visible faults pixel-exactly and use the official pooled DTI with α=0.2, β=0.8 and a 300 m triangular kernel. Test each feature alone for leakage; AUC over 0.90 is a stop until disproven. Compare surface rank and three-pixel overlap against the registry before dot placement and final dots after placement: a correlation above 0.90 or overlap above 70% is a duplicate and a mandatory stop. Report the exact metric evidence class, evaluator, withheld-positive count, 95% CI and a JSON run card. Stop after three experiments or two hours. Never spend a competition slot on an unproven hypothesis; promotion is a separate selector with the weekly cap. A negative result is a deliverable.

The prompt references a single-method paragraph but supplies none, so H1 was explicitly chosen as a **provisional**, not coordinator-assigned, lane before implementation; the distinction is documented in the [pre-registration](docs/research/preregistration-2026-10-27.md). Concurrent preliminary reviewers interpreted the missing assignment more strictly and did not experiment. For future parallel runs, obtain an explicit lane assignment in the shared registry before starting. The user's historical values are archived as *claims*, not treated as receipts; see the [history list](docs/user-reported-history.md). User priorities and safety gates take precedence over a desire to display a TIFF.

### Research and evidence principles

- **Maximize P(Win):** choose evidence-backed experiments over slot-consuming guesses. **Own the Outcome:** preserve failures and fix or report shared tooling defects rather than keeping a private fork.
- Do not invent a leaderboard score, a prior score, a confidence interval, source provenance, a receipt, uniqueness, an allowed quota, or a TIFF. Predictions of geological plausibility are not performance estimates.
- A historical file is never “unique” merely because it has a new name or different metadata. A single disqualifying registered peer is enough to stop; a pass needs the complete accessible registry.
- Label scores **HOLDOUT-DTI** with evaluator, withheld positives and 95% CI, or **ORGANIZER-CONFIRMED** only when a receipt links the score to the exact bytes. A timestamped public leaderboard observation is neither a receipt for our TIFF nor a private score.
- Validate saved file bytes automatically: a single float32 band, correct sample grid/CRS/transform, finite inside the footprint and values in `[0,1]`, plus a SHA-256. A validator is not a scientific or uniqueness gate.
- Do not bypass the strict stop rule, quietly prune predictions to evade it, or use a live competition slot without a separate selector and current quota. Do not keep a private fork of a shared tool; report shared defects upstream.
- Cite primary and official sources, respect data licensing and site terms, and label owner mirrors and dated snapshots honestly. Useful negative experiments should remain reproducible.

## Current result

| Item | Evidence |
| --- | --- |
| New file / submission | **None.** The only new run stopped before dot placement. |
| H1 pre-placement surface | **0.048064 HOLDOUT-DTI**, evaluator `gems57-pooled-hide-v2`, 60,988 withheld positives, 95% spatial-cluster CI `[0.044295, 0.051633]`. Not a dot-field or organizer score. |
| Same-fold terrain control | **0.059785 HOLDOUT-DTI**, same evaluator and positives, CI `[0.054213, 0.065646]`; H1 minus control `−0.011721`, paired CI `[−0.014326, −0.009464]`. |
| Uniqueness stop | 100% of H1's positive surface support was within 3 pixels of a registered lattice (limit: more than 70%). Full-footprint Spearman was `−0.000259`. Only one disqualifying peer was required; this was not a complete registry scan. |
| Historical 0.2778 | **User-reported, unverified attribution.** The linked H33 audit calls the file unscored. We cannot connect a receipt to its SHA. H33 removes 2,545 catalogue-near pixels from GEMSDOE31 H27, adding none; a plausible mechanism is not proof of causation. |
| Public leaderboard | **0.4544 official public leaderboard observation**, 2026-10-27 UTC, not our receipt or a private/final score. [Check the source](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). |

The [run card](evidence/h1-run-card.json) includes the hypothesis, mechanism, non-fault mimic, holdout components and CI, registry witness, raw/derived canaries, explicit null raster/validator/name fields, and `negative` verdict. The separate [input audit](evidence/h1-input-audit.json) documents post-stop raw-band canaries and lattice coverage. An [independent distance-transform check](evidence/h1-overlap-verification.json) reconstructed the same surface hash and confirmed the overlap, without making a new candidate. No estimated organizer score is available.

## Project map

- [Dashboard](index.html) and [executive summary / submission guide](executive-summary.html).
- [Research results, sources, irregularities and remaining access](docs/research/results-and-irregularities.md).
- [Four ranked hypotheses and pre-registration](docs/research/preregistration-2026-10-27.md).
- [Nine-site audit JSON](docs/data/focus-nine-audit.json) and [pinned input manifest](registry/focus-nine.json): only those nine historical files, not the full registry.
- [H1 implementation](src/lane_h1.py), [bounded run](scripts/run_h1.py), [post-stop input audit](scripts/audit_h1_inputs.py), [historical raster audit](scripts/audit_focus.py), and [pinned template/data bootstrap](scripts/bootstrap_template.py).
- [Automated tests](tests/), [three-pass review log](docs/research/review-log.md), and [CI workflow](.github/workflows/ci.yml).
- Preserved preliminary reviews: [initial executive summary](docs/EXECUTIVE_SUMMARY.md), [dated review](docs/review-2026-10-27.md), [previous landing page](docs/index.html), [previous submission guide](docs/submission-guide.html), and [review-only negative card](evidence/negative_run_card.json). These describe an earlier state before H1 and the raster audit; they are not the current run card. The prior [README at the merged main commit](https://github.com/sassnarep3-star/GEMSDOESASS3/blob/dc7e945/README.md) remains available in Git history.

## Reproducing the checks

Python 3.11, `gh` authenticated for the public GitHub API, sufficient disk/memory and network access are required. Raw imagery, generated caches, TIFFs, credentials and environments are intentionally not committed. The bootstrap fetches unmodified shared modules from a pinned public revision and verifies file SHA-256; the input data are **owner-published mirrors**, not authenticated organizer downloads. Do not use the mirrored sample's pixel values as independent truth: its nonzero mask exactly equals the mirrored fault catalogue despite the official description of an absence sample.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/bootstrap_template.py --template-only   # small source files, for tests
.venv/bin/pytest -q
node tests/site_dom_test.cjs
python3 -m http.server 8000 --bind 0.0.0.0                   # local static site
```

To rebuild the much larger, 19-band data cache and rerun the historical or raw-input audits:

```sh
.venv/bin/python scripts/bootstrap_template.py --cache-bands
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/audit_focus.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/audit_h1_inputs.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/verify_h1_overlap.py
```

Published evidence is never overwritten by these scripts. Reproductions default to timestamped JSON under `.cache/reproductions/`; `--output` accepts a new explicit path and refuses to overwrite an existing file.

`run_h1.py` records the fixed research experiment, but the published run is already negative; it will not place dots or produce a TIFF. Do not keep rerunning or tuning that stopped lane to seek an exemption. It checks one disqualifying witness, not the full registry. The shared writer is exercised on a synthetic temporary raster in tests and is never used to publish a candidate from this negative run.

## Remaining access and decisions

An authenticated organizer sample and submission receipts, complete registry and same-evaluator prior best are not available here; use of new data requires verified rights, coverage and alignment. The shared writer requires finite zero-filled exterior pixels, while the official description says data outside bounds are null/NaN. If the mirrored irregular footprint is the relevant boundary, these policies conflict; a local writer pass is not proof of compliance. Resolve the boundary against an authenticated sample and organizer guidance, and correct the shared template before a release rather than silently treating zero-fill as equivalent. A separate authorized selector needs a current quota before any upload. Some sister repositories do not grant this account push access; their sites have not been modified. The upstream metric documentation has a mathematically incorrect single-dot inequality (the metric computation used here is correct); our GitHub integration could neither push a fix nor file an issue upstream. Details, examples, and the public official links are in the [research review](docs/research/results-and-irregularities.md).
