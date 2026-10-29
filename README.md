# GEMSDOESASS3 — GEMS Prize Challenge Submission Hub

**Arena branch:** `arena/84fd876f-gemsdoesass3` (fixed — do not switch or push to any other branch)
**Status:** Active | **Unique TIF submission:** download-ready, format-valid, submit-gated



## Machine-readable identifiers

- Submission name: `gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif`
- SHA-256: `7ab47cf538791e921fc54544b1979e93fc25acda1d91aa5528e940f67359f41f`
- SHA-256 (first 12): `7ab47cf53879`
- Submission note: `GEMSDOESASS3 BGK-PBE EXP1: basement gravity-gradient x K/eTh radiometric enrichment x geodetic dilatation blind-fault locator. NNE-trendi...`
- Run card: `evidence/current_run_card.json`

---

## Standing Prompt (read every session)

The full standing prompt is the user request for this session. Key requirements:

1. **Focus on the 9 highest-scoring GEMSDOE sites:** GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36. Produce an executive summary on every site that is clear and obvious which is the best submission to download/submit for a high leaderboard score. Each entry must be unique — not an exact duplicate of any previous submission. Include a table: file to download, estimated score, whether unique vs the other GEMSDOE sites.

2. **MUST GENERATE A UNIQUE TIF SUBMISSION.** Do not copy a previous submission (except for learning/education). It must be obvious whether the generated TIF is OK to download and submit.

3. **Easy download:** a clickable File to submit must be obvious on the site (executive summary or very beginning).

4. **Validation without human intervention:** inspection must be done through the project, validated for submission without human intervention. No NaN inside footprint, values in [0,1], CRS/shape/transform must match.

5. **Unique name + short note** (≤140 chars, e.g. "clustering with k=25").

6. **PARALLEL-RUN PROTOCOL** — LANE / REUSE / LABEL / LEAKAGE CANARY / RUN CARD / BUDGET. Fail closed on registry overlap >70% or rank correlation >0.90. Label every number as HOLDOUT-DTI or ORGANIZER-CONFIRMED. End with one JSON run card. Stop after 3 experiments or 2 hours.

7. **3–5 candidate geological hypotheses** not yet tried, each naming layers, physical signature, why it catches catalogue-missing faults, and how it differs from repo implementations. Rank by expected DTI improvement and implementation cost. Validate top candidate on holdout before touching a weekly submission slot.

8. **GitHub Pages site** with clean UI, user-friendly, organized, official verified links.

9. **Create a PR and merge to main.** Report remaining work and limitations.

---

## Current Submission (Unique, Format-Valid)

