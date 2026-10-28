# Recomputed claims: GEMSDOESASS3, 2026-10-28

Companion to `docs/research/review-20261028.md` (independent review on `main`). This file recomputes the headline claims from the file bytes. **Decision: DO NOT SUBMIT** under the literal parallel-run registry-overlap rule (lattice 99.78% > 70%, IR-SASS3-19). Whether the synthetic lattice should count is an owner decision; no exemption is applied here.

Scope: the nine focus sites (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36), the LWST-GeoConduit GeoTIFF, and every headline claim in the README. Branch `arena/12a73fc6-gemsdoesass3`, base `86874b7`.

**Labels used throughout.** `HOLDOUT-DTI` = our own proxy evaluator (version, withheld positives and 95% CI given). `PROJECTION` = a regression output, never a score. `OWNER-REPORT` = a public score taken from the session listing, not an organizer receipt. `ORGANIZER-CONFIRMED` = none exists for any file in this review. `PROGRAMMATIC` = recomputed from the file bytes against the published spec.

---

## 0. Bottom line

1. **Format: valid. Submission: blocked.** `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` passes every format check (CRS, shape, transform, float32, single band, `nodata=None`, zero NaN or inf, values in [0,1], 37,654 positives, SHA-256, not on any catalogue cell). *PROGRAMMATIC.* Under the literal rule it **fails**: the calibration lattice `13gems_20261001_r13-lattice-s5_v2_nan-outside.tif` overlaps 99.78%. Excluding the lattice as degenerate gives max overlap 63.27%, which passes at 70%. That exclusion is an interpretation, not the protocol, and needs your decision.
2. **Score: NOT established.** The headline claim HR 0.111062 does **not** reproduce from the file. Recomputed static HR is **0.006130** [0.005175, 0.007123] (n = 22,232). *HOLDOUT-DTI, recomputed.*
3. **"Beats 0.2778 on both holdouts" is not supported.** SGMC-CAL reproduces (0.065702 [0.058992, 0.071240] vs champion 0.064121). The paired delta is +0.0016 with a stored CI of [−0.0055, +0.0089]. That CI spans zero, so the advantage is not demonstrated. (The paired CI itself was not re-derived here; see §5, IR-REV-03.)
4. **No candidate in this review is shown to beat 0.2778, and none is near the live #1 of 0.4544.** The flagship's linear PROJECTION is 0.258 (residual SD 0.055). That is a projection, not a score, and it sits below 0.2778.
5. **Leaderboard figures conflict.** The prompt cites 0.4413 as the leader and 0.3195 as "highest right now". The live DrivenData board (fetched 2026-10-28) shows #1 = **0.4544** (xiaofanhu), #2 = 0.3916, #3 = 0.3911. Neither 0.4413 nor 0.3195 appears. *ORGANIZER-PUBLIC.* Flagged for your review.
6. **The registry is less unique than its file count suggests.** 386 files contain only **213 distinct dot sets**. Three dot sets are filed under more than one site (IR-REV-16). Two sites' public scores attach to the same raster.
7. **Prior verdict withdrawn.** The verdict `promote` was self-issued and is not used. The run card is `negative`, `ok_to_submit: false`, matching `main`. The gates treat the score claims as WARN, not PASS, so CI stays green while the overclaim is visible.

---

## 1. Best submission per focus site

Method: `scripts/site_best_uniqueness.py`. For each site, the candidate is the registry raster with the highest SGMC-CAL proxy among rasters with 36,000–46,000 dots. That is the band where the proxy was validated (§4). Research-only, DO-NOT-SUBMIT, probe and placeholder files are excluded. Uniqueness is the maximum within-3-px overlap against every raster from a *different* repo. The lattice raster (99.8% overlap, degenerate for dense maps) is excluded from the maximum and reported separately.

