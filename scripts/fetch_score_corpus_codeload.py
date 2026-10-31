#!/usr/bin/env python3
"""Fetch the 128-raster score corpus via codeload.github.com tarballs (API rate-limit free).

Reads evidence/score_corpus_manifest_20261030.json, downloads each unique repo once as a
tarball, extracts only the matched .tif blobs, verifies the SHA-256 pin, and stores them
flat in .cache/gems_corpus/. Writes evidence/score_corpus_fetch_20261031.json.

The corpus is the supervision set for the leaderboard-inversion estimator; it is also the
set the uniqueness audit must check (the binding 65% raster is a corpus raster, not a
nine-site registry raster).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import io
import json
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence" / "score_corpus_manifest_20261030.json"
OUT_DIR = ROOT / ".cache" / "gems_corpus"
RECEIPT = ROOT / "evidence" / "score_corpus_fetch_20261031.json"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def download(repo: str) -> bytes:
    url = f"https://codeload.github.com/{repo}/tar.gz/refs/heads/main"
    return subprocess.run(["curl", "-sL", url], capture_output=True, check=True, timeout=600).stdout


def process_repo(repo: str, entries: list[dict]) -> list[dict]:
    out = []
    try:
        blob = download(repo)
        tf = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
    except Exception as exc:  # noqa: BLE001
        for e in entries:
            out.append({"repo": repo, "path": e.get("path"), "status": "download_error", "error": str(exc)[:200]})
        return out
    members = {}
    for m in tf.getmembers():
        if m.isfile() and m.name.lower().endswith(".tif"):
            members.setdefault(Path(m.name).name, m)
    for e in entries:
        path = e.get("path")
        if not path:
            out.append({"repo": repo, "path": path, "status": "unmatched"})
            continue
        base = Path(path).name
        if base not in members:
            out.append({"repo": repo, "path": path, "status": "not_in_tarball"})
            continue
        data = tf.extractfile(members[base]).read()
        got = sha256_bytes(data)
        if got != e["sha256"]:
            out.append({"repo": repo, "path": path, "status": "sha_mismatch", "expected": e["sha256"], "got": got})
            continue
        dest = OUT_DIR / base
        dest.write_bytes(data)
        out.append({"repo": repo, "path": path, "status": "fetched", "sha256": got, "bytes": len(data)})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    man = json.loads(MANIFEST.read_text())
    matched = [r for r in man["rows"] if r.get("status") == "matched" and r.get("path") and r.get("sha256")]
    by_repo: dict[str, list[dict]] = {}
    for r in matched:
        by_repo.setdefault(r["repo"], []).append(r)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_repo, repo, ents): repo for repo, ents in sorted(by_repo.items())}
        for f in cf.as_completed(futs):
            results.extend(f.result())
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": "evidence/score_corpus_manifest_20261030.json",
        "fetcher": "scripts/fetch_score_corpus_codeload.py (codeload tarballs)",
        "n_matched_entries": len(matched),
        "n_unique_repos": len(by_repo),
        "n_fetched": counts.get("fetched", 0),
        "status_counts": counts,
        "results": results,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(counts, indent=1))
    bad = [r for r in results if r["status"] in ("sha_mismatch", "download_error")]
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
