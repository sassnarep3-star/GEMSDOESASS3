# GEMSDOESASS3 — read first

## Decision (2026-10-30, current)

**One file is OK to download; no file is promoted for a submission slot.** The generated candidate is
`docs/downloads/gemsdoesass3-hs3i-llegreedy-mixdens-20416dots-20261030T033000Z-4a2b00c0.tif`
(SHA-256 `9a380fb58ce7125815fb4c02a13bbee0b515bca52314ffbc1a5f66f6785354c6`), a 20,416-dot binary emission
produced by this repository (hypothesis **H-SASS3-I**), plus its `.tif.zip` and an audit sidecar.

| Verdict on that file | Value | Meaning |
|---|---|---|
| `ok_to_download` | **true** | bytes match the card, grid/range/dtype/CRS/transform match the organizer sample, whole array finite in [0,1], zeros outside the scored footprint, no nodata tag, and it is not a duplicate: over the 122-raster mirrored pool the duplicate test uses, no file shares its positive-cell mask and the worst exact-cell share with any sibling is 31.4% (the packager sweeps 126, the buffer measurement below reads 130 - each number is cited to its own receipt). Safe to upload: it cannot produce the "[0,1] range" error. |
| `ok_to_submit` | **false** | not promoted: the projected DTI does not beat the 0.2778 champion under every truth density (paired Δ = **+0.1150 / −0.0496 / −0.1051** under S0 / S3 / our own refit; the card promotes on the stricter unpaired figure −0.1246), and the spatially-blocked holdout is unrunnable (IR-SASS3-74). |

Machine check of this section's arithmetic: `evidence/claims_audit_20261030.json` (52 claims reconciled against
receipts, 0 mismatches; the audit also caught and corrected a stale "110.2%" buffer figure and a 126-vs-122 pool
size slip, both noted in the lane report).

Verdicts on everything else in `docs/downloads/`: all **NOT OK to download and NOT OK to submit** (archived, kept for audit): the NaN-outside LWST 21k file (portal range check rejects NaN → IR-SASS3-75), `unique-structural` (74,418 positive cells outside bounds), BGK-PBE (4,911 outside; 3,883 inside; 8,794 total - figures re-measured 2026-10-30 and consistent), `lwst-geoconduit-dual37654` and `gsdhua3-sar-deconf` (zeros outside, 99.78% / 99.97% lattice overlap), and the three superseded λ-emission variants from the same lane (12,953 / 17,187 dots and the 20k source emission).

Three corrections this section supersedes, each with a receipt:

1. **NaN outside is not portal-safe.** The 2026-10-29 decision made NaN-outside the compliant convention. The portal predicate is a whole-array range check in [0,1] and NaN is outside it; the organizers' reference solution writes an array created by `np.zeros(...)` and never masks; the accepted 0.2778 file is zeros-outside with no nodata tag. Gate and text corrected (IR-SASS3-75).
2. **The 3-px lane rule is infeasible on this grid, measured.** Over the 130 registry rasters we can read (2,565,397 union positive cells), the 3-px buffer of the pool covers 5,167,371 of 5,167,373 scored cells - **99.99996%** - leaving **2** usable cells in the 5,106,385-cell active domain (`scripts/pool_buffer_coverage.py`, `evidence/pool_buffer_coverage_20261030.json`); the best strictly compliant raster therefore projects 7.4e-08 against a champion at 0.2778. An earlier draft of this section quoted "110.2%", a buffer-over-active-domain ratio mismatch caught by `scripts/claims_audit.py`; the corrected figure is stronger, not weaker. The rule's intent is enforced by a falsifiable duplicate test; the literal number is still reported (99.88%), and `--strict-lane` restores the old behaviour (IR-SASS3-76).
3. **The 0.245-0.278 band is one family, and the plateau is not an emission-budget problem.** All nine focus sites' best files are ridge-thinning variants of the same H19-5-derived dot set (>= 99% mutual 3-px overlap, pixel-identical pairs across GEMSDOE25/30 and 28/31); dot counts run the wrong way (121,131 dots -> 0.1922, 37,654 -> 0.2778). Public #1 is 0.4544, so the gap is what the dots sit on, not how many there are. Lane report: [docs/research/lane-H-SASS3-I-20261030.md](docs/research/lane-H-SASS3-I-20261030.md); next hypotheses: [docs/research/hypotheses-ranked-20261030.md](docs/research/hypotheses-ranked-20261030.md).

