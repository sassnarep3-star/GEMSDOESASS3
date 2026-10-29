# GEMSDOESASS3 — read before every session

**Arena values:** **Maximize P(Win)** · **Own the Outcome**.

## Current decision — 2026-10-28

**Do not submit the archived LWST GeoTIFF.** The file can be downloaded from this repository for research/archival use only; uploading it is not approved. Its local GeoTIFF/range checks pass, but the official sample, complete current registry, cached feature stack, and sibling checkouts are absent in this checkout. A prior pinned/hash-checked lattice audit recorded **99.7849%** of its dots within 3 px of the calibration raster, above the protocol's 70% limit. The witness is now absent locally, so that is explicitly an **archived measurement**, not a fresh recheck; the current gate fails closed.

The former final-dot scan over 451 submitted downloads recorded a 66.53% maximum overlap and 0.135425 maximum sampled absolute Spearman correlation. Those are **archived subset results only**, not current full-registry clearance. A separate archived run card reports the pre-placement surface and final dots on a different 386-raster scope; neither is revalidated here. Do not conflate those scopes or claim current uniqueness. See [the review](docs/research/independent-review-20261028.md) and [the review run card](docs/data/current_run_card.json).

**No new unique competition TIF was generated in this review.** Renaming or repackaging the historical candidate would not make it unique. A new raster cannot be validated without the required data and current registry; the task brief also does not identify this checkout's single assigned method paragraph, and the recorded H-SASS3-A lane already used its 3-experiment budget. No experiment or submission slot was spent in this review. This is a recorded blocker, not a claim that the user's “must generate” requirement has been completed.

The stored archive is [`gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif`](docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif) · SHA-256 `bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a`. **Download only for analysis; do not upload.** Current archive note (93/140 chars): “Archive only: format checked; literal registry uniqueness fails the 3-px rule. Do not submit.”

The earlier `HIDE-RECOVER=0.111062` statement is withdrawn as the static file's score; it was an OOF/per-fold result with a mislabeled comparator. The archived static-file proxy values are **HOLDOUT-DTI** 0.006130 [0.005175, 0.007123] (GEMSDOE32-HIDE-RECOVER-v3.0; 22,232 withheld positives; B_visible=2 px) and 0.065702 [0.058992, 0.071240] (GEMSDOE32-SGMC-CAL-v3.0; 62,703 withheld positives). Neither is an organizer score or a leaderboard prediction. The prompt's 0.4413 and 0.4544 leaderboard-top claims conflict and were not independently checked in this review.

## Standing task prompt — retain and read before each project session

The complete prompt as supplied by the user is preserved in [`docs/research/standing-prompt-as-recorded-20261027.md`](docs/research/standing-prompt-as-recorded-20261027.md). The active requirements are summarized here so this README itself remains the session entry point:

- Compare the best reported work from GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, and 36. Keep **OWNER-REPORT**, **HOLDOUT-DTI** estimates/proxies, **model projections**, and **ORGANIZER-CONFIRMED** receipts separate. A leaderboard score is confirmed only with organizer evidence.
- **MUST GENERATE A UNIQUE TIF SUBMISSION** is an acceptance requirement; it is explicitly unmet and blocked in this review. The goal is a distinct, format-valid GeoTIFF with a unique filename and truthful note of at most 140 characters. It must be obvious whether downloading or submitting is allowed. Never copy a prior submission as a candidate; archive files may be used for learning only. A format-valid archive is not an eligible submission.
- Before implementation, rank 3–5 geological hypotheses. For each, state the named layer(s), physical signature, why it might locate uncatalogued faults, how it differs from repository work, implementation cost, and any official data source required. Verify data availability before calling an idea viable.
- Use the shared `vendor/gems57` feature/evaluator/writer stack; fix shared tools once, do not fork. Validate with buffered whole-segment hide-and-recover, exact visible-fault masking, single-feature leakage canaries, named evaluator, withheld-positive count and 95% CI. Preserve negative results.
- **PARALLEL-RUN PROTOCOL — read first.** Stay inside the explicitly assigned method lane; compare **both** the pre-placement surface and final dots against every in-scope registry raster; fail closed above 0.90 absolute rank correlation or 70% of dots within 3 px. Do not exempt a raster without a protocol amendment.
- Stop at 3 experiments or 2 hours. Do not use a submission slot or promote a candidate; promotion is a separate selector decision under the current organizer cap.
- End the review with one JSON run card covering hypothesis/mechanism/mimic, HOLDOUT-DTI evidence, uniqueness status, raster hash, validator output, filename/note, download/submission status, and verdict.
- Preserve **Maximize P(Win)** and **Own the Outcome**. Verify claims line by line, name official sources, flag irregularities, automate checks where possible, and do not hallucinate.

**Current blockers:** the assigned lane paragraph is not identifiable from the prompt for this checkout; the H-SASS3-A ledger records 3/3 experiments; local official sample, cached feature stack, and sibling registry are absent. Resolve these before proposing another experiment or a submission. The archived lattice result remains a blocking negative under the literal rule; no exemption is applied here.

## Site and reproducibility

- [Overview](index.html) · [Submission guide](executive-summary.html) · [Full independent review](docs/research/independent-review-20261028.md)
- Rebuild the evidence report with `python scripts/independent_review.py` (requires NumPy, SciPy, and Rasterio). Its output labels unavailable registry checks as archived and fails the current uniqueness gate closed.
- Rebuild the static pages with `python scripts/build_review_site.py`.
- Run `pytest -q` and `python scripts/verify_all_gates.py --expect-blocked`. A blocked submission is the expected state unless current, complete uniqueness evidence and all other protocol gates pass.

Official references for manual review: [competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) · [competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [official data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) · [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [GEMS Official Rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution). External data and the current organizer board were not checked in this review; a link alone is not proof of availability or score provenance.
<details>
<summary>Verbatim standing task prompt (recorded 2026-10-27)</summary>

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