| Property | Value |
|---|---|
| **File** | `docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif` |
| **ZIP** | `docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif.zip` |
| **SHA-256** | `7ab47cf538791e921fc54544b1979e93fc25acda1d91aa5528e940f67359f41f` |
| **Method** | BGK-PBE (Hypothesis #1): basement gravity-gradient × radiometric K/eTh × geodetic dilatation blind-fault locator, NNE-trending normal faults |
| **Format** | Single-band GeoTIFF, EPSG:32611, 3730×3292, 100 m, float32, nodata=None |
| **Range** | [0, 1], zero NaN, zero Inf |
| **Positive dots** | 6,178 hard · 8,794 soft (300 m triangular halo) |
| **OK to download** | ✅ YES (format gate passed) |
| **OK to submit** | ❌ NOT YET — OK TO SUBMIT: NOT YET (holdout & registry gates pending competition data) |
| **Unique vs focus-9** | ✅ YES — not a copy of any GEMSDOE24/25/27/28/30/31/32/33/36 file |
| **Run card** | `evidence/current_run_card.json` |

**Download on the site:** https://sassnarep3-star.github.io/GEMSDOESASS3/executive-summary.html

---

## Focus-9 Executive Summary (owner-reported scores)

| Site | Best file | Score | Unique? | Action |
|---|---|---|---|---|
| GEMSDOE32 | h33-h33-2-b2-...-zeros | **0.2778** (best of 9) | No — H19-5 family | Already scored, do not resubmit |
| GEMSDOE36 | anderson-geothermal-pinn-... | 0.2750 | No — 97.4% vs champion | Duplicate |
| GEMSDOE28 | h36-1-rung30-blind-r1-... | 0.2710 | No — 95.5% vs champion | Duplicate |
| GEMSDOE31 | h27-4-solo-d28-... | 0.2708 | No — exact dup of GEMSDOE28 | Duplicate |
| GEMSDOE33 | h33d-analog-tip-stepover-... | 0.2632 | No — 92.6% vs champion | Duplicate |
| GEMSDOE25 | dotted-h19-5-d2-8-... | 0.2600 | No — byte-identical to GEMSDOE30 | Duplicate |
| GEMSDOE30 | d28-poisson300m-offcat-... | 0.2600 | No — byte-identical to GEMSDOE25 | Duplicate |
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5-... | 0.2477 | No — H19-5 D1.5 variant | Duplicate |
| GEMSDOE27 | topo-gap-closure-t-v2-on-d1-5-... | 0.2449 | No — 86.7% vs champion | Duplicate |

Full table with download links: `docs/executive-summary.html`

---

## Ranked Hypotheses (not yet tried)

See `docs/research/hypotheses_ranked_20261028.md`:

1. **BGK-PBE** (recommended): gravity-gradient × K/eTh radiometric × geodetic dilatation, blind-fault locator
2. **SST-2MT**: paleo sinter mounds + 2 m shallow-temperature probe confluence
3. **MT-Edge**: magnetic tilt-angle + analytic-signal lineament coherence
4. **LLW-SPI**: Lake Lahontan shoreline flexure + SPI/Theta persistence
5. **InSAR-LST** (deferred): Sentinel-1 InSAR + ECOSTRESS thermal inertia

---

## Validation Gates

Run on a machine with competition data in `.cache/gems_data/`:

```bash
bash scripts/download_competition_data.sh   # requires DrivenData login
python scripts/verify_all_gates.py          # 13-check format + holdout + registry
python -m pytest -q
```

The format gate (CRS/shape/transform/range [0,1]/NaN) has been verified on this sandbox. Holdout-DTI, leakage canary, and registry-overlap require `training_features.tif`, `labels.tif`, `sample_submission.tif` (DrivenData login required — absent here).

---

## Official Sources

- Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Problem description: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Data (login required): https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- USGS GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- GDR #1391 INGENIOUS: https://gdr.openei.org/submissions/1391
- EPSG:32611: https://epsg.io/32611
- Tversky index: https://en.wikipedia.org/wiki/Tversky_index

---

## Core Values

- **Maximize P(Win):** every decision weighs tradeoffs, assesses risk, chooses the path maximizing probability of winning.
- **Own the Outcome:** end-to-end accountability; treat failure and success as signals.

---

## Limitations

- No DrivenData auth in this sandbox → cannot auto-download competition data or run holdout/registry gates.
- Raster content is a synthetic stand-in; real multi-sensor features must be computed on `training_features.tif` + public GeoDAWN rasters before submission.
- No organizer-confirmed score exists for the new file. Leaderboard top 0.4413 (owner-reported) and focus-9 best 0.2778 (owner-reported) are not beaten here.
- Promotion to a real submission slot is a separate selector step within the weekly cap.

## Machine-readable identifiers

- Submission name: `gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif`
- SHA-256: `7ab47cf538791e921fc54544b1979e93fc25acda1d91aa5528e940f67359f41f`
- SHA-256 (first 12): `7ab47cf53879`
- Submission note: `GEMSDOESASS3 BGK-PBE EXP1: basement gravity-gradient x K/eTh radiometric enrichment x geodetic dilatation blind-fault locator. NNE-trendi...`
- Run card: `evidence/current_run_card.json`
