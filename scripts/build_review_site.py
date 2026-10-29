#!/usr/bin/env python3
"""Build the public review pages from archived evidence with explicit provenance labels."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "evidence/current_run_card.json").read_text())
AUDIT = json.loads((ROOT / "evidence/nine_sites_executive_audit.json").read_text())
REVIEW = json.loads((ROOT / "evidence/independent_review_20261028.json").read_text())
ESC = html.escape


def fmt_num(value: object, digits: int = 4) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else "not available"


def fmt_pct(value: object) -> str:
    return f"{value * 100:.2f}%" if isinstance(value, (int, float)) else "not available"


def ci_text(value: object, digits: int = 6) -> str:
    if not isinstance(value, list) or len(value) != 2:
        return "CI unavailable"
    return f"[{value[0]:.{digits}f}, {value[1]:.{digits}f}]"


rows_by_site = {row["site"]: row for row in REVIEW.get("per_site_table", [])}
rows = []
for site_record in AUDIT.get("sites", []):
    site = site_record["site"]
    hist = site_record.get("historical_best", {})
    row = rows_by_site.get(site, {})
    hold = row.get("holdout_dti", {})
    proj = row.get("model_projection_not_score", {})
    proj_value = proj.get("projected_dti")
    band = proj.get("loo_mae_band")
    projection = (
        f"LLI-v1-S0 {fmt_num(proj_value, 6)}; LOO-MAE band {ci_text(band, 4)} (NOT a score/CI)"
        if isinstance(proj_value, (int, float)) and isinstance(band, list)
        else "Not available"
    )
    holdout = (
        f"HOLDOUT-DTI {fmt_num(hold.get('dti'), 6)} {ci_text(hold.get('ci95'))}; "
        f"{ESC(str(hold.get('evaluator_version', 'evaluator not recorded')))}, "
        f"n={hold.get('withheld_positive_pixels', 'not recorded')}"
        if isinstance(hold.get("dti"), (int, float))
        else "Not available"
    )
    owner_score = row.get("owner_reported_score", site_record.get("hist_score_owner_report"))
    owner = f"OWNER-REPORT {fmt_num(owner_score)}; no submission receipt in this checkout"
    overlap = hist.get("max_3px_overlap_vs_other_8_hist")
    peer = hist.get("nearest_peer_site") or "peer not recorded"
    pairwise = (
        f"{fmt_pct(overlap)} vs {ESC(str(peer))}; archived leader-to-leader comparison only"
        if isinstance(overlap, (int, float))
        else "Not available"
    )
    candidate_overlap = row.get("archived_lwst_overlap_vs_this_file")
    lwst_overlap = (
        f"{fmt_pct(candidate_overlap)} of archived LWST dots within 3 px (directional, archived)"
        if isinstance(candidate_overlap, (int, float))
        else "Not available"
    )
    rows.append(
        "<tr>"
        f"<th scope='row'><a href='{ESC(site_record.get('site_url', '#'), quote=True)}'>{ESC(site)}</a></th>"
        f"<td><code>{ESC(str(site_record.get('hist_name', 'not recorded')))}</code></td>"
        f"<td>{ESC(owner)}</td>"
        "<td>None found</td>"
        f"<td>{ESC(projection)}</td>"
        f"<td>{holdout}</td>"
        f"<td>{pairwise}</td>"
        f"<td>{ESC(lwst_overlap)}</td>"
        "</tr>"
    )

lat = REVIEW.get("lattice_gate_literal", {})
uq = REVIEW.get("uniqueness_gate", {})
lat_fraction = lat.get("within3_frac")
lat_freshness = "recomputed from local witness" if lat.get("recomputed_this_run") else "archived measurement; witness unavailable for fresh recheck"
archived_lattice = fmt_pct(lat_fraction)
archived_downloads = int(uq.get("n_submitted_rasters_compared") or 0)
archived_dot_overlap = fmt_pct(uq.get("max_within3_frac"))
archived_rho = fmt_num(uq.get("max_abs_spearman_sampled"), 3)

submission_path_docs = f"downloads/{CARD['submission_name']}"
submission_path_root = f"docs/downloads/{CARD['submission_name']}"
card_path_docs = "data/current_run_card.json"
card_path_root = "docs/data/current_run_card.json"
review_path_docs = "research/independent-review-20261028.md"
review_path_root = "docs/research/independent-review-20261028.md"

hero = f"""
<section class="hero" aria-labelledby="page-title">
  <p class="eyebrow">SUBMISSION STATUS · BLOCKED</p>
  <h1 id="page-title">Do not submit the archived LWST GeoTIFF</h1>
  <p class="lead">It may be downloaded for analysis, but it is <strong>not cleared for upload</strong>. The archived lattice comparison reports <strong>{ESC(archived_lattice)} of its dots within 3 pixels</strong> of the calibration witness, above the 70% limit. That witness is absent from this checkout, so the old result is not represented as freshly recomputed. The current full-registry check fails closed.</p>
  <p class="actions"><a class="button" href="{{DOWNLOAD_PATH}}">Download archive for analysis only</a> <a class="button secondary" href="executive-summary.html">Submission guide</a> <a class="button secondary" href="{{CARD_PATH}}">Run card JSON</a></p>
  <dl class="artifact-meta">
    <div><dt>Archived file name</dt><dd><code>{ESC(CARD['submission_name'])}</code></dd></div>
    <div><dt>SHA-256</dt><dd><code>{ESC(str(CARD['raster_sha256']))}</code></dd></div>
    <div><dt>Archive note ({len(CARD['submission_note'])}/140 chars)</dt><dd>{ESC(CARD['submission_note'])}</dd></div>
  </dl>
  <p><strong>No new unique candidate was created.</strong> Renaming or repackaging this file cannot clear the uniqueness rule. Required data, the official sample, and a complete current registry are absent; the method lane is unresolved and the prior lane budget is exhausted.</p>
