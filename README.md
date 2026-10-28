# GEMSDOESASS3 — read first

**Current decision: DO NOT SUBMIT.** The archived candidate fails the literal parallel-run registry-overlap rule. Its local range and grid checks do not establish scientific performance, uniqueness, or organizer acceptance. See the [executive summary](docs/executive-summary.html) and [review](docs/research/review-20261028.md).

The project's standing prompt as recorded in a previous session is [here](docs/research/standing-prompt-as-recorded-20261027.md); read it before starting work. The current request adds the **PARALLEL-RUN PROTOCOL** and the requirement **MUST GENERATE A UNIQUE TIF SUBMISSION**: fail closed on any registry overlap above 70% or rank correlation above 0.90, check both surface and dots, run leakage canaries and buffered hide-and-recover, limit experiments, and leave final promotion to a separate selector. Do not interpret a failed uniqueness gate as permission to submit. Optimize for outcome, document uncertainty, and never fabricate a score.

Historical archive only: `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif` · SHA-256 `bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a` · prior note `GEMSDOESASS3 LWST-GeoConduit EXP3: 3D SPI+WijnsTheta+DualHGB300m 37654d B=2 HR=0.1111 SGMC=0.0657`.

## Reproduce checks

Create a Python virtual environment and install `numpy scipy scikit-learn rasterio pytest`. Run `python scripts/verify_all_gates.py`: a nonzero exit is expected while the candidate is blocked. CI runs `python scripts/verify_all_gates.py --expect-blocked`, which succeeds only for the documented blocking failure. Run `pytest -q`. `python scripts/build_review_site.py` refreshes the static pages; legacy page builders are disabled to prevent their outdated approval claims from returning.

[Competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) · [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) · [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution). Raw data and caches are not included in this checkout; restore receipts are historical and mirror hashes do not authenticate organizer provenance.
