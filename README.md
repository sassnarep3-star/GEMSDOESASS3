# GEMSDOESASS3 — read first

## Decision (2026-10-29)

**Status: NOT OK to download and NOT OK to submit for any file. Neither the BGK-PBE file nor the unique-structural file is format-valid under the competition's outside-bounds rule.** The validator (`python scripts/verify_all_gates.py`) reports `OK TO DOWNLOAD: NO (BLOCKED)` and `OK TO SUBMIT: NO` for the current candidate. Download approval now requires the outside-bounds, literal-lattice and registry checks to pass on the file itself, and fails closed when any cannot be measured (IR-SASS3-41, 42, 49).

| File | Download? | Submit? | Why |
|------|-----------|---------|-----|
| `docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif` (PR #19, unique-structural placeholder) | **NO** | **NO** | 74,418 non-zero cells outside the competition bounds (rule: null or NaN). Its validator receipt said "all hard checks PASS" only because the footprint check was not run (IR-SASS3-49, 51). Reads no data; no score is estimable. |
| `docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif` (PR #16, BGK-PBE, current run card) | **NO** | **NO** | 4,911 non-zero cells outside the bounds. Literal lattice overlap is 99.59% inside the footprint (limit 70%); the 44.41% all-cell figure comes from dots outside the scored region (IR-SASS3-42, 43, 44). |
| `docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` | Archive only | **NO** | Zeros outside the bounds. Literal lattice overlap 99.78% inside the footprint (fails). Review SGMC-CAL HOLDOUT-DTI 0.065702 [0.058992, 0.071240] against the champion's 0.064121: intervals overlap, no improvement shown (IR-SASS3-34, 53). |
| `docs/downloads/gemsdoesass3-gsdhua3-sar-deconf-37654-20261027-74f544e862fd-zeros.tif` | Archive only | **NO** | Zeros outside the bounds. Literal lattice overlap 99.97% inside the footprint (fails). |

**Measured by:** `scripts/candidate_format_audit.py` (REGISTRY-MEASUREMENT, `evidence/candidate_format_audit_20261029.json`); the gate `scripts/verify_all_gates.py`; `scripts/validate_submission_tif.py` (now fails closed without the footprint).

**Nothing in this repo is evidenced to beat 0.2778 or the leaderboard top (0.4544).** The blocker is the labels (`labels.tif`, `training_features.tif`), which come only through your DrivenData account (official rules §3.1). They are not in this workspace, and this session did not download them. The 28 restored files are owner-mirror copies (IR-SASS3-46) and are not organizer-authenticated.

**Owner decision needed (not an agent action):** the literal lattice rule blocks every focus-site file. Options in [docs/research/lattice-decision-20261028.md](docs/research/lattice-decision-20261028.md): **A (recommended)** the like-for-like reading that the shared template already implements, which excludes halo-saturated lattices (`vendor/gems57/uniqueness.py` line 353) from the dot-overlap test; **B** keep the literal rule (nothing eligible); **C** an edge-only rule (not produced, not endorsed). Option A does not clear any file for the outside-bounds rule, which needs its own fix.

Executive summary and submission guide: [docs/executive-summary.html](docs/executive-summary.html) · Site: [docs/index.html](docs/index.html) · Per-site table: [docs/research/focus-site-candidates-20261028.md](docs/research/focus-site-candidates-20261028.md) · Independent review: [docs/research/independent-review-20261028.md](docs/research/independent-review-20261028.md) · Decision memo: [docs/research/lattice-decision-20261028.md](docs/research/lattice-decision-20261028.md) · Protocol amendment (PROPOSED, not applied): [docs/research/protocol-amendments.md](docs/research/protocol-amendments.md)

## Standing prompt (verbatim, as recorded 2026-10-27)

The full standing prompt is at [docs/research/standing-prompt-as-recorded-20261027.md](docs/research/standing-prompt-as-recorded-20261027.md). Read it each session.

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

- Maximize P(Win)
- Own the Outcome

## Leaderboard (ORGANIZER-CONFIRMED)

Source: [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), fetched 2026-10-28 and 2026-10-29. #1 xiaofanhu **0.4544**; #27 kpomazi **0.3195**; #48 roison **0.2897**. The champion GEMSDOE32 (0.2778) is below #48. The standing prompt's 0.4413 does not match the page and is superseded. Public-split scores only (competition page 967).

## Verified official facts (with links)

| Fact | Source |
|------|--------|
| Metric: distance-weighted Tversky, α = 0.2, β = 0.8, triangular kernel with 300 m (3 px) support | [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| Worked example: TP_w = 3.00, FP_w = 1.89, FN_w = 2.00 → TI = 0.60. Repo check: 3/(3 + 0.2·1.89 + 0.8·2.00) = 0.6027 | Same page; `tests/test_metric_official_example.py` |
| Format: single layer, float32, values in [0, 1], EPSG:32611, 100 m, same bounds as training data; "data outside the bounds is null or nan" | Same page, "Submission format" |
| Three submissions per week; one final submission per entity; generative-AI use must be disclosed in the narrative | [Official rules (NLR PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) §3.2, §3.4 |
| Training features and labels come via the DrivenData account after registration; labels are from the INGENIOUS Great Basin compilation (doi:10.15121/1881483) | Official rules §3.1, §3.3 |
| Leaderboard top: #1 xiaofanhu 0.4544 | [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) |
| Rules page | [herox rules](https://www.herox.com/GEMSPrize/resource/2274) |

**Outside-bounds interpretation.** The official text asks for null or NaN outside the bounds. Zeros outside the footprint are the convention of the owner-scored files, including the 0.2778 champion, so this repo treats zeros as accepted and rejects non-zero values outside (IR-SASS3-27). This is an interpretation, not an organizer statement.

## Current candidate on main: BGK-PBE (blocked)

- Submission name: `gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif`
- SHA-256: `7ab47cf538791e921fc54544b1979e93fc25acda1d91aa5528e940f67359f41f`
- SHA-256 (first 12): `7ab47cf53879`
- Submission note: `GEMSDOESASS3 BGK-PBE EXP1: basement gravity-gradient x K/eTh x dilatation blind-fault locator, NNE faults, unscored`
- Run card: `evidence/current_run_card.json` (corrected 2026-10-29: `ok_to_download` set to false; the earlier value was true)
- File: `docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif` (audit copy, not an approved download)

The hypothesis for this file is in `docs/research/hypotheses_ranked_20261028.md` (BGK-PBE, PR #16). No holdout result exists for it.

## Why 0.2778 scored highest, and why the local holdout cannot say so

Owner-reported leaderboard scores for the nine focus sites, against the HR-static evaluator recorded in the audit (`docs/data/focus9_executive_audit.json`):

| Site | Owner-reported score | HOLDOUT-DTI HR-static [95% CI] | File |
|------|----------------------|--------------------------------|------|
| GEMSDOE24 | 0.2477 | 0.0932 [0.0813, 0.1060] | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` |
| GEMSDOE25 | 0.2600 | 0.0967 [0.0842, 0.1095] | `dotted-h19-5-d2-8-20261002-e56ea318af89-zeros` |
| GEMSDOE27 | 0.2449 | 0.0927 [0.0809, 0.1054] | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite` |
| GEMSDOE28 | 0.2710 (best of 4 files) | 0.0294 [0.0250, 0.0344] | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite` |
| GEMSDOE30 | 0.2600 | 0.0967 [0.0842, 0.1095]* | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` |
| GEMSDOE31 | 0.2708 | 0.0305 [0.0257, 0.0361] | `h27-4-solo-d28-20261004-8acb75e1-allfinite` |
| GEMSDOE32 | **0.2778 (champion)** | 0.0045 [0.0038, 0.0053] | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` |
| GEMSDOE33 | 0.2632 | 0.0520 [0.0458, 0.0583] | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` |
| GEMSDOE36 | 0.2750 | 0.0046 [0.0039, 0.0053] | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` |

\* GEMSDOE30's audit row is attached to a file named with `gems24-`; file identity unconfirmed (IR-SASS3-22).

Labels: owner scores are **OWNER-REPORT**, not organizer-confirmed. The HR-static values are **HOLDOUT-DTI** for that evaluator, but the withheld-positive count is not recorded in the audit, so the label is incomplete.

**Finding (reported, not re-run here).** The HR-static holdout ranks these files in reverse order of the leaderboard (Spearman −0.89, n = 10, p = 0.001; `evidence/holdout_vs_leaderboard_concordance_20261029.json`). The independent review's other evaluators disagree: SGMC-CAL puts the champion second of nine (0.064121 vs top GEMSDOE36 0.064444); pooled-hide-v2 gives the champion 0.003885 [0.003316, 0.004478] (IR-SASS3-36).

**Structural observation (measured here).** GEMSDOE32's historical file (37,654 dots) overlaps the other focus-site historical files at 99.9–100% within 3 px (`evidence/focus_site_candidate_audit_20261028.json`). The 0.2778 result therefore sits inside a family of near-identical dot placements. Why it scored high is still a hypothesis: the holdout tests recovery of catalogue faults, while the scored set is new faults outside the USGS catalogue. Explaining 0.2778 needs the labels, and then a holdout designed for off-catalogue recovery.

## Hypotheses (ranked; validation status)

From the independent review §8 (`docs/research/independent-review-20261028.md`):

| Rank | ID | Status |
|---|---|---|
| 1 | H-SASS3-E basement minimum-curvature ridges | TESTED — NEGATIVE (experiment E1, 1 of 3 budget; no slot spent) |
| 2 | H-SASS3-F Gaussian-mixture boundaries on the multi-layer geophysical vector | UNTESTED (candidate for E2) |
| 3 | H-SASS3-G anisotropic earthquake-epicentre clustering (Ripley's K) | UNTESTED |
| 4 | H-SASS3-H Otsu-thresholded geodetic dilatation ridges | UNTESTED (lowest priority) |

No hypothesis has passed the spatially-blocked holdout. The budget is 3 experiments or 2 hours, and this session used none of it.

## What is needed to go further (in order)

1. **Owner decision** on the lattice rule: Option A, B or C (see Decision above). Not an agent action.
2. **Labels and features from your DrivenData account**: download `training_features.tif` and `labels.tif` (official rules §3.1) into `.cache/gems_data/` or `data/`. Do not use third-party mirror copies (IR-SASS3-26).
3. **Fix the outside-bounds rule** for the BGK-PBE and unique-structural files (both have non-zero outside cells), or replace them. Re-run `scripts/candidate_format_audit.py`.
4. **Measure the current file's registry overlap** inside the gate. The gate's registry check currently reads a stored LWST audit (IR-SASS3-45).
5. **Redesign the holdout** for off-catalogue structure, and check that it reproduces the leaderboard order on the nine owner-reported files. Reconcile the evaluators (IR-SASS3-36).
6. **Compute the SGMC-CAL proxy** for the nine latest candidates (not done).
7. **Run H-SASS3-F, G or H** only after the owner decision, within the budget, on the spatially-blocked holdout.
8. **Obtain the missing lane paragraph** of the parallel-run protocol (IR-SASS3-37).
9. Choose at most one candidate, check it against the 3-per-week cap, and record the generative-AI disclosure (rules §3.2).

## Irregularities

Full ledger: `evidence/irregularities_ledger.json` (identical copy at `docs/data/irregularities_ledger.json`), 53 entries. Open items for review: IR-SASS3-20 (holdout vs leaderboard), 22 (GEMSDOE30 file identity), 25 (prompt leaderboard figures), 26 (third-party data mirrors), 27 (outside-bounds convention), 29 (legacy build scripts), 34 (literal lattice rule blocks all focus files), 36 (evaluators disagree), 37 (missing lane paragraph), 42–44 (BGK-PBE outside bounds and format gate), 45 (registry check reads a stored audit), 49–51 (unique-structural outside bounds; format-only PASS claims; validator fix), 52–53 (LWST figures and "OK to upload").

## PARALLEL-RUN PROTOCOL (binding)

Rules applied: lane checks (rank correlation ≤ 0.90; ≤ 70% of dots within 3 px of any registry raster, checked on surface and dots), the leakage canary (single-feature AUC ≤ 0.90), buffered hide-and-recover with visible-only masking, labels reported only as HOLDOUT-DTI or ORGANIZER-CONFIRMED, run card JSON, budget of 3 experiments or 2 hours. A failed uniqueness gate is never permission to submit. No copying of previous submissions. The protocol's lane paragraph is missing from the request (IR-SASS3-37), so the lane is defined here by the rules above only.

**Current run cards:**
- BGK-PBE (current): `evidence/current_run_card.json` and `evidence/run_card.json`. Verdict: `blocked_outside_bounds`; `ok_to_download` false; `ok_to_submit` false.
- Unique-structural placeholder (PR #19): `evidence/run_card_unique_structural_20261029.json`. Verdict: negative; `ok_to_download` corrected to false; `ok_to_submit` false.
- LWST (archive): experiment ledger `evidence/lwst_experiment_ledger.json`; review `evidence/independent_review_20261028.json`. NOT OK to submit.

## How to submit (only when every gate passes)

1. Run `python scripts/verify_all_gates.py` with the competition data restored. It must print `OK TO DOWNLOAD: YES (APPROVED)` and `OK TO SUBMIT: YES`. Anything else means do not submit.
2. Run the fold-honest evaluator and the feature canaries. Report the version, withheld-positive count and spatial-block CI (HOLDOUT-DTI).
3. Check rank correlation and final-dot overlap against every accessible registry raster, with no exclusions. Fail closed when coverage is incomplete.
4. Run the leakage canary (AUC ≤ 0.90) and buffered hide-and-recover with visible-only masking.
5. Validate with `python scripts/validate_submission_tif.py <file.tif>`. It must pass every hard check, including the outside-bounds check.
6. Use a distinct filename and a note of at most 140 characters. Write a run card JSON with all metrics, the CI, the gates and the promotion decision.
7. A separate selector promotes a passing candidate, within the weekly cap of 3 (official rules §3.2), via "New submission" on the [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/).

## Reproduce checks

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install numpy scipy scikit-learn rasterio pytest
pytest -q                                              # metric, site, gate and link tests
python scripts/verify_all_gates.py --expect-blocked    # exit 0 = documented blocked state
python scripts/candidate_format_audit.py               # outside-bounds and literal lattice, all candidate files (needs restored data)
python scripts/validate_submission_tif.py docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif   # exits 1: outside-bounds fails
python scripts/build_review_site.py                    # regenerates the four pages and the per-site table
```

> **Warning (IR-SASS3-29):** `scripts/build_site.py` and `scripts/build_docs_pages.py` are legacy builders. They overwrite the README and site pages from older templates and would revert the corrections. Do not run them. `scripts/build_review_site.py` writes only the four pages and the per-site research table, not the README.

## Limitations

- The competition data (labels and features) is not in this workspace. The restored copies come from owner mirrors (`data/restore_receipt.json`, 28 files, SHA-256 verified), not organizer-authenticated downloads.
- Owner scores come from the task prompt and the leaderboard page, not organizer receipts. The leaderboard shows only the public split.
- The overlap check covers ten references for the focus files and the lattice, not the full registry. The 451-download scan from the independent review was not re-run here.
- Holdout values are proxies. Evaluators disagree about the champion and the owner order.
- The outside-bounds convention (zeros outside) is an interpretation of the official text, not an organizer statement.
- The lane paragraph of the protocol is missing (IR-SASS3-37).
- GitHub Pages output was checked by a local build only.

## Sources

- [Competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description and metric (page 967)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition data (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official rules (NLR PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [HeroX rules page](https://www.herox.com/GEMSPrize/resource/2274)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [GDR #1391 INGENIOUS](https://gdr.openei.org/submissions/1391)
- [13GEMSDOE (calibration lattice source)](https://github.com/buffedlizard55-lab/13GEMSDOE)
- [EPSG:32611](https://epsg.io/32611) · [Tversky index](https://en.wikipedia.org/wiki/Tversky_index)
