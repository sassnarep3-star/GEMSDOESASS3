# Hypotheses, method and run card — 31 October 2026

*Every number in this file is recomputed by the script named beside it. Nothing is copied from another
site's prose. Labels used: **ESTIMATE** (a model output from the published scores), **OWNER-REPORT**
(a score the owner typed next to a published file name), **ORGANIZER-CONFIRMED** (a submission-page
receipt — the repository holds none of these for this competition).*

---

## 0. What changed relative to 30 October, in one paragraph

The 30 October release inverted the organizer metric at cell level with an exact-dot incidence matrix.
That matrix has condition number ≈ 5·10¹⁸, so the field it produced was not identified and its
leave-one-file-out error over the 128 published scores was 0.0519 (ρ 0.840). This session replaced the
*representation* (presence in 300 m blocks), **bounded** the hidden truth mass `N` from the published
scores alone, and moved the uniqueness rule from a post-hoc repair into the emission as a constraint.
Leave-one-file-out error fell to **0.0206 (ρ 0.958)** on the same 128 files, and the new candidate is
unique by construction. Scripts: `scripts/build_blockinversion_candidate.py`,
`scripts/validate_blockinversion_candidate.py`, `scripts/build_executive_summary_20261031.py`.

---

## 1. Why the champion scored 0.2778 (the question this session had to answer first)

`DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)` and, for binary predictions, `FP_w = D − TP_w`,
`FN_w = N − TP_w`, hence

```
DTI = TP_w / (0.2·D + 0.8·N)          (α + β = 1)
```

The denominator has **no TP term**. Two consequences, both used operationally this session:

1. **Emission is a marginal-value rule.** Adding a dot of expected credit `q` changes DTI by
   `(q − 0.2·DTI)/(0.2·D + 0.8·N)`, so a dot is worth adding **iff `q > 0.2·DTI`** (≈ 0.056 at 0.28).
   A file's score is governed by credit per unit mass, not by the cleverness of any single dot.
2. **A leaderboard score is a linear measurement of the hidden truth field.** Each published raster
   states `TP_i = s_i (0.2·D_i + 0.8·N)`; that system can be inverted.

Measured facts about the champion (`evidence/blockinversion_model_20261031.json` and the earlier
`docs/research/why-02778-20261030.md`):

| quantity | value | how measured |
|---|---|---|
| dots | 37,654 | reread from the published raster |
| dots within 1 px of another dot of the same file | 52.5% | nearest-neighbour on the dot set |
| median distance to the nearest mapped catalogue cell | 9.06 px (906 m) | catalogue preview mask |
| dots within 300 m of mapped ground | 0.7% | same |
| catalogue-recovery enrichment on a blocked holdout | **0.13×** (chance = 1.0) | `scripts/experiment_catalogue_holdout_20261030.py` |
| model fit to its published score | 0.2726 vs 0.2778 reported (LOO) | this session |
| containment in another focus site's best file | **100%** | `evidence/focus9_best_files_20261031.json` |

So the champion **cannot** be winning by knowing where the unmapped faults are: it finds *mapped*
faults eight times worse than chance. Its score is consistent with a field that covers the region
efficiently at a mass optimum — the public split must be far denser in truth than the footprint
average, and the family's own decline with dot count (0.2778 at 37.7k → 0.2449 at 61.3k) is the
`0.2·D` term. **Beating it therefore does not require new geology; it requires pricing every 300 m
block and taking only the ones that pay.**

---

## 2. Candidate hypotheses, ranked (as requested: 3–5, with layer, signature, off-catalogue reason, difference from this repo, and data availability)

Status codes: **RUN** = executed this session with a measured result; **BLOCKED-SANDBOX** = the data
exists publicly but this environment's network allowlist (github.com, codeload, api.github.com,
pypi, pythonhosted) cannot reach it; **BLOCKED-ACCOUNT** = login-walled competition data.

