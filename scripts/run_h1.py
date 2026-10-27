#!/usr/bin/env python3
"""Run one bounded H1 surface experiment using the unmodified shared evaluator.

A duplicate signal at the surface gate is a hard stop: no dots, TIFF, upload,
selection or later experiment is created. See the pre-registration for protocol.
"""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import numpy as np
import rasterio
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from bootstrap_template import BRIDGE_HASHES, ensure_template, fetch_file, sha256  # noqa: E402
from evidence_io import choose_output  # noqa: E402
from lane_h1 import make_fields  # noqa: E402

RUNTIME = ROOT / ".cache/runtime"
OUT = ROOT / "evidence/h1-run-card.json"
LATTICE = ROOT / ".cache/registry/r13-lattice.tif"
LATTICE_REPO = "buffedlizard55-lab/GEMSDOE24"
LATTICE_REF = "7ab1c8f77f0b4b8644e3929403a0dab65838b008"
LATTICE_PATH = "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LATTICE_SHA = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"


def write_card(card: dict, output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {output}")
    # Write privately, then link atomically without replacing an existing file.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=output.parent, prefix=".run-card-",
                                         suffix=".partial", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(card, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def require_lane_assignment(path: Path | None) -> dict:
    """Require an explicit coordinator assignment before re-running H1.

    This checks a caller-provided attestation, not the identity of its author.
    The original parallel run was provisional and is retained as negative evidence.
    """
    if path is None:
        raise ValueError("H1 is not an assigned lane; provide an explicit coordinator assignment before running")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(record, dict) or record.get("lane") != "H1" or record.get("assigned") is not True
            or not isinstance(record.get("assigned_by"), str) or not record["assigned_by"].strip()
            or not isinstance(record.get("method_paragraph"), str) or not record["method_paragraph"].strip()):
        raise ValueError("assignment must attest lane H1, assigned=true, assigned_by and a method paragraph")
    return record


def elapsed_guard(start: float) -> None:
    if time.monotonic() - start >= 7200:
        raise TimeoutError("two-hour experiment budget reached; stop")


def build_fold_crops(spatial, catalogue, footprint):
    """Keep compact fold crops and global block alignment; no truth-shaped crop."""
    result = []
    for fold in spatial.folds(catalogue, footprint, buffer_px=80):
        yy, xx = np.nonzero(fold["region"])
        if not len(yy):
            raise ValueError("empty holdout region")
        sl = np.s_[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
        cropped = {name: np.array(fold[name][sl], dtype=bool, copy=True)
                   for name in ("region", "visible", "truth")}
        result.append(dict(slice=sl, origin=(int(yy.min()), int(xx.min())),
                           fold=cropped, receipt=fold["receipt"]))
    return result


def leakage_canaries(features, support, folds, sample_size=100000, seed=20261027):
    """Each feature, each fold: positives vs sampled catalogue-zero proxies.

    The unlabeled negatives need not be true absences. AUC is a leakage alarm,
    not a competition score or calibrated measure of geological discrimination.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for f in folds:
        sl = f["slice"]
        fold = f["fold"]
        eligible = support[sl] & fold["region"] & ~fold["visible"]
        positive = np.flatnonzero(eligible & fold["truth"])
        negative = np.flatnonzero(eligible & ~fold["truth"])
        if not len(positive) or not len(negative):
            raise ValueError("AUC undefined: holdout fold has no positives or negatives")
        if len(negative) > sample_size:
            negative = rng.choice(negative, size=sample_size, replace=False)
        labels = np.concatenate((np.ones(len(positive), np.uint8), np.zeros(len(negative), np.uint8)))
        for name, feature in features.items():
            v = np.asarray(feature[sl]).ravel()
            values = np.concatenate((v[positive], v[negative]))
            if not np.isfinite(values).all():
                raise ValueError(f"non-finite feature in leakage canary: {name}")
            auc = float(roc_auc_score(labels, values))
            rows.append(dict(fold=int(f["receipt"]["fold"]), feature=name,
                             auc=auc, direction_free_auc=max(auc, 1.0 - auc),
                             positives=int(len(positive)), negative_proxies=int(len(negative))))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="new run-card path; never overwrites existing evidence")
    parser.add_argument("--assignment", type=Path, help="coordinator lane-assignment JSON; caller attestation, not authenticated")
    args = parser.parse_args()
    require_lane_assignment(args.assignment)
    output = choose_output(OUT, args.output)
    start = time.monotonic()
    sys.path.insert(0, str(ensure_template()))
    from gems57 import evaluate_holdout as evaluator, spatial, uniqueness

    sample = RUNTIME / "data/official/sample_submission.tif"
    labels_path = RUNTIME / "data/official/existing_faults.tif"
    training = RUNTIME / "data/official/training_features.tif"
    receipt_path = RUNTIME / "evidence/feature_cache.json"
    for p in (sample, labels_path, training, receipt_path):
        if not p.is_file():
            raise FileNotFoundError(f"{p}: run scripts/bootstrap_template.py --cache-bands")
    for p in (sample, labels_path, training):
        if sha256(p) != BRIDGE_HASHES[p.name]:
            raise ValueError(f"mirror hash mismatch: {p}")
    with rasterio.open(sample) as src, rasterio.open(labels_path) as lbl:
        if (src.shape, src.crs, src.transform) != (lbl.shape, lbl.crs, lbl.transform):
            raise ValueError("label/sample grid mismatch")
        footprint = np.isfinite(src.read(1))
        catalogue = (lbl.read(1) == 1) & footprint
        expected_grid = (src.shape, src.crs, src.transform)
    cache_report = json.loads(receipt_path.read_text())
    if cache_report.get("source_sha256") != BRIDGE_HASHES["training_features.tif"]:
        raise ValueError("feature cache source hash does not match the mirrored stack")
    cached = {int(b["band"]): b for b in cache_report["bands"]}
    for i in (2, 12):
        path = RUNTIME / cached[i]["cache_file"]
        if not path.is_file() or sha256(path) != cached[i]["sha256"]:
            raise ValueError(f"band {i} cache missing or altered")
    rtp = np.load(RUNTIME / cached[2]["cache_file"], mmap_mode="r")
    elev = np.load(RUNTIME / cached[12]["cache_file"], mmap_mode="r")
    print("[H1] constructing fixed label-free magnetic-displacement fields", flush=True)
    features, support = make_fields(rtp, elev, footprint)
    elapsed_guard(start)
    print("[H1] preparing whole-component spatial folds and leakage canaries", flush=True)
    folds = build_fold_crops(spatial, catalogue, footprint)
    # Test raw input bands as well as every derived field before trusting DTI.
    canaries = leakage_canaries({**features, "raw_rtp": rtp, "raw_detrended_elevation": elev}, support, folds)
    # Strong negative separation is just as suspicious as positive separation.
    max_auc = max(row["direction_free_auc"] for row in canaries)
    card = {
        "schema_version": "h1-run-card-v1", "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypothesis": "H1: displaced magnetic texture across a topographic break may indicate an unmapped fault",
        "mechanism": "Four directional comparisons of squared RTP patch mismatch with/without tangential shifts, gated by a cross-line detrended-elevation break; no fault catalogue feature",
        "named_non_fault_process": "Lithologic contacts or fluvially reworked magnetic sediment",
        "experiments_used": 1, "experiment_budget": 3, "weekly_slots_used": 0,
        "evidence_scope": "Owner-published bridge rasters; integrity verified, organizer provenance not independently authenticated. Canary negatives are unlabelled proxies.",
        "folds": [f["receipt"] for f in folds],
        "feature_canaries": {"type": "LEAKAGE-CANARY AUC, direction-free max(auc, 1-auc); diagnostic, not DTI", "max_auc": max_auc,
                             "limit": 0.90, "passed": max_auc <= 0.90, "rows": canaries},
        "holdout_dti": None, "correlation_overlap_vs_registry": None,
        "raster_sha256": None,
        "validator_output": {"status": "NOT RUN: no output raster created", "no_nan_inside": None,
                             "range_0_1": None, "crs_shape_transform_match": None},
        "submission_name": None,
        "note": "H1 displacement test; research only; no submission authorized.",
        "verdict": "negative", "ok_to_submit": False,
    }
    if max_auc > 0.90:
        card["stop_reason"] = "feature-only AUC exceeds leakage threshold; STOP"
        write_card(card, output)
        print(f"[H1] LEAKAGE CANARY STOP; evidence {output}; no output raster", flush=True)
        return 0
    elapsed_guard(start)
    print("[H1] scoring surface and two same-fold controls via shared evaluator", flush=True)
    surfaces = {"h1_surface": features["combined_surface"],
                "terrain_control": features["terrain_control"],
                "uniform_control": support.astype(np.float32) * np.float32(0.05)}
    terms_by_arm = {}
    fold_scores = {}
    for f in folds:
        sl = f["slice"]
        for name, arr in surfaces.items():
            ev, terms = evaluator.evaluate(arr[sl], f["fold"], footprint[sl], origin=f["origin"],
                                           global_shape=footprint.shape)
            terms_by_arm[name] = terms_by_arm.get(name, np.zeros_like(terms)) + terms
            fold_scores.setdefault(name, []).append(ev)
        elapsed_guard(start)
    summary = evaluator.pooled_summary(terms_by_arm, draws=1000, seed=20261027, candidate="h1_surface")
    summary["scope_note"] = ("Continuous pre-placement fields, not submitted dots. Withheld catalogue faults are a proxy, "
                             "and CI is conditional on these folds, not a leaderboard-score interval. "
                             "No same-evaluator prior holdout-best has been reproduced.")
    summary["fold_scores"] = fold_scores
    card["holdout_dti"] = summary
    # The surface itself must pass the literal gate. The pinned lattice is in
    # GEMSDOE32's public nine-site registry. One >threshold peer suffices to STOP.
    fetch_file(f"repos/{LATTICE_REPO}/contents/{LATTICE_PATH}?ref={LATTICE_REF}", LATTICE, LATTICE_SHA)
    with rasterio.open(LATTICE) as ds:
        if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != expected_grid:
            raise ValueError("registry lattice does not match the sample grid")
        reference = ds.read(1)
    print("[H1] checking surface against a registered lattice before any placement", flush=True)
    rho = uniqueness.surface_rho(surfaces["h1_surface"], reference, footprint)
    overlap = uniqueness.dot_overlap(surfaces["h1_surface"], reference, radius_px=3.0)
    rank = rho["spearman_full_footprint"]
    if not np.isfinite(rank):
        rank = None
    duplicate = bool((rank is not None and rank > 0.90) or overlap > 0.70)
    card["surface_sha256"] = hashlib.sha256(surfaces["h1_surface"].astype("<f4", copy=False).tobytes()).hexdigest()
    card["correlation_overlap_vs_registry"] = {
        "phase": "pre-placement surface support", "reference_repo": LATTICE_REPO,
        "reference_commit": LATTICE_REF, "reference_path": LATTICE_PATH,
        "reference_sha256": LATTICE_SHA, "full_footprint_spearman": rank,
        "fraction_of_positive_surface_within_3px": float(overlap),
        "thresholds": {"spearman_exceeds": 0.90, "overlap_exceeds": 0.70},
        "duplicate": duplicate,
        "scope": "Single pre-placement disqualifying peer. Not a complete registry scan; a pass cannot clear a candidate.",
        "final_dot_comparison": "NOT RUN: mandatory STOP before placement" if duplicate else "NOT RUN: complete registry scan required",
    }
    card["stop_reason"] = ("Surface exceeds literal registry threshold; STOP before placement"
                           if duplicate else "Surface has not been cleared against the full registry; STOP")
    card["runtime_seconds"] = round(time.monotonic() - start, 2)
    write_card(card, output)
    print(f"[H1] STOP: {card['stop_reason']}; overlap={overlap:.6f}, rho={rank}", flush=True)
    print(f"[H1] Evidence: {output}; no dots, TIFF, upload or slot used", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
