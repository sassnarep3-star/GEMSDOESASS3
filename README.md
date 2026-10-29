# GEMSDOESASS3 — read first

## Status (2026-10-28)

**Current decision: NOT OK to submit.** The archived file is NOT OK to submit (`ok_to_submit: false`), and the literal Rule 1 gate is BLOCKED. No focus-site file is cleared. The archived LWST file is kept for audit only. The validator reports `OK TO DOWNLOAD: NO (BLOCKED)` and `OK TO SUBMIT: NO`.

- **Why:** the 13GEMSDOE calibration lattice covers 99.87% of the footprint within 3 px. Only 6,649 footprint cells lie outside the buffer, so the literal 70% test caps a passing file at 22,163 dots. Every focus-site file has 37,654 or more dots and fails. All 18 measured focus-site files (9 historical, 9 latest) fail with 99.05% to 100.00% overlap.
- **What would change it:** an owner decision (Option A, B or C) recorded in [docs/research/lattice-decision-20261028.md](docs/research/lattice-decision-20261028.md). Option A, the like-for-like reading that the shared template already implements, is recommended. The official NLR rules contain no uniqueness or dot-count requirement; the 70% test is the project's internal protocol.
- **Start here:** [executive summary and submission guide](docs/executive-summary.html) · [focus-site table](docs/research/focus-site-candidates-20261028.md) · [decision memo](docs/research/lattice-decision-20261028.md) · [independent review (2026-10-28)](docs/research/independent-review-20261028.md) · [review-20261028](docs/research/review-20261028.md).
- **Measured in this checkout:** [lattice bound](evidence/lattice_bound_audit_20261028.json) (`scripts/lattice_bound_audit.py`) and [per-file measurements](evidence/focus_site_candidate_audit_20261028.json) (`scripts/focus_site_candidate_audit.py`).
- **Correction:** earlier figures of 5,379 cells and 11,297 dots did not reproduce. The recomputed values above replace them (ledger IR-SASS3-20).

Earlier claims that the archived file beats the 0.2778 champion are withdrawn. The LWST SGMC-CAL value is 0.065702 [0.058992, 0.071240] against the champion's 0.064121, and the intervals overlap. No file in this repo has an organizer receipt.

**Leaderboard (ORGANIZER-CONFIRMED, public page fetched 2026-10-28):** rank 1 xiaofanhu 0.4544; rank 27 kpomazi 0.3195; rank 48 roison 0.2897. The 0.4413 figure in the standing prompt is superseded.

**Historical archive only** (not cleared): `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` · SHA-256 `bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a` · prior note `GEMSDOESASS3 LWST-GeoConduit EXP3: 3D SPI+WijnsTheta+DualHGB300m 37654d B=2 HR=0.1111 SGMC=0.0657`.

## Core Values

1. **Maximize P(Win).**
2. **Own the Outcome.**

## Remaining work and limitations

Remaining work (in order):
1. Owner records Option A, B or C (the decision, not an agent action). Draft amendment: [docs/research/protocol-amendments.md](docs/research/protocol-amendments.md), status PROPOSED.
2. If Option A is recorded: re-run the gates with the recorded reading, then a separate selector picks one file within the weekly cap of three (NLR Official Rules §3.2).
3. Reconcile the two holdout evaluators (`gems57-pooled-hide-v2` vs SGMC-CAL) on the owner-scored set (ledger IR-SASS3-23).
4. Compute the SGMC-CAL proxy for the nine latest candidates (not done).
5. Hypotheses H-SASS3-F, G and H are untested. Run them only after step 1, within the budget of 3 experiments or 2 hours, on the spatially-blocked holdout. This session ran no experiments.
6. Obtain the missing parallel-run lane paragraph (ledger IR-SASS3-24).

Limitations:
- The lane paragraph is missing, so the lane is undefined.
- Owner scores come from the task prompt, not organizer receipts. The public leaderboard shows only the public split (competition page 967).
- Overlap was checked against ten references for the focus files, not a full registry scan. The 451-download figure was not re-run here.
- Holdout values are proxies. The two evaluators disagree about the champion and the owner order.
- Raw data is not in the checkout; restore receipts are historical, and mirror hashes do not authenticate organizer provenance.
- GitHub Pages output was checked by a local build only.

Full irregularities: [evidence/irregularities_ledger.json](evidence/irregularities_ledger.json).

## Standing prompt (verbatim)

The project's standing prompt as recorded on 2026-10-27 is also stored at [docs/research/standing-prompt-as-recorded-20261027.md](docs/research/standing-prompt-as-recorded-20261027.md). Read it before starting work.

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

## Reproduce checks

Create a Python virtual environment and install `numpy scipy scikit-learn rasterio pytest`.

1. `python scripts/verify_all_gates.py`: a nonzero exit is expected while the candidate is blocked. CI runs `python scripts/verify_all_gates.py --expect-blocked`, which succeeds only for the documented blocking failure.
2. `pytest -q`.
3. `python scripts/build_review_site.py` regenerates the static pages and the per-site table from the evidence files.
4. `python scripts/lattice_bound_audit.py` and `python scripts/focus_site_candidate_audit.py` regenerate the measurements. Both need the restored data (`python scripts/restore_data.py`); the second fetches sibling files with `gh`.

Legacy page builders are disabled to prevent their outdated approval claims from returning.

[Competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) · [page 967 (rules and metric)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [official rules (PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) · [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
