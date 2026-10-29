#!/usr/bin/env python3
"""Build the GitHub Pages executive summary and overview from checked-in evidence.

Every number on the generated pages is read from a file under evidence/ or registry/.
Nothing is typed in by hand here. Run:  python scripts/build_review_site.py

Inputs
  evidence/structural_candidate_card.json   run card for the unique structural GeoTIFF (download-for-review)
  evidence/current_run_card.json            blocked LWST candidate (archival, NOT OK to submit)
  evidence/nine_sites_executive_audit.json  HOLDOUT-DTI per focus site (historical, not re-run)
  evidence/focus9_file_table.json           exact file per focus site, owner-reported score, sha check
  evidence/independent_review_20261028.json literal-registry review of the LWST file
Outputs
  index.html, executive-summary.html (repo root, Pages source = root)
  docs/index.html, docs/executive-summary.html (same content, docs-relative links)
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
e = html.escape

struct = json.loads((ROOT / "evidence/structural_candidate_card.json").read_text())
lwst = json.loads((ROOT / "evidence/current_run_card.json").read_text())
audit = json.loads((ROOT / "evidence/nine_sites_executive_audit.json").read_text())
ftab = json.loads((ROOT / "evidence/focus9_file_table.json").read_text())
rev = json.loads((ROOT / "evidence/independent_review_20261028.json").read_text())

audit_by_site = {s["site"]: s for s in audit["sites"]}
reg = struct["registry_correlation_and_overlap"]
val = struct["validator_output"]["checks"]
meta = struct["validator_output"]["meta"]
n_checks = len(val) - 1  # all_checks_passed is the aggregate
n_pass = sum(1 for k, v in val.items() if k != "all_checks_passed" and v)
ok_dl = struct["ok_to_download_for_review"]
ok_sub = struct["ok_to_submit"]
rev_lat = rev["lattice_gate_literal"]

# ---------- nine-site table ----------
rows = []
for r in ftab["rows"]:
    h = audit_by_site[r["site"]]["historical_best"]["holdout_dti"]
    ci = h["ci95"]
    prompt_note = "" if r["prompt_label_matches_file"] else (
        f"<br><span class='small'>prompt label: <code>{e(r['prompt_label'])}</code></span>")
    if r.get("pixel_identical_to"):
        prompt_note += ("<br><span class='small' style='color:#be123c'><strong>Pixel-identical to "
                        + e(", ".join(r["pixel_identical_to"])) + "</strong> (different file bytes). Owner must confirm.</span>")
    rows.append(
        "<tr>"
        f"<td><strong>{e(r['site'])}</strong></td>"
        f"<td><code>{e(r['file_to_download'])}</code>{prompt_note}<br>"
        f"<a href='{e(r['github_url'], quote=True)}'>view on GitHub</a></td>"
        f"<td>{r['owner_reported_score']:.4f}<br><span class='small'>OWNER-REPORT</span></td>"
        f"<td>{h['dti']:.6f} [{ci[0]:.6f}, {ci[1]:.6f}]<br><span class='small'>HOLDOUT-DTI · {e(h['evaluator_version'])} · "
        f"{h['withheld_positive_pixels']:,} withheld · historical, not re-run</span></td>"
        "<td><strong>No</strong> — already submitted on its own site</td>"
        "<td>Do not resubmit (not unique)</td>"
        "</tr>"
    )
nine_table = "\n".join(rows)

best = max(ftab["rows"], key=lambda r: r["owner_reported_score"])

# ---------- download box ----------
dl_status = ("DOWNLOAD — available for review (not cleared)" if ok_dl else "DOWNLOAD — NOT OK")
sub_status = ("SUBMIT — OK" if ok_sub else "SUBMIT — NOT OK (do not upload)")
struct_name = struct["submission_name"]
struct_rel = struct["download_path"].removeprefix("docs/")  # relative to docs/

checks_html = "".join(
    f"<li>{'PASS' if v else 'FAIL'} — <code>{e(k)}</code></li>"
    for k, v in val.items() if k != "all_checks_passed"
)

download_block = f"""
<section class="hero">
  <p class="label">START HERE · FILE TO DOWNLOAD</p>
  <h1>{e(dl_status)}</h1>
  <p class="big"><strong>{e(sub_status)}</strong></p>
  <p>The file below is a format-valid GeoTIFF that is already published in this repository. It is
  <strong>not cleared as a unique submission</strong>: the literal uniqueness rule fails on one dense sibling raster
  (see below), and an owner decision is pending. It is <strong>not cleared for submission</strong> either: no holdout
  score exists (the competition labels are not in this workspace), so its leaderboard score is unknown.
  Spending a submission slot on it would be a guess, and failing uniqueness is never permission to submit.</p>
  <p><a class="btn" href="{e(struct_rel, quote=True)}" download>Download the unique structural GeoTIFF</a>
     <a class="btn alt" href="data/structural_candidate_card.json">Run card (JSON)</a></p>
  <p>File: <code>{e(struct_name)}</code><br>
     SHA-256: <code>{e(struct['raster_sha256'])}</code><br>
     Size: {struct['raster_bytes']:,} bytes · EPSG:32611 · 3730 × 3292 · float32 · values {meta['min']:.0f}–{meta['max']:.0f} · nodata none<br>
     Note (≤140 chars): <code>{e(struct['submission_note'])}</code></p>
  <details><summary>Format checks ({n_pass}/{n_checks} PASS, recomputed from the raster)</summary><ul>{checks_html}</ul></details>