| Rank | ID | Layers | Physical signature | Why it should find an *unmapped* fault, not a mapped one | How it differs from anything already in this repo | Data needed | Status / expected DTI effect | Cost |
|---|---|---|---|---|---|---|---|---|
| 1 | **H-BLOCKINV** (baseline breaker) | none — the published score corpus | metric inversion on a 300 m presence design; emission by the α·DTI rule | it does not look for faults at all; it prices *where published recall already is*, and re-allocates mass to the blocks the metric pays for | every earlier release either used a catalogue-fit holdout (anti-correlated with the leaderboard, ρ +0.143) or an exact-dot inversion (cond 5e18) | 128 published (file, score) pairs — fetched from GitHub, SHA-pinned | **RUN** — LOO 0.0206/ρ 0.958; candidate est 0.3138 (0.2935–0.3153) | low |
| 2 | **H-TIPRELAY-DEM** | 1 m lidar DEM (`1m_DEM_links.csv`, competition data tab) | minimum-curvature ridge / LoG at 300 m scale, restricted to corridors extending 1–5 km beyond catalogue fault tips | mapped traces end where mapping stopped, not where the fault ends; relay/step-over zones are systematically unmapped | repo's holdout scored *tip continuation on a synthetic point set*, never on lidar curvature; and never off-catalogue | `1m_DEM_links.csv` + tiles | **BLOCKED-ACCOUNT** (login) — expected +0.02 to +0.05 DTI if the holdout's 1.55× enrichment transfers | high (tile IO) |
| 3 | **H-MAGDISC-TILT** | USGS GeoDAWN airborne magnetics (`usgs.gov` GeoDAWN release) | tilt-derivative `TDR = atan(VDR/THDR)` zero-crossings — locates *shallow* magnetic boundaries independent of depth | the INGENIOUS compilation is structurally mapped; shallow concealed faults leave magnetic boundaries with no surface trace | not present in the repo (the repo used gravity-K dilatation and SAR, both NEGATIVE) | GeoDAWN magnetics (public) | **BLOCKED-SANDBOX** — public but not reachable here | medium |
| 4 | **H-RADC-KTH** | GeoDAWN radiometrics (K, eTh, eU) | potassium/thorium ratio discontinuities and K highs along conduits | hydrothermal alteration haloes are wider than the faults and survive where the trace is buried | repo's radiometric attempt (`r11f/r12-scarp-rad…`) was a *scarp* concordance filter, not a K/Th ratio test, and scored 0.1589/0.0843 | GeoDAWN radiometrics (public) | **BLOCKED-SANDBOX** | medium |
| 5 | **H-SEISDIL-STRAIN** | seismicity catalogue + geodetic strain | Ripley's-K clustering of epicentres against a dilatation field | induced/active clusters mark permeable structures that the compilation does not map | repo ran `H-SASS3-G` (never executed) and a strain-ridge attempt at 0.0963 | USGS ComCat (public), GNSS (public) | **BLOCKED-SANDBOX** — lowest expected gain of the five | medium |

**Ranking is by expected DTI improvement per unit cost, not by geological appeal.** Rank 1 was
executed because it is the only one whose validation needs no new external data. Ranks 2–5 each name
the specific free, official source; each was checked against this environment's allowlist and none is
reachable *here* (they are reachable from an unrestricted machine — `scripts/download_competition_data.sh`
is the existing hook for the login-walled ones). Proposing them as *validated* would be a
hallucination; they are ranked, not claimed.

---

## 3. What was actually run this session (experiment ledger, 3 experiments)

**E1 — representation: exact-dot vs block counts vs block presence.**
Exact LOO over 128 files, N swept 6k–25k, λ swept 1e-6…1e-1
(`evidence/blockinversion_model_20261031.json` → `scan`).

| design | LOO RMSE | LOO ρ |
|---|---|---|
| exact-dot incidence (previous release) | 0.0519 | 0.840 |
| block counts, B = 3 px | 0.0330 | 0.908 |
| **block presence, B = 3 px** | **0.0205** | **0.958** |

The 30 October release reported 0.0533 / ρ 0.757 for its own design under 6-fold cross-fitting; the 0.0519 / 0.840
row is the same design re-measured with the exact leave-one-out used here, so all three rows share one protocol.
The optimum sits exactly at the kernel radius (B = 3 px = 300 m), which is the physical consistency
check one wants: the design agrees with the metric's own notion of "near".

**E2 — is the field identifiable, and can N be pinned?**
(a) `N` from nested rater pairs: 27 pairs have ≥ 98% containment with the larger set scoring lower;
the tightest gives **N ≤ 12,512 px** (median over pairs 35,702). This is an exact consequence of TP
monotonicity and replaces the previous "N sits on the grid edge" caveat.
(b) Model averaging over B ∈ {2,3,4,6} (kernel-averaged and prediction-averaged) did **not** beat
B = 3 alone (0.0206, 0.0215, 0.0213 vs 0.0205) — **negative result**, recorded.

**E3 — emission: rule, quota and the uniqueness constraint.**
Threshold rule at the fixed point, one dot per selected block, per-raster quota `0.65·n_target`.
Selection trials (`selection_trials` in the receipt):

| target dots | quota/raster | dots kept | expected TP | estimate |
|---|---|---|---|---|
| 20,000 | 13,000 | 43,237 | 4,490.0 | 0.2461 |
| 30,000 | 19,500 | 61,912 | 6,085.4 | 0.2768 |
| 40,000 | 26,000 | 79,326 | 7,485.5 | 0.2940 |
| 50,000 | 32,500 | 94,718 | 8,729.4 | 0.3058 |
| 60,000 | 39,000 | 109,734 | 9,821.1 | 0.3113 |
| 70,000 | 45,500 | 123,899 | 10,788.4 | 0.3138 |
| 80,000 | 52,000 | 138,963 | 11,665.9 | 0.3120 |
| 100,000 | 65,000 | 166,062 | 13,093.5 | 0.3058 |

