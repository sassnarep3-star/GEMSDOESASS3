# GEMS Field Notes

> **Current decision: DO NOT SUBMIT.** No new competition TIFF or score was produced. The usual 37,654-dot budget cannot satisfy the literal registry rule, the required assigned method paragraph and cached feature stack are missing, and shared-template defects are unresolved. [Executive guide](executive-summary.html) · [Detailed review](research/REVIEW.md) · [Run card](evidence/run_card.json).

## Standing user brief — read at the start of every session

The full conversation is the authoritative prompt. The following preserves the operative request and protocol here; it is a concise record, **not a claim that every repeated passage and all historical submission names have been transcribed verbatim**. A [prior partial prompt record](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/1398109a23f04a2ace71c1bd2f527cfba87860b5/docs/research/standing-prompt-as-recorded-20261026.md) also warns that its completeness is unverified.

> Review the repo. Focus on the highest scoring submissions from GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33 and GEMSDOE36. Provide a clear executive summary, a unique new competition TIFF, its estimated score, uniqueness evidence, and an obvious download/submit decision. Do not copy a previous submission except for learning and education. Perform validation through the project without a human geological inspector. The user reported a prior portal rejection: “Predicted values must be in range [0, 1]”. Give any eventual candidate a unique name and a short note (at most 140 characters).
>
> Before implementing, generate 3–5 candidate geological hypotheses, naming layers, physical signature, why they could catch a fault missing from the catalogue, differences from existing work, expected improvement and cost. Verify any external data source is free, official and obtainable before describing it as viable. Validate the top candidate on a spatially blocked holdout and beat the current comparable best before considering a weekly submission slot. Do not invent an organizer score or present a projection as a score.
>
> **PARALLEL-RUN PROTOCOL — read first.** This session is one of several running from this same prompt.
>
> 1. **LANE.** Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds 0.90, or more than 70% of your dots fall within 3 px of one registry raster's dots, log it as a duplicate and stop. Check this on the surface before placement AND on the final dots.
> 2. **REUSE, DON'T REBUILD.** Use the template's cached feature stack, `evaluate_holdout.py` and `submission_writer.py`. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.
> 3. **LABEL EVERY NUMBER** as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score. Historical values supplied by the user without receipts must instead be identified as unverified reports, not mislabeled as either evidence class.
> 4. **LEAKAGE CANARY.** Test each feature alone on the holdout before trusting any result. AUC above 0.90 means leakage until proven otherwise.
> 5. **RUN CARD.** End with one JSON card: hypothesis; mechanism; named non-fault mimic; holdout DTI + CI; correlation/overlap vs registry; raster SHA-256; validator output (no NaN inside footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.
> 6. **BUDGET.** Stop after 3 experiments or 2 hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.
>
> Build a simple, clean GitHub Pages site with a submission guide and auditable official source links. Research and validate autonomously, flag irregularities, and avoid hallucinations. Work through three passes: implement and verify; review for bugs, missing requirements and edge cases; then recheck and improve. Open and merge a pull request on the permitted session branch. Explain remaining work and limitations.

**Core values:** *Maximize P(Win)* by weighing tradeoffs and protecting scarce slots; *Own the Outcome* by verifying, reporting failures, and fixing what can be fixed. Those values never authorize silently weakening the protocol or inventing evidence.

## What this repository provides

- [Dashboard](index.html): nine-site comparison, historical score evidence classes, literal novelty findings and a fail-closed status.
- [Executive submission guide](executive-summary.html): steps, range-error troubleshooting, and official links.
- [Research page](research.html) and [four ranked prospective hypotheses](research/HYPOTHESES.md), written before this implementation; none is an assigned lane or validated result.
- [Detailed research review](research/REVIEW.md) and [exact-byte historical audit](evidence/focus_audit.json).
- [A mathematical registry preflight](scripts/registry_preflight.py) and [saved-byte GeoTIFF auditor](scripts/geotiff_audit.py). These are audit tools, **not** a replacement model, holdout evaluator, submission writer or slot selector.
- [Synthetic probes](evidence/upstream_probe.json) of shared-template issues [#37](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37), [#41](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/41) and [#42](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/42). They remain unresolved upstream; this account has read-only access there. No private fork was kept.

## Reproduce the read-only audit

Python 3.11+, GitHub CLI (`gh`) and internet access to GitHub and PyPI are required. JavaScript tests also require Node.js 22+, npm and the npm registry; the bundled headless-browser smoke test targets Linux x86-64 with `tar`. Owner mirrors are not authenticated organizer files. Raster downloads and the virtual environment are ignored by Git.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/restore_audit_inputs.py --group all  # hash-pinned owner mirrors only
python scripts/registry_preflight.py --dots 37654  # exit 2 = proven stop; 0 = not proven, NOT a pass
python scripts/audit_focus.py                      # 72 directed historical comparisons
python scripts/refresh_sources.py                  # public GitHub refs only, not scores
pytest -q
npm ci --ignore-scripts
npm run test:js
npm run test:browser  # headless Chromium, with mocked GitHub responses
python -m http.server 8000 --bind 0.0.0.0          # local preview
```

The preflight's nonzero stop is intentional. Do not chain it with later commands using `&&` when reproducing the full audit. The three software probes can be reproduced without modifying the shared template:

```bash
git clone https://github.com/buffedlizard55-lab/GEMSDOE32.git /tmp/gems32-audit
# In the separate read-only source clone, pin the recorded commit (not a new branch).
git -C /tmp/gems32-audit checkout --detach 1398109a23f04a2ace71c1bd2f527cfba87860b5
python scripts/probe_upstream.py --template-dir /tmp/gems32-audit
```

To examine an exact TIFF (this does **not** approve submission):

```bash
python scripts/geotiff_audit.py candidate.tif --template /path/to/authenticated_sample_submission.tif
```

The validator separately reports finite/in-range footprint values, raw whole-array range and outside null/mask. It never clips or changes a raster, including if the JSON output path aliases an input. The CLI returns 0 only if both local profiles pass, 2 if either fails, and 1 on an error; even exit 0 is not approval. A raw-array failure is not proof of organizer rejection. Official outside-null wording and the previously reported range rejection leave the actual portal handling of an internal mask uncertain; only an organizer receipt establishes acceptance.

## Status and next work

The highest of the nine supplied claims is GEMSDOE32 B2 **0.2778 USER-REPORTED / UNVERIFIED**, not an authenticated team score. The official public leaderboard showed **0.4544** on 2026-10-27 UTC, not a team receipt and potentially stale. A local HOLDOUT-DTI is not a calibrated leaderboard score; no forecast or victory claim is justified.

Coordinate an explicit lane; resolve the literal lattice/budget conflict without silently changing the rule; fix the shared tools upstream; restore the prepared cache and complete current registry; obtain authenticated competition inputs; then run leakage canaries, matched buffered whole-segment holdout, both novelty stages, saved-byte validation and a separate quota-aware selector. See [the detailed review](research/REVIEW.md) for the independent evidence and exact limitations.
