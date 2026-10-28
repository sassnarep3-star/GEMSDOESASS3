#!/usr/bin/env python3
"""Build a conservative static review page from checked-in historical evidence."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
card = json.loads((ROOT / 'evidence/current_run_card.json').read_text())
audit = json.loads((ROOT / 'evidence/nine_sites_executive_audit.json').read_text())
e = html.escape
rev = json.loads((ROOT / 'evidence/independent_review_20261028.json').read_text())
_lat = rev['lattice_gate_literal']
_uq = rev['uniqueness_gate']
review_sec = (
    '<section><h2>Independent review (2026-10-28)</h2><ul>'
    f"<li><strong>Format gate:</strong> {'PASS' if rev['verdict']['format_valid_programmatic'] else 'FAIL'} (recomputed from the raster).</li>"
    f"<li><strong>Uniqueness on the {_uq['n_submitted_rasters_compared']} submitted downloads:</strong> {'PASS' if rev['verdict']['unique_on_downloads_programmatic'] else 'FAIL'} "
    f"(max within-3 px overlap {_uq['max_within3_frac']*100:.2f}% vs 70%).</li>"
    f"<li><strong>Literal registry rule, including the calibration lattice:</strong> {'PASS' if rev['verdict']['unique_literal_incl_calibration_lattice'] else 'FAIL'} "
    f"({_lat['within3_frac']*100:.2f}% vs 70%). <strong>Verdict: NOT OK to submit.</strong> At 37,654 dots no raster can meet this rule: only {_lat['coverage_analysis']['footprint_px_outside_3px_of_lattice']:,} footprint pixels lie outside the lattice buffer, and {_lat['coverage_analysis']['dots_needed_outside_3px_to_pass']:,} dots would be needed there. An owner decision on the calibration lattice is required.</li>"
    "<li><strong>Score claims:</strong> the earlier \"beats 0.2778\" claim is withdrawn; the 0.2778 and 0.4544 comparisons are not demonstrated (HOLDOUT-DTI CIs overlap).</li>"
    "<li>Full review, corrections, per-site table, ranked hypotheses and limitations: "
    "<a href=\"research/independent-review-20261028.md\">independent-review-20261028.md</a>.</li>"
    '</ul></section>'
)
rows = []
for site in audit['sites']:
    h = site['historical_best']['holdout_dti']
    ci = h['ci95']
    rows.append(f"<tr><td><a href='{e(site['site_url'], quote=True)}'>{e(site['site'])}</a></td>"
                f"<td><code>{e(site['hist_name'])}</code></td>"
                f"<td>{h['dti']:.6f} [{ci[0]:.6f}, {ci[1]:.6f}]</td>"
                f"<td>No — historical cross-site overlap exceeds the protocol threshold; already submitted.</td></tr>")
table = '\n'.join(rows)
body = f'''<section class="hero"><p class="label">SUBMISSION STATUS · BLOCKED</p>
<h1>Do not submit the current GeoTIFF</h1><p>Its pixels pass the local range check, but the literal uniqueness gate fails. A prior registry audit and an independent recheck found <strong>99.7849% of its dots within 3 pixels</strong> of the registered 13GEMSDOE lattice. The protocol allows at most 70%. No density exemption is allowed. This is not a claim that the files are byte-identical.</p>
<p><a href="{e(card['download_path'].removeprefix('docs/'), quote=True)}">Download historical TIF for analysis only</a> · <a href="data/current_run_card.json">Run card</a> · <a href="executive-summary.html">Submission instructions</a></p>
<p>Archive: <code>{e(card['submission_name'])}</code><br>SHA-256: <code>{e(card['raster_sha256'])}</code><br>Historical note: <code>{e(card['submission_note'])}</code></p></section>
{review_sec}
<section><h2>Executive summary: nine sites</h2><p>There is <strong>no eligible file to recommend</strong>. These are historical leaders identified in the repository audit, not suggestions to resubmit. Values are historical <strong>HOLDOUT-DTI</strong>, evaluator <code>gems57-pooled-hide-v2</code>, 22,893 withheld positives, with 95% intervals. They are not organizer scores or calibrated leaderboard estimates. Audit measurements were not rerun in this session.</p><div class="scroll"><table><thead><tr><th>Site</th><th>Historical file (not approved)</th><th>HOLDOUT-DTI [95% CI]</th><th>Unique against other focus sites?</th></tr></thead><tbody>{table}</tbody></table></div>
<p>For the former candidate, the historical run card reports HOLDOUT-DTI <strong>0.111062 [0.098423, 0.123755]</strong>, evaluator <code>GEMSDOE32-HIDE-RECOVER-v3.0</code>, 22,232 withheld positives. Its historical companion control is 0.099202 [0.085951, 0.112668] under the same evaluator. This does not predict a leaderboard score, and neither evaluation was reproduced here.</p></section>
<section><h2>What explains the GEMSDOE32 result?</h2><p>The user reports a 0.2778 result for h33-h33-2-b2, but an organizer receipt was not independently available; it is not organizer-confirmed here. The repository's historical set-algebra audit reports that this raster removes a two-pixel catalogue collar from the d2.8 dotted H19-5 family. This suggests a plausible combination of off-catalogue masking and spatial allocation matched the metric, not proof of the causal reason. Held-out positives and the organizer's hidden labels can differ. Nothing here establishes that a new submission exceeds that result or either conflicting leaderboard figure in the request.</p></section>
<section><h2>How to submit when a candidate passes</h2><ol><li>Run the complete, fold-honest evaluator and feature canaries; report version, withheld count and spatial-block confidence intervals. Beat the current holdout best without using a weekly slot.</li><li>Check surface rank correlation and final dot overlap against every accessible registry raster, with no exclusions; fail closed for incomplete coverage. Private or unlinked submissions cannot be ruled out.</li><li>Validate a single-band GeoTIFF against the official example: CRS, shape, transform and finite [0,1] values. Generate a distinct filename and short note.</li><li>Only a separate selector may promote a passing candidate. Check the actual weekly cap on the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition page</a>, then upload the file using New submission. The archive linked above does not qualify.</li></ol></section>
<section><h2>Evidence and limitations</h2><p>The current checkout has no cached feature stack, official template, full registry, or authenticated organizer receipts. Old restore receipts describe an earlier workspace, not files present now. No new experiment was run or submission slot used. The lattice witness was retrieved by pinned GitHub commit, its SHA-256 verified, and the 3-pixel overlap recomputed; see <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif">witness source</a>. Its hash is <code>b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2</code>.</p>
<p>Official references: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">data</a> · <a href="https://github.com/drivendataorg/gems-prize-reference-solution">reference solution</a> · <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a>. Access to these non-GitHub hosts was not verified in this sandbox.</p><p>The earlier <a href="hypotheses.md">hypothesis record</a> contains unverified quantitative projections and data-availability claims; treat it as a research proposal, not established results.</p></section>'''
style = '''body{font:16px/1.6 system-ui,sans-serif;color:#14243a;background:#f2f6fa;margin:0}main{max-width:1100px;margin:auto;padding:24px}section{background:white;border:1px solid #d7e1eb;border-radius:12px;padding:24px;margin-bottom:20px}.hero{border-left:7px solid #be123c}.label{font-weight:800;color:#be123c}a{color:#075fac}code{overflow-wrap:anywhere}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;border-bottom:1px solid #dae3eb;text-align:left;vertical-align:top}th{background:#edf3f8}'''
for name,title in [('index.html','GEMS review'),('executive-summary.html','Submission guide and executive summary')]:
    page=f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title><style>{style}</style></head><body><main><nav><a href="index.html">Overview</a> · <a href="executive-summary.html">Submission guide</a></nav>{body}</main></body></html>\n'
    (ROOT / 'docs' / name).write_text(page)
    # Root Pages uses a different base for artifacts.
    rootpage = page.replace('href="downloads/', 'href="docs/downloads/').replace('href="data/', 'href="docs/data/').replace('href="hypotheses.md"', 'href="docs/hypotheses.md"').replace('href="research/', 'href="docs/research/')
    (ROOT / name).write_text(rootpage)
