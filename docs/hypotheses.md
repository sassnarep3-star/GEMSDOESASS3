# Five ranked hypotheses (2026-10-30)

Every hypothesis below names the layer it uses, the physical signature it targets, why the signature should mark a fault
that is **absent from the USGS/INGENIOUS catalogue** rather than one that is already in it, and how it differs from what
this repository has already run. Ranking is by expected DTI improvement per unit of implementation cost, using the measured
score model in `evidence/score_estimate_20261030.json`.

Ground rules (from the task and the parallel-run protocol):

* a hypothesis is only "validated" if it beats the current best on a spatially blocked holdout **before** a weekly slot is spent;
* if a hypothesis cannot be validated without external data, the exact free official source is named and its reachability is checked;
* a projection is never written as a score.

Measured context that drives the ranking (all reproducible, see `docs/research/why-02778-20261030.md`):

* the exact metric caps a dot field with **no** enrichment (ε = 1) at ≈ **0.041** at any dot count;
* the nine focus-site files carry an implied enrichment of **4.1–5.3×** for the withheld faults, while measuring **ε = 0.13** for
  *catalogue* faults on the blocked holdout — i.e. their success cannot be explained by reproducing mapped structure;
* therefore **any** hypothesis that only re-states the catalogue cannot be expected to beat 0.28, and any hypothesis that
  extracts a signal which the catalogue does not already encode is worth its cost.

---

## 1. H-SASS3-J — Catalogue tip continuation at metric-matched spacing  **[SHIPPED]**

* **Layers:** public USGS Quaternary faults + INGENIOUS catalogue vector/raster.
  Source: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> (labels come from the USGS Quaternary
  fault maps and INGENIOUS), USGS GeoDAWN <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>,
  GBCGE INGENIOUS <https://gbcge.org/current-projects/ingenious/>.
* **Signature:** local strike, taken as the principal direction of the eight nearest mapped catalogue cells, extrapolated
  up to 8 × 400 m beyond each mapped cell, with any cell within 200 m of mapped ground rejected.
* **Why it targets the unmapped set:** the test labels are, by construction, faults the catalogue does not contain. Fault
  networks grow by tip propagation and segment linkage, so the highest-prior location for an unmapped fault is the
  along-strike continuation of a mapped one — a location the catalogue explicitly does not encode.
* **How it differs from this repo's history:** earlier runs (`LWST`, `GSD-HUA`, `BGK-PBE`, `unique-structural`) placed dots from
  feature surfaces or lattices inside the footprint; none used the catalogue's own strike geometry as the generator, and none
  passed the forward lane rule against a submission-scale field.
* **Cost:** ~20 s of CPU, no external data.
* **Validation (HOLDOUT-DTI, catalogue-recovery surrogate v1, exact metric, 747 withheld cells in 262 blocked 4 km blocks,
  95% block-bootstrap CI):** capture 0.0534 vs 0.0526 (uniform) and 0.0415 (jittered lattice) at equal budget — best of five
  strategies; enrichment ε = 1.55 at 24k dots, 1.30 for the released 44,923-dot file. Full table: `evidence/holdout_catalogue_20261030.json`.
* **Verdict:** shipped as `docs/downloads/gemsdoesass3-tipcont-disp44923-4px-20261030T0330Z.tif`.

## 2. H-SASS3-K — Relay-ramp and step-over bridging

* **Layers:** same catalogue; adds the spacing statistics of en-echelon segments (2 km threshold).
* **Signature:** where two mapped tips face each other within 2 km and their strikes overlap or are parallel, place dots in the
  relay zone between them.
* **Why it targets the unmapped set:** relay ramps host short, low-throw faults that regional-scale compilation drops; they are
  the classic "missing fault" in a Basin-and-Range compilation.
