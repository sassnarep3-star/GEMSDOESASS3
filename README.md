# GEMSDOESASS3 — research and submission readiness

> **Read this file at the start of every project session.** It is the project charter, current evidence ledger, and fail-closed submission decision. Update evidence with dated, reproducible records; do not silently replace old results.

## Executive decision (2026-10-27)

**No submission TIFF was generated in this checkout. There is no file here that is approved to download or submit.** The repository currently contains only this README: no model code, data, cached features, evaluator, writer, registry rasters, tests, run cards, or TIFFs. Consequently we cannot run a holdout, measure uniqueness, validate the competition grid, diagnose the reported `[0, 1]` error, or truthfully estimate an entry's competition score. Do not spend a DrivenData submission slot on a historical TIFF or on a file generated without those checks.

The task is research-and-validation first, not file-generation-at-any-cost. A candidate can be **downloadable for research** while still being **not approved to submit**. A local format pass, a projected score, or a historical score is not submission authorization. The inherited GitHub Pages landing page is [`docs/index.html`](docs/index.html); its detailed public-facing brief is [`docs/EXECUTIVE_SUMMARY.md`](docs/EXECUTIVE_SUMMARY.md). Keep both aligned with this README, which is the session-start source of truth.

## Project charter — carry forward the user's requirements

Build an auditable, automated DOE GEMS fault-discovery workflow that can generate a single-band GeoTIFF and make the download/submit decision obvious. Study the nine named project sites and their highest reported results; explain the H33 result without overclaiming; form distinct, scientifically grounded hypotheses; and only promote a new candidate after a spatially blocked validation and uniqueness audit. Keep official-source references, methods, assumptions, negative findings, and limitations in the repository. Avoid manual inspection as a required gate: a human may review the evidence, but automated checks must be reproducible and fail closed.

Core decision principles:

- **Maximize P(Win):** choose evidence-backed experiments over slot-consuming guesses; do not mistake a leaderboard number or a proxy for scientific validation.
- **Own the Outcome:** preserve failed results, diagnose our own tooling, and repair shared/template code rather than maintaining a private fork.
- **No hallucinated evidence:** label each score by evidence class; cite official sources for competition rules and data facts; distinguish current public facts from user-supplied claims and project-site claims.
- **Uniqueness is a gate, not a filename:** before placement and on final predictions, compare with every available registry raster. Stop and log a duplicate if rank correlation exceeds 0.90 or if over 70% of dots lie within 3 pixels of a registry raster. Do not move dots just to evade the test.

### Required experimental protocol

1. **Stay in the assigned method lane.** The prompt refers to a “single method paragraph,” but no unambiguous assigned paragraph is present in the supplied task. Record the lane as unassigned and do not run experiments until a single lane is explicitly represented in the shared template/registry. The budget for this review is 0 of 3 experiments.
2. **Reuse the shared template.** Use its cached feature stack and shared `evaluate_holdout.py` / `submission_writer.py` (or their actual canonical names). Do not create a private fork. Those tools are absent from this checkout, so none was substituted or improvised here.
3. **Holdout = hide and recover.** Withhold whole fault segments with a buffer; derive catalogue-based features only from visible faults; mask visible faults pixel-exactly; then compute pooled distance-weighted Tversky with α=0.2, β=0.8, and a 300 m triangular kernel. Record evaluator version, withheld-positive count, and a spatial-block 95% CI for every HOLDOUT-DTI value. A public/private leaderboard score is not a holdout score.
4. **Leakage canary.** Evaluate each candidate feature alone on the holdout; treat AUC > 0.90 as leakage until disproved.
5. **Three-experiment / two-hour ceiling.** Stop at whichever limit arrives first. Do not choose or upload a submission; weekly-slot promotion is a separate selector step after checking the portal cap.
6. **Run card required.** End every experiment with one JSON card covering hypothesis, mechanism, a named non-fault mimic, HOLDOUT-DTI and CI, registry correlation/overlap, raster SHA-256, validator result, submission name/note (≤140 characters), and `promote` or `negative`. Negative results are deliverables.

## Nine-site executive summary

