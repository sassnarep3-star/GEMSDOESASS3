# GEMSDOESASS3 — read first

## Decision (2026-10-29)

**Status (2026-10-29):** format-valid · download-ready for a format test only · submit-gated (**NOT OK to submit** until a holdout and the registry gates pass).


| File | Download? | Submit? | Why |
|------|-----------|---------|-----|
| `docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif` | Yes, format test only | **NO** | Format PASS (`scripts/validate_submission_tif.py`). Lattice lane PASS (42.35% dot-level within 3 px; Spearman 0.0015). Score **NOT ESTIMABLE**, and it uses no data signal (fixed straight corridors from an RNG). |
| `docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif` | Yes, format test only | **NO** | Format PASS (validator). Lattice lane PASS (44.4% pixel-level within 3 px; ρ −0.0016). Holdout NOT RUN, so score **NOT ESTIMABLE**. Built on main by PR #16, not by this branch; its own run card says `ok_to_submit: False`. Its original submission note was truncated and is replaced (IR-SASS3-31). |
| `docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` | Archive only | **NO** | Lattice lane FAIL (99.79%). Holdout 0.1111 HOLDOUT-DTI, not organizer-confirmed. |
| `docs/downloads/gemsdoesass3-gsdhua3-sar-deconf-37654-20261027-74f544e862fd-zeros.tif` | Archive only | **NO** | Lattice lane FAIL (99.97%). |

**Nothing in this repo is evidenced to beat 0.2778 or the leaderboard top of 0.4544.** The single blocker is the labels: `labels.tif` and `training_features.tif` come through your own DrivenData account (official rules §3.1). They are not in this workspace, so no holdout DTI or confidence interval can be produced here.

Full review: [docs/research/independent-review-20261028.md](docs/research/independent-review-20261028.md) · Run card: [evidence/run_card_unique_structural_20261029.json](evidence/run_card_unique_structural_20261029.json) · Site: [docs/index.html](docs/index.html) · Submission guide: [docs/executive-summary.html](docs/executive-summary.html)

---

## Standing prompt (read every session)

> I want to focus on the highest scoring submissions from the following sites and I want an executive summary on every site:
> GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36.
>
> I want an executive summary on every site that is clear and obvious which is the best submission to submit to obtain a high score on the leaderboard.
>
> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION.
> It must score higher than 0.2778 (ideally higher than the leaderboard top, 0.4544 as of 2026-10-29).
> There should be an easy to download submission tif file.
>
> It must pass validation without any human intervention.
> Values in [0,1]. No NaN inside footprint. CRS/EPSG:32611/shape/transform match the training grid.
>
> Follow PARALLEL-RUN PROTOCOL (lane rule: rank-correlation ≤0.90 vs registry rasters; ≤70% of dots within 3 px;
> holdout hide-and-recover with visible-only masking; leakage canary AUC ≤0.90; run card JSON; budget 3 experiments / 2 hours).
> Must not copy previous submissions.
> Must create executive summary subpage explaining how to submit.
>
> Short submission note ≤ 140 chars. Easy download link must be prominent (top of site / executive summary).
> No human inspection; validation must be programmatic.
>
> Do not interpret a failed uniqueness gate as permission to submit.
> No hallucinations; verify line by line; official verified sources with links.
> Put prompt into repo README and read it each session.
> Core values: Maximize P(Win), Own the Outcome.

---

## Verified official facts (with links)