</section>
"""

review_section = f"""
<section aria-labelledby="gate-title">
  <h2 id="gate-title">Gate status and evidence freshness</h2>
  <div class="callout danger"><strong>Upload: NO.</strong> Download for research/archive use: YES. The archived file is not eligible for a submission slot.</div>
  <div class="table-scroll"><table>
    <thead><tr><th>Gate</th><th>Status</th><th>Evidence</th></tr></thead>
    <tbody>
      <tr><th scope="row">Local GeoTIFF format/range</th><td>{'PASS' if REVIEW['format_gate']['all_pass'] else 'FAIL'}</td><td>Fresh local check: single-band float32, EPSG:32611, 3730 × 3292, recorded transform, finite [0,1] values, 37,654 positive pixels. Official sample comparison available: <strong>{str(REVIEW['format_gate'].get('organizer_sample_comparison_available', False)).lower()}</strong>.</td></tr>
      <tr><th scope="row">Historical download subset</th><td>ARCHIVED ONLY</td><td>{archived_downloads} submitted downloads; max within-3-pixel overlap {ESC(archived_dot_overlap)}; max sampled |Spearman| {ESC(archived_rho)}. Archived subset-only pass={str(uq.get('archived_pass')).lower()}; this is not a current full-registry clearance.</td></tr>
      <tr><th scope="row">Literal rule including lattice</th><td>FAIL CLOSED</td><td>{ESC(archived_lattice)} within 3 px vs 70% limit; {ESC(lat_freshness)}.</td></tr>
      <tr><th scope="row">Current surface and final-dot checks</th><td>NOT VERIFIED</td><td>Current sibling registry rasters are absent. The prior surface and dot measurements remain archived only; no promotion is allowed.</td></tr>
    </tbody>
  </table></div>
  <p>The archived coverage calculation says only 5,379 footprint pixels lie outside the 3-pixel lattice buffer, while 11,297 dots would need to lie outside that buffer to keep overlap at or below 70%. This supports the prior conclusion that this dot count cannot pass under the literal rule. It is a historical calculation, not a fresh measurement in this checkout.</p>
  <p><a href="{review_path_docs}">Read the full independent review, per-site table, corrections, ranked hypotheses, and final run card</a>.</p>
