# GEMSDOESASS3 — read first

## Status (2026-10-28)

**Current decision: NOT OK to submit. OK TO DOWNLOAD: NO (BLOCKED) for every candidate.** No focus-site file is cleared. The validator is `python scripts/verify_all_gates.py`; its current output is in the section below.

- **BGK-PBE file on main (current run card):** not format-valid. It has 4,911 non-zero cells outside the competition bounds, which the competition rule forbids ("data outside the bounds is null or nan"). Its literal lattice overlap is 44.41% over all positive cells, but 99.59% inside the footprint, which fails the 70% limit. Its run card still says `ok_to_download: true`; the gate overrides that. Ledger IR-SASS3-29, IR-SASS3-30.
- **LWST archive:** blocked by the literal lattice rule. Its lattice overlap is 99.78% inside the footprint. The lattice covers 99.87% of the footprint within 3 px, so a file of 37,654 dots cannot pass the literal rule under any placement that stays inside the bounds (at most 22,163 dots can pass). See [docs/research/lattice-decision-20261028.md](docs/research/lattice-decision-20261028.md).
- **The owner decision** (Option A, B or C) is needed before any file can be downloaded or submitted. Option A, the like-for-like reading that the shared template already implements, is recommended. Draft amendment: [docs/research/protocol-amendments.md](docs/research/protocol-amendments.md), status PROPOSED.
- **Start here:** [executive summary and submission guide](docs/executive-summary.html) · [per-site table](docs/research/focus-site-candidates-20261028.md) · [decision memo](docs/research/lattice-decision-20261028.md) · [independent review (2026-10-28)](docs/research/independent-review-20261028.md) · [review-20261028](docs/research/review-20261028.md) · [candidate format audit](evidence/candidate_format_audit_20261029.json) · [lattice bound](evidence/lattice_bound_audit_20261028.json) · [per-file measurements](evidence/focus_site_candidate_audit_20261028.json).

**Leaderboard (ORGANIZER-CONFIRMED, public page fetched 2026-10-28):** rank 1 xiaofanhu 0.4544; rank 27 kpomazi 0.3195; rank 48 roison 0.2897. The 0.4413 figure in the standing prompt is superseded. Owner-reported focus-9 best: GEMSDOE32 0.2778 (OWNER-REPORT, not an organizer receipt).

**Earlier claims are withdrawn:** that the archived LWST file beats the 0.2778 champion; the 5,379 and 11,297 figures (IR-SASS3-20); and that the BGK file is OK to download (IR-SASS3-29). LWST SGMC-CAL is 0.065702 [0.058992, 0.071240] against the champion's 0.064121, and the intervals overlap.

## Current candidate on main (BGK-PBE): identifiers from the run card

- Submission name: `gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif`
- SHA-256: `7ab47cf538791e921fc54544b1979e93fc25acda1d91aa5528e940f67359f41f`
- SHA-256 (first 12): `7ab47cf53879`
- Submission note: `GEMSDOESASS3 BGK-PBE EXP1: basement gravity-gradient x K/eTh radiometric enrichment x geodetic dilatation blind-fault locator. NNE-trendi...`
- Run card: `evidence/current_run_card.json` (its `ok_to_download: true` is overridden by the gate; see IR-SASS3-29)
- File (audit copy, not a download link): `docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif`

**Measured in this checkout** (`python scripts/candidate_format_audit.py`, REGISTRY-MEASUREMENT):
- Grid: EPSG:32611, 3730 × 3292, float32, one band: pass
- NaN inside the footprint: 0; values in [0, 1] inside: True
- Outside the bounds: 7,111,787 finite cells, of which 4,911 are non-zero
- Positive cells: 8,794 total; 3,883 inside the footprint; 4,911 outside
- Literal lattice overlap, all positive cells: 44.41%; inside the footprint: 99.59% (limit 70%)
- Sampled rank correlation with the lattice: -0.0013 (limit 0.90)
- Holdout-DTI and registry gates: not run for this file (`registry_rasters_checked: 0`). No HOLDOUT-DTI or ORGANIZER-CONFIRMED number exists for it.

## Archived LWST file (not cleared)

- File: `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif`
- SHA-256: `bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a`
- Note: `GEMSDOESASS3 LWST-GeoConduit EXP3: 3D SPI+WijnsTheta+DualHGB300m 37654d B=2 HR=0.1111 SGMC=0.0657`
- Outside the bounds: 0 non-zero cells; literal lattice overlap inside the footprint 99.78%.

## Standing prompt (verbatim)

The project's standing prompt as recorded on 2026-10-27 is at [docs/research/standing-prompt-as-recorded-20261027.md](docs/research/standing-prompt-as-recorded-20261027.md). Read it before starting work.

<details>
<summary>Show the standing prompt</summary>

```text
Review the repo. 

I want to focus on the highest scoring submissions from the following sites, GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36.

THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt. Read the entire prompt. A lot of sites mention inspection only and a human inspector, but the inspection needs to be done through the project and needs to be validated for submission without human intervention.

PARALLEL-RUN PROTOCOL — read first. This session is one of several running from this same prompt.

1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check this on the surface before placement AND on the final dots.

2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_holdout.py and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.

3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.

4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above [0.90] means leakage until proven otherwise.

5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.

6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:
https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html
h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?
Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition. Must be unique submission unlike any within the GEMSDOE sites above. Verify working line by line no hallucinations.

Current competition leaderboard GEMSDOE high score: 0.4413

Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.

Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.

I tried to submit the document that i downloaded from the site but it returned this error on the submission form: "Predicted values must be in range [0, 1]"
Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later e.g. clustering with k=25
Create a executive summary subpage that explains exactly how to make a submission into the contest.
Create a github page for this repo that has clean ui, user friendly, simple and easy to use. It should be organized and clean.
```

