# Candidate geological hypotheses — 2026-10-31 (third pass, prompt §2)

The standing prompt requires that, before any new generator is written, three to five new
hypotheses be produced, each naming (a) the specific layer(s) involved, (b) the physical
signature targeted, (c) why it should catch a fault **missing** from the USGS/INGENIOUS
catalogue rather than one already in it, and (d) how it differs from anything already
implemented in this repository — ranked by expected DTI improvement and implementation cost.

One definitional fact drives all five. DrivenData staff, answering "Where do you draw the
line?", confirmed that for this competition *"new fault" means **any fault pixel not already
captured by USGS/INGENIOUS, and can include newly mapped geometry of an existing fault system —
continuations past a mapped endpoint, splays, parallel strands within the same fault zone all
count*."
([thread 11536](https://community.drivendata.org/t/where-do-you-draw-the-line/11536)).
Staff also confirmed that known USGS/INGENIOUS pixels are **masked and score-neutral**
([thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)).
So the target is not "somewhere new on the map", it is "any geometry the catalogue does not
already contain" — which means fault *tips* are the highest-value real estate on the grid.

---

## The measurement that ranks them

Over the 182 published rasters with owner-reported scores
(`evidence/diagnose_truth_location_20261031.json`), an OLS fit of
`score ~ 1 + f0 + f1 + f2 + clumpiness + log10(D)` (R² = 0.221, n = 182) gives

| term | coefficient | p |
|---|---|---|
| `f0` (mass within 300 m of a catalogued fault) | −0.339 | 0.0002 |
| `f1` (mass in the 300–600 m shell) | +0.124 | 0.24 |
| `f2` (mass in the 600–900 m shell) | −0.120 | 0.26 |
| clumpiness (share of dots whose 3-px neighbourhood holds ≥ 1000 units of mass) | −0.0056 | 1.5 × 10⁻⁵ |
| `log10(D)` | +0.047 | 0.0066 |

and, separately, the mean score by median-per-dot distance from the catalogue peaks in the
**12–20 px (1.2–2.0 km) stand-off band at 0.167** (max 0.278 for the champion) and collapses
past 20 px to 0.052.

**Interpretation.** The hidden truth is an *annulus around the catalogue, not the catalogue and
not the deep background*. A hypothesis earns its place by (i) reasoning about structures at
1–2 km stand-off, and (ii) *not* being clumpy — the negative clumpiness term means the
published fields that scored best were spread along traces, not blobs at hotspots.

---

## Ranked hypotheses

### H1 — Geodetic strain-rate **ridge continuation** past catalogue tips  ★ best expected DTI / cost
- **Layers.** `geod_dilaterate` (band 4), `geod_shearrate` (band 7), `geod_2ndinv` (band 8),
  with `tmi_hg` (band 3) and `det_elev_slope` (band 19) as concordance gates.
- **Physical signature.** The ridge line (local maximum, and zero transverse gradient) of the
  second invariant of the horizontal strain-rate tensor. A fault zone that accommodates strain
  produces a strain-rate ridge that is *continuous through* the gap where the surface trace has
  not been mapped; the ridge therefore keeps its azimuth past the mapped tip, while the
  catalogue stops.
- **Why it catches a missing fault.** The continuation past a mapped endpoint is, verbatim, a
  "new fault" under the staff definition above. The strain-rate field is largely independent of
  the surface mapping that produced the catalogue, so a ridge that continues past a tip is
  evidence the catalogue's endpoint is a mapping limit, not a geological one.
- **How it differs from the repo.** The repo already contains tip-continuation arms
  (`gemsdoesass3-tipcont-disp44923-4px-20261030T0330Z.tif`, GEMSDOE27's `h27-4-tip-fill`,
  `topo-gap-closure`), but every one of them extrapolates along the **azimuth of the mapped
  fault** — it inherits the catalogue's geometry, so it can only extend what the catalogue
  already knows in the direction the catalogue already points. H1 takes the azimuth from the
  *strain-rate tensor's own ridge*, which can bend away from the mapped trace (step-overs,
  relays, en-échelon splays), and gates each continuation on the sign of the dilatation being
  consistent with the kinematics of the segment it continues.
- **Cost.** Medium (one new ridge-extraction operator, ~2 h). Status: **not run**.

### H2 — Off-catalogue **SGMC traces gated by magnetic vertical-gradient concordance**
- **Layers.** `external/derived_sgmc_faults_100m_u8.tif` + `tmi_vg` (band 9) +
  `iso_grav_anom_hg` (band 18).
- **Physical signature.** A state-geological-map fault trace that lies > 300 m from any
  catalogued fault pixel **and** is colinear with a magnetic vertical-gradient maximum /
  zero-crossing within 200 m. The magnetic gate is the physical test: a real basement-penetrating
  structure offsets the magnetised basement and produces a linear gradient anomaly; a
  compilation artefact, a cartographic generalisation, or a mapped-at-1:500 k splay that does not
  exist at 1:24 k does not.
- **Why it catches a missing fault.** The USGS/INGENIOUS label set and the SGMC compilation are
  different products. Measured here: **62 122 of the 83 593 SGMC fault pixels lie more than
  300 m from any catalogue pixel**, i.e. three quarters of the SGMC network is off-catalogue and
  is therefore, by the staff definition, legitimate "new fault" real estate.
- **How it differs from the repo — and the warning.** Two published submissions that are
  essentially the raw off-catalogue SGMC layer scored **0.0492 and 0.0512**
  (`docs/research/session-20261030-review.md`), and the SGMC layer is already in the repo's
  `artifacts/`. So H2 is only worth anything **because of the magnetic concordance gate**: the
  unfiltered layer is a proven negative, and the value of the hypothesis is precisely the
  filter. Nothing in the repo combines SGMC with a magnetic-gradient concordance test.
- **Cost.** Low (all three layers are already on disk). Status: **not run**.

### H3 — LiDAR scarp height/width ratio inside the **1–6 km annulus**
- **Layers.** `external/lidar_scarp_features_u8.tif` (12 bands derived from the 1 m 3DEP DEM;
  `ex_max`, `ex_mean`, …), `det_elev` (band 12), `det_elev_slope` (band 19).
- **Physical signature.** Ridge-like topographic lineaments (high excess-elevation maximum, low
  width relative to height — i.e. *sharp* scarps rather than broad pediment edges) whose
  centroid sits **1–6 km** from the nearest catalogued fault.
- **Why it catches a missing fault.** The stand-off measurement above puts the truth's centre of
  mass at 1.2–2.0 km from the catalogue. A synthetic-aperture scarp detector run over the whole
  DEM without that restriction drowns in Quaternary alluvial-fan edges, terrace risers and
  landslide headwalls; restricting to the annulus raises the prior that a detected scarp is a
  tectonic splay of a known system — again exactly the staff's "parallel strands within the same
  fault zone".
- **How it differs from the repo.** The repo has lidar-scarp arms
  (12GEMSDOE `r7-nms3-dem10-scarp`, 7GEMSDOE `lidarscarp-ridge-top2pct`) but neither applies the
  annulus restriction nor normalises scarp height by width; both rank scarps by absolute
  amplitude, which biases them to the largest (and most already-mapped) scarps.
- **Cost.** Low–medium. Status: **the motivating measurement is done** (stand-off band and
  clumpiness terms above); the generator is **not run**.

### H4 — Buried **basin-bounding** faults from the depth-to-conductive-base discontinuity
- **Layers.** `depth_to_base_surf` (band 15), `cond_surf` (band 17), `tmi` (band 14),
  `rtp` (band 2), `iso_grav_anom` (band 13).
- **Physical signature.** A steep lateral gradient (or a linear discontinuity under a
  gradient-orientation coherence test) in depth-to-conductive-base that has **no** corresponding
  lineament in `det_elev` — i.e. a structure buried beneath the basin fill that offsets the
  pre-Cenozoic basement but has not reached, or no longer reaches, the surface.
- **Why it catches a missing fault.** A buried fault is structurally the strongest possible
  candidate for a real fault that a *surface*-mapping catalogue cannot contain. The GeoDAWN
  region's geothermal systems are localised on exactly these structures, which is why the repo's
  2 m temperature probe and paleo-geothermal inventories cluster along them; those inventories
  mark the surface expression of the conduit, not the fault trace itself.
- **How it differs from the repo.** The repo uses `depth_to_base_surf` and `cond_surf` as
  *predictors* inside the logit and the correlator (`gemsdoesass3-lbinv-…`,
  `…-bgk-pbe-…`), never as a *lineament source* — no arm in the repo extracts discontinuity
  lines from the basement-depth surface.
- **Cost.** High: gradient-scale selection on a smooth interpolated surface is easy to get wrong
  and needs its own holdout. Status: **not run**.

### H5 — Radiometric **alteration haloes** along off-catalogue lineaments
- **Layers.** `external/geodawn_rad_u8.tif` (K, Th, U, …) and
  `external/geodawn_extensions_u8.tif` (`ThK`, `UK`, …).
- **Physical signature.** Elongated K-enrichment and high K/Th anomalies. Hydrothermal fluids
  circulating along a fault leach K into the wall rock and/or precipitate K-bearing alteration
  minerals (adularia, illite, sericite), producing a halo that is elongated along the conduit.
- **Why it catches a missing fault.** Alteration haloes are the one signature that survives
  burial and erosion: a fault with no scarp, no basement offset resolvable at 100 m, and no
  gravity expression can still be marked by its fluid pathway. This targets faults the other
  four hypotheses are blind to.
- **How it differs from the repo.** The repo's radiometric arm
  (`gemsdoesass3-precambrian-cond-20261030T0449Z-ap9c8b8e.tif`) uses the radiometric bands as a
  *lithology/province* predictor, not as a lineament source; no arm extracts elongated
  anomaly axes or K/Th-ratio lineaments.
- **Cost.** Medium. Status: **not run**.

---

## Ranking

| rank | hypothesis | expected DTI improvement | implementation cost | evidence on hand |
|---|---|---|---|---|
| 1 | **H1** strain-rate ridge continuation past tips | **highest** — it targets the one geometry staff explicitly blessed, at the one stand-off the diagnostic says the truth lives at | medium | staff definition + stand-off band + negative `f0` coefficient |
| 2 | **H3** LiDAR scarp ratio in the 1–6 km annulus | high — directly exploits the measured 12–20 px peak | low–medium | stand-off band measured on 182 files |
| 3 | **H2** SGMC off-catalogue × magnetic concordance | medium — 62 k off-catalogue pixels is a big prior, but the unfiltered layer is a **proven 0.05** | low | off-catalogue count measured |
| 4 | **H5** radiometric alteration lineaments | medium, high variance — physically independent of H1–H4 | medium | none |
| 5 | **H4** buried basement-depth discontinuities | potentially high, but the gradient-scale choice dominates and needs its own holdout | **high** | none |

**External data.** None of H1–H5 requires external data: every layer named above is already
present under `.cache/gems_data/` (`data/restore` restores them; 28/28 SHA-verified this
session). No download is needed, so the prompt's "confirm it is obtainable first" gate is
satisfied vacuously.

**Honest status.** Only H1's and H3's *motivating diagnostic* has been run. None of H1–H5 has
been generated, and none has been evaluated on the spatially-blocked holdout. The prompt's rule
is that the top candidate must be validated on the holdout **before** a weekly submission slot
is spent; that validation has not happened, so **no slot should be spent on H1 yet**. This
session's entire compute budget went to the consensus reconstruction described in
`docs/research/diagnostic-to-submission-20261031.md`, which is a different (and, on the honest
five-fold design, better-supported) object.