| Site | File to download (sibling repo `docs/downloads/`) | Dots | Estimated score | Unique vs other GEMSDOE sites? (max overlap) | Notes |
|---|---|---:|---|---|---|
| **Flagship (this repo)** | `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` | 37,654 | **Not established.** SGMC-CAL 0.0657 (HOLDOUT-DTI, above the validated range); HR claim not reproduced | **Yes** — max 63.27% (GEMSDOE32 h47-ldgi) | Format-valid. Shipped in this repo, not in a sibling. |
| GEMSDOE24 | `gems24-xvar1-duplicate-semivariogram-20261026-7d909c75458c-nan.tif` | 37,654 | Not scored. Proxy 0.0777 (not a score) | **Yes** — 55.10% (vs HISTORICAL gems16-h16-1) | Proxy-only. |
| GEMSDOE25 | `gems25-apfl-piedmont-flexure-s3p0-k3p5-20261026-8aebdab87158-nan.tif` | 43,798 | Not scored. Proxy 0.0843 (not a score) | **Yes** — 54.85% (vs GEMSDOE31) | Proxy-only. |
| GEMSDOE27 | `gems27-all-increments-d2-8-h27-4-r1-t-v2-20261002-23ad46a4d7ba-allfinite.tif` | 41,507 | Not scored. Proxy 0.0633 | **No** — 97.15% (vs GEMSDOE31 union-b) | Near-duplicate of another site. Do not submit as unique. |
| GEMSDOE28 | `gems28-s19-ascp-20261026-dc717c1ab13b-allfinite.tif` | 37,654 | Not scored. Proxy 0.0972 is **above the validated range**, so no score is inferred | **No** — 74.90% (vs GEMSDOE31 h3-lidar-scarp) | Over the 70% threshold. |
| GEMSDOE30 | `gems30-CSR1-44090-20261026-502fb5948335-zeros.tif` | 44,090 | Not scored. Proxy 0.0649 | **Yes** — 60.63% (vs historical set) | Proxy-only. |
| GEMSDOE31 | `gemsdoe31-as1-lidar-antislope-38000dots-20261025-9b3afbc8-allfinite.tif` | 38,000 | Not scored. Proxy 0.0945 (out of range) | **No** — 76.65% (vs GEMSDOE28 s19-ascp) | Over the threshold. |
| GEMSDOE32 | `gems32-bayesopt-dilation-scarp-d28-20261004-nan.tif` | 45,000 | Not scored. Proxy 0.2567 — **out of regime** (dilated, blob-like map; see IR-REV-06) | **No** — 73.23% (vs GEMSDOE31 h3-lidar) | Its proxy is inflated and must not be read as a score. |
| GEMSDOE33 | `gemsdoe33-dpps-dipproj-persistence-37654-20261026-111ae96bb235-nan.tif` | 37,654 | Not scored. Proxy 0.0942 | **Yes** — 57.93% (vs GEMSDOE31) | Proxy-only. |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-nan.tif` | 38,854 | **OWNER-REPORT 0.2750** | **No** — 97.75% (vs a GEMSDOE24 mirror). Also 1,200 XOR dots from the champion (100% overlap) | Effectively the 0.2778 champion (see §2.1). |

Caveats for this table. The per-site candidate is the proxy's choice inside the band, and a different proxy would change it. Overlap is directional (candidate dots → other dots). "Unique" here means ≤ 70% within 3 px, the threshold the portal's uniqueness rule is assumed to use. Those rules are not verified against an organizer source; treat the threshold as a working assumption.

---

## 2. Direct questions

### 2.1 Why did GEMSDOE32 `h33-h33-2-b2` (0.2778) score highest?

Facts we can state:
- Public score 0.2778 (OWNER-REPORT). 37,654 dots (the B = 2 budget).
- Static HR 0.004515 [0.003816, 0.005262]; SGMC-CAL 0.064121 [0.056730, 0.071649]. *HOLDOUT-DTI, recomputed.*
- Within the 27 owner-reported points it sits in the top cluster of 14 with GEMSDOE36 anderson (0.2750), GEMSDOE28 h36-1 (0.2710), GEMSDOE28 h38-1 (0.2707) and GEMSDOE31 h27-4 (0.2708). Their SGMC-CAL values lie between 0.0630 and 0.0644.
- The anderson raster differs from the champion by 1,200 dots, and every champion dot lies within 3 px of an anderson dot. The 0.0028 public gap between them is therefore within the noise of a near-identical submission.

What we cannot establish: the README's "mathematical proof" of why 0.2778 won (§2.1 of the README) is narrative. We did not reproduce its mechanism, and this review does not confirm it. The reason the champion is highest among the nine sites is **not established**. What the data do support is the ordering: SGMC-CAL tracks public score (see §4).

### 2.2 Is > 0.2778 achievable?

Not demonstrated. Not ruled out.
- The one candidate that plausibly exceeds the champion on the proxy is the flagship, by 0.0016 (SGMC-CAL). That margin is inside the CI, and the flagship's proxy is above the validated maximum (0.0644), so its score is extrapolated.
- Within the validated band, no unique candidate in the registry has a proxy above the champion's.
- The gap to the live #1 (0.4544) is far outside the validated range. No candidate here is close to it on any proxy we trust.
- The only way to establish a score is a portal submission. Slot selection is a separate selector step and was not performed here.

---

## 3. Untested geological hypotheses

README §3 lists four ranked hypotheses. **Only H-SASS3-A (LWST-GeoConduit) was implemented, and it is the flagship.** H-SASS3-B (AGAD LiDAR micro-scarps), H-SASS3-C (RACC radiometric and MT clay-cap edge) and H-SASS3-D (DD-SeisFault relocated microseismicity planes) are **untested**. No expected DTI gain has been estimated for them, and none has been validated on a spatially blocked holdout. This review used none of the 3-experiment or 2-hour budget. The sources named in §3 are the USGS ComCat FDSN API (linked in README §3) and the DOE GeoDAWN and GDR datasets. Those were not re-verified in this review (see §6).

---

## 4. Validation of the proxies (what we trust, and what we don't)

Public-board calibration, 27 owner-reported scores matched to local rasters (`evidence/proxy_validation_20261028.json`, post-fix):

| Proxy | Spearman ρ vs public | 95% CI | Kendall τ | Status |
|---|---:|---|---:|---|
| SGMC-CAL (`GEMSDOE32-SGMC-CAL-v3.0`) | **0.843** | [0.589, 0.968] | 0.708 | Ranks the public board. Validated range: SGMC-CAL 0.0579–0.0644 (dots 11k–174k, median 41,865). |
| Static HR (`HIDE-RECOVER-v3.0`, static mask) | 0.059 | [−0.390, 0.443] | — | **Does not rank the board.** Do not use as a promotion gate. |

Within the top cluster (public ≥ 0.20, n = 14): ρ(SGMC-CAL) = 0.934; ρ(static HR) = −0.395.

Caveats:
- The first run gave ρ = 0.808 [0.530, 0.957]. Six listing rows then received file-matching tokens, and ρ rose to 0.843 (IR-REV-05). The matching is therefore a sensitivity, not a fixed fact.
- The linear map is public ≈ 5.01 × SGMC-CAL − 0.072, residual SD 0.055. It is a **PROJECTION** and is never reported as a score.
- The proxy is count-based on the FP side and is not the official distance-weighted metric. It is inflated for sparse or blob-like maps (IR-REV-06).

---

## 5. Claim-by-claim verification

| Claim (source) | Check performed | Result | Label |
|---|---|---|---|
| HR 0.111062 for shipped TIF (README, run card) | Recomputed static HR from the shipped bytes with `gems32.holdout` (B-visible = 2 px) | **NOT REPRODUCED** — 0.006130 [0.005175, 0.007123], n = 22,232 | HOLDOUT-DTI (recomputed) |
| Champion HR baseline 0.099202 (README) | Recomputed the file it names | **MISLABELED** — that is the GEMSDOE25 D2.8 raster's static HR. Champion static HR = 0.004515 | HOLDOUT-DTI (recomputed) |
| SGMC-CAL 0.065702 shipped | Recomputed | **REPRODUCED** — [0.058992, 0.071240] | HOLDOUT-DTI (recomputed) |
| SGMC-CAL 0.064121 champion | Recomputed | **REPRODUCED** — [0.056730, 0.071649] | HOLDOUT-DTI (recomputed) |
| Paired Δ SGMC vs champion +0.0016, CI [−0.0055, +0.0089] | Single values recomputed; **paired CI taken from the stored receipt, not re-derived** | Span zero per stored CI | HOLDOUT-DTI (stored) |
| TIF format and grid | All format checks recomputed | **PASS** — 13/13 plus SHA | PROGRAMMATIC |
| Uniqueness "386 rasters, max 63.27%" | Recomputed overlap for every registry raster | **PASS** at 70%; max 63.27%. Dot-set duplicates: 213 distinct of 386 | PROGRAMMATIC |
| `IR-SASS3-01`: NaN outside footprint causes the portal's [0,1] error | Scanned all 386 rasters for finite values outside [0,1], inf, −9999 | **NOT SUPPORTED** — 181 contain NaN; 0 have out-of-range finite values, inf, or −9999. NaN-encoded files were scored on the portal (OWNER-REPORT). Actual trigger **unknown** | PROGRAMMATIC |
| Leakage canary 51/51 ≤ 0.90 (worst curv_s2 0.5883) | Stored report only; **not re-run** | Claimed | CLAIMED |
| Live #1 = 0.4544 | Fetched DrivenData leaderboard | Confirmed on the fetch date | ORGANIZER-PUBLIC |
| Metric: distance-weighted Tversky, α = 0.2 (FP), β = 0.8 (FN), R = 300 m, values in [0, 1] | Fetched DrivenData competition page | Confirmed | ORGANIZER-PUBLIC |
| "Predicted values must be in range [0, 1]" | No portal receipt for any file | Unresolved | — |

---

## 6. Irregularities

Full entries: `evidence/irregularities_ledger.json` (IR-SASS3-01 and IR-REV-01 to IR-REV-17).

- **IR-SASS3-01** (root cause of the portal error): not supported by the registry scan. Severity lowered to "root cause not reproduced".
- **IR-REV-01** (HIGH): headline HR 0.111062 does not reproduce. It comes from per-fold OOF masks, not the file.
- **IR-REV-02** (HIGH): 0.099202 labelled as the champion baseline is GEMSDOE25 D2.8's static HR.
- **IR-REV-03** (HIGH): "beats champion on both, CI > 0" is not established. The paired CI was not re-derived here.
- **IR-REV-04** (HIGH): gates and the `promote` verdict were self-referential.
- **IR-REV-05** (MEDIUM): calibration moves with file-matching (0.808 → 0.843).
- **IR-REV-06** (HIGH): the SGMC-CAL proxy is inflated out of range (GEMSDOE36 h6 offcatalog 0.3426 at 24,881 dots; GEMSDOE32 dilation 0.2567 at 45,000 dots). Neither has a public score; a linear map would place them above the live #1, which is implausible.
- **IR-REV-07** (MEDIUM): 51 of 279 band rasters have a higher proxy than the flagship. The flagship's 0.0657 is above all public-scored files (max 0.0644) but within CI.
- **IR-REV-08** (HIGH): uniqueness margin is narrow. The flagship and champion share 37,654 dots; directional overlap is 41.53% (shipped → champion) and 35.32% (champion → shipped).
- **IR-REV-09** (MEDIUM): five of nine per-site proxy-best candidates are not unique across sites (§1).
- **IR-REV-10** (HIGH): prompt leaderboard figures (0.4413, 0.3195) conflict with the live board (0.4544). Flagged for you.
- **IR-REV-11** (MEDIUM): eight HISTORICAL_SCORED registry paths return 404 at the listed location and resolve only through `data_manifest.json`. Two entries are excluded (GEMSDOE31 csdu-stepover nan: malformed; GEMSDOE36 FORMAT_TEST: fixture).
- **IR-REV-12** (LOW): `run_lwst_experiments.py` and `run_gsd_hua_experiments.py` still write `verdict: promote`. Re-running them would restore the overclaim.
- **IR-REV-13** (LOW): stale branch field in the run card.
- **IR-REV-14** (LOW): the portal note cited the unreproduced HR. Replaced, and the raster is byte-identical.
- **IR-REV-15** (LOW): max |Spearman| differs between documents (0.1255 vs 0.1238). Both are below 0.90.
- **IR-REV-16** (HIGH): cross-site exact duplicates. 40,199 dots (GEMSDOE28 ↔ GEMSDOE31, both public 0.2708); 44,090 dots, the D2.8 reference (GEMSDOE24, 30, 32, 33; public 0.2600); 60,069 dots (GEMSDOE24 ↔ GEMSDOE30).
- **IR-REV-17** (MEDIUM): 386 files are 213 distinct dot sets. Most duplicates are nan/zeros encodings within one site.

---

## 7. What changed in this session

- **Gates** (`scripts/verify_all_gates.py`): the two "beats champion" checks are WARN items recomputed from `evidence/independent_verification_20261028.json`. The literal registry-overlap rule from `main` stays blocking. `ok_to_submit` still requires `verdict == "promote"`, so it stays false.
- **Run cards** (4 copies): kept on `main`'s `negative` / `ok_to_submit: false`. Added `score_status`. Replaced the note that quoted the unreproduced HR with a factual 122-character note.
- **Builders**: headline text, hero, KPI notes, README header and HOLDOUT rows now read the recomputed receipt. Core Values section added to the README. `build_docs_pages.py` was already broken at HEAD (stale keys); it is patched to run, but it is a **legacy generator that overwrites the same pages**. `build_site.py` is canonical and must run last (README pipeline).
- **Tests**: `tests/test_lwst_submission.py` and `tests/test_gemsdoesass3_gates.py` updated to the new contract. 10/10 pass with `GEMS_DATA_DIR=/tmp/gems_data`.
- **New evidence**: `independent_verification`, `proxy_validation`, `registry_sgmc_rank`, `site_best_uniqueness`, `registry_exact_duplicates`, `registry_value_scan`, `registry_overlap_vs_shipped`, `public_score_calibration_pre_fix`, `holdout_eval_*`, `pairwise_overlap`. Scratch scripts are in `scripts/review_20261028/`; those use `/tmp` paths.
- **Restored data**: `data/restore_receipt.json` reverted. Competition inputs were restored from pinned sources and SHA-verified against `registry/data_manifest.json`. They were **not** downloaded through DrivenData login, so the original DrivenData files were not independently checked.

---

## 8. Limitations and suggested next steps

1. **Get a portal receipt.** The only way to turn a proxy into a score is a portal submission. Slot selection is your call (separate selector step).
2. **Replace the proxy's FP term** with the official distance-weighted FP, and re-calibrate on more public scores. Until then, rank only inside the 36k–46k band.
3. **Re-derive the paired CI** for the SGMC delta from the raw blocks, not the stored receipt.
4. **Resolve cross-site duplicates** (IR-REV-16) with the organizer or the portal: which site does each duplicated score belong to?
5. **Stop the pipelines** from writing `promote` (IR-REV-12).
6. **Test hypotheses B–D** on a spatially blocked holdout within a fresh 3-experiment budget, before any slot.
7. **Verify external links not fetched in this session:** NLR rules PDF `https://docs.nlr.gov/docs/fy26osti/96647.pdf`; reference solution `https://github.com/drivendataorg/gems-prize-reference-solution`; USGS SGMC `https://doi.org/10.3133/ds1052`; USGS GeoDAWN `https://doi.org/10.5066/P93LGLVQ`; DOE GDR `https://gdr.openei.org/submissions/1391`; EPSG:32611 `https://epsg.io/32611`. Confirm each before citing.
8. **Confirm the leaderboard figure** you intend to beat (0.4413, 0.4544 or 0.3195).
9. **Re-run the leakage canary**; this review used the stored report.