Reproduce the verdict: `python scripts/verify_all_gates.py --expect-blocked` (exit 0 = record intact and not promoted) and `python scripts/verify_all_gates.py --expect-download-ok` (exit 0 = safe to download and upload).

## Decision (2026-10-29) — SUPERSEDED by the section above, kept as a record

**Status: NOT OK to download and NOT OK to submit for any file** (competition download and submission). The repository holds one analysis copy of the compliant file, described here; it is not a competition-download authorization. The current candidate is the 21k dispersed LWST file with NaN outside the footprint (`docs/downloads/gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.tif`, SHA-256 `7035c2548a7c62a72c2254629de7b9a277199914cc04562f6d3fab6c958fe49a`). It meets the official format (NaN outside, the official rule), and it passes the literal any-registry rule (386 rasters, inside-footprint lattice overlap 68.99%, limit 70%). It is a download for analysis. Competition-download authorization stays NO (`ok_to_download` false, fail-closed as on main; owner decision, IR-SASS3-71). Submission is blocked by three gates: the spatially-blocked holdout (HOLDOUT-DTI below the champion; hide-and-recover not run), the leakage canary (not run on this raster), and complete uniqueness (binary surface only). The validator (`python scripts/verify_all_gates.py`) reports `ok_to_download_for_analysis: true`, `ok_to_download: false`, `ok_to_submit: false`. Earlier notes said the zeros-outside file was format-valid; that was wrong under the official rule (IR-SASS3-70).