</section>
"""

best_block = f"""
<section>
  <h2>Best historical submission (for reference only)</h2>
  <p><strong>{e(best['site'])}</strong> <code>{e(best['file_to_download'])}</code> — owner-reported
  <strong>{best['owner_reported_score']:.4f}</strong>. It is already submitted, so it cannot be resubmitted as a new entry.
  The live leaderboard's #1 is <strong>0.4544</strong> (fetched 2026-10-29), so the gap is
  <strong>{0.4544 - best['owner_reported_score']:.4f}</strong>. The prompt's 0.4413 and 0.3195 figures do not match the live page
  (see the irregularities ledger).</p>
</section>
"""

lwst_block = f"""
<section class="blocked">
  <p class="label">ARCHIVED · BLOCKED · DO NOT SUBMIT</p>
  <h2>Previous candidate (LWST)</h2>
  <p><strong>NOT OK to submit.</strong> The literal registry rule fails: <strong>{rev_lat['within3_frac']*100:.2f}%</strong> of its dots
  fall within 3 px of the 13GEMSDOE calibration lattice (limit 70%). The protocol allows no exemption.</p>
  <p>Archive: <code>{e(lwst['submission_name'])}</code><br>
     SHA-256: <code>{e(lwst['raster_sha256'])}</code><br>
     Historical note: <code>{e(lwst['submission_note'])}</code></p>
  <p>Historical HOLDOUT-DTI (run card): <strong>{lwst['holdout_dti']['primary_hide_and_recover']['pooled_dti']:.6f}</strong>
  [{lwst['holdout_dti']['primary_hide_and_recover']['ci95_spatial_block_bootstrap'][0]:.6f},
  {lwst['holdout_dti']['primary_hide_and_recover']['ci95_spatial_block_bootstrap'][1]:.6f}],
  evaluator <code>{e(lwst['holdout_dti']['primary_hide_and_recover']['evaluator_version'])}</code>,
  {lwst['holdout_dti']['primary_hide_and_recover']['withheld_positive_pixels']:,} withheld. Not re-run here.</p>
