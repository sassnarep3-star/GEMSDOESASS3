# GEMSDOESASS3 — read first

**Focus values:** Maximize P(Win). Own the Outcome.

## Verdicts (2026-10-29)

**Current candidate: `gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-zeros.tif`** (21,012 dots, literal-rule compliant).
The current file is format-valid and literal-rule compliant. **OK to download: YES.** **OK to submit: NO (not recommended for a leaderboard slot).**

| File | Estimated score (label) | Unique under the literal rule? | OK to download? | OK to submit / upload? |
|---|---|---|---|---|
| **`gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-zeros.tif`** (current) | HOLDOUT-DTI 0.042851 [0.038871, 0.046157] (proxy, not an organizer score) | **YES.** Lattice overlap 68.9987% (limit 70%). Max non-lattice 55.2%. \|Spearman\| 0.150 (limit 0.90). | **YES** | **NOT RECOMMENDED for a slot.** Proxy is below the champion, and the CIs do not overlap. |
| `gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif` (main, BGK-PBE) | Not scored: holdout not run, fail-closed | **NO.** Lattice overlap 99.59%. 4,911 non-zero values outside the footprint. | **NO** | **NOT OK to submit.** |
| `gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif` (main, unique-structural) | Not scored: holdout not run, fail-closed | **NO.** Lattice overlap 99.85%. 74,418 non-zero values outside the footprint. | **NO** | **NOT OK to submit.** |
| `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` (archived, 37,654 dots) | HOLDOUT-DTI 0.065702 [0.058992, 0.071240] | **NO.** Lattice overlap 99.78%. | **NO** | **NOT OK to submit.** |
| `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (champion, already scored) | OWNER-REPORT 0.2778. HOLDOUT-DTI 0.064121 [0.056730, 0.071649] | Already in the registry | n/a | Do not resubmit. |

**Download the current file:** [TIF](docs/downloads/gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-zeros.tif) · [ZIP](docs/downloads/gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-zeros.tif.zip) · [run card](evidence/run_card.json) · [literal receipt](evidence/literal_audit_gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2.json)

- **Submission name:** `gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-zeros.tif`
- **Note to paste (≤140 characters):** `LWST dispersed 21k dots: literal-unique (max lattice overlap 68.99%); proxy below champion; not promoted`
- **SHA-256:** `d84217d5c59ffc7ec06c3f2bbbf390ae764b26bf96810dca6bfe7ab7fd752fdb`

All scores are HOLDOUT-DTI proxies from `GEMSDOE32-SGMC-CAL-v3.0`, with 62,703 withheld positives, not organizer scores. No organizer receipt exists for any new file. Only a portal upload shows acceptance, and it uses one of the three weekly submissions.

**Decision needed from the owner.** Does the synthetic 13GEMSDOE calibration lattice count as a registry raster under Rule 1? The lattice is listed in the registry manifest, so this repo counts it, with no exemption (IR-SASS3-35). If it counted as none, the 37,654-dot LWST file would become OK to download, with its proxy effectively tied with the champion. The owner should also rule on the measure. Rule 1 says "dots", which is the measure used here. `main`'s IR-SASS3-30 argues the dot-level measure does not suit line-like rasters, and its pixel-level figures (44.4%, 42.35%) are not the rule's wording (IR-SASS3-42).

**Current decision: NOT OK to submit** for any file. The compliant file is the only one that is OK to download. Earlier claims that the LWST file beats the 0.2778 champion are withdrawn: its SGMC-CAL value 0.065702 [0.058992, 0.071240] overlaps the champion's 0.064121. The archived note's `HR=0.1111` is a per-fold OOF value; the file's static HIDE-RECOVER value is 0.006130.

**Archive pointer:** `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` · SHA-256 `bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a` · prior note `GEMSDOESASS3 LWST-GeoConduit EXP3: 3D SPI+WijnsTheta+DualHGB300m 37654d B=2 HR=0.1111 SGMC=0.0657`.

Pages: [submission guide and executive summary](docs/executive-summary.html) · [overview](docs/index.html) · [independent review](docs/research/independent-review-20261028.md).

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

## Protocol rules in force

- Lane check: rank correlation above 0.90 or more than 70% of dots within 3 px of any registry raster is a duplicate. Checked on the surface and on the final dots, against all 386 focus-registry rasters, with no exemption.
- Leakage canary AUC above 0.90 fails (51 channels).
- Hypothesis numbers are labelled HOLDOUT-DTI or ORGANIZER-CONFIRMED.
- Budget: 3 candidate experiments or 2 hours. Controls are not counted. The lane count across E1 and the literal candidates may exceed the cap (IR-SASS3-41, open).
- Promotion is a separate selector step. No file is promoted here.

## Hypotheses

Ranked and untried, except E1 (H-SASS3-E, negative): H-SASS3-F (Gaussian-mixture boundaries on `tmi_hg`, `iso_grav_anom_hg`, `geod_shearrate`, `cond_surf`), H-SASS3-G (anisotropic Ripley's K on `ieq/deq_n100a15` seismicity), H-SASS3-H (Otsu ridges on `geod_dilaterate`; lowest priority). Details in the review. No hypothesis will be spent without HOLDOUT-DTI validation first. `main`'s BGK-PBE and unique-structural candidates were generated outside this review's protocol and have not been scored (see the table).

## Limitations and access needs

- **Needed from the owner:** a DrivenData account for any portal upload (the agent has none); the lattice and measure ruling (IR-SASS3-35, IR-SASS3-42); a decision on the experiment count across lanes (IR-SASS3-41); one of three weekly submissions; and confirmation of the sibling mapping to `buffedlizard55-lab` (IR-SASS3-09).
- **Data provenance:** the training data was restored from an owner mirror, with SHA-256 pins checked. The pins prove mirror consistency, not organizer provenance (IR-SASS3-14, IR-SASS3-43).
- **Hide-and-recover not run** for the current file. Only SGMC-CAL was run, so the file is not evaluated on the full protocol yet (blocker in the gates).
- **Margin:** the current file sits 1.0 point below the 70% limit, and the registry can change. Rerun the literal audit before any upload.
- **Leaderboard figures conflict:** the request cites 0.3195 and 0.4413. The live page fetched in this session shows #1 xiaofanhu 0.4544 and #2 cfld__ 0.3916 ([leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)). Public and private scores can differ (IR-SASS3-39).
- **Irregularities:** 43 entries in [`evidence/irregularities_ledger.json`](evidence/irregularities_ledger.json). New open items from this merge: IR-SASS3-35, 37, 38, 39, 40, 41, 42.

## Reproduce checks

Create the environment: `python3 -m venv .venv && .venv/bin/pip install numpy scipy scikit-learn rasterio pytest`.

1. `bash scripts/download_competition_data.sh` restores the 28 training files into `.cache/gems_data/` and checks their SHA-256 pins. Restore receipts are historical.
2. `.venv/bin/python scripts/fetch_registry_rasters.py --workers 4` fetches and SHA-verifies the 378 registry rasters.
3. `.venv/bin/python scripts/lattice_gap_check.py` writes `evidence/lattice_gap_check.json` (ceiling of about 21,713 dots under the literal rule).
4. `.venv/bin/python scripts/build_literal_candidate.py --variant dispersed --out <path.tif>` rebuilds the current file. It reproduces SHA-256 `d84217d5…fd752fdb`.
5. `.venv/bin/python scripts/literal_registry_audit.py <candidate.tif> <receipt.json>` runs the literal audit (about 150 s).
6. `.venv/bin/python scripts/verify_literal_candidate.py --write-card` checks the current file's bytes, receipts and canary, and writes the run cards.
7. `.venv/bin/python scripts/verify_all_gates.py --expect-blocked` must report exactly the two documented holdout blockers and exit 0.
8. `.venv/bin/python -m pytest -q`.
9. `.venv/bin/python scripts/build_review_site.py` refreshes the static pages (root and `docs/`).

`scripts/independent_review.py` is still broken in this checkout (IR-SASS3-38). Legacy page builders are disabled to prevent their outdated approval claims from returning.

## Official links

- [DrivenData competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Problem description (metric)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [GEMS Prize Official Rules (NLR PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

Not yet fetched, listed for manual review: USGS GeoDAWN (doi 10.5066/P93LGLVQ), epsg.io/32611, the Tversky index definition, gbcge.org INGENIOUS, and USGS ANSS.
