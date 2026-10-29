# Protocol amendments

Only amendments recorded here are in force. Every amendment needs an explicit owner decision and a date.

## PROPOSED-20261028-A — like-for-like reading of Rule 1 (NOT APPLIED)

Status: **PROPOSED. Not applied.** The owner must record the decision (Option A in
`docs/research/lattice-decision-20261028.md`). Until then, every gate keeps the literal reading and every focus-site
file stays blocked.

Draft text for the owner to accept, amend, or reject:

> Rule 1 (uniqueness). A submission is a duplicate if more than 70% of its dots lie within 3 px of the dots of any
> registry raster, EXCEPT that a registry raster whose 3-px halo covers more than 90% of footprint cells
> (`HALO_SATURATION_FRACTION` in `vendor/gems57/uniqueness.py`) is excluded from the dot-overlap test. Rank
> correlation (Spearman > 0.90 on the surface or on the dots) still applies to every registry raster, including
> halo-saturated ones. Halo-saturated rasters must be listed in the run card with their measured coverage.

Rationale: the literal dot-overlap test on a space-filling calibration lattice measures geometry, not lane. On the
measured footprint, the 13GEMSDOE lattice covers 99.87% of cells within 3 px, so any dense dot field fails. See
`evidence/lattice_bound_audit_20261028.json`.

Recorded by: ____________ (owner) on ____________ (date). Decision: ACCEPT / AMEND / REJECT.
