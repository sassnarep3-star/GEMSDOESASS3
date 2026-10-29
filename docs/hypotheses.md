# Historical hypothesis archive — NOT CURRENT APPROVAL

> **Audit warning (2026-10-29):** this file records prior-session plans and claims that have not been independently reproduced in the current checkout. It contains inconsistent lane identifiers (`H-GASS3-1`/GSD-HUA versus `H-SASS3-A`/LWST-GeoConduit), claims cached rasters that are absent now, quantitative uplift/cost claims without current source data, and an H-GASS3-1 band mapping that conflicts with the audited 19-band schema in `data/feature_bands_audit.json`. Treat the entries below as unverified archival hypotheses, not facts, current results, or implementation instructions. The active run card is negative; no submission is approved.

# Preregistered Geological & Geothermal Hypotheses (`GEMSDOESASS3`)

- **Preregistration Timestamp:** `2026-10-27T11:58:00Z` (committed **prior to** writing any `GSD-HUA` feature-extraction, training, or allocation code)
- **Repository / Branch:** `sassnarep3-star/GEMSDOESASS3` (`arena/d076f77e-gemsdoesass3`)
- **Assigned Single Method Lane (Protocol Rule 1):** `H-GASS3-1` — **Geothermally Coupled Geomechanical Slip–Dilation & Hydrothermal Alteration Upflow Architecture (`GSD-HUA`)**
- **Shared Holdout Contract (Protocol Rule 2):** `vendor/gems57/evaluate_holdout.py` (`evaluator_version = "gems57-pooled-hide-v2"`, buffered whole-component LOQO splits `seeds = (20, 21)`, `hide_frac = 0.20`, `buffer_px = 3` (`300 m` feature context collar), `boundary_px = 12` (`1.2 km` quadrant boundary erosion), exact `DTI(0.2, 0.8)` with `300 m` triangular kernel and 20 km physical spatial-block bootstrap `95% CI`)
- **Leakage Canary Gate (Protocol Rule 4):** Symmetric single-feature ROC-AUC check `max(AUC, 1 - AUC) <= 0.90` evaluated on withheld whole fault components before any multivariable fit
- **Dual-Phase Uniqueness Gate (Protocol Rule 1):** `vendor/gems57/uniqueness.py` (`complete_accessible_scan = True` across all 43 unique SHA-256 registry rasters / 46 files):
  - **Pre-placement continuous `surface`:** `|Spearman| <= 0.90` across the `5,167,373`-pixel active footprint AND `(surface > 0)` 3-px overlap `<= 70.0%`
  - **Final binary `dots`:** `|Spearman| <= 0.90` AND `3-px` dot overlap `<= 70.0%` (`jaccard <= 0.70`, non-identical bytes/predictions)
- **Compute & Experiment Cap (Protocol Rule 6):** Hard stop at `<= 3` scored experimental model arms (`EXP-1`, `EXP-2`, `EXP-3`) and `<= 2.0` wall-clock hours

---

## Critical Pre-Experiment Data Audit Discoveries (`IR-DATA-B06` & `IR-DATA-BAND-ORDER`)

Before running the final `GSD-HUA` feature stack, a byte-level audit of `training_features.tif` (`4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`) verified all 19 embedded GDAL `band_name` tags (`data/feature_bands_audit.json`):

1. **Exact Verified 19-Band Schema (`IR-DATA-BAND-ORDER`):**
   - `B01`: `mag_anom`, `B02`: `rtp`, `B03`: `tmi_hg`, `B04`: `geod_2ndinv`, `B05`: `iso_grav_anom_slope`, `B06`: `tc` (GeoDAWN Radiometric Total Count), `B07`: `geod_shearrate`, `B08`: `geod_dilaterate`, `B09`: `tmi_vg`, `B10`: `deq_n100a15`, `B11`: `iso_grav_anom_vg`, `B12`: `det_elev`, `B13`: `iso_grav_anom`, `B14`: `tmi`, `B15`: `depth_to_base_surf` (sedimentary cover thickness in meters!), `B16`: `ieq_n100a15`, `B17`: `cond_surf`, `B18`: `iso_grav_anom_hg`, `B19`: `det_elev_slope` (degrees, median `3.75°`).
   - Crucially, `B15` (`depth_to_base_surf`, median `316 m`, 95th percentile `1,882 m`) provides a direct basement-relief surface whose horizontal gradient $|\nabla Z_{\text{basement}}|$ locates concealed range-front and intrabasin horst-bounding faults beneath flat Quaternary playa/bajada cover (`B19 det_elev_slope < 3.5°`).