---

## 9. Run card

```json
{
  "run_card_version": "review-20261028",
  "date_utc": "2026-10-28",
  "branch": "arena/12a73fc6-gemsdoesass3",
  "submission_file": "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif",
  "sha256": "bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a",
  "verdict": "negative",
  "ok_to_download": "archive_only",
  "ok_to_submit": false,
  "score_status": "NOT_ESTABLISHED",
  "format_valid": "PROGRAMMATIC",
  "literal_registry_overlap_rule": {"result": "FAIL", "lattice_within3px": 0.997849, "limit": 0.70, "ledger": "IR-SASS3-19"},
  "scores": {
    "hr_claimed_0p111062": "NOT_REPRODUCED",
    "hr_recomputed_static": {"value": 0.006130, "ci95": [0.005175, 0.007123], "n_withheld": 22232, "label": "HOLDOUT-DTI"},
    "sgmc_cal_recomputed": {"value": 0.065702, "ci95": [0.058992, 0.071240], "n_withheld": 62703, "label": "HOLDOUT-DTI"},
    "champion_sgmc_cal": {"value": 0.064121, "label": "HOLDOUT-DTI"},
    "paired_delta_sgmc": {"value": 0.001581, "ci95_stored": [-0.005523, 0.008911], "significant": false}
  },
  "projection_not_a_score": {"linear_public_on_sgmc_cal": 0.258, "residual_sd": 0.055, "label": "PROJECTION"},
  "public_board_calibration": {"n": 27, "rho_sgmc_cal": 0.843, "rho_sgmc_cal_ci95": [0.589, 0.968], "rho_static_hr": 0.059, "label": "OWNER-REPORT"},
  "uniqueness": {"registry_files": 386, "distinct_dot_sets": 213, "max_within3px_flagship_excluding_lattice": 0.6327, "threshold": 0.70, "cross_site_duplicate_groups": 3},
  "leaderboard": {"live_1st": 0.4544, "2nd": 0.3916, "3rd": 0.3911, "prompt_cited": [0.4413, 0.3195], "label": "ORGANIZER-PUBLIC"},
  "experiments_used": {"new": 0, "budget": 3},
  "irregularities": "IR-SASS3-01 (root cause not reproduced); IR-REV-01..17",
  "open_items": ["owner decision on whether the synthetic lattice counts (IR-SASS3-19)", "portal receipt", "paired CI re-derivation", "FP term replacement", "hypotheses B-D untested", "external link verification"]
}
```
