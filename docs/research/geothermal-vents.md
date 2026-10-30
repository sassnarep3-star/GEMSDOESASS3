# Geothermal vents, springs and blind faults — reusable knowledge (2026-10-30)

**Purpose.** A standing reference for this repo: what the free official geothermal data actually contains,
what it can and cannot do for the GEMS DTI, and the measured numbers behind the claim. Written from
(a) the official dataset landing pages fetched on 2026-10-30 and (b) the pinned extracts already in this
workspace. Nothing here is a score. Regenerate the measurements with
`/home/user/.venv/bin/python scripts/geothermal_prior_audit.py` (writes `evidence/geothermal_prior_audit_20261030.json`)
and the inventory with the snippet recorded in `evidence/geothermal_inventory_20261030.json`.

---

## 1. What the official sources say (fetched 2026-10-30, links for manual review)

| Source | Verified content | Link |
|---|---|---|
| GDR submission **1391** — *INGENIOUS – Great Basin Regional Dataset Compilation* | DOI `10.15121/1881483`, CC-BY 4.0. Stated goal: "accelerate discoveries of new, commercially viable **hidden geothermal systems** while reducing exploration risk". 9 downloadable resources + linked DOI releases covering: 2-m temperature probes, Quaternary faults (v1 and a superseding v2), Quaternary volcanic vents/flows, geodetic shear & dilation, seismicity/earthquake density, heat flow, MT conductance, magnetics, gravity, **paleogeothermal spring deposits (sinter and tufa)**, spring and well temperatures, aqueous geochemistry, thermal conductivity, fault slip & dilation tendency | <https://gdr.openei.org/submissions/1391> |
| Direct files (no login, free) | `2m_temperature_probe_INGENIOUS_regional_data.zip` (1.03 MB) · `seismicity_INGENIOUS_regional_data.zip` (22.98 MB) · `geodetics_INGENIOUS_regional_data.zip` (51.99 MB) · `paleo_geothermal_regional.zip` (82 kB) · `faults_quaternary_INGENIOUS_regional_data.zip` (5.76 MB) · `qfaults_ingenious_nad83conus117_2023-06-27.zip` (5.85 MB, **supersedes v1**) · `great_basin_q_volcanics.zip` (9.44 MB, vents = points, flows = polygons) · `wellspringdata.gdb.zip` (19.85 MB, authoritative spring/well temps + chemistry) · `study_area_boundary_INGENIOUS_regional_data.zip` | `https://gdr.openei.org/files/1391/<name>` |
| Linked DOI releases in the same submission | MT conductance `10.5066/P9TWT2LU` · elevation trend / detrended elevation `10.5066/P9MQRCBY` · gravity & magnetics `10.5066/P9Z6SA1Z` · heat flow `10.5066/P9BZPVUC` · Quaternary slip & dilation tendency `10.5066/P9YL58W6` · thermal conductivity = GDR **1390** (abridged SMU heat-flow DB) | see submission page |
| Project site | GBCG *INGENIOUS* project page (consortium, background, collaborators) | <https://gbcge.org/current-projects/ingenious/> |
| GeoDAWN | High-resolution airborne **magnetic and radiometric** surveys over northern/western Nevada and eastern California, flown by EDCON-PRJ under USGS contract 2021-11-01 → 2022-11-20, two overlapping areas spanning the **Walker Lane and northwestern Great Basin**; EarthMRI + DOE GTO funding. Lidar over the same extents was acquired through USGS **3DEP**; bare-earth DEMs are explicitly described as useful for "mapping active fault scarps even when their expression is subtle or concealed in heavily vegetated areas", "particularly relevant to geothermal resource" studies | GDR <https://gdr.openei.org/submissions/1591> · <https://catalog.data.gov/dataset/geodawn-west-central-nevada-earthmri-data> · GRC paper <https://publications.mygeoenergynow.org/grc/1034804.pdf> |

