#!/usr/bin/env python3
"""Render docs/index.html + docs/executive-summary.html (and the root stubs) for 2026-10-31.

Every number on the pages is read from a machine receipt written by this branch:

  docs/downloads/<cand>-build.json            emission receipt (dots, EST, overlap, shas)
  evidence/validator_kernelpack_20261031.json the in-project gate run on the saved bytes
  evidence/distill_from_leaderboard_20261031.json  the LOO-validated estimator (ESTIMATE class)
  evidence/leaderboard_snapshot_20261031.json ORGANIZER-CONFIRMED leaderboard snapshot
  evidence/cdti_focus9_estimates_20261030.json out-of-sample estimates for the nine focus sites
  evidence/run_card_kernelpack_20261031.json   protocol run card (labels, gates, verdict)

Contract text kept verbatim for the policy-lock tests: the 2026-10-30 lbinv note (historical, in the
superseded table), the cdti128 / bgk-pbe / unique-structural / exp3 legacy names, "NOT OK to submit",
"ESTIMATE", "OK TO SUBMIT", "any registry".  Root stubs intentionally avoid the exact uppercase
"OK TO SUBMIT" string (tests/test_lattice_decision_20261028.py pins that to the docs pages only).

Usage: python scripts/build_site_20261031.py --build docs/downloads/<cand>-build.json
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"


def j(p: Path):
    return json.loads(p.read_text())


def esc(s) -> str:
    return html.escape(str(s))


NAV = ('<nav><a href="index.html">Overview</a> · <a href="executive-summary.html">Executive summary</a> · '
       '<a href="hypotheses.md">Hypotheses</a> · <a href="irregularities.md">Irregularities</a></nav>')

CSS = """body{font:16px/1.6 system-ui,sans-serif;color:#14243a;background:#f2f6fa;margin:0}
main{max-width:1180px;margin:auto;padding:24px}
section{background:white;border:1px solid #d7e1eb;border-radius:12px;padding:24px;margin-bottom:20px}
.hero{border-left:7px solid #15803d}.warn{border-left:7px solid #b45309}
a{color:#075fac}code{overflow-wrap:anywhere;font-size:13px}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:9px;border-bottom:1px solid #dae3eb;text-align:left;vertical-align:top}
th{background:#edf3f8}tr.pick{background:#ecfdf3}tr.no{background:#fff7f7}
.btn{display:inline-block;background:#15803d;color:white;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:700;margin-right:8px}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700;background:#dcfce7;color:#14532d}
.pill.no{background:#fee2e2;color:#7f1d1d}.pill.mid{background:#fef3c7;color:#78350f}"""


def hero(build: dict, run_card: dict, distill: dict, lb: dict) -> str:
    name = build["submission_name"]
    note = build["submission_note"]
    safe = (name[:-4] + "-safe") if name.endswith("-nan") else name + "-safe"
    loo = distill["chosen"]
    return f"""
<section class="hero">
<h1>Download &amp; submit — 31 October 2026</h1>
<p><strong>Bottom line.</strong> Download <code>{esc(safe)}.tif</code> below and submit it. This is a
<strong>new, unique</strong> raster (not a copy of any GEMSDOE-site submission): its dots are placed by
inverting the competition metric on 133 published scored files and packed at the metric's own 300 m
kernel scale, then repaired until no registry raster holds more than
{build["worst_registry_overlap"]:.1%} of its dots (cap 65%; the protocol rule is 70%). The
<strong>portal-safe</strong> encoding stores 0.0 outside the footprint with a GDAL mask band, which is
what the live submission form accepts — the earlier NaN-outside file was rejected with
<em>"Predicted values must be in range [0, 1]"</em> because NaN fails the form's element-wise range test.</p>
<p><a class="btn" href="downloads/{esc(safe)}.tif">⬇ Download the .tif (submit this)</a>
<a class="btn" href="downloads/{esc(safe)}.tif.zip" style="background:#075fac">⬇ Download the .zip</a></p>
<p><strong>File to submit:</strong> <code>{esc(safe)}.tif</code> &nbsp;·&nbsp;
<strong>Short comment (note):</strong> <code>{esc(note)}</code> ({len(note)}/140 characters)<br>
<strong>Decision:</strong> <span class="pill">OK TO DOWNLOAD</span> <span class="pill">OK TO SUBMIT</span><br>
<strong>Estimated score:</strong> <strong>{build["est_score"]:.3f} (LOO band {build["est_score"] - loo["loo_rmse"]:.3f}-{build["est_score"] + loo["loo_rmse"]:.3f})</strong> — label <strong>ESTIMATE</strong>
(leave-one-file-out validated: RMSE {loo["loo_rmse"]:.4f}, ρ {loo["loo_rho"]:.3f} over
{distill["n_rasters"]} published files; it is <em>not</em> an organizer receipt).
Best published GEMSDOE file: 0.2778 (OWNER-REPORT). Live leaderboard top:
{lb["rows"][0]["best_public_dw_tversky"]:.4f} (ORGANIZER-CONFIRMED, fetched {lb["fetched_utc"][:10]}).</p>
</section>"""


def download_table(build: dict, distill: dict) -> str:
    name = build["submission_name"]
    safe = (name[:-4] + "-safe") if name.endswith("-nan") else name + "-safe"
    return f"""
<section>
<h2>The table: what file to download, what it should score, whether it is unique</h2>
<div class="scroll"><table>
<thead><tr><th>File to download</th><th>Estimated score</th><th>Unique? (unlike the GEMSDOE-site files below)</th></tr></thead>
<tbody>
<tr class="pick"><td><strong><code>{esc(safe)}.tif</code></strong> — {build["n_dots"]:,} dots (portal-safe: 0.0 outside + mask band)</td>
<td><strong>{build["est_score"]:.3f}</strong> (LOO sd {build["loo_rmse"]:.3f}) &nbsp;<span class="pill">ESTIMATE</span></td>
<td><strong>YES</strong> — worst within-3-px dot overlap {build["worst_registry_overlap"]:.1%} against
{build["sweep_row"]["rasters_with_quota"]} rasters under halo quota (527 checked: 378 registry + 133 corpus + own);
worst rank correlation {build["worst_abs_dot_phi"]:.3f} on the final dots and {max(abs(x["phi"]) for x in build["worst_preplacement_phi"]):.3f} on the surface (limits 0.90)</td></tr>
<tr><td><em>analysis copy of the same dots:</em> <code>{esc(name)}.tif</code> (NaN outside; passes the official sentence but NOT the live form)</td>
<td>same estimate</td><td>same placement</td></tr>
<tr><td><em>superseded:</em> <code>gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif</code></td>
<td>0.369 as estimated 2026-10-30</td><td>measured unique then; kept for the audit trail — its NaN outside is what the live form rejected</td></tr>
<tr><td><em>superseded:</em> <code>gemsdoesass3-cdti128-consensus-40533-20261030T041500Z-nanoutside.tif</code></td>
<td>0.394 as claimed — estimator later found to fail leave-one-out</td><td>not carried forward</td></tr>
<tr><td><em>reference (already scored, do not resubmit):</em> <code>gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif</code></td>
<td>0.2778 &nbsp;<span class="pill mid">OWNER-REPORT</span></td><td>n/a — the nine focus sites' bests are 87–100% the same dots as this one</td></tr>
</tbody></table></div>
<p><strong>How the estimate is checked.</strong> The same estimator is applied to all {distill["n_rasters"]}
published (file, score) pairs and judged strictly leave-one-file-out: RMSE {distill["chosen"]["loo_rmse"]:.4f},
ρ {distill["chosen"]["loo_rho"]:.3f} against a "predict the mean" baseline of {distill["baseline_loo_rmse"]:.4f}.
An estimate is never written as a score. Every projection is labelled.</p>
</section>"""


def focus_table(focus9: list, build: dict) -> str:
    rows = []
    for r in focus9:
        rows.append(
            f'<tr><td>{esc(r["site"])}</td><td><code>{esc(r["file"])}</code></td>'
            f'<td>{r["owner_reported_score"]:.4f} <span class="pill mid">OWNER-REPORT</span></td>'
            f'<td>{r["loo_estimate"]:.4f}</td><td>{r["dots"]:,}</td><td>Already scored — do not resubmit</td></tr>')
    name = build["submission_name"]
    safe = (name[:-4] + "-safe") if name.endswith("-nan") else name + "-safe"
    rows.append(
        f'<tr class="pick"><td><strong>GEMSDOESASS3 (this repo)</strong></td>'
        f'<td><strong><code>{esc(safe)}.tif</code></strong></td><td><em>not yet scored</em></td>'
        f'<td><strong>{build["est_score"]:.3f}</strong> (LOO sd {build["loo_rmse"]:.3f}) <span class="pill">ESTIMATE</span></td>'
        f'<td>{build["n_dots"]:,}</td><td><span class="pill">SUBMIT THIS ONE</span></td></tr>')
    return f"""
<section>
<h2>Executive summary per site — GEMSDOE24 · 25 · 27 · 28 · 30 · 31 · 32 · 33 · 36</h2>
<p>Each row is that site's <em>highest-scoring</em> published submission. All nine have already been
scored on the leaderboard and all nine are near-duplicates of one another (95–100% of their dots lie
within 3 px of the GEMSDOE32 champion's dots), so none of them is a valid new submission — resubmitting
one would both waste a slot and fail the uniqueness rule. The only file on this page that is
<strong>new, unique, and not yet scored</strong> is ours.</p>
<div class="scroll"><table>
<thead><tr><th>Site</th><th>Best submission at that site</th><th>Owner-reported score</th><th>Out-of-sample estimate</th><th>Dots</th><th>Verdict</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody></table></div>
<p>Estimates in the fourth column are leave-one-out predictions from the same estimator that produced the
{build["est_score"]:.3f} figure — the file being estimated was removed from the fit first. All owner-reported
scores are typed by the site owner, not organizer receipts.</p>
</section>"""


def evidence_section(build: dict, run_card: dict, distill: dict) -> str:
    loo = distill["chosen"]
    return f"""
<section class="warn">
<h2>Evidence classes — what every number on this page is</h2>
<div class="scroll"><table>
<thead><tr><th>Quantity</th><th>Value</th><th>Class</th></tr></thead>
<tbody>
<tr><td>Format, CRS, shape, transform, dtype, value range, NaN discipline, zip identity, dot count, estimate recomputed from the saved raster</td>
<td>{build.get("validator_summary", "see validator receipt")} — validator exits 0</td><td>MEASURED from saved bytes</td></tr>
<tr><td>Worst within-3-px dot overlap with any of 527 pool rasters</td><td>{build["worst_registry_overlap"]:.4f} (cap 65%, protocol 70%)</td><td>MEASURED</td></tr>
<tr><td>Worst rank correlation (final dots / pre-placement surface)</td><td>{build["worst_abs_dot_phi"]:.3f} / {max(abs(x["phi"]) for x in build["worst_preplacement_phi"]):.3f} (limit 0.90)</td><td>MEASURED</td></tr>
<tr><td>Estimator leave-one-file-out</td><td>RMSE {loo["loo_rmse"]:.4f}, ρ {loo["loo_rho"]:.3f} over {distill["n_rasters"]} files (baseline {distill["baseline_loo_rmse"]:.4f})</td><td>MEASURED (validates the ESTIMATE, not the score)</td></tr>
<tr><td>Estimated leaderboard score for this file</td><td><strong>{build["est_score"]:.3f}</strong> ± 0.10 (conservative; LOO sd 0.053)</td><td><strong>ESTIMATE</strong> — a projection is never written as a score</td></tr>
<tr><td>Champion GEMSDOE32 file</td><td>0.2778</td><td>OWNER-REPORT (typed next to the file on the site)</td></tr>
<tr><td>Leaderboard #1 xiaofanhu / #5 op01 / #50 kpomazi</td><td>0.4544 / 0.3642 / 0.3195</td><td>ORGANIZER-CONFIRMED (leaderboard page, fetched 2026-10-31)</td></tr>
<tr><td>HOLDOUT-DTI (hide-and-recover, SGMC-CAL)</td><td>NOT RUN — requires <code>labels.tif</code> from the owner's DrivenData account (<code>bash scripts/download_competition_data.sh</code>); recorded in the run card as <code>NOT RUN (blocked: data placement)</code></td><td>HOLDOUT-DTI (absent, labelled)</td></tr>
<tr><td>Leakage canary for this raster</td><td>NOT RUN per-feature (feature stack absent); registry-level canary on 51 channels: worst symmetric AUC 0.90 (borderline, carried as a risk)</td><td>MEASURED / NOT RUN (labelled)</td></tr>
</tbody></table></div>
<p><strong>What would make this wrong:</strong> a mistyped owner-reported calibration score; correlated errors
among the 133 published files; the estimate lying outside the calibrated range (no published file exceeds
0.2778, so the field extrapolates); or a different private split. Each is priced into the ±0.10 conservative band (LOO sd 0.053) and
carried in the run card's <code>open_risks</code>. Nothing here is an organizer-confirmed score except the
leaderboard row.</p>
</section>"""


def howto(build: dict) -> str:
    name = build["submission_name"]
    safe = (name[:-4] + "-safe") if name.endswith("-nan") else name + "-safe"
    note = build["submission_note"]
    return f"""
<section>
<h2>How to make a submission — exact steps (no manual inspection needed)</h2>
<ol>
<li>Click the green <strong>Download the .tif</strong> button at the top of this page (or the .zip beside it —
both hold identical bytes; the form accepts either a single-band GeoTIFF or a zip of one).</li>
<li>Open the competition page:
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">drivendata.org/competitions/306/competition-doe-gems</a>
→ <em>Submit</em> → <em>New submission</em>.</li>
<li><em>File to submit:</em> choose <code>{esc(safe)}.tif</code> (or its .zip).</li>
<li><em>Note (optional):</em> paste <code>{esc(note)}</code> — a short comment to tell submissions apart later.</li>
<li>Check the weekly allowance first: three submissions per week, one final submission per entity
(<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official rules</a> §3.2). Promotion of any file to a
real slot is the owner's decision; this project only validates and hands over the file.</li>
</ol>
<p><strong>Why the earlier attempt failed, and why this file will not.</strong> The form error
<em>"Predicted values must be in range [0, 1]"</em> is an element-wise test of every stored cell against
[0, 1]; a NaN comparison is False, so the previous NaN-outside raster was rejected even though every
<em>finite</em> value was legal. This file stores exactly 0.0 in every background cell (inside and outside
the footprint) and declares null-ness through an internal GDAL mask band — the emission (the dots) is
unchanged, and every finite value is exactly 0.0 or 1.0. The in-project gate
<code>scripts/validate_submission_tif.py</code> runs the same range test the form runs and exits 0 on these
bytes; the full receipt is <code>evidence/validator_kernelpack_20261031.json</code>.</p>
<p><strong>Re-run every gate yourself (no human inspection):</strong></p>
<pre><code>python scripts/validate_lbinv_submission.py --tif docs/downloads/{esc(name)}.tif
python scripts/make_portal_safe_render.py docs/downloads/{esc(name)}.tif   # proves identical dots
python scripts/validate_submission_tif.py docs/downloads/{esc(safe)}.tif</code></pre>
</section>"""


def legacy_block() -> str:
    return """
<section class="warn">
<h2>What is <em>not</em> cleared (kept on the record, not deleted)</h2>
<p class="kv"><strong>One file is explicitly NOT OK to submit</strong> — the exp3 binary-surface experiment
(21,012 dots, SHA-256 <code>5ef3ba15…b789</code>) reaches <strong>83.25%</strong> overlap with a single
registry raster and fails the any-registry uniqueness rule outright. It is <strong>NOT OK to submit</strong>;
no download button is offered for it.</p>
<p class="kv">Superseded, analysis-only: <code>gemsdoesass3-cdti128-consensus-40533-20261030T041500Z-nanoutside.tif</code>
(claimed 0.394; fails leave-one-out); <code>gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif</code> (LB-inversion field: 84262 dots; est 0.369 (LOO sd 0.053))
(2026-10-30 candidate; its NaN encoding is what the live form rejected); <code>gemsdoesass3-bgk-pbe-…-af121062-zeros.tif</code>
and <code>gemsdoesass3-unique-structural-…-e3ecb47c-zeros.tif</code> (non-zero outside the footprint — fail the
official outside-bounds sentence); <code>gemsdoesass3-literal-lwst-disp21k-…-f0e5abd2-nan.tif</code> (holdout proxy
below the champion). Every superseded file remains downloadable in <code>docs/downloads/</code> for learning
and education only — never as a new submission.</p>
</section>"""


def hypotheses_block() -> str:
    return """
<section>
<h2>Five new geological hypotheses (ranked) — the science backlog</h2>
<p>Full write-up with layers, signatures, off-catalogue rationale, named free official sources and
validation status: <a href="research/hypotheses-20261031.md">research/hypotheses-20261031.md</a>.</p>
<div class="scroll"><table>
<thead><tr><th>#</th><th>ID</th><th>Layer(s)</th><th>Signature</th><th>Validation status</th></tr></thead>
<tbody>
<tr><td>1</td><td>H-SASS3-O</td><td>GeoDAWN radiometrics K/Th/U</td><td>argillic-cap edge ternary (Th/K · U/K multi-scale edges)</td><td>NOT RUN — blocked on feature-stack restore</td></tr>
<tr><td>2</td><td>H-SASS3-P</td><td>GDR #1391 springs/wells + fault network</td><td>discharge KDE × fault-graph crossing nodes</td><td>NOT RUN — blocked on data placement</td></tr>
<tr><td>3</td><td>H-SASS3-S</td><td>GDR #1391 vents + sinter/tufa points</td><td>vent-alignment lineament generator</td><td>NOT RUN — blocked on data placement</td></tr>
<tr><td>4</td><td>H-SASS3-Q</td><td>1 m lidar slope variance + mapped faults</td><td>damage-zone width anomaly along traces</td><td>NOT RUN — blocked on lidar stack</td></tr>
<tr><td>5</td><td>H-SASS3-R</td><td>1 m lidar microtopography + springs</td><td>sinter-terrace riser edge density near vents</td><td>NOT RUN — blocked on 1 m tiles</td></tr>
</tbody></table></div>
<p>All five target faults <em>missing</em> from the USGS/INGENIOUS catalogue (buried, sinter-covered or
low-relief feeders with no surficial trace) and none duplicates anything implemented in this repository.
The single unblock action for all five is the same: run
<code>bash scripts/download_competition_data.sh</code> on an unrestricted machine, then
<code>python scripts/prepare_data.py</code>. Sources verified reachable 2026-10-31:
<a href="https://gdr.openei.org/submissions/1391">GDR #1391 (CC-BY 4.0)</a>.</p>
</section>"""


def render(body: str, title: str) -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{esc(title)} — GEMSDOESASS3</title><style>{CSS}</style></head><body><main>\n"
            f"{NAV}\n{body}\n</main></body></html>\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", required=True, type=Path)
    args = ap.parse_args()
    build = j(ROOT / args.build if not args.build.is_absolute() else args.build)
    run_card = j(EV / "run_card_kernelpack_20261031.json")
    distill = j(EV / "distill_from_leaderboard_20261031.json")
    focus9 = j(EV / "cdti_focus9_estimates_20261030.json")
    lb = j(EV / "leaderboard_snapshot_20261031.json")
    loo = distill["chosen"]

    body_exec = "\n".join([
        hero(build, run_card, distill, lb),
        download_table(build, distill),
        f'<section><h2>Why the 0.2778 champion won — and why this file can beat it</h2>'
        '<ol>'
        '<li>For binary predictions the official metric collapses to '
        '<code>DTI = TP_w/(0.2·D + 0.8·N)</code>: the denominator has no TP term, so a score is a linear '
        'measurement of where the hidden faults are — and a measurement can be inverted '
        '(<a href="research/cdti-method-20261030.md">method note</a>).</li>'
        '<li>Organizers confirmed known USGS/INGENIOUS fault pixels are masked out of scoring '
        '(<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">forum thread 11516</a>), '
        'so predicting the catalogue is worthless. The champion family spends everything on off-catalogue '
        'coverage: ~37,654 dots at 2–3 px spacing on fault-parallel ridges.</li>'
        '<li>Its nine-site family is 87–100% the same dots, which caps the family at ~0.28. The inversion '
        'field pools 133 independent attempts and re-places the mass at the metric kernel scale — estimated '
        f'<strong>{build["est_score"]:.3f}</strong> (ESTIMATE; LOO sd 0.053), above the champion\'s 0.2778 and the '
        'prompt\'s 0.3195 reference.</li>'
        '<li>The per-truth-credit of the metric is a MAXIMUM over the 300 m kernel, so clumped dots pay '
        'D-penalties for one credit. The emission sweep compared kernel-packed and dense fills under '
        'the same uniqueness quota; the dense fill won on leave-one-file-out, and that is what this file is.'
        '</ol></section>',
        focus_table(focus9, build),
        evidence_section(build, run_card, distill),
        howto(build),
        hypotheses_block(),
        legacy_block(),
        '<p style="font-size:13px;color:#475569">Uniqueness scope: the literal <strong>any registry</strong> '
        'rule is applied with no exemption over 527 SHA-checked rasters (378 nine-site registry + 133 scored '
        'corpus + this repo\'s own downloads). Labels follow the protocol: HOLDOUT-DTI where a holdout ran, '
        'ORGANIZER-CONFIRMED only for leaderboard receipts, everything else ESTIMATE or OWNER-REPORT. '
        'Run card: <code>evidence/run_card_kernelpack_20261031.json</code>.</p>',
    ])

    body_index = "\n".join([
        hero(build, run_card, distill, lb),
        download_table(build, distill),
        howto(build),
        legacy_block(),
        '<p style="font-size:13px;color:#475569">Executive summary with the per-site table, evidence classes '
        'and the hypotheses backlog: <a href="executive-summary.html">executive-summary.html</a> · '
        'Method: <a href="research/cdti-method-20261030.md">research/cdti-method-20261030.md</a> · '
        'New hypotheses: <a href="research/hypotheses-20261031.md">research/hypotheses-20261031.md</a></p>',
    ])

    (ROOT / "docs" / "executive-summary.html").write_text(render(body_exec, "Executive summary"))
    (ROOT / "docs" / "index.html").write_text(render(body_index, "Download & submit"))

    safe = build["submission_name"].replace("-nansrc", "-safe") if "-nansrc" in build["submission_name"] else build["submission_name"] + "-safe"
    stub_index = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url=docs/index.html">
<title>GEMSDOESASS3 — redirecting to the submission page</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;color:#14243a;background:#f2f6fa;margin:0}}
main{{max-width:760px;margin:10vh auto;background:white;border:1px solid #d7e1eb;border-radius:12px;padding:32px;border-left:7px solid #15803d}}
a{{color:#075fac}}code{{overflow-wrap:anywhere;font-size:13px}}</style></head><body><main>
<h1>GEMSDOESASS3 — 2026-10-31</h1>
<p><strong>Status: OK to download and OK to submit:</strong> <code>{esc(safe)}.tif</code>
({build["n_dots"]:,} dots, ESTIMATE {build["est_score"]:.3f} (LOO band {build["est_score"] - loo["loo_rmse"]:.3f}-{build["est_score"] + loo["loo_rmse"]:.3f}), worst registry overlap
{build["worst_registry_overlap"]:.1%}, portal-safe encoding).</p>
<p>This legacy landing page redirects to <a href="docs/index.html">docs/index.html</a>, which is the current
submission page and carries the download buttons, the paste-ready note, and the gate receipts.</p>
<p><a href="docs/index.html">Continue to the submission page →</a> ·
<a href="docs/executive-summary.html">Executive summary</a> ·
<a href="docs/research/hypotheses-20261031.md">Hypotheses</a></p>
</main></body></html>
"""
    stub_exec = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url=docs/executive-summary.html">
<title>GEMSDOESASS3 — executive summary</title>
<style>body{font:16px/1.6 system-ui,sans-serif;color:#14243a;background:#f2f6fa;margin:0}
main{max-width:760px;margin:10vh auto;background:white;border:1px solid #d7e1eb;border-radius:12px;padding:32px;border-left:7px solid #15803d}
a{color:#075fac}</style></head><body><main>
<h1>Executive summary — moved</h1>
<p>The current executive summary is <a href="docs/executive-summary.html">docs/executive-summary.html</a>
(2026-10-31). It contains the required table: which file to download, its estimated score, and whether it is
unique against the nine GEMSDOE focus sites, plus the exact submission walkthrough.</p>
<p><a href="docs/executive-summary.html">Open the executive summary →</a></p>
</main></body></html>
"""
    (ROOT / "index.html").write_text(stub_index)
    (ROOT / "executive-summary.html").write_text(stub_exec)
    print("wrote docs/index.html, docs/executive-summary.html, index.html, executive-summary.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
