#!/usr/bin/env python3
"""Measure every focus-site file named in evidence/nine_sites_executive_audit.json from its sibling repo.

For each of the nine focus sites (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36) this fetches, through the
GitHub API (api.github.com):

* the historical best file (owner-reported score; already submitted, so not eligible), and
* the sibling's `latest_unique_candidate` file (its own verdict is recorded as a claim, not accepted).

Each file is checked programmatically (grid, CRS, dtype, finiteness, [0, 1] range, dot count) and
compared with: the 13GEMSDOE calibration lattice (literal Protocol Rule 1 witness), each other focus
historical file, and the LWST archive. Overlap is the protocol's forward measure: the fraction of
candidate dots within 3 px of a reference dot. Spearman is sampled, as in the uniqueness audit.

Output: evidence/focus_site_candidate_audit_20261028.json. Requires `gh` with read access and the
restored lattice in .cache/gems_data (run scripts/restore_data.py first).

No measured number here is an organizer score. Labels: OVERLAP and RHO are REGISTRY-MEASUREMENT;
owner scores are OWNER-REPORT (from the prompt); holdout values are NOT in this file, see evidence/nine_sites_executive_audit.json (HOLDOUT-DTI).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
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
OVERLAP_LIMIT = 0.70
RHO_LIMIT = 0.90
N_SAMPLE = 300_000
SEED = 20261028


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(repo: str, path: str, dest: Path) -> Path:
    """Download one file at the repo's default branch via the GitHub contents API."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    with tmp.open("wb") as fh:
        subprocess.run(
            ["gh", "api", f"repos/{repo}/contents/{path}", "-H", "Accept: application/vnd.github.raw"],
            stdout=fh,
            check=True,
        )
    tmp.replace(dest)
    return dest


def split_raw_url(url: str) -> tuple[str, str]:
    # https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}
    tail = url.split("raw.githubusercontent.com/", 1)[1]
    owner, repo, _head, path = tail.split("/", 3)
    return f"{owner}/{repo}", path


def load_grid(path: Path):
    with rasterio.open(path) as s:
        arr = s.read(1)
        meta = dict(
            crs=s.crs.to_string() if s.crs else None,
            shape=list(s.shape),
            transform=[round(float(x), 6) for x in list(s.transform)[:6]],
            dtype=s.dtypes[0],
            count=s.count,
            nodata=None if s.nodata is None else str(s.nodata),
        )
    return arr, meta