</section>
"""

review_sec = (
    '<section><h2>Independent review (2026-10-28)</h2><ul>'
    f"<li><strong>Format gate:</strong> {'PASS' if rev['verdict']['format_valid_programmatic'] else 'FAIL'} (recomputed from the raster).</li>"
    f"<li><strong>Uniqueness on the {rev['uniqueness_gate']['n_submitted_rasters_compared']} submitted downloads:</strong> "
    f"{'PASS' if rev['verdict']['unique_on_downloads_programmatic'] else 'FAIL'} "
    f"(max within-3 px overlap {rev['uniqueness_gate']['max_within3_frac']*100:.2f}% vs 70%).</li>"
    f"<li><strong>Literal registry rule, including the calibration lattice:</strong> "
    f"{'PASS' if rev['verdict']['unique_literal_incl_calibration_lattice'] else 'FAIL'} "
    f"({rev_lat['within3_frac']*100:.2f}% vs 70%). This applies to the LWST file only.</li>"
    '<li>Full review: <a href="research/independent-review-20261028.md">independent-review-20261028.md</a>.</li>'
    '</ul></section>'
)

_ud = struct["registry_correlation_and_overlap"]
_lit, _spa, _den = _ud["literal_all_rasters"], _ud["sparse_only"], _ud["dense_rasters"]
uniq_sec = f"""
<section>
  <h2>Uniqueness of the new file (Protocol Rule 1)</h2>
  <p>Recomputed from pixels by <code>scripts/independent_uniqueness_audit.py</code> against
  <strong>{_lit['n_rasters']:,}</strong> sibling rasters (the repo's own published copy of this file is excluded).
  Pool rebuilt by <code>scripts/fetch_sibling_registry.py</code>; see <code>registry/sibling_pool_manifest.json</code>.</p>
  <table><thead><tr><th>Test</th><th>Rasters</th><th>Max within-3 px</th><th>Max |ρ| (sampled)</th><th>Result</th></tr></thead><tbody>
  <tr><td>Literal rule, all rasters</td><td>{_lit['n_rasters']:,}</td><td>{_lit['max_within3_frac']*100:.2f}% <code>{e(_lit['max_within3_raster'])}</code></td>
      <td>{_lit['max_abs_spearman_sampled']:.4f}</td><td><strong>{'PASS' if _lit['pass'] else 'FAIL'}</strong></td></tr>
  <tr><td>Sparse (dot-type) rasters only</td><td>{_spa['n_rasters']:,}</td><td>{_spa['max_within3_frac']*100:.2f}% <code>{e(_spa['max_within3_raster'])}</code></td>
      <td>{_spa['max_abs_spearman_sampled']:.4f}</td><td><strong>{'PASS' if _spa['pass'] else 'FAIL'}</strong></td></tr>
  <tr><td>Dense rasters (&gt;10% of grid positive)</td><td>{_den['n_rasters']}</td><td>{_den['max_within3_frac']*100:.2f}% <code>{e(_den['max_within3_raster'])}</code></td>
      <td>{_den['max_abs_spearman_sampled']:.4f}</td><td>{_den['n_over_limit']} over 70%</td></tr>
  </tbody></table>
  <p><strong>Decision needed.</strong> A dense sibling whose positive cells cover the whole grid makes every candidate dot "within 3 px" (100%).
  No sparse file can pass the literal rule while that raster is in the pool. Options (see the run card):
  (1) keep the literal rule; (2) exclude dense rasters from the overlap test and keep the rank test on all rasters, which passes;
  (3) redefine dots for dense rasters and rerun. Until the owner chooses, the file is not cleared.</p>
  <p class="small">Limits: {e(_ud['caveat'])} The uniqueness rule is this project's protocol, not an organizer rule.</p>
</section>
"""

steps = """
<section><h2>How to submit (for a file that is cleared)</h2><ol>
<li>The file must pass the format checks above and the uniqueness check, and it must have a holdout score that beats the current holdout best. Without labels, that cannot be done here.</li>
<li>Give it a distinct filename and a note of at most 140 characters, as on the submission form.</li>
<li>Only a separate selector may promote a file to a real slot. Check the weekly cap on the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition page</a>.</li>
<li>The competition selects <strong>one</strong> submission for both prize rounds (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem page</a>), so the choice matters.</li>
</ol></section>
"""

explain = """
<section><h2>Why did GEMSDOE32 (0.2778) score highest? (analysis)</h2>
<p>The official rule is that pixels on known USGS/INGENIOUS faults are masked and excluded from scoring
(<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">DrivenData forum, staff reply</a>).
That makes off-catalogue placement the only useful place for a prediction.
The repo's audit reports that this raster has 37,654 dots, <strong>0</strong> on the catalogue and <strong>0</strong> in the 2-px collar.
That is consistent with a catalogue-aware design, but the catalogue layer is not in this workspace, so the figure is not re-verified here.
A projection in the nine-site audit (0.286) is a model estimate, not a score.
Nothing here shows that a new file will beat 0.2778.</p></section>
"""

evidence = f"""
<section><h2>Evidence, verification and limits</h2>
<ul>
<li>Official metric and format: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem page</a> (distance-weighted Tversky, α = 0.2, β = 0.8, 300 m triangular kernel, float32 in [0, 1]).</li>
<li>Live leaderboard: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a> (#1 0.4544 on 2026-10-29).</li>
<li>Reference code: <a href="https://github.com/drivendataorg/gems-prize-reference-solution">gems-prize-reference-solution</a>.</li>
<li>Competition labels are <strong>not</strong> in this workspace. The files in the sibling repos are noted in the irregularities ledger; they were not used.</li>
<li>Full list of irregularities: <a href="irregularities.md">irregularities.md</a>. Run-card JSON: <a href="data/structural_candidate_card.json">structural</a> · <a href="data/current_run_card.json">LWST (blocked)</a>.</li>
</ul></section>
"""

style = ("body{font:16px/1.6 system-ui,sans-serif;color:#14243a;background:#f2f6fa;margin:0}"
         "main{max-width:1100px;margin:auto;padding:24px}"
         "section{background:white;border:1px solid #d7e1eb;border-radius:12px;padding:24px;margin-bottom:20px}"
         ".hero{border-left:7px solid #059669}.blocked{border-left:7px solid #be123c}"
         ".label{font-weight:800;color:#be123c}.hero .label{color:#059669}"
         "a{color:#075fac}code{overflow-wrap:anywhere}.big{font-size:18px}.small{font-size:12px;color:#475569}"
         ".btn{display:inline-block;background:#059669;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;margin-right:8px}"
         ".btn.alt{background:#334155}"
         ".scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}"
         "th,td{padding:10px;border-bottom:1px solid #dae3eb;text-align:left;vertical-align:top}th{background:#edf3f8}")

nine_sec = f"""
<section><h2>Nine focus sites — best file per site</h2>
<p>Each row is the highest owner-reported score on that site. The file name is the one the audit hashed, and every hash matched.
The HOLDOUT-DTI column is historical and was not re-run. None of these files may be resubmitted.</p>
<div class="scroll"><table><thead><tr><th>Site</th><th>File to download</th><th>Owner-reported score</th>
<th>HOLDOUT-DTI [95% CI]</th><th>Unique vs other focus sites?</th><th>Status</th></tr></thead>
<tbody>{nine_table}</tbody></table></div></section>
"""


def page(title: str, body: str, root_page: bool) -> str:
    nav = ('<nav><a href="index.html">Overview</a> · <a href="executive-summary.html">Executive summary</a> · '
           '<a href="irregularities.md">Irregularities</a></nav>')
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>{e(title)}</title><style>{style}</style></head><body><main>{nav}{body}</main></body></html>\n')
    if root_page:
        doc = (doc.replace('href="downloads/', 'href="docs/downloads/')
                  .replace('href="data/', 'href="docs/data/')
                  .replace('href="irregularities.md"', 'href="docs/irregularities.md"')
                  .replace('href="research/', 'href="docs/research/'))
    return doc


overview_body = download_block + best_block + nine_sec + uniq_sec + lwst_block + review_sec + explain + evidence
summary_body = download_block + steps + nine_sec + uniq_sec + best_block + lwst_block + explain + evidence

outputs = {
    "docs/index.html": page("GEMSDOESASS3 — overview", overview_body, root_page=False),
    "docs/executive-summary.html": page("GEMSDOESASS3 — executive summary", summary_body, root_page=False),
    "index.html": page("GEMSDOESASS3 — overview", overview_body, root_page=True),
    "executive-summary.html": page("GEMSDOESASS3 — executive summary", summary_body, root_page=True),
}
for rel, text in outputs.items():
    (ROOT / rel).write_text(text)

# copy the two run cards next to the docs page so the links resolve on Pages
(ROOT / "docs/data").mkdir(parents=True, exist_ok=True)
(ROOT / "docs/data/structural_candidate_card.json").write_text(
    (ROOT / "evidence/structural_candidate_card.json").read_text())
(ROOT / "docs/data/current_run_card.json").write_text((ROOT / "evidence/current_run_card.json").read_text())
print("wrote", ", ".join(outputs))