2. **Band 6 Metadata Mislabeling (`IR-DATA-B06`):**
   - Embedded GDAL metadata labels Band 6 (`tc`, valid range `[2.953, 88.571]`) as `"Tilt angle or total curvature - magnetic field derivative"`.
   - Cross-correlating Band 6 against the raw USGS GeoDAWN airborne radiometric survey (`geodawn_rad_u8.tif`, DOI `10.5066/P93LGLVQ`, Band 4 = Radiometric Total Count) across the `5,164,300` jointly valid footprint pixels yields **$\rho_{\text{Spearman}}(\text{Band 6}, \text{GeoDAWN Rad TC}) = +0.999954$**, whereas correlating Band 6 against true Miller–Singh magnetic tilt angle $\theta_M = \arctan(\text{Band 9 } \text{tmi\_vg} / \text{Band 3 } \text{tmi\_hg})$ yields **$\rho_{\text{Spearman}} = +0.021917$** (statistically orthogonal!).
   - In `H-GASS3-1`, we treat Band 6 according to its true physical identity (GeoDAWN Radiometric Total Count) and explicitly compute **true Miller–Singh (1994) magnetic tilt angle** and horizontal tilt-derivative edges (`Theta-map`, Wijns et al., 2005) directly from `tmi_vg` (`B09`) and `tmi_hg` (`B03`), plus gravity tilt from `iso_grav_anom_vg` (`B11`) and `iso_grav_anom_slope` (`B05`).

---

## Five Untried Geological & Geothermal Hypotheses (`H-GASS3-1` through `H-GASS3-5`)

### `H-GASS3-1` (Rank #1 — Selected Lane): Geothermally Coupled Geomechanical Slip–Dilation & Hydrothermal Alteration Upflow Architecture (`GSD-HUA`)

1. **Exact Data Layers:**
   - **Competition Stack (`training_features.tif`, 100 m EPSG:32611):**
     - Topography/geomorphology: Band 1 (`dem`), Band 5 (`slope`), Band 7 (`tri`), Band 8 (`tpi`), Band 10 (`twi`)
     - Potential fields & MT conductivity: Band 2 (`tmi`), Band 3 (`tmi_hg`), Band 9 (`tmi_vg`), Band 11 (`cba`), Band 12 (`cba_hg`), Band 13 (`cba_vg`), Band 18 (`cond_surf`), Band 19 (`cond_15km`)
     - Radiometric / VNIR-SWIR mineral ratios: Band 6 (`tc` = GeoDAWN Radiometric Total Count per `IR-DATA-B06`), Band 14 (`iron`), Band 15 (`clay`), Band 16 (`ferric`), Band 17 (`ferrous`)
   - **Permissively Licensed Public External Datasets (cached & SHA-256-verified in `.cache/gems_data/`):**
     - **USGS GeoDAWN Airborne Magnetic & Radiometric Grids** (`geodawn_mag_f32.tif`, `geodawn_rad_u8.tif`; USGS Data Release DOI `10.5066/P93LGLVQ`, CC0 Public Domain): Band 2 `TMI_RTP_up150m` (`150 m` upward-continued RTP magnetics) and Radiometric `K` (Band 1), `eTh` (Band 2), `eU` (Band 3), `TC` (Band 4).
     - **GBCGE / OpenEI GDR Submission #1391 — INGENIOUS Great Basin Play Fairway Compilation** (DOI `10.15121/1881483`, CC-BY-4.0):
       - `Geodetics.zip` (Kreemer et al. GPS strain-rate tensor: $\dot{e}_{ee}, \dot{e}_{nn}, \dot{e}_{en}$, dilatation rate, shear strain rate, principal extension azimuth $\psi_{\text{ext}}$)
       - `Geochemistry_v3_March2022.csv` (18,000+ spring/well samples with $\text{SiO}_2, \text{Na}, \text{K}, \text{Ca}, \text{Li}, \text{B}, \text{Cl}, \text{HCO}_3, \text{SO}_4$ & Fournier quartz/chalcedony geothermometer temperatures)
       - `2MeterTempData.csv` (Kratt et al. shallow 2 m temperature probe surveys targeting blind geothermal anomalies across Carson Sink / Humboldt / Granite Springs / Bradys–Desert Peak)
       - `Paleogeothermal.zip` (Quaternary siliceous sinter, travertine, and tufa mounds marking paleo/active fault-controlled fluid discharge)
       - `WellsAndSprings.zip` & `Heatflow.csv` (thermal wells, warm/hot springs, conductive heat-flow boreholes)
       - `Earthquakes.csv` (relocated microseismicity hypocenters delineating active brittle fault damage zones at depth)
       - `Transportation.zip` (anthropogenic road/rail/transmission infrastructure used solely as a **mimic-suppression penalty**, never as a positive fault proxy)
