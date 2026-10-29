#!/usr/bin/env python3
"""Build conservative GitHub Pages summaries from the current fail-closed run card."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "evidence/current_run_card.json").read_text())
SITES = [
    ("GEMSDOE24", "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", "0.2477"),
    ("GEMSDOE25", "dotted-h19-5-d2-8-20261002-e56ea318af89-nan", "0.2600"),
    ("GEMSDOE27", "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", "0.2449"),
    ("GEMSDOE28", "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", "0.2710"),
    ("GEMSDOE30", "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", "0.2600"),
    ("GEMSDOE31", "h27-4-solo-d28-20261004-8acb75e1-nan", "0.2708"),
    ("GEMSDOE32", "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", "0.2778"),
    ("GEMSDOE33", "h33d-analog-tip-stepover-r30-20261004-cb490425926e", "0.2632"),
    ("GEMSDOE36", "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", "0.2750"),
]

def e(x: object) -> str:
    return html.escape(str(x), quote=True)

STYLE = """
:root{color-scheme:dark;--bg:#0b1220;--panel:#111c2e;--panel2:#17253a;--line:#2b3a50;--text:#edf4fc;--muted:#aec0d4;--red:#fb7185;--amber:#fbbf24;--blue:#7dd3fc}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:1180px;margin:auto;padding:24px}nav{padding:12px 0 20px}a{color:var(--blue)}section{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px;margin:0 0 18px}.hero{border:2px solid var(--red);background:linear-gradient(135deg,#321b2b,var(--panel) 55%)}.warning{display:inline-block;color:#18040a;background:var(--red);font-weight:900;padding:5px 11px;border-radius:5px}h1{font-size:clamp(1.8rem,4vw,2.7rem);line-height:1.15;margin:.55rem 0}h2{margin-top:0}p,li{color:var(--muted)}strong{color:var(--text)}code{overflow-wrap:anywhere;background:#09101b;padding:2px 5px;border-radius:4px}.download{display:inline-block;background:#5b2333;color:#fff;font-weight:800;padding:11px 16px;border:1px solid var(--red);border-radius:8px;text-decoration:none}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:760px;font-size:.9rem}th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid var(--line)}th{background:var(--panel2)}.muted{color:var(--muted)}.small{font-size:.88rem}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}.tile{background:var(--panel2);border-radius:9px;padding:14px}
"""

site_rows = []
for site, filename, score in SITES:
    url = f"https://buffedlizard55-lab.github.io/{site}/"
    site_rows.append(
        f"<tr><td><a href='{e(url)}'>{e(site)}</a></td><td><code>{e(filename)}</code></td>"
        f"<td>OWNER-REPORT {e(score)} (historical; not a prediction)</td>"
        "<td>No — already submitted; do not reuse</td></tr>"
    )

candidate = CARD["submission_name"] + ".tif"
archive_path = CARD["download_path"].removeprefix("docs/")
run_card_path = "data/current_run_card.json"
review_path = "research/repo-review-20261029.md"

common = f"""
<section class="hero">
<span class="warning">SUBMISSION BLOCKED · NO APPROVED FILE · DO NOT SUBMIT</span>
<h1>GEMS fault-map review &amp; submission status</h1>
<p><strong>Executive decision:</strong> no available file has both a supported holdout result and a complete uniqueness clearance. The candidate link below is explicitly archive-only.</p>
<p><a class="download" href="{e(archive_path)}">Download archive-only diagnostic TIF — NOT approved</a></p>
<p><strong>Filename:</strong> <code>{e(candidate)}</code><br><strong>Estimated competition score:</strong> NOT ESTIMABLE (no candidate HOLDOUT-DTI and no organizer receipt).<br><strong>Unique against the complete registry?</strong> NOT CLEARED.<br><strong>Verdict:</strong> negative / archive only.</p>
<p class="small">SHA-256 <code>{e(CARD['raster_sha256'])}</code> · {e(CARD['submission_note'])}</p>
</section>
<section><h2>Why it is not approved</h2><ul>
<li>Local raster inspection: one-band float32, EPSG:32611, 3730×3292, recorded transform, all cells finite and values in [0,1]. The official <code>sample_submission.tif</code> is absent, so the transform is compared to the checked-in manifest, not the organizer sample.</li>
<li>The current BGK-PBE raster is synthetic: its footprint is an approximate ellipse and its gravity/K/dilatation fields are placeholders, not official competition or USGS measurements. It has 6,178 hard cells (>0.5) and 8,794 positive cells (>0).</li>
<li>HOLDOUT-DTI and candidate-specific leakage canary: NOT RUN; feature stack and labels are not present.</li>
<li>Against one pinned calibration lattice, 3,905/8,794 = 44.4053% of positive cells (2,687/6,178 = 43.4930% of hard cells) are within 3 px. This does not cover the other registry rasters or clear uniqueness. No official footprint or complete pre-placement check is available.</li>
</ul><p>Archive only. The complete machine-readable card is <a href="{e(run_card_path)}">current_run_card.json</a>; one-witness measurement: <a href="data/uniqueness_audit_current_candidate_20261029.json">audit JSON</a>.</p></section>
<section><h2>Nine-site executive summary</h2><p>The scores below are OWNER-REPORT / supplied historical results, not independently verified organizer receipts and not score estimates for this candidate. Each historical file has already been submitted; none is recommended for reuse. There is no current file eligible to submit.</p>
<div class="table-wrap"><table><thead><tr><th>Site</th><th>Highest historical file reported</th><th>Reported result</th><th>Unique / eligible to submit now?</th></tr></thead><tbody>{''.join(site_rows)}</tbody></table></div>
<p><strong>Highest focus-site report:</strong> GEMSDOE32 h33-h33-2-b2 at OWNER-REPORT 0.2778. The repository describes it as related to the D2.8/H19-5 family with a catalogue collar removed. That could plausibly help uncatalogued-target scoring, but outcome data alone does not prove the mechanism. No supported estimate shows the new candidate exceeds 0.2778.</p></section>
<section><h2>Independent review (2026-10-28)</h2><p>This is a historical review of the prior LWST file, not approval of the current diagnostic. It withdrew earlier score claims and found a literal lattice-overlap failure. See <a href="research/independent-review-20261028.md">the archived independent review</a>; its measurements must not be applied to the current candidate.</p></section>
<section><h2>Score and leaderboard caveats</h2><p>The request gives conflicting leaderboard snapshots (0.3195 and 0.4413); older checked-in evidence reported a public leaderboard value of 0.4544 as of 2026-10-27. The live board was not independently refreshed in this review, so none is presented as today's confirmed top score. Public/private leaderboard differences may also apply.</p><p>Do not convert HOLDOUT-DTI into a projected leaderboard score. No score number exists for the archive-only candidate.</p></section>
<section><h2>How to submit a future approved candidate</h2><ol><li>Only use a file whose current run card and page explicitly say <strong>OK TO SUBMIT</strong>; this archive candidate does not.</li><li>Verify the single-band GeoTIFF against the official sample for CRS, dimensions, and geotransform; enforce finite predictions in [0,1].</li><li>Check leakage canaries, buffered hide-and-recover HOLDOUT-DTI with evaluator/count/CI, and surface plus final-dot uniqueness against the complete accessible registry.</li><li>After a separate selector promotes it, open DrivenData &gt; New submission, select the GeoTIFF (or zip containing exactly one GeoTIFF), and enter the name/comment from the run card. Check the current weekly cap and disclose AI use if required by the rules.</li></ol><p>See the <a href="executive-summary.html">submission guide</a> and <a href="{e(review_path)}">repository review and next steps</a>.</p></section>
<section><h2>Auditable references</h2><ul><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition rules and submission page</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">Competition data (login may be required)</a></li><li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference solution</a></li><li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules PDF</a></li><li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a></li><li><a href="https://gbcge.org/current-projects/ingenious/">INGENIOUS Great Basin project</a></li><li><a href="https://epsg.io/32611">EPSG:32611</a></li></ul><p>Historical research queue: <a href="hypotheses.md">hypotheses</a> · <a href="irregularities.md">irregularities</a> · <a href="{e(review_path)}">review memo</a>.</p></section>
"""


def render(title: str, root: bool = False) -> str:
    body = common
    if root:
        body = body.replace('href="downloads/', 'href="docs/downloads/')
        body = body.replace('href="data/', 'href="docs/data/')
        body = body.replace('href="../evidence/', 'href="evidence/')
        body = body.replace('href="research/', 'href="docs/research/')
        body = body.replace('href="hypotheses.md"', 'href="docs/hypotheses.md"')
        body = body.replace('href="irregularities.md"', 'href="docs/irregularities.md"')
        body = body.replace('href="executive-summary.html"', 'href="docs/executive-summary.html"')
        base = "docs/"
    else:
        base = ""
    nav = f'<nav><strong>GEMSDOESASS3</strong> · <a href="{base}index.html">Overview</a> · <a href="{base}executive-summary.html">Submission guide</a></nav>'
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Fail-closed GEMS submission review"><title>{e(title)}</title><style>{STYLE}</style></head><body><main>{nav}{body}</main></body></html>\n'


def main() -> None:
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs/index.html").write_text(render("GEMS review"), encoding="utf-8")
    (ROOT / "docs/executive-summary.html").write_text(render("Submission guide and executive summary"), encoding="utf-8")
    (ROOT / "index.html").write_text(render("GEMS review", root=True), encoding="utf-8")
    (ROOT / "executive-summary.html").write_text(render("Submission guide and executive summary", root=True), encoding="utf-8")

if __name__ == "__main__":
    main()