</section>
"""

per_site_section = f"""
<section aria-labelledby="sites-title">
  <h2 id="sites-title">Executive summary: nine historical leaders</h2>
  <p>The OWNER-REPORT column records site-reported values; no per-file organizer receipt is present. HOLDOUT-DTI is an archived local proxy evaluation, not a leaderboard score. LLI-v1-S0 is a model projection, not a score; its LOO-MAE band is not a confidence interval. Pairwise uniqueness compares each historical leader with the other eight historical leaders only.</p>
  <div class="table-scroll"><table>
    <thead><tr><th>Site</th><th>Historical file</th><th>OWNER-REPORT</th><th>ORGANIZER-CONFIRMED</th><th>LLI-v1-S0 projection (not score)</th><th>HOLDOUT-DTI proxy</th><th>Max overlap vs other 8 historic leaders</th><th>Archived LWST overlap</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
  <p>All nine archived leader-to-leader maximum overlaps exceed 70%. These figures do not establish uniqueness against the complete registry. The archived LWST overlaps in the last column are directional: fraction of the candidate's dots within 3 pixels of that historical file.</p>
  <p>For the archived LWST file, the static HIDE-RECOVER proxy is HOLDOUT-DTI 0.006130 [0.005175, 0.007123] (GEMSDOE32-HIDE-RECOVER-v3.0; 22,232 withheld positives, B_visible=2 px). Its SGMC-CAL proxy is HOLDOUT-DTI 0.065702 [0.058992, 0.071240] (GEMSDOE32-SGMC-CAL-v3.0; 62,703 withheld positives). These historical results were not rerun here. The earlier 0.111062 claim is withdrawn as the static file score; it was an OOF/per-fold result. The prompt's 0.4413 and 0.4544 leaderboard-top figures conflict and are not treated as current verified benchmarks.</p>
</section>
"""

instructions = f"""
<section aria-labelledby="instructions-title">
  <h2 id="instructions-title">How to submit a future candidate</h2>
  <p><strong>These are conditional instructions, not approval to upload the linked archive.</strong></p>
  <ol>
    <li>Resolve the assigned method lane and confirm the applicable experiment/time budget before implementation.</li>
    <li>Use the shared <code>vendor/gems57</code> evaluator and writer. Validate using whole-segment spatial hide-and-recover with a buffer; run single-feature leakage canaries and report the evaluator, withheld-positive count, and 95% confidence interval.</li>
    <li>Compare both the pre-placement surface and final dots against every in-scope registry raster. Fail closed if the registry is incomplete or any rank-correlation / 3-pixel overlap threshold is exceeded.</li>
    <li>Validate the actual GeoTIFF against the official sample grid (CRS, shape, transform, dtype, finite values in [0,1]); use a unique filename and a truthful note of at most 140 characters.</li>
    <li>Only a separate selector may decide whether to use a weekly slot. Confirm the current cap and upload workflow on the organizer's submission page. Do not upload this archived candidate.</li>
  </ol>
</section>
"""

sources = """
<section aria-labelledby="sources-title">
  <h2 id="sources-title">Official sources and limitations</h2>
  <ul>
    <li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">GEMS Prize Official Rules (PDF)</a> — cited in archived work; not fetched again during this review edit.</li>
    <li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Competition problem page</a> and <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">official data page</a> — not checked in this review; local data cache is absent.</li>
    <li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official leaderboard</a> — not checked in this review; conflicting prompt values are not presented as current confirmed scores.</li>
    <li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a> — named as a possible official source for future hypotheses; coverage and download availability were not verified.</li>
    <li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">DrivenData reference solution</a> — cited for evaluator conventions; the shared <code>vendor/gems57</code> tools are retained.</li>
    <li><a href="research/review-20261028.md">Prior review and evidence ledger</a> — includes the pinned lattice-witness source and records why the uniqueness gate was blocked.</li>
  </ul>
  <p>Current raw features, the official sample raster, and local sibling checkouts are absent. Historical results are not current revalidation. No organizer receipt for the reviewed file is present. Use the data/source links above for manual provenance review; do not infer availability from a URL alone.</p>