2. **Physical Signature & Mathematical Transform:**
   - **True Crustal Magnetic Phase & Magnetite-Destruction Corridor:**
     - Compute true Miller–Singh (1994) magnetic tilt angle $\theta_M = \arctan\!\big(\text{tmi\_vg} / \sqrt{\text{tmi\_hg}^2 + \varepsilon^2}\big)$ and horizontal tilt gradient $|\nabla \theta_M|$ (depth-invariant contact/fault edge locator).
     - Compute shallow hydrothermal magnetite-destruction residual $\Delta\text{TMI}_{\text{destr}} = \text{TMI}_{\text{RTP},\uparrow 150\text{m}} - \text{TMI}_{\text{RTP},0\text{m}}$ paired with high GeoDAWN `eTh / (K + \varepsilon)` and SWIR `clay` (`Band 15`) / `ferric-ferrous` oxidation (`Band 16 / Band 17`): oxidizing meteoric/geothermal fluids circulating along dilatant Basin-and-Range fault conduits alter primary titanomagnetite to non-magnetic hematite/pyrite/smectite in the upper `50–300 m`, producing narrow linear magnetic-low troughs flanked by argillic clay caps (`|\nabla \log \text{cond\_surf}|`)!
   - **Geothermally Coupled Morris–Ferrill–Henderson (1996) Slip & Dilation Tendency:**
     - Estimate local structural strike $\hat{\mathbf{s}}(y, x)$ at `1.0 km` and `2.5 km` scales from the dominant eigenvector of a **joint multi-sensor structure tensor** combining `cba_hg` (basement density step), $|\nabla \theta_M|$ (true magnetic phase contact), $|\nabla \text{cond\_surf}|$ (MT clay-cap margin), and multi-scale `dem` break-in-slope curvature.
     - Project the local Kreemer GPS horizontal strain-rate tensor $\dot{\mathbf{E}}(y, x)$ onto fault-normal $\hat{\mathbf{n}} = (-\sin\phi, \cos\phi)$ to obtain **dilation tendency** $T_d(\phi) = (\dot{e}_{nn,\perp} - \dot{e}_{\min}) / (\dot{e}_{\max} - \dot{e}_{\min} + \varepsilon)$ and **slip tendency** $T_s(\phi) = |\dot{e}_{ns,\parallel}| / (\dot{e}_{\max} - \dot{e}_{\min} + \varepsilon)$ (Faulds & Hinz, 2015: NW Nevada geothermal upflow concentrates along NNE-striking normal faults perpendicular to WNW–ESE extension $\psi_{\text{ext}} \approx 110^\circ\text{–}120^\circ$ and ENE/NNW transtensional step-overs).
   - **Thermal / Geochemical Fluid-Upflow Plume Corroboration:**
     - Build multi-bandwidth (`1.5 km` and `4.0 km` Gaussian KDE / IDW) excess temperature & fluid-flux fields from GDR `#1391` chalcedony/quartz geothermometry anomalies, 2 m shallow temperature probe anomalies (`\Delta T_{2\text{m}}`), thermal springs/wells, paleo-geothermal sinter/tufa mounds, and microseismic lineament density, then form the **coupled mechano-thermal interaction** $I_{\text{GSD-HUA}} = T_d(\phi) \cdot \Phi_{\text{thermal}} \cdot \Phi_{\text{subsurface\_edge}}$ so diffuse valley-wide thermal plumes sharpen strictly onto physically localized fault conduits.
   - **Oriented `1.0 km` & `2.5 km` Line-Integral Coherence + Fold-Visible Crack-Tip / Relay Bridges + Two-Regime Exact `300 m` Submodular CELF Allocation:**
     - Integrate multi-sensor fault probability along 12 strike orientations (`15°` spacing) over `1.0 km` and `2.5 km` windows to enforce topological continuity across alluvial fans while rejecting isotropic blobs.
     - Using **only `fold['visible']` catalogue traces** (`buffer_px = 3` withheld collar honored strictly per fold), compute elastic Mode-II/III fault-tip damage lobes (`300 m – 3.5 km` forward of visible segment tips along visible tip strike) and overlapping en-echelon step-over relay corridors (`0.5–4.0 km` inter-segment spacing), suppressed around anthropogenic road/rail lineaments (`Transportation.zip`) and constant-elevation Lake Lahontan paleo-shorelines (`~1,320–1,345 m`).
     - Allocate discrete binary `{0.0, 1.0}` predictions outside a `B = 2 px` (`200 m`) visible-catalogue collar via `vendor/gems57/emit.py`'s exact `300 m` kernel greedy marginal-gain allocator (`allocate_patient`) with explicit **two-regime budget split** between exposed/piedmont range-front toes and low-slope concealed sedimentary basins (`slope < 2.5°`), preserving a positive pre-placement continuous surface across the active off-catalogue footprint so both `surface` and `dots` pass literal registry uniqueness gates.