| Fact | Source |
|------|--------|
| Metric: distance-weighted Tversky, α = 0.2, β = 0.8, triangular kernel with 300 m (3 px) support | [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| Worked example: TP_w = 3.00, FP_w = 1.89, FN_w = 2.00 → TI = 0.60. Repo check: 3/(3 + 0.2·1.89 + 0.8·2.00) = 0.6027, and the three metric implementations agree | Same page; `tests/test_metric_official_example.py` |
| Format: single layer, float32, values in [0, 1], EPSG:32611, 100 m, same bounds as training data; "data outside the bounds is null or nan" | Same page, "Submission format" |
| Three submissions per week; one final submission per entity; generative-AI use must be disclosed in the narrative | [Official rules (NLR PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) §3.2, §3.4 |
| Training features and labels come via the DrivenData account after registration; labels are from the INGENIOUS Great Basin compilation (doi:10.15121/1881483) | Official rules §3.1, §3.3 |
| Leaderboard top: #1 xiaofanhu, 0.4544 (checked 2026-10-29). The 0.4413 and 0.3195 figures in the prompt do not match. | [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) |
| Rules page | [herox rules](https://www.herox.com/GEMSPrize/resource/2274) |

---

## What the new TIF is, and what it is not

`docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif`

- Generated by `scripts/generate_unique_submission.py`. It reads **no feature layer and no label**. About 10,000 dots sit on six fixed straight NNE corridors with ±400 m random jitter (seed 24301), burned as radius-2 disks. It is off-lattice and unique by construction, not predictive.
- Format: float32, one band, EPSG:32611, 3292 × 3730 at 100 m, values 0 or 1, no NaN. Receipt: `evidence/validator_unique_structural_20261029.json`.
- Lattice lane (dot-level): 42.35% of blobs within 3 px of the 13GEMSDOE calibration lattice (limit 70%); sampled Spearman 0.0015 (limit 0.90). Receipt: `evidence/lattice_lane_check_20261029.json`. The other 450 downloads were not re-checked here.
- Cells outside the dots are 0.0, not NaN. The official text asks for null/NaN outside bounds. This is unconfirmed (IR-SASS3-27).
- Its earlier description as "geologically-informed" and "off-catalogue traces" was **wrong**. Corrected in IR-SASS3-24.

---

## Why 0.2778 scored highest, and why the local holdout cannot say so

Owner-reported leaderboard scores for the nine focus sites, against the local holdout (HR-static DTI, from `docs/data/focus9_executive_audit.json`):

| Site | Owner-reported score | HOLDOUT-DTI [95% CI] (evaluator as recorded in audit) | File | Unique? |
|------|----------------------|------------------------------------------------------|------|---------|
| GEMSDOE24 | 0.2477 | 0.0932 [0.0813, 0.1060] | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | No (submitted) |
| GEMSDOE25 | 0.2600 | 0.0967 [0.0842, 0.1095] | `dotted-h19-5-d2-8-20261002-e56ea318af89-zeros` | No (submitted) |
| GEMSDOE27 | 0.2449 | 0.0927 [0.0809, 0.1054] | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite` | No (submitted) |
| GEMSDOE28 | 0.2710 (best of 4 files) | 0.0294 [0.0250, 0.0344] | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite` | No (submitted) |
| GEMSDOE30 | 0.2600 | 0.0967 [0.0842, 0.1095]* | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | No (submitted) |
| GEMSDOE31 | 0.2708 | 0.0305 [0.0257, 0.0361] | `h27-4-solo-d28-20261004-8acb75e1-allfinite` | No (submitted) |
| GEMSDOE32 | **0.2778 (champion)** | 0.0045 [0.0038, 0.0053] | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | No (submitted) |
| GEMSDOE33 | 0.2632 | 0.0520 [0.0458, 0.0583] | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | No (submitted) |
| GEMSDOE36 | 0.2750 | 0.0046 [0.0039, 0.0053] | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | No (submitted) |

\* GEMSDOE30's audit row is attached to a file named with `gems24-`; file identity unconfirmed (IR-SASS3-22).

Labels: owner-reported scores are **OWNER-REPORT**, not organizer-confirmed. Holdout values are **HOLDOUT-DTI**; the withheld-positive count is not recorded in the audit, so the label is incomplete.

**Finding.** The holdout ranks these files in reverse order of the leaderboard (Spearman −0.89, n = 10, p = 0.001; `evidence/holdout_vs_leaderboard_concordance_20261029.json`). The champion has the second-lowest holdout score. Hypothesis, unverified: the holdout tests recovery of catalogue faults, while the scored set is new faults outside the USGS catalogue. A holdout that rewards the catalogue cannot select a leaderboard submission. Explaining 0.2778 requires labels from the user's account, and then a holdout redesigned for off-catalogue recovery.

---

## What is needed to go further (in order)

1. **Labels and features, from your DrivenData account.** Download `training_features.tif` and `labels.tif` (official rules §3.1). Place them under `.cache/gems_data/` or `data/`. Do not use third-party mirror copies (IR-SASS3-26).
2. **Redesign the holdout** to withhold off-catalogue-like structure, and check it reproduces the leaderboard order on the nine owner-reported files. Only then is it a usable selector.
3. **Confirm the footprint and NaN convention** against `sample_submission.tif` (IR-SASS3-27).
4. **Re-run the lane check against all 451 downloads** (needs the sibling checkouts).
5. Choose at most one candidate, check it against the 3-per-week cap, and record the generative-AI disclosure (rules §3.2).

---

## Irregularities

Full ledger: `evidence/irregularities_ledger.json` (identical copy at `docs/data/irregularities_ledger.json`). Open items for review: IR-SASS3-20 (holdout vs leaderboard), 22 (GEMSDOE30 file identity), 26 (third-party data mirrors), 27 (NaN convention), 25 (prompt leaderboard figures), 29 (legacy build scripts overwrite pages).

---

## PARALLEL-RUN PROTOCOL (binding)
**Current run card (main, PR #16, BGK-PBE):** `evidence/run_card.json`
- Submission: `gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif`
- Note: `GEMSDOESASS3 BGK-PBE EXP1: basement gravity-gradient x K/eTh x dilatation blind-fault locator, NNE faults, unscored`
- SHA-256: `7ab47cf538791e921fc54544b1979e93fc25acda1d91aa5528e940f67359f41f`
- Verdict: `format_valid_pending_data` · ok_to_download: True · ok_to_submit: False
- Holdout and registry gates NOT RUN (no labels locally). Source of the file: PR #16. Its full lattice-lane result is in `evidence/lattice_lane_check_20261029.json`.


Rules 1–6: lane checks (rank-correlation ≤0.90, ≤70% of dots within 3 px), reuse template tools
(`evaluate_holdout.py`, `submission_writer.py`), label numbers as HOLDOUT-DTI or ORGANIZER-CONFIRMED
only, leakage canary, run card JSON, budget 3 experiments / 2 hours. Do not interpret a failed
uniqueness gate as permission to submit. No copying of previous submissions.

**Last run card (historical, blocked):** `evidence/run_card.json`
- Submission: `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif`
- Note: `GEMSDOESASS3 LWST-GeoConduit EXP3: 3D SPI+WijnsTheta+DualHGB300m 37654d B=2 HR=0.1111 SGMC=0.0657`
- SHA-256: `bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a`
- Verdict: negative. **NOT OK to submit** (literal lattice rule, 99.78% > 70%). Review: [independent-review-20261028.md](docs/research/independent-review-20261028.md).

**Current run card:** `evidence/run_card_unique_structural_20261029.json`. Verdict: negative (not promoted). ok_to_download true, ok_to_submit false.

---

## How to submit (when a candidate passes every gate)

1. Run the fold-honest evaluator and the feature canaries. Report version, withheld count and spatial-block CI.
2. Check rank correlation and final-dot overlap against every accessible registry raster, with no exclusions. Fail closed when coverage is incomplete.
3. Run the leakage canary (AUC ≤ 0.90) and buffered hide-and-recover with visible-only masking.
4. Validate with `python scripts/validate_submission_tif.py <file.tif>`. It must pass every hard check. Use a distinct filename and a note of at most 140 characters.
5. Write a run card JSON with all metrics, the CI, the gates, and the promotion decision.
6. A separate selector promotes a passing candidate, within the weekly cap of 3 (official rules §3.2), via "New submission" on the [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/).

---

## Reproduce checks

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install numpy scipy scikit-learn rasterio pytest
pytest -q                                          # metric, site, and gate tests
python scripts/validate_submission_tif.py docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif
# Lattice lane needs .cache/gems_data/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif
#   (pinned sha256 b4570b40…; fetch with gh api, see scripts/check_lattice_lane.py)
python scripts/check_lattice_lane.py               # exit 0 only if every file passes
python scripts/verify_all_gates.py                 # nonzero exit expected while blocked
```

> **Warning (IR-SASS3-29):** do not run `scripts/build_site.py`, `scripts/build_docs_pages.py` or `scripts/build_review_site.py`. They overwrite the README and site pages from older templates and would revert the 2026-10-29 corrections.

---

## Sources

- [Competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description and metric (page 967)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official rules (NLR PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [HeroX rules page](https://www.herox.com/GEMSPrize/resource/2274)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS Great Basin compilation, doi:10.15121/1881483](https://doi.org/10.15121/1881483)
- [EPSG:32611](https://epsg.io/32611)

Raw data and caches are not included in this checkout. Restore receipts are historical, and mirror hashes do not authenticate organizer provenance.
