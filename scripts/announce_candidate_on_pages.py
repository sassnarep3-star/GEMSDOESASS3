#!/usr/bin/env python3
"""Idempotently insert the current-candidate banner into the two overview pages.

The overview pages (`index.html` and `docs/index.html`) are hand-maintained and carry contract text that
`tests/test_independent_review.py` and `tests/test_lattice_decision_20261028.py` assert on, so they are not
regenerated wholesale. This script replaces only the block between the sentinels

  <!-- SASS3:CANDIDATE:BANNER-BEGIN --> ... <!-- SASS3:CANDIDATE:BANNER-END -->

which keeps the pages idempotent (run it twice, same bytes) and keeps the download prompt on the overview
consistent with the receipts. Hrefs are rewritten per page location so the local-link test passes from both
the repo root and `docs/`.

All numbers come from: evidence/candidate_build_receipt.json, evidence/lane_sweep_s3_ocm_20261030.json and
the portal-safe re-render receipt for main's promoted candidate (IR-SASS3-86).

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
    ap.add_argument("--render", default=str(ROOT / "evidence/portal_safe_render_gemsdoesass3-tipcont-disp44923-4px-20261030T0330Z-safe.json"))
    ap.add_argument("--pages", default="index.html,docs/index.html")
    args = ap.parse_args()

    build = json.loads(Path(args.receipt).read_text())
    lane = json.loads(Path(args.lane).read_text())
    reprint = json.loads(Path(args.render).read_text())
    subs = [r for r in lane["rows"] if r.get("status") == "ok" and "/docs/downloads/" in r["file"]]
    latt = [r for r in lane["rows"] if r.get("status") == "ok" and "lattice" in r["file"]]
    max_sub = max(r["overlap3px_cand_within_registry"] for r in subs)
    max_lat = max((r["overlap3px_cand_within_registry"] for r in latt), default=0.0)
    safe = build["safe"]
    tip = reprint["output"]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for rel in [p.strip() for p in args.pages.split(",") if p.strip()]:
        page = ROOT / rel
        pre = "docs/" if page.parent == ROOT else ""
        parts = [
            BEGIN,
            '<section class="hero ok"><p class="label">CURRENT CANDIDATES &middot; updated ' + stamp
            + " &middot; one-click downloads below &middot; NOT OK to submit without an owner slot decision"
            " &middot; NOT CLEARED FOR SUBMISSION</p>",
            "<h2>Which file to download</h2>",
            "<p><b>If a slot is to be spent for information, use</b> <code>" + tip["file"] + "</code> &mdash; main's "
            "promoted tip-continuation emission re-rendered in the portal-safe encoding (dot set bit-identical, "
            "symmetric difference " + str(tip.get("dot_set_symmetric_difference", reprint["proof"]["dot_set_symmetric_difference"]))
            + "; SHA-256 <code>" + tip["sha256"] + "</code>). The copy main released with a NaN payload is "
            "<b>rejected by the live form</b> (&ldquo;Predicted values must be in range [0, 1]&rdquo;); see IR-SASS3-86.</p>",
            "<p><b>The uniqueness-clean alternative</b> is <code>" + safe["tif"] + "</code> (SHA-256 <code>"
            + safe["tif_sha256"] + "</code>): " + f"{build['emitted_px']:,}" + " px, max 3-px dot overlap "
            + f"{max_sub:.4f}" + " against all " + str(len(subs)) + " pinned sibling submissions, "
            + f"{max_lat:.4f}" + " against a saturated calibration lattice (literal FAIL, owner question IR-SASS3-82).</p>",
            '<p><a class="btn" href="' + pre + "downloads/" + tip["file"] + '">tipcont -safe TIF</a> '
            '<a class="btn alt" href="' + pre + "downloads/" + str(tip.get("zip", "")) + '">tipcont -safe ZIP</a> '
            '<a class="btn" href="' + pre + "downloads/" + safe["tif"] + '">s3-ocm TIF</a> '
            '<a class="btn no" href="' + pre + "downloads/" + safe["zip"] + '">s3-ocm ZIP</a> '
            '<a href="' + pre + 'executive-summary.html">Submission guide &amp; nine-site table</a> '
            '<a href="' + pre + 'research/FEED.md">Status feed</a></p>',
            "<p><b>Neither file is evidenced to beat 0.2778.</b> Every number available for either one is a projection or a "
            "local HOLDOUT-DTI, and both sit below the champion on the live-calibrated instrument. The portal-validity problem "
            "is fixed for both: mask-band encoding, all validator checks green, exit code 0. SLOT USE BLOCKED &mdash; no file "
            "here is a path to clearance.</p></section>",
            END,
        ]
        block = "\n".join(parts)
        txt = page.read_text()
        if BLOCK.search(txt):
            new = BLOCK.sub(lambda _m: block, txt, count=1)
            action = "replaced"
        else:
            i = txt.find("<main>")
            if i < 0:
                raise SystemExit(f"{rel}: no <main> anchor; add the sentinels by hand once")
            i += len("<main>")
            new = txt[:i] + "\n" + block + txt[i:]
            action = "inserted"
        page.write_text(new)
        print(f"{rel}: banner {action} ({len(block)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