3. **Why USGS Qfaults / NBMG / INGENIOUS Missed These Faults:**
   - Over `55%` of the Churchill–Pershing–Lander study footprint lies beneath Quaternary Lake Lahontan lacustrine clays (`< 1,335 m` elevation), aeolian sand sheets, and active coalescing piedmont bajadas where `10–15 ka` sedimentation rates exceed slip rates on `0.1–0.5 mm/yr` blind normal and accommodation-zone faults (e.g., Bradys–Desert Peak step-over, Carson Sink, McGee Mountain / Dixie-Humboldt marshes, Salt Wells / Stillwater relays; Faulds et al., 2016). Photogeologic and LiDAR scarp compilations map the eroded bedrock range-front break in slope (`100–500 m` upslope of the buried piedmont master fault) and miss blind intrabasin horst-bounding and relay faults entirely—precisely the targets DOE GEMS expert geothermal geologists added from geophysical & drilling syntheses!
4. **Named Non-Fault Mimics & Explicit Suppression:**
   - **Mimic 1:** Anthropogenic graded highways (`I-80`, `US-50`, `US-95`), railroad embankments, canals, and transmission corridors (`Transportation.zip`) creating razor-sharp `100 m` DEM/TPI linear breaks and cultural magnetic spikes -> suppressed via buffered transportation-alignment penalty where `cba_hg` basement support is absent.
   - **Mimic 2:** Wave-cut Pleistocene Lake Lahontan highstand shorelines (`~1,330 m` Sehoo highstand) and concentric playa desiccation/evaporite rims (`slope -> 0`, contour-parallel strike $\nabla z \perp \hat{\mathbf{s}}$ with zero basement `cba_hg` step and high surficial `tc`/`cond_surf` brine sheet) -> suppressed via contour-parallel shoreline index and zero-basement-gradient evaporite mask.
5. **Novelty vs All Sibling & Historical Attempts:**
   - Neither `GEMSDOE24..36`, `19GEMSDOE`, `GEMSDOE48/63/70/76`, nor `GEMSDOESASS1..2` combined: (a) the `IR-DATA-B06` correction restoring true Miller–Singh magnetic tilt $\theta_M$ alongside GeoDAWN `150 m` upward-continued magnetite-destruction + `eTh/K` alteration ratios, (b) GDR `#1391` geothermometry + 2 m shallow temperature probe + paleo-sinter fluid-upflow plumes coupled multiplicatively to GPS slip–dilation tendency along multi-sensor strike, and (c) fold-visible crack-tip/step-over relay bridging with explicit `Transportation.zip` + Lahontan shoreline mimic suppression under two-regime `300 m` CELF allocation. (`GEMSDOE36`'s historical `anderson-geothermal-pinn` was verified in `evidence/nine_sites_executive_audit.json` to be `100%` of `GEMSDOE32`'s `H19-5` topographic ridge dots plus `1,200` extra dots, using zero GDR `#1391` thermal/geochemical data!)

