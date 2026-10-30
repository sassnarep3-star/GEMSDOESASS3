# Candidate geological hypotheses — ranked 2026-10-30

Before any further submission work, four hypotheses that this repo has **not** implemented. Each names the layer(s), the
physical signature, why it should find a fault that is *missing* from the USGS/INGENIOUS catalogue (rather than one already in
it), how it differs from everything already built here, and what free official data it needs.

Layer names are the official ones from the problem description
(<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>), verified against
`data/feature_bands_audit.json` in this repo.

**All four are untested.** No score is claimed. Ranking is by expected SGMC-CAL improvement per unit of implementation cost,
given that SGMC-CAL is the evaluator calibrated to the leaderboard this session (ρ = 0.962, `evidence/focus9_concordance_20261030.json`).

| Rank | ID | Layers | Signature | Why off-catalogue | Differs from repo as built | Mimic to exclude | Cost |
|---|---|---|---|---|---|---|---|
| 1 | H-SASS3-J | `tc` (top-of-crustal magnetic source depth), `rtp` | **step** detector on `tc` differenced along the NNE fabric (Canny/phase-congruency on depth, not on field intensity) | A concealed fault offsets the magnetic basement; the *depth* to source steps across it even where no scarp, no TMI lineament and no mapped trace exists. Catalogue faults were digitised from surface expression, so basement-offsetting blind faults are systematically absent | No existing channel uses gradients of `tc`. The current stack uses `tc` only as a level feature (`features.py`, 35-channel stack) and the LWST 16-channel stack uses SPI/local-wavenumber on `rtp` and gravity, never on `tc` | Intrusive contacts, flow margins, basin-fill thickness changes (test: keep steps that do not coincide with `rtp` horizontal-gradient maxima) | Low — in-provided layer, no new data |
| 2 | H-SASS3-K | `iso_grav_anom_slope`, `rtp` | gravity-slope ridges **conditioned on the absence** of a magnetic gradient: `G_slope × (1 − Ĝ_rtp)` | A density-only boundary with no magnetic expression is where a catalogue built largely on magnetic/RTP lineaments is weakest; it is also the classic signature of a non-magnetic lithology juxtaposition across a fault | The repo's BGK-PBE idea combined gravity with potassium and dilatation but never *conditioned on magnetic absence*; no channel implements the multiplicative absence term | Basin-fill density ramps, playa/lake edges (repo already holds Lahontan masks and `tiger_road_distance_m.tif` to veto) | Low |
| 3 | H-SASS3-L | `geod_2ndinv`, `deq_n100a15`, `ieq_n100a15` | ridge crests of strain-rate second invariant that coincide with elevated earthquake density, restricted to >300 m from catalogue traces | Active blind faults localise contemporary strain and micro-seismicity even with no Quaternary scarp; the catalogue is geology-based, the strain field is not | H-GASS3-1 (slip–dilation) used dilatation/shear rates with a mechanical prior; this uses the **second invariant plus seismic co-location** as a joint detector, and the repo has no seismic-density channel in any candidate build | Quarry blasting, subsidence, irrigation-induced events (test: drop clusters with no strain ridge within 3 px) | Medium — sampling and co-location logic |
| 4 | H-SASS3-M | `external/lidar_scarp_features_u8.tif`, `det_elev`, `det_elev_slope` | scarp **polarity asymmetry** at sub-100 m scale (up-slope vs down-slope step), not scarp presence | The catalogue was digitised on a 100 m grid; metre-scale scarps on alluvial fans fall between pixels and are missed | Repo lines h50/h64 used LiDAR scarp *presence/density* (LB 0.038–0.076); polarity asymmetry is a different statistic and is already in the external layer as a separate band | Road cuts, shorelines, agricultural terracing (the LWST mimic-veto gate already exists) | Medium (layer exists; needs band separation and canary) |

## Validation protocol for any of these (unchanged, binding)

1. Build the channel label-free; run the 51-channel leakage canary (`max(AUC, 1−AUC) ≤ 0.90`).
2. Score on **SGMC-CAL** (primary, calibrated to the leaderboard) **and** hide-and-recover (secondary, leak-free on catalogue
   faults). Report both with CI and withheld counts.
3. Allocate dots against the **union** of all registry rasters' 3-px buffers, then re-check Rule 1 on the emitted bytes.
4. Do not spend a weekly slot until SGMC-CAL ≥ 0.0641 (champion parity) **and** Rule 1 passes.

## Data needed

Nothing above requires new external data: `tc`, `iso_grav_anom_slope`, `geod_2ndinv`, `deq_n100a15`, `ieq_n100a15` are bands of
`training_features.tif`, and the LiDAR scarp layer is already restored and SHA-verified in `.cache/gems_data/external/`.
If a future hypothesis needs more: USGS 3DEP 1 m DEM tiles (<https://www.usgs.gov/3d-elevation-program>) and the GeoDAWN
magnetic/radiometric release
(<https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>) are both
free and official; only the sibling-mirrored copies inside `.cache/gems_data/external/` were reachable from this sandbox, and they
are already verified.
