#!/usr/bin/env python3
"""Per-site best file for the nine focus sites, with duplicate/uniqueness overlaps — from bytes.

For each of GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36 the highest-scoring published file is taken
from the model receipt's per-file table (which came from the 128-file score corpus), and three
overlaps are measured on the rasters themselves, all with a 3 px Chebyshev neighbourhood (the
organizer kernel radius, 300 m):

* ``worst_overlap_other_focus``  — share of this file's dots that sit near another focus site's best
  file.  Near 1.0 means the two files are the same field.
* ``new_dots_within_this_file``  — share of **our new candidate's** dots near this file.  This is the
  direction the uniqueness rule constrains; it must stay under the cap.
* ``this_files_dots_within_new`` — share of this file's dots near our candidate.  It is large because
  our candidate is denser than any of them, and it is reported so the asymmetry is not mistaken for
  a duplicate in the other direction.

Usage
-----
    python scripts/build_focus9_table_20261031.py [--registry .cache/registry_rasters]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
FOCUS = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
MODEL = ROOT / "evidence" / "blockinversion_model_20261031.json"
OUT = ROOT / "evidence" / "focus9_best_files_20261031.json"
STRUCT = np.ones((7, 7), bool)


def load_mask(p: Path, shape) -> np.ndarray | None:
    try:
        with rasterio.open(p) as ds:
            if ds.shape != tuple(shape):
                return None
            a = ds.read(1)
    except Exception:  # noqa: BLE001 - an unreadable raster is reported as absent
        return None
    m = np.isfinite(a) & (a > 0)
    return m if m.any() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", type=Path, default=ROOT / ".cache" / "registry_rasters")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    model = json.loads(MODEL.read_text())
    by_site: dict[str, dict] = {}
    for row in model["files"]:
        site = row["site"]
        if site not in FOCUS:
            continue
        if site not in by_site or row["owner_reported_score"] > by_site[site]["owner_reported_score"]:
            by_site[site] = row
    missing = [s for s in FOCUS if s not in by_site]
    if missing:
        raise SystemExit(f"focus sites missing from the model table: {missing}")

    with rasterio.open(ROOT / ".cache" / "gems_data" / "sample_submission.tif") as ds:
        shape = ds.shape
    new_tif = ROOT / "docs" / "downloads" / f"{model['submission']['submission_name']}.tif"
    new_mask = load_mask(new_tif, shape)
    if new_mask is None:
        raise SystemExit(f"candidate raster unreadable: {new_tif}")

    masks, paths = {}, {}
    for site in FOCUS:
        name = Path(by_site[site]["file"]).name.split("__")[-1]
        cands = list(args.registry.rglob(name))
        if not cands:
            raise SystemExit(f"registry copy of {name} not found — run scripts/fetch_sibling_registry_rasters.py")
        paths[site] = cands[0]
        m = load_mask(paths[site], shape)
        if m is None:
            raise SystemExit(f"unreadable raster for {site}: {paths[site]}")
        masks[site] = m
    dilated = {s: binary_dilation(m, structure=STRUCT) for s, m in masks.items()}

    out = {}
    for site in FOCUS:
        m = masks[site]
        others = sorted(((float((m & dilated[s2]).sum()) / m.sum(), s2) for s2 in FOCUS if s2 != site),
                        reverse=True)
        row = dict(by_site[site])
        out[site] = {
            "file": str(paths[site].relative_to(ROOT)),
            "sha256": row.get("sha256"),
            "D": int(m.sum()),
            "owner_reported_score": row["owner_reported_score"],
            "loo_predicted_score": row["loo_predicted_score"],
            "worst_overlap_other_focus": round(others[0][0], 4),
            "worst_overlap_site": others[0][1],
            "new_dots_within_this_file": round(float((new_mask & dilated[site]).sum()) / new_mask.sum(), 4),
            "this_files_dots_within_new": round(float((m & binary_dilation(new_mask, structure=STRUCT)).sum())
                                                / m.sum(), 4),
        }
        print(f"{site:10s} D={out[site]['D']:6d} score={row['owner_reported_score']:.4f} "
              f"loo={row['loo_predicted_score']:.4f} dup={others[0][0]:.4f} ({others[0][1]}) "
              f"ours->theirs={out[site]['new_dots_within_this_file']:.4f} "
              f"theirs->ours={out[site]['this_files_dots_within_new']:.4f}")

    payload = {
        "schema_version": 1,
        "label": "OWNER-REPORT scores; overlaps measured on raster bytes",
        "not_organizer_confirmed": True,
        "candidate": model["submission"]["submission_name"],
        "candidate_dots": int(new_mask.sum()),
        "neighbourhood_px": 3,
        "note": ("new_dots_within_this_file is the direction the uniqueness cap constrains; "
                 "this_files_dots_within_new is large because the candidate is denser than any focus file."),
        "sites": out,
    }
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
