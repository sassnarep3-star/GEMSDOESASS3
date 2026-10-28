# GEMSDOESASS3 — read first

**Current decision: DO NOT SUBMIT.** The archived candidate fails the literal parallel-run registry-overlap rule. Its local range and grid checks do not establish scientific performance, uniqueness, or organizer acceptance. See the [executive summary](docs/executive-summary.html) and [review](docs/research/review-20261028.md).

**Independent review (2026-10-28):** the format gate passes (recomputed from the raster). Uniqueness on the 451 submitted downloads passes (max within-3 px overlap 66.53%). The literal registry rule, which includes the calibration lattice, **fails** (99.78% against a 70% limit), so the file is **NOT OK to submit**. At this dot count the literal rule cannot be met by any raster: only 5,379 footprint pixels lie outside the lattice buffer, and passing needs at least 11,297 dots there. This needs an owner decision on the calibration lattice. Earlier claims that it beats the 0.2778 champion are withdrawn: LWST SGMC-CAL 0.065702 [0.058992, 0.071240] against the champion 0.064121, with overlapping intervals. The archived note's `HR=0.1111` is a per-fold OOF value; the file's static HIDE-RECOVER value is 0.006130. Sibling links that pointed to `sassnarep3-star` (404) are repointed to `buffedlizard55-lab`. Full review, corrections, per-site table, ranked hypotheses and limitations: [docs/research/independent-review-20261028.md](docs/research/independent-review-20261028.md).

The project's standing prompt as recorded in a previous session is [here](docs/research/standing-prompt-as-recorded-20261027.md); read it before starting work. The current request adds the **PARALLEL-RUN PROTOCOL** and the requirement **MUST GENERATE A UNIQUE TIF SUBMISSION**: fail closed on any registry overlap above 70% or rank correlation above 0.90, check both surface and dots, run leakage canaries and buffered hide-and-recover, limit experiments, and leave final promotion to a separate selector. Do not interpret a failed uniqueness gate as permission to submit. Optimize for outcome, document uncertainty, and never fabricate a score.

Historical archive only: `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` · SHA-256 `bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a` · prior note `GEMSDOESASS3 LWST-GeoConduit EXP3: 3D SPI+WijnsTheta+DualHGB300m 37654d B=2 HR=0.1111 SGMC=0.0657`.

Current submission note (122 characters, from `evidence/current_run_card.json`): `LWST-GeoConduit 37654 dots, B=2: format-valid. Literal lattice rule fails (99.8%). Score NOT established; HR unreproduced.` · status: **DO NOT SUBMIT** (literal registry-overlap rule fails; see IR-SASS3-19).

## 🎯 Core Values (focal point of every session)

1. **Maximize P(Win).** Every decision is judged by its effect on the probability of finishing first on the DrivenData GEMS leaderboard, not by how good a document looks. Ship only what can be checked; prefer a verified small gain to an unverified large one.
2. **Own the Outcome.** Report negative results and irregularities plainly, correct claims that do not reproduce, and state exactly what remains unknown. Nothing is labelled a score unless it is reproduced or organizer-confirmed.

Recomputed claims for 2026-10-28 (with the per-site table): [`docs/research/recomputed-claims-20261028.md`](docs/research/recomputed-claims-20261028.md). Main-branch review: [`docs/research/review-20261028.md`](docs/research/review-20261028.md).

## Reproduce checks

Create a Python virtual environment and install `numpy scipy scikit-learn rasterio pytest`. Run `python scripts/verify_all_gates.py`: a nonzero exit is expected while the candidate is blocked. CI runs `python scripts/verify_all_gates.py --expect-blocked`, which succeeds only for the documented blocking failure. Run `pytest -q`. `python scripts/build_review_site.py` refreshes the static pages; legacy page builders are disabled to prevent their outdated approval claims from returning.

[Competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) · [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) · [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution). Raw data and caches are not included in this checkout; restore receipts are historical and mirror hashes do not authenticate organizer provenance.
