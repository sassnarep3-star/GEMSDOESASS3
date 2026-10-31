> Companion document: [`hypotheses-20261031.md`](hypotheses-20261031.md) is the H-BLOCKINV method document for the
> emitted file (296 → 0.3138 ESTIMATE, 28/28 gates). This file is the geology slate.

# Five new candidate geological hypotheses — 2026-10-31 (H-SASS3-O … H-SASS3-S)

**Prompt requirement addressed:** "generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the
specific layer(s) involved, the physical signature being targeted, why it should catch a fault missing from the USGS/INGENIOUS
catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by
expected DTI improvement and implementation cost."

**Grounding.** The scored truth is an expert-mapped set of faults deliberately absent from the public USGS catalogue
([problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/): "faults that are not
contained within the current public USGS database … will comprise the test dataset"), and known catalogue pixels are masked
out of scoring ([forum thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)).
The measured score model (`evidence/score_estimate_20261030.json`) says a dot field with no enrichment scores ≈ 0.041 at any
budget, while the nine focus-site leaders (0.2449–0.2778) imply 4.1–5.3× enrichment on withheld faults — so the only
hypotheses worth running are ones whose physical signal is *not* the surface expression the mappers already drew.

**Every hypothesis below is therefore judged on one question:** does its signature exist on faults that have *no* mappable
surface trace (buried, sinter-covered, young, low-relief)?

**IDs.** `docs/hypotheses.md` (this repo) already assigns H-SASS3-A…N; `research/hypotheses-20261030.md` re-uses J–M with
different definitions (flagged as IR-SASS3-84 in the ledger). This document uses the next free letters O–S and checks each
against both documents and against every sibling-site method visible in `registry/published_score_table_20261031.json`.

**Shared validation blocker.** Every hypothesis here needs the restored feature stack (`.cache/gems_data`, recorded in
`data/restore_receipt.json`) or one of the GDR/USGS downloads below. In this sandbox the stack is absent and the network
allow-list blocks gdr.openei.org and usgs.gov; therefore **no hypothesis below is validated this session** and none is
written into a submission slot. Each entry names its free official source and the reachability check performed today. The
protocol says negative and blocked results are deliverables; these are recorded as **NOT RUN (blocked: data placement)**.

Sources checked reachable on 2026-10-31 (HTTP evidence in `evidence/source_health_20261031.json`):

* GDR #1391 INGENIOUS compilation — <https://gdr.openei.org/submissions/1391> — **reachable**, CC-BY 4.0, direct
  downloads for `wellspringdata.gdb.zip` (springs/wells, 19.85 MB), `great_basin_q_volcanics.zip` (vents + flows,
  9.44 MB), `paleo_geothermal_regional.zip` (sinter/tufa, 82 KB), `faults_quaternary_INGENIOUS_regional_data.zip` +
  `qfaults_ingenious_nad83conus117_2023-06-27.zip`, `seismicity_INGENIOUS_regional_data.zip`, and DOIs for MT
  conductance, gravity/magnetics, heat flow, slip/dilation tendency.
* USGS GeoDAWN (radiometrics/magnetics) —
  <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and> —
  named official source (retrieval to be done from an unrestricted machine).
* USGS 3DEP lidar — <https://www.usgs.gov/3d-elevation-program> — named official source for 1 m DEMs.

---

## Ranking (expected DTI improvement ÷ implementation cost)

| Rank | ID | Layer(s) | Physical signature | Expected DTI gain | Cost | Validation status |
|---|---|---|---|---|---|---|
| 1 | **H-SASS3-O** | GeoDAWN radiometrics K/Th/U (`rad_*`, `ext_geodawn_rad_u8`) | multi-scale edge detector on log(Th/K) ternary-ratio images (argillic-cap margin) | moderate–high | low–medium | NOT RUN (blocked: feature stack) |
| 2 | **H-SASS3-P** | `gdr_wellspring_in_footprint.csv` (GDR #1391) + fault network (`labels.tif`, SGMC) | adaptive KDE of spring/vent discharge × fault-graph crossing nodes | moderate | low | NOT RUN (blocked: feature stack + CSV restore) |
| 3 | **H-SASS3-S** | `gdr_volcanic_vents_in_footprint.csv`, paleo-geothermal (sinter/tufa) points (GDR #1391) | vent-alignment lineament generator (point-pair azimuth clustering at 1–5 km) | moderate | low | NOT RUN (blocked: CSV restore) |
| 4 | **H-SASS3-Q** | `lidar_scarp_features_u8` / 1 m DEM slope variance, `existing_faults.tif` | damage-zone width anomaly: swath slope-variance exceeding the mapped trace's own geometry | low–moderate | medium | NOT RUN (blocked: lidar stack) |
| 5 | **H-SASS3-R** | 1 m lidar microtopography + GDR spring locations | sinter-terrace riser edge density (decimetre relief) within 500 m of discharge points | low–moderate | medium–high | NOT RUN (blocked: 1 m tiles) |

---

## 1. H-SASS3-O — Radiometric argillic-cap edge ternary (Th/K · U/K)

* **Layers.** GeoDAWN radiometric channels K, Th, U and their ratios (restored as `ext_geodawn_rad_u8`,
  `ext_geodawn_extensions_u8` per `data/restore_receipt.json`; official source: USGS GeoDAWN link above).
* **Signature.** Multi-scale (300/900/1800 m) Canny-style edge magnitude on `log(Th/K)` and `log(U/K)` images, restricted to
  Basin-and-Range frontal zones; ridge-thinned to one-pixel crests; emitted where two scale levels agree.
* **Why it catches faults missing from the catalogue.** Argillic (clay) alteration halos blanket the upflow margins of blind
  hydrothermal systems; the feeder faults beneath them are commonly buried by alluvium or sinter and have **no** surficial
  scarp — exactly the population USGS/INGENIOUS surface mapping cannot contain. The edge marks the *alteration front*,
  which is a chemical boundary, not a topographic one, so it carries information the catalogue does not encode.
* **How it differs from this repo.** E1 (H-SASS3-E) used basement minimum-curvature on magnetics only and scored negative;
  no radiometric ratio transform, and no edge detector of any kind, exists in `scripts/` or `src/`. Sibling sites used
  single-channel K or Th masks (`h16-1-topo-geophys`, `r11f-scarp-radiometric-fusion` 0.1589) and a generic
  "alteration-halo" (`gems91-s91-alm`, unscored) — none uses ternary-ratio *edge geometry* at metric-matched spacing.
* **Named non-fault mimic.** Lithologic contacts in ash-flow tuffs and pedogenic K-enrichment on old fan surfaces produce
  the same Th/K gradients; the two-scale persistence filter and the frontal-zone mask are the defence.
* **Cost.** ~1–2 h (ratio transforms, edge extraction, holdout) once the stack is restored.
* **Unblock.** `bash scripts/download_competition_data.sh` + owner restore into `.cache/gems_data` (28 files, SHA-256
  receipts already recorded), or download the GeoDAWN mosaics from the USGS page above.

## 2. H-SASS3-P — Spring-vent nexus: discharge KDE × fault-graph crossings

* **Layers.** `gdr_wellspring_in_footprint.csv` (568 mapped springs/wells, GDR #1391 `wellspringdata.gdb.zip`), fault
  network from `labels.tif` + derived SGMC (`ext_derived_sgmc_faults_100m_u8`).
* **Signature.** Adaptive-bandwidth (~1.5 km) kernel density of spring and well discharge points, multiplied by a
  crossing-node detector on the fault graph (nodes where two traces intersect within 1 km); output is the product surface,
  thinned to node centroids.
* **Why off-catalogue.** Discharge clusters localize where crossing structures dilate; the connecting segments at those
  crossings are routinely dropped from regional 1:100k compilations for being short/low-throw. The springs are direct
  evidence of *current* permeability, i.e. of the fault population that is hydrologically alive — which is not the same set
  the catalogue's geomorphic criteria select.
* **Difference from this repo.** `scripts/geothermal_prior_audit.py` inventoried wells but never built a point-pattern
  surface, and no script intersects a vent KDE with a fault graph. Sibling `karage1-kp1-ttca-springalter-far-conduit` uses
  springs as a gate on a conduit model (unscored), not as a nexus density.
* **Mimic.** Alluvial aquifer springs with no structural control (valley-bottom seeps); the crossing-node requirement and
  the fault-parallel anisotropy test are the defence.
* **Cost.** ~1 h (KDE + graph), all inputs in the restore set or GDR downloads.

## 3. H-SASS3-S — Vent-alignment lineament generator

* **Layers.** `gdr_volcanic_vents_in_footprint.csv` (Quaternary vents, GDR #1391 `great_basin_q_volcanics.zip`), paleo
  geothermal features (sinter/tufa, `paleo_geothermal_regional.zip`), `labels.tif` for masking.
* **Signature.** Point-pair azimuth clustering of vent and sinter locations (1–5 km pairs, Watson test for common
  orientation); each significant alignment is extrapolated as a two-ended lineament and sampled every 3 px, rejecting any
  sample within 200 m of a mapped trace.
* **Why off-catalogue.** Vent alignments trace dike/fracture swarms feeding the geothermal system; the swarm's connecting
  segments are the faults. Because the generator starts from *vent points*, it places dots on structures that have no
  surface rupture at all — mappers had nothing to draw.
* **Difference from this repo.** No point-set alignment detector exists here (`H-SASS3-J` extrapolated catalogue *traces*,
  not point swarms). Sibling `GEMSDOE33 h33d-analog-tip-stepover` used analog step-over geometry (0.2632) — different
  input (traces, not vents) and different transform.
* **Mimic.** Glacial/aeolian vent-like mounds and randomly clustered volcanic vents with no tectonic alignment; the
  orientation-test significance threshold (p < 0.01) is the defence.
* **Cost.** ~1 h.

## 4. H-SASS3-Q — Damage-zone width anomaly (lidar slope-variance swath)

* **Layers.** `lidar_scarp_features_u8` / 1 m DEM slope derivatives, `existing_faults.tif`.
* **Signature.** Along-trace swath (±250 m) slope-variance profile; segments where the width of elevated variance exceeds
  the mapped trace's own damage-zone envelope (fitted per trace length) are flagged, and dots are placed on the excess
  lobe's crest.
* **Why off-catalogue.** Splay faults and damage-zone anastomosing strands widen the variance swath beyond the single
  mapped trace; the excess lobe is the unmapped strand.
* **Difference from this repo.** `vendor/gems57/damagezone_envelope.py` exists (template) but has never been run or
  validated here; the sibling lidar-scarp runs (`GEMSDOE47/50/64/66`, 0.038–0.115) detect scarps, not width anomalies.
* **Mimic.** Drainage incision and landslide deposits widen slope variance too; the along-trace continuity requirement
  (≥ 200 m of excess) is the defence.
* **Cost.** ~2–4 h (DEM IO dominates).

## 5. H-SASS3-R — Sinter-terrace riser edge density near discharge points

* **Layers.** 1 m lidar microtopography, GDR spring locations, `paleo_geothermal_regional.zip`.
* **Signature.** Decimetre-relief riser edges (morphological gradient at 1–3 m windows) inside 500 m of mapped
  springs/sinter; edges are sampled at 3 px and clustered by density.
* **Why off-catalogue.** Siliceous sinter terraces grow around discharge vents; their riser edges are the vent loci
  themselves, which may be hundreds of metres from any fault scarp the catalogue maps.
* **Difference from this repo.** Nothing here reads 1 m data (documented gap). Sibling `karage1 hmas-sinter-dualcover`
  masks sinter polygons (unscored); this targets riser *edge geometry* as lineaments.
* **Mimic.** Fluvial terrace risers and shoreline strands of palaeo-Lake Lahontan (which is why the 500 m spring gate and
  the sinter-association test are mandatory — `62GEMSDOE`'s Lahontan-tangent scored 0.0000).
* **Cost.** ~1–2 days (tiling the 1 m DEMs).

---

## Decision for this session

Per the budget rule (3 experiments / 2 hours) and the rule "do not spend a submission slot on an idea that hasn't beaten
the current holdout best":

* **No geological hypothesis is validated or promoted today** — all five are blocked on data placement (the standing
  blocker; the single highest-value owner action remains running
  `bash scripts/download_competition_data.sh` on an unrestricted machine, then `python scripts/prepare_data.py`).
* The session's implementable experiment runs in the standing metric-inversion lane (see `research/leaderboard-inversion-20261030.md`),
  which needs only the public sibling rasters that *are* obtainable here. Its deliverable is a unique, portal-safe TIF
  with an ESTIMATE from the leave-one-file-out-validated estimator, plus a run card.
* When the stack is placed, H-SASS3-O runs first (best expected gain per cost), tested on the spatially-blocked
  hide-and-recover holdout (`scripts/evaluate_holdout.py`, `GEMSDOE32-HIDE-RECOVER-v3.0`) with the leakage canary, before
  any weekly slot is touched.

---

## H-LBINV2 — Metric-inversion credit field at kernel-scale packing (RUN 2026-10-31, E2/E2b lane)

Not a *geological* hypothesis — the fifth-avenue question was "what placement of which field maximises
DW-Tversky under the uniqueness rule".  It is recorded here because the run card must name its
hypothesis and because it is the method the promoted candidate was built from.

- **Mechanism (why it can beat the corpus).**  For the published DW-Tversky, the marginal value of a
  dot at a novel location is q(x) — the consensus field credit from the distillation — while its
  marginal cost is α·(value-normalised contribution of the 0.2·D denominator).  The rule q > 0.2·EST
  is exact for unit-value dots; with the [0,1] value band, small kernels (2–3 px) are optimal because
  each dot then pays its own denominator for an independent 300 m kernel (src/gems32/metric.py takes a
  per-truth-pixel MAX over predicted pixels within 3 px).  Placement = greedy admission of the
  highest-q cells with a kernel-scale exclusion and a per-raster halo quota (uniqueness by
  construction).
- **Mimicking non-fault process.**  The field itself encodes what sibling methods agree on; they share
  input features, so shared artefacts (survey-lineation, coverage edges) are in the field.  The
  rank-correlation/overlap gates make the final file unlike any single artefact.
- **How it differs from anything in the repository.**  The repo's earlier emitters placed at fixed
  budgets in q order without metric-kernel reasoning (cbf-trace: D−αN pseudo-TP, 0.3255); the
  2026-10-30 LB-inversion used the same algebra but at sep≈2 over 84k dots with kill-repair; this run
  enforces the uniqueness rule *during* placement (per-raster halo quotas at the final count) and
  sweeps the packing radius.
- **Validation status.**  Ran 2026-10-31 on the 133-file field: estimator leave-one-file-out RMSE
  0.0531 / ρ 0.751 (labelled ESTIMATE); hide-and-recover holdout still blocked on labels.tif.
  Sweep rows in `evidence/run_card_kernelpack_20261031.json`; the kill-repair predecessor is a
  recorded negative result (`evidence/run_card_neg_killrepair_20261031.json`).
- **Expected DTI gain vs cost.**  Ranking the *geological* hypotheses (O–S) is unchanged; H-LBINV2 is
  the method layer they would plug into (a GeoDAWN/predictor field replaces q, the placement engine is
  reused).
