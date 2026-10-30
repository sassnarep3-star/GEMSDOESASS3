#!/usr/bin/env python3
"""Download the nine-site focus registry (386 valid rasters) for the uniqueness gate.

Reads ``registry/focus_registry_manifest.json`` (built on main from the nine public
sibling repositories named in the owner's prompt) and materialises every raster into
``--out`` (default ``.cache/focus_registry``), verifying the recorded SHA-256.

Network: api.github.com via the authenticated ``gh`` CLI only.  Nothing is written
inside the repository tree.

Usage
-----
    python scripts/fetch_focus_registry.py --out .cache/focus_registry \
        --receipt evidence/focus_registry_fetch_20261030.json --jobs 6
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(repo: str, path: str, dest: Path, want: str) -> tuple[str, str]:
    if dest.exists() and sha256_file(dest) == want:
        return ("present", want)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    with tmp.open("wb") as fh:
        r = subprocess.run(
            ["gh", "api", f"repos/buffedlizard55-lab/{repo}/contents/{path}",
             "-H", "Accept: application/vnd.github.raw"],
            stdout=fh, stderr=subprocess.PIPE,
        )
    if r.returncode != 0:
        tmp.unlink(missing_ok=True)
        return ("fetch_failed", want)
    got = sha256_file(tmp)
    if got != want:
        tmp.unlink(missing_ok=True)
        return ("hash_mismatch", got)
    tmp.replace(dest)
    return ("fetched", got)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / ".cache" / "focus_registry")
    ap.add_argument("--manifest", type=Path,
                    default=ROOT / "registry" / "focus_registry_manifest.json")
    ap.add_argument("--receipt", type=Path,
                    default=ROOT / "evidence" / "focus_registry_fetch_20261030.json")
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()

    man = json.loads(args.manifest.read_text())
    rasters = man["rasters"]
    rows = []
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futs = {}
        for r in rasters:
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{r['repo']}__{Path(r['path']).name}")
            dest = args.out / safe
            futs[pool.submit(fetch, r["repo"], r["path"], dest, r["sha256"])] = (r, dest)
        for fut in cf.as_completed(futs):
            r, dest = futs[fut]
            status, got = fut.result()
            rows.append({"repo": r["repo"], "path": r["path"], "sha256": r["sha256"],
                         "local": str(dest), "status": status, "got_sha256": got})
    ok = [x for x in rows if x["status"] in ("fetched", "present")]
    print(f"verified {len(ok)}/{len(rows)} rasters")
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps({
        "schema_version": 1,
        "source_manifest": str(args.manifest.relative_to(ROOT)),
        "n_requested": len(rows), "n_verified": len(ok),
        "label": "MEASURED (SHA-256 verified local copies of the public sibling rasters)",
        "rows": sorted(rows, key=lambda x: (x["repo"], x["path"])),
    }, indent=1) + "\n")
    return 0 if len(ok) == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
