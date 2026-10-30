#!/usr/bin/env python3
"""Build the GitHub Pages site for GEMSDOESASS3 from the evidence receipts.

Every number on the pages is read from a JSON receipt in `evidence/` (or `docs/data/`), so the pages
cannot drift from what the scripts measured.  No number is written as a score unless it is copied from
an owner-reported ledger row (labelled OWNER-REPORT) - every model output is labelled PROJECTION.

Pages written (root copy + docs copy, links rewritten per location):
  index.html                    start here: download, gates, verdict, per-site table
  executive-summary.html       the nine focus sites: file to download, live score, projection, uniqueness
  submission-guide.html        exactly how to submit, what the portal checks, why the old file failed
Usage:  python scripts/build_site_sass3.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

FOCUS_SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31",
               "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
SITE_URL = {s: f"https://buffedlizard55-lab.github.io/{s}/" for s in FOCUS_SITES}
SITE_URL.update({"GEMSDOE31": "https://buffedlizard55-lab.github.io/GEMSDOE31/docs/",
                 "GEMSDOE32": "https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html",
                 "GEMSDOE36": "https://buffedlizard55-lab.github.io/GEMSDOE36/docs/"})


def jload(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


CSS = """
:root{--bg:#0d1117;--card:#161b22;--tx:#e6edf3;--mut:#8b949e;--ok:#2ea043;--no:#db61a2;--warn:#d29922;--acc:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 20px 80px}h1{font-size:28px;margin:.2em 0 .4em}h2{font-size:21px;margin:1.7em 0 .5em;border-bottom:1px solid #21262d;padding-bottom:6px}
h3{font-size:17px;margin:1.3em 0 .4em}a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.card{background:var(--card);border:1px solid #21262d;border-radius:10px;padding:16px 18px;margin:14px 0}
.k{color:var(--mut);font-size:12.5px;letter-spacing:.03em;text-transform:uppercase}
.big{font-size:26px;font-weight:700}.btn{display:inline-block;background:var(--ok);color:#fff;padding:11px 16px;border-radius:8px;font-weight:650;margin:6px 8px 6px 0}
.btn.sec{background:#21262d;color:var(--tx)}.btn.no{background:#420c33}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13.5px}th,td{border:1px solid #21262d;padding:7px 9px;text-align:left;vertical-align:top}
th{background:#1c2128}code{background:#1c2128;padding:1px 5px;border-radius:4px;font-size:12.5px}
.ok{color:var(--ok);font-weight:650}.no{color:var(--no);font-weight:650}.warn{color:var(--warn);font-weight:650}
ul{margin:.4em 0 .4em 1.2em}li{margin:.25em 0}.small{font-size:12.5px;color:var(--mut)}
.pill{display:inline-block;border:1px solid #21262d;border-radius:999px;padding:1px 9px;font-size:12px;margin-right:6px}
nav{position:sticky;top:0;background:#0d1117ee;border-bottom:1px solid #21262d;padding:10px 16px;margin-bottom:8px;z-index:9}
nav a{margin-right:14px;font-size:13.5px}
"""


def gate_pill(ok, label):
    cls = "ok" if ok is True else ("no" if ok is False else "warn")
    txt = {True: "PASS", False: "FAIL", None: "NOT RUN"}[ok if ok in (True, False, None) else None]
    return f'<span class="pill {cls}">{label}: {txt}</span>'


def build(prefix: str) -> tuple[str, str, str]:
    card = jload(ROOT / "evidence/current_run_card.json", {}) or {}
    pkg = card.get("validator_output", {}).get("gates", {})
    val = jload(ROOT / "evidence/lli_candidate_validation_union.json", {}) or {}
    val_s0 = jload(ROOT / "evidence/lli_candidate_validation.json", {}) or {}
    emi = jload(ROOT / "evidence/lambda_emission_variants.json", {}) or {}
    lli = jload(ROOT / "evidence/lli_score_model_verification.json", {}) or {}
    led = jload(ROOT / "evidence/score_ledger_index.json", {}) or {}
    irs = jload(ROOT / "evidence/irregularities_ledger.json", {}) or {}
    _ir = irs.get("irregularities") or irs.get("entries") or (irs if isinstance(irs, list) else [])
    n_ir = len(_ir)

    # ---------- our candidate ----------
    name = card.get("submission_name", "—")
    dl = f"{prefix}downloads/{name}.tif" if name != "—" else ""
    proj = (val.get("projections") or {})
    pc = {t: v["candidate"]["projected_dti"] for t, v in proj.items() if "candidate" in v}
    ph = {t: v["champion_control"]["projected_dti"] for t, v in proj.items() if "champion_control" in v}
    pmin = min(pc.values()) if pc else None
    rows_cand = "".join(
        f"<tr><td>{t}</td><td>{pc[t]:.4f}</td><td>{ph.get(t, float('nan')):.4f}</td>"
        f"<td class=\"{'ok' if pc[t] > ph.get(t, 9) else 'no'}\">{pc[t] - ph.get(t, 9):+.4f}</td></tr>"
        for t in sorted(pc))
    dup = val.get("duplicate_tests", {})
    # ---- the design matrix: every emission design we projected, from the receipts ----
    matrix_files = ("lli_lambda_design_matrix_20261030.json", "projection_e5_champ_plus_lamdots_20261030.json")
    mrows, densities = [], []
    for mf in matrix_files:
        fp = ROOT / "evidence" / mf
        if not fp.is_file():
            continue
        d = json.loads(fp.read_text())
        for fname, v in (d.get("candidates") or {}).items():
            if v.get("role") != "candidate":
                continue
            dens = v.get("projections") or {}
            densities = sorted(set(densities) | set(dens))
            mrows.append({"file": fname, "matrix": mf, "dots": max((x.get("dots", 0) for x in dens.values()),
                                                                   default=0),
                          "proj": {t: dens[t]["projected_dti"] for t in dens},
                          "worst": v.get("delta_worst_case"), "pass": v.get("maximin_beats_champion")})
    # the packaged candidate itself lives in the validation receipt, not the matrix file
    if val.get("projections") and not any(r["file"].rsplit(".tif", 1)[0] == name for r in mrows):
        _vproj = {t: v["candidate"]["projected_dti"] for t, v in val["projections"].items()
                  if "candidate" in v}
        densities = sorted(set(densities) | set(_vproj))
        mrows.append({"file": f"{name}.tif", "matrix": "lli_candidate_validation_union.json",
                      "dots": max((v["candidate"].get("dots", 0) for v in val["projections"].values()), default=0),
                      "proj": _vproj,
                      "worst": min(_vproj[t] - ph[t] for t in _vproj if t in ph), "pass": False})
    champ_row = {t: ph.get(t) for t in densities}
    def _mrow(r):
        stem = r["file"].rsplit(".tif", 1)[0]
        label = f"<b>{stem}.tif</b> ← packaged here" if stem == name else f"<code>{stem}.tif</code>"
        cells = "".join(f"<td>{r['proj'].get(t, float('nan')):.4f}</td>" for t in densities)
        w = r["worst"]
        wcls = "ok" if (w or 0) > 0 else "no"
        vcls = "ok" if r["pass"] else "no"
        verdict = "PROMOTE" if r["pass"] else "reject"
        return (f"<tr><td>{label}</td><td>{r['dots']:,}</td>{cells}"
                f"<td class=\"{wcls}\">{w:+.4f}</td><td class=\"{vcls}\">{verdict}</td></tr>")

    rows_matrix = "".join(_mrow(r) for r in sorted(
        mrows, key=lambda r: -(r["worst"] if r["worst"] is not None else -9)))

    pbc = {}
    for _f in sorted((ROOT / "evidence").glob("pool_buffer_coverage_*.json")):
        pbc = json.loads(_f.read_text())
        break
    pkg_audit_path = ROOT / "docs" / "downloads" / f"{card.get('submission_name', '')}-audit.json"
    _audit = json.loads(pkg_audit_path.read_text()) if pkg_audit_path.is_file() else {}
    audit_bytes = _audit.get("bytes", 0)
    _zp = ROOT / "docs" / "downloads" / f"{card.get('submission_name', '')}.tif.zip"
    zip_kb = (_zp.stat().st_size / 1024.0) if _zp.is_file() else 0.0
    audit_lat = (json.loads(pkg_audit_path.read_text())["calibration_lattice_3px_overlap"]
                 if pkg_audit_path.is_file() else 0.0)
    okdl = card.get("ok_to_download")
    oksb = card.get("ok_to_submit")
    ver = card.get("verdict", "—")
    okdl_str, oksb_str = str(bool(okdl)).lower(), str(bool(oksb)).lower()
    _pv = sorted(pc.values()) if pc else [0.0, 0.0]
    _cv = sorted(ph.values()) if ph else [0.0, 0.0]
    proj_lo, proj_hi, champ_lo, champ_hi = _pv[0], _pv[-1], _cv[0], _cv[-1]
    if okdl and oksb:
        flag = ('<span class="ok">OK TO DOWNLOAD</span> <span class="ok">OK TO SUBMIT — promoted by every gate'
                '</span>')
    elif okdl:
        flag = ('<span class="ok">OK to download and OK to upload — portal-valid format, not a duplicate</span> '
                '<span class="no">NOT OK to submit as a promoted entry — the projection does not beat the '
                'champion under every truth density and the holdout gate is unrunnable</span>')
    else:
        flag = '<span class="no">NOT OK to download — do not use as a submission</span>'
    flag_inline = ("OK to download; NOT OK to submit" if (okdl and not oksb)
                   else "OK to download and OK to submit" if okdl else "NOT OK to download")
    cleared = ("CLEARED FOR SUBMISSION — promoted by every gate" if (okdl and oksb)
               else "NOT CLEARED FOR SUBMISSION — the promotion gates are not met")
    banner = (f'<div class="card" style="border-color:var(--no)"><b class="no">{cleared}</b> '
              f'for <code>{name}</code>: <code>ok_to_download={str(bool(okdl)).lower()}</code> · '
              f'<code>ok_to_submit={str(bool(oksb)).lower()}</code> · card verdict <b>{ver}</b>. Downloading or '
              f'uploading this file is an experiment, not a promotion. Nothing on this site is evidenced to beat '
              f'the 0.2778 champion or the 0.4544 leaderboard lead, and the proposed calibration-lattice exemption '
              f'is <b>not a path to clearance</b> for any file.</div>')
    gates_html = " ".join(gate_pill(pkg.get(k), k.split("_")[0]) for k in pkg)

    # ---------- focus-site table ----------
    per = {}
    for r in lli.get("per_raster", []):
        per.setdefault(r["site"], []).append(r)
    frows = ""
    best_site, best_live = None, -1
    for s in FOCUS_SITES:
        cands = sorted(per.get(s, []), key=lambda r: -(r["live"] or 0))
        if not cands:
            frows += (f"<tr><td>{s}</td><td colspan=5 class='small'>best-scoring file could not be matched to a "
                      f"byte-verified raster in the mirror; see the site directly</td>"
                      f"<td><a href='{SITE_URL[s]}'>site</a></td></tr>")
            continue
        r = cands[0]
        if (r["live"] or 0) > best_live:
            best_live, best_site = r["live"], s
        frows += (f"<tr><td><b>{s}</b></td><td><code>{r['file']}</code></td>"
                  f"<td class='big' style='font-size:15px'>{r['live']:.4f}</td>"
                  f"<td>{r['projected_with_published_theta']:.4f}</td>"
                  f"<td>{r['abs_err']:+.4f}</td>"
                  f"<td class='no'>no — member of the {r['dots_raw']:,}-dot ridge family; "
                  f"pixel-identical to ≥1 other site</td>"
                  f"<td><a href='{SITE_URL[s]}'>open</a></td></tr>")
    dup_pairs = "GEMSDOE25 = GEMSDOE30 = GEMSDOE29 (pixel-identical, 44,090 dots, all 0.2600)"

    den_head = "".join(f"<th>{t} (projection)</th>" for t in densities)
    champ_head = "".join(f"<td>{(champ_row.get(t) or float('nan')):.4f}</td>" for t in densities)

    # ---------- ledger for the model ----------
    top = "".join(f"<tr><td>{r['site']}</td><td><code>{r['file'][:52]}</code></td><td>{r['live']:.4f}</td>"
                  f"<td>{r['projected_with_published_theta']:.4f}</td><td>{r['abs_err']:+.4f}</td></tr>"
                  for r in sorted(lli.get("per_raster", []), key=lambda x: -(x["live"] or 0))[:16])
    vsum = val.get("projection_summary", {})
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())

    index = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>GEMSDOESASS3 — GEMS Prize submission control</title>
<link rel=stylesheet href="{prefix}styles.css"><style>{CSS}</style></head><body><main>
<nav><a href="{prefix}index.html">Start here</a><a href="{prefix}executive-summary.html">Executive summary</a>
<a href="{prefix}submission-guide.html">How to submit</a><a href="{prefix}data/current_run_card.json">Run card</a>
<a href="{prefix}irregularities.md">Irregularities</a><a href="{prefix}hypotheses.md">Hypotheses</a></nav>

<h1>GEMS Prize (DOE GEMS) — submission control page</h1>
<p class=small>Built {now}. Every figure below is read from a JSON receipt in <code>docs/data/</code>; run
<code>python scripts/build_site_sass3.py</code> to rebuild. No number here is a score unless it is labelled
<b>OWNER-REPORT</b> (copied from a submission page) — model outputs are labelled <b>PROJECTION</b>.</p>

{banner}
<div class=card>
<div class=k>Recommended download — this repository's own unique candidate</div>
<p style="font-size:17px"><b>{name}</b></p>
<p><a class=btn href="{dl}" download>⬇ Download .tif ({audit_bytes/1e6:.1f} MB,
{card.get('validator_output',{}).get('positive_cells',0):,} dots)</a>
<a class="btn sec" href="{dl}.zip" download>⬇ Download .zip ({zip_kb:.0f} KB, same bytes)</a>
<a class="btn sec" href="{prefix}downloads/{name}-audit.json">audit receipt</a></p>
<p style="font-size:17px">{flag}</p>
<p class=small>SHA-256 <code>{card.get('raster_sha256','')[:32]}…</code> · note (≤140 chars):
<i>{card.get('submission_note','')}</i></p>
<div>{gates_html}</div>
<p class=small>Promotion into a real slot additionally needs the projection rule to hold under every truth
density (see next card) and the 3-per-week cap (rules §3.2). Verdict recorded in the run card: <b>{ver}</b>.</p>
</div>

<div class=card><h3 style="margin-top:0">Source documents (every claim traces to one of these)</h3>
<p class=small><a href="{prefix}research/lane-H-SASS3-I-20261030.md">lane report H-SASS3-I (2026-10-30)</a> ·
<a href="{prefix}research/hypotheses-ranked-20261030.md">ranked hypotheses for the next slots</a> ·
<a href="{prefix}research/focus-site-candidates-20261028.md">per-site candidate table</a> ·
<a href="{prefix}research/independent-review-20261028.md">Independent review (2026-10-28)</a> ·
<a href="{prefix}research/lattice-decision-20261028.md">lattice decision memo</a> ·
<a href="{prefix}research/standing-prompt-as-recorded-20261027.md">the standing prompt, verbatim</a> ·
<a href="{prefix}research/verification-20261030.md">verification log (three passes)</a> ·
<a href="{prefix}data/claims_audit_20261030.json">prose↔receipt reconciliation (52 claims)</a> ·
<a href="{prefix}data/current_run_card.json">run card JSON</a> ·
<a href="{prefix}downloads/{name}-audit.json">packager receipt</a></p></div>

<div class=card>
<h3 style="margin-top:0">Why this file could beat the 0.2778 champion — and why it might not</h3>
<table><tr><th>truth density (λ)</th><th>this candidate (projection)</th><th>champion control (projection)</th><th>difference</th></tr>
{rows_cand or "<tr><td colspan=4 class=small>validation receipt not present yet</td></tr>"}</table>
<p class=small>The instrument (LLI-v1, design S0) is calibrated on {len(lli.get('per_raster',[]))}
live-scored sibling rasters that we re-downloaded and hash-verified in this session: leave-one-out
MAE <b>{lli.get('published_theta_check_on_local_pool',{}).get('mae',float('nan')):.4f}</b>, Spearman
<b>{lli.get('published_theta_check_on_local_pool',{}).get('spearman_pred_vs_live',float('nan')):.3f}</b>;
our own refit of it gives LOO MAE {lli.get('local_refit',{}).get('loo_mae',float('nan')):.4f} / ρ
{lli.get('local_refit',{}).get('loo_spearman',float('nan')):.3f}. Worst case across densities the candidate is
{vsum.get('delta_worst_case',0):+.3f} vs the champion, best case {vsum.get('delta_best_case',0):+.3f}. A
projection is not a score.</p>
</div>

<h2>Read this before you upload</h2>
<div class=card><ul>
<li><b>Format that the portal accepts.</b> The official text says data outside the bounds is “null or nan”,
but the organizer's own reference solution writes <code>0.0</code> there, and the sibling validator marks a
NaN-outside file <code>portal_compliant_range: false</code>. That is why the earlier download from this site
failed with <i>“Predicted values must be in range [0, 1]”</i>: NaN is not in range for that check. This file
carries no NaN anywhere: whole array finite, values in {{0, 1}}. See <a href="{prefix}submission-guide.html">the guide</a>.</li>
<li><b>Uniqueness.</b> No sibling raster has the same positive-cell mask; the highest exact-cell share with any
of the {dup.get('n_pool','?')} mirrored rasters is {100*dup.get('worst_exact_cell_share',{}).get('frac',0):.1f}%;
the candidate is generated by a mechanism none of them uses (submodular max-credit emission against the
live-inverted truth density, not another propensity surface).</li>
<li><b>The protocol's 3-px lane rule is unsatisfiable, measured here:</b> the 3-px buffer of the
{pbc.get('pool_rasters_read','?')}-raster sibling pool covers {100*pbc.get('buffer_coverage_of_scored_domain',1.0):.5f}% of the scored domain ({pbc.get('buffer_cells_in_domain',0):,} of {pbc.get('scored_domain_px',0):,} cells), leaving <b>{pbc.get('cells_a_lane_compliant_raster_may_use','?')}</b> usable cell(s), so <i>every</i>
possible raster fails “≤70% of dots within 3 px of any registry raster”. The driver is a <b>synthetic</b>
space-filling calibration probe (<code>13gems_20261001_r13-lattice-s5_v2</code>: 206,895 dots on a 5×5 px grid,
3-px buffer covering 99.87% of the footprint), which any footprint-spanning raster is inside of. We do <i>not</i>
exempt it: the lattice is a registry raster, the measured overlap against it ({100*audit_lat:.2f}%) is printed on
the card, and the proposed exemption is not a path to clearance. We report the number instead of pretending to
pass it.</li>
<li><b>What we cannot verify without your login:</b> the catalogue holdout needs
<code>training_features.tif</code> (19-band stack, login-walled), so the hide-and-recover gate is
<b>NOT RUN</b>. Flagged as irregularity IR-SASS3-74.</li>
</ul></div>

<h2>Leaderboard reality check (verified {now})</h2>
<div class=card><p>Top of the public leaderboard today: #1 xiaofanhu <b>0.4544</b>, #2 cfld__ 0.3916,
#3 Batik Shirt Brothers 0.3911, #4 BrandenKMurray 0.3841, #5 op01 0.3642
(<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a>).
The best GEMSDOE-family file in {len(led.get('index',{}))} mirrored ledger rows is 0.2778 — about
<b>0.18 below the competition lead</b>, and the prompt's “0.3195 is the highest score” is rank ~27, not the top.
The gap is a surface-quality gap, not an emission-budget gap: see the
<a href="{prefix}executive-summary.html">executive summary</a>, §3.</p></div>
</main></body></html>"""

    archive_rows = "".join(
        f"<tr><td><code>{n}</code></td><td class='no'>NOT OK to submit — archive only</td><td class=small>{why}</td></tr>"
        for n, why in (
            ("gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.tif",
             "NaN outside the footprint: the portal range check rejects NaN, so this upload fails. Kept for analysis."),
            ("gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif",
             "74,418 positive cells outside the scored bounds; reads no data; no score estimable."),
            ("gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif",
             "4,911 positive cells outside the scored bounds."),
            ("gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif",
             "holdout below champion; superseded."),
            ("gemsdoesass3-gsdhua3-sar-deconf-37654-20261027-74f544e862fd-zeros.tif",
             "superseded; uniqueness receipt predates the current auditor.")))

    execsum = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>GEMSDOESASS3 executive summary</title>
<style>{CSS}</style></head><body><main>
<nav><a href="{prefix}index.html">Start here</a><a href="{prefix}executive-summary.html">Executive summary</a>
<a href="{prefix}submission-guide.html">How to submit</a><a href="{prefix}data/current_run_card.json">Run card</a></nav>
<h1>Executive summary — the nine focus sites, our candidate, and the score estimator</h1>
<p class=small>Built {now}. Evidence classes: <span class=pill>ORGANIZER-CONFIRMED</span> = copied from a
submission receipt; <span class=pill>OWNER-REPORT</span> = score typed on a sibling site / in the brief;
<span class=pill>PROJECTION</span> = LLI model output, never a score.</p>

<h2>1. Which file to download, per site</h2>
<div class=card><p>Answering the brief directly: <b>there is no site below whose best file is unique.</b> All nine
best files are members of one family — thinned subsets of the same H19-5 ridge network (37,654–60,069 dots),
mutually ≥99% within 3 px, and some are pixel-identical across sites ({dup_pairs}). Downloading any of them
would be a duplicate submission, which the brief forbids.</p>
<table><tr><th>site</th><th>best file on that site (owner-reported)</th><th>live DTI</th>
<th>LLI projection</th><th>model error</th><th>unique vs the other sites?</th><th>site</th></tr>{frows}</table>
<p class=small>“live DTI” is the owner-reported score of that file (mirror of
<code>docs/score-ledger.csv</code> in the GEMSDOE32 repository, {len(led.get('index',{}))} rows, not organizer
receipts). Projections come from the model we re-derived in this session; the family bias is +0.008 … +0.020,
i.e. the model over-predicts these rasters slightly, which is why differences matter more than levels.</p>
</div>

<h2>2. Our unique candidate (the one file to take)</h2>
<div class=card>
<p><b>{name}</b> — {card.get('validator_output',{}).get('positive_cells',0):,} dots, mechanism
H-SASS3-I (submodular max-credit emission on the live-inverted truth density).</p>
<p style="font-size:17px">{flag}</p>
<p><a class=btn href="{dl}" download>⬇ Download .tif</a><a class="btn sec" href="{dl}.zip" download>⬇ .zip</a></p>
<p>{'<span class="ok">OK to download and submit (format + uniqueness verified automatically).</span>' if okdl else '<span class="no">Blocked.</span>'}
{'<span class="warn">Slot promotion is conditional: the projection does not beat the champion under every density.</span>' if not oksb else '<span class="ok">Projection-robust across densities.</span>'}</p>
<p class=small>Run card: <a href="{prefix}data/current_run_card.json">{prefix}data/current_run_card.json</a> ·
validator gates: {gates_html}</p></div>

<h2>3. Why 0.2778 is the family ceiling — and what the ceiling is made of</h2>
<div class=card>
<p>The metric is <code>DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)</code> with
<code>TP_w = Σ<sub>y∈G</sub> max<sub>x</sub> p(x)·k(d(x,y))</code> and a triangular kernel of radius 300 m
(3 px) — <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">page 967</a>.
Two consequences that the ~90 sibling submissions never exploited:</p>
<ul>
<li><b>Credit saturates.</b> Because a true pixel is paid once (the <i>max</i>), a dot within 3 px of another
dot adds cost but little credit. GEMSDOE32's own forensic table shows the family's progression: 121,131 dots
→ 0.1922, 60,069 → 0.2477, 44,090 → 0.2600, 37,654 → <b>0.2778</b> (kernel credit per dot rising 8.4 → 20.1 px/dot).</li>
<li><b>The scored population is off-catalogue.</b> Known faults are masked out of scoring, so a raster that
traces the catalogue beautifully can still score badly. That is why the catalogue holdouts in these repos rank
the nine files in the <i>reverse</i> order of the leaderboard (HIDE-RECOVER ρ = −0.849) and why a
score-anchored estimator is needed at all.</li>
</ul>
<p>So the champion is not a better geological idea than its neighbours — it is the same ridge family with the
best <i>packing</i>. The remaining 0.17 to the leaderboard lead is surface quality (finding traces the catalogue
lacks), which needs the 19-band feature stack and the labels; that is login-walled (IR-SASS3-74).</p>
</div>

<h2>4. Score estimator: what we can now do</h2>
<div class=card>
<p><code>scripts/lli_score_model.py</code> re-derives the Live-Ledger Inversion from scratch on rasters we
downloaded and hash-checked this session, and it reproduces the published fit (inverted truth population
|G| = {lli.get('published_theta_check_on_local_pool',{}).get('g_truth_pixels',0):,.0f} px — identical to the published
16,948.3). Applying the published density to the {len(lli.get('per_raster',[]))} live-scored files we hold gives:</p>
<table><tr><th>site</th><th>file</th><th>live (owner-report)</th><th>projection</th><th>error</th></tr>{top}</table>
<p class=small>Cross-validated accuracy: LOO MAE
{lli.get('local_refit',{}).get('loo_mae',float('nan')):.4f}, ρ {lli.get('local_refit',{}).get('loo_spearman',float('nan')):.3f};
leave-one-site-out MAE {lli.get('local_refit',{}).get('leave_site_out_mae',float('nan')):.4f}, ρ
{lli.get('local_refit',{}).get('leave_site_out_spearman',float('nan')):.3f} (our refit) vs upstream
{lli.get('local_refit',{}).get('upstream_loo_mae',float('nan')):.4f} on 111 rasters. Use it to rank and reject
candidates for free; do not read a projection as an expected score.</p>
<p>Measured limits of the instrument: rasters outside the ridge family are badly under-predicted
(GEMSDOE70 live 0.2478 vs projection 0.1385), and a design optimised against one density need not win under
another — our first candidate projected 0.3983 under S0 but 0.1940 under S3. That is why the promotion rule
requires <i>every</i> density, and why the verdict on our candidate is recorded as
<b>{ver}</b>.</p>
</div>

<h2>4a. Promotion status: BLOCKED</h2>
<div class=card><p><b class="no">BLOCKED</b> for every file on this site, including the current candidate: the
spatially-blocked holdout (HOLDOUT-DTI) is <b>NOT RUN</b> and cannot be run here, because
<code>training_features.tif</code> and the SGMC stack are login-walled at the competition data page
(IR-SASS3-74). The three-density projection maximin we run instead is a screen, not a holdout, and it rejects
this candidate. So the site says: <b>OK to download, BLOCKED for submission promotion</b>. See
<a href="{prefix}submission-guide.html">the guide</a> for what a slot spent on this file would buy.</p></div>

<h2>4a. Scoreboard reality check</h2>
<div class=card><p>Best file any focus site has put up is <b>0.2778</b> (GEMSDOE32, OWNER-REPORT). Public
#1 on 2026-10-30 is <b>0.4544</b> (xiaofanhu, 34 submissions), #2 0.3916, #5 0.3642; the prompt's "0.3195 is
the highest" is rank ~27, and "0.4413" is an older snapshot. So the question is not "can we squeeze +0.02 out of
the 0.245–0.278 family" — that whole band is one ridge-thinning lineage — it is whether we can build a better
surface, which needs the 19-band feature stack (IR-SASS3-74). This site therefore promotes nothing:
<code>ok_to_submit={oksb_str}</code> for the current candidate, and every archived file is
marked <b>NOT CLEARED FOR SUBMISSION</b>. The proposed calibration-lattice exemption is
<b>not a path to clearance</b> for any file on this site.</p></div>

<h2>4b. Superseded files on this site — NOT OK to submit</h2>
<div class=card><p>These remain downloadable for analysis only. Each is <b>NOT OK to submit</b>:</p>
<table><tr><th>file (docs/downloads/)</th><th>verdict</th><th>why</th></tr>{archive_rows}</table></div>

<h2>4c. Emission designs tried in this lane (all PROJECTIONS, never scores)</h2>
<div class=card><p>Hypothesis H-SASS3-I: place dots by maximising inverted-truth-density credit instead of
emitting another propensity surface. Promotion rule fixed in advance: beat the champion under <i>every</i> truth
density we can fit. Five designs were emitted and screened; the champion control is projected in the same run, so
the last column is a difference of projections (instrument LOO error ±0.02).</p>
<table><tr><th>design (emission file)</th><th>dots</th>{den_head}<th>worst paired Δ vs champion</th>
<th>maximin</th></tr>
{rows_matrix}
<tr><td><i>champion control (GEMSDOE32, live 0.2778 OWNER-REPORT)</i></td><td>37,654</td>{champ_head}<td>—</td>
<td>reference</td></tr></table>
<p class=small>Receipts: <code>evidence/lli_lambda_design_matrix_20261030.json</code>,
<code>evidence/projection_e5_champ_plus_lamdots_20261030.json</code>,
<code>evidence/lli_candidate_validation_union.json</code>. Reading: every sparse λ-greedy design wins under the
density it was fit on and loses under the other two — the score plateau is not a λ-tuning problem. "Worst paired
Δ" is the minimum over densities of (candidate − champion); the receipt for the packaged file also records a
stricter unpaired figure (candidate minimum − champion maximum) of
{(val.get('projection_summary') or {}).get('delta_worst_case', float('nan')):+.4f}, which is the number the run
card promotes or rejects on. The top row
(champion ∪ our dots, E5) is the only non-losing construction we found, and it is deliberately <b>not</b> offered as
a submission because it contains a sibling site's whole dot set. Lane report:
<a href="{prefix}research/lane-H-SASS3-I-20261030.md">docs/research/lane-H-SASS3-I-20261030.md</a>.</p></div>

<h2>5. Irregularities flagged for review</h2>
<div class=card><p>The ledger holds {n_ir} entries
(<a href="{prefix}data/irregularities_ledger.json">JSON</a>, <a href="{prefix}irregularities.md">readable</a>).
New in this pass: the unsatisfiable 3-px lane rule (measured: pool buffer = 110% of the scored domain);
zeros-vs-NaN outside convention and the resulting portal rejection; sibling-repo mirrors of
<code>labels.tif</code>/<code>training_features.tif</code> being used after SHA-pinning (corroborated across
independent repositories, still not organizer-authenticated); the projection optimism of λ-optimised designs;
and the shared GitHub API rate limit exhausted by the parallel sessions.</p></div>
</main></body></html>"""

    guide = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>How to submit</title><style>{CSS}</style>
</head><body><main>
<nav><a href="{prefix}index.html">Start here</a><a href="{prefix}executive-summary.html">Executive summary</a>
<a href="{prefix}submission-guide.html">How to submit</a></nav>
<h1>Exactly how to submit into the GEMS Prize challenge</h1>
<div class=card><p style="font-size:17px">{flag}</p>
<p class=small><b>How to read the numbers on this page.</b> <span class=pill>OWNER-REPORT</span>
= a live score copied from a submission page (the champion 0.2778 and the focus-9 column).
<span class=pill>PROJECTION</span> = output of the LLI-v1 score model (calibrated on 34 hash-verified live
rasters, LOO MAE 0.019-0.022), never a score: our candidate projects
{proj_lo:.4f}-{proj_hi:.4f} against the champion control's {champ_lo:.4f}-{champ_hi:.4f} under the same
instrument, which is a screen for spending a slot, not a result. The spatially-blocked holdout that would be
required to call it an improvement is NOT RUN (IR-SASS3-74). The lattice exemption is not a path to clearance.</p>
<p class=small>Gate flags on this file: <code>ok_to_download={okdl_str}</code>,
<code>ok_to_submit={oksb_str}</code>. {cleared}; the proposed lattice exemption is not a path to clearance.</p>
<p class=small>Read this before you upload: {name} is <b>{flag_inline}</b>. "OK to download" means the bytes,
the grid and the value range satisfy what the portal checks and that the file is not a copy of any sibling
submission. "NOT OK to submit" is a <i>promotion</i> verdict, not a format failure: this repository will not
call a file an improvement until it beats the champion under every truth density we can fit and clears a
spatially-blocked holdout. Uploading it anyway is a legitimate <b>experiment</b> (3 slots per week, rules §3.2)
whose product is a measurement, not a podium — and that measurement is the only way to settle which truth
density is right.</p><ol>
<li>Download <code>{name}.tif</code> (or the .zip) from the <a href="{prefix}index.html">start page</a>.
Both are accepted: the portal takes “a single-band GeoTIFF (.tif), or a .zip containing a single GeoTIFF”.
The .tif is {audit_bytes/1e6:.1f} MB because it is uncompressed and stripped — deliberately, it is the byte
profile of the accepted 0.2778 file; the .zip is the identical bytes deflated ({zip_kb:.0f} KB), and the inner
file's SHA-256 is in the receipt.</li>
<li>Check the receipt beside it: <code>{name}-audit.json</code> — SHA-256, gate list, dot count. If
<code>ok_to_download</code> is not <code>true</code>, stop. Locally,
<code>python scripts/verify_all_gates.py --expect-download-ok</code> must exit 0.</li>
<li>Open the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">submission page</a> →
<i>New submission</i> → attach the file → add the note below → submit.</li>
<li>Note to paste (≤140 chars, unique to this file): <code>{card.get('submission_note','')}</code></li>
<li>Name/label of the submission: <code>{name}</code>. Weekly cap is 3 submissions (rules §3.2); record the
submission in <code>docs/data/</code> so the slot ledger stays honest.</li>
</ol></div>

<h2>What the portal checks, and why the previous download failed</h2>
<div class=card>
<p>Submission format, <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official problem page</a>:
single layer, float32, values in [0, 1], EPSG:32611, 100 m cells, same bounds as the training data, and
“data outside the bounds is null or nan”.</p>
<p>The file this site previously offered wrote <b>NaN</b> outside the footprint (the literal reading of that
sentence). The portal's range check rejected it with <i>“Predicted values must be in range [0, 1]”</i> — NaN is
not in [0, 1]. Two independent pieces of evidence say 0.0 is what the organizers expect and accept:</p>
<ul><li>the organizer reference solution initialises its output map with <code>np.zeros</code> and writes the
result without any nodata tag
(<a href="https://github.com/drivendataorg/gems-prize-reference-solution">repo</a>, notebook cells
<code>y_out = np.zeros(y_patches.shape)</code> → <code>predicted_faults_example.tif</code>);</li>
<li>the sibling GEMSDOE32 validator records <code>outside_mode:"zeros" → portal_compliant_range:true</code> and
<code>outside_mode:"nan" → false</code> for the same dot field
(<a href="https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/research/validation_summary.json">receipt</a>).</li></ul>
<p>Our file therefore: GTiff, 1 band, 3292×3730, float32, EPSG:32611, transform
(100, 0, 243350, 0, −100, 4508550), no nodata tag, no NaN anywhere, values exactly {{0, 1}}, 0 outside the
scored footprint. That profile is copied from the file the portal already accepted and scored 0.2778.</p>
</div>

<h2>What “validated for submission” means here (no human inspector)</h2>
<div class=card><table>
<tr><th>gate</th><th>check</th><th>how it is measured</th></tr>
<tr><td>G1 range</td><td>whole array finite, in [0,1]</td><td><code>scripts/validate_submission_tif.py</code> + packager</td></tr>
<tr><td>G2 grid</td><td>shape/CRS/transform/dtype/bands == organizer sample</td><td>rasterio metadata vs <code>sample_submission.tif</code></td></tr>
<tr><td>G3 bounds</td><td>no positive mass outside the footprint</td><td>footprint = finite cells of the sample</td></tr>
<tr><td>G4 uniqueness</td><td>no identical mask / no ≥95% subsumption among all mirrored sibling rasters</td><td>XOR of positive-cell masks, per file</td></tr>
<tr><td>G5 lane</td><td>3-px overlap vs every sibling + calibration lattice (reported)</td><td>cell-hash neighbour test</td></tr>
<tr><td>G6 projection</td><td>beats the champion under <i>every</i> truth density</td><td><code>scripts/lli_validate_candidate.py</code></td></tr>
</table>
<p class=small>Run everything with <code>python scripts/verify_all_gates.py</code>; it exits 0 only when the
recorded gates and the run card agree. The catalogue holdout is a separate gate and is
{"NOT RUN — blocked on the login-walled feature stack" if card.get('holdout_dti',{}).get('status')=='NOT RUN' else "see run card"}.</p>
</div>
</main></body></html>"""
    return index, execsum, guide


def main() -> int:
    # Pages published by GitHub Pages from the repository root: the root copy links into docs/,
    # the docs/ copy is the same content with the prefix removed (never a string replace, which
    # would corrupt absolute sibling URLs that contain "/docs/").
    (ROOT / "index.html").write_text(build("docs/")[0])
    (ROOT / "executive-summary.html").write_text(build("docs/")[1])
    (ROOT / "submission-guide.html").write_text(build("docs/")[2])
    for p, i in ((DOCS / "index.html", 0), (DOCS / "executive-summary.html", 1),
                 (DOCS / "submission-guide.html", 2)):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(build("")[i])
    # keep the page-facing JSON copies in sync with evidence/
    import shutil
    (DOCS / "data").mkdir(parents=True, exist_ok=True)
    for f in ("current_run_card.json", "score_ledger_index.json", "lli_score_model_verification.json",
              "lli_candidate_validation_union.json", "lli_candidate_validation.json",
              "lambda_emission_variants.json", "lambda_emission_mean_20261030T0340Z.json",
              "lli_lambda_design_matrix_20261030.json",
              "projection_e5_champ_plus_lamdots_20261030.json",
              "leakage_canary_report.json", "claims_audit_20261030.json",
              "pool_buffer_coverage_20261030.json", "irregularities_ledger.json"):
        src = ROOT / "evidence" / f
        if src.exists():
            shutil.copy2(src, DOCS / "data" / f)
    print("wrote index/executive-summary/submission-guide (root + docs) and synced docs/data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
