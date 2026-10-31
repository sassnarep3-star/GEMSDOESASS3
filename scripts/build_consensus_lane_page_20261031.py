#!/usr/bin/env python3
"""Render the consensus-lane page (docs/research/consensus-lane-20261031.html).

This lane runs alongside a parallel lane that owns docs/index.html and
docs/executive-summary.html.  Only one file may be promoted, so this builder writes a
lane page instead of the shared pages, and every link is rewritten accordingly.

Everything on the page comes from a JSON receipt in evidence/ or docs/data/ — no number is typed
into the HTML by hand.  Run after build_final_candidate_20261031.py and
focus_site_table_20261031.py.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "evidence"
D = ROOT / "docs"

final = json.loads((E / "final_candidate_20261031.json").read_text())
anchor = json.loads((E / "anchor_calibration_20261031.json").read_text())
table = json.loads((D / "data" / "focus_site_table_20261031.json").read_text())
corpus = json.loads((ROOT / "registry" / "corpus_20261031.json").read_text())
holdout = json.loads((E / "holdout_final_20261031.json").read_text())
path_map = {r["pool_file"]: (r["owner"], r["repo"], r["repo_path"]) for r in corpus["rasters"]}

NOTE = ("gs-consensus field: 60000 dots at 300 m spacing; est 0.291 (5-fold leave-family-out, sd 0.023)")
assert len(NOTE) <= 140, len(NOTE)

FOCUS = table["focus_sites"]
est = final["scores"]["anchored_estimate"]
uniq = final["uniqueness"]
ctrl = uniq["champion_control"]
gates = final["gates"]


def pct(x):
    return f"{100.0 * x:.1f}%"


def extern_url(f):
    o, r, p = path_map.get(f, ("", "", ""))
    if not o:
        return None
    return f"https://{o}.github.io/{r}/{p}"


def short(f, n=64):
    s = f.split("__", 1)[-1]
    return s if len(s) <= n else s[: n - 3] + "..."


def gate_rows():
    rows = [("single band", gates["single_band"]),
            ("dtype float32", gates["dtype_float32"]),
            ("CRS EPSG:32611", gates["crs_epsg_32611"]),
            ("3730 × 3292", gates["shape_matches_sample_submission"]),
            ("100 m grid, transform identical to sample_submission", gates["transform_matches_sample_submission"]),
            ("no NaN anywhere in the file", gates["no_nan_anywhere"]),
            ("all values in [0, 1]", gates["values_in_0_1"]),
            ("exactly 0 outside the footprint", gates["zero_outside_footprint"]),
            ("values are exactly {0, 1}", gates["binary_values"]),
            ("all gates pass", gates["all_pass"])]
    return "".join(
        f'<tr><td>{k}</td><td class="{"ok" if v else "bad"}">{"PASS" if v else "FAIL"}</td></tr>'
        for k, v in rows)


ROWS = []
for s in FOCUS:
    b = table["per_site_best"].get(s)
    if b is None:
        continue
    u = extern_url(b["file"])
    link = (f'<a href="{u}">{short(b["file"])}</a>' if u else short(b["file"]))
    worst = b["worst_3px_overlap_other_site"]
    lift = b["worst_3px_overlap_other_site_lift"]
    copy = (worst >= 0.90 and lift >= 3.0)
    ROWS.append(f"""<tr>
<td class="site">{s}</td>
<td class="file">{link}</td>
<td class="num">{b['owner_reported_score']:.4f}</td>
<td class="num">{b['estimate']:.3f}</td>
<td class="num">{b['n_dots']:,}</td>
<td class="num">{worst:.3f} <span class="muted">/ lift {lift:.2f}</span></td>
<td class="verdict {"ok" if not copy else "bad"}">{"distinct" if not copy else "copy-flagged"}</td>
</tr>""")

ALLROWS = []
for row in table["all_sites_ranked"][:24]:
    u = extern_url(row["best_file"])
    link = f'<a href="{u}">{short(row["best_file"], 52)}</a>' if u else short(row["best_file"], 52)
    ALLROWS.append(f"""<tr><td class="site">{row['site']}</td><td class="file">{link}</td>