* **Difference from history:** none of this repo's generators bridges tips; `H-SASS3-J` only continues them outwards.
* **Cost:** small (pure geometry), already partly realised inside the shipped generator as gap densification.
* **Validation:** merged into H-SASS3-J; measured *no* separate gain on the catalogue holdout, so it is not claimed as an
  independent improvement.
* **Verdict:** folded in; not promoted separately.

## 3. H-SASS3-L — Strain-rate ridge extraction  **[BLOCKED: data]**

* **Layers:** `training_features.tif` band group "Dilatation rate, shear strain rate, second invariant of the strain rate tensor"
  (<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>).
* **Signature:** ridges of the second strain-rate invariant, thresholded by Otsu, thinned to one-pixel crests, sampled every 3 px.
* **Why it targets the unmapped set:** active strain localises on the youngest structures; a mapped fault and an unmapped one
  are equally strong strain ridges, so the layer does not privilege the catalogue.
* **Difference from history:** the repo's `LWST` line built *conduit* scores from this family but always on a lattice-constrained
  support, which is what failed the lane rule; a pure ridge crest with no lattice has not been tried.
* **Why blocked:** `training_features.tif` (418,912,844 bytes) is served only from the login-walled data page. It is not in this
  workspace; `data/restore_receipt.json` records an owner-mirror hash that was **not** used.
* **Unblock:** one download with a DrivenData account into `data/`, then `python scripts/prepare_data.py`.
* **Cost once unblocked:** ~1 h (ridge extraction + holdout).

## 4. H-SASS3-M — 1 m lidar scarp detection (curvature / openness)  **[BLOCKED: data + network]**

* **Layers:** 1 m DEM tiles listed in `1m_DEM_links.csv`; transform: profile curvature plus topographic openness on 3–10 m windows.
* **Signature:** paired scarp faces (a convex break above, concave below) that persist over ≥ 200 m.
* **Why it targets the unmapped set:** this is how the organizers' own experts found the new faults — scarps that are obvious in
  lidar and invisible in 100 m rasters. A 100 m feature stack structurally cannot see them.
* **Difference from history:** the repo has never touched 1 m data; `GEMSDOE47/50`-style lidar scarp runs in the sibling sites
  scored 0.038–0.076.
* **Why blocked:** `1m_DEM_links.csv` is login-walled, and the tile hosts (USGS 3DEP / OpenTopography) are outside this sandbox's
  network allow-list. Official sources named for manual retrieval:
  <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>,
  <https://www.usgs.gov/3d-elevation-program>.
* **Cost once unblocked:** 1–2 days (tiling, curvature, scarp classifier).

## 5. H-SASS3-N — Magnetic-basement depth discontinuity (Euler deconvolution)  **[BLOCKED: data]**

* **Layers:** reduced-to-pole magnetics, vertical and horizontal TMI gradients, top-of-crustal magnetic source depth.
* **Signature:** discontinuities in the Euler depth solution along lineaments — an abrupt basement offset without a surface scarp.
* **Why it targets the unmapped set:** buried faults have no topographic expression, so they are systematically missing from a
  surface-mapping compilation.
* **Difference from history:** sibling sites tried Euler depth clustering (GEMSDOE40: 0.035–0.098); this repo has not.
* **Why blocked:** same feature stack as #3.
* **Expected value:** low — the historical runs that tried it scored 0.02–0.10, below the family's 0.25–0.28.

---

## What is *not* on this list, and why

* **Re-using the 13GEMSDOE lattice support.** It is the highest-scoring support ever observed here (its children score
  0.245–0.278), but every field built on it overlaps the others at 88–100% within 3 px, so it is a duplicate by construction and
  cannot be submitted as a unique entry.
* **Copying any focus-site file.** Explicitly excluded by the task; also already scored.
* **Crowd-consensus placement** (aggregating sibling submissions into a prior and re-sampling it). It would raise expected
  score, but the lane rule caps dot overlap at 70% with any single registry raster, and this prior is exactly where that
  overlap is highest. It is the obvious next experiment if the owner relaxes the lane rule.
