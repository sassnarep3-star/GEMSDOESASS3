#!/usr/bin/env python3
"""Audit committed candidate rasters against the competition format and the lattice rule.

For each raster given on the command line (default: the LWST archive and the BGK-PBE file on main) this measures:

* grid: CRS, shape, transform, band count, dtype (must be EPSG:32611, 3730 x 3292, the sample geotransform, 1, float32);
* footprint: finite cells of the organizer sample_submission.tif (the scored region);
* NaN inside the footprint, values inside [0, 1];
* outside the footprint: non-null cells and non-zero cells. The competition text says "data outside the bounds is
  null or nan"; zeros are the convention used by the owner-scored files, so they are reported separately;
* positive cells (> 0) inside and outside the footprint. Cells outside the footprint cannot be scored;
* literal lattice overlap: the share of ALL positive cells within 3 px of a lattice dot (the literal count), and the
  same share over positive cells INSIDE the footprint only;
* sampled Spearman rank correlation against the lattice (surface check, Protocol Rule 1).

Writes evidence/candidate_format_audit_20261029.json. Needs the restored data (`python scripts/restore_data.py`).
Labels: REGISTRY-MEASUREMENT only. No holdout, no organizer score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_CRS = "EPSG:32611"
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
LATTICE_REL = "scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LATTICE_SHA = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
DEFAULT = [
    "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif",
    "docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif",
]
N_SAMPLE = 300_000
SEED = 20261028


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", default=DEFAULT)
    ap.add_argument("--data", default=str(ROOT / ".cache/gems_data"))
    ap.add_argument("--out", default=str(ROOT / "evidence/candidate_format_audit_20261029.json"))
    args = ap.parse_args()
    data = Path(args.data)

    lat_path = data / LATTICE_REL
    if sha256_file(lat_path) != LATTICE_SHA:
        raise SystemExit("lattice SHA-256 mismatch")
    with rasterio.open(data / "sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(lat_path) as s:
        L = s.read(1)
    lat = np.isfinite(L) & (L > 0)
    near = ndi.distance_transform_edt(~lat) <= 3.0  # within 3 px of a lattice dot (Euclidean)
    rng = np.random.default_rng(SEED)
    samp = rng.choice(np.flatnonzero(foot.ravel()), size=min(N_SAMPLE, int(foot.sum())), replace=False)

    rows = []
    for rel in args.paths:
        p = ROOT / rel if not Path(rel).is_absolute() else Path(rel)
        with rasterio.open(p) as s:
            arr = s.read(1)
            meta = dict(crs=s.crs.to_string(), shape=list(s.shape), transform=list(s.transform)[:6],
                        count=s.count, dtype=s.dtypes[0], nodata=s.nodata)
        grid_ok = (meta["crs"] == EXPECTED_CRS and tuple(meta["shape"]) == EXPECTED_SHAPE
                   and tuple(meta["transform"]) == EXPECTED_TRANSFORM and meta["count"] == 1 and meta["dtype"] == "float32")
        fin = np.isfinite(arr)
        in_f = arr[foot]
        out_f = arr[~foot]
        pos = fin & (arr > 0)
        pos_in = pos & foot
        pos_out = pos & ~foot
        ov_all = float((pos & near).sum() / pos.sum()) if pos.any() else 0.0
        ov_in = float((pos_in & near).sum() / pos_in.sum()) if pos_in.any() else 0.0
        rho = spearmanr(np.nan_to_num(arr.ravel()[samp]).astype(np.float64),
                        lat.ravel()[samp].astype(np.float64)).statistic
        row = dict(
            path=rel,
            sha256=sha256_file(p),
            bytes=p.stat().st_size,
            grid=dict(meta, grid_ok=bool(grid_ok)),
            footprint=dict(
                nan_inside=int(np.isnan(in_f).sum()),
                values_0_1_inside=bool(np.isfinite(in_f).all() and (in_f >= 0).all() and (in_f <= 1).all()),
                outside_nonnull=int(np.isfinite(out_f).sum()),
                outside_nonzero=int(np.count_nonzero(np.isfinite(out_f) & (out_f != 0))),
            ),
            positive_cells=dict(total=int(pos.sum()), inside_footprint=int(pos_in.sum()),
                                outside_footprint=int(pos_out.sum()),
                                hard_value_1_inside=int((fin & foot & (arr >= 0.999999)).sum()),
                                hard_value_1_outside=int((fin & ~foot & (arr >= 0.999999)).sum())),
            lattice=dict(
                overlap_all_positive_cells=round(ov_all, 6),
                overlap_inside_footprint=round(ov_in, 6),
                spearman_vs_lattice_sampled=round(float(rho), 6),
            ),
        )
        row["verdict"] = dict(
            format_ok=bool(grid_ok and row["footprint"]["nan_inside"] == 0 and row["footprint"]["values_0_1_inside"]
                           and row["footprint"]["outside_nonzero"] == 0),
            outside_bounds_null_or_nan_strict=bool(row["footprint"]["outside_nonnull"] == 0),
            outside_bounds_no_positive_cells=bool(row["positive_cells"]["outside_footprint"] == 0),
            literal_lattice_rule_on_all_dots=bool(ov_all <= 0.70 and abs(rho) <= 0.90),
            literal_lattice_rule_inside_footprint=bool(ov_in <= 0.70 and abs(rho) <= 0.90),
        )
        rows.append(row)
        print(f"{rel}: grid_ok={grid_ok} outside_nonzero={row['footprint']['outside_nonzero']:,} "
              f"positive_out={row['positive_cells']['outside_footprint']:,} overlap_all={ov_all:.4f} "
              f"overlap_inside={ov_in:.4f} rho={rho:.4f}", flush=True)

    out = dict(
        schema_version=1,
        generated_by="scripts/candidate_format_audit.py",
        evidence_class="REGISTRY-MEASUREMENT (format, footprint, lattice overlap, rank correlation). No holdout, no organizer score.",
        footprint_cells=int(foot.sum()),
        lattice=dict(path=f"data/{LATTICE_REL}", sha256=LATTICE_SHA),
        competition_rule_text="data outside the bounds is null or nan (competition page 967, submission format)",
        candidates=rows,
    )
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
