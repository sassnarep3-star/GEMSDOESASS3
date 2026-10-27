#!/usr/bin/env python3
"""Run synthetic probes of the unmodified, pinned shared GEMSDOE32 template.

No model is fitted, no competition prediction is emitted, and no template code
is copied or patched. These probes are not a substitute for an upstream fix.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import numpy as np
import rasterio
from rasterio.transform import from_origin

from restore_audit_inputs import sha256_file

ROOT = Path(__file__).resolve().parents[1]
PIN = "1398109a23f04a2ace71c1bd2f527cfba87860b5"


def probe(template: Path) -> dict:
    commit = subprocess.run(["git", "-C", str(template), "rev-parse", "HEAD"],
                            check=True, capture_output=True, text=True).stdout.strip()
    if commit != PIN:
        raise ValueError(f"expected unmodified template commit {PIN}; got {commit}")
    status = subprocess.run(["git", "-C", str(template), "status", "--porcelain", "--untracked-files=all"],
                            check=True, capture_output=True, text=True).stdout
    if status.strip():
        raise ValueError("upstream template worktree is not clean; refusing to label it unmodified")
    files = ("scripts/submission_writer.py", "scripts/evaluate_holdout.py", "src/gems32/holdout.py", "src/gems32/release_gate.py")
    hashes = {f: sha256_file(template / f) for f in files}
    sys.path.insert(0, str(template / "src"))
    spec = importlib.util.spec_from_file_location("upstream_submission_writer", template / "scripts/submission_writer.py")
    if spec is None or spec.loader is None:
        raise ValueError("could not load upstream writer")
    writer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(writer)
    forwarded = {}

    class Captured(Exception):
        pass

    def capture(**kwargs):
        forwarded["mask"] = kwargs["mask"].astype(int).tolist()
        raise Captured()

    # Intercept only in memory; never alter a template file.
    original = writer.submission.write_submission_pair
    writer.submission.write_submission_pair = capture
    try:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            profile = dict(driver="GTiff", height=2, width=2, count=1, dtype="float32",
                           crs="EPSG:32611", transform=from_origin(0, 200, 100, 100))
            for filename in ("sample_submission.tif", "labels.tif"):
                with rasterio.open(directory / filename, "w", **profile) as dst:
                    dst.write(np.zeros((2, 2), np.float32), 1)
            try:
                writer.write_validated_submission(np.array([[0.2, 1.2], [np.nan, -0.1]], dtype=np.float32),
                                                  "synthetic", {}, ddir=directory, out_dir=directory)
            except Captured:
                pass
    finally:
        writer.submission.write_submission_pair = original

    from gems32.holdout import PreparedCell, evaluate_hide_and_recover
    shape = (16, 16)
    foot = np.ones(shape, bool)
    cells, predictions = [], {}
    for seed in (20, 21):
        for fold in range(4):
            key = f"draw{seed}_fold{fold}"
            empty = np.array([], dtype=int)
            cells.append(PreparedCell(key=key, fold=fold, seed=seed,
                bbox=(slice(0, shape[0]), slice(0, shape[1])), active_sub=foot,
                truth_coords=(empty, empty), k_dg_sub=np.zeros(shape), n_truth=0))
            predictions[key] = np.zeros(shape, bool)
    predictions[cells[0].key][3, 3] = True
    result = evaluate_hide_and_recover(predictions, SimpleNamespace(foot=foot, cells=cells), grid_n=2, n_boot=20)
    fold_fp = sum(row["fp"] for row in result["folds"].values())
    pooled_fp = float(result["_block_totals"][1].sum())

    from gems32.release_gate import compare_registry
    rng = np.random.default_rng(27)
    dots = np.zeros(shape, bool)
    dots[4, 4] = dots[11, 11] = True
    gate = compare_registry(rng.random(shape), dots, foot, {"peer": (rng.random(shape), dots)}, stage="surface")
    if (forwarded.get("mask") != [[1, 1], [0, 0]] or fold_fp != 1.0 or pooled_fp != 0.0
            or gate["comparisons"][0]["within_3px_fraction"] != 1.0 or gate["passed"] is not True):
        raise ValueError("probe outcome differs from the recorded reproductions; do not report the old findings")
    return {
        "kind": "synthetic software probes; no geological experiment or score",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "template_repository": "https://github.com/buffedlizard55-lab/GEMSDOE32",
        "template_commit": commit,
        "source_sha256": hashes,
        "writer": {
            "input": [[0.2, 1.2], ["NaN", -0.1]],
            "forwarded_binary_mask": forwarded.get("mask"),
            "issue": "https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37",
            "warning": "Entry point silently thresholds probabilities and malformed inputs; no TIFF was written.",
        },
        "empty_truth_holdout": {
            "fold_false_positive_mass": fold_fp, "pooled_block_false_positive_mass": pooled_fp,
            "issue": "https://github.com/buffedlizard55-lab/GEMSDOE32/issues/41",
            "warning": "Empty-truth prediction mass is absent from pooled block terms in this probe.",
        },
        "surface_gate": {
            "preview_dot_overlap": gate["comparisons"][0]["within_3px_fraction"],
            "gate_returned_pass": gate["passed"],
            "issue": "https://github.com/buffedlizard55-lab/GEMSDOE32/issues/42",
            "warning": "Surface-stage gate returned pass despite identical preview dots in this probe.",
        },
        "upstream_write_access": False,
        "upstream_modified": False,
        "action": "Already reported upstream; read-only access prevents a shared fix. Fail closed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "evidence" / "upstream_probe.json")
    args = parser.parse_args()
    try:
        if args.out.resolve().is_relative_to(args.template_dir.resolve()):
            raise ValueError("probe output must not be written inside the shared template")
        record = probe(args.template_dir)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps(record, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Upstream probe failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
