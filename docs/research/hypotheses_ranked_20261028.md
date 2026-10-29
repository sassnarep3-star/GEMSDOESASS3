# Ranked Geological Hypotheses for GEMSDOE Prize Challenge

**Generated:** 2026-10-28 | **Repository:** GEMSDOESASS3 | **Branch:** arena/84fd876f-gemsdoesass3
**Protocol:** Parallel-Run Protocol (LANE / REUSE / LABEL / LEAKAGE CANARY / RUN CARD / BUDGET)
**Status:** Research documentation only — no submission slot consumed.

---

## Problem Context (PhD-level framing)

The DOE GEMS competition scores submissions with a Distance-Weighted Tversky Index (DTI, alpha=0.2, beta=0.8, 300 m triangular kernel) against hidden fault labels. The public leaderboard top is 0.4413 (owner-reported); the best focus-site file is GEMSDOE32 `h33-h33-2-b2` at 0.2778 (owner-reported, not organizer-confirmed). All 9 focus-site files (GEMSDOE24/25/27/28/30/31/32/33/36) are already scored and must not be resubmitted. The current repo candidate (LWST-GeoConduit) is format-valid but blocked by the literal registry-overlap rule (99.78% vs 70% against the 13GEMSDOE calibration lattice; verdict: negative).

The scientific gap: USGS Qfaults / INGENIOUS catalogue traces map exposed bedrock scarps. Over half the Churchill–Pershing–Lander footprint lies beneath Quaternary Lake Lahontan lacustrine clays, aeolian sand, and coalescing piedmont bajadas where 10–15 ka sedimentation outpaces slip on blind 0.1–0.5 mm/yr normal faults (Bradys–Desert Peak step-over, Carson Sink, McGee Mountain, Salt Wells–Stillwater relays). Photogeologic and LiDAR compilations map the eroded bedrock range-front break in slope and miss blind intrabasin horst-bounding and relay faults entirely. A contrarian, high-P(Win) strategy must target faults **missing from the catalogue** — i.e., blind, concealed, or young structures with no surface expression — rather than re-dotting known catalogue traces.

---

## Hypothesis 1 (Rank #1 — Recommended): Basement-Fault Gravity Gradient × Radiometric Potassium Anomaly × Piedmont Basin-Edge (BGK-PBE)

| Element | Specification |
|---|---|
| **Layers** | `training_features.tif` Bands B05 (`iso_grav_anom_slope`), B08 (`geod_dilaterate`), B17 (`cond_surf`), B12 (`det_elev`), B15 (`depth_to_base_surf`), B06 (`tc` = GeoDAWN radiometric total count per IR-DATA-B06), external USGS GeoDAWN `geodawn_rad_u8.tif` Band 2 (eTh) and Band 1 (K) |
| **Physical signature** | (a) Horizontal gradient of isostatic gravity anomaly (density step across concealed basement faults); (b) elevation of radiometric potassium (K) and K/eTh ratio over hydrothermal argillic alteration; (c) dilatation rate from GPS strain tensor at the piedmont-to-basin transition; (d) basement-depth gradient masking only low-slope (< 2.5°) basin interiors. Combined multiplicatively so that diffuse valley-wide signals sharpen onto physically localized blind fault conduits. |
| **Why it catches catalogue-missing faults** | Blind intrabasin horst-bounding and accommodation-zone faults have no surface scarp (sedimented over), but they offset basement density (gravity gradient), focus dilatant strain (geodetic dilatation), and host hydrothermal alteration plumes that elevate K and clay conductivity. USGS Qfaults maps only the eroded bedrock range-front break, not the buried master fault 150–400 m basinward. |
| **How it differs from existing repo work** | Current lane (LWST-GeoConduit / GSD-HUA) uses true Miller–Singh magnetic tilt + Wijns Theta + GDR #1391 thermal-geochemical plumes + crack-tip/step-over relay bridging. BGK-PBE does **not** use magnetics, tilt, or thermal springs; it substitutes gravity-gradient × K/eTh × dilatation, a sensor suite none of the 9 focus-site files or GEMSDOESASS1–3 have combined. No overlap with lattice or dotted-ridge families by construction. |
| **Expected DTI improvement** | Moderate-to-high (holdout proxy). Gravity-gradient + K anomaly is a distinct physical channel from magnetic-tilt; expected to recover faults missed by both the magnetic lane and the dotted-ridge lane. |
| **Implementation cost** | Low–Medium. Requires only Bands B05/B08/B12/B15/B17/B06 from `training_features.tif` plus GeoDAWN K/eTh rasters (public, DOI 10.5066/P93LGLVQ). No GDR #1391 CSV joins, no InSAR, no seismic. ~1–2 hours. |
| **Leakage canary** | Single-feature AUC of gravity-gradient slope, K raster, and dilatation rate against holdout withheld faults must each be <= 0.90. All three are continuous, non-catalogue-derived fields; leakage risk is low. |
| **Non-fault mimic** | Plutonic intrusive margins (Cretaceous granodiorite stocks vs Mesozoic metasediments) create steep gravity gradients but have zero Quaternary brittle slip. Suppress where `depth_to_base_surf` indicates shallow bedrock outcrop (< 100 m sediment cover) and where USGS geologic map shows plutonic contacts. |

