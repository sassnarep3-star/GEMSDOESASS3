#!/usr/bin/env python3
"""Build the scored-raster corpus: validate every fetched raster and cache its dots.

For every raster in ``registry/sibling_downloads_manifest_20261031.json`` this script

1. opens it with rasterio and checks the submission-format gates that can be checked
   without the hidden labels (CRS, shape, transform, band count, dtype, value range);
2. extracts the non-zero cells as flat indices (``uint32``) plus their values, and stores
   them in ``.cache/corpus_20261031/<sha>.npz`` so later steps never re-open 3 000 rasters;
3. matches the file name against ``registry/published_score_table_20261030.json`` so each
   raster that the owner published a score for is flagged with that score
   (label: OWNER-REPORT, never organizer-confirmed).

Output: ``registry/corpus_20261031.json`` (tracked) + ``.cache/corpus_20261031/`` (ignored).

Usage:
    python scripts/build_corpus_20261031.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CACHE = ROOT / ".cache" / "corpus_20261031"
MANIFEST_IN = ROOT / "registry" / "sibling_downloads_manifest_20261031.json"
SCORE_TABLE = ROOT / "registry" / "published_score_table_20261030.json"
OUT = ROOT / "registry" / "corpus_20261031.json"

EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
EXPECTED_EPSG = 32611

# Suffix tokens the owners append to publish the same raster in several encodings.
STATUS_SUFFIXES = [
    "zeros-zeros", "nanoutside", "allfinite", "zeros", "zero", "nan", "hard",
    "safe", "build", "candidate",
]


def strip_status(name: str) -> str:
    """Remove a trailing -nan / -zeros / -allfinite / ... token (repeatedly)."""
    base = re.sub(r"\.tif$", "", name, flags=re.I)
    changed = True
    while changed:
        changed = False
        for suf in STATUS_SUFFIXES:
            for sep in ("-", "_"):
                if base.lower().endswith(sep + suf):
                    base = base[: -(len(suf) + 1)]
                    changed = True
    return base


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-cache", action="store_true")
    args = ap.parse_args()

    import rasterio  # imported late so --help works without the dep

    man = json.loads(MANIFEST_IN.read_text())
    files = man["files"]
    if args.limit:
        files = files[: args.limit]

    scores = json.loads(SCORE_TABLE.read_text())["entries"]
    # index the score tokens by normalised, status-stripped name
    token_index: dict[str, list[dict]] = {}
    for e in scores:
        key = norm(strip_status(e["token"]))
        token_index.setdefault(key, []).append(e)

    CACHE.mkdir(parents=True, exist_ok=True)
    out: list[dict] = []
    n_bad = 0
    for i, f in enumerate(files, 1):
        path = ROOT / ".cache" / "sibling_downloads" / f["pool_file"]
        rec = {
            "pool_file": f["pool_file"], "repo": f["repo"], "owner": f["owner"],
            "repo_path": f["repo_path"], "bytes": f["bytes"], "sha256": f["sha256"],
        }
        if not path.exists():
            rec["status"] = "missing"
            n_bad += 1
            out.append(rec)
            continue
        try:
            with rasterio.open(path) as ds:
                rec.update(count=ds.count, dtype=ds.dtypes[0], height=ds.height, width=ds.width)
                rec["crs"] = ds.crs.to_epsg() if ds.crs else None
                rec["transform"] = list(ds.transform)[:6]
                if ds.count != 1:
                    rec["status"] = "rejected_multiband"
                    n_bad += 1
                    out.append(rec)
                    continue
                arr = ds.read(1)
            shape_ok = arr.shape == EXPECTED_SHAPE
            tf_ok = all(abs(a - b) < 1e-6 for a, b in zip(rec["transform"], EXPECTED_TRANSFORM))
            rec["shape_ok"] = shape_ok
            rec["transform_ok"] = tf_ok
            rec["crs_ok"] = rec["crs"] == EXPECTED_EPSG
            if not (shape_ok and tf_ok and rec["crs_ok"]):
                rec["status"] = "rejected_grid"
                n_bad += 1
                out.append(rec)
                continue

            finite = np.isfinite(arr)
            vals = arr[finite]
            rec["n_finite"] = int(vals.size)
            rec["n_nan"] = int(arr.size - vals.size)
            vmin = float(vals.min()) if vals.size else float("nan")
            vmax = float(vals.max()) if vals.size else float("nan")
            rec["vmin"], rec["vmax"] = vmin, vmax
            rec["in_range"] = bool(vals.size and vmin >= 0.0 and vmax <= 1.0)
            nz = (finite & (arr > 0))
            rec["n_positive"] = int(nz.sum())
            rec["mass"] = float(np.nansum(arr))
            rec["is_binary"] = bool(vals.size and set(np.unique(vals).tolist()) <= {0.0, 1.0})
            idx = np.flatnonzero(nz.ravel()).astype(np.uint32)
            val = arr.ravel()[idx].astype(np.float32)
            np.savez_compressed(CACHE / f"{f['sha256']}.npz", idx=idx, val=val)

            # score match
            key = norm(strip_status(f["pool_file"].split("__", 1)[-1]))
            hits = token_index.get(key)
            if hits is None:
                # fall back to substring match on the normalised name
                hits = [e for e in scores
                        if norm(strip_status(e["token"])) and norm(strip_status(e["token"])) in key]
            if hits and len({h["owner_reported_score"] for h in hits}) == 1:
                rec["owner_reported_score"] = float(hits[0]["owner_reported_score"])
                rec["score_token"] = hits[0]["token"]
                rec["score_site"] = hits[0]["site"]
                rec["score_label"] = "OWNER-REPORT"
            elif hits:
                rec["score_ambiguous"] = sorted({h["owner_reported_score"] for h in hits})
            rec["status"] = "ok"
        except Exception as exc:  # pragma: no cover - defensive
            rec["status"] = f"error:{type(exc).__name__}"
            rec["error"] = str(exc)[:200]
            n_bad += 1
        out.append(rec)
        if i % 200 == 0:
            print(f"  ...{i}/{len(files)}", flush=True)

    good = [r for r in out if r.get("status") == "ok"]
    scored = [r for r in good if "owner_reported_score" in r]
    # de-duplicate scored entries by sha256
    seen: dict[str, dict] = {}
    for r in scored:
        seen.setdefault(r["sha256"], r)
    OUT.write_text(json.dumps({
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(MANIFEST_IN.relative_to(ROOT)),
        "grid_expectation": {
            "shape": list(EXPECTED_SHAPE), "transform": list(EXPECTED_TRANSFORM),
            "epsg": EXPECTED_EPSG,
            "authority": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        },
        "n_rasters": len(out), "n_valid": len(good), "n_rejected": n_bad,
        "n_with_owner_score": len(scored), "n_unique_scored_by_sha": len(seen),
        "score_label": "OWNER-REPORT — typed by the owner on the sibling Pages sites; "
                       "not organizer-confirmed, not re-verifiable on the public leaderboard",
        "rasters": out,
    }, indent=1))
    print(f"rasters={len(out)} valid={len(good)} rejected={n_bad} "
          f"scored={len(scored)} unique_scored={len(seen)} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
