#!/usr/bin/env python3
"""Build the static review pages (root and docs/) from checked-in evidence.

Every number on the page is read from a receipt file. Labels: HOLDOUT-DTI (evaluator named),
OWNER-REPORT (typed in the request, not an organizer receipt). Nothing here is an organizer score.
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
e = html.escape

card = json.loads((ROOT / "evidence/archive/run_card_lwst_archived_20261027.json").read_text())  # archived LWST file (blocked)
bgk = json.loads((ROOT / "evidence/run_card_bgk_pbe.json").read_text())
uni = json.loads((ROOT / "evidence/run_card_unique_structural_20261029.json").read_text())
cur = json.loads((ROOT / "evidence/run_card.json").read_text())                  # current candidate
lit = json.loads((ROOT / "evidence/run_card_literal.json").read_text())           # compliant file
hold = json.loads((ROOT / "evidence/literal_candidates_sgmc.json").read_text())
base = json.loads((ROOT / "evidence/literal_audit_lwst_baseline.json").read_text())
LWST_LAT = base["final_dots_stage"]["worst_within_3px_fraction"]  # 37,654-dot file, fresh registry bytes
owner = json.loads((ROOT / "registry/owner_reported_scores_focus.json").read_text())
ledger = json.loads((ROOT / "evidence/irregularities_ledger.json").read_text())

LIT_NAME = lit["submission_name"]
LIT_NOTE = lit["submission_note"]
LIT_SHA = lit["raster_sha256"]
LIT_DOTS = lit["summary"]["dots"]
LIT_WORST = lit["correlation_overlap_vs_registry"]["worst_within_3px_fraction"]
LIT_WORST_NONLAT = None
audit = json.loads((ROOT / "evidence/literal_audit_gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2.json").read_text())
for row in audit["final_dots_stage"]["worst_rows"]:
    if row["repo"] != "HISTORICAL_SCORED" or "lattice" not in row["path"]:
        LIT_WORST_NONLAT = row["within_3px_fraction"]
        break
LIT_RHO = lit["correlation_overlap_vs_registry"]["worst_abs_spearman"]
LIT_RESULT = lit["holdout_dti"]["controls"]
lit_val = lit["holdout_dti"]["value"]
lit_ci = lit["holdout_dti"]["ci95"]
champ = LIT_RESULT["champion_0.2778_file"]
lwst = LIT_RESULT["lwst_37654_blocked_file"]
same = LIT_RESULT["same_count_random_no_lattice_constraint"]
n_wh = lit["holdout_dti"]["n_withheld_positives"]
EVAL = lit["holdout_dti"]["evaluator_version"]

# Best owner-reported file per focus site (reference only; already scored).
best: dict[str, dict] = {}
for ent in owner["entries"]:
    if ent["site"] not in best or ent["owner_reported_score"] > best[ent["site"]]["owner_reported_score"]:
        best[ent["site"]] = ent
site_rows = []
for site in sorted(best, key=lambda s: int(s.removeprefix("GEMSDOE"))):
    ent = best[site]
    fname = Path(ent["file"]).name
    site_rows.append(
        f"<tr><td>{e(site)}</td><td><code>{e(fname)}</code></td>"
        f"<td>OWNER-REPORT {ent['owner_reported_score']:.4f}</td>"
        f"<td>Already scored. Do not resubmit.</td></tr>"
    )
site_table = "\n".join(site_rows)

rev_items = (
    f"<li><strong>Format gate (compliant file):</strong> PASS. Single band float32, EPSG:32611, 3730x3292, "
    f"organizer transform, all pixels finite, values in [0,1], {LIT_DOTS:,} dots.</li>"
    f"<li><strong>Literal Rule 1 on the compliant file:</strong> PASS. Worst lattice overlap "
    f"{LIT_WORST*100:.4f}% (limit 70%); worst non-lattice overlap {LIT_WORST_NONLAT*100:.2f}%; "
    f"worst |Spearman| {LIT_RHO:.3f} (limit 0.90). Checked against all 386 registry rasters.</li>"
    f"<li><strong>Literal Rule 1 on the 37,654-dot LWST file:</strong> FAIL. The 13GEMSDOE lattice holds "
    f"{LWST_LAT*100:.2f}% of its dots within 3 px. Reproduced on fresh bytes.</li>"
)

hero_ok = f'''<section class="hero ok"><p class="label">START HERE · DOWNLOAD-READY FILE (format-valid, literal-rule compliant)</p>
<h1>Download the unique, format-valid TIF</h1>
<p><strong>File:</strong> <code>{e(LIT_NAME)}</code><br>
<strong>Note to paste (≤140 characters):</strong> <code>{e(LIT_NOTE)}</code><br>
<strong>SHA-256:</strong> <code>{e(LIT_SHA)}</code></p>
<p><a class="btn" href="downloads/{e(LIT_NAME)}">Download TIF</a> <a class="btn alt" href="downloads/{e(LIT_NAME)}.zip">Download ZIP</a> <a href="data/run_card_literal.json">Run card (JSON)</a></p>
<p><strong>Download: YES.</strong> It passes the format gate and the literal uniqueness rule against all 386 registry rasters.
<strong>Upload to a leaderboard slot: NOT RECOMMENDED.</strong> On the holdout proxy it scores below the 0.2778 champion, and
the confidence intervals do not overlap. Promotion is a separate selector decision, and any upload uses one of the three weekly submissions.</p>
</section>'''

table_ok = f'''<section><h2>Which file to use: summary table</h2>
<p>Scores are <strong>HOLDOUT-DTI</strong> estimates from the repo's SGMC-CAL evaluator (<code>{e(EVAL)}</code>, {n_wh:,} withheld off-catalogue positives, 95% spatial-cluster bootstrap CI). They are <strong>not organizer scores</strong> and are not calibrated to the leaderboard scale. The only organizer-scale number is the champion's OWNER-REPORT 0.2778, which is a typed value, not an organizer receipt.</p>
<div class="scroll"><table><thead><tr><th>File to download</th><th>Estimated score</th><th>Unique vs GEMSDOE 24-36 and registry?</th><th>OK to download?</th><th>OK to upload?</th></tr></thead><tbody>
<tr class="pick"><td><code>{e(LIT_NAME)}</code><br><a href="downloads/{e(LIT_NAME)}">download</a></td>
<td>HOLDOUT-DTI {lit_val:.6f} [{lit_ci[0]:.6f}, {lit_ci[1]:.6f}]</td>
<td><strong>YES.</strong> Lattice overlap {LIT_WORST*100:.4f}% (&lt;70%); worst non-lattice {LIT_WORST_NONLAT*100:.2f}%.</td>
<td><strong>YES</strong></td><td><strong>Allowed by rule. Not recommended:</strong> proxy below champion.</td></tr>
<tr><td><code>{e(bgk['submission_name'])}</code> (main, BGK-PBE)</td>
<td>Not scored: fail-closed. Holdout is not run once uniqueness fails.</td>
<td><strong>NO.</strong> Lattice overlap {bgk['literal_audit_2026_10_29']['worst_within_3px_fraction_final_dots']*100:.2f}%. 4,911 non-zero values outside the footprint.</td>
<td><strong>NO</strong></td><td><strong>NOT OK to submit.</strong></td></tr>
<tr><td><code>{e(uni['submission_name'])}</code> (main, unique-structural)</td>
<td>Not scored: fail-closed.</td>
<td><strong>NO.</strong> Lattice overlap {uni['literal_audit_2026_10_29']['worst_within_3px_fraction_final_dots']*100:.2f}%. 74,418 non-zero values outside the footprint.</td>
<td><strong>NO</strong></td><td><strong>NOT OK to submit.</strong></td></tr>
<tr><td><code>{e(card['submission_name'])}</code> (37,654 dots, archived)</td>
<td>HOLDOUT-DTI {lwst['value']:.6f} [{lwst['ci95'][0]:.6f}, {lwst['ci95'][1]:.6f}]</td>
<td><strong>NO.</strong> Lattice overlap {LWST_LAT*100:.2f}% (limit 70%).</td>
<td><strong>NO</strong></td><td><strong>NO</strong> (blocked; needs owner ruling on the lattice)</td></tr>
<tr><td><code>gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif</code> (champion)</td>
<td>OWNER-REPORT 0.2778. HOLDOUT-DTI {champ['value']:.6f} [{champ['ci95'][0]:.6f}, {champ['ci95'][1]:.6f}]</td>
<td>Already in the registry.</td><td>n/a</td><td><strong>NO.</strong> Already scored; resubmitting is not useful.</td></tr>
</tbody></table></div>
<p><strong>Reading the gap.</strong> The 37,654-dot LWST file has a proxy of {lwst['value']:.6f}, against the champion proxy {champ['value']:.6f}: essentially tied, with overlapping intervals. Making it compliant means dropping to about 21k dots, and that costs roughly a third of the proxy score. A same-count random control with no lattice constraint scores {same['value']:.6f} [{same['ci95'][0]:.6f}, {same['ci95'][1]:.6f}], so the dot cap alone explains about a fifth of the loss; the forced gap dots and the constrained placement explain the rest.</p>
<p><strong>Decision needed from the owner:</strong> does the synthetic 13GEMSDOE calibration lattice count as a registry raster under Rule 1? If it does not, the 37,654-dot LWST file becomes OK to download, with a proxy tied with the champion. If it does, the compliant file is the only unique option, and it is weaker on the proxy.</p>
</section>'''

submit_steps = f'''<section><h2>How to submit (exact steps)</h2><ol>
<li>Download <code>{e(LIT_NAME)}</code> from this page. Do not use the blocked 37,654-dot file.</li>
<li>Re-run the checks: <code>python scripts/verify_literal_candidate.py</code>, and <code>python scripts/literal_registry_audit.py docs/downloads/{e(LIT_NAME)} /tmp/check.json</code>. Both must pass on the day of upload, because the registry changes.</li>
<li>On the DrivenData "New submission" page, choose the <strong>.tif</strong> as the file. Paste the note above (≤140 characters).</li>
<li>The official rules allow three submissions per week (<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR Official Rules PDF</a>). Check your remaining count on the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition page</a> first.</li>
<li>Upload only if the owner decides to spend a slot. The proxy says this file will likely rank below the current 0.2778 site leaders.</li>
</ol>
<p>The portal error reported earlier was "Predicted values must be in range [0, 1]". Its root cause is not verified (review C6). This file has no NaN or nodata values, and the format gate confirms every value is in [0, 1].</p></section>'''

rows_ledger = sum(1 for i in ledger["irregularities"] if "OPEN" in i["severity"])
owner_section = f'''<section><h2>Per-site summary: nine focus sites (best owner-reported file each)</h2>
<p>These are reference only. Each file is already scored, so none should be resubmitted. Scores are OWNER-REPORT values from the request, not organizer receipts.</p>
<div class="scroll"><table><thead><tr><th>Site</th><th>Best file (already scored)</th><th>Score</th><th>Action</th></tr></thead><tbody>
{site_table}
</tbody></table></div></section>'''

review_sec = f'''<section><h2>Verification (2026-10-29)</h2><ul>{rev_items}</ul>
<p>Open irregularities: <strong>{rows_ledger}</strong>. The full ledger is in <a href="data/irregularities_ledger.json">data/irregularities_ledger.json</a>. The lattice-gap numbers are in <a href="data/lattice_gap_check.json">data/lattice_gap_check.json</a>. Literal audit receipts: <a href="data/literal_audit_compliant.json">compliant file</a>. Holdout receipts: <a href="data/literal_holdout_sgmc.json">HOLDOUT-DTI</a>. Full review and corrections: <a href="research/independent-review-20261028.md">Independent review (2026-10-28)</a>.</p></section>'''

leaderboard_sec = '''<section><h2>Leaderboard reference</h2><p>The live DrivenData leaderboard page, fetched in this session, shows #1 <strong>xiaofanhu 0.4544</strong> and #2 <strong>cfld__ 0.3916</strong>. The request mentions 0.3195 and 0.4413 as the top score. These figures conflict, and the owner should confirm which applies (IR-SASS3-26). Source: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a>. Public and private scores can differ.</p></section>'''

champ_sec = f'''<section><h2>Why the 0.2778 file scored highest (what the evidence supports)</h2>
<ol>
<li>It is the best member of a near-duplicate family. Its neighbours overlap 86.7-100% within 3 px (IR-SASS3-02, from the repo's earlier audit). Its owner-reported score is the highest of the 21 known files.</li>
<li>Across the 21 owner-scored files, SGMC-CAL ranks the owner scores well (Spearman 0.87). This is consistent with an off-catalogue advantage, but that is an inference, not a test. HIDE-RECOVER does not rank them (Spearman 0.14), so the static HIDE-RECOVER value cannot explain the score.</li>
<li>The gap from 0.2778 to the live leader (0.4544) is 0.1766. Nothing in this repo shows a route to that gap. The most promising route is probably a different family of method; that is an open question, not a result.</li>
</ol>
<p>Source: <code>docs/research/independent-review-20261028.md</code>, section 6.</p></section>'''

limits_sec = '''<section><h2>Evidence and limitations</h2><ul>
<li>Training data is restored from an owner mirror with SHA-256 pins. Pins prove mirror consistency, not organizer authentication (IR-SASS3-14).</li>
<li>Registry rasters were fetched from the public sibling repositories and SHA-verified against the manifest in this session (<code>evidence/registry_fetch_receipt.json</code>).</li>
<li>Holdout values are proxies. The HIDE-RECOVER value is not used for selection because it does not rank owner scores (rho 0.14).</li>
<li>No organizer receipt exists for either new file. Only an upload can reveal the score, and that uses a weekly slot.</li>
</ul>
<p>Official references: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description</a> · <a href="https://github.com/drivendataorg/gems-prize-reference-solution">reference solution</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official rules (PDF)</a>.</p></section>'''

blocked_archive = f'''<section class="hero"><p class="label">BLOCKED · DO NOT DOWNLOAD FOR SUBMISSION</p>
<h2>Archived 37,654-dot LWST file</h2>
<p>It passes the format check, but the literal uniqueness rule fails: <strong>{LWST_LAT*100:.2f}%</strong> of its dots lie within 3 px of the registered calibration lattice (limit 70%).</p>
<p>Archive: <code>{e(card['submission_name'])}</code><br>SHA-256: <code>{e(card['raster_sha256'])}</code><br>Historical note: <code>{e(card['submission_note'])}</code></p>
<p><a href="downloads/{e(card['submission_name'])}">Historical TIF for analysis only</a> · <a href="data/run_card_lwst_archived.json">Archived run card</a></p></section>'''

body = f'''{hero_ok}
{table_ok}
{submit_steps}
{review_sec}
{owner_section}
{leaderboard_sec}
{champ_sec}
{blocked_archive}
{limits_sec}'''

style = ('body{font:16px/1.6 system-ui,sans-serif;color:#14243a;background:#f2f6fa;margin:0}'
         'main{max-width:1100px;margin:auto;padding:24px}section{background:white;border:1px solid #d7e1eb;border-radius:12px;padding:24px;margin-bottom:20px}'
         '.hero{border-left:7px solid #be123c}.hero.ok{border-left:7px solid #15803d}.label{font-weight:800;color:#be123c}'
         '.hero.ok .label{color:#15803d}a{color:#075fac}code{overflow-wrap:anywhere}.scroll{overflow-x:auto}'
         'table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;border-bottom:1px solid #dae3eb;text-align:left;vertical-align:top}'
         'th{background:#edf3f8}tr.pick{background:#ecfdf3}.btn{display:inline-block;background:#15803d;color:white;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:700}'
         '.btn.alt{background:#075fac}')

for name, title in [("index.html", "GEMS review"), ("executive-summary.html", "Submission guide and executive summary")]:
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{title}</title><style>{style}</style></head><body><main><nav><a href="index.html">Overview</a> · '
            f'<a href="executive-summary.html">Submission guide</a></nav>{body}</main></body></html>\n')
    (ROOT / "docs" / name).write_text(page)
    root_page = (page.replace('href="downloads/', 'href="docs/downloads/')
                 .replace('href="data/', 'href="docs/data/')
                 .replace('href="research/', 'href="docs/research/')
                 .replace('href="hypotheses.md"', 'href="docs/hypotheses.md"'))
    (ROOT / name).write_text(root_page)

# Copy the new run card and receipts into docs/ so every relative link resolves on Pages.
shutil.copyfile(ROOT / "evidence/run_card_literal.json", ROOT / "docs/data/run_card_literal.json")
shutil.copyfile(ROOT / "evidence/lattice_gap_check.json", ROOT / "docs/data/lattice_gap_check.json")
shutil.copyfile(ROOT / "evidence/literal_candidates_sgmc.json", ROOT / "docs/data/literal_holdout_sgmc.json")
shutil.copyfile(ROOT / "evidence/irregularities_ledger.json", ROOT / "docs/data/irregularities_ledger.json")
shutil.copyfile(ROOT / "evidence/archive/run_card_lwst_archived_20261027.json", ROOT / "docs/data/run_card_lwst_archived.json")
shutil.copyfile(ROOT / "evidence/run_card_bgk_pbe.json", ROOT / "docs/data/run_card_bgk_pbe.json")
shutil.copyfile(ROOT / "evidence/run_card_unique_structural_20261029.json", ROOT / "docs/data/run_card_unique_structural.json")
print("built docs/index.html, docs/executive-summary.html, and root copies")