---

## Hypothesis 2 (Rank #2): Young Volcanic / Hydrothermal Silica Sinter Mound + 2 m Shallow-Temperature Probe Confluence (SST-2MT)

| Element | Specification |
|---|---|
| **Layers** | GDR #1391 `Paleogeothermal.zip` (Quaternary siliceous sinter/travertine/tufa mounds), `2MeterTempData.csv` (Kratt et al. shallow 2 m temperature probes), `training_features.tif` B17 (`cond_surf`), B06 (`tc`), B15 (`depth_to_base_surf`), external `geodawn_rad_u8.tif` Band 4 (TC) |
| **Physical signature** | Coincidence of (a) mapped paleo/active silica sinter and travertine mounds (fault-controlled fluid discharge at the surface), (b) shallow 2 m temperature anomalies (> +3°C over background), and (c) elevated surficial electrical conductivity from clay-rich alteration caps. Fault location inferred as the linear trend connecting mound clusters and thermal anomalies, not the mound footprint itself. |
| **Why it catches catalogue-missing faults** | Sinter mounds and 2 m temperature anomalies mark blind faults whose surface expression is limited to a small hydrothermal mound, not a mappable fault trace. USGS Qfaults requires a through-going scarp; these structures may be blind below a thin Quaternary veneer. |
| **How it differs** | None of the focus-site submissions use GDR #1391 paleogeothermal sinter + 2 m temperature probe confluence as the primary locator. Distinct from the magnetic/gravity lane (Hypothesis 1) and from all dotted-ridge / scarp methods. |
| **Expected DTI improvement** | Moderate. Sparse point data (mounds, probes) will produce few dots; precision likely high but recall limited. Best as a secondary corroboration layer. |
| **Implementation cost** | Medium. Requires GDR #1391 CSV downloads (public, DOI 10.15121/1881483), point-to-raster rasterization, and kernel smoothing. ~2–3 hours. |
| **Leakage canary** | Sinter mound locations are independent of the USGS/INGENIOUS catalogue; AUC against holdout faults should be modest (0.55–0.75), well below 0.90 leakage threshold. |
| **Non-fault mimic** | Cold CO2 springs and travertine from non-tectonic carbonate dissolution; suppress where no conductivity anomaly and no 2 m temperature excess co-occur. |

---

## Hypothesis 3 (Rank #3): Multi-Scale Magnetic Tilt-Angle Edge + Analytic-Signal Lineament Coherence (MT-Edge)