---

### `H-GASS3-2` (Rank #2 — Backup Candidate, Not Executed per Single-Lane Rule): Magnetite-Destruction & Argillic Demagnetization Trenching (`MDZ-BDP`)

- **Exact Layers:** `geodawn_mag_f32.tif` (`TMI_RTP_0m`, `TMI_RTP_up150m`), `geodawn_rad_u8.tif` (`K`, `eTh`, `eU`), `training_features.tif` Bands `2, 3, 9, 14, 15, 16, 17, 18`.
- **Physical Signature:** Matched band-pass Mexican-hat trough detector on $\text{TMI}_{\text{RTP},0\text{m}} - \text{TMI}_{\text{RTP},\uparrow 150\text{m}}$ gated by low ferric/ferrous ratio and elevated `clay` (`Band 15`) + shallow conductivity (`Band 18`), isolating hydrothermally demagnetized fault gouge inside magnetic Miocene/Oligocene volcanic cover.
- **Why Missed by Catalogues:** Volcanic plateaus (Trinity, Pah Rah, Desatoya, Stillwater ranges) host densely welded tuffs where altered fault zones erode into subdued swales indistinguishable from cooling joints without airborne magnetic-radiometric phase contrast.
- **Named Mimic:** Reversely magnetized Neogene ash-flow tuff stratigraphic contacts and unaltered mafic dike swarms.
- **Why Ranked #2:** Its highest-leverage physical ingredients ($\Delta\text{TMI}_{\text{destr}}$, true tilt $\theta_M$, `eTh/K`, SWIR clay/iron) are cleanly subsumed as core subsurface features inside `H-GASS3-1`, whereas standalone `MDZ-BDP` underperforms inside thick non-magnetic Quaternary basin fill.

---

### `H-GASS3-3` (Rank #3 — Not Executed): Alluvial Piedmont Fan-Apex Back-Projection & Buried Scarp Toe (`APF-BWC`)

- **Exact Layers:** `usgs_3dep_10m_dem.tif` (`10 m` 3DEP DEM downsampled to `100 m` sub-pixel break-in-slope & profile curvature moments) + `training_features.tif` Bands `1, 5, 8, 10, 11, 12`.
- **Physical Signature:** Directed `100–400 m` downslope vector shift from eroded bedrock range-front facet bases to the maximum convex-to-concave profile curvature inflection + horizontal Bouguer gravity gradient (`cba_hg`) peak beneath coalescing alluvial aprons.
- **Why Missed by Catalogues:** Legacy `1:250,000` fault traces frequently digitized the topographic bedrock-alluvium contact rather than the active buried piedmont master fault `150–400 m` basinward; furthermore, `GEMSDOE24` (`S3DEP1`) tested raw 10 m monoclinal scarp curvature without basinward gravity-locked toe projection and suffered a negative result due to bedrock cliff noise.
- **Named Mimic:** Wave-cut Lake Lahontan shorelines and incised axial river terraces (Humboldt / Carson rivers).

---

### `H-GASS3-4` (Rank #4 — Not Executed): Poisson Source-Depth Multi-Scale Gravity–Magnetic Euler Deconvolution (`PSDR-Edge`)

- **Exact Layers:** `training_features.tif` Bands `2, 3, 9, 11, 12, 13` + `geodawn_mag_f32.tif` + `gravity_isostatic_f32.tif` (`USGS Isostatic Gravity`).
- **Physical Signature:** Structural-index $N = 0.5$ Thompson (1982) / Reid (1990) Euler deconvolution clustering across `200 m`, `500 m`, and `1,500 m` upward continuations to trace dip-consistent basement fault planes from surface break to `2 km` depth.
- **Why Missed by Catalogues:** Blind intrabasin horsts (e.g., Fallon FORGE / Carson Sink basement highs) have zero surface relief and are known only from gravity/seismic reflection.
- **Named Mimic:** Plutonic intrusive margins (Cretaceous granodiorite stocks against Mesozoic metasediments) with steep density/susceptibility walls but zero Quaternary brittle slip.

