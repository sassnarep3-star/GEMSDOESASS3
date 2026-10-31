#!/usr/bin/env python3
"""Independently verify the uniqueness of whatever file main has promoted.

This lane did not build `gemsdoesass3-blockinv3-123899-20261031T062457Z-nullmask.tif`; a parallel
lane did and merged it to main.  Two lanes cannot both be the promoted submission, so rather than
take the other lane's number on trust this re-runs *this* lane's registry scan — 1 978 grid-valid
rasters fetched from 110 sibling repositories, coverage-normalised — on their file, on this lane's
file, and on the 0.2778 champion as the control.

Also scores their file on the honest five-fold design?  No: their file is not in this lane's scored
corpus, so the fold yardsticks are independent of it and the raw fold estimate is comparable to this
lane's.  That comparison is in `scripts/anchor_calibration_20261031.py`; this script does the
uniqueness half, which is the prompt's HIGHEST URGENCY item.

Usage
    python scripts/cross_check_promoted_20261031.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32 import corpus as CP  # noqa: E402
from gems32.corpus import W  # noqa: E402
from build_final_candidate_20261031 import overlap_profile  # noqa: E402

TARGETS = [
    "docs/downloads/gemsdoesass3-blockinv3-123899-20261031T062457Z-nullmask.tif",
    "docs/downloads/gemsdoesass3-gs-s3.0-b60000-n12000-20261031T071328Z.tif",
    ".cache/sibling_downloads/60GEMSDOE__gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif",
]
LABELS = ["blockinv3 (promoted on main, built by the parallel lane)",
          "gs-s3.0-b60000 (built by this lane)",
          "champion control (0.2778, OWNER-REPORT)"]


def dots_of(path: Path):
    with rasterio.open(path) as ds:
        a = ds.read(1, masked=False)
    m = np.isfinite(a) & (a > 0)
    return np.flatnonzero(m.reshape(-1))


def main() -> int:
    valid, _ = CP.load_grid()
    corpus = json.loads(CP.CORPUS_JSON.read_text())
    out = []
    for path, label in zip(TARGETS, LABELS):
        p = ROOT / path
        if not p.exists():
            print("missing", p)
            continue
        idx = dots_of(p)
        prof = overlap_profile(idx, corpus, valid)
        ws = prof["worst_overlap_submission_shaped"]
        print(f"{label}")
        print(f"   dots={idx.size:,}  worst(3px, submission-shaped)={ws['overlap']:.4f} "
              f"against {ws['file'][:70]}")
        print(f"   ref coverage={ws['coverage']:.4f}  lift={ws['lift']:.2f}  "
              f"n refs over 70% = {prof['n_submission_shaped_refs_over_70pct']}"
              f"/{prof['n_submission_shaped_refs']}")
        out.append({"file": str(path), "label": label, "n_dots": int(idx.size),
                    "worst_overlap_submission_shaped": ws,
                    "n_over_70pct": prof["n_submission_shaped_refs_over_70pct"],
                    "n_submission_shaped_refs": prof["n_submission_shaped_refs"],
                    "protocol_rule_1_pass": prof["n_submission_shaped_refs_over_70pct"] == 0,
                    "normalised_criterion_pass": not (ws["overlap"] >= 0.90 and ws["lift"] >= 3.0)})
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "cross_check_promoted_20261031.json").write_text(json.dumps({
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "why": ("two lanes promoted different files on the same day; this re-runs this lane's "
                "independent 1 978-raster registry scan on both, plus the champion control"),
        "rows": out,
    }, indent=1) + "\n")
    print("wrote evidence/cross_check_promoted_20261031.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