**Consequence for us:** the pinned `data/external/geodawn_*` and `lidar_scarp_features_u8.tif` rasters in this
workspace are *derived* products of exactly these surveys, and `2m_temperature_probe_...zip` plus
`paleo_geothermal_regional.zip` are **already present locally** (unzipped in `.cache/gems_data/external/`). The
free, no-login gap that remains is: the authoritative `wellspringdata.gdb.zip`, `great_basin_q_volcanics.zip`,
the Qfaults **v2** shapefile, and the heat-flow / conductance DOI rasters.

## 2. What the data looks like on our grid (measured 2026-10-30)

Grid facts: EPSG:32611, 100 m cells, 3730 × 3292; the scoring kernel is a 300 m = 3 px triangular kernel;
organizer-side the *known-fault* pixels are excluded from scoring (chrisk-dd, forum thread 11516).

| Layer (in-footprint extract) | records | median px to existing catalogue faults | ≤3 px | ≤10 px | >50 px |
|---|---|---|---|---|---|
| All spring/well rows | 27,092 rows / **12,570 unique grid cells** | 24.0 | 11.6% | 28.1% | 20.8% |
| `thermalclass == "Hot"` | 1,873 (+121 rows stored as `"Hot "` — see §4) | **13.04** | 25.6% | 46.3% | 10.5% |
| Quaternary volcanic vents | 21 (20 basalt, 1 rhyolite) | 22.2 | **0.0%** | 28.6% | 28.6% |
| Spring temperatures (°C) | 8,718 | median 32.0, p90 111.0, max 296.5 | | | |
| Quartz geothermometer (°C) | 973 | median 96.7, p90 163.2, max 269.1 | | | |

Proximity of the two emissions under comparison (`evidence/geothermal_prior_audit_20261030.json`;
`p_*_farther_than_control` < 0.5 means *closer than* 44,090 uniform random in-footprint cells, seed 20261030):

| Layer | candidate median px | champion median px | random control | p(farther) cand | p(farther) champ |
|---|---|---|---|---|---|
| any spring/well cell | 25.1 | 24.4 | 128.8 | 0.238 | **0.231** |
| `Hot` springs | 116.0 | 102.2 | 255.8 | 0.276 | **0.245** |
| volcanic vents | 519.2 | 484.6 | 718.4 | 0.368 | **0.329** |
| Qfault trace centroids | **52.6** | 61.7 | 62.8 | **0.424** | 0.486 |
| catalogue labels | **14.9** | 19.6 | 122.4 | **0.164** | 0.213 |

## 3. What follows — and where the conventional wisdom is wrong

**Claim (contrarian, and it is the load-bearing one): a geothermal-vent or hot-spring prior is the wrong
lever for *this* metric, and the dataset itself tells you so.**

1. **Springs are fault-followers, and the scored faults are the ones without springs.** 46.3% of Hot-class
   springs are within 1 km of an *existing catalogue* trace and 25.6% within 300 m. Those are precisely the
   pixels the organizer masks out of the evaluation. An emission anchored on springs therefore spends up to
   half of its FP-weighted mass in the non-scored halo, which is how `h51-km-faultzone` (a 1 km fault-zone
   corridor) ended at 0.0106.
2. **The tail that matters is far from the springs.** In-footprint Hot springs are 1,873 records over a
   5.17 M-cell footprint: even if every one of them marked a perfectly-placed 3-px collar, the *supply* of
   new true positives is orders of magnitude below what the ~0.18 gap to the current leaderboard high
   (0.4544 ≈ 40% recall, vs 0.2778 ≈ 23.5%) requires.
3. **Vents are decorrelated from the catalogue but vanishingly sparse.** 21 vents in the footprint, 0 of them
   within 3 px of a catalogue fault — geologically interesting, metrically irrelevant. Any "geothermal vent
   discovery" pipeline must be judged on the *fault scarp* label class, not on vent proximity; the GEMS label
   set is expert-mapped faults (surface expression, sometimes buried), not thermal anomalies.
