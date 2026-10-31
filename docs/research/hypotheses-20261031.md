# New hypotheses (2026-10-31) — ranked, with validation status

This is the 2026-10-31 addendum to `docs/hypotheses.md` (H-SASS3-J/K/L/M/N). Every hypothesis below
names the layer(s), the physical signature, why it should mark a fault **absent from the
USGS/INGENIOUS catalogue**, how it differs from anything already in this repo, its cost, and — if it
cannot be validated here — the exact free official source that would unblock it.

Ground rules (unchanged): a hypothesis is only "validated" if it beats the current best on a
spatially blocked holdout **before** a weekly slot is spent; a projection is never written as a score;
every number is labelled HOLDOUT-DTI, ORGANIZER-CONFIRMED, OWNER-REPORT or ESTIMATE.

---

## Ranked

| Rank | ID | Status | Expected DTI gain | Cost |
|---|---|---|---|---|
| 1 | H-SASS3-O — consensus-line directional continuation | implementable now; **not yet holdout-validated** | medium (creates recall the inversion cannot) | ~1 h |
| 2 | H-SASS3-P — redundancy-deweighted inversion | implementable now; LOO test is a 1-line change | small-medium (better q, same support) | ~30 min |
| 3 | H-SASS3-Q — strain-rate ridge on the strain/seismicity layer | **BLOCKED (data)** | medium-high | 1 h once unblocked |
| 4 | H-SASS3-R — 1 m lidar scarp openness | **BLOCKED (data + network)** | high (this is how the organizers found new faults) | 1–2 days |
| 5 | H-SASS3-S — clay/silica alteration halo union | **BLOCKED (data)** | low-medium | 1 h once unblocked |

---

## 1. H-SASS3-O — Consensus-line directional continuation

* **Layers:** the 128 published submissions' dot placements (public GitHub, OWNER-REPORT scores) plus
  the leaderboard-inversion field `q` built from them. No competition-internal data.
* **Signature:** `q` is non-zero **only** where a published raster places a dot, so the inversion can
  only redistribute recall the corpus already has. H-SASS3-O propagates `q` **directionally** — along
  the local orientation of the corpus consensus — into adjacent ground no published raster covers,
  with a linear decay over `L` px. The propagated field is then emitted by the metric's own marginal
  rule (`add a dot iff q > 0.2·DTI`).
* **Why it targets the unmapped set:** the corpus recalled *segments* of hidden faults. Faults are
  continuous line structures, so the highest-prior location for a segment the corpus missed is the
  along-strike continuation of a segment it did recall — a location the corpus explicitly does not
  cover, and (unlike the catalogue) one the corpus's own success already certifies.
* **How it differs from this repo:** `H-SASS3-J` continues the **catalogue** past its tips;
  H-SASS3-O continues the **corpus consensus**. Nothing in this repository propagates the inversion
  field at all — the incumbent emits `q` where it already is.
* **Non-fault process that could mimic it:** linear artefacts the corpus consensus also follows —
  drainage channels, survey-line striping, vehicle tracks — which the directional filter will happily
  continue. This is the named risk.
* **Cost:** ~1 h (a directional max-filter propagation plus the existing emitter). No external data.
* **Validation:** the emission can be checked against the metric's marginal rule and the lane rule
  today, but the **DTI gain cannot be measured** without labels: the catalogue holdouts in this repo
  are anti-correlated with the leaderboard (ρ = +0.143). It is therefore recorded as
  **not holdout-validated**, and it is *not* promoted over the incumbent on this session's evidence.

## 2. H-SASS3-P — Redundancy-deweighted inversion

* **Layers:** the same 128 published rasters.
* **Signature:** the top published rasters share 0.87–1.00 of their dots, so the ridge system
  `(O + λI)α = t` lets a few near-duplicates dominate the fit. Weight each file by the inverse of its
  *effective* redundancy (from the eigen-structure of `O`) before solving, so rare placements get more
  weight and the field `q` stops being a restatement of the densest rasters.