</details>

## Core Values

- **Maximize P(Win):** every decision weighs tradeoffs, assesses risk, chooses the path maximizing probability of winning.
- **Own the Outcome:** end-to-end accountability; treat failure and success as signals.

(The definitions above are as recorded on main; the two labels are from the request.)

## Focus-9 owner-reported summary (from main, not re-verified here)

The table below is as recorded on main. Its uniqueness statements were not re-verified in this session. The measured per-site table is in [docs/research/focus-site-candidates-20261028.md](docs/research/focus-site-candidates-20261028.md).

| Site | Best file | Owner-reported score | Action |
|---|---|---|---|
| GEMSDOE32 | h33-h33-2-b2-...-zeros | **0.2778** (best of 9) | Already scored, do not resubmit |
| GEMSDOE36 | anderson-geothermal-pinn-... | 0.2750 | Already scored, do not resubmit |
| GEMSDOE28 | h36-1-rung30-blind-r1-... | 0.2710 | Already scored, do not resubmit |
| GEMSDOE31 | h27-4-solo-d28-... | 0.2708 | Already scored, do not resubmit |
| GEMSDOE33 | h33d-analog-tip-stepover-... | 0.2632 | Already scored, do not resubmit |
| GEMSDOE25 | dotted-h19-5-d2-8-... | 0.2600 | Already scored, do not resubmit |
| GEMSDOE30 | d28-poisson300m-offcat-... | 0.2600 | Already scored, do not resubmit |
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5-... | 0.2477 | Already scored, do not resubmit |
| GEMSDOE27 | topo-gap-closure-t-v2-on-d1-5-... | 0.2449 | Already scored, do not resubmit |

## Ranked hypotheses (not yet tested on the holdout)

See [docs/research/hypotheses_ranked_20261028.md](docs/research/hypotheses_ranked_20261028.md) (main) and [docs/research/independent-review-20261028.md](docs/research/independent-review-20261028.md) §7–8 (H-SASS3-E tested and negative; F, G, H untested).

## Validation gates

- `python scripts/verify_all_gates.py` (exit 0 is required in CI with `--expect-blocked`, which accepts only the documented blocked state).
- `pytest -q`.
- `python scripts/build_review_site.py` regenerates the pages and the per-site table from the evidence.
- `python scripts/lattice_bound_audit.py`, `python scripts/focus_site_candidate_audit.py` and `python scripts/candidate_format_audit.py` regenerate the measurements. They need the restored data (`python scripts/restore_data.py`); the focus audit also fetches sibling files with `gh`.

Competition data is restored into `.cache/gems_data` from owner mirrors (`data/restore_receipt.json`, 28 files, SHA-256 verified). The mirrors do not authenticate organizer provenance.

## Official sources

- Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Problem description, metric, submission format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Data (login required): https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- Official rules (NLR, Sept 2026): https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- USGS GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- GDR #1391 INGENIOUS: https://gdr.openei.org/submissions/1391
- 13GEMSDOE (calibration lattice source): https://github.com/buffedlizard55-lab/13GEMSDOE
- EPSG:32611: https://epsg.io/32611
- Tversky index: https://en.wikipedia.org/wiki/Tversky_index

## Remaining work

1. The owner records Option A, B or C (the decision is not an agent action).
2. The BGK file needs a provenance check (IR-SASS3-34) and a corrected run card (IR-SASS3-29). It must not be downloaded until the outside-bounds rule passes.
3. If Option A is recorded: re-run the gates with the recorded reading, then a separate selector picks one file within the weekly cap of three (NLR Official Rules §3.2).
4. Reconcile the two holdout evaluators (`gems57-pooled-hide-v2` vs SGMC-CAL) on the owner-scored set (IR-SASS3-23).
5. Compute the SGMC-CAL proxy for the nine latest candidates (not done).
6. Hypotheses H-SASS3-F, G and H are untested. Run them only after the decision, within the budget of 3 experiments or 2 hours, on the spatially-blocked holdout. This session ran no experiments.
7. Obtain the missing lane paragraph of the parallel-run protocol (IR-SASS3-24).

## Limitations

- The lane paragraph is missing, so the lane is undefined.
- Owner scores come from the task prompt and the leaderboard page, not organizer receipts. The public leaderboard shows only the public split (competition page 967).
- Overlap for the focus files was checked against ten references, not a full registry scan. The 451-download figure in the independent review was not re-run here.
- Holdout values are proxies. The two evaluators disagree about the champion and the owner order.
- Competition data comes from owner mirrors, not organizer-authenticated downloads.
- The raster content of the BGK file has an unresolved provenance statement (IR-SASS3-34).
- GitHub Pages output was checked by a local build only.

Full irregularities: [evidence/irregularities_ledger.json](evidence/irregularities_ledger.json).

## Reproduce checks

Create a Python virtual environment and install `numpy scipy scikit-learn rasterio pytest`.

1. `python scripts/verify_all_gates.py --expect-blocked`: exit 0 with the documented blocked state.
2. `pytest -q`.
3. `python scripts/build_review_site.py`.

Legacy page builders are disabled to prevent their outdated approval claims from returning.
