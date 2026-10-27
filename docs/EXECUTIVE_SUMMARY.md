> **Historical preliminary review — superseded for current status.** This document records a review before the H1 experiment and nine-raster audit. Its statements that no experiment, data, or comparisons existed are historical, not current. No submission TIFF was produced. See the [current dashboard](../index.html), [H1 run card](../evidence/h1-run-card.json), and [updated research review](research/results-and-irregularities.md).

# Executive summary — requested GEMS sites and research gates

**Decision: DO NOT SUBMIT.** No candidate raster was generated in this checkout. It has no competition data, template toolchain, or comparison registry. There is no download-ready TIF and no defensible estimate of a future TIF's leaderboard score. A file must not be called unique until its raster content has been measured against the actual registry rasters.

## Immediate answer

From the values supplied in the request, **GEMSDOE32's `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is the highest listed result across the nine requested sites (reported value 0.2778)**. This ranks the *reported entries only*. The prompt does not include a submission receipt, raster bytes, evaluator run, or validation record for that entry, so its score is **not independently verified here** and must not be labeled `ORGANIZER-CONFIRMED`. Its name alone does not establish the method or explain why it scored as it did. A scientific explanation of its actual performance requires the exact raster, underlying method/configuration, and scoring receipt; inferring the algorithm from the slug would be speculation.

The two overall leaderboard claims in the supplied material (**0.3195** and **0.4413**) conflict. I checked the [official DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) at **2026-10-27 11:36 UTC**: its top displayed public entry was **0.4544** (ORGANIZER-PUBLISHED PUBLIC LEADERBOARD; page snapshot, not a submission-page receipt). Treat the prompt's two older values as stale/unverified, not the current public-board high. A public leaderboard value is not a prediction for this project and does not disclose private-test or final-prize performance. The public metric is a distance-weighted Tversky index, so higher recall is favored relative to false alarms (beta 0.8 vs alpha 0.2), and small positional errors receive triangular distance credit out to 300 m. That explains how a broad, carefully located prediction can perform well in principle; it does **not** establish why the named H33 artifact scored well.

## Best reported entry per requested site

The following is a transcription of the scores and names in the user-provided prompt, not an independent audit. The confidence/uniqueness column is deliberately conservative: a name and score are not enough to compare raster bytes. The scores below are **UNVERIFIED USER-REPORTED VALUES**—not `HOLDOUT-DTI` and not `ORGANIZER-CONFIRMED` because no receipt was supplied. No value in this table is a projection for a new method.

| Site | Highest entry listed in prompt | Value as quoted (unverified) | Highest among entries quoted for that site? | Exact duplicate / registry uniqueness verified here? | Download & submit decision |
|---|---|---:|---|---|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 | Yes, versus the other listed entry | **Unknown** — artifact comparison not performed | No approval here; score is historical/unverified |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 | Yes, versus the other listed entry | **Unknown** | No approval here |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 | Yes, versus the other listed entry | **Unknown** | No approval here |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 | Yes, among four listed entries | **Unknown** | No approval here |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 | Yes, versus the other listed entry | **Unknown** | No approval here |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 | Yes, among entries quoted | **Unknown** | No approval here |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | 0.2778 | Yes, among entries quoted | **Unknown** | **Do not treat as a newly generated or selected candidate** |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 | Yes, among entries quoted | **Unknown** | No approval here |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 | Yes, among entries quoted | **Unknown** | No approval here |

**Important distinction:** This answers “which is highest among the scores pasted?” but not “which should be uploaded?” Under the supplied parallel-run protocol, promotion to a live slot is a separate selector step. This review does not select a real slot or recommend copying/re-uploading the historical H33 raster.

## Candidate hypotheses to pre-register (not tested)

These are experiment proposals, not validated claims, expected scores, or approvals. Since the local checkout has no model/code/data, “different from this repo” is currently a vacuous baseline. The prompt's other-site methods overlap many broad families (dotted lineaments, DEM scarps/ridges, magnetic/geothermal proxies); exact novelty against every external implementation cannot be established without the actual code, configuration, and rasters. The protocol's single-lane rule means **select at most one** for a future, pre-registered run. Ordinal impact/cost are qualitative priors only.