4. **The prior that is not saturated is Quaternary slip/dilation tendency, not temperature.** The one axis on
   which our candidate beats the champion is proximity to Qfault trace *centroids* (52.6 px vs 61.7 px).
   `10.5066/P9YL58W6` ships slip- and dilation-tendency values per Quaternary segment; a segment with high
   dilation tendency whose trace is *not* in `existing_faults.tif` is a candidate blind strand. That is a
   structural prior with a mechanism, and it is free.
5. **Paleogeothermal deposits beat active springs for this task.** Sinter/tufa (in
   `paleo_geothermal_regional.zip`, already local) marks *palaeo* vent sites; those sit on structures that may
   have been inactive long enough to be missed by the modern-scarp mappers yet still offset the surface. This
   is also what the INGENIOUS brief is about — "hidden geothermal systems".
6. **Where the lid actually is.** Lidar morphometry in this workspace is a pinned 100 m *derivative* of
   GeoDAWN/3DEP. The scarp AUCs measured in experiment E1 (best single field: `det_elev_slope` 0.659;
   `lidar_valid` 0.191, i.e. the family *avoids* non-LiDAR terrain) say the derivative carries ranking
   information but far too little to build a better surface. 1 m 3DEP point clouds (data.gov entry above) are
   the only free route to something genuinely stronger, and they are a large download, not a re-weighting.

**Therefore:** use the geothermal data to (a) *exclude* the spring-halo around catalogue faults and
(b) *propose* blind strands from slip/dilation tendency and paleogeothermal deposits. Do not rank by
temperature proximity — it is the one axis on which the family is already as good as, or better than, anything
we can build from the same layer (p(farther) 0.231 vs 0.238).

## 4. Irregularities found while building this (flagged, not silently fixed)

- `thermalclass` in `gdr_wellspring_in_footprint.csv` contains both `"Hot"` (1,873) and `"Hot "` (121, trailing
  space), plus `""`, `NULL` and `Unknown`. A filter written as `== "Hot"` silently drops 6.1% of hot springs.
  Any future use must `str.strip()` and normalise the NULL spellings.
- 27,092 rows describe only **12,570** distinct grid cells because the extract unions `well_features`,
  `well_chemistry`, `well_temperature`, `spring_chemistry`, `spring_temperature` and `spring_features` layers.
  Counting rows instead of locations overstates the density 2.15×.
- `dist_known_fault_px` in the extract is in **grid pixels at 100 m**, not metres; it agrees with our own
  `distance_transform_edt` on `labels.tif` to within 1 px for the samples checked.
- `age` is empty (`nan`) for all 21 vent records, so vent-age filtering is impossible from this extract; the
  authoritative `great_basin_q_volcanics.zip` would be needed.
- The extract's spring points are the *only* geothermal layer present locally at 100 m; the 2-m temperature
  probe zip present in `.cache/gems_data/external/` has **not** been rasterised — no claim is made here about
  what it would add.

## 5. Reusable interface in this repo

| Asset | What it does |
|---|---|
| `scripts/geothermal_prior_audit.py` | Any emission mask vs any GDR point layer: median px distance, fraction within the 3-px kernel, and the closer-than-random Mann-Whitney statistic. Re-run for every new candidate; it is cheap (7 s) and it is the only place the spring-halo argument is checked numerically. |
| `src/gemsdoesass3/ocm.py` → `LIDAR_BANDS` | The band map for the pinned scarp derivative (`valid` = 12, never a statistic) used by E1/E3. |
| `evidence/geometry_experiment_E1_partial.log` | Per-field live-dot keying AUCs, including `lidar_valid 0.1911`. |
| `docs/research/hypotheses-20261030-strand-lane.md` | H-N5/H-N6, the two hypotheses this audit produced. |

**Non-claims.** No number above is an organizer score or a projected score. The GDR extracts are derived
products and are not the authoritative layer; treat their positions as ±1 cell. The forum quote about
known-fault masking (thread 11516, chrisk-dd, 2026-09-16) is the source of the exclusion assumption; if the
organizer changes that rule, §3.1 changes with it.
