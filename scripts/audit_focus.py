#!/usr/bin/env python3
"""Reproduce the nine historical-support comparisons; never generate a submission."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from geotiff_audit import template_geometry, validate_tif
from restore_audit_inputs import MANIFEST, load_manifest, sha256_file
from io_safety import protect_inputs

ROOT = Path(__file__).resolve().parents[1]


def binary_spearman(a: np.ndarray, b: np.ndarray, footprint: np.ndarray) -> float | None:
    """Exact rank correlation of two binary arrays: Pearson's phi on the footprint."""
    if a.shape != b.shape or a.shape != footprint.shape:
        raise ValueError("grid mismatch")
    n = int(footprint.sum())
    if n == 0:
        raise ValueError("empty footprint")
    n_a = int((a & footprint).sum())
    n_b = int((b & footprint).sum())
    if not 0 < n_a < n or not 0 < n_b < n:
        return None
    n_ab = int((a & b & footprint).sum())
    # Cast before arithmetic to avoid integer overflow on production grids.
    n, n_a, n_b, n_ab = map(float, (n, n_a, n_b, n_ab))
    den = np.sqrt(n_a * (n - n_a) * n_b * (n - n_b))
    return float((n * n_ab - n_a * n_b) / den)


def load_support(path: Path, geom: dict) -> np.ndarray:
    fp = geom["footprint"]
    with rasterio.open(path) as src:
        if (src.count != 1 or src.shape != geom["shape"] or src.crs != geom["crs"]
                or src.transform != geom["transform"]):
            raise ValueError(f"incompatible geometry: {path}")
        if src.driver != "GTiff" or len(src.files) != 1:
            raise ValueError(f"historical support has external sidecars or is not a GeoTIFF: {path}")
        a = src.read(1)
        if not (src.read_masks(1)[fp] != 0).all():
            raise ValueError(f"masked historical support inside footprint: {path}")
    v = a[fp]
    if not np.isfinite(v).all() or not np.isin(v, [0, 1]).all():
        raise ValueError(f"historical support is not binary and finite inside footprint: {path}")
    support = (a > 0) & fp
    if not support.any():
        raise ValueError(f"empty historical support: {path}")
    return support