| Element | Specification |
|---|---|
| **Layers** | `training_features.tif` B03 (`tmi_hg`), B09 (`tmi_vg`), B14 (`tmi`), B02 (`rtp`); external USGS GeoDAWN `geodawn_mag_f32.tif` (TMI_RTP at 0 m and upward-continued 150 m) |
| **Physical signature** | True Miller–Singh (1994) magnetic tilt angle θ_M = arctan(tmi_vg / sqrt(tmi_hg² + ε)) and its horizontal gradient |∇θ_M| (depth-invariant contact/fault-edge locator), combined with analytic-signal amplitude of RTP magnetics and the 0 m vs 150 m upward-continuation residual (magnetite-destruction trough over hydrothermally altered fault rock). |
| **Why it catches catalogue-missing faults** | Alteration along blind faults destroys magnetite in the upper 50–300 m, producing narrow linear magnetic-low troughs with no topographic expression. The tilt angle is depth-invariant and contrast-invariant, so it locates concealed contacts that scarp mapping misses. |
| **How it differs** | The current repo lane uses true tilt + Theta as one component of a 51-channel stack. MT-Edge makes tilt/analytic-signal the **sole** locator, with no GDR thermal, no gravity, no geodetic strain. Distinct sensor physics from BGK-PBE (gravity + radiometrics) and from SST-2MT (geochemistry + temperature). |
| **Expected DTI improvement** | Moderate. Magnetics alone underperforms in thick non-magnetic basin fill; best where volcanic cover exists. |
| **Implementation cost** | Low. Purely raster algebra on existing bands + public GeoDAWN magnetics. < 1 hour. |
| **Leakage canary** | Tilt angle is computed from competition Bands B03/B09 only; no catalogue-derived input. Leakage risk negligible. |
| **Non-fault mimic** | Reversely magnetized Neogene ash-flow tuff contacts and unaltered mafic dikes create tilt edges with no Quaternary slip. Suppress where GeoDAWN eTh/K ratio indicates unaltered volcanic stratigraphy. |

---

## Hypothesis 4 (Rank #4): Lake-Lahontan Shoreline-Warped Flexure + Subsurface SPI/Theta Persistence (LLW-SPI)

| Element | Specification |
|---|---|
| **Layers** | `training_features.tif` B12 (`det_elev`), B19 (`det_elev_slope`), B15 (`depth_to_base_surf`), B03 (`tmi_hg`), B09 (`tmi_vg`); GDR #1391 `Heatflow.csv` and `WellsAndSprings.zip` |
| **Physical signature** | Pleistocene Lake Lahontan highstand (~1,330 m Sehoo) shoreline contours flexed over blind basement faults; minimum-curvature ridges of basement depth weighted by |∇z|, corroborated by 150 m upward-continued SPI/Theta persistence and heat-flow anomalies > 120 mW/m². |
| **Why it catches catalogue-missing faults** | Shoreline warping records subtle tectonic tilting across blind faults active during the Pleistocene. USGS Qfaults maps Holocene scarps, not Pleistocene-tilted shorelines. Blind faults active 10–100 ka are invisible to scarp mapping but recorded in shoreline flexure and basement relief. |
| **How it differs** | Explicitly targets Pleistocene (not Holocene) faulting via shoreline flexure — a temporal window no focus-site submission addresses. Combines with SPI/Theta persistence for subsurface confirmation. |
| **Expected DTI improvement** | Low-to-moderate. Shoreline features are regionally extensive; precision limited without tight thermal corroboration. |
| **Implementation cost** | Medium. Requires DEM-derived shoreline contour extraction and flexure analysis; GDR #1391 heat-flow CSV joins. ~2–3 hours. |
| **Leakage canary** | Shoreline contours are independent of the fault catalogue; AUC should be < 0.70. |
| **Non-fault mimic** | Wave-cut shorelines and aeolian dune crests parallel shoreline trends with no fault offset. Suppress where basement-depth gradient is flat and no heat-flow anomaly co-occurs. |

---

## Hypothesis 5 (Rank #5 — Deferred): Sentinel-1 InSAR Phase-Gradient + ECOSTRESS Predawn Thermal Inertia (InSAR-LST)