def near_map(dots: np.ndarray) -> np.ndarray:
    """Boolean map of cells within 3 px (Euclidean, inclusive) of any dot in `dots`."""
    return ndi.distance_transform_edt(~dots) <= 3.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sites-json", default=str(ROOT / "evidence/nine_sites_executive_audit.json"))
    ap.add_argument("--cache", default=str(ROOT / ".cache/sib/focus"))
    ap.add_argument("--data", default=str(ROOT / ".cache/gems_data"))
    ap.add_argument("--lwst", default=str(ROOT / "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif"))
    ap.add_argument("--out", default=str(ROOT / "evidence/focus_site_candidate_audit_20261028.json"))
    args = ap.parse_args()

    cache = Path(args.cache)
    data = Path(args.data)
    sites = json.loads(Path(args.sites_json).read_text())["sites"]
    foot = np.isfinite(load_grid(data / "sample_submission.tif")[0])
    foot_idx = np.flatnonzero(foot.ravel())

    # ---- reference set (dots = positive finite pixels, the inherited support definition) ----
    refs: dict[str, dict] = {}
    lat_arr, lat_meta = load_grid(data / LATTICE_REL)
    refs["LATTICE_13GEMSDOE"] = dict(dots=(np.isfinite(lat_arr) & (lat_arr > 0)), sha=sha256_file(data / LATTICE_REL), meta=lat_meta)
    lwst_arr, lwst_meta = load_grid(Path(args.lwst))
    refs["LWST_ARCHIVE"] = dict(dots=(np.isfinite(lwst_arr) & (lwst_arr > 0)), sha=sha256_file(Path(args.lwst)), meta=lwst_meta)
    for s in sites:
        repo, rel = split_raw_url(s["hist_download_url"])
        local = fetch(repo, rel, cache / f"hist_{s['site']}.tif")
        arr, meta = load_grid(local)
        refs[f"HIST_{s['site']}"] = dict(dots=(np.isfinite(arr) & (arr > 0)), sha=sha256_file(local), meta=meta,
                                         repo=repo, path=rel)

    # Near-maps are reused across all candidates (one distance transform per reference).
    near = {k: near_map(v["dots"]) for k, v in refs.items()}
    # Sampled pixels for rho (fixed seed, identical sample for every comparison).
    rng = np.random.default_rng(SEED)
    samp = rng.choice(foot_idx, size=min(N_SAMPLE, foot_idx.size), replace=False)

    results = []
    for s in sites:
        for role, key in (("historical_best", "hist"), ("latest_unique_candidate", "latest")):
            if role == "historical_best":
                url = s["hist_download_url"]
                name = s["hist_name"]
                owner_score = s["hist_score_owner_report"]
                verdict = "already submitted (owner-reported); not eligible"
            else:
                url = s["latest_download_url"]
                name = s["latest_name"]
                owner_score = None
                verdict = s["latest_site_verdict"]
            repo, rel = split_raw_url(url)
            local = fetch(repo, rel, cache / f"{key}_{s['site']}.tif")
            arr, meta = load_grid(local)
            dots = np.isfinite(arr) & (arr > 0)
            in_f = arr[foot]
            fmeta = dict(
                grid_match=(meta["crs"] == EXPECTED_CRS and tuple(meta["shape"]) == EXPECTED_SHAPE
                            and tuple(meta["transform"]) == EXPECTED_TRANSFORM),
                single_band=meta["count"] == 1,
                dtype=meta["dtype"],
                nan_in_footprint=int(np.isnan(in_f).sum()),
                finite_in_footprint=int(np.isfinite(in_f).sum()),
                footprint_px=int(foot.sum()),
                min_in_footprint=float(np.nanmin(in_f)) if np.isfinite(in_f).any() else None,
                max_in_footprint=float(np.nanmax(in_f)) if np.isfinite(in_f).any() else None,
                values_in_0_1_footprint=bool(np.isfinite(in_f).all() and (in_f >= 0).all() and (in_f <= 1).all()),
                values_in_0_1_whole_grid=bool(np.nanmin(arr) >= 0 and np.nanmax(arr) <= 1),
                # Competition text: "data outside the bounds is null or nan". Non-null outside cells are reported;
                # zeros outside are tolerated only because an owner-scored zeros file exists (see the review).
                outside_footprint_nonnull=int(np.isfinite(arr[~foot]).sum()),
                outside_footprint_nonzero=int(np.count_nonzero(np.isfinite(arr[~foot]) & (arr[~foot] != 0))),
                positive_cells_outside_footprint=int((dots & ~foot).sum()),
                positive_cells_inside_footprint=int((dots & foot).sum()),
            )
            dots_in = dots & foot
            row = dict(
                site=s["site"],
                role=role,
                file=name,
                source=f"https://github.com/{repo}/blob/HEAD/{rel}",
                sha256=sha256_file(local),
                dots=int(dots.sum()),
                owner_reported_score=owner_score,
                sibling_verdict_claimed=verdict,
                format=fmeta,
                overlap_within3px=dict(),
                spearman_sampled=dict(),
            )
            for rk, rv in refs.items():
                if rk.startswith("HIST_") and rk == f"HIST_{s['site']}" and role == "historical_best":
                    continue  # the file against itself
                row["overlap_within3px"][rk] = round(float(near[rk][dots].mean()) if dots.any() else 0.0, 6)
                # Same measure with dots outside the scored footprint removed (they cannot score).
                row.setdefault("overlap_within3px_inside_footprint", {})[rk] = (
                    round(float(near[rk][dots_in].mean()) if dots_in.any() else 0.0, 6))
            # Sampled Spearman against the lattice and the LWST archive (binary references).
            for rk in ("LATTICE_13GEMSDOE", "LWST_ARCHIVE"):
                ref_b = refs[rk]["dots"].ravel()[samp].astype(np.float64)
                cand_v = np.nan_to_num(arr.ravel()[samp].astype(np.float64))
                rho = spearmanr(cand_v, ref_b).statistic if cand_v.std() > 0 and ref_b.std() > 0 else float("nan")
                row["spearman_sampled"][rk] = None if np.isnan(rho) else round(float(rho), 6)
            results.append(row)
            print(f"{s['site']:9s} {role:24s} dots={row['dots']:6d} grid={fmeta['grid_match']} "
                  f"lattice={row['overlap_within3px']['LATTICE_13GEMSDOE']:.4f} "
                  f"maxHistPeer={max(v for k, v in row['overlap_within3px'].items() if k.startswith('HIST_')):.4f}",
                  flush=True)

    # ---- per-candidate verdicts under both readings (literal = lattice included) ----
    def verdict_for(row: dict) -> dict:
        ov = row["overlap_within3px"]
        hist_peer = {k: v for k, v in ov.items() if k.startswith("HIST_") and k != f"HIST_{row['site']}"}
        dot_field_ok = all(v <= OVERLAP_LIMIT for v in hist_peer.values()) and ov["LWST_ARCHIVE"] <= OVERLAP_LIMIT
        literal_ok = dot_field_ok and ov["LATTICE_13GEMSDOE"] <= OVERLAP_LIMIT
        rho_ok = all(v is None or abs(v) <= RHO_LIMIT for v in row["spearman_sampled"].values())
        return dict(
            format_ok=bool(row["format"]["grid_match"] and row["format"]["single_band"] and row["format"]["nan_in_footprint"] == 0
                           and row["format"]["values_in_0_1_footprint"] and row["format"]["outside_footprint_nonzero"] == 0),
            outside_bounds_null_or_nan_strict=bool(row["format"]["outside_footprint_nonnull"] == 0),
            literal_rule_ok=bool(literal_ok and rho_ok),
            like_for_like_rule_ok=bool(dot_field_ok and rho_ok),
            max_overlap_vs_other_focus_hist=max(hist_peer.values()) if hist_peer else None,
            lattice_overlap=ov["LATTICE_13GEMSDOE"],
        )

    for row in results:
        row["verdict"] = verdict_for(row)

    out = dict(
        schema_version=1,
        evidence_class="REGISTRY-MEASUREMENT (overlap, rho, format). Owner scores are OWNER-REPORT.",
        thresholds=dict(overlap_within3px_max=OVERLAP_LIMIT, abs_spearman_max=RHO_LIMIT, radius_px=3.0),
        rule_readings=dict(
            literal="every registry raster incl. the 13GEMSDOE calibration lattice (Protocol Rule 1 text)",
            like_for_like="excludes the halo-saturated lattice from the dot-overlap test, as vendor/gems57/uniqueness.py classifies it; rho still applied to all",
        ),
        references={k: dict(sha256=v["sha"], dots=int(v["dots"].sum()), source=(f"https://github.com/{v['repo']}/blob/HEAD/{v['path']}" if "repo" in v else "local restore"))
                    for k, v in refs.items()},
        candidate_count=len(results),
        rows=results,
    )
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    sys.exit(main())