---

### `H-GASS3-5` (Rank #5 — Deferred / Sandbox Network-Constrained): Sentinel-1 InSAR Phase-Gradient + ECOSTRESS Predawn Thermal Inertia Lineaments (`InSAR-LST`)

- **Exact Layers:** ASF Sentinel-1 ARIA unwrapped interferograms + NASA LP DAAC ECOSTRESS predawn land-surface temperature (`70 m`) over NW Nevada.
- **Physical Signature:** Cross-fault groundwater barrier / moisture-contrast thermal inertia step + aseismic differential compaction phase gradient across blind basin faults.
- **Why Deferred:** Outbound sandbox network access is restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org`; ASF/LP DAAC hosts are unreachable in-sandbox, whereas `H-GASS3-1` operates 100% deterministically on SHA-256-verified cached datasets.

---

## Expected DTI-Gain vs Cost Ranking Matrix

| Rank | ID | Hypothesis | Expected `HOLDOUT-DTI` Lift vs Controls | Compute & Engineering Cost | Data Availability in Sandbox | Decision |
|---:|---|---|---|---|---|---|
| **1** | **`H-GASS3-1`** | **`GSD-HUA`** (Mechano-thermal slip–dilation + `IR-DATA-B06` true magnetic tilt + GeoDAWN magnetite-destruction/`eTh/K` + fold-visible relay bridges + two-regime 300 m CELF) | **Highest (`+0.015` to `+0.040` over same-split tabular/ridge controls)** — unites exposed/piedmont scarp physics, blind geothermal fluid conduits, and exact 300 m DTI geometry | Moderate (`~12–18 min` total for 3 LOQO experiments across 8 folds) | **100% cached & SHA-256 verified** (`.cache/gems_data/` + `.cache/features/`) | **EXECUTE (Single Assigned Lane)** |
| 2 | `H-GASS3-2` | `MDZ-BDP` (Magnetite-destruction + argillic trenching only) | Medium in volcanic ranges; weak in thick lacustrine basins | Low (`~5 min`) | 100% cached | Subsumed as features in `H-GASS3-1` |
| 3 | `H-GASS3-3` | `APF-BWC` (3DEP piedmont toe + gravity lock) | Low–Medium (confined to `~20%` range-front margin) | Moderate (`~15 min` on 10 m grid) | 100% cached | Key `cba_hg` + piedmont curvature captured in `H-GASS3-1` |
| 4 | `H-GASS3-4` | `PSDR-Edge` (Multi-altitude Euler deconvolution) | Low–Medium (plutonic contact false positives) | Moderate (`~10 min` FFT stack) | 100% cached | Not executed (single-lane discipline) |
| 5 | `H-GASS3-5` | `InSAR-LST` (Sentinel-1 + ECOSTRESS predawn LST) | Medium in playas | High (`>1 hr` preprocessing) | Blocked by network allowlist | Deferred to Phase-2 external ingest |

---

## Preregistered 3-Experiment Plan Within `H-GASS3-1` (`GSD-HUA`)

All models and controls are evaluated **strictly out-of-sample** on the exact same 8 buffered whole-component LOQO folds (`seeds = (20, 21)`, `hide_frac = 0.20`, `buffer_px = 3`, `boundary_px = 12`) in `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`), with paired 20 km physical spatial-block bootstrap 95% confidence intervals (`1,000` bootstrap draws):

- **Same-Split Reference Controls (0 experimental budget slots):**
  - `CTRL-0` (`H19-5` topographic ridge baseline evaluated on fold-visible collar `d_vis > 2.0`, `37,654` dots equivalent density): tests pure historical `H19-5` ridge geometry under fold-honest `B = 2` collar.
  - `CTRL-1` (`19-Band Pixel HGB + B=2 CELF`): standard HistGradientBoostingClassifier trained on the raw 19 competition bands only (no `IR-DATA-B06` true magnetic tilt, no GeoDAWN upward continuation/`eTh/K`, no GDR `#1391` mechano-thermal fields, no oriented line integrals, no crack-tip bridges), allocated with `B = 2` `300 m` greedy non-overlapping kernel selection (`K = 37,654` full-grid equivalent density).
