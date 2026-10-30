#!/usr/bin/env python3
"""Fetch and SHA-verify the pinned sibling-site submission rasters used for the lane check.

The registry manifest ``registry/sibling_registry_manifest_20261028.json`` pins 460 GeoTIFFs
(454 submissions + 6 calibration lattices) from the nine focus-site repositories
(buffedlizard55-lab/GEMSDOE{24,25,27,28,30,31,32,33,36}) at a specific commit.  The lane rule of
the parallel-run protocol ("no more than 70% of your dots within 3 px of any registry raster,
rank correlation <= 0.90") can only be evaluated on bytes we can reproduce, so this script
downloads each pinned file through the GitHub contents API and keeps it only when the recomputed
SHA-256 equals the pin.

Outputs
-------
* ``.cache/registry_rasters/<repo>/<basename>`` - the verified rasters (git-ignored scratch)
* ``evidence/registry_siblings_fetch_receipt.json`` - tracked receipt (fetched/cached/failed/mismatch)
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
sys.path.insert(0, str(ROOT / "scripts"))


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch_one(repo: str, ref: str, entry: dict, out_dir: Path) -> dict:
    path = entry["path"]
    parts = Path(path).parts
    sub = Path(*parts[1:]) if len(parts) > 1 else Path(parts[-1])  # strip the leading repo directory
    dest = out_dir / repo / sub
    if dest.exists() and sha256_bytes(dest.read_bytes()) == entry["sha256"]:
        return {"repo": repo, "path": path, "status": "cached", "sha256": entry["sha256"]}
    api_path = str(sub)
    cmd = ["gh", "api", f"repos/buffedlizard55-lab/{repo}/contents/{api_path}?ref={ref}",
           "-H", "Accept: application/vnd.github.raw"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=180)
        if r.returncode != 0:
            return {"repo": repo, "path": path, "status": "failed", "error": r.stderr.decode()[:200]}
        got = sha256_bytes(r.stdout)
        if got != entry["sha256"]:
            return {"repo": repo, "path": path, "status": "hash_mismatch", "expected": entry["sha256"], "got": got}
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.stdout)
        return {"repo": repo, "path": path, "status": "fetched", "sha256": got, "bytes": len(r.stdout)}
    except Exception as exc:  # noqa: BLE001 - receipt must record any failure
        return {"repo": repo, "path": path, "status": "error", "error": repr(exc)[:200]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default=str(ROOT / "registry/sibling_registry_manifest_20261028.json"))
    ap.add_argument("--out-dir", default=str(ROOT / ".cache/registry_rasters"))
    ap.add_argument("--receipt", default=str(ROOT / "evidence/registry_siblings_fetch_receipt.json"))
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    man = json.loads(Path(args.manifest).read_text())
    out_dir = Path(args.out_dir)
    jobs = []
    for f in man["files"]:
        repo = f["path"].split("/")[0]
        ref = man["source_repos"][repo]["commit"]
        jobs.append((repo, ref, f))
    results = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(fetch_one, repo, ref, e, out_dir) for repo, ref, e in jobs]
        for i, fut in enumerate(cf.as_completed(futs), 1):
            results.append(fut.result())
            if i % 25 == 0:
                print(f"{i}/{len(jobs)} done", flush=True)
    tally: dict[str, int] = {}
    for r in results:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "manifest": str(Path(args.manifest).relative_to(ROOT)),
        "n_jobs": len(jobs),
        "tally": tally,
        "out_dir": str(out_dir.relative_to(ROOT)) if str(out_dir).startswith(str(ROOT)) else str(out_dir),
        "problems": [r for r in results if r["status"] not in ("fetched", "cached")],
    }
    Path(args.receipt).write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({"tally": tally, "receipt": args.receipt}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