def audit(data_dir: Path) -> dict:
    manifest = load_manifest()
    entries = {e["id"]: e for e in manifest["files"]}
    for e in manifest["files"]:
        if sha256_file(data_dir / e["destination"]) != e["sha256"]:
            raise ValueError(f"pinned SHA-256 mismatch: {e['id']}")
    template = data_dir / entries["template"]["destination"]
    geom = template_geometry(template)
    fp = geom["footprint"]
    focus = [e for e in manifest["files"] if e["group"] == "focus"]
    if len(focus) != 9 or len({e["id"] for e in focus}) != 9:
        raise ValueError("the frozen focus audit must contain nine distinct sites")
    supports = {e["id"]: load_support(data_dir / e["destination"], geom) for e in focus}
    lattice = load_support(data_dir / entries["lattice"]["destination"], geom)
    with rasterio.open(data_dir / entries["labels"]["destination"]) as src:
        if src.count != 1 or src.shape != geom["shape"] or src.crs != geom["crs"] or src.transform != geom["transform"]:
            raise ValueError("label grid mismatch")
        if src.driver != "GTiff" or len(src.files) != 1:
            raise ValueError("label mirror has external sidecars or is not a GeoTIFF")
        label_arr = src.read(1)
        if not (src.read_masks(1)[fp] != 0).all():
            raise ValueError("label mirror contains masked pixels inside footprint")
    if not np.isin(label_arr[fp], [0, 1]).all():
        raise ValueError("invalid label mirror inside footprint")
    labels = (label_arr == 1) & fp

    pairs = []
    # Reuse each reference EDT. Within-three is directional: candidate -> reference.
    for ref in focus:
        peer = supports[ref["id"]]
        distances = distance_transform_edt(~peer)
        for e in focus:
            if e["id"] == ref["id"]:
                continue
            candidate = supports[e["id"]]
            rho = binary_spearman(candidate, peer, fp)
            within = int((distances[candidate] <= 3).sum())
            count = int(candidate.sum())
            fraction = within / count
            pairs.append({
                "candidate": e["id"], "reference": ref["id"],
                "candidate_positive_pixels": count,
                "candidate_within_3px_count": within,
                "candidate_within_3px_fraction": fraction,
                "spearman_binary_footprint": rho,
                "rank_measurable": rho is not None,
                "literal_duplicate": (rho is not None and rho > 0.90) or fraction > 0.70,
            })
    if len(pairs) != 72:
        raise ValueError("incomplete directed comparison")
    lattice_distance = distance_transform_edt(~lattice)
    rows = []
    for e in focus:
        cand = supports[e["id"]]
        directed = [p for p in pairs if p["candidate"] == e["id"]]
        strongest = max(directed, key=lambda p: p["candidate_within_3px_fraction"])
        report = validate_tif(data_dir / e["destination"], template)
        rows.append({
            "site": e["id"],
            "historical_mirror_name": Path(e["path"]).name,
            "historical_mirror_sha256": e["sha256"],
            "historical_mirror_source": f"https://github.com/{e['repo']}/blob/{e['ref']}/{e['path']}",
            "site_url": e["site_url"],
            "claim": e["claim"], "claim_class": e["claim_class"],
            "candidate_positive_pixels": int(cand.sum()),
            "max_directed_overlap": strongest,
            "all_eight_comparisons_duplicate": all(p["literal_duplicate"] for p in directed),
            "lattice_within_3px_fraction": float((lattice_distance[cand] <= 3).mean()),
            "local_official_profile_pass": report["local_official_profile_pass"],
            "raw_whole_array_finite_range_pass": report["raw_whole_array_finite_range_pass"],
            "outside_null_or_nan": report["checks"]["outside_null_or_nan"],
            "submission_approved": False,
        })
    d25 = supports["GEMSDOE25"]
    d30 = supports["GEMSDOE30"]
    b1 = supports["GEMSDOE31"]
    b2 = supports["GEMSDOE32"]
    distance_cat = distance_transform_edt(~labels)
    pred_b1, pred_b2 = d25 & (distance_cat > 1), d25 & (distance_cat > 2)
    spotchecks = []
    for e in (entry for entry in manifest["files"] if entry["group"] == "spotcheck"):
        support = load_support(data_dir / e["destination"], geom)
        nearby = int((lattice_distance[support] <= 3).sum())
        count = int(support.sum())
        spotchecks.append({
            "site": e["site"], "file": Path(e["path"]).name,
            "sha256": e["sha256"],
            "source": f"https://github.com/{e['repo']}/blob/{e['ref']}/{e['path']}",
            "owner_page_claim": e["owner_page_claim"],
            "candidate_positive_pixels": count,
            "within_3px_of_lattice_count": nearby,
            "within_3px_of_lattice_fraction": nearby / count,
            "literal_duplicate": 10 * nearby > 7 * count,
            "decision": "DO NOT SUBMIT" if 10 * nearby > 7 * count else "NOT ASSESSED",
        })
    return {
        "evidence_class": "COMPUTED — pixel comparisons only; claims are USER-REPORTED / UNVERIFIED",
        "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Nine pinned historical owner mirrors only, not the current full registry; no original upload or receipt authenticated.",
        "not_a_score_or_forecast": True,
        "template_sha256": entries["template"]["sha256"],
        "labels_sha256": entries["labels"]["sha256"],
        "witness_sha256": entries["lattice"]["sha256"],
        "n_directed_comparisons": len(pairs),
        "min_directed_3px_overlap": min(p["candidate_within_3px_fraction"] for p in pairs),
        "all_directed_comparisons_duplicate": all(p["literal_duplicate"] for p in pairs),
        "rows": rows,
        "comparisons": pairs,
        "spotchecked_promotions": spotchecks,
        "forensics": {
            "d25_vs_d30_support_xor_pixels": int((d25 ^ d30).sum()),
            "d25_minus_within_1px_vs_gems31_xor_pixels": int((pred_b1 ^ b1).sum()),
            "d25_minus_within_2px_vs_gems32_xor_pixels": int((pred_b2 ^ b2).sum()),
            "d25_to_b1_removed_pixels": int((d25 & ~b1).sum()),
            "b1_to_b2_removed_pixels": int((b1 & ~b2).sum()),
            "label_positive_pixels": int(labels.sum()),
            "interpretation": "Support relations are reproducible but cannot establish hidden-label causality or uploaded-file identity.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--out", type=Path, default=ROOT / "evidence" / "focus_audit.json")
    args = parser.parse_args()
    try:
        inputs = [MANIFEST, *[args.data_dir / e["destination"] for e in load_manifest()["files"]]]
        protect_inputs(args.out, inputs)
        result = audit(args.data_dir)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(f"Wrote {args.out}: {result['n_directed_comparisons']} directed comparisons; "
              f"minimum overlap {result['min_directed_3px_overlap']:.4%}.")
        print(json.dumps(result["forensics"], indent=2))
        return 0
    except (OSError, KeyError, ValueError, rasterio.errors.RasterioError) as exc:
        print(f"Audit failed closed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
