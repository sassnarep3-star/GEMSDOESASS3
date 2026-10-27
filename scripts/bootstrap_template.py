#!/usr/bin/env python3
"""Fetch the unmodified shared template and hash-pinned owner data mirrors.

This script does not include credentials, data, or a private evaluator fork.
The bridges are public mirrors, NOT independently authenticated DrivenData data.
Data and source modules remain in .cache and are never committed. Some upstream
assembler calls still require gh; no upstream source files are changed here.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

from restore_audit_inputs import stream_github_raw

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
REPO = "buffedlizard55-lab/GEMSDOE32"
REF = "1398109a23f04a2ace71c1bd2f527cfba87860b5"
TEMPLATE = {
    "__init__.py": "bd7f12b45caf67b7b4d0da4656c7c3895513bec524ec0b7f251227ecbdd39d26",
    "evaluate_holdout.py": "ad86640b46f3c5fc6b1aceec4c4bfc82d03e35008b37ab2a8ad6076e6810ff3a",
    "grid.py": "b96df7ec0f33658a61b0baa5db85fcd19be2cd8b1873f99699bd26bddae8cd8d",
    "metric.py": "4afe10cbaa229948520c75194b1ebc32676e72544f05582f0725092b097b4d7f",
    "spatial.py": "fad7b09db9efc512247b9a176a7e7ce8631e287592b4e07902d0b9c38bed00f8",
    "holdout.py": "7a0a84176986190b527aa9c6a84216c2dab4b599f25b1143db5f420e85020ab1",
    "network.py": "d5e53d7df182e69bb22a6e39ac16f43d3f5b730e503d86538d5f8f7360020943",
    "gates.py": "7c57f70dbba58bb1112df4193a3de56516af0f981970d4b943b394f99b573dae",
    "submission_writer.py": "41220185ac2823fe5358603d38f2a915ea3e5f1ab1f94f0b237295b38b4a2565",
    "uniqueness.py": "1c5094b814277ae801ccea6a47cf744429cffcdc10f9cc79f229d5fc44a8df95",
    "validate.py": "e7849554b47f6a2b66aeb2f7cfd5db06267412f049f52a73f1c41f934a2c34dd",
    "prepare_data.py": "73c743e8ab7238b44ce82b9a8d4f9c7a17312fc023ee894ebd0e3788a456d7d6",
}
BRIDGE_HASHES = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_file(endpoint: str, dest: Path, expected: str) -> None:
    if dest.is_file() and sha256(dest) == expected:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".partial")
    try:
        with tmp.open("wb") as out:
            stream_github_raw(endpoint, out, timeout=180)
        digest = sha256(tmp)
        if digest != expected:
            raise ValueError(f"hash mismatch for {endpoint}: {digest} != {expected}")
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


def ensure_template() -> Path:
    parent = CACHE / "shared"
    for name, digest in TEMPLATE.items():
        fetch_file(f"repos/{REPO}/contents/vendor/gems57/{name}?ref={REF}",
                   parent / "gems57" / name, digest)
    return parent


def ensure_bridge(prepare) -> Path:
    """Use template's own five-part assembler, reusing verified local bytes."""
    runtime = CACHE / "runtime"
    official = runtime / "data" / "official"
    official.mkdir(parents=True, exist_ok=True)
    prior = CACHE / "bridge"
    for name, digest in BRIDGE_HASHES.items():
        dest = official / name
        if dest.exists():
            if sha256(dest) != digest:
                raise ValueError(f"existing data does not match pin: {dest}")
            continue
        saved = prior / name
        if saved.is_file() and sha256(saved) == digest:
            dest.symlink_to(os.path.relpath(saved, dest.parent))
        elif name == "training_features.tif":
            prepare.assemble_features(runtime)
        else:
            original = "example_submission.tif" if name == "sample_submission.tif" else name
            prepare.fetch_raw(prepare.BRIDGE_REPO, f"data/bridge/{original}", prepare.BRIDGE_COMMIT,
                              dest, digest)
    return runtime


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-bands", action="store_true", help="invoke the shared template's band cache builder")
    parser.add_argument("--template-only", action="store_true", help="fetch small shared source files, without data")
    args = parser.parse_args()
    sys.path.insert(0, str(ensure_template()))
    if args.template_only:
        print("Shared template pinned to", REF)
        return 0
    prepare = importlib.import_module("gems57.prepare_data")
    runtime = ensure_bridge(prepare)
    report_path = runtime / "evidence" / "feature_cache.json"
    if args.cache_bands:
        # Do not trust a stale, incomplete, or tampered band cache.
        valid_cache = False
        if report_path.is_file():
            report = json.loads(report_path.read_text())
            bands = report.get("bands", [])
            valid_cache = (len(bands) == 19 and report.get("source_sha256") == BRIDGE_HASHES["training_features.tif"]
                           and all((runtime / b["cache_file"]).is_file()
                                   and sha256(runtime / b["cache_file"]) == b["sha256"] for b in bands))
        if not valid_cache:
            report = prepare.cache_bands(runtime)
        print(f"Shared template cached {report['count']} bands under {runtime / '.cache' / 'features'}")
    print("Shared template pinned to", REF)
    print("Verified mirrored rasters:", runtime / "data" / "official")
    print("Mirror hash verification is not an organizer provenance receipt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