| Rank | Hypothesis and layers | Target signature & off-catalogue rationale | Difference / overlap caveat | Expected DTI benefit (qualitative) | Cost / key mimic |
|---:|---|---|---|---|---|
| 1 | **DEM drainage-normalized scarp persistence** — official competition 1 m DEM links / USGS 3DEP DEM, existing DEM derivatives; optionally only use geophysical layers as independent corroboration | Seek linear slope-break and profile-curvature ridges persistent across DEM scales after removing drainage-aligned channel/terrace responses. A previously unmapped fault may form a subtle, continuous scarp or deflect channels beyond catalogued traces. | Adds explicit hydrogeomorphic suppression and multi-scale persistence rather than a raw scarp/ridge score. Still overlaps prior lidar-scarp and topographic methods; only the normalization/persistence formulation is distinct as a hypothesis, not yet proven unique. | Medium-high prior; no score estimate | Medium-high; mimic: erosional terrace risers / road cuts / lithologic scarps. Free official DEM availability is documented by USGS 3DEP; exact tile coverage at target sites must be checked before use. |
| 2 | **Cross-survey radiometric ratio-edge persistence** — GeoDAWN K, eTh, eU and total-count products where available; magnetic derivatives from the provided feature stack | Use ratios and edge orientation/coherence, with flight-line/altitude artifact suppression, to locate persistent lithologic/contact boundaries that may reveal concealed fault juxtaposition without following known mapped traces. | Focuses on robust ratio-domain contacts and acquisition-aware persistence, not raw intensity or simple multi-layer fusion. Radiometric/geophysical fusion appears in the broader prior-work list; novelty must be checked against actual scripts and rasters. | Medium prior | Medium; mimic: soil moisture, surficial cover, weathering, flight-line seams. USGS GeoDAWN release is a public official source; exact band availability and licenses need dataset-level inspection. |
| 3 | **Joint strain-field transition + independent magnetic edge** — provided dilatation/shear/second-invariant layers plus magnetic TMI/RTP derivatives | Look for a spatially coherent strain-gradient boundary supported by an independent magnetic edge, then score only where the co-located response extends off the known catalog. This may expose a concealed structural corridor rather than reward proximity to mapped faults. | Tests an interaction/conditional residual, not either layer alone. Structural/geophysical baselines exist in the reported site history; therefore this is only a candidate for a specifically pre-registered interaction test. | Medium-low prior | Medium; mimic: broad tectonic domain boundaries and processing seams. Both layer families are listed by DrivenData as supplied features; availability of exact arrays still unverified locally. |
| 4 | **Gravity–magnetic edge azimuth agreement with scale stability** — isostatic gravity anomaly/slope and magnetic anomaly/derivatives | Seek coincident, similarly oriented boundaries across physically different fields that remain stable over several scales; faults can juxtapose density and susceptibility contrasts, including buried structures with weak topographic expression. | Explicit orientation/scale agreement differs from a single edge or simple union. Other projects have used geophysical baselines; inspect registry and implementations to ensure this is not relabeling a previous method. | Low-medium prior | Medium; mimic: non-fault lithologic contacts, regional basin margins, gridding artifacts. Source layers are listed in official challenge description. |
| 5 | **Earthquake-density discontinuity conditioned on surface structure** — supplied earthquake-density layer, DEM/strain context | Test whether localized seismic-density changes align with independent mapped geomorphic/strain boundaries outside known faults. Potentially sensitive to active blind structures. | Focus is a conditional discontinuity, not earthquake density alone; risk of rediscovering existing seismic clusters is high. | Low prior | Low-medium; mimic: uneven catalog completeness, transient swarms, spatial sampling. Official description lists earthquake density as a provided feature; event-level metadata and time window are not in this checkout. |

### Required selection gate

Before an experiment, retrieve the template's approved cached feature stack and shared `evaluate_holdout.py` / `submission_writer.py`, determine exact data versions, and preregister a single row above. If those tools are absent in the template, resolve that in the shared template rather than making a fork. Do not run a submission until the candidate beats the current best under the same spatially blocked holdout/evaluator and has its full confidence interval, leakage-canary result, registry comparison, and run card. No candidate here has met that gate.

## Format, novelty, and automated approval

A generated TIF can be marked “OK to download / submit” only after all of the following are machine-verified on the final saved bytes:

- one-band float32 GeoTIFF; exact sample-template CRS, dimensions, bounds, and affine transform;
- no NaN/Inf within the valid footprint, all valid predictions in `[0, 1]`, and null/NaN outside the valid bounds;
- SHA-256 recorded and rechecked after writing;
- unique against every required registry raster: rank-correlation at or below 0.90 and no more than 70% of predicted dots within 3 px of any one registry raster, checked both on the surface before placement and on final dots;
- holdout metric on the required whole-segment, buffered hide-and-recover split, plus feature-by-feature leakage canary and 95% CI;
- separate promotion selector approval within the weekly cap shown on the submission page.

None of these raster-specific gates has been run in this repository. The rejection “Predicted values must be in range [0, 1]” is consistent with any values outside that interval (including infinities) in the valid footprint; this checkout has no failed file to diagnose. The correct remedy is to validate the final pixels and compare metadata against the organizer's sample template, not to assume clipping alone solves other format errors.

## Evidence, sources, and access limits