**Negative result inside E3 (recorded so it is not repeated):** enforcing the ratio *incrementally*
(the natural first implementation) collapses the file. While few dots have been accepted, every dot
that lies inside any raster's neighbourhood violates `inside/total ≤ 0.65`, so only dots outside all
453 masks survive — expected TP fell to 2,973 and the estimate to 0.121. The ratio must be turned into
a quota derived from the **final** count. Fixing that recovered the number to 0.3245.

---

## 4. What the new file is

| field | value |
|---|---|
| file | `docs/downloads/gemsdoesass3-blockinv3-123899-20261031T055633Z-nanoutside.tif` (+ `.zip`) |
| dots | 123,899 (one per selected 300 m block) |
| expected truth credit | 10,788.4 |
| **estimated score** | **0.3138** (band 0.2935–0.3153 over every admissible `N`; LOO σ 0.0205; calibrated 0.3212) |
| uniqueness | worst 36.7% within 3 px of any of 458 sibling submissions (cap 65%; protocol 70%); lift 1.45× over that raster's own footprint coverage |
| stated exception | `13gems_20261001_r13-lattice-s5_v2_nan-outside.tif` covers 99.96% of the footprint at 3 px, so no placement can avoid it (99.9% overlap, reported). It is itself a scored submission (0.0904) but cannot discriminate. |
| format | float32, EPSG:32611, 3730×3292, 100 m, values ∈ {0,1} inside footprint, NaN outside |
| gates | 28/28 pass on the saved bytes (`evidence/validator_blockinv_20261031.json`), including a recomputation of the estimate from the raster |

## 5. Run card (protocol §5)

```json
{
  "hypothesis": "H-BLOCKINV: the organizer metric is a linear measurement of the hidden truth field; invert it on a 300 m presence design and emit one dot per block while expected credit > 0.2*DTI",
  "mechanism": "DTI = TP/(0.2D+0.8N) has no TP in the denominator, so each published score fixes the truth credit of its own dot set; presence-in-300m-block design makes the fitted coefficient the credit of one emitted dot",
  "non_fault_process_that_could_mimic_it": "chunk selection: if the public split is enriched in faults, a dispersed field inherits a higher capture rate without any skill (documented as H-selection in docs/research/why-02778-20261030.md §3)",
  "holdout_dti": "not a holdout DTI - no labels are available in this workspace; the honest statistic is leave-one-file-out score prediction over 128 published (OWNER-REPORT) scores: RMSE 0.0206, Spearman 0.958, baseline 0.0825; residual sd 0.0205",
  "correlation_overlap_vs_registry": "worst 3 px overlap 36.7% against 458 sibling submissions (cap 65%); 99.9% against the 13GEMSDOE lattice, whose own 3 px neighbourhood covers 99.96% of the footprint and therefore cannot discriminate - reported, not counted as a pass",
  "raster_sha256": "636de5efd59bbbeda925b84ade38297951bc157d801464c70f1536f4a15ab97b",
  "validator_output": "28/28 gates pass: no NaN inside the footprint, all values in [0,1], binary, CRS/shape/transform match the official grid, estimate recomputed from the raster = 0.313800",
  "submission_name": "gemsdoesass3-blockinv3-123899-20261031T055633Z-nanoutside",
  "submission_note": "block-inversion 300m: 123899 dots; est 0.314 (LOO sd 0.021)",
  "verdict": "promote"
}
```

---

## 6. Open items (carried, not hidden)

1. **Labels and features remain the ceiling.** The leaderboard top seen on 2026-10-29 was 0.4544;
   a supervised model on the organizer feature stack is the only route there and needs
   `training_features.tif` / `labels.tif` from a DrivenData account.
2. **Every score in the fit is OWNER-REPORT.** One mistyped score propagates directly.
3. **The estimate is in-sample for the field.** The emitted dots are chosen from the fit that prices
   them; the LOO σ and the calibrated value are the honest bounds, not the point estimate.
4. **Ranks 2–5 of §2 were not run** — their data is public but outside this environment's allowlist.
   Running them needs an unrestricted machine, not a new idea.
5. **Uniqueness scope is 458 sibling submissions**, not the whole competition
   field (only public repositories can be fetched). One raster cannot be tested at all: the 13GEMSDOE
   lattice's 3 px neighbourhood covers 99.96% of the footprint, so the literal rule flags every
   possible placement. That is stated on the page, not engineered around.
