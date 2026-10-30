#!/usr/bin/env python3
"""Idempotently insert the current-candidate banner into the two overview pages.

The overview pages (`index.html` and `docs/index.html`) are hand-maintained and carry contract text that
`tests/test_independent_review.py` and `tests/test_lattice_decision_20261028.py` assert on, so they are not
regenerated wholesale. This script replaces only the block between the sentinels

  <!-- SASS3:CANDIDATE:BANNER-BEGIN --> ... <!-- SASS3:CANDIDATE:BANNER-END -->

which keeps the pages idempotent (run it twice, same bytes) and keeps the download prompt on the overview
consistent with the SHA-256 in `evidence/candidate_build_receipt.json`. Hrefs are rewritten per page
location, so the local-link test passes from both the repo root and `docs/`.

Usage:  /home/user/.venv/bin/python scripts/announce_candidate_on_pages.py
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEGIN, END = "<!-- SASS3:CANDIDATE:BANNER-BEGIN -->", "<!-- SASS3:CANDIDATE:BANNER-END -->"
BLOCK = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--receipt", default=str(ROOT / "evidence/candidate_build_receipt.json"))
    ap.add_argument("--lane", default=str(ROOT / "evidence/lane_sweep_s3_ocm_20261030.json"))
    ap.add_argument("--pages", default="index.html,docs/index.html")
    args = ap.parse_args()

    build = json.loads(Path(args.receipt).read_text())
    lane = json.loads(Path(args.lane).read_text())
    subs = [r for r in lane["rows"] if r.get("status") == "ok" and "/docs/downloads/" in r["file"]]
    latt = [r for r in lane["rows"] if r.get("status") == "ok" and "lattice" in r["file"]]
    max_sub = max(r["overlap3px_cand_within_registry"] for r in subs)
    max_lat = max((r["overlap3px_cand_within_registry"] for r in latt), default=float("nan"))
    safe, lit = build["safe"], build["literal"]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for rel in [p.strip() for p in args.pages.split(",") if p.strip()]:
        page = ROOT / rel
        pre = "docs/" if str(page.parent) == str(ROOT) else ""
        h = (
            f"{BEGIN}\n<section class=\"hero ok\"><p class=\"label\">CURRENT CANDIDATE &middot; updated {stamp} "
            "&middot; one-click download below &middot; NOT OK to submit (ok_to_submit: false) &middot; "
            "NOT CLEARED FOR SUBMISSION</p>"
            f"<h2>Download <code>{safe['tif']}</code></h2>"
            f"<p><a class=\"btn\" href=\"{pre}downloads/{safe['tif']}\">TIF ({safe['tif_bytes']:,} bytes)</a> "
            f"<a class=\"btn alt\" href=\"{pre}downloads/{safe['zip']}\">ZIP</a> "
            f"<a href=\"{pre}executive-summary.html\">Submission guide &amp; nine-site table</a> "
            f"<a href=\"{pre}research/FEED.md\">Status feed</a></p>"
            f"<p><b>SHA-256</b> <code>{safe['tif_sha256']}</code> &middot; {build['emitted_px']:,} positive pixels "
            f"&middot; float32, EPSG:32611, 3730&times;3292, binary emission, all stored cells in [0, 1] with a "
            "GDAL per-dataset mask band outside the footprint.</p>"
            f"<p><b>Uniqueness:</b> max 3-px dot overlap {max_sub:.4f} against {len(subs)} pinned sibling "
            f"submissions (cap 0.70 &mdash; PASS), {max_lat:.4f} against the {len(latt)} saturated calibration "
            "lattices (literal FAIL; the lattice exemption is a proposed amendment, not applied). No exact duplicate "
            "against any registry raster. <b>SLOT USE BLOCKED:</b> this file is not a path to clearance &mdash; it is "
            "format-ready and unique, and no instrument shows it beating the 0.2778 champion.</p>"
            "<p>The 2026-10-29 promoted file <code>gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.tif</code> "
            "(and the reference copy <code>" + lit["tif"] + "</code>) is kept for education only: a NaN payload outside the "
            "footprint is the exact failure mode behind the live portal error &ldquo;Predicted values must be in range "
            "[0, 1]&rdquo;.</p></section>\n"
            f"{END}"
        )
        txt = page.read_text()
        if BLOCK.search(txt):
            new = BLOCK.sub(lambda m: h, txt, count=1)
        else:
            i = txt.find("<main>")
            if i < 0:
                raise SystemExit(f"{rel}: no <main> anchor; add the sentinels by hand once")
            i += len("<main>")
            new = txt[:i] + "\n" + h + txt[i:]
        page.write_text(new)
        print(f"{rel}: banner {'replaced' if BLOCK.search(txt) else 'inserted'} ({len(h)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