| Claim / need | Source | What it verifies | What it does not verify |
|---|---|---|---|
| Fault-mapping objective, test labels concern faults absent from existing public USGS database, provided layers, DTI, submission requirements | [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Competition's published problem and metric specification | Any candidate score, hidden truth, or leaderboard receipt |
| Organizer baseline | [Official reference-solution repository](https://github.com/drivendataorg/gems-prize-reference-solution) | Public baseline implementation and setup documentation | That this local checkout contains its data or any competing project's tools |
| GeoDAWN magnetic/radiometric data and coordinated airborne lidar context | [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Official survey description, release DOI, and products | Exact competition-band files downloaded into this workspace |
| Free public DEMs and distribution | [USGS 3DEP products & services](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services) | USGS states 3DEP products are available free and without use restrictions | Local availability/coverage of particular 1 m tiles for each area |
| Project context | [INGENIOUS](https://gbcge.org/current-projects/ingenious/) | Official project context link supplied for this research | Any new fault truth labels |
| CRS definition | [EPSG:32611](https://epsg.io/32611) | UTM zone 11N identifier | Exact sample raster shape/transform |
| Public leaderboard snapshot | [Official DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) checked 2026-10-27 11:36 UTC | ORGANIZER-PUBLISHED PUBLIC LEADERBOARD: top displayed public score was 0.4544 at retrieval time | Private test / final-prize performance, persistence of that ranking, or any submission's receipt |
| Historical site names/scores | User-provided prompt and the linked site pages | Values as quoted in the request | Organizer confirmation unless a receipt is available |

**Access limitation:** the competition's data tab requires an authenticated account. This runtime has no DrivenData login and this checkout contains no files from that data tab. The prompt also mentions Dropbox links, but no contents of those links are included in this Git worktree. We will not claim to have downloaded, inspected, or validated them. USGS public availability is confirmed at the provider level, but no external DEM data have been fetched or coverage-checked for this work.

## Three-pass repository review and next steps

**Pass 1 — inventory:** `HEAD` is the initial commit and contains only `README.md` before this documentation; there is no code, tests, data, feature cache, registry, generated TIFF, or prior local history to review. That means there is no present implementation to execute or debug.

**Pass 2 — risks and missing requirements:** the requested “highest scoring” table mixes site-reported values with two contradictory overall leaderboard claims. No receipts are present. The named H33 artifact cannot be explained from its name or score, and uniqueness cannot be tested without raster bytes. A TIF created without the official grid would risk another portal rejection. Copying a prior TIF is explicitly out of bounds.

**Pass 3 — final requirements check:** this document provides the requested nine-site comparison, no fabricated score, explicit download/submission decision, 3–5 hypotheses with layers/signature/off-catalogue rationale/difference/cost/mimic, official source links, access blockers, and a no-go decision. It does **not** claim to have tested a hypothesis or produced a TIF. The former requires the approved shared toolchain and actual feature/label/registry/template data.

### Work required to unblock an actual experiment

1. Link or vendor by reference the approved shared template version (feature cache, evaluator, writer, and tests); preserve its provenance and fix defects there.
2. Make authorized competition data available to the runtime or provide a verified data-access mechanism; inventory and hash every input, including the organizer sample template and registry rasters.
3. Retrieve historical site rasters and receipts from the listed pages or artifact registry, record bytes/SHA-256, and verify which numbers are organizer receipts versus site-side metadata.
4. Reconcile the current leaderboard value against a dated official leaderboard page/receipt; do not use either conflicting number from the prompt as current truth.
5. Pre-register one candidate only, obey the three-experiment/two-hour budget, run all leakage/holdout/uniqueness checks, and generate a run card even for negative results.
6. Implement an automated report/download UI only once it can fail closed: “download for research” must never be presented as “OK to submit” unless every validation and promotion gate passes. A true competition-ready TIF is currently blocked, so none is linked here.

## Run card

This is a negative, no-run card. The experiment did not start because the required template tools, feature stack, labels, sample grid, and registry rasters are absent. The untested candidate ranking above is a proposal only; it is not an experiment result.

```json
{
  "hypothesis": "No candidate tested; experiment blocked by absent shared template and competition data.",
  "mechanism": "Not evaluated.",
  "named_non_fault_mimic": "Not selected; no experiment was run.",
  "holdout_dti": {
    "status": "NOT_RUN",
    "metric_label": "HOLDOUT-DTI",
    "evaluator_version": null,
    "withheld_positives": null,
    "estimate": null,
    "ci95": null
  },
  "correlation_overlap_vs_registry": {
    "status": "NOT_RUN",
    "preplacement_max_abs_rank_correlation": null,
    "preplacement_max_fraction_within_3px": null,
    "final_dot_max_abs_rank_correlation": null,
    "final_dot_max_fraction_within_3px": null
  },
  "raster_sha256": null,
  "validator": {
    "status": "NOT_RUN",
    "no_nan_inside_footprint": null,
    "values_in_range_0_1": null,
    "crs_match": null,
    "shape_match": null,
    "transform_match": null
  },
  "submission_name": null,
  "submission_note": "No TIF generated; required template data and validator are missing.",
  "verdict": "negative"
}
```