| Element | Specification |
|---|---|
| **Layers** | Sentinel-1 interferometric phase-gradient (line-of-sight velocity), ECOSTRESS predawn land-surface temperature / thermal inertia, `training_features.tif` B17 (`cond_surf`) |
| **Physical signature** | Coincident InSAR line-of-sight deformation (creeping or locked fault patch) and predawn thermal-anomaly lineaments, marking active blind fault creep and shallow hydrothermal upflow. |
| **Why it catches catalogue-missing faults** | Directly observes active deformation and thermal expression of faults with zero surface scarp — the ultimate "missing from catalogue" target. |
| **How it differs** | Entirely different data domain (radar interferometry + thermal IR) from all potential-field / geodetic / geochemical methods in the repo and focus sites. |
| **Expected DTI improvement** | Unknown (untested physics for this competition's label set). |
| **Implementation cost** | High. Requires Sentinel-1 SLC pairs, InSAR processing (GAMMIT/GMTSAR), ECOSTRESS L3 downloads, co-registration to EPSG:32611 100 m grid. External data not yet verified obtainable. |
| **Data availability check** | Sentinel-1: ESA Copernicus Open Access Hub (free, requires registration). ECOSTRESS: NASA LP DAAC (free, requires registration). Both obtainable but processing time exceeds the 2-hour budget. **Deferred** pending data-access verification. |
| **Non-fault mimic** | Agricultural irrigation, groundwater pumping, and landslide creep create InSAR signals with no fault association. |

---

## Ranking Summary

| Rank | Hypothesis | Layers | Expected DTI Δ | Cost | Leakage Risk | Mimic Control | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | BGK-PBE (gravity-gradient × K/eTh × dilatation) | B05/B08/B12/B15/B17/B06 + GeoDAWN K/eTh | Moderate–High | Low–Med | Low | Plutonic margins (suppress shallow bedrock) | **RECOMMENDED** |
| 2 | SST-2MT (sinter + 2 m temp probe) | GDR #1391 Paleo + 2MeterTemp + B17/B06/B15 | Moderate | Medium | Negligible | Cold CO2 springs | Backup |
| 3 | MT-Edge (magnetic tilt + analytic signal) | B02/B03/B09/B14 + GeoDAWN magnetics | Moderate | Low | Negligible | Reversed-mag tuffs/dikes | Backup |
| 4 | LLW-SPI (Lahontan shoreline flexure + SPI) | B12/B15/B19/B03/B09 + Heatflow | Low–Mod | Medium | Negligible | Wave-cut shorelines | Hold |
| 5 | InSAR-LST (radar + thermal inertia) | Sentinel-1 + ECOSTRESS + B17 | Unknown | High | Low | Irrigation/groundwater | Deferred |

---

## Validation Plan (per Protocol Rules 4–6)

1. Run leakage canary on each feature alone against the spatially-blocked holdout before any multivariable fit. AUC > 0.90 → leakage, reject.
2. Validate Hypothesis 1 (BGK-PBE) on the holdout with buffered hide-and-recover (alpha 0.2, beta 0.8, 300 m triangular kernel) and off-catalogue SGMC-CAL.
3. Only if BGK-PBE beats the current holdout best without consuming a weekly slot, generate a submission TIF and run the full 13-check validator.
4. Promotion to a real submission slot is a separate selector step within the weekly cap.

---

## Data Sources (Official, Free, Public)

| Source | URL | License | Status |
|---|---|---|---|
| DrivenData GEMS competition | https://www.drivendata.org/competitions/306/competition-doe-gems/ | Competition rules | Requires login for data |
| GEMs prize reference solution | https://github.com/drivendataorg/gems-prize-reference-solution | MIT | Public |
| USGS GeoDAWN airborne magnetic & radiometric | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and | DOI 10.5066/P93LGLVQ (CC0) | Public |
| GBCGE / OpenEI GDR #1391 INGENIOUS | https://gdr.openei.org/submissions/1391 | CC-BY-4.0 | Public |
| EPSG:32611 (WGS 84 / UTM zone 11N) | https://epsg.io/32611 | EPSG | Public |
| Tversky Index | https://en.wikipedia.org/wiki/Tversky_index | — | Public |