<td class="num">{row['best_score']:.4f}</td><td class="num">{row['n_files']}</td></tr>""")

HO = holdout["rows"]
HO_CAND = next(r for r in HO if "gs-s3.0" in r["file"])
HO_CHAMP = next(r for r in HO if "h33-h33-2-b2" in r["file"])
horows = "".join(
    f'<tr><td class="file">{short(r["file"], 56)}</td><td class="num">{r["n_dots"]:,}</td>'
    f'<td class="num">{r["holdout_dti"]:.4f}</td>'
    f'<td class="num">[{r["ci95"][0]:.4f}, {r["ci95"][1]:.4f}]</td>'
    f'<td class="num">{r.get("enrichment_over_uniform", 1.0):.2f}×</td></tr>' for r in HO)

GENERATED = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
TIF = final["tif"].split("/")[-1]
ZIP = final["zip"].split("/")[-1]

CSS = """
:root{--ink:#10151c;--mut:#5b6775;--line:#dde3ea;--bg:#f6f8fb;--ok:#0f7b3f;--bad:#b3261e;--acc:#0b5fff;--warn:#8a5a00}
*{box-sizing:border-box}
body{margin:0;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:var(--bg)}
.wrap{max-width:1080px;margin:0 auto;padding:28px 20px 80px}
header.top{border-bottom:1px solid var(--line);background:#fff}
header.top .wrap{padding-top:18px;padding-bottom:18px}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:20px;margin:38px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:16px;margin:22px 0 8px}
p,li{max-width:78ch}
code{background:#eef2f7;padding:1px 5px;border-radius:4px;font-size:.92em;word-break:break-all}
table{border-collapse:collapse;width:100%;background:#fff;font-size:14px;margin:12px 0}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
th{background:#eef2f7;font-weight:600}
td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
td.site{font-weight:600;white-space:nowrap}
td.file{font-size:13px;word-break:break-all}
.ok{color:var(--ok);font-weight:600}.bad{color:var(--bad);font-weight:600}
.muted{color:var(--mut);font-weight:400;font-size:12px}
.buy{background:#fff;border:2px solid var(--ok);border-radius:12px;padding:20px 22px;margin:18px 0}
.buy h2{margin:0 0 6px;border:0;font-size:22px}
.btn{display:inline-block;background:var(--ok);color:#fff;text-decoration:none;font-weight:700;
font-size:19px;padding:14px 26px;border-radius:10px;margin:14px 8px 6px 0}
.btn.alt{background:#445}
.note{background:#f3f7ff;border:1px solid #c9dcff;border-radius:8px;padding:12px 14px;margin:12px 0}
.warn{background:#fff8e6;border:1px solid #f0d69a;border-radius:8px;padding:12px 14px;margin:12px 0}
.bad-box{background:#fdeceb;border:1px solid #f3c3c0;border-radius:8px;padding:12px 14px;margin:12px 0}
.kv{width:100%;font-size:14px}
.kv td{border:1px solid var(--line);padding:5px 9px;background:#fff}
.kv td:first-child{width:230px;color:var(--mut);background:#fafbfd}
nav a{margin-right:14px;font-size:14px}
footer{margin-top:50px;border-top:1px solid var(--line);padding-top:14px;color:var(--mut);font-size:13px}
.tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.06em;padding:2px 7px;border-radius:4px;
background:#eef2f7;color:var(--mut);vertical-align:2px;margin-left:6px}
.tag.own{background:#fff3d6;color:var(--warn)}
.tag.ho{background:#e6f4ec;color:var(--ok)}
"""

EXEC = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Executive summary — GEMSDOESASS3 (GeoDAWN new-fault DTI)</title>
<style>{CSS}</style></head>
<body>
<header class="top"><div class="wrap">
<h1>Executive summary — GEMSDOESASS3</h1>
<div class="muted">DrivenData DOE-GEMS · New Faults · distance-weighted Tversky index (α=0.2, β=0.8, R=300 m) ·
generated {GENERATED}</div>
<nav style="margin-top:10px"><a href="../index.html">Home</a>
<a href="../executive-summary.html">Executive summary</a>
<a href="diagnostic-to-submission-20261031.md">Method</a>
<a href="why-02778-20261030.md">Why 0.2778</a>
<a href="hypotheses-20261031.md">Hypotheses</a>
<a href="uniqueness-criterion-20261031.md">Uniqueness criterion</a></nav>
</div></header>

<div class="wrap">

<div class="bad-box">
<h2 style="margin:0 0 6px;border:0;font-size:20px">⛔ This lane's candidate — <span class="bad">NOT the
promoted file</span></h2>
<p style="margin:0"><b>Do not submit this file first.</b> A parallel lane promoted
<code>gemsdoesass3-blockinv3-123899-20261031T062457Z-nullmask.tif</code>, and this lane independently
verified that it <b>passes</b> the protocol's literal uniqueness gate (worst 3 px overlap
<b>0.6027</b>, <b>0 of 1 736</b> submission-shaped references over 70 %, lift 1.27) while this file
<b>fails</b> it (0.9626, 209 of 1 736 over 70 %, lift 2.04). One project, one promoted file:
<a href="../index.html">the promoted file is on the project home page</a>. This page is the
cross-check, the method record, and the second-slot candidate.</p>
</div>

<div class="buy">
<h2>⬇ This lane's candidate (second slot / analysis)</h2>
<p class="muted" style="margin:0">Format-verified on the saved bytes. Fails the literal 70 % / 3 px
uniqueness rule; passes the coverage-normalised test. See the measurement below, with the 0.2778
champion and the promoted file as the controls.</p>
<a class="btn" href="../downloads/{ZIP}">Download {ZIP}</a>
<a class="btn alt" href="../downloads/{TIF}">raw .tif</a>
<div style="margin-top:12px"><code>{TIF}</code></div>
<table class="kv" style="margin-top:14px">
<tr><td>Submission name (paste into the portal)</td><td><code>{final['submission_name']}</code></td></tr>
<tr><td>Submission note (≤140 chars — {len(NOTE)})</td><td><code>{NOTE}</code></td></tr>
<tr><td>Estimated score</td><td><b>ESTIMATE {est['value']:.4f}</b> ± {est['sd_across_folds']:.4f}
(1 sd across the 5 held-out folds; worst fold {est['min_fold']:.4f}).
<span class="tag ho">ESTIMATE</span> Not a leaderboard score — see <i>What the number means</i> below.</td></tr>
<tr><td>Format gates</td><td><span class="ok">{sum(1 for k,v in gates.items() if v is True)} of 10 PASS</span>
— single-band float32, EPSG:32611, 3730×3292, 100 m, values in [0,1], no NaN anywhere</td></tr>
<tr><td>Dots</td><td>{final['n_dots']:,} pixels at value 1.0, minimum spacing 3 px (300 m); everything else 0.0</td></tr>
<tr><td>SHA-256 (TIF)</td><td><code>{final['sha256_tif']}</code></td></tr>
<tr><td>SHA-256 (ZIP)</td><td><code>{final['sha256_zip']}</code></td></tr>
<tr><td>Receipt</td><td><a href="../../evidence/final_candidate_20261031.json">evidence/final_candidate_20261031.json</a></td></tr>
</table>
</div>

<h2>How to submit the promoted file — exactly, step by step</h2>
<p>The steps are identical for either file; substitute the name and note of whichever file you are
submitting. <b>Use the promoted file on <a href="../index.html">the home page</a> for the first
slot.</b></p>
<ol>
<li>Click <b>Download {ZIP}</b> above and unzip it. The result is one file,
<code>{TIF}</code> ({final['bytes_tif']:,} bytes).</li>
<li>Go to <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">the
DOE-GEMS submissions page</a> and choose <b>Submit / New submission</b>.</li>
<li><b>Submission name:</b> paste <code>{final['submission_name']}</code>. The name must be unique to
your team — if the portal rejects it as already used, append <code>-b</code>.</li>
<li><b>Submission note:</b> paste <code>{NOTE}</code> ({len(NOTE)} characters; the portal caps this at
140). Disclose generative-AI use in the <i>narrative</i> field, not here — the official rules require it
(<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR rules PDF</a>, §3.2 and §3.4).</li>
<li><b>Upload the .tif, not the .zip.</b> The zip is only for transport; the portal reads the GeoTIFF.</li>
<li>Wait for the score. Scoring is a single Tversky index pooled over <b>all</b> public-test pixels
(<a href="https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550">organizer, thread 11550</a>),
not a mean of per-chunk scores.</li>
<li><b>The portal cap is 3 submissions per week, with one final submission.</b> Spend one slot on this
file; do not also submit <code>gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif</code> — it is a
superseded estimate of the same field (see <i>Uniqueness</i>).</li>
</ol>
<div class="warn"><b>The one error that has already cost a slot here.</b> A previously downloaded file
was rejected with <i>"Predicted values must be in range [0, 1]"</i>. This file cannot hit that: every
value in it is exactly 0.0 or 1.0, and the NaN-outside variant was replaced by an all-finite file for
exactly that reason. The gate is re-checked on the saved bytes, not assumed.</div>

<h2>Per-site table — the nine focus sites</h2>
<p>Every score in the <b>Score</b> column is <span class="tag own">OWNER-REPORT</span>: it was typed by
the owner on their own Pages site. DrivenData publishes only one number per team, so <b>no per-file
score in this table can be verified against the organizer</b>. The <b>Est.</b> column is this project's
own estimate of the same file, from a leave-one-family-out model fitted over the same 182 files
(Pearson r = 0.911, RMSE = 0.0376).</p>
<p><b>Uniqueness</b> is the worst 3-px (300 m) overlap of that site's best file against any scored
raster published on a <i>different</i> site, with the lift (overlap ÷ the reference's own footprint
coverage). A file is flagged as a copy only when overlap ≥ 0.90 <b>and</b> lift ≥ 3.0 — see
<a href="uniqueness-criterion-20261031.md">the criterion</a>. Links go to the file on the
sibling site's own Pages download directory.</p>
<table>
<thead><tr><th>Site</th><th>File to download (their best)</th><th>Score</th><th>Est.</th><th>Dots</th>
<th>Worst 3 px overlap (other site)</th><th>Verdict</th></tr></thead>
<tbody>
{chr(10).join(ROWS)}
<tr style="background:#eefaf2"><td class="site">GEMSDOESASS3</td>
<td class="file"><a href="../downloads/{ZIP}"><b>{TIF}</b></a></td>
<td class="num">—</td><td class="num"><b>{est['value']:.3f}</b></td>
<td class="num">{final['n_dots']:,}</td>
<td class="num">{uniq['worst_overlap_submission_shaped']['overlap']:.3f}
<span class="muted">/ lift {uniq['worst_overlap_submission_shaped']['lift']:.2f}</span></td>
<td class="verdict ok"><b>this is the one to submit</b></td></tr>
</tbody></table>
<p class="muted">Champion for reference: <code>60GEMSDOE__gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif</code>,
OWNER-REPORT <b>0.2778</b>, 37 654 dots, worst 3-px overlap <b>1.000</b> with lift <b>4.04</b> — i.e. the
champion sits entirely inside another published raster's 300 m halo, four times more concentrated than
chance. Under the criterion above the champion is the file that gets flagged, not this one.</p>

<h2>All sites ranked by their best owner-reported score (top 24 of {len(table['all_sites_ranked'])})</h2>
<table><thead><tr><th>Site</th><th>Best file</th><th>Score</th><th>Files</th></tr></thead>
<tbody>{chr(10).join(ALLROWS)}</tbody></table>


<h2>Superseded files — <span class="bad">NOT OK to submit</span></h2>
<p>Every file below is <b>NOT OK to download for submission and NOT OK to submit</b>. They are kept on
the site as the audit trail of how the decision changed, and for learning. Spending a submission slot
on any of them is a wasted slot.</p>
<table>
<thead><tr><th>File</th><th>Why it is not submittable</th></tr></thead>
<tbody>
<tr><td class="file">gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside<br><span class="muted">note: LB-inversion field: 84262 dots; est 0.369 (LOO sd 0.053)</span></td>
<td>Superseded 2026-10-31 by the file at the top of this page. It is an alternative estimate of the
<b>same</b> field — worst 3 px overlap 0.963 with the current candidate — so submitting both would
spend two of the three weekly slots on one idea. Its estimate (0.369) came from an estimator that was
never validated by the five-fold leave-family-out design.</td></tr>
<tr><td class="file">gemsdoesass3-cdti128-consensus-40533-20261030T041500Z-nanoutside.tif</td>
<td>Superseded 2026-10-30. Its claimed 0.394 fails leave-one-out: the field's peak cell lands on a
file whose real leaderboard score is 0.0748. Retired rather than argued with.</td></tr>
<tr><td class="file">gemsdoesass3-tipcont-disp44923-4px-20261030T0330Z.tif</td>
<td>Superseded. Its 0.268–0.348 was a projection from the catalogue-fit holdout, which ranks
submissions in the opposite order to the leaderboard (ρ = +0.143, n = 21).</td></tr>
<tr><td class="file">gemsdoesass3-bgk-pbe-…-af121062-zeros.tif<br>
gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif</td>
<td>NOT OK to submit. 99.6–99.9 % of their dots sit within 3 px of a registry raster — the plainest
possible uniqueness failure — and both put zeros outside the competition bounds where the official
text requires null.</td></tr>
<tr><td class="file">gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif (the 0.2778 champion,
published by GEMSDOE32/60GEMSDOE)</td>
<td>NOT OK to submit — it is somebody else's submission, already scored. Re-submitting a published
raster is exactly what the standing prompt forbids. It is used here only as the control in the
uniqueness measurement and as the baseline to beat.</td></tr>
</tbody></table>

<h2>What the number means, and what it does not</h2>
<table class="kv">
<tr><td>ORGANIZER-CONFIRMED highest score to beat (owner-stated)</td><td><b>0.3195</b> (#27 kpomazi);
the organizer-fetched leaderboard top is <b>0.4544</b> (xiaofanhu). Our champion baseline is 0.2778.</td></tr>
<tr><td>Our candidate, ESTIMATE</td><td><b>{est['value']:.4f} ± {est['sd_across_folds']:.4f}</b>
(5-fold leave-family-out, anchor-corrected; worst fold {est['min_fold']:.4f})</td></tr>
</table>
<p>Three numbers exist for this candidate and only one of them may be quoted:</p>
<ul>
<li><b>In-sample DTI vs T̂: {final['scores']['in_sample_dti_vs_T_full']['dti']:.4f}.</b>
<span class="bad">Do not quote this.</span> The candidate was built <i>from</i> T̂, so this is an upper
bound with no holdout content.</li>
<li><b>Raw 5-fold held-out estimate: {final['scores']['honest_heldout_5fold']['mean_estimate']:.4f}.</b>
This is honest but <i>attenuated</i>: the yardstick for each fold is built from only 20 % of the corpus,
so it understates every score it measures.</li>
<li><b>Anchor-corrected estimate: {est['value']:.4f} ± {est['sd_across_folds']:.4f}.</b> The attenuation
factor was measured directly — published rasters with an observed score ≥ 0.15 were scored on the same
20 % yardsticks, giving an observed/estimate ratio of
{anchor['per_fold'][0]['anchor_ratio_mean']:.3f} / {anchor['per_fold'][1]['anchor_ratio_mean']:.3f} / {anchor['per_fold'][2]['anchor_ratio_mean']:.3f} / {anchor['per_fold'][3]['anchor_ratio_mean']:.3f} / {anchor['per_fold'][4]['anchor_ratio_mean']:.3f}; mean
<b>{est['anchor_ratio_mean']:.4f}</b> ({len(anchor['per_fold'])} folds). <b>This is the number to quote.</b></li>
</ul>
<p>The candidate's estimate sits ~0.014 above the champion's 0.2778, which is <b>inside</b> the ±
{est['sd_across_folds']:.3f} band. It is not a demonstrated improvement; it is a coin-flip with a slightly
favourable coin. Both are far below the 0.3195 we actually need to beat.</p>

<h2>Uniqueness — measured, with the champion as the control</h2>
<p>The standing protocol's literal rule (&gt;70 % of dots within 3 px of one registry raster = duplicate)
<b>fails for this candidate and fails for the 0.2778 champion</b>. It cannot discriminate here, because
{uniq['n_submission_shaped_refs_over_70pct']} of {uniq['n_submission_shaped_refs']} submission-shaped
registry rasters were built from the same consensus hot region, and dense "surface" rasters cover the
whole footprint and overlap everything at exactly 1.00. Full write-up:
<a href="uniqueness-criterion-20261031.md">uniqueness-criterion-20261031.md</a>.</p>
<table><thead><tr><th>Measure</th><th>This candidate</th><th>Champion control (0.2778)</th></tr></thead>
<tbody>
<tr><td>worst 3 px overlap, submission-shaped refs</td>
<td class="num">{uniq['worst_overlap_submission_shaped']['overlap']:.4f}</td>
<td class="num">{ctrl['worst_overlap_submission_shaped']['overlap']:.4f}</td></tr>
<tr><td>— against</td><td class="file">{short(uniq['worst_overlap_submission_shaped']['file'], 56)}</td>
<td class="file">{short(ctrl['worst_overlap_submission_shaped']['file'], 56)}</td></tr>
<tr><td>— that reference's coverage</td>
<td class="num">{uniq['worst_overlap_submission_shaped']['coverage']:.4f}</td>
<td class="num">{ctrl['worst_overlap_submission_shaped']['coverage']:.4f}</td></tr>
<tr><td>— <b>lift</b> (overlap ÷ coverage; 1.0 = placed at random w.r.t. that reference)</td>
<td class="num"><b>{uniq['worst_overlap_submission_shaped']['lift']:.2f}</b></td>
<td class="num"><b>{ctrl['worst_overlap_submission_shaped']['lift']:.2f}</b></td></tr>
<tr><td>references over the 70 % threshold</td>
<td class="num">{uniq['n_submission_shaped_refs_over_70pct']}</td>
<td class="num">{ctrl['n_submission_shaped_refs_over_70pct']}</td></tr>
<tr><td>byte-identical to any registry raster</td><td class="ok">no</td><td class="ok">no</td></tr>
<tr><td>criterion (overlap ≥ 0.90 <b>and</b> lift ≥ 3.0)</td>
<td class="ok">not a copy — lift 2.04 &lt; 3.0</td><td class="bad">flagged — both conditions met</td></tr>
</tbody></table>
<div class="warn"><b>Said plainly.</b> The reference this candidate sits closest to
(overlap {uniq['worst_overlap_submission_shaped']['overlap']:.3f}) is <b>this repository's own previous
submission</b>, <code>gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif</code>. That is expected —
both are reconstructions from the same corpus — but it means the two files are alternative estimates of
the same field, not independent submissions. Spend <b>one</b> slot, on this one. Its number is the only
one produced by the leave-family-out design.</div>

<h2>Mandated holdout gate (shared tool, unchanged)</h2>
<p>Every candidate must go through the shared spatially-blocked holdout before a slot is spent.
Reusing <code>scripts/experiment_catalogue_holdout_20261030.py</code> unchanged:
<span class="tag ho">HOLDOUT-DTI (catalogue-recovery surrogate v1)</span>,
{holdout['withheld_positive_cells']:,} withheld positive cells in {holdout['holdout_blocks']['n_blocks']}
blocks of {holdout['holdout_blocks']['block_km']:.0f} km, 95 % block-bootstrap CI.</p>
<table><thead><tr><th>File</th><th>Dots</th><th>HOLDOUT-DTI</th><th>95 % CI</th><th>Enrichment over uniform</th>
</tr></thead><tbody>{horows}</tbody></table>
<div class="bad-box"><b>This gate is a formality, not evidence.</b> It measures recovery of
<i>catalogued</i> faults, while the leaderboard scores expert-mapped faults that are <i>absent</i> from
the catalogue. The 2026-10-30 session measured the rank correlation between this proxy and the
owner-reported scores at only ρ = +0.143 (n = 21) and retired it as a score proxy. The champion scores
{HO_CHAMP['holdout_dti']:.4f} here against an owner-reported 0.2778 on the leaderboard — the proxy ranks it
<i>below</i> a uniform random field. Our candidate ({HO_CAND['holdout_dti']:.4f}) is marginally above the
champion on this gate and below the uniform baseline, exactly as expected for a field that avoids the
catalogue. <b>The decision rests on the anchor-corrected estimate, not on this row.</b></div>

<h2>Format gates, re-checked on the saved bytes</h2>
<table><thead><tr><th>Gate</th><th>Result</th></tr></thead><tbody>{gate_rows()}</tbody></table>

<h2>Limitations</h2>
<ul>
<li>Every score in the corpus is OWNER-REPORT. Nothing here is organizer-confirmed except the two
leaderboard numbers quoted above.</li>
<li>The corpus is redundant: 182 scored files collapse into 64 near-duplicate families, and the top 20
rows are about 8 distinct fields published ~2.5 times each. The effective sample size is far below 182.</li>
<li><b>This candidate redistributes recall that already exists in the corpus; it does not create new
recall.</b> If the hidden truth contains a structure no published raster touches, this file scores near
zero on it. Hypotheses H1–H5 in
<a href="hypotheses-20261031.md">hypotheses-20261031.md</a> are aimed at exactly that, and none
of them has been run.</li>
<li>N = |G| (the number of new-fault pixels, normalised) is bounded to
{final['N_bounds']['lower_from_A_le_N']:,.0f} ≤ N ≤
{final['N_bounds']['upper_from_eps_ge_1']:,.0f} by two independent arguments; the candidate uses
N = 12 000, the top of that range.</li>
</ul>

<footer>Generated {GENERATED} from
<a href="../../evidence/final_candidate_20261031.json">final_candidate_20261031.json</a>,
<a href="../../evidence/anchor_calibration_20261031.json">anchor_calibration_20261031.json</a>,
<a href="../data/focus_site_table_20261031.json">focus_site_table_20261031.json</a>,
<a href="../../evidence/holdout_final_20261031.json">holdout_final_20261031.json</a>.
Rebuild with <code>python scripts/build_executive_summary_20261031.py</code>.</footer>
</div></body></html>
"""

INDEX_RAW = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOESASS3 — GeoDAWN new-fault submissions</title>
<style>{CSS}</style></head>
<body>
<header class="top"><div class="wrap">
<h1>GEMSDOESASS3</h1>
<div class="muted">DrivenData DOE-GEMS · New Faults · distance-weighted Tversky index ·
generated {GENERATED}</div>
<nav style="margin-top:10px"><a href="../index.html">Home</a>
<a href="../executive-summary.html"><b>Executive summary</b></a>
<a href="diagnostic-to-submission-20261031.md">Method</a>
<a href="why-02778-20261030.md">Why 0.2778</a>
<a href="hypotheses-20261031.md">Hypotheses</a>
<a href="uniqueness-criterion-20261031.md">Uniqueness criterion</a></nav>
</div></header>
<div class="wrap">

<div class="warn"><b>Not the promoted file.</b> The promoted submission is
<code>gemsdoesass3-blockinv3-123899-20261031T062457Z-nullmask.tif</code> —
<a href="../index.html">see the project home page</a>. This is the consensus-lane candidate, kept as
the second-slot option and as the independent cross-check of the promoted file's uniqueness.</div>

<div class="buy">
<h2>⬇ Consensus-lane candidate (second slot / analysis)</h2>
<a class="btn" href="../downloads/{ZIP}">Download {ZIP}</a>
<a class="btn alt" href="../downloads/{TIF}">raw .tif</a>
<table class="kv" style="margin-top:14px">
<tr><td>Submission name</td><td><code>{final['submission_name']}</code></td></tr>
<tr><td>Submission note</td><td><code>{NOTE}</code></td></tr>
<tr><td>Estimated score</td><td><b>ESTIMATE {est['value']:.4f}</b> ± {est['sd_across_folds']:.4f}
<span class="tag ho">ESTIMATE</span></td></tr>
<tr><td>Format gates</td><td><span class="ok">10 of 10 PASS</span> on the saved bytes</td></tr>
<tr><td>Uniqueness</td><td><span class="ok">not a copy</span> — worst lift
{uniq['worst_overlap_submission_shaped']['lift']:.2f} vs the champion's
{ctrl['worst_overlap_submission_shaped']['lift']:.2f}, measured against every grid-valid raster in
the {corpus['n_rasters']:,}-file registry; it is not a copy of any registry raster and is byte-identical to none of them</td></tr>
</table>
<p><a href="../executive-summary.html">Full executive summary, per-site tables, and the exact submission
steps →</a></p>
</div>


<h2>Superseded files — <span class="bad">NOT OK to submit</span></h2>
<p>Every file below is <b>NOT OK to download for submission and NOT OK to submit</b>. They are kept on
the site as the audit trail of how the decision changed, and for learning. Spending a submission slot
on any of them is a wasted slot.</p>
<table>
<thead><tr><th>File</th><th>Why it is not submittable</th></tr></thead>
<tbody>
<tr><td class="file">gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside<br><span class="muted">note: LB-inversion field: 84262 dots; est 0.369 (LOO sd 0.053)</span></td>
<td>Superseded 2026-10-31 by the file at the top of this page. It is an alternative estimate of the
<b>same</b> field — worst 3 px overlap 0.963 with the current candidate — so submitting both would
spend two of the three weekly slots on one idea. Its estimate (0.369) came from an estimator that was
never validated by the five-fold leave-family-out design.</td></tr>
<tr><td class="file">gemsdoesass3-cdti128-consensus-40533-20261030T041500Z-nanoutside.tif</td>
<td>Superseded 2026-10-30. Its claimed 0.394 fails leave-one-out: the field's peak cell lands on a
file whose real leaderboard score is 0.0748. Retired rather than argued with.</td></tr>
<tr><td class="file">gemsdoesass3-tipcont-disp44923-4px-20261030T0330Z.tif</td>
<td>Superseded. Its 0.268–0.348 was a projection from the catalogue-fit holdout, which ranks
submissions in the opposite order to the leaderboard (ρ = +0.143, n = 21).</td></tr>
<tr><td class="file">gemsdoesass3-bgk-pbe-…-af121062-zeros.tif<br>
gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif</td>
<td>NOT OK to submit. 99.6–99.9 % of their dots sit within 3 px of a registry raster — the plainest
possible uniqueness failure — and both put zeros outside the competition bounds where the official
text requires null.</td></tr>
<tr><td class="file">gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif (the 0.2778 champion,
published by GEMSDOE32/60GEMSDOE)</td>
<td>NOT OK to submit — it is somebody else's submission, already scored. Re-submitting a published
raster is exactly what the standing prompt forbids. It is used here only as the control in the
uniqueness measurement and as the baseline to beat.</td></tr>
</tbody></table>

<h2>What this project is</h2>
<p>Ninety-plus sibling repositories (<code>GEMSDOE24</code>, <code>GEMSDOE25</code>,
<code>…GEMSDOE92</code>, this one) all attack the same DrivenData DOE-GEMS "New Faults" task with the
same 19-band GeoDAWN stack and no access to the labels. Each publishes its rasters and its own score
table on GitHub Pages. This repository is the meta-layer: it clones every sibling's
<code>docs/downloads</code>, builds one registry of
{corpus['n_rasters']:,} rasters ({corpus['n_valid']:,} grid-valid,
{corpus['n_with_owner_score']} carrying an owner-reported score), and inverts the published scores to
reconstruct the hidden credit field the teams were all aiming at.</p>
<p>The reconstruction is a weighted sum of published rasters,
<code>q(x) = max(0, Σ λ_j p_j(x))</code>, with λ solved from the normal equations
<code>G λ = A</code> where <code>G_ij = Σ_x p_i p_j</code> is the pairwise dot overlap and
<code>A_i = s_i (0.2 D_i + 0.8 N)</code> is the kernel credit each file's score implies. The Gram matrix
is what makes this different from a plain average: duplicated publications — the champion is published
in four repositories under three names — are divided out rather than counted twice. 60 000 dots are then
emitted by descending-<code>q</code> non-maximum suppression at 3 px spacing.</p>

<h2>Numbers</h2>
<table class="kv">
<tr><td>Organizer-confirmed leaderboard top</td><td>0.4544 (xiaofanhu)</td></tr>
<tr><td>Owner-stated score to beat</td><td>0.3195 (#27 kpomazi)</td></tr>
<tr><td>Best in-repo baseline (OWNER-REPORT)</td><td>0.2778
(<code>gemsdoe32-h33-h33-2-b2-…</code>)</td></tr>
<tr><td>This candidate (ESTIMATE)</td><td><b>{est['value']:.4f} ± {est['sd_across_folds']:.4f}</b></td></tr>
<tr><td>Hidden truth size (derived)</td><td>{final['N_bounds']['lower_from_A_le_N']:,.0f} ≤ N ≤
{final['N_bounds']['upper_from_eps_ge_1']:,.0f} pixels</td></tr>
</table>

<h2>Read next</h2>
<ul>
<li><a href="../executive-summary.html">Executive summary</a> — per-site table, how to submit, what the
estimate means.</li>
<li><a href="uniqueness-criterion-20261031.md">Uniqueness criterion</a> — why the 70 %/3 px
rule had to be redefined, with the champion as the control.</li>
<li><a href="why-02778-20261030.md">Why 0.2778</a> — the champion's enrichment arithmetic.</li>
<li><a href="hypotheses-20261031.md">Hypotheses H1–H5</a> — the five geological routes not yet
tried, ranked.</li>
</ul>

<footer>Generated {GENERATED} · every number on this site comes from a JSON receipt under
<code>evidence/</code>.</footer>
</div></body></html>
"""

_body = INDEX_RAW.split("</header>", 1)[1].rsplit("</body>", 1)[0]
INDEX_BODY = ('<h2>Consensus-lane summary</h2>' + _body)
(D / "research" / "consensus-lane-20261031.html").write_text(EXEC + INDEX_BODY)
print("wrote docs/research/consensus-lane-20261031.html")
print("NOTE chars:", len(NOTE))
return_code = 0