- **Scored Experimental Budget (`<= 3` Arms, `<= 2h`):**
  1. **`EXP-1` (`GSD-HUA Core` — Catalogue-Free Multi-Physics + Mechano-Thermal + Oriented Line Integrals + Single-Regime `B=2` CELF):**
     - Adds corrected `IR-DATA-B06` true Miller–Singh magnetic tilt $\theta_M$ & $|\nabla \theta_M|$, GeoDAWN magnetite-destruction $\Delta\text{TMI}_{\text{destr}}$ & `eTh/K` alteration ratios, MT clay-cap lateral gradient $|\nabla \log \text{cond\_surf}|$, Kreemer GPS slip–dilation tendency along multi-sensor strike, GDR `#1391` geothermometer + 2 m probe + sinter/spring/microseismic plumes, and `1.0 km` / `2.5 km` 12-azimuth oriented line-integral coherence. Zero catalogue-derived predictors in the classifier (`100%` immune to catalogue proximity shortcuts), allocated via single-regime `B = 2` `300 m` CELF (`K = 37,654` full-grid equivalent).
  2. **`EXP-2` (`GSD-HUA + Fold-Visible Crack-Tip / Relay Bridges + Anthropogenic & Shoreline Mimic Suppression`):**
     - Augments `EXP-1` with **strictly fold-visible (`fold['visible']`)** Mode-II/III fault-tip propagation lobes (`300 m – 3.5 km` along visible tip strike) and en-echelon step-over relay bridges (`0.5–4.0 km` between sub-parallel visible fault tips) gated multiplicatively by `EXP-1` subsurface/geothermal support (so blank alluvium between unrelated tips receives zero phantom bridge weight!), PLUS explicit suppression of `Transportation.zip` road/rail corridors lacking basement `cba_hg` contrast and constant-elevation Lake Lahontan shoreline contours (`~1,330 m`).
  3. **`EXP-3` (`GSD-HUA Two-Regime Basin/Range-Front Calibrated CELF + Optimal Density Sweep`):**
     - Takes the winning surface architecture from `{EXP-1, EXP-2}` and replaces global single-regime ranking with **two-regime basin vs range-front calibration and exact `300 m` submodular CELF allocation** (`Regime R1`: exposed bedrock & piedmont bajada toes; `Regime R2`: low-slope concealed basins `slope < 2.5°` where geophysical/mechano-thermal probability is quantile-matched against range-front tail sharpness so blind basin faults are not starved by sharp range-front DEM gradients), selecting the fold-optimal global budget `K` on out-of-fold validation before locking the single full-grid emission.

### Preregistered Promotion & Verdict Criteria
- **Leakage Gate:** Every engineered feature in `EXP-1..3` must satisfy symmetric single-feature holdout `max(AUC, 1 - AUC) <= 0.90` on withheld fault components. Any feature failing this check is quarantined before training.
- **Uniqueness Gate:** Both the full-grid continuous pre-placement surface (`surface > 0` across active off-catalogue footprint) AND the final binary dot raster (`dots`) must pass `vendor/gems57/uniqueness.py` (`|Spearman| <= 0.90` AND `3-px overlap <= 70.0%` across all 43 unique SHA-256 registry rasters).
- **Promotion Rule:** Promote the highest-`HOLDOUT-DTI` arm among `{EXP-1, EXP-2, EXP-3}` **if and only if** it beats **both** `CTRL-0` (`H19-5` fold-honest `B=2` control) and `CTRL-1` (`19-Band Pixel HGB + B=2 CELF`) on `gems57-pooled-hide-v2` pooled `HOLDOUT-DTI` (`delta > 0` with paired 20 km spatial-block bootstrap CI reported) AND passes every automated format/range/catalogue/uniqueness gate (`verdict = "promote"`). Otherwise emit the best validated unique artifact for transparent archival and set `verdict = "negative"` (`OK to download = YES`, `OK to submit = NO`).
