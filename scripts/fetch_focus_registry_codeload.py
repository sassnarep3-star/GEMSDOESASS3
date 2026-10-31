#!/usr/bin/env python3
"""Fetch the nine focus-site registry rasters via codeload.github.com tarballs.

Why this exists: the API-based fetcher (scripts/fetch_registry_rasters.py) exhausted the
unauthenticated GitHub API rate limit when run with many workers. codeload.github.com serves
repository tarballs under a separate, much higher limit and is on the sandbox's allow-list.
This script downloads each repo once, extracts only the .tif files named in
registry/focus_registry_manifest.json, verifies the SHA-256 pin, and writes a receipt.

Output: .cache/focus_registry/<basename>  (git-ignored) and evidence/focus_registry_fetch_20261031.json
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "focus_registry_manifest.json"
OUT_DIR = ROOT / ".cache" / "focus_registry"
RECEIPT = ROOT / "evidence" / "focus_registry_fetch_20261031.json"
OWNER = "buffedlizard55-lab"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def download_tarball(repo: str) -> bytes:
    url = f"https://codeload.github.com/{OWNER}/{repo}/tar.gz/refs/heads/main"
    out = subprocess.run(["curl", "-sL", url], capture_output=True, check=True, timeout=600)
    return out.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    entries = [e for e in manifest["rasters"] if e["repo"] != "HISTORICAL_SCORED"]
    by_repo: dict[str, list[dict]] = {}
    for e in entries:
        by_repo.setdefault(e["repo"], []).append(e)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    seen: set[str] = set()
    for repo, ents in sorted(by_repo.items()):
        try:
            blob = download_tarball(repo)
        except Exception as exc:  # noqa: BLE001
            for e in ents:
                results.append({"repo": repo, "path": e["path"], "status": "tarball_error", "error": str(exc)[:200]})
            continue
        try:
            tf = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
        except Exception as exc:  # noqa: BLE001
            for e in ents:
                results.append({"repo": repo, "path": e["path"], "status": "tar_open_error", "error": str(exc)[:200]})
            continue
        # map basename -> member
        members = {}
        for m in tf.getmembers():
            if m.isfile() and m.name.lower().endswith(".tif"):
                members.setdefault(Path(m.name).name, m)
        for e in ents:
            base = Path(e["path"]).name
            if base in seen:
                results.append({"repo": repo, "path": e["path"], "status": "duplicate_basename_skipped"})
                continue
            seen.add(base)
            if base not in members:
                results.append({"repo": repo, "path": e["path"], "status": "not_in_tarball"})
                continue
            data = tf.extractfile(members[base]).read()
            got = sha256_bytes(data)
            if got != e["sha256"]:
                results.append({"repo": repo, "path": e["path"], "status": "sha_mismatch",
                                "expected": e["sha256"], "got": got})
                continue
            dest = OUT_DIR / base
            dest.write_bytes(data)
            results.append({"repo": repo, "path": e["path"], "status": "fetched",
                            "sha256": got, "bytes": len(data)})
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": "registry/focus_registry_manifest.json",
        "fetcher": "scripts/fetch_focus_registry_codeload.py (codeload tarballs)",
        "n_manifest_rasters": len(entries),
        "n_fetched": counts.get("fetched", 0),
        "status_counts": counts,
        "results": results,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(counts, indent=1))
    bad = [r for r in results if r["status"] in ("sha_mismatch", "tarball_error", "tar_open_error")]
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