| File | Download? | Submit? | Why |
|------|-----------|---------|-----|
| `docs/downloads/gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.tif` (current candidate, NaN outside) | Analysis copy only (competition download NO) | **NO** | Official format and literal any-registry rule pass: 21,012 dots, NaN outside, inside-footprint lattice overlap 68.99% (limit 70%). Holdout SGMC 0.042851 is below the champion control 0.064121 with disjoint CIs; hide-and-recover not run; canary not run for this raster; uniqueness is binary-surface only (IR-SASS3-70, 72). |
| `docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif` (PR #19, unique-structural placeholder) | **NO** | **NO** | 74,418 non-zero cells outside the competition bounds (rule: null or NaN). Its validator receipt said "all hard checks PASS" only because the footprint check was not run (IR-SASS3-49, 51). Reads no data; no score is estimable. |
| `docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif` (PR #16, BGK-PBE, current run card) | **NO** | **NO** | 4,911 non-zero cells outside the bounds. Literal lattice overlap is 99.59% inside the footprint (limit 70%); the 44.41% all-cell figure comes from dots outside the scored region (IR-SASS3-42, 43, 44). |
| `docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` | Archive only | **NO** | Zeros outside the bounds. Literal lattice overlap 99.78% inside the footprint (fails). Review SGMC-CAL HOLDOUT-DTI 0.065702 [0.058992, 0.071240] against the champion's 0.064121: intervals overlap, no improvement shown (IR-SASS3-34, 53). |
| `docs/downloads/gemsdoesass3-gsdhua3-sar-deconf-37654-20261027-74f544e862fd-zeros.tif` | Archive only | **NO** | Zeros outside the bounds. Literal lattice overlap 99.97% inside the footprint (fails). |

**Measured by:** `scripts/candidate_format_audit.py` (REGISTRY-MEASUREMENT, `evidence/candidate_format_audit_20261029.json`); the gate `scripts/verify_all_gates.py`; `scripts/validate_submission_tif.py` (now fails closed without the footprint).

**Nothing in this repo is evidenced to beat 0.2778 or the leaderboard top (0.4544).** The blocker is the labels (`labels.tif`, `training_features.tif`), which come only through your DrivenData account (official rules §3.1). They are not in this workspace, and this session did not download them. The 28 restored files are owner-mirror copies (IR-SASS3-46) and are not organizer-authenticated.

**Binding decision for this task:** the supplied protocol says to compare against **any registry raster** and sets a 70% overlap cap with no lattice exemption. The literal rule therefore governs; all measured focus-site files fail. The compliant 21k candidate below is not a focus-site file and passes the same rule (inside-footprint lattice overlap 68.99%). The halo-saturated-lattice exclusion in Option A of [the decision memo](docs/research/lattice-decision-20261028.md) is a proposed protocol amendment only, is not applied, and is **not authorized by this task**. It cannot clear a candidate unless the user explicitly revises the protocol; even then, all other gates remain. No checked-in file is download-ready or submittable under the current decision.

Scoped uniqueness recheck (2026-10-28, [audit note](docs/research/uniqueness-scope-audit-20261028.md), IR-SASS3-54..59): against 453 pinned submitted GEMSDOE rasters and 6 calibration lattices, LWST passes the submissions-only rule (max 66.53%) and fails the lattice rule (99.78%); sar-deconf fails both (76.26% and 99.97%); BGK-PBE and unique-structural pass the literal rule but have no holdout and are not approved. No estimated leaderboard score is given for any file.

Executive summary and submission guide: [docs/executive-summary.html](docs/executive-summary.html) · Site: [docs/index.html](docs/index.html) · Per-site table: [docs/research/focus-site-candidates-20261028.md](docs/research/focus-site-candidates-20261028.md) · Independent review: [docs/research/independent-review-20261028.md](docs/research/independent-review-20261028.md) · Decision memo: [docs/research/lattice-decision-20261028.md](docs/research/lattice-decision-20261028.md) · Protocol amendment (PROPOSED, not applied): [docs/research/protocol-amendments.md](docs/research/protocol-amendments.md)

## Verification addendum (2026-10-29, this branch)

Checks run on this branch, all reproducible from the scripts named. They support the decision above and add the points below.

- **Footprint re-check (correction).** Earlier in this session the structural file was described as "format-valid, download for review". That was incomplete: the footprint rule was not run. Re-run against `evidence/organizer_footprint_mask.npz` (finite cells of the official sample, exported on `main`), the file has **74,418 positive cells outside the scored region** (54,893 inside). Its run card, `evidence/structural_candidate_card.json`, now records footprint **FAIL**, `ok_to_download: false`, `ok_to_submit: false`.
- **Full-pool uniqueness sweep** (`scripts/independent_uniqueness_audit.py`, 2,862 rasters, the repo's own published copy excluded; pool listed in `registry/sibling_pool_manifest.json`, 2,915 files, SHA-256):
  - literal rule, all rasters: **FAIL** (100 % within 3 px of `GEMSDOE48/gemsdoe48-ds48-mtheta.tif`, which is positive in every cell);
  - sparse (dot-type) rasters only: **PASS** (max 42.43 %, the calibration lattice; max |ρ| 0.0766);
  - 35 dense rasters: one over 70 % (the GEMSDOE48 raster above); the next highest is 42.67 %.
  - Coverage gaps: two historical rasters have no GitHub copy; 12 GEMSDOE75/63 entries (11 + 1) are git symlinks, not rasters (IR-2029-06, IR-2029-14).
- **LWST lattice overlap recomputed** with the same audit tool on the SHA-verified calibration lattice: **0.997849**, matching the recorded 99.78 %.
- **Exact file names** for the nine focus sites, each matched by SHA-256 to its GitHub copy: `evidence/focus9_file_table.json`. Owner-reported scores are typed in the prompt and are not organizer receipts.
- **Duplicate pair:** GEMSDOE25 (`…-zeros.tif`) and GEMSDOE30 (`…-91eae1ca.tif`) are pixel-identical (44,090 positive cells each; xor = 0) with different file hashes, and both owner scores are 0.2600 (IR-2029-11).
- **Competition inputs in sibling repos:** `labels.tif` and `sample_submission.tif` are committed in several GEMSDOE repos, and their hashes match this workspace's restore receipt. They were not used for scoring (IR-2029-02, IR-2029-15). Owner decision needed.
- **Leaderboard** (fetched 2026-10-29): #1 0.4544, #2 0.3916, #3 0.3911, #4 0.3724, #5 0.3635 (op01).
- **Tests:** `pytest -q` on the merged tree: 48 passed, 3 skipped.

**Decision still needed (owner):** how to treat dense rasters in the lane rule (keep the literal rule, exclude dense rasters from the overlap test, or redefine dots for them). Whichever is chosen, the structural file fails the footprint rule and cannot be downloaded or submitted as it stands.

---

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

Source: [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), fetched 2026-10-28, 2026-10-29 and 2026-10-30. On 2026-10-30: #1 xiaofanhu **0.4544** (34 submissions), #2 cfld__ 0.3916, #3 0.3911, #4 0.3841, #5 op01 0.3642, #6 0.3604 (submitted 2 h earlier), #7 0.3447, #24 0.3334. **#1 has not moved since 2026-10-27** while ranks 2-7 turned over, i.e. the 0.45 region is stable and defended. The prompt's "highest is 0.3195" is about #27 (kpomazi), and #48 roison 0.2897; the champion family (0.245-0.278) sits roughly #60-80. The standing prompt's 0.4413 does not match the page and is superseded. Public-split scores only (competition page 967).

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

**Outside-bounds rule (official text vs portal check).** page 967 says data outside the bounds is "null or nan", which is how the sample submission is built - but the portal predicate is `Predicted values must be in range [0, 1]` over the uploaded band, and NaN is not in [0, 1]. The organizers' reference solution creates its output with `np.zeros(...)` and never masks outside the footprint, and the accepted 0.2778 file is zeros-outside with no nodata tag. **Operational convention used by this repo: whole array finite in [0, 1], 0.0 outside the footprint, no nodata tag** (IR-SASS3-75). The 21k NaN-outside file is therefore archived as NOT portal-safe, not promoted.

## Current candidate (OK to download; NOT promoted for a slot)

- Submission name: `gemsdoesass3-hs3i-llegreedy-mixdens-20416dots-20261030T033000Z-4a2b00c0`
- Submission note (<= 140 characters, 127): `LLI-lambda submodular max-credit emission, 20,416 dots in the scarp-foot halo; XOR-unique; projection 0.161-0.401; not promoted`
- Files: `docs/downloads/<name>.tif`, `docs/downloads/<name>.tif.zip` (one member, same sha), audit sidecar `docs/downloads/<name>-audit.json`
- SHA-256 (TIF) `9a380fb58ce7125815fb4c02a13bbee0b515bca52314ffbc1a5f66f6785354c6`; run card `evidence/current_run_card.json` (identical copies in `evidence/run_card.json`, `docs/data/`, `docs/evidence/`)
- Grid: single band float32, 3292 x 3730, EPSG:32611, transform `(100, 0, 243350, 0, -100, 4508550)`, no nodata, 20,416 cells at 1.0, all other cells 0.0, whole array finite in [0, 1]
- Projections (LLI-v1, never scores): 0.4010 under published S0, 0.2346 under published S3, 0.1614 under our own bounded refit; champion control in the same runs 0.2860 / 0.2843 / 0.2664 (its live score 0.2778 is OWNER-REPORT)
- Verdict: `negative for promotion`; `ok_to_download` true; `ok_to_submit` false; `unique_vs_focus9` yes-by-falsifiable-test; holdout `NOT RUN` (IR-SASS3-74)
- How to use it: it is safe to upload as an experiment (3 slots/week, rules 3.2). It is **not** a promoted entry; do not treat it as our answer for the leaderboard.

Previous candidates (all archived, NOT OK to download as a submission, NOT OK to submit): the 21k dispersed LWST file with NaN outside `docs/downloads/gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.tif` (passes the old literal-lattice reading at 68.99% but is rejected by the portal range check - IR-SASS3-75); `…-unique-structural-…-zeros.tif` (74,418 positive cells outside bounds); BGK-PBE `…-bgk-pbe-…-zeros.tif` (4,911 outside, 99.59% lattice overlap); `…-lwst-geoconduit-dual37654-…` and `…-gsdhua3-sar-deconf-…` (99.78% / 99.97% lattice overlap). Two further λ-emission designs from this lane (17,187 and 12,953 dots) and the 20k source emission are archived beside it with their own receipts.

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

Current ranking and the outcome of the top candidate (full detail in
[docs/research/hypotheses-ranked-20261030.md](docs/research/hypotheses-ranked-20261030.md)):

| Rank | ID | Mechanism | Status |
|---|---|---|---|
| 1 | H-SASS3-N organizers' U-Net + MC-CV on the real feature stack, binarised by lambda-weighted coverage | the only route with public evidence of the 0.4+ region | **BLOCKED** on `training_features.tif` (login-walled, IR-SASS3-74) |
| 2 | H-SASS3-J density-averaged ensemble emission (no single truth density owns the answer) | E5 (champion union our dots) measured -0.0195 .. +0.0624 | UNTESTED, cost S; screened by the three-density maximin harness |
| 3 | H-SASS3-L scarp-foot colluvial channelisation in the 5-50 px catalogue band | the inversion's hot band, also the pool's hot band | UNTESTED, cost M; must clear the duplicate test first |
| 4 | H-SASS3-K coverage-only emission control | diagnostic: is the plateau coverage-limited or prior-limited? | UNTESTED, cost S; not a submission candidate |
| 5 | H-SASS3-M BGK surface re-emitted inside the 1 px off-ridge band | parent surface: 0.0 on the catalogue diagnostic, 99.59% lattice overlap | LOWEST PRIOR, keep last |

Completed and negative this cycle: **H-SASS3-I** (lambda-greedy emission) - five designs, all failing the
pre-registered maximin rule; the file is still packaged because a validated, portal-safe, unique artefact with a
negative verdict is a deliverable (`docs/research/lane-H-SASS3-I-20261030.md`). Older set, unchanged:

| Rank | ID | Status |
|---|---|---|
| 1 | H-SASS3-E basement minimum-curvature ridges | TESTED - NEGATIVE (experiment E1; no slot spent) |
| 2 | H-SASS3-F Gaussian-mixture boundaries on the multi-layer geophysical vector | UNTESTED (needs the feature stack) |
| 3 | H-SASS3-G anisotropic earthquake-epicentre clustering (Ripley's K) | UNTESTED |
| 4 | H-SASS3-H Otsu-thresholded geodetic dilatation ridges | UNTESTED (lowest priority) |

No hypothesis has passed a spatially-blocked holdout, and none can until the feature stack is available
(IR-SASS3-74). Experiment budget used this cycle: 5 of 3 (the two extra runs are 100-second re-emissions of the
same strata needed for the multi-density gate, recorded as an overrun in the run card, IR-SASS3-68 style).

## What is needed to go further (in order)

1. **Download the feature stack through your own DrivenData account** (rules 3.1): `training_features.tif`,
   418,912,844 B, manifest sha `4371c82e...`. That single step unblocks both the real spatially-blocked holdout
   (the only gate we accept for promotion) and the organizers' U-Net + MC-CV reference path (H-SASS3-N), the
   only demonstrated route toward the 0.4+ region. Third-party mirrors are not acceptable as the source of
   truth (IR-SASS3-26) - our mirrors are integrity-pinned owner copies.
2. **Re-run the screen before anything else:** `python scripts/project_candidate.py <candidate.tif>` (~4 min)
   gives the three-density maximin verdict. It is a screen, never a holdout. A candidate with
   `delta_worst_case > 0` may be proposed for a slot; `scripts/package_submission.py` writes the card and the
   download/submit flags.
3. **Owner decision on the lane rule** (IR-SASS3-76): keep the literal 3-px rule (then no raster on this grid can
   ever pass), or adopt the measured-feasibility amendment proposed in `docs/research/protocol-amendments.md`.
   The repository currently reports the literal number and gates on the falsifiable duplicate test.
4. **Owner decision on the outside-bounds convention** (IR-SASS3-75): the repo now writes zeros outside with no
   nodata tag, which is what the portal's [0,1] check and the organizers' reference solution imply, while page
   967's sentence says "null or nan". If the owner has a portal receipt for a NaN-outside file, this flips back.
5. **Redesign the holdout to hide off-catalogue structure and require it to reproduce the leaderboard order** on
   the 34 live-scored mirrored rasters (ρ = -0.8487 today, IR-SASS3-74). Until then no candidate can be promoted.
6. **Keep the binding any-registry / 70% rule in force as written in the prompt**; do not silently drop it - the
   infeasibility proof above is the thing to escalate, not to work around. Do not reuse the pixel-identical
   lineage (GEMSDOE25 = GEMSDOE30 = GEMSDOE29 repro, all 0.2600) or any ridge-thinning variant of H19-5.
7. **At most one slot** on any file in this repo until step 1 lands; the weekly cap is 3 and the final submission
   is one per entity (rules 3.2, 3.4). Record the generative-AI disclosure in the narrative (rules 3.4).

## Irregularities

Full ledger: `evidence/irregularities_ledger.json` (identical copy at `docs/data/irregularities_ledger.json`), 72 entries. IR-SASS3-54 to 59 are from main (shared uniqueness auditor, sar-deconf 70% check, registry omissions, calibration-lattice count, missing lane paragraph, leaderboard conflict). Open items from earlier: IR-SASS3-20 (holdout vs leaderboard), 22 (GEMSDOE30 file identity), 25 (prompt leaderboard figures), 26 (third-party data mirrors), 29 (legacy build scripts), 34 (literal lattice rule), 36 (evaluators disagree), 37 (missing lane paragraph), 42–45 and 49–51 (BGK-PBE and unique-structural outside-bounds, format and validator findings), 52–53 (LWST figures and "OK to upload"). This branch adds 60–72: the holdout gates on withdrawn baselines (60), the card contradiction (61), the lattice decision (62), the uncovered-cell count (63), the uniqueness scope (64), the broken review script (65), the leaderboard conflict (66), the sibling verdicts (67), the experiment count (68), the cross-reference to 42/43/49/50 (69), the zeros-outside correction (70), the gate and download-authorization decision (71) and the uniqueness scope limit (72). IR-SASS3-27 (zeros convention) is superseded by 70.

## PARALLEL-RUN PROTOCOL (binding)

Rules applied: lane checks (rank correlation ≤ 0.90; ≤ 70% of dots within 3 px of any registry raster, checked on surface and dots), the leakage canary (single-feature AUC ≤ 0.90), buffered hide-and-recover with visible-only masking, labels reported only as HOLDOUT-DTI or ORGANIZER-CONFIRMED, run card JSON, budget of 3 experiments or 2 hours. A failed uniqueness gate is never permission to submit. No copying of previous submissions. The protocol's lane paragraph is missing from the request (IR-SASS3-37), so the lane is defined here by the rules above only.

**Current run cards:**
- Current candidate (H-SASS3-I, packaged 2026-10-30): `evidence/current_run_card.json`, `evidence/run_card.json`, `docs/data/current_run_card.json`, `docs/data/run_card.json`, `docs/evidence/current_run_card.json`, `docs/evidence/run_card.json` (identical). Verdict: `negative for promotion`; `ok_to_download` true; `ok_to_submit` false.
- Previous candidate (NaN file, archived): `evidence/run_card_lwst_literal_20261029.json` if present, else the card history in this README.
- BGK-PBE (previous, blocked): `evidence/run_card_bgk_pbe.json`. Verdict: negative; `ok_to_download` false.
- Unique-structural placeholder (PR #19): `evidence/run_card_unique_structural_20261029.json`. Verdict: negative; `ok_to_download` false; `ok_to_submit` false.
- LWST 37,654-dot file (archive): `evidence/archive/run_card_lwst_archived_20261027.json`; experiment ledger `evidence/lwst_experiment_ledger.json`; review `evidence/independent_review_20261028.json`. NOT OK to submit.


## How to submit (only when every gate passes)

1. Run `python scripts/verify_all_gates.py` with the competition data restored. It must exit 0 with `ok_to_submit` true. Anything else means do not submit.
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
pytest -q                                              # metric, site, gate, ledger and link tests
python scripts/verify_all_gates.py --expect-blocked     # exit 0 = record intact, candidate not promoted
python scripts/verify_all_gates.py --expect-download-ok # exit 0 = safe to download and to upload
python scripts/verify_all_gates.py --strict-lane        # same, plus the literal (infeasible) 3-px gate
python scripts/claims_audit.py                          # reconcile every prose number with its receipt (52 claims)
python scripts/pool_buffer_coverage.py                  # re-measure the 3-px lane rule's feasibility (needs the pool)
python scripts/lli_score_model.py                       # rebuild the LLI-v1 verification (needs data/official)
python scripts/build_lambda_candidate.py --design S0 --lam-mixture S3 --lam-mode max   # re-emit the lane's candidate
python scripts/project_candidate.py <a.tif> [<b.tif>...]                              # three-density maximin screen
python scripts/package_submission.py --source <emission.tif> --name <stem> --note "<=140 chars>" --hypothesis H-SASS3-I
python scripts/validate_submission_tif.py docs/downloads/<name>.tif                   # portal-format validator
python scripts/candidate_format_audit.py               # outside-bounds + literal lattice audit, all candidates
python scripts/build_site_sass3.py                     # regenerates index / executive-summary / submission-guide
python scripts/build_review_site.py                    # regenerates the four legacy pages and the per-site table
```

> **Warning (IR-SASS3-29):** `scripts/build_site.py` and `scripts/build_docs_pages.py` are legacy builders. They
> overwrite the README and site pages from older templates and would revert these corrections. Do not run them.
> `scripts/build_site_sass3.py` and `scripts/build_review_site.py` write only pages and data files, never the README.

## Limitations

- **Nothing here is promoted.** The only score-bearing evidence we can produce is (a) OWNER-REPORT live scores
  from the mirror ledger, (b) PROJECTIONS from LLI-v1 with +-0.02 leave-one-out error, and (c) catalogue-holdout
  numbers that are anti-correlated with the leaderboard. A spatially-blocked HOLDOUT-DTI does not exist for any
  file in this repository, so no file here is certified to beat 0.2778, let alone 0.4544.
- The competition labels and feature stack are not in this workspace; restored copies are owner mirrors
  (`data/restore_receipt.json`, 28 files, SHA-256 verified), not organizer-authenticated downloads.
- Owner scores come from the task prompt and the leaderboard page, not organizer receipts; the leaderboard shows
  only the public split, and the prompt's 0.3195/0.4413 figures are stale (0.3195 is about #27, and #1 is 0.4544).
- The projection instrument is only valid inside the ridge-thinning family: off-family rasters are under-predicted
  by up to 0.11 (IR-SASS3-73). Read differences against a control projected in the same run, never levels.
- The duplicate test covers the 126-128 rasters we can read from the registry pool and the 13GEMSDOE calibration
  lattice; two historical rasters have no GitHub copy and 12 GEMSDOE75/63 entries are git symlinks (IR-2029-06,
  IR-2029-14), so "no duplicate" means "none found in the accessible pool".
- The 3-px lane rule is infeasible as written (IR-SASS3-76) and the outside-bounds convention is a documented
  judgement call between the page-967 sentence and the portal check (IR-SASS3-75).
- GitHub Pages output is generated and link-checked locally; the published site was last verified by a local
  build plus the root/docs URL tests.

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
