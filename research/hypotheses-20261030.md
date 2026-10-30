# New candidate hypotheses — 2026-10-30 (ranked, untested)

**Status:** proposals. None has been tested on a submission slot. Every quantity quoted as
"measured" comes from a script named beside it and is reproducible in this checkout.

**What changed in the evidence base today.** Three measurements reset the problem:

1. The scored truth is a **private set of expert-mapped faults that are deliberately absent from the
   public USGS catalogue** (official problem description, page 967: "faults that are not contained
   within the current public USGS database … will comprise the test dataset").
2. Across **50 scored submissions** the catalogue-recovery proxy (`dti_catalogue_proxy`) has rank
   correlation **−0.004** with the owner-reported leaderboard score
   (`scripts/analyze_score_drivers.py` → `evidence/score_drivers_20261030.json`). Recovering the
   public catalogue is not the objective; it is close to irrelevant.
3. The eleven best submissions (0.2560–0.2778) are **one structure**: 95–100 % of each file's dots
   lie within 3 px of the champion's dots. On the same hide-and-recover evaluator the champion
   scores HOLDOUT-DTI **0.00452 [0.00382, 0.00526]** — the *lowest* of the files tested — while the
   `h19-5` multiline file (leaderboard 0.1922) scores 0.06879 [0.05882, 0.08006]
   (`evidence/holdout_candidate_20261030.json`, `.cache/ho_*.json`).

So the search space that matters is **off-catalogue structure that a fault expert would draw**, and
the best available local criterion is agreement with the score-weighted consensus of prior
submissions (`scripts/build_unique_candidate.py`), not catalogue recovery.

## Ranking

| Rank | ID | Layer(s) | Physical signature | Expected DTI gain | Cost |
|---|---|---|---|---|---|
| 1 | **H-SASS3-J** | catalogue traces + `det_elev_slope`, `tmi_hg`, LiDAR `strike`, `gdr_qfaults_traces.csv` azimuth/slip rate | along-strike trace **extrapolation** beyond mapped tips and through step-overs | moderate–high | medium |
| 2 | **H-SASS3-K** | `geod_shearrate`, `geod_dilaterate`, `geod_2ndinv` + LiDAR `strike` | lineament strike within ±10° of the Andersonian optimum for the local strain-rate tensor | moderate | low–medium |
| 3 | **H-SASS3-L** | `iso_grav_anom_hg/vg` **conditioned on weak** `tmi_hg`/`tc` | gravity-only density step: concealed basement fault with no magnetic edge | moderate | low |
| 4 | **H-SASS3-M** | `gdr_wellspring_in_footprint.csv`, `gdr_volcanic_vents_in_footprint.csv`, `rad_K`/`rad_Th`, `cond_surf` | fault corridors that connect geothermal discharge points and K-enriched alteration | low–moderate | low |

## H-SASS3-J — structural continuation (rank 1)

- **Layers.** `labels.tif` (mapped traces), `gdr_qfaults_traces.csv` (per-trace azimuth, slip rate,
  recency, map scale), `det_elev_slope` (B19), `tmi_hg` (B3), LiDAR `strike` (band 11).
- **Signature.** For each mapped trace, extrapolate the local azimuth beyond each tip for ≤ 1.5 km
  and keep only extrapolations that coincide with a topographic or magnetic grain. Weight by the
  trace's slip rate × recency (the CSV carries both; no repository document uses them).
- **Why it catches catalogue-missing faults.** An expert adding a fault to a national database draws
  the continuation the compiler never visited. The step-over/relay between two mapped segments is
  precisely the geometry a national compilation drops.
- **Difference from existing work.** `h19-5` ("multiline corroborated") is a *field* rule — it
  corroborates continuous geophysical lineaments anywhere. This is *trace-anchored*: the candidate
  must lie on the forward projection of a specific catalogue trace and carry its attributes.
- **Mimic to control.** Streams and drainage follow fault lineaments and continue past tips. Control
  with `det_elev_slope` directional anisotropy and by excluding pixels whose nearest LiDAR `upface`
  ridge is a drainage divide.

## H-SASS3-K — Andersonian strike optimality (rank 2)

- **Layers.** `geod_2ndinv` (B4), `geod_shearrate` (B7), `geod_dilaterate` (B8), LiDAR `strike` (band
  11), catalogue trace azimuths.
- **Signature.** Estimate the local principal strain axes from the geodetic tensor; a normal fault is
  optimally oriented at ≈30° to σ1. Score lineaments by |Δstrike| to that optimum.
- **Why it catches catalogue-missing faults.** Optimally oriented faults take most of the modern
  strain, so they are the youngest and the shortest — exactly the class a regional compilation
  under-represents.
- **Difference.** `H-GASS3-1` (docs/hypotheses.md) uses slip–dilatation co-location only; no
  repository hypothesis uses strike-versus-strain alignment.
- **Mimic to control.** Joint sets and cooling fractures in plutons are strike-clustered but carry no
  Quaternary slip; suppress where `depth_to_base_surf` shows bedrock at surface.

## H-SASS3-L — gravity-only lineament (rank 3)

- **Layers.** `iso_grav_anom_hg` (B18), `iso_grav_anom_vg` (B11), `tmi_hg` (B3), `tc` (B6).
- **Signature.** High gravity gradient **and** weak magnetic gradient. A density contrast with no
  magnetic expression is a sediment-covered basement offset.
- **Why it catches catalogue-missing faults.** Magnetic lineament picking drives most submissions in
  this competition; non-magnetic faults are systematically invisible to that lane.
- **Difference.** `H-N4` (next-hypotheses-20261029) proposes gravity-slope lineaments alone; this is
  an explicit *minus* rule against the magnetic edge response.
- **Mimic to control.** Lithologic density contacts (basalt/tuff boundaries) produce the same
  signature; suppress where `cond_surf` and `rad_Th` indicate a mapped volcanic contact.

## H-SASS3-M — hydrothermal conduit corridors (rank 4)

- **Layers.** `gdr_wellspring_in_footprint.csv` (thermal class, temperature), `gdr_volcanic_vents_in_footprint.csv`, `rad_K`/`rad_Th`, `cond_surf` (B17).
- **Signature.** Fault segments that connect two or more discharge points and pass through
  K-enriched, conductive ground.
- **Why it catches catalogue-missing faults.** Completions are best near infrastructure and known
  systems; the *connecting* faults between systems are the least mapped and the most interesting for
  the Final Prize Round, which rewards faults the panel can verify.
- **Difference.** No repository document uses either GDR CSV as a locator (they are restored assets
  only).
- **Mimic to control.** Agricultural/evaporation ponds and playa salts raise conductivity with no
  fault; control with `d_road_px` and distance to playa margins.

## How these would be tested (before any submission slot)

1. Build the field for the hypothesis; emit dots with the metric-exact greedy
   (`src/gems32/emitter.py`, unchanged) at a fixed budget.
2. Score it with the leaderboard-calibrated estimator (`scripts/build_unique_candidate.py`,
   leave-one-file-out RMSE 0.0653, Spearman 0.695 on the 50 scored submissions).
3. Keep the hypothesis only if it beats the current candidate's estimate **and** passes the lane rule.
4. No submission slot is consumed by any of these until then.