The following are the highest values supplied in the user's project brief for the requested sites. They are **USER-REPORTED historical scores**; no submission-page receipt binding score to file bytes was supplied or retrieved. They are not HOLDOUT-DTI, not organizer-confirmed in this review, and not valid estimates of a new candidate's competition score. For every row, a defensible new-entry score estimate is **NOT ESTIMABLE** without a validated transfer model and current private labels. The project-maintained GEMSDOE28 public page reports that all 72 directional comparisons among these nine historical rasters exceeded 86.72% within-3-pixel dot overlap; this is a published claim, not a fresh byte-level audit by this empty checkout. Under the requested >70% lane stop, treat these historic candidates as **not unique/NOT FOR RESUBMISSION** until an independent registry audit says otherwise.

| Site | Highest result in the supplied brief | Historical artifact / source | New-entry score estimate | Unique under the requested lane gate? | Action |
|---|---|---|---|---|---|
| GEMSDOE24 | 0.2477 — USER-REPORTED | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` · [site](https://buffedlizard55-lab.github.io/GEMSDOE24/) | NOT ESTIMABLE | No — published cross-site overlap report flags the nine-raster set; not independently recomputed here | Historical only; do not resubmit |
| GEMSDOE25 | 0.2600 — USER-REPORTED | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` · [site](https://buffedlizard55-lab.github.io/GEMSDOE25/) | NOT ESTIMABLE | No — same caveat | Historical only; do not resubmit |
| GEMSDOE27 | 0.2449 — USER-REPORTED | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` · [site](https://buffedlizard55-lab.github.io/GEMSDOE27/) | NOT ESTIMABLE | No — same caveat | Historical only; do not resubmit |
| GEMSDOE28 | 0.2710 — USER-REPORTED | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` · [site](https://buffedlizard55-lab.github.io/GEMSDOE28/) | NOT ESTIMABLE | No — same caveat | Historical only; do not resubmit |
| GEMSDOE30 | 0.2600 — USER-REPORTED | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` · [site](https://buffedlizard55-lab.github.io/GEMSDOE30/) | NOT ESTIMABLE | No — same caveat | Historical only; do not resubmit |
| GEMSDOE31 | 0.2708 — USER-REPORTED | `h27-4-solo-d28-20261004-8acb75e1-nan` · [site](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | NOT ESTIMABLE | No — same caveat | Historical only; do not resubmit |
| GEMSDOE32 | 0.2778 — USER-REPORTED | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` · [site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | NOT ESTIMABLE | No — same caveat | Best reported historical anchor; already historical, do not copy or resubmit |
| GEMSDOE33 | 0.2632 — USER-REPORTED | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` · [site](https://buffedlizard55-lab.github.io/GEMSDOE33/) | NOT ESTIMABLE | No — same caveat | Historical only; do not resubmit |
| GEMSDOE36 | 0.2750 — USER-REPORTED | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` · [site](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | NOT ESTIMABLE | No — same caveat | Historical only; do not resubmit |

**There is no “best file to submit” among these nine historical files.** On the supplied historical claims, GEMSDOE32's 0.2778 is the numerical maximum, but numerical rank does not override the uniqueness and fresh-validation gates. The site pages themselves contain newer research artifacts and conflicting/dated submit-status statements; those artifacts are not imported into this repository and are not authorized by this review.

### H33 / 0.2778: what can and cannot be concluded

The competition's official metric rewards predictions near held-out fault pixels using a 300 m triangular distance kernel and sets α=0.2, β=0.8, so false negatives are penalized more heavily than false positives. That makes a broad, well-placed prediction field a plausible reason for a high value; a sparse/“dotted” representation may also allocate a fixed prediction budget toward locally promising structures. Those are **mechanistic hypotheses**, not a verified explanation of this specific score. A single score cannot show which feature or geological mechanism caused it, and historical site names are not enough to recover the exact algorithm, input bytes, split, or receipt. The value 0.2778 is USER-REPORTED in the supplied brief, not ORGANIZER-CONFIRMED here.

The current official public leaderboard was observed at **0.4544** for rank 1 on 2026-10-27 (official live page; volatile public score, not this project's result). Thus the user-provided historical benchmark `0.3195` / `0.4413` is not current as observed during this review. No score target or estimate for a new candidate follows from this comparison. See the [live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).

## Candidate hypothesis queue — preregistration only, no experiment run

The checkout has no existing implementation, so all candidates below differ from code currently in this repository. That does **not** establish novelty across the GEMSDOE site family: their full code, feature registries, and raster registries are not present here. Rank/cost are provisional prioritization, not measured DTI improvements. Use the official shared cache first; audit prior methods and registry rasters before any fit or placement.

| Rank | Hypothesis and specific layers | Target signature / why it could find an unrecorded fault | Difference from this checkout and known uncertainty | Named non-fault mimic | Cost / expectation |
|---|---|---|---|---|---|
| 1 | **Radiometric alteration-boundary coherence:** GeoDAWN airborne radiometric channel products (verify from the chosen release's metadata whether K, equivalent-U, and Th channels are present); if available, derive log-ratios (e.g., K/eTh, eU/eTh) and multiscale cross-channel gradients, conditioned on survey/flight-line seam masks. | A coherent, narrow geochemical boundary or asymmetric alteration halo can mark fluid-rock interaction along a concealed structure not yet represented in the USGS/INGENIOUS fault catalogue; require independent support across ratios and scales rather than a single high count. | No radiometric workflow exists in this checkout. The official USGS GeoDAWN release describes radiometric products, but the exact competition stack bands and file access must be verified from local metadata. Not proven untried on GEMSDOE sites. | Lithologic contact, transported regolith, playa/soil chemistry, radon or survey-height/flight-line residual. | **Moderate cost; moderate expected value, high confounding risk.** Obtain/verify official USGS products if not in the cache; free public CC0 release described by USGS. |
| 2 | **Multi-scale basement-relief hinge:** supplied RTP/TMI and isostatic-gravity anomaly, plus top-of-crust magnetic source depth and conductivity/depth-to-base bands. | A paired change in edge orientation/curvature and source-depth gradient across scales may expose a buried fault-controlled basin-margin hinge, not merely a mapped surface trace. | No code exists here; this is not a claim of novelty across other projects, many of which already test magnetic/gravity edges and structural proxies. | Unfaulted lithologic boundary, intrusive body, basin-fill thickness change, or survey seam. | **Low-to-moderate cost; low-to-moderate expectation.** Use provided feature stack; no external data if all bands are present. |
| 3 | **Drainage-deflection and scarp polarity, stratified by terrain regime:** competition 1 m DEM links or official USGS 3DEP DEM, detrended elevation and slope; extract channel-bend/valley-asymmetry and multi-scale curvature, then require an independent geophysical lineament. | Persistent channel deflection or aligned scarps across several catchments can indicate young, unmapped surface rupture; matching a potential-field signal reduces the chance of simply mapping erosional lineaments. | No implementation in this checkout. Topographic gap/scarp concepts already appear in supplied historic candidate names, so the proposed joint catchment-scale test may overlap prior art and is not presumed novel. | Alluvial-fan margins, shoreline benches, roads/canals, landslide toes, lithologic resistance contrasts. | **Moderate-to-high cost; moderate expectation.** Use the official competition-linked DEM URLs if locally licensed/available; no data are present here. |
| 4 | **Strain-orientation / basement-edge concordance without catalogue-derived inputs:** geodetic dilatation, shear-strain tensor, second invariant, earthquake density, magnetic source depth and gravity gradients. Test fold-safe local orientation agreement and spatial continuity rather than raw high values. | A continuous, independent deformation corridor coincident with a basement discontinuity is more consistent with an active buried structure than either layer alone and can extend beyond mapped traces. | No implementation in this checkout; the supplied GEMSDOE33 page describes a strain/seismicity attempt, so this candidate is not clearly novel and must be audited before use. | Volcanic/caldera deformation, aquifer compaction, non-tectonic seismic swarm, broad regional strain field. | **Moderate cost; low-to-moderate expectation.** Only viable if the feature stack has these bands and leakage canaries pass. |

**Do not run this queue yet.** First recover the canonical shared template and data; identify the lane that was actually assigned; inventory existing code and registered rasters; preflight exact template grid and cache. If a candidate relies on an external source, confirm its downloadable item, license, coverage, and reproducible retrieval before fitting. The USGS GeoDAWN source is a free official candidate source: [USGS data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) (DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)); the USGS page states that it includes magnetic/radiometric grids and geotiff products and marks the work CC0. The official competition page also permits additional sources with a license allowing challenge use and sharing with the sponsor.

## Submission contract and reported range error

The official problem page requires one single-band 32-bit float GeoTIFF, EPSG:32611, 100 m, same bounds/grid as training data, prediction values in `[0,1]`, and null/NaN outside the bounds. A file with zero-valued exterior cells may meet a numeric range check but does **not** match the stated exterior-data requirement; do not advertise zero-fill as a fix. The reported portal error cannot be diagnosed without the rejected file bytes and matching sample/template metadata. No automated validation has run here.

Before presenting a download as **OK TO SUBMIT**, the shared validator must reopen the final written TIFF and verify at minimum:

- one band, float32; CRS exactly EPSG:32611; resolution/bounds/shape/affine transform match the official sample raster;
- all in-footprint predictions finite and within `[0,1]`; outside-footprint pixels are null/NaN as required;
- no visible-catalogue leakage; exact visible-fault mask; hash of final bytes recorded;
- all individual feature AUC canaries ≤0.90; pooled holdout/CI and paired comparisons recorded;
- pre-placement surface and final raster/dots pass comparisons against the complete registry at ρ≤0.90 and ≤70% within-3-pixel overlap;
- immutable run card, reproducible command, and separate slot-selector approval.

Passing these gates is necessary, not proof that DrivenData will accept a file. The portal's current weekly cap is only knowable from the authenticated submission page; this repository must not invent it or claim a slot is approved.

### Submission steps for the future authorized file

1. Open the competition's authenticated **New submission** page and check the current weekly allowance.
2. Download only the artifact marked `OK TO SUBMIT` by the latest run card; verify its SHA-256 against that card. Do not use a historical site link or research-only file.
3. Upload the `.tif` (or a ZIP containing exactly one GeoTIFF if needed), enter the unique run name and its ≤140-character note, then submit.
4. Save the submission-page receipt and organizer score as separate evidence. Label a score copied from that receipt `ORGANIZER-CONFIRMED`; do not relabel a local holdout or a projection.
5. Do not upload if the selector says `negative`, `unknown`, `research only`, `duplicate`, or `not authorized`.

## Evidence sources for manual review

| Source | What it supports | Scope/limit |
|---|---|---|
| [DrivenData problem description and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Task is prediction of faults missing from public catalogue; labels/data context; feature description; DTI, kernel, and TIFF format | Official challenge description; not proof of this repo's model performance |
| [DrivenData competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/) | Entry rules and competition context | Check the live authenticated page for slot/quota and any current changes |
| [Official live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Volatile public standings; observed top 0.4544 on 2026-10-27 | Public score, not private/final score, holdout, or organizer receipt for our file |
| [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) | Officially linked baseline code and workflow | Must inspect and reuse the canonical template/tools, not assume they exist in this checkout |
| [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) / [DOI](https://doi.org/10.5066/P93LGLVQ) | Public magnetic/radiometric survey data; associated lidar/topography; CC0 status stated by USGS | Separate source from competition-provided files; verify exact product, coverage, and local license records |
| [INGENIOUS project](https://gbcge.org/current-projects/ingenious/) | Official project context named by the competition | Does not substantiate any candidate score |
| [EPSG:32611](https://epsg.io/32611) | CRS definition | Confirm the actual file transform from the competition sample, not EPSG name alone |
| [DOE/NREL challenge PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Challenge documentation supplied in user prompt | Cross-check details against the current official DrivenData submission-format page |
| [GEMSDOE32 site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) and other nine-site links above | Project-published artifacts and claims for audit | Third-party project pages, not the organizer. Their scores/statuses may be stale or conflict internally; independently verify bytes and receipts. |

## Repository review and blockers

- **Verified local state:** at review start the current branch was clean and tracked only `README.md` (14 bytes); history contained only the initial commit. Therefore there is no implementation to review, no tests to run, and no generated TIFF to validate.
- **Training/data blocker:** no competition data, template cache, holdout labels, sample submission, or permitted external layer is in this checkout. The user reports that DrivenData data download needs login; this review did not authenticate or try to bypass access controls. No credentials are requested or stored.
- **Shared-tool blocker:** `evaluate_holdout.py`, `submission_writer.py`, and an agreed shared template are absent; the instruction to reuse them cannot currently be satisfied.
- **Registry blocker:** no complete raster registry or dot inventory is local. Public site contents alone cannot prove uniqueness against all earlier submissions, especially if artifacts are missing or site pages change.
- **Evidence irregularities:** the user-supplied current leaderboard anchors 0.3195 and 0.4413 conflict with one another and with the official live page observation (0.4544 on 2026-10-27). The GEMSDOE36 page first labels a later KPL-36 artifact “OK to submit,” but later on that same page says the literal registry/lattice overlap makes the standard dot budget fail and describes artifacts as research-only; these statements conflict and the site's own later caveat blocks reliance on the earlier green status. GEMSDOE28 also distinguishes a research artifact from selector approval. Project Pages contain current and historical status statements that can conflict; only a byte-bound current run card plus the official submission receipt can resolve file-specific claims. A public site saying a TIFF is “OK to submit” is not sufficient.
- **No independent science claim:** the official source confirms data context and metric, but does not validate the proposed hypotheses or explain H33's observed score. All four hypotheses are preregistration candidates, not findings.

## Next steps (ordered; no submission slot)

1. Bring the canonical shared-template repository or its required files into this project through the intended shared workflow; do not create private copies. Record exact commit/version and tool paths.
2. Place authorized competition data in the documented `data/` location and inventory checksums/metadata: training features, labels/existing faults, sample submission, and official DEM link list. Do not bypass DrivenData authentication. Check the source and use license for every external file.
3. Run a read-only preflight to confirm feature stack presence, grid/footprint, available evaluator/writer, all needed registry rasters, and lane assignment. If any prerequisite is missing, emit a negative run card and stop before feature engineering.
4. Archive exact bytes + provenance for the nine historical leading submissions and the larger registry; independently measure surface rank-correlation before placement and dot overlap after placement. The reported 0.2778 must be tied to a submission-page receipt before calling it organizer-confirmed.
5. Preregister exactly one allowed candidate in the shared template; run feature-only leakage tests, spatially blocked hide-and-recover holdout, paired CI versus the current same-evaluator holdout best, final-format validation, and novelty checks. Stop immediately on the lane duplicate threshold. Do not exceed 3 experiments or 2 hours.
6. Only if every gate passes, let the separate selector decide whether a weekly slot is available. Then generate/download the exact validated TIFF, copy its unique name and ≤140-character note, and retain the organizer receipt.
7. Add tested code, a clean user-facing executive summary/site, automated current-feed updates, CI checks, and a record of failed experiments after the evidence pipeline exists. Until then, a polished upload button would imply a capability this repo does not have.

## Review run card (this checkout)

```json
{
  "hypothesis": "No geological candidate was executed: the shared template, assigned method lane, data, and registry are absent from this checkout.",
  "mechanism": "Review-only; no feature derivation, placement, model fit, or raster write was performed.",
  "named_non_fault_mimic": "Not applicable: no prediction surface was generated.",
  "holdout_dti": {
    "status": "NOT RUN",
    "evaluator_version": null,
    "withheld_positive_count": null,
    "95_percent_ci": null
  },
  "correlation_overlap_vs_registry": {
    "status": "NOT MEASURED: registry rasters are absent",
    "max_absolute_rank_correlation": null,
    "max_fraction_of_dots_within_3px": null
  },
  "raster_sha256": null,
  "validator_output": {
    "status": "BLOCKED: no TIFF generated",
    "no_nan_inside_footprint": "unknown",
    "values_in_0_1": "unknown",
    "crs_shape_transform_match": "unknown"
  },
  "submission_name": null,
  "submission_note": "No TIFF generated; no file is approved to download or submit.",
  "verdict": "negative"
}
```
