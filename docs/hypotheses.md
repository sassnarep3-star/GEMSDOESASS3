# Hypotheses for the next authorized experiment — 2026-10-31

**Current verdict: proposals only. No experiment was run in this review and no numerical DTI forecast is supportable.** Read the [full repo review](research/repo-review-20261031.md#candidate-hypothesis-slate--proposals-only-not-tested) for layer details, physical rationale, mimics, source access checks and the exact blocking conditions.

| Rank | Proposal | Signature / layers | Expected DTI improvement (qualitative) | Cost | Status |
|---:|---|---|---|---|---|
| 1 | H-R31-1: 1 m DEM paired-scarp profile asymmetry | Multiscale paired profile-curvature breaks from the source DEM; compare with 100 m `det_elev` / `det_elev_slope` | Potential moderate–high; **not measured** | High | Blocked until the official `1m_DEM_links.csv` and tile coverage are restored; USGS GeoDAWN/LiDAR release is official/public, but exact competition tiles are not locally verified. |
| 2 | H-R31-2: gravity–magnetic edge phase lag | Scale-dependent signed cross-wavelet phase from `iso_grav_anom` / `iso_grav_anom_hg` and `rtp` / `tmi` / `tmi_hg` | Potential moderate; **not measured** | Medium–high | Inputs are competition features; cache and preregistration needed. Conceptual overlap with older multichannel concordance needs review. |
| 3 | H-R31-3: signed geodetic dilation nullcline networks | Zero-crossing curves in signed `geod_dilaterate`, checked for persistence and intersections with `geod_shearrate` / `geod_2ndinv` | Potential low–moderate; **not measured** | Low–medium | Existing layers suffice once cache is restored; resolution/artifacts are major risks. |
| 4 | H-R31-4: gravity-edge / basement-depth change points with magnetic-negative control | Alignment of `iso_grav_anom_hg` / `iso_grav_anom_vg` with `depth_to_base_surf`; use `tmi_hg` as a negative/control channel | Potential low–moderate; **not measured** | Medium | Lower novelty due overlap with prior gravity lineament proposals. |

These are qualitative priorities, not leaderboard predictions or scores. No proposal may be implemented until the exact lane/method paragraph is recovered, data and dependencies are available, and the shared leakage canary and spatially blocked holdout are runnable. Do not spend a submission slot on a hypothesis that has not beaten the same-version holdout best; preserve the three-experiment/two-hour budget.

## Official sources

- [DrivenData problem description and supplied feature layers](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [USGS GeoDAWN airborne magnetic, radiometric and coordinated LiDAR release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — DOI 10.5066/P93LGLVQ
- [INGENIOUS project and cited Great Basin releases](https://gbcge.org/current-projects/ingenious/)
