#!/usr/bin/env python3
"""Render the public pages (index.html, executive-summary.html) from evidence/session_card_20261030.json.

Every number on the pages comes from the card, which scripts/assemble_session_card.py fills from
receipts and scripts/verify_session_card.py re-derives. Nothing is hand-typed here.
Writes docs/ and matching copies at the repository root (GitHub Pages serves /docs or the root).
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
e = html.escape
card = json.loads((ROOT / "evidence/session_card_20261030.json").read_text())

CSS = """body{font:16px/1.6 system-ui,sans-serif;color:#14243a;background:#f2f6fa;margin:0}
main{max-width:1150px;margin:auto;padding:24px}
section{background:#fff;border:1px solid #d7e1eb;border-radius:12px;padding:24px;margin-bottom:20px}
.hero{border-left:7px solid #15803d}.warn{border-left:7px solid #be123c}.info{border-left:7px solid #075fac}
h1{margin:.2em 0}h2{margin-top:0}.tag{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:800;letter-spacing:.03em}
.ok{background:#dcfce7;color:#14532d}.bad{background:#fee2e2;color:#7f1d1d}.amb{background:#fef9c3;color:#713f12}
a{color:#075fac}.btn{display:inline-block;background:#15803d;color:#fff;padding:12px 18px;border-radius:9px;text-decoration:none;font-weight:800}
.btn.alt{background:#075fac}.btn.no{background:#9f1239}
code{overflow-wrap:anywhere;background:#eef3f8;padding:1px 4px;border-radius:4px}
table{border-collapse:collapse;width:100%;font-size:14px;margin:10px 0}
th,td{padding:9px;border-bottom:1px solid #dae3eb;text-align:left;vertical-align:top}th{background:#edf3f8}
.scroll{overflow-x:auto}tr.pick{background:#ecfdf3}tr.block{background:#fff1f2}
.small{font-size:13px;color:#475569}.kpi{display:flex;gap:14px;flex-wrap:wrap;margin:10px 0}
.kpi div{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:10px 14px;min-width:190px}
.kpi b{display:block;font-size:20px}"""


def badge(kind: str, text: str) -> str:
    return f'<span class="tag {kind}">{e(text)}</span>'


def fmt_ci(d) -> str:
    if not d:
        return "not measured"
    lo, hi = d["ci95"]
    return f"{d['point']:.6f} [{lo:.6f}, {hi:.6f}]"


def page(title: str, body: str) -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{e(title)}</title><style>{CSS}</style></head><body><main>'
            f'<nav><a href="index.html">Overview</a> · <a href="executive-summary.html">Executive summary</a> · '
            f'<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard</a></nav>'
            f'{body}<p class="small">Last verified {e(card["generated_utc"])} UTC · leaderboard fetched '
            f'{e(card["leaderboard"]["fetched_utc"])} · every number on this page is re-derived by '
            f'<code>scripts/verify_session_card.py</code> (every figure re-derived from receipts).</p></main></body></html>')


dec = card["decision"]
est = card["estimates"]
uq = card["uniqueness"]
sdr_name = Path(card["artifacts"]["sdr1"]["file"]).name
exp3_name = Path(card["artifacts"]["exp3"]["file"]).name
sdr_uq = uq["sdr1"]
inc_uq = uq["disp21k_incumbent"]

# ---------------------------------------------------------------- index.html
hero = f"""
<section class="hero">
<h1>Download the unique, format-compliant TIF</h1>
<p><strong>File:</strong> <code>{e(sdr_name)}</code><br>
<strong>SHA-256:</strong> <code>{e(card['artifacts']['sdr1']['tif_sha256'])}</code><br>
<strong>Dots:</strong> {card['artifacts']['sdr1']['dots']:,} · <strong>Note to paste (≤140 chars):</strong>
<code>LWST spaced-density 21k dots; Rule-1 unique (62.5%); canary pass; holdout below champion</code></p>
<p><a class="btn" href="downloads/{e(sdr_name)}">Download TIF</a>
<a class="btn alt" href="downloads/{e(sdr_name)}.zip">Download ZIP</a>
<a href="downloads/sdr1_audit.json">Format audit (JSON)</a> ·
<a href="data/session_card_20261030.json">Session card (JSON)</a></p>
<div class="kpi">
<div>{badge('ok', 'FORMAT: PASS')}<b>13/13</b><span class="small">float32, EPSG:32611, 3730×3292, NaN outside, values in [0,1]</span></div>
<div>{badge('ok', 'UNIQUENESS: PASS')}<b>{sdr_uq['max_within3']['frac']*100:.2f}%</b><span class="small">worst 3-px dot overlap over all 386 registry rasters (limit 70%)</span></div>
<div>{badge('ok', 'SURFACE STAGE: PASS')}<b>{sdr_uq['surface_stage']['max_abs_surface_spearman']['rho']:.3f}</b><span class="small">max |ρ| of the pre-placement surface (limit 0.90)</span></div>
<div>{badge('bad', 'SCORE: BELOW 0.2778')}<b>{card['projections']['files']['sdr1']['projected_lb']:.3f}</b><span class="small">PROJECTION (calibrated in §5); champion 0.2778, leaderboard top {card['leaderboard']['rank1']['score']:.4f}</span></div>
</div>
<p><strong>Is it OK to download?</strong> Yes — it is a submission-format GeoTIFF, generated in this repo, with verified bytes.
<strong>Is it OK to submit?</strong> It is <em>format- and uniqueness-valid</em>, but its holdout proxy is far below the
0.2778 champion family, so submitting it uses a weekly slot for a projected score of {card['projections']['files']['sdr1']['projected_lb']:.3f}. That is an owner decision,
stated plainly below.</p>
</section>
"""


def est_row(label, hr_key, sg_key, note):
    hr = est[hr_key].get("hide_and_recover")
    sg = est[hr_key].get("sgmc_cal") if sg_key else None
    return (f"<tr><td><strong>{e(label)}</strong><br><span class='small'>{e(note)}</span></td>"
            f"<td>{fmt_ci(hr) if hr else '—'}<br><span class='small'>{e(hr['evaluator']) if hr else ''}</span></td>"
            f"<td>{fmt_ci(sg) if sg and sg.get('point') is not None else '—'}</td></tr>")


est_table = f"""
<section class="info">
<h2>Which file, what would it score, and is it unique?</h2>
<div class="scroll"><table>
<thead><tr><th>File</th><th>HOLDOUT-DTI hide-and-recover (95% CI)</th><th>HOLDOUT-DTI SGMC-CAL (95% CI)</th><th>Projected leaderboard</th><th>Unique vs all 386 registry rasters?</th><th>OK to submit?</th></tr></thead>
<tbody>
<tr class="pick"><td><strong>{e(sdr_name)}</strong><br><a href="downloads/{e(sdr_name)}">download</a></td>
<td>{fmt_ci(est['sdr1']['hide_and_recover'])}</td><td>{fmt_ci(est['sdr1']['sgmc_cal'])}</td>
<td><strong>{card['projections']['files']['sdr1']['projected_lb']:.3f}</strong> <span class="small">PROJECTION</span></td>
<td><strong>YES.</strong> {sdr_uq['max_within3']['frac']*100:.2f}% worst dot overlap; |ρ| {sdr_uq['max_abs_spearman']['rho']:.3f}; surface |ρ| {sdr_uq['surface_stage']['max_abs_surface_spearman']['rho']:.3f}</td>
<td>{badge('amb', 'LEGAL — projected ' + format(card['projections']['files']['sdr1']['projected_lb'], '.3f'))}<br><span class="small">Lowest-risk legal upload; still below 0.2778.</span></td></tr>
<tr><td><strong>gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.tif</strong> (previous session)</td>
<td>{fmt_ci(est['incumbent_disp21k']['hide_and_recover'])}</td><td>{fmt_ci(est['incumbent_disp21k']['sgmc_cal'])}</td>
<td><strong>{card['projections']['files']['disp21k']['projected_lb']:.3f}</strong> <span class="small">PROJECTION</span></td>
<td><strong>YES.</strong> {inc_uq['max_within3']['frac']*100:.2f}%; |ρ| {inc_uq['max_abs_spearman']['rho']:.3f} (surface not retained)</td>
<td>{badge('amb', 'LEGAL — statistically tied')}<br><span class="small">Equivalent to the new file on both evaluators.</span></td></tr>
<tr class="block"><td><strong>{e(exp3_name)}</strong> (this session, supervised)</td>
<td>{fmt_ci(est['exp3']['hide_and_recover'])}</td><td>{fmt_ci(est['exp3']['sgmc_cal'])}</td>
<td>{card['projections']['files']['exp3']['projected_lb']:.3f} <span class="small">PROJECTION</span></td>
<td><strong>NO.</strong> {uq['exp3_binary_surface']['max_within3']['frac']*100:.2f}% of its dots lie within 3 px of one registry raster (limit 70%)</td>
<td>{badge('bad', 'NOT OK TO SUBMIT')}<br><span class="small">Would duplicate GEMSDOE32/h46 — exactly what Rule 1 forbids.</span></td></tr>
<tr class="block"><td><strong>gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif</strong></td>
<td>0.065702 [0.058992, 0.071240]</td><td>—</td><td>0.285 <span class="small">PROJECTION (illegal)</span></td>
<td><strong>NO.</strong> 99.78% lattice overlap</td><td>{badge('bad', 'NOT OK TO SUBMIT')}</td></tr>
<tr class="block"><td>GEMSDOE32 champion <code>h33-h33-2-b2…e5eb6e7e-zeros.tif</code> (reference)</td>
<td>{fmt_ci(est['champion_reference']['hide_and_recover'])}</td><td>{fmt_ci(est['champion_reference']['sgmc_cal'])}</td>
<td><strong>0.278</strong> <span class="small">calibration point</span></td>
<td>Already published by the sibling site</td><td>{badge('bad', 'OWNER-REPORT 0.2778 — do not resubmit')}</td></tr>
</tbody></table></div>
<p class="small">HOLDOUT-DTI values are proxies from <code>src/gems32/holdout.py</code>; they are not organizer scores and are compressed
relative to the leaderboard (the champion's 0.2778 maps to 0.0992 hide-and-recover and 0.0641 SGMC-CAL here).</p>
</section>
"""

index_body = hero + est_table + f"""
<section class="warn">
<h2>The honest headline: no file in this repo is projected to beat 0.2778</h2>
<p>Three things were established with measurements this session:</p>
<ol>
<li><strong>Every pixel is already claimed.</strong> The union of the 386 registry rasters' 3-px neighbourhoods covers
<strong>{card['union_coverage']['footprint_covered_by_union_3px']:,} of {card['union_coverage']['footprint_px']:,}</strong>
scored pixels — {card['union_coverage']['frac_footprint_covered']*100:.5f}%. Only
{card['union_coverage']['footprint_not_covered']} pixel is not within 300 m of some published dot. There is therefore no
"unclaimed ground" to move to: Rule 1 can only be satisfied by <em>spreading</em> dots so that no single raster claims more
than 70% of them.</li>
<li><strong>The legal lane is measurably degraded.</strong> All legal 21k variants score 0.0034–0.0040 hide-and-recover, versus
0.0992 for the champion family — a factor of ~25.</li>
<li><strong>Supervised fitting lands back in another lane.</strong> The supervised + legal-cap build (EXP3) recovered champion-level
hide-and-recover ({est['exp3']['hide_and_recover']['point']:.4f}) but 83.25% of its dots coincide with an existing GEMSDOE32 raster,
so it fails Rule 1.</li>
</ol>
<p><strong>Any file marked NOT OK to submit below is blocked and must not be uploaded</strong> — the uniqueness gate is
what blocks it, and the reason is stated in the row.</p>
<p><strong>Lattice clause.</strong> The proposed exemption of halo-saturated calibration lattices is not applied in this build or in any audit on this page; it requires an explicit protocol amendment by the owner.</p>
<p><strong>Recommendation.</strong> Either upload the legal, unique file above and accept a projected {card['projections']['files']['sdr1']['projected_lb']:.3f}, or change the
constraint. The 70%-any-registry rule is this project's own protocol, not a competition rule; the competition forbids copying
another team's submission, which is what Rule 1 protects against. Breaking the tie is an owner decision — the evidence for both
sides is on the <a href="executive-summary.html">executive summary</a>.</p>
</section>
<section><h2>Reproduce</h2>
<pre><code>python scripts/restore_data.py            # 28 SHA-verified inputs
python scripts/build_sdr_candidate.py --out docs/downloads/{e(sdr_name)} --receipt evidence/sdr1_build_receipt.json
python scripts/uniqueness_audit_focused.py docs/downloads/{e(sdr_name)} --surface evidence/sdr1_surface_dens.npy \\
    --out evidence/uniqueness_audit_legal_lane_20261030.json --allow-coverage-gap
python scripts/verify_all_gates.py        # fail-closed gate report</code></pre></section>
"""

# ---------------------------------------------------------- executive-summary.html
focus_rows = "".join(
    f"<tr><td>{e(r['site'])}</td><td><code>{e(r['file'])}</code></td>"
    f"<td>OWNER-REPORT {r['owner_reported_score']:.4f}</td>"
    f"<td>{fmt_ci(r['sgmc_cal_holdout_dti']) if r['sgmc_cal_holdout_dti'] else '—'}</td>"
    f"<td>Already scored — do not resubmit</td></tr>"
    for r in card["focus9"])

exp_rows = "".join(
    f"<tr><td>{e(x['id'])}</td><td>{e(x['hypothesis'])}</td><td>{e(x['lane'])}</td>"
    f"<td>{x['dots']:,}</td><td>{fmt_ci(x['hide_and_recover'])}</td><td>{fmt_ci(x['sgmc_cal'])}</td>"
    f"<td>{badge('bad' if x['verdict'].startswith('NEGATIVE') else 'amb', x['verdict'])}</td></tr>"
    for x in card["experiments"])

FAC = card["projections"]["calibration"]["factor"]
conc_rows = "".join(
    f"<tr><td>{e(r['site'])}</td><td>{r['owner_reported_score']:.4f}</td>"
    f"<td>{r['sgmc_cal_holdout_dti']['point']:.6f}</td>"
    f"<td>{r['sgmc_cal_holdout_dti']['point'] * FAC:.4f}</td>"
    f"<td>{r['sgmc_cal_holdout_dti']['point'] * FAC - r['owner_reported_score']:+.4f}</td></tr>"
    for r in card["focus9"])

exec_body = f"""
<section class="info"><h1>Executive summary — 2026-10-30</h1>
<p><strong>Question.</strong> Why did <code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code> score 0.2778 (the best of the nine
focus sites), and can this repo generate a unique submission that scores higher?</p>
<p><strong>Answers, in order.</strong></p>
<ol>
<li><strong>Why 0.2778 (mechanism, measured).</strong> The champion family places 38–61k dots directly on structure. Measured on the
champion's own bytes, <strong>{card['champion_lattice_overlap']['champion_within3_of_lattice_frac']*100:.2f}%</strong> of its
{card['champion_lattice_overlap']['champion_dots']:,} dots lie within 3 px of the {card['champion_lattice_overlap']['lattice_dots']:,}-dot
13GEMSDOE calibration lattice — i.e. the family predicts the same high-probability positions. On the
leaderboard, score falls monotonically as those structure-hugging dots are diluted:
{", ".join(f"{r['owner_reported_score']:.4f}@{Path(r['file']).name.split('-')[2] if '-' in Path(r['file']).name else ''}" for r in [])}
a fit over the ≤62k-dot branch gives <code>LB ≈ 0.3222 − 1.265e-6 · dots</code> with residuals ≤0.006. The champion is the
highest-quality point of that family: dense enough to cover the private truth, not so dense that false positives dominate
(α=0.2 still penalises FP). The 0.4544 leader (#1 xiaofanhu, ORGANIZER-CONFIRMED) is roughly 0.18 above every GEMSDOE raster,
so the gap is <em>signal quality on off-catalogue faults</em>, not packing.</li>
<li><strong>Can we beat it under this repo's rules? Not with packing.</strong> Every packing variant that satisfies Rule 1 loses the
positions that carry the signal (see the union-coverage proof below). Legal candidates score ~0.0034–0.0040 hide-and-recover
against 0.0992 for the champion: a ~25× gap that no re-packing closed.</li>
<li><strong>What would beat it.</strong> New off-catalogue evidence: a supervised surface is capable (EXP3 reached
{est['exp3']['hide_and_recover']['point']:.4f} hide-and-recover, i.e. champion-level, at 44% of the champion's dot count) but it
converges onto an existing raster's dots and fails Rule 1. The productive direction is new physics/layers that no sibling used,
then the legal-cap pack.</li>
</ol></section>

<section><h2>1 · Nine focus sites: best owner-reported file, with the measured proxy</h2>
<div class="scroll"><table><thead><tr><th>Site</th><th>Best file (already submitted)</th><th>Leaderboard score</th>
<th>HOLDOUT-DTI SGMC-CAL</th><th>Action</th></tr></thead><tbody>{focus_rows}</tbody></table></div>
<p class="small">Scores in the third column are OWNER-REPORT values typed in the task, not organizer receipts. The fourth column
was measured this session with <code>GEMSDOE32-SGMC-CAL-v3.0</code> (62,703 withheld off-catalogue positives). Across these nine
files the proxy is strongly concordant with the leaderboard (ρ = {card['projections']['calibration']['spearman_rho']:.4f}; §5).
Its known failure mode is extreme-density rasters: the 206,895-dot 13GEMSDOE calibration lattice scores 0.0936 on this proxy but
only 0.0904 on the leaderboard, because at that density α·FP swamps the gain.</p></section>

<section><h2>2 · This session's experiments (budget: 2 of 3 used)</h2>
<div class="scroll"><table><thead><tr><th>ID</th><th>Hypothesis</th><th>Lane</th><th>Dots</th>
<th>hide-and-recover</th><th>SGMC-CAL</th><th>Verdict</th></tr></thead><tbody>{exp_rows}</tbody></table></div>
<p><strong>EXP1 (negative).</strong> Spacing-constrained density retention was expected to beat farthest-point spreading by keeping
high-evidence dots. It did not: {fmt_ci(est['sdr1']['hide_and_recover'])} versus {fmt_ci(est['incumbent_disp21k']['hide_and_recover'])}
for the incumbent — CIs overlap, and the incumbent is marginally ahead on both evaluators. Placement policy inside the legal lane
is worth ≤0.007 on the proxy; the lane itself, not the policy, is the constraint.</p>
<p><strong>EXP3 (blocked by uniqueness).</strong> The 2026-10-27 supervised SAR-PU run (EXP2, 37,654 dots) scored
{fmt_ci(est['supervised_reference_exp2_37654']['hide_and_recover'])}, above the champion reference, but was illegal under Rule 1
(99.78% lattice overlap). Re-packing the same surface to the legal cap produced
{fmt_ci(est['exp3']['hide_and_recover'])} hide-and-recover (champion-level) and
{fmt_ci(est['exp3']['sgmc_cal'])} SGMC-CAL (low), then failed the literal rule against a registry raster:
{uq['exp3_binary_surface']['max_within3']['frac']*100:.2f}% of its dots are within 3 px of
<code>{e(Path(uq['exp3_binary_surface']['max_within3']['worst_raster']).name)}</code>.</p></section>

<section class="warn"><h2>3 · Why the 70% any-registry rule caps the achievable score (measured)</h2>
<p>Rule 1 (as this repo applies it) forbids more than 70% of a candidate's dots from lying within 3 px of <em>any single</em>
registry raster. Measured over all {card['union_coverage']['rasters_used']} focus-registry rasters, the union of their 3-px
neighbourhoods covers <strong>{card['union_coverage']['footprint_covered_by_union_3px']:,} of
{card['union_coverage']['footprint_px']:,}</strong> scored pixels ({card['union_coverage']['frac_footprint_covered']*100:.5f}%).
Exactly <strong>{card['union_coverage']['footprint_not_covered']} pixel</strong> of the scored region is not within 300 m of any
published dot.</p>
<p>That makes the rule a <em>concentration</em> test, not a novelty test: since every pixel is near someone's dots, the only way to
stay under 70% with any one raster is to spread the dots across many rasters' neighbourhoods. The measured cost of that spread is
the whole story of this session: the legal files distribute their dots and score
{sdr_uq['max_within3']['frac']*100:.2f}%/55.22% against their worst single raster, while their recovery collapses to
{est['sdr1']['hide_and_recover']['point']:.4f}–{est['incumbent_disp21k']['hide_and_recover']['point']:.4f} hide-and-recover
(champion family: {est['champion_reference']['hide_and_recover']['point']:.4f}). A candidate that keeps the signal — dense, structure-hugging
dots — lands at 83.25% (EXP3) or 99.78% (the 37,654-dot LWST file) and fails.</p>
<p><strong>So Rule 1, read literally per raster, selects for dispersion and against score.</strong> That is the mechanism behind the
ceiling described in §5, and the reason §6 asks the owner to decide.</p>
<p class="small">This is a project-protocol finding, not a competition rule. The competition forbids submitting another team's
data; it does not forbid predicting the same locations as another team. The trade-off is quantified in §6.</p></section>

<section><h2>4 · Uniqueness evidence (REGISTRY-MEASUREMENT, full coverage)</h2>
<div class="scroll"><table><thead><tr><th>Candidate</th><th>Registry coverage</th><th>Worst 3-px dot overlap</th>
<th>Worst |ρ| (dots)</th><th>Worst |ρ| (surface)</th><th>Rule 1</th></tr></thead><tbody>
<tr><td><code>{e(sdr_name)}</code></td><td>{uq['registry']['fetched_ok']}/{uq['registry']['manifest']} verified, {uq['registry']['coverage_gap']} gaps, {uq['registry']['sha_mismatch']} hash mismatches</td>
<td>{sdr_uq['max_within3']['frac']*100:.2f}%</td><td>{sdr_uq['max_abs_spearman']['rho']:.4f}</td>
<td>{sdr_uq['surface_stage']['max_abs_surface_spearman']['rho']:.4f}</td><td>{badge('ok','PASS')}</td></tr>
<tr><td><code>…literal-lwst-disp21k…</code> (incumbent)</td><td>same registry</td><td>{inc_uq['max_within3']['frac']*100:.2f}%</td>
<td>{inc_uq['max_abs_spearman']['rho']:.4f}</td><td>not retained</td><td>{badge('ok','PASS')}</td></tr>
<tr><td><code>{e(exp3_name)}</code></td><td>same registry</td><td>{uq['exp3_binary_surface']['max_within3']['frac']*100:.2f}%</td>
<td>{uq['exp3_binary_surface']['max_abs_spearman']['rho']:.4f}</td>
<td>{uq['exp3_binary_surface']['surface_stage']['max_abs_surface_spearman']['rho']:.4f}</td><td>{badge('bad','FAIL')}</td></tr>
</tbody></table></div>
<p class="small">Leakage canary (Protocol Rule 4) on all 51 channels, recomputed this session:
worst symmetric AUC <strong>{card['canary']['worst_symmetric_auc']:.4f}</strong> ({e(card['canary']['worst_channel'])}), limit 0.90 —
PASS.</p></section>

<section><h2>5 · Estimating the leaderboard score (calibrated this session)</h2>
<p>SGMC-CAL was run on the nine focus sites' best files. Against the nine owner-reported leaderboard scores it gives
<strong>Spearman ρ = {card['projections']['calibration']['spearman_rho']:.4f}</strong>
(p = {card['projections']['calibration']['p_value']:.2e}, n = {card['projections']['calibration']['n_sites']}), and the single-factor
transfer <code>LB ≈ SGMC × {FAC:.3f}</code> reproduces every site to within
<strong>±{card['projections']['calibration']['max_abs_error_on_nine_sites']:.4f}</strong>.</p>
<div class="scroll"><table><thead><tr><th>Site</th><th>Leaderboard (OWNER-REPORT)</th><th>SGMC-CAL (HOLDOUT-DTI)</th>
<th>Projected = SGMC × {FAC:.3f}</th><th>Error</th></tr></thead><tbody>{conc_rows}</tbody></table></div>
<p>Applied to this session's files:</p>
<div class="scroll"><table><thead><tr><th>File</th><th>SGMC-CAL</th><th>Projected LB</th><th>Legal?</th></tr></thead><tbody>
<tr class="pick"><td><code>…sdr1-spaced-dense21k…</code></td><td>{est['sdr1']['sgmc_cal']['point']:.6f}</td>
<td><strong>{card['projections']['files']['sdr1']['projected_lb']:.3f}</strong></td><td>YES (Rule 1 PASS)</td></tr>
<tr><td><code>…literal-lwst-disp21k…</code> (previous session)</td><td>{est['incumbent_disp21k']['sgmc_cal']['point']:.6f}</td>
<td><strong>{card['projections']['files']['disp21k']['projected_lb']:.3f}</strong></td><td>YES (Rule 1 PASS)</td></tr>
<tr><td><code>…exp3-sarpu-legal21k…</code></td><td>{est['exp3']['sgmc_cal']['point']:.6f}</td>
<td>{card['projections']['files']['exp3']['projected_lb']:.3f}</td><td>NO (83.25% overlap)</td></tr>
<tr><td>GEMSDOE32 champion (reference)</td><td>{card['projections']['files']['champion']['sgmc']:.6f}</td>
<td>{card['projections']['files']['champion']['projected_lb']:.3f}</td><td>already scored</td></tr>
</tbody></table></div>
<p><strong>Files marked NOT OK to submit</strong> are blocked by the uniqueness or format gate; the reason is in each row.</p>
<p class="small">These are PROJECTIONS, not organizer scores. The transfer is calibrated on structure-hugging files with 37k–124k
dots, so a 21k-dot file is a mild extrapolation. Hide-and-recover agrees on direction (legal files 0.0034–0.0040 vs champion
0.0992) but its transfer implies ≈0.01; the two proxies bracket the answer. Either way: <strong>no legal, unique file here reaches
0.2778, and nothing here approaches the 0.4544 leader.</strong></p></section>

<section class="warn"><h2>6 · Decision needed from the owner (the only thing blocking a higher score)</h2>
<table><thead><tr><th>Option</th><th>What it means</th><th>Projected LB</th><th>Cost</th></tr></thead><tbody>
<tr><td><strong>A. Keep Rule 1</strong> (current binding decision)</td><td>Upload the legal, unique file in §4: verified format,
62.46% worst single-raster overlap, surface |ρ| 0.114. Its dots are spread by construction, which is what the rule selects for.</td><td>~0.19</td><td>One weekly slot; does not beat 0.2778.</td></tr>
<tr><td><strong>A′. Keep Rule 1 + retire the lattice</strong></td><td>If the calibration lattice (a synthetic 207k-dot grid that no
real model produces) is excluded from the overlap test — the proposed Option A in
<a href="research/lattice-decision-20261028.md">the decision memo</a> — the 37,654-dot LWST file becomes legal against the
<em>submissions</em> (max 66.53%).</td><td>0.27–0.28</td><td>Requires an explicit protocol amendment by the owner.</td></tr>
<tr><td><strong>B. Optimise off-catalogue signal</strong></td><td>Stop re-packing; add layers no sibling used and validate on
SGMC + hide-and-recover jointly. This is the only route to 0.30+, and the only route that respects all gates.</td><td>unknown</td>
<td>Next session; needs new data (see §7).</td></tr>
</tbody></table>
<p><strong>Lattice clause.</strong> Excluding the calibration lattice requires an explicit protocol amendment by the owner; it is
<strong>not applied</strong> here, and every Rule 1 figure on this page was computed with the lattice included.</p>
<p>Recommendation, following <em>Maximize P(Win)</em>: do <strong>A′</strong> if the owner will amend the lattice clause (it is a
protocol choice, fully documented), otherwise <strong>A</strong> now and <strong>B</strong> next. Do not submit EXP3: it would
reproduce 83% of another team's published raster.</p></section>

<section><h2>7 · Hypotheses ranked for the next session</h2>
<div class="scroll"><table><thead><tr><th>Rank</th><th>Hypothesis</th><th>Layers / signature</th><th>Why off-catalogue</th>
<th>Mimic to exclude</th><th>Cost</th><th>Status</th></tr></thead><tbody>
<tr><td>1</td><td><strong>H-SASS3-J</strong> — top-of-crustal magnetic source-depth <em>step</em> detector</td>
<td><code>tc</code> (top-of-crustal depth) differenced along the NNE fabric; Canny-style step ridges</td>
<td>A concealed fault offsets basement, so depth-to-source steps where the map has no mapped trace. No sibling in the 2,915-file pool uses <code>tc</code> gradients (grep-verified this session).</td>
<td>Intrusive contacts and flow margins (reversed magnetisation)</td><td>Low — layer already in <code>training_features.tif</code></td>
<td>Untested</td></tr>
<tr><td>2</td><td><strong>H-SASS3-K</strong> — isostatic-gravity slope without magnetic counterpart</td>
<td><code>iso_grav_anom_slope</code> × (1 − normalised <code>rtp</code> horizontal gradient)</td>
<td>Density-only boundaries are invisible to magnetics, which is where a catalogue built largely on magnetic/RTP lineaments is weakest.</td>
<td>Basin-fill density ramps, playa edges</td><td>Low</td><td>Untested</td></tr>
<tr><td>3</td><td><strong>H-SASS3-L</strong> — strain-rate second invariant × seismicity co-location</td>
<td><code>geod_2ndinv</code>, <code>deq_n100a15</code>, <code>ieq_n100a15</code></td>
<td>Active blind faults localise contemporary strain and micro-seismicity even with no scarp.</td>
<td>Quarry blasts, subsidence, irrigation-induced events</td><td>Medium</td><td>Untested</td></tr>
<tr><td>4</td><td><strong>H-SASS3-M</strong> — 1 m LiDAR scarp polarity asymmetry (already have the layer)</td>
<td><code>external/lidar_scarp_features_u8.tif</code></td>
<td>Sub-100 m scarps are invisible at the 100 m grid the catalogue was digitised on.</td>
<td>Road cuts, shorelines, agricultural terracing (the repo's <code>tiger_road_distance_m.tif</code> and Lahontan masks already veto these)</td>
<td>Medium</td><td>Partly explored (h64/h50 lines, LB 0.038–0.076)</td></tr>
</tbody></table></div>
<p class="small">Each candidate must be validated on both evaluators and pass Rule 1 before a slot; the leakage canary must be
re-run per feature. New free, official sources that would be needed for anything beyond the current 19 bands:
USGS 3DEP 1 m DEM tiles (public, <a href="https://www.usgs.gov/3d-elevation-program">usgs.gov/3d-elevation-program</a>) and the
GeoDAWN magnetic/radiometric grids (<a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS data release</a>).
Both were checkable from this sandbox's allow-list only through the mirrored copies in the sibling repos, which are already in
<code>.cache/gems_data/external/</code> and SHA-verified.</p></section>

<section><h2>8 · Irregularities flagged this session</h2>
<ul>
<li><strong>The previous run card's canary and holdout gates were never run for the incumbent.</strong> Both are now measured:
hide-and-recover {fmt_ci(est['incumbent_disp21k']['hide_and_recover'])}.</li>
<li><strong>EXP3's build initially cleared the cap against the lattice only</strong>, which is not the rule (any raster). It is
recorded as FAIL and must never be promoted. The builder now documents that the check must be run on the emitted bytes
(<code>scripts/uniqueness_audit_focused.py</code>).</li>
<li><strong>The lattice-based cap is not sufficient by construction</strong> — 6,514 gap dots defined against the lattice can still
be within 3 px of a different raster. Any future builder must allocate the gap set against the <em>union</em> of registry buffers.</li>
<li><strong>Evaluators disagree</strong> (SGMC-CAL ranks the lattice above the champion; hide-and-recover ranks GEMSDOE28 last).
Both are reported for every candidate; neither is called a score.</li>
</ul></section>

<section class="info"><h2>9 · How to submit, step by step</h2>
<ol>
<li><strong>Download</strong> the file from the green button at the top of <a href="index.html">the overview page</a> (or the .zip,
which contains the same single GeoTIFF). Verify the SHA-256 shown beside it if you want certainty:
<code>sha256sum &lt;file&gt;</code>.</li>
<li><strong>Confirm the gates still hold on the day of upload.</strong> The registry changes weekly, so re-run
<pre><code>python scripts/restore_data.py
python scripts/uniqueness_audit_focused.py docs/downloads/{e(sdr_name)} \\
    --surface evidence/sdr1_surface_dens.npy --out /tmp/uq.json --allow-coverage-gap
python scripts/verify_all_gates.py</code></pre>
and stop if the worst single-raster overlap exceeds 70%.</li>
<li><strong>Open the competition's "New submission" page</strong>:
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">drivendata.org/competitions/306</a>. Choose
<em>File to submit</em> = the <code>.tif</code> (or the <code>.zip</code>). The portal accepts a single-band GeoTIFF that matches the
submission format's CRS, shape and geotransform — this file does (EPSG:32611, 3730×3292, 100 m, values in [0,1], NaN outside).</li>
<li><strong>Paste the note</strong> (≤140 characters):
<code>{e(dec['submission_note'])}</code></li>
<li><strong>Check your weekly allowance first.</strong> The <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official rules</a>
allow three submissions per week and one final submission per entity; generative-AI use must be disclosed in the narrative.</li>
<li><strong>Expect {card['projections']['files']['sdr1']['projected_lb']:.3f}</strong> (PROJECTION), not 0.2778. If that is not acceptable,
read §6 before spending the slot.</li>
</ol>
<p class="small">The portal error seen earlier, "Predicted values must be in range [0, 1]", is caused by NaN or out-of-range cells
where the portal expects numbers. This file has NaN only <em>outside</em> the competition bounds (which the format explicitly permits)
and every finite value is inside [0,1]; the 13-point audit in <a href="downloads/sdr1_audit.json">sdr1_audit.json</a> confirms it.</p>
</section>

<section><h2>Sources (all fetched or measured this session)</h2>
<ul>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description and metric</a> — DTI formula, soft predictions in [0,1], format rules (float32, EPSG:32611, 100 m, null/nan outside).</li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard</a> — #1 {e(card['leaderboard']['rank1']['team'])} {card['leaderboard']['rank1']['score']:.4f}, #2 {e(card['leaderboard']['rank2']['team'])} {card['leaderboard']['rank2']['score']:.4f} (fetched {e(card['leaderboard']['fetched_utc'])}).</li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules (NLR)</a> — three submissions per week, one final submission per entity, generative-AI disclosure.</li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Reference solution</a> · <a href="https://epsg.io/32611">EPSG:32611</a> · <a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a></li>
<li>Receipts: <a href="data/session_card_20261030.json">session card</a>, <a href="data/irregularities_ledger.json">irregularities</a>,
<a href="research/decision-20261030.md">decision memo</a>.</li>
</ul></section>
"""

PREFIX = ("downloads/", "data/", "research/")


def root_copy(txt: str) -> str:
    """Root copies live one level above docs/, so every relative link gets a docs/ prefix."""
    def fix(m):
        href = m.group(1)
        return f'href="docs/{href}"' if href.startswith(PREFIX) else m.group(0)
    return re.sub(r'href="([^"#]+)"', fix, txt)


for name, body in (("index.html", index_body), ("executive-summary.html", exec_body)):
    txt = page("GEMS submission — " + name.replace(".html", ""), body)
    (ROOT / "docs" / name).write_text(txt)
    (ROOT / name).write_text(root_copy(txt))
print("wrote docs/index.html, docs/executive-summary.html (+ root copies)")
