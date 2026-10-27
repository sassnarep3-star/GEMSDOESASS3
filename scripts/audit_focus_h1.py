#!/usr/bin/env python3
"""Independently audit the nine user-reported historical rasters (no submission).

This is a bounded, pinned historical comparison, not a complete registry scan.
It cannot authorize a newly generated file or authenticate a leaderboard score.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from bootstrap_template import BRIDGE_HASHES, ensure_template, fetch_file, sha256  # noqa: E402
from evidence_io import choose_output  # noqa: E402


def audit(manifest_path: Path, output_path: Path) -> dict:
    sys.path.insert(0, str(ensure_template()))
    from gems57.gates import format_report

    rows = json.loads(manifest_path.read_text())["rows"]
    cache = ROOT / ".cache" / "focus-nine"
    sample = ROOT / ".cache" / "runtime" / "data" / "official" / "sample_submission.tif"
    faults = ROOT / ".cache" / "runtime" / "data" / "official" / "existing_faults.tif"
    if not sample.is_file() or not faults.is_file():
        raise FileNotFoundError("Run scripts/bootstrap_template.py before the historical audit")
    for path in (sample, faults):
        if sha256(path) != BRIDGE_HASHES[path.name]:
            raise ValueError(f"untrusted mirrored input raster: {path.name}")

    def fetch(row):
        dest = cache / (row["site"] + ".tif")
        fetch_file(f"repos/{row['repo']}/contents/{row['path']}?ref={row['ref']}", dest, row["sha256"])
        return dest

    # A failed download/hash is fatal, not silently treated as a unique result.
    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = list(pool.map(fetch, rows))
    with rasterio.open(sample) as ref, rasterio.open(faults) as labs:
        footprint = np.isfinite(ref.read(1))
        if labs.shape != ref.shape or labs.crs != ref.crs or labs.transform != ref.transform:
            raise ValueError("mirrored labels and sample have different grids")
        catalogue = (labs.read(1) == 1) & footprint
        expected_grid = ref.shape, ref.crs, ref.transform
    masks, format_reports = [], []
    for path in paths:
        with rasterio.open(path) as ds:
            if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != expected_grid:
                raise ValueError(f"historical raster grid does not match sample: {path}")
            arr = ds.read(1)
            masks.append(np.isfinite(arr) & (arr > 0) & footprint)
        report = format_report(path, sample, footprint=footprint)
        format_reports.append(dict(all_finite_policy_passed=report["ok"],
                                   reasons=report["problems"], min=report.get("min"),
                                   max=report.get("max"), nan_pixels=report["nan_pixels"]))
    yy, xx = np.mgrid[-3:4, -3:4]
    disk = yy * yy + xx * xx <= 9
    overlaps = np.zeros((len(rows), len(rows)), dtype=np.float64)
    for i, other in enumerate(masks):
        halo = binary_dilation(other, structure=disk)
        for j, mine in enumerate(masks):
            overlaps[j, i] = float(halo[mine].mean()) if mine.any() else 0.0
    result_rows = []
    for i, row in enumerate(rows):
        others = [(float(overlaps[i, j]), rows[j]["site"]) for j in range(len(rows)) if j != i]
        worst, peer = max(others)
        exact = [rows[j]["site"] for j in range(len(rows)) if i != j and np.array_equal(masks[i], masks[j])]
        result_rows.append({**row, "support_pixels": int(masks[i].sum()),
                            "exact_support_matches_within_nine": exact,
                            "max_fraction_within_3px": worst,
                            "worst_peer": peer,
                            "overlap_by_other_site": {rows[j]["site"]: float(overlaps[i, j])
                                                      for j in range(len(rows)) if i != j},
                            # Rank correlations are not computed in this audit: an overlap pass is
                            # not a protocol clearance. Only a failure can be concluded here.
                            "unique_by_protocol_among_these_nine": False if worst > 0.70 or exact else None,
                            "rank_correlation_check": "NOT RUN — an overlap pass alone cannot establish uniqueness",
                            "format_local_policy": format_reports[i],
                            "estimated_organizer_score": None,
                            "recommendation": "AUDIT ONLY — already used or user-reported; not a new unique file"})
    i32 = next(i for i, r in enumerate(rows) if r["site"] == "GEMSDOE32")
    i31 = next(i for i, r in enumerate(rows) if r["site"] == "GEMSDOE31")
    removed = masks[i31] & ~masks[i32]
    added = masks[i32] & ~masks[i31]
    distances = distance_transform_edt(~catalogue)
    lineage = {
        "from": "GEMSDOE31", "to": "GEMSDOE32",
        "removed_pixels": int(removed.sum()), "added_pixels": int(added.sum()),
        "removed_within_2px_of_catalogue": int((removed & (distances <= 2)).sum()),
        "removed_outside_2px_of_catalogue": int((removed & (distances > 2)).sum()),
        "h33_positive_at_or_within_2px_of_catalogue": int((masks[i32] & (distances <= 2)).sum()),
        "interpretation": "Measured raster lineage only; it does not verify or cause the user-reported score."
    }
    result = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "Only nine pinned historical files compared on the mirrored footprint; rank correlations and private or other submissions not checked.",
        "reported_values_are_not_organizer_receipts": True,
        "source_sample_sha256": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
        "source_labels_sha256": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
        "h33_lineage": lineage,
        "rows": result_rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Audited {len(rows)} pinned historical files; wrote {output_path}")
    print("H33 lineage:", lineage)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="new audit path; never overwrites existing evidence")
    args = parser.parse_args()
    output = choose_output(ROOT / "docs/data/focus-nine-audit.json", args.output)
    audit(ROOT / "registry/focus-nine.json", output)