</section>
"""

style = """
:root{color-scheme:light;--ink:#14243a;--muted:#53657a;--paper:#f2f6fa;--card:#fff;--line:#d6e0ea;--accent:#146c94;--danger:#b4233d;--danger-bg:#fff0f2;--good:#176b45}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}main{width:min(1240px,100%);margin:auto;padding:20px}nav{padding:4px 4px 18px;color:var(--muted)}nav a{margin-right:10px}a{color:#075fac;text-underline-offset:2px}a:hover{text-decoration-thickness:2px}section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:24px;margin:0 0 18px;box-shadow:0 4px 16px #17324d0a}h1{font-size:clamp(2rem,4vw,3.15rem);line-height:1.1;margin:.2em 0 .45em}h2{font-size:1.45rem;margin:0 0 .6em}.hero{border-top:6px solid var(--danger)}.eyebrow{font-weight:850;letter-spacing:.08em;color:var(--danger);margin:0}.lead{font-size:1.16rem}.actions{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}.button{display:inline-block;background:#075fac;color:white;text-decoration:none;border-radius:8px;padding:10px 15px;font-weight:700}.button.secondary{background:#e9f1f7;color:#13486e}.artifact-meta{display:grid;grid-template-columns:1fr;gap:8px}.artifact-meta div{display:grid;grid-template-columns:minmax(180px,240px) 1fr;gap:8px}.artifact-meta dt{font-weight:700;color:var(--muted)}.artifact-meta dd{margin:0;overflow-wrap:anywhere}.callout{padding:12px 14px;border-radius:8px;margin:12px 0}.danger{background:var(--danger-bg);border-left:4px solid var(--danger)}.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:1000px;font-size:.91rem}th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}thead th{background:#eaf1f6}tbody th{font-weight:750;white-space:nowrap}code{font: .9em ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}ol,ul{padding-left:1.35rem}li{margin:.45em 0}.small{color:var(--muted);font-size:.9rem}footer{padding:8px 4px 30px;color:var(--muted)}@media(min-width:800px){.artifact-meta{grid-template-columns:1fr 1fr}.artifact-meta div:first-child{grid-column:1/-1}}
"""

for subdir, download_path, card_path, review_path, title in [
    (ROOT / "docs", submission_path_docs, card_path_docs, review_path_docs, "GEMSDOESASS3 review"),
    (ROOT, submission_path_root, card_path_root, review_path_root, "GEMSDOESASS3 review"),
]:
    nav = '<nav aria-label="Main navigation"><a href="index.html">Overview</a><a href="executive-summary.html">Submission guide</a></nav>'
    page_content = (
        hero.replace("{DOWNLOAD_PATH}", ESC(download_path)).replace("{CARD_PATH}", ESC(card_path))
        + review_section.replace(review_path_docs, ESC(review_path))
        + per_site_section
        + instructions
        + sources.replace("research/review-20261028.md", ESC("research/review-20261028.md" if subdir.name == "docs" else "docs/research/review-20261028.md"))
    )
    if subdir.name == "docs":
        index_page = page_content
        guide_page = hero.replace("{DOWNLOAD_PATH}", ESC(download_path)).replace("{CARD_PATH}", ESC(card_path)) + instructions + review_section.replace(review_path_docs, ESC(review_path)) + per_site_section + sources.replace("research/review-20261028.md", "research/review-20261028.md")
    else:
        index_page = page_content
        guide_page = hero.replace("{DOWNLOAD_PATH}", ESC(download_path)).replace("{CARD_PATH}", ESC(card_path)) + instructions + review_section.replace(review_path_docs, ESC(review_path)) + per_site_section + sources.replace("research/review-20261028.md", "docs/research/review-20261028.md")

    for filename, body in [("index.html", index_page), ("executive-summary.html", guide_page)]:
        title_text = "Overview" if filename == "index.html" else "Submission guide"
        html_page = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="description" content="Conservative competition submission review; archived candidate is blocked from upload.">'
            f'<title>{ESC(title_text)} · {ESC(title)}</title><style>{style}</style></head><body>'
            f'<main>{nav}{body}<footer>GEMSDOESASS3 · archived evidence review · no submission approval</footer></main></body></html>\n'
        )
        (subdir / filename).write_text(html_page, encoding="utf-8")

print(json.dumps({
    "pages_written": ["index.html", "executive-summary.html", "docs/index.html", "docs/executive-summary.html"],
    "submission_allowed": False,
    "archive_download_allowed": bool(CARD.get("ok_to_download")),
    "site_rows": len(rows),
    "lattice_overlap_archived": lat_fraction,
}, indent=2))
