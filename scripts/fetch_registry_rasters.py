#!/usr/bin/env python3
"""Fetch every raster listed in registry/focus_registry_manifest.json and verify its SHA-256.

Why: the uniqueness audits must run on bytes the repo can reproduce, not on paths in a
sandbox that no longer exists (the old audit read /tmp/sib and /tmp/ref_repos). Each file is
fetched from the GitHub REST API (api.github.com, default branch of buffedlizard55-lab/<repo>)
and kept only if its SHA-256 equals the manifest pin. Mismatches are written to the receipt
and are NOT used by the audit.

Output: .cache/registry_rasters/<repo>/<basename>  (git-ignored) and
        evidence/registry_fetch_receipt.json       (tracked).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "focus_registry_manifest.json"
OUT_DIR = ROOT / ".cache" / "registry_rasters"
RECEIPT = ROOT / "evidence" / "registry_fetch_receipt.json"
OWNER = "buffedlizard55-lab"


def repo_slug(repo: str) -> str:
    # Manifest uses short names (e.g. GEMSDOE24); HISTORICAL_SCORED entries carry their own repo.
    return f"{OWNER}/{repo}"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch_one(entry: dict) -> dict:
    repo = entry["repo"]
    path = entry["path"]
    dest = OUT_DIR / repo / Path(path).name
    if dest.exists() and sha256_bytes(dest.read_bytes()) == entry["sha256"]:
        return {"repo": repo, "path": path, "status": "cached", "sha256": entry["sha256"]}
    if repo == "HISTORICAL_SCORED":
        return {"repo": repo, "path": path, "status": "skipped_no_source_repo", "sha256": entry["sha256"]}
    cmd = [
        "gh", "api", f"repos/{repo_slug(repo)}/contents/{path}",
        "-H", "Accept: application/vnd.github.raw",
    ]
    try:
        data = subprocess.run(cmd, check=True, capture_output=True, timeout=300).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        return {"repo": repo, "path": path, "status": "fetch_error", "error": str(exc)[:200]}
    got = sha256_bytes(data)
    if got != entry["sha256"]:
        return {"repo": repo, "path": path, "status": "sha_mismatch", "expected": entry["sha256"], "got": got}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {"repo": repo, "path": path, "status": "fetched", "sha256": got, "bytes": len(data)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    entries = manifest["rasters"]
    results: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for r in ex.map(fetch_one, entries):
            results.append(r)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": "registry/focus_registry_manifest.json",
        "n_manifest_rasters": len(entries),
        "status_counts": counts,
        "note": "SHA-256 pins come from the manifest, which was built from owner-mirror checkouts. "
                "A pin match proves byte identity with the mirror, not organizer authentication.",
        "results": results,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(counts, indent=1))
    bad = [r for r in results if r["status"] in ("sha_mismatch", "fetch_error")]
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