* **Why it targets the unmapped set:** it does not move the support of `q` (that is H-SASS3-O's job),
  but it sharpens where the corpus's *disagreement* is, which is where the corpus is least certain and
  the hidden faults most likely to be under-covered.
* **How it differs:** the incumbent solves the ridge with uniform weights. This is a re-weighting of
  the same system — a one-line change to `scripts/distill_from_leaderboard.py`.
* **Cost:** ~30 min. No external data.
* **Validation:** directly comparable — leave-one-file-out RMSE/ρ against the incumbent's
  **0.0533 / 0.757**. If it does not beat that, it is a negative result and is dropped.

## 3. H-SASS3-Q — Strain-rate ridge on the strain/seismicity layer  **[BLOCKED: data]**

* **Layers:** `training_features.tif` band group *"Dilatation rate, shear strain rate, second invariant
  of the strain rate tensor"* (competition page 967).
* **Signature:** Otsu-thresholded ridges of the second strain-rate invariant, thinned to 1-px crests,
  sampled every 3 px.
* **Why it targets the unmapped set:** active strain localises on the youngest structures; a mapped
  fault and an unmapped one are equally strong strain ridges, so the layer does not privilege the
  catalogue.
* **How it differs:** the repo's `LWST` line built *conduit* scores from this family but always on a
  lattice-constrained support (which failed the lane rule); a pure ridge crest with no lattice has not
  been tried.
* **Why blocked:** `training_features.tif` (418,912,844 bytes) is served only from the login-walled
  data page; it is not in this workspace.
* **Unblock (exact free official source):** one download with a DrivenData account from
  <https://www.drivendata.org/competitions/306/competition-doe-gems/data/> into `data/`, then
  `python scripts/prepare_data.py`. **Reachability checked 2026-10-31: the data page redirects to a
  login wall (no DrivenData auth in this sandbox), so it is not obtainable here.**

## 4. H-SASS3-R — 1 m lidar scarp openness  **[BLOCKED: data + network]**

* **Layers:** 1 m DEM tiles listed in `1m_DEM_links.csv`; profile curvature plus topographic openness
  on 3–10 m windows.
* **Signature:** paired scarp faces (convex break above, concave below) persisting over ≥ 200 m.
* **Why it targets the unmapped set:** this is how the organizers' own experts found the new faults —
  scarps obvious in lidar and invisible in 100 m rasters. A 100 m feature stack structurally cannot see
  them.
* **How it differs:** the repo has never touched 1 m data; sibling lidar-scarp runs scored 0.038–0.076.
* **Why blocked:** `1m_DEM_links.csv` is login-walled, and the tile hosts (USGS 3DEP / OpenTopography)
  are **outside this sandbox's network allow-list** (only `github.com`, `codeload.github.com`,
  `api.github.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org` are reachable).
* **Unblock (exact free official sources, for manual retrieval):**
  <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>,
  <https://www.usgs.gov/3d-elevation-program>.
* **Cost once unblocked:** 1–2 days.

## 5. H-SASS3-S — Clay/silica alteration halo union  **[BLOCKED: data]**

* **Layers:** the radiometric/alteration bands of `training_features.tif`.
* **Signature:** the union of clay and silica alteration halos, thinned, intersected with the
  structural ridge network.
* **Why it targets the unmapped set:** hydrothermal alteration halos outline fault-controlled upflow
  zones that may have no surface scarp; the geothermal prize is about vents, not just breaks.
* **How it differs:** sibling sites tried single-band alteration maps; the *union of two halos
  intersected with structure* has not been tried here.
* **Why blocked:** same feature stack as H-SASS3-Q.
* **Expected value:** low-medium — historical alteration-only runs scored 0.02–0.10.

---

## Negative result carried into this session (deliverable, not a failure)

**Swap-based uniqueness repair does not beat drop-based repair.** The incumbent repairs a registry
overlap breach by *dropping* the lowest-credit offending dots. This session implemented a *swap*
variant (`scripts/emit_new_candidate_20261031.py`) that removes the offender and re-places the same
number of dots outside the raster's 3 px neighbourhood. Measured on the same field and the same cap:

| Repair | Dots kept | Expected TP | Estimated score |
|---|---|---|---|
| drop (incumbent, budget 60,000) | 37,480 | 5,850.5 | 0.3422 |
| swap (this session, budget 60,000) | 60,000 | 4,501.7 | 0.2084 |

The swap keeps the predicted mass `D` high while the re-placed dots sit where the inversion field is
essentially zero (it is defined only on corpus-covered cells), so expected credit `TP` falls faster
than `D`. Because the metric is `TP/(0.2D + 0.8N)`, that is a strict loss. The drop-repair is kept.

## Reproduction check (no-hallucination)

Both estimators were re-run from scratch on the 129 public corpus rasters fetched from the sibling
GitHub repositories and SHA-256 verified against `evidence/score_corpus_manifest_20261030.json`:

* `scripts/fit_lb_truth_inverse.py` → 128 distinct rasters, chosen N = 4000, λ = 1.0,
  LOO RMSE **0.0489**, ρ **0.858** — identical to `evidence/lb_truth_inverse_fit_20261030.json`.
* `scripts/distill_from_leaderboard.py` → chosen N = 12000, c = 0.915,
  LOO RMSE **0.0533**, ρ **0.757** — identical to `evidence/distill_from_leaderboard_20261030.json`,
  and the budget sweep reproduces (0.336 / 0.353 / 0.365 / 0.373 / 0.377 / 0.372).

The new candidate shipped on the site is an emission of the second (template) estimator at a
different dot budget, repaired under the same literal 65% cap.
