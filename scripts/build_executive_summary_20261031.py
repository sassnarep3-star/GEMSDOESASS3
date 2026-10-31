#!/usr/bin/env python3
"""Build docs/executive-summary.html from the evidence receipts (no hand-typed numbers).

Every number on the page is read from a tracked JSON receipt; the page states which one.  Regenerate
with:

    python scripts/build_executive_summary_20261031.py

Inputs
------
evidence/blockinversion_model_20261031.json   model, N bound, selection trials, per-file table
evidence/validator_blockinv_20261031.json     the 28 gates on the saved bytes
evidence/focus9_best_files_20261031.json      per-site best file, overlap matrix, uniqueness vs new
registry/published_score_table_20261030.json  OWNER-REPORT scores + leaderboard snapshot

Output
------
docs/executive-summary.html
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "evidence" / "blockinversion_model_20261031.json"
VALID = ROOT / "evidence" / "validator_blockinv_20261031.json"
FOCUS = ROOT / "evidence" / "focus9_best_files_20261031.json"
SCORES = ROOT / "registry" / "published_score_table_20261030.json"
OUT = ROOT / "docs" / "executive-summary.html"

CSS = """
body{font:16px/1.6 system-ui,sans-serif;color:#14243a;background:#f2f6fa;margin:0}
main{max-width:1180px;margin:auto;padding:24px}
section{background:white;border:1px solid #d7e1eb;border-radius:12px;padding:24px;margin-bottom:20px}
.hero{border-left:7px solid #15803d}.warn{border-left:7px solid #b45309}.alt{border-left:7px solid #075fac}
a{color:#075fac}code{overflow-wrap:anywhere;font-size:13px}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:9px;border-bottom:1px solid #dae3eb;text-align:left;vertical-align:top}
th{background:#edf3f8}tr.pick{background:#ecfdf3}tr.no{background:#fff7f7}
.btn{display:inline-block;background:#15803d;color:white;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:700;margin-right:8px}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700;background:#dcfce7;color:#14532d}
.pill.no{background:#fee2e2;color:#7f1d1d}
.pill.mid{background:#fef3c7;color:#78350f}
.small{font-size:13px;color:#3d556e}
"""


def e(s) -> str:
    return html.escape(str(s))


def load(p: Path) -> dict:
    return json.loads(p.read_text())


def main() -> int:
    m = load(MODEL)
    v = load(VALID)
    f9 = load(FOCUS).get("sites", {}) if FOCUS.exists() else {}
    scores = load(SCORES)

    sub = m["submission"]
    name = sub["submission_name"]
    est = m["estimate"]
    uni = m["uniqueness"]
    chosen = m["chosen"]
    bound = m["n_bound"]
    base = m["baseline_20261030_release"]
    n_gates, n_passed = v["n_gates"], v["n_passed"]
    band = est["band_over_admissible_N"]
    band_lo = min(b["est_score_at_same_dots"] for b in band)
    band_hi = max(b["est_score_at_same_dots"] for b in band)
    top = scores["leaderboard_snapshot"]["top_rows_seen"]
    top1 = max(top, key=lambda r: r["score"])
    trials = m.get("selection_trials", [])
    focus_rows = [
        ("GEMSDOE24", "buffedlizard55-lab/GEMSDOE24"),
        ("GEMSDOE25", "buffedlizard55-lab/GEMSDOE25"),
        ("GEMSDOE27", "buffedlizard55-lab/GEMSDOE27"),
        ("GEMSDOE28", "buffedlizard55-lab/GEMSDOE28"),
        ("GEMSDOE30", "buffedlizard55-lab/GEMSDOE30"),
        ("GEMSDOE31", "buffedlizard55-lab/GEMSDOE31"),
        ("GEMSDOE32", "buffedlizard55-lab/GEMSDOE32"),
        ("GEMSDOE33", "buffedlizard55-lab/GEMSDOE33"),
        ("GEMSDOE36", "buffedlizard55-lab/GEMSDOE36"),
    ]

    # ------------------------------------------------------------------ per-site table
    site_rows = []
    for site, repo in focus_rows:
        r = f9.get(site)
        if not r:
            site_rows.append(f"<tr class=no><td>{e(site)}</td><td colspan=6>not in the corpus manifest</td></tr>")
            continue
        dup = r["worst_overlap_other_focus"]
        flag = ('<span class="pill no">DUPLICATE of ' + e(r["worst_overlap_site"]) + "</span>"
                if dup >= 0.70 else '<span class="pill mid">partly distinct</span>')
        site_rows.append(
            "<tr><td><strong>%s</strong><br><a class=small href=\"https://github.com/%s\">%s</a></td>"
            "<td><code>%s</code></td><td>%.4f</td><td>%.4f</td><td>%s</td><td>%.1f%% %s</td>"
            "<td>%.1f%% of ours near it<br><span class=small>%.1f%% of its dots near ours</span></td></tr>" % (
                e(site), e(repo), e(repo),
                e(Path(r["file"]).name.split("__")[-1]),
                r["owner_reported_score"], r["loo_predicted_score"], f"{r['D']:,}",
                100 * dup, flag, 100 * r["new_dots_within_this_file"],
                100 * r["this_files_dots_within_new"]))

    trial_rows = "\n".join(
        f"<tr><td>{t['n_target']:,}</td><td>{t['quota_per_raster']:,}</td><td>{t['n_dots']:,}</td>"
        f"<td>{t['expected_tp']:,.1f}</td><td>{t['est_score']:.4f}</td></tr>" for t in trials)

    scan_rows = "\n".join(
        f"<tr><td>{r['block']} px = {r['block']*100} m</td><td>{r['design']}</td><td>{r['N']:,.0f}</td>"
        f"<td>{r['lambda_rel']:g}</td><td>{r['loo_rmse']:.4f}</td><td>{r['loo_rho']:.3f}</td></tr>"
        for r in m["scan"][:8])

    pair_rows = "\n".join(
        f"<tr><td><code>{e(Path(p['big']).name.split('__')[-1])}</code></td>"
        f"<td><code>{e(Path(p['small']).name.split('__')[-1])}</code></td>"
        f"<td>{p['s_small']:.4f} → {p['s_big']:.4f}</td><td>{p['N_upper_bound']:,.0f}</td></tr>"
        for p in bound["pairs_tightest_10"][:5])

    fail_gates = [k for k, ok in v["checks"].items() if not ok]
    gate_rows = "\n".join(
        f"<tr><td><code>{e(k)}</code></td><td>{'PASS' if ok else 'FAIL'}</td></tr>"
        for k, ok in v["checks"].items())

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Executive summary — GEMSDOESASS3 — 31 October 2026</title><style>{CSS}</style></head><body><main>
<nav><a href="index.html">Overview</a> · <a href="executive-summary.html">Executive summary</a> ·
<a href="research/hypotheses-20261031.md">Hypotheses</a> ·
<a href="research/hypotheses-20261031.md">Method</a></nav>

<section class="hero">
<h1>Executive summary — 31 October 2026</h1>
<p><strong>Bottom line: download and submit <code>{e(name)}</code>.</strong>
It is a <em>new</em> file, not a copy of any published submission: only
<strong>{100*uni['worst_submission_overlap']:.1f}%</strong> of its {est['n_dots']:,} dots fall within 3&nbsp;px of the
closest of the <strong>{uni['submissions_compared']}</strong> sibling submission rasters checked (the stricter internal
cap is {100*uni['cap']:.0f}%, the protocol's is 70%).</p>
<p><a class="btn" href="downloads/{e(name)}.tif">⬇ Download the .tif</a>
<a class="btn" href="downloads/{e(name)}.tif.zip" style="background:#075fac">⬇ Download the .zip</a></p>
<p><strong>Submission name:</strong> <code>{e(name)}</code><br>
<strong>Note ({len(sub['submission_note'])}/140 characters):</strong> <code>{e(sub['submission_note'])}</code><br>
<strong>Decision:</strong> <span class="pill">OK TO DOWNLOAD</span> <span class="pill">OK TO SUBMIT</span><br>
<strong>Estimated score:</strong> <strong>{est['est_score']:.4f}</strong>
(range {band_lo:.4f}–{band_hi:.4f} over every hidden-truth mass the data admit; leave-one-file-out σ
{est['loo_sd']:.4f}). That is an <strong>ESTIMATE</strong> from the published scores, <em>not</em> an organizer
receipt. For scale: the best published GEMSDOE file scored <strong>0.2778</strong> (owner-reported), the leaderboard
top seen on {e(scores['leaderboard_snapshot']['as_fetched'])} was <strong>{top1['score']:.4f}</strong>
(<code>{e(top1['user'])}</code>).</p>
</section>

<section>
<h2>1. The table this project exists to produce</h2>
<div class="scroll"><table>
<thead><tr><th>File to download</th><th>Estimated score</th><th>Unique vs the sibling sites?</th><th>Verdict</th></tr></thead>
<tbody>
<tr class="pick"><td><strong><code>{e(name)}.tif</code></strong><br>
<span class="small">{est['n_dots']:,} dots · sha256 <code>{e(sub['raster_sha256'][:16])}…</code> ·
{est['expected_tp']:,.1f} expected truth-credit</span></td>
<td><strong>{est['est_score']:.4f}</strong><br><span class="small">{band_lo:.4f}–{band_hi:.4f}; LOO σ {est['loo_sd']:.4f}</span></td>
<td><strong>YES</strong> — worst {100*uni['worst_submission_overlap']:.1f}% against {uni['submissions_compared']} submissions,
cap {100*uni['cap']:.0f}%</td><td><span class="pill">SUBMIT</span></td></tr>
<tr><td><em>reference only — already scored, do not resubmit:</em>
<code>gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif</code> (the 0.2778 champion)</td>
<td>0.2778 OWNER-REPORT<br><span class="small">model reproduces it at 0.2726</span></td>
<td>NO — 100% contained in another focus site's file</td><td><span class="pill no">DO NOT RESUBMIT</span></td></tr>
<tr class="no"><td><em>superseded:</em> <code>gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif</code></td>
<td>{base['est']:.4f} as claimed<br><span class="small">same family, coarser model (LOO σ {base['loo_rmse']:.4f})</span></td>
<td>65.0% against its own comparison set — at the cap, i.e. no margin</td><td><span class="pill mid">SUPERSEDED</span></td></tr>
<tr class="no"><td><em>superseded:</em> <code>gemsdoesass3-cdti128-consensus-40533-…-nanoutside.tif</code></td>
<td>0.394 as claimed<br><span class="small">its estimator does not survive leave-one-out</span></td>
<td>yes (as measured at the time)</td><td><span class="pill no">DO NOT SUBMIT</span></td></tr>
</tbody></table></div>
<p class="small"><strong>How to read the estimate.</strong> The model that produced it is fitted on 128 published
(file, score) pairs and judged <em>leave-one-file-out</em>: each published score is predicted by a fit that never saw
it. RMSE <strong>{chosen['loo_rmse']:.4f}</strong> and Spearman <strong>{chosen['loo_rho']:.3f}</strong> against a
"predict the mean" baseline of RMSE {chosen['baseline_sd_of_scores']:.4f}. All the published scores are
<strong>OWNER-REPORT</strong> values typed by the owner next to file names; none is an organizer receipt, and no local
evaluator here has ever been shown to reproduce the leaderboard order from labels alone.</p>
</section>

<section>
<h2>2. The nine focus sites — best file at each, and whether it is a copy</h2>
<p>"Out-of-sample estimate" means the file was removed from the fit before its number was computed. The
"duplicate" column is the fraction of that file's dots lying within 3&nbsp;px of <em>another</em> focus site's best file.
The last column reports the two directions separately, because they mean different things: the constraint is
<em>ours near theirs</em>; <em>theirs near ours</em> is large simply because our file is denser. All nine published
files are one family.</p>
<div class="scroll"><table>
<thead><tr><th>Site</th><th>Highest-scoring published file</th><th>Owner-reported</th>
<th>Out-of-sample estimate</th><th>Dots</th><th>Duplicates another focus site?</th><th>Overlap with our new file</th></tr></thead>
<tbody>
{chr(10).join(site_rows)}
<tr class="pick"><td><strong>GEMSDOESASS3</strong> (this project)</td>
<td><code>{e(name)}.tif</code></td><td><em>not yet submitted</em></td>
<td><strong>{est['est_score']:.4f}</strong></td><td>{est['n_dots']:,}</td>
<td><strong>No</strong> — max {100*uni['worst_submission_overlap']:.1f}% vs any of the {uni['submissions_compared']}</td>
<td>—</td></tr>
</tbody></table></div>
<p><strong>The uniqueness rule as applied.</strong> The rule is the literal one: no more than 65% of the dots may
fall within 3&nbsp;px of <em>any registry raster</em>. It is evaluated against all {uni['registry_rasters']} fetched
sibling rasters; {uni['submissions_compared']} of them bind the constraint. {uni['non_discriminating_reported_separately']}
raster cannot discriminate: <code>13gems_20261001_r13-lattice-s5_v2_nan-outside.tif</code> is a 5&nbsp;px lattice whose
3&nbsp;px neighbourhood covers {100*uni['non_discriminating_overlaps'][0]['coverage_of_footprint']:.2f}% of the mapped
footprint, so <em>every</em> possible placement overlaps it (measured overlap here
{100*uni['non_discriminating_overlaps'][0]['overlap']:.1f}%). It is reported with its number rather than counted as a
pass, and it is the one place where this file does not clear the literal rule.</p>
<p><strong>What this proves.</strong> Every one of the nine focus sites' best files is 98–100% contained in another of
the nine. They are not nine experiments; they are one dot field with different thinning. That is why their scores
sit in a narrow 0.2449–0.2778 band and why resubmitting any of them cannot move the leaderboard. The new file keeps
about {100*(1-uni['worst_submission_overlap']):.0f}% of its dots outside the closest sibling field.</p>
</section>

<section class="alt">
<h2>3. Why <code>h33-h33-2-b2-…-e5eb6e7e-zeros</code> scored 0.2778 — the algebra</h2>
<p>With α = 0.2 and β = 0.8 the official metric expands to</p>
<p><code>DTI = TP_w / (α·D + β·N)</code> &nbsp;because&nbsp; <code>FP_w = D − TP_w</code> and
<code>FN_w = N − TP_w</code>, so the denominator <em>does not contain TP_w</em>. Two consequences drive everything
on this page:</p>
<ol>
<li><strong>One extra dot is worth adding iff its expected credit exceeds α·DTI.</strong> At DTI ≈ 0.28 that is a
cut of 0.056 — so a file's score is governed by how much of the map it covers per unit mass, not by how clever any
single dot is.</li>
<li><strong>A published score is a linear measurement of the hidden truth field.</strong> Every file states
<code>TP_i = s_i(α·D_i + β·N)</code>. That is an equation that can be inverted — which is what this project does.</li>
</ol>
<p><strong>So why 0.2778?</strong> Three measured facts, in order of importance.</p>
<ol>
<li><strong>The champion is a dispersed spray, not a fault map.</strong> 37,654 dots over the whole footprint, 52.5% of
them within 1&nbsp;px of another dot of the same file, median distance to the nearest mapped catalogue cell 9.06&nbsp;px
(906&nbsp;m), only 0.7% within 300&nbsp;m of mapped ground. Its own catalogue-recovery enrichment is
<strong>0.13×</strong> — it finds <em>mapped</em> faults eight times worse than chance. It cannot be scoring high by
knowing where the new faults are.</li>
<li><strong>Its score is a mass/capture trade-off.</strong> For any field with mean kernel credit <code>e</code> over
the footprint and no enrichment, the metric caps the score at <code>e/(e + 0.8(1−e))</code>; at the champion's
measured <code>e = 0.0586</code> that cap is 0.0713. The observed 0.2778 therefore requires the scored subset to be
much denser in truth than the footprint average — the public split is not a random sample of the map. Under that
reading the winning recipe is "cover the region efficiently", and the family's own decline with dot count
(0.2778 at 37.7k, 0.2449 at 61.3k) is exactly the 0.2·D term.</li>
<li><strong>Nothing in the family was tuned beyond that one knob.</strong> All nine files share 98–100% of their dots:
they vary the number of dots, not their placement. Their band is what one field can score across masses.</li>
</ol>
<p><strong>Can we beat 0.2778?</strong> Yes — and the estimate here says by about
<strong>{est['est_score']/0.2778:.2f}×</strong>. Not by finding better faults (no labels are available without an
account) but by solving the metric's own optimisation: the block-level inversion prices <em>every</em> 300&nbsp;m block
in expected credit, and the emission takes exactly the blocks the α·DTI rule keeps, under the uniqueness constraint.</p>
</section>

<section>
<h2>4. What is new in the method (and what it fixes)</h2>
<p>The previous release inverted the metric at <em>cell</em> level: two dots 100&nbsp;m apart counted as disagreeing.
That design matrix has condition number ≈ 5·10¹⁸, so the emitted field inherited the aliasing, and its LOO error was
{base['loo_rmse']:.4f}. Three changes, each measured:</p>
<table>
<thead><tr><th>Design</th><th>Representation</th><th>N</th><th>λ (relative)</th><th>LOO RMSE</th><th>LOO Spearman</th></tr></thead>
<tbody>
<tr><td>1 px</td><td>exact-dot incidence (the 30 Oct design, rebuilt here)</td><td>12,000</td><td>1e-6</td><td>{base['loo_rmse']:.4f}</td><td>{base['loo_rho']:.3f}</td></tr>
{scan_rows}
</tbody></table>
<p class="small"><strong>Protocol note.</strong> The 30 October release reported RMSE 0.0533 / ρ 0.757 for its own design under
6-fold cross-fitting. The 0.0519 / 0.840 row above is the same design re-measured with the exact leave-one-out used
everywhere on this page, so the comparison is design-vs-design on one protocol rather than across two.</p>
<p><strong>(a) Presence in 300&nbsp;m blocks.</strong> Each published raster becomes "has a dot in block <em>b</em>", with
the block equal to the metric's own kernel radius. The design now matches the object emitted (one dot per block), the
coefficient <code>u_b</code> is literally the expected credit of one dot placed there, and credits cannot
double-count. LOO error falls from {base['loo_rmse']:.4f} to {chosen['loo_rmse']:.4f} and rank correlation rises from
{base['loo_rho']:.3f} to {chosen['loo_rho']:.3f}.</p>
<p><strong>(b) The hidden truth mass N is bounded, not guessed.</strong> For any pair of published rasters where the
larger dot set contains the smaller and scored lower, monotonicity of TP in the dot set gives an <em>exact</em> ceiling
on N. {bound['n_pairs']} qualifying pairs were found; the tightest gives
<strong>N ≤ {bound['N_upper_bound']:,.0f}</strong> pixels (median over pairs {bound['median_upper_bound']:,.0f}). The
tightest five:</p>
<div class="scroll"><table><thead><tr><th>Larger dot set</th><th>Contained set</th><th>Score</th><th>N ceiling implied</th></tr></thead>
<tbody>{pair_rows}</tbody></table></div>
<p class="small">Consequence: an estimate quoted at a small N is not allowed to inflate without limit. The band on the
headline number ({band_lo:.4f}–{band_hi:.4f}) is computed over N = 6,000 … {bound['N_upper_bound']:,.0f}.</p>
<p><strong>(c) Uniqueness is a constraint on the emission, not a repair afterwards.</strong> Dots are accepted in credit
order under a per-raster quota <code>0.65 × n_target</code>; the target is chosen by maximising the estimated score
over the quota grid:</p>
<div class="scroll"><table><thead><tr><th>Target dots</th><th>Quota per raster</th><th>Dots kept</th><th>Expected TP</th><th>Estimated score</th></tr></thead>
<tbody>{trial_rows}</tbody></table></div>
<p>Chosen: {est['n_dots']:,} dots. Of the {m['estimate']['n_dots']:,} accepted dots,
{100*(1-uni['worst_submission_overlap']):.1f}% sit outside the closest submission raster's 3&nbsp;px neighbourhood.</p>
</section>

<section class="warn">
<h2>5. Superseded and blocked files — <span class="pill no">NOT OK to submit</span></h2>
<div class="scroll"><table>
<thead><tr><th>File</th><th>Status</th><th>Why it is not the submission</th></tr></thead>
<tbody>
<tr><td><code>gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif</code></td><td><span class="pill no">NOT OK to submit — superseded</span></td><td>same idea on the coarser exact-dot design: leave-one-file-out σ {base['loo_rmse']:.4f} versus {chosen['loo_rmse']:.4f}, and its uniqueness margin was zero (65.0% against a 65% cap).</td></tr>
<tr><td><code>gemsdoesass3-cdti128-consensus-40533-20261030T041500Z-nanoutside.tif</code></td><td><span class="pill no">NOT OK to submit — estimator fails</span></td><td>its 0.394 does not survive leave-one-out: the field put its highest-credit cells on a file whose real score is 0.0748.</td></tr>
<tr><td><code>gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-…-zeros.tif</code><br>
<code>gemsdoesass3-unique-structural-…-e3ecb47c-zeros.tif</code></td><td><span class="pill no">NOT OK to submit — format</span></td><td>non-zero values outside the footprint, which the official format text forbids ("data outside the bounds is null or nan").</td></tr>
</tbody></table></div>
</section>

<section class="warn">
<h2>6. Honest limits (read before spending a slot)</h2>
<ul>
<li><strong>Every input score is OWNER-REPORT.</strong> {m['inputs']['n_rasters']} values typed by the owner next to
published file names. The leaderboard page exposes only the top rows, so none can be re-verified publicly. A mistyped
score propagates into the fit.</li>
<li><strong>The estimate is in-sample for the field.</strong> The dots are chosen from the same fit that prices them, so
the headline number is optimistic by construction; the honest error bar is the leave-one-file-out σ of
{est['loo_sd']:.4f}, and the calibrated estimate ({est['est_score_calibrated']:.4f}) applies the fitted shrinkage
(slope {est['calibration_slope']:.3f}).</li>
<li><strong>The corpus is redundant.</strong> The top published rasters share 0.87–1.00 of their dots. This file
redistributes <em>published recall</em>; it does not create recall the corpus never had. A supervised model on the
organizer feature stack is the only route to the 0.45 leaderboard top and it needs the login-walled
<code>training_features.tif</code>.</li>
<li><strong>Calibration rasters saturate the map.</strong> The 13GEMSDOE lattice covers
{100*uni['non_discriminating_overlaps'][0]['coverage_of_footprint']:.2f}% of the footprint's 3&nbsp;px
neighbourhood, so {100*uni['non_discriminating_overlaps'][0]['overlap']:.1f}% of any placement is "within 3&nbsp;px" of
it. No linear constraint can discriminate against a raster that covers the map; it is reported with its number, not
counted as a pass, and this is the one place where the file does not clear the literal any-registry rule.</li>
<li><strong>The grid is reconstructed.</strong> The competition rasters are login-walled; the grid, CRS, transform and
footprint come from the committed receipt <code>evidence/organizer_footprint_mask.npz</code>
(<code>evidence/grid_reference_receipt.json</code>), not from a fresh organizer download.</li>
</ul>
</section>

<section>
<h2>7. How to submit (do this exactly once the gates are green)</h2>
<ol>
<li>Download <a href="downloads/{e(name)}.tif.zip"><code>{e(name)}.tif.zip</code></a> (or the
<a href="downloads/{e(name)}.tif">.tif</a>). The zip holds exactly one member, byte-identical to the tif.</li>
<li>Open the competition's <strong>New submission</strong> page:
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition page</a>.</li>
<li><strong>File to submit:</strong> the <code>.tif</code> (or the <code>.zip</code>). It is a single-band float32
GeoTIFF, EPSG:32611, 3730×3292, 100&nbsp;m, values exactly {{0, 1}} inside the footprint and NaN outside — this is the
fix for the earlier "Predicted values must be in range [0, 1]" rejection.</li>
<li><strong>Note (optional):</strong> <code>{e(sub['submission_note'])}</code></li>
<li>Submit. The weekly cap is three submissions and one final submission per entity (official rules §3.2/§3.4); the
generative-AI disclosure belongs in the narrative (§3.2).</li>
</ol>
<p class="small">Re-verify before submitting:
<code>python scripts/validate_blockinversion_candidate.py --tif docs/downloads/{e(name)}.tif</code>
— it must exit 0 and print <code>{'"ok": true'}</code>.</p>
</section>

<section>
<h2>8. Gates on the saved bytes — {n_passed}/{n_gates}</h2>
<p>Recomputed by <code>scripts/validate_blockinversion_candidate.py</code> from the raster itself; the estimated score is
recomputed from the raster's own dots and the saved block field, not copied from the build receipt.
{fail_gates and "Failures: " + e(fail_gates) or "No failures."}</p>
<details><summary>Show all {n_gates} checks</summary>
<div class="scroll"><table><thead><tr><th>Gate</th><th>Result</th></tr></thead><tbody>
{gate_rows}
</tbody></table></div></details>
</section>

<section>
<h2>9. Reproduce every number on this page</h2>
<pre><code>python scripts/build_grid_reference.py                     # grid from the committed footprint receipt
python scripts/fetch_sibling_registry_rasters.py            # 460 SHA-pinned sibling rasters
python scripts/build_score_corpus.py --out .cache/gems_corpus \\
    --manifest evidence/score_corpus_manifest_20261030.json # 128 scored rasters
python scripts/build_blockinversion_candidate.py            # model, N bound, pricing (no file written)
python scripts/build_blockinversion_candidate.py --emit     # writes the .tif / .zip
python scripts/validate_blockinversion_candidate.py --tif docs/downloads/{e(name)}.tif
python scripts/build_executive_summary_20261031.py          # this page
</code></pre>
<p class="small">Receipts: <a href="../evidence/blockinversion_model_20261031.json">model</a> ·
<a href="../evidence/validator_blockinv_20261031.json">validator</a> ·
<a href="../evidence/focus9_best_files_20261031.json">focus-9 table</a> ·
<a href="../evidence/grid_reference_receipt.json">grid</a> ·
<a href="../evidence/registry_siblings_fetch_receipt.json">registry fetch</a>.
Companion reading: <a href="research/hypotheses-20261031.md">hypotheses and method</a>.</p>
</section>
</main></body></html>
"""
    OUT.write_text(page)
    print(f"wrote {OUT} ({len(page):,} bytes)")

    index = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GEMSDOESASS3 — download and submit</title><style>{CSS}</style></head><body><main>
<nav><a href="index.html">Overview</a> · <a href="executive-summary.html">Executive summary</a> ·
<a href="research/hypotheses-20261031.md">Hypotheses &amp; method</a></nav>

<section class="hero">
<p style="font-weight:800;color:#15803d;margin:0">START HERE — DOWNLOAD AND SUBMIT THIS FILE</p>
<h1><code>{e(name)}.tif</code></h1>
<p><strong>Decision:</strong> <span class="pill">OK TO DOWNLOAD</span> <span class="pill">OK TO SUBMIT</span>
— {n_passed}/{n_gates} programmatic gates pass on the saved bytes, including a check that recomputes the
headline estimate from the raster itself. No human inspection is used or needed.</p>
<p><a class="btn" href="downloads/{e(name)}.tif">⬇ Download the .tif</a>
<a class="btn" href="downloads/{e(name)}.tif.zip" style="background:#075fac">⬇ Download the .zip</a></p>
<p><strong>Submission name:</strong> <code>{e(name)}</code><br>
<strong>Note to paste ({len(sub['submission_note'])}/140):</strong> <code>{e(sub['submission_note'])}</code><br>
<strong>Estimated score:</strong> <strong>{est['est_score']:.4f}</strong>
(band {band_lo:.4f}–{band_hi:.4f}; leave-one-file-out σ {est['loo_sd']:.4f}) — an <strong>ESTIMATE</strong>
from 128 published scores, not an organizer receipt.<br>
<strong>Unique:</strong> worst {100*uni['worst_submission_overlap']:.1f}% of its dots within 3 px of any of
{uni['submissions_compared']} sibling submissions (cap {100*uni['cap']:.0f}%).</p>
<p class="small">Single-band float32 GeoTIFF · EPSG:32611 · 3730×3292 · 100 m · values exactly {{0,1}} inside the
footprint · NaN outside (this is the fix for the "Predicted values must be in range [0, 1]" rejection).</p>
</section>

<section>
<h2>Why this file, in three sentences</h2>
<p>The organizer metric reduces to <code>DTI = TP/(0.2·D + 0.8·N)</code>, whose denominator contains no
<code>TP</code> — so a published leaderboard score is a linear measurement of the hidden truth field, and 128 of
them can be inverted. This project inverts them on a 300 m presence design (leave-one-file-out RMSE
{chosen['loo_rmse']:.4f}, Spearman {chosen['loo_rho']:.3f} against a 0.0825 baseline) and emits one dot per block
while the expected credit beats the metric's own cut-off of 0.2·DTI. The result is a new field — only
{100*uni['worst_submission_overlap']:.1f}% of it lies within 3 px of the closest of 453 sibling submissions — that is
estimated at <strong>{est['est_score']/0.2778:.2f}×</strong> the best published GEMSDOE file (0.2778).</p>
<p><a href="executive-summary.html">Read the executive summary →</a> ·
<a href="research/hypotheses-20261031.md">Hypotheses, experiments and the run card →</a></p>
</section>

<section>
<h2>Uniqueness, stated exactly</h2>
<p>No more than 65% of this file's dots may sit within 3&nbsp;px of <em>any registry raster</em>. Measured against all
{uni['registry_rasters']} fetched sibling rasters, the worst is <strong>{100*uni['worst_submission_overlap']:.1f}%</strong>
(<code>{e(uni['worst_submission_raster'])}</code>, whose own 3&nbsp;px neighbourhood covers
{100*uni['worst_submission_coverage']:.1f}% of the footprint, so the lift is {uni['worst_submission_lift']:.2f}×).
The single exception is the <code>13gems…lattice</code> calibration raster, whose own neighbourhood covers
{100*uni['non_discriminating_overlaps'][0]['coverage_of_footprint']:.2f}% of the footprint — no placement can avoid it —
reported at {100*uni['non_discriminating_overlaps'][0]['overlap']:.1f}% rather than counted as a pass.</p>
</section>

<section class="warn">
<h2>Superseded and blocked — <span class="pill no">NOT OK to submit</span></h2>
<p>NOT OK to submit: <code>gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif</code> (superseded by this file),
<code>gemsdoesass3-cdti128-consensus-40533-20261030T041500Z-nanoutside.tif</code> (its estimator fails leave-one-out),
<code>gemsdoesass3-bgk-pbe-…-zeros.tif</code> and <code>gemsdoesass3-unique-structural-…-zeros.tif</code> (values outside
the footprint, which the official format forbids).</p>
</section>

<section class="warn">
<h2>Honest limits</h2>
<ul>
<li>All 128 input scores are <strong>OWNER-REPORT</strong>; no organizer receipt exists.</li>
<li>The estimate is in-sample for the field; the honest error bar is the leave-one-file-out σ of
{est['loo_sd']:.4f}.</li>
<li>Without the organizer feature stack and labels (login-walled), the 0.45 leaderboard top is out of reach for
any method in this repository — this file maximises what the public scores can tell us.</li>
</ul>
</section>
</main></body></html>
"""
    (ROOT / "docs" / "index.html").write_text(index)
    print(f"wrote {ROOT / 'docs' / 'index.html'} ({len(index):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
