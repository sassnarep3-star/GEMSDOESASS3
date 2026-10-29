# GEMSDOESASS3 — read first

**Focus values:** Maximize P(Win). Own the Outcome.

## Verdicts (2026-10-29)

| File | Estimated score (label) | Unique under the literal rule? | OK to download? | OK to submit / upload? |
|---|---|---|---|---|
| **`gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-zeros.tif`** (21,012 dots) | HOLDOUT-DTI 0.042851 [0.038871, 0.046157] (proxy, not an organizer score) | **YES.** Lattice overlap 68.9987% (limit 70%). Max non-lattice 55.2%. \|Spearman\| 0.150 (limit 0.90). | **YES: OK to download** | **NOT RECOMMENDED for a slot.** Proxy is below the champion, and the CIs do not overlap. |
| `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` (37,654 dots, archived) | HOLDOUT-DTI 0.065702 [0.058992, 0.071240] | **NO.** Lattice overlap 99.78% (limit 70%). | **NO** | **NOT OK to submit.** |
| `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (champion, already scored) | OWNER-REPORT 0.2778. HOLDOUT-DTI 0.064121 [0.056730, 0.071649] | Already in the registry | n/a | Do not resubmit. |

**Download:** [the compliant TIF](docs/downloads/gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-zeros.tif) · [ZIP](docs/downloads/gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-zeros.tif.zip) · [run card](evidence/run_card_literal.json)

**Note to paste (≤140 characters):** the compliant file's `submission_note` in [`evidence/run_card_literal.json`](evidence/run_card_literal.json) (104 characters).

**Submission name:** `gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-zeros.tif`
**SHA-256:** `d84217d5c59ffc7ec06c3f2bbbf390ae764b26bf96810dca6bfe7ab7fd752fdb`

All scores are HOLDOUT-DTI proxies from `GEMSDOE32-SGMC-CAL-v3.0`, not organizer scores. No organizer receipt exists for either new file. Only a portal upload shows acceptance, and that uses one of the three weekly submissions.

**Decision needed from the owner:** whether the synthetic 13GEMSDOE calibration lattice counts as a registry raster under Rule 1. If it does not, the archived 37,654-dot file becomes OK to download (its proxy is effectively tied with the champion). If it does, the 21,012-dot file is the only unique option. The compliant file's download status does not depend on this answer; any upload does.

**Current decision: NOT OK to submit** for the archived 37,654-dot file. Its lattice overlap is 99.78%. The full review is in [docs/research/independent-review-20261028.md](docs/research/independent-review-20261028.md). Earlier claims that it beats the 0.2778 champion are withdrawn. Its SGMC-CAL value 0.065702 [0.058992, 0.071240] overlaps the champion's 0.064121. The archived note's `HR=0.1111` is a per-fold OOF value; the file's static HIDE-RECOVER value is 0.006130.

Historical archive only: `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` · SHA-256 `bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a` · prior note `GEMSDOESASS3 LWST-GeoConduit EXP3: 3D SPI+WijnsTheta+DualHGB300m 37654d B=2 HR=0.1111 SGMC=0.0657`.

Pages: [executive summary and submission guide](docs/executive-summary.html) · [overview](docs/index.html).

## Standing prompt

The project's standing prompt as recorded in a previous session is [here](docs/research/standing-prompt-as-recorded-20261027.md); read it before starting work. The current request adds the **PARALLEL-RUN PROTOCOL** and the requirement **MUST GENERATE A UNIQUE TIF SUBMISSION**: fail closed on any registry overlap above 70% or rank correlation above 0.90, check both surface and dots, run leakage canaries and buffered hide-and-recover, limit experiments, and leave final promotion to a separate selector. Do not interpret a failed uniqueness gate as permission to submit. Optimize for outcome, document uncertainty, and never fabricate a score.

Protocol rules in force: lane check (rank correlation >0.90 or >70% of dots within 3 px of any registry raster is a duplicate); leakage canary AUC >0.90 fails; hypothesis numbers labelled HOLDOUT-DTI or ORGANIZER-CONFIRMED; budget of 3 candidate experiments or 2 hours; promotion is a separate selector step. Experiment count (IR-SASS3-28): three literal candidate experiments (dense, random, dispersed) plus E1 (basement curvature, negative, a separate lane recorded as "1 of 3"). If the cap applies to all lanes together, it was exceeded by one. No further experiments run without an owner decision.

## Hypotheses

Ranked and untried, except E1 (H-SASS3-E, negative): H-SASS3-F (Gaussian-mixture boundaries on `tmi_hg`, `iso_grav_anom_hg`, `geod_shearrate`, `cond_surf`), H-SASS3-G (anisotropic Ripley's K on `ieq/deq_n100a15` seismicity), H-SASS3-H (Otsu ridges on `geod_dilaterate`; lowest priority). Details in the review. None will be spent without HOLDOUT-DTI validation first.

## Limitations and access needs

- **Access needed:** a DrivenData account for the portal upload (the agent has none); the owner's decision on the lattice (IR-SASS3-22); one of three weekly submissions; and confirmation of the sibling repository mapping (`buffedlizard55-lab`, IR-SASS3-09).
- **Data provenance:** restored training data comes from an owner mirror, and its SHA-256 pins prove mirror consistency, not organizer provenance (IR-SASS3-14). Official data download requires DrivenData login.
- **Lattice margin:** the compliant file sits 1.0 point below the 70% limit. Any refresh of the registry can change this. Rerun the literal audit immediately before any upload.
- **Leaderboard figures conflict:** the request cites a 0.3195 top score and a 0.4413 leader. The live leaderboard fetched in this session shows #1 xiaofanhu 0.4544 and #2 cfld__ 0.3916 ([leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)). Public and private scores can differ. The owner should confirm which figure applies (IR-SASS3-26).
- **Irregularities:** 28 entries are in [`evidence/irregularities_ledger.json`](evidence/irregularities_ledger.json). Open: IR-SASS3-22 (literal rule vs the 37,654-dot file), IR-SASS3-24 (uniqueness audit mixes in a non-submission raster), IR-SASS3-25 (`scripts/independent_review.py` cannot run here), IR-SASS3-26 (leaderboard figures), IR-SASS3-27 (1-point lattice margin). Also open: IR-SASS3-28 (experiment count across lanes). Resolved this session: IR-SASS3-20 (holdout gates passed on withdrawn baselines), IR-SASS3-21 (card contradicted the gate), IR-SASS3-23 (review's 5,379 gap count not reproduced).

## Reproduce checks

Create the environment: `python3 -m venv .venv && .venv/bin/pip install numpy scipy scikit-learn rasterio pytest`.

1. `bash scripts/download_competition_data.sh` restores the 28 training files into `.cache/gems_data/` and verifies SHA-256 pins. Restore receipts are historical.
2. `.venv/bin/python scripts/fetch_registry_rasters.py --workers 4` fetches and SHA-verifies the 378 registry rasters.
3. `.venv/bin/python scripts/lattice_gap_check.py` writes `evidence/lattice_gap_check.json` (ceiling of about 21,713 dots under the literal rule).
4. `.venv/bin/python scripts/build_literal_candidate.py --variant dispersed --out <path.tif>` rebuilds the compliant file. It reproduces SHA-256 `d84217d5…fd752fdb`.
5. `.venv/bin/python scripts/literal_registry_audit.py <candidate.tif> <receipt.json>` runs the literal audit.
6. `.venv/bin/python scripts/verify_literal_candidate.py [--write-card]` checks the compliant file's bytes, receipts, and run card.
7. `.venv/bin/python scripts/verify_all_gates.py --expect-blocked` must report exactly three documented FAILs (holdout HIDE-RECOVER, holdout SGMC, literal lattice) and exit 0.
8. `.venv/bin/python -m pytest -q`.
9. `.venv/bin/python scripts/build_review_site.py` refreshes the static pages (root and `docs/`).

`scripts/independent_review.py` is currently broken (IR-SASS3-25). Legacy page builders are disabled to prevent their outdated approval claims from returning.

## Official links

- [DrivenData competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Problem description (metric)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [GEMS Prize Official Rules (NLR PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

Not yet fetched, listed for manual review: USGS GeoDAWN (doi 10.5066/P93LGLVQ), epsg.io/32611, the Tversky index definition, gbcge.org INGENIOUS, and USGS ANSS.
