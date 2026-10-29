# Next candidate hypotheses — 2026-10-29 (NOT VALIDATED, NO SCORE)

**Status:** research proposals only. None has a holdout result. The competition labels are not in
this workspace, so the spatially-blocked hide-and-recover evaluator cannot run. Nothing below is a
score, and nothing below should consume a submission slot.

**Layer names are taken from the official problem page** (fetched 2026-10-29):
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>. That page lists the
provided features as: surface conductivity and depth to the conductive base; detrended elevation and
its slope; dilatation rate, shear strain rate and the second invariant of the strain-rate tensor;
isostatic gravity anomaly and its slope; RTP magnetics, TMI, vertical and horizontal slope of TMI,
top-of-crustal magnetic source depth; and density of earthquakes.

**Overlap check:** the existing hypotheses are H-GASS3-1 to H-GASS3-5 in `docs/hypotheses.md`. The
headings there were checked. Where a candidate touches one of them, the overlap is stated.

## Ranking (qualitative; expected DTI gain cannot be estimated without labels)

| Rank | ID | Layer(s) | Target signature | Cost | Overlap with existing H-GASS3 | Gate needed |
|---|---|---|---|---|---|---|
| 1 | H-N1 | strain-rate 2nd invariant + earthquake density | ridge crests of strain where seismic density is also high, kept >300 m from the catalogue | M | partly H-GASS3-1 (slip–dilation physics) | labels + leakage canary |
| 2 | H-N2 | top-of-crustal magnetic source depth | lateral steps in source depth aligned with the NNE fabric | S | none (no existing hypothesis uses the depth layer directly) | labels + leakage canary |
| 3 | H-N3 | surface conductivity × depth to conductive base | lateral discontinuities in conductive-base depth coincident with alteration/clay caps | M | partly H-GASS3-2 (argillic alteration) | labels + leakage canary; playa mimic must be excluded |
| 4 | H-N4 | isostatic gravity slope | high-gradient lineaments with no matching RTP magnetic ridge | S | partly H-GASS3-4 (gravity–magnetic Euler) | labels + leakage canary |

## Per-hypothesis detail

**H-N1 — strain-rate ridges with seismic co-location.** Mechanism: active normal faults localise both
shear strain and micro-seismicity. The catalogue omits concealed faults, so the expected signal is
off-catalogue ridges in strain that coincide with seismic density. Mimic to test: quarry blasting or
subsidence features produce seismic density without fault geometry. Requirement: the catalogue-distance
mask must be applied before any feature is fitted.

**H-N2 — source-depth steps.** Mechanism: a fault offsets magnetic basement, so the depth-to-source
estimate steps across the fault. Mimic to test: lithologic contacts such as intrusive margins and flow
edges. Cost is low because the layer is already provided.

**H-N3 — conductive-base contacts.** Mechanism: fault zones with alteration clay or upwelling fluid
can show a conductive-base step. Mimic to test: Lake Lahontan shoreline and saline playa clays, which
the existing LWST notes already flag as confounders.

**H-N4 — gravity-slope lineaments without magnetic counterpart.** Mechanism: a density contrast
across a concealed fault that has no magnetic expression. Mimic to test: lithologic density contrasts.

## Metric note (already implemented; not a new finding)

Under the official formula, DTI = TP / (TP + 0.2·FP + 0.8·FN). The marginal inclusion rule
`marginal_inclusion_threshold(current_dti) = 0.2 × current_dti` is already in
`src/gems32/metric.py`. A pixel is worth adding only if its kernel credit exceeds that threshold.
At an achieved DTI near 0.28 this is about 0.056, so a dense-but-calibrated map can beat a sparse one.
This is an approximation for a single added pixel, and it has not been checked against labels.

## What is needed before any of this can be validated

1. **Labels for the holdout.** The official `labels.tif` requires DrivenData login. A copy is publicly
   hosted in a sibling repo; see the irregularities ledger. Its use has not been approved.
2. **Free external layers, if used.** The 1 m DEM link list is login-walled on DrivenData, and the
   Dropbox links in the prompt were not verified from this sandbox. USGS and other public sources are
   not on the outbound allow-list. Each proposed source must be obtained and hash-checked before use.
