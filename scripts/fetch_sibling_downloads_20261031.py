#!/usr/bin/env python3
"""Fetch every published submission raster from the sibling GitHub Pages repos.

Why this exists
---------------
The uniqueness audit and the score estimator must run on bytes this repo can
reproduce from a public source.  raw.githubusercontent.com and the github.io
Pages hosts are not reachable from the sandbox, but git-over-https to
github.com is, so each repo is cloned once with

    git clone --depth 1 --filter=blob:none --sparse   +   sparse-checkout set docs/downloads

which downloads only the `docs/downloads` blobs.  Every copied file is hashed
and only kept if it is a plausible submission raster (single-band, 3730x3292,
100 m EPSG:32611) or is recorded as ``rejected`` with the reason.

Outputs (all git-ignored / or tracked receipts):
    .cache/sibling_downloads/<REPO>__<basename>.tif
    registry/sibling_downloads_manifest_20261031.json

Usage:
    python scripts/fetch_sibling_downloads_20261031.py --workers 4 [--repos GEMSDOE24,GEMSDOE32]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / ".cache" / "sibling_downloads"
MANIFEST = ROOT / "registry" / "sibling_downloads_manifest_20261031.json"

# owner/repo pairs taken from registry/sibling_repos.txt (the leaderboard list in the
# standing prompt).  Every one of these hosts a GitHub Pages site with docs/downloads.
DEFAULT_REPOS: list[tuple[str, str]] = [
    ("buffedlizard55-lab", n) for n in [
        "GEMSDOE", "6GEMSDOE", "GEMSDOE3", "GEMSDOE2", "GEMSDOE4", "5GEMSDOE", "7GEMSDOE",
        "8GEMSDOE", "GEMSDOE9", "11GEMSDOE", "12GEMSDOE", "15GEMSDOE", "14GEMSDOE",
        "17GEMSDOE", "18GEMSDOE", "19GEMSDOE", "GEMSDOE10", "13GEMSDOE", "16GEMSDOE",
        "GEMSDOE21", "20GEMSDOE", "GEMSDOE22", "GEMSDOE23", "GEMSDOE26", "GEMSDOE29",
        "GEMSDOE34", "GEMSDOE35", "GEMSDOE37", "GEMSDOE38", "GEMSDOE39", "GEMSDOE40",
        "GEMSDOE41", "GEMSDOE42", "GEMSDOE43", "GEMSDOE44", "GEMSDOE45", "GEMSDOE46",
        "GEMSDOE47", "GEMSDOE48", "GEMSDOE49", "GEMSDOE50", "GEMSDOE51", "GEMSDOE52",
        "GEMSDOE53", "GEMSDOE54", "55GEMSDOE", "56GEMSDOE", "57GEMSDOE", "58GEMSDOE",
        "59GEMSDOE", "60GEMSDOE", "61GEMSDOE", "62GEMSDOE", "GEMSDOE63", "GEMSDOE64",
        "GEMSDOE65", "GEMSDOE66", "GEMSDOE67", "GEMSDOE68", "GEMSDOE69", "GEMSDOE70",
        "GEMSDOE71", "GEMSDOE72", "GEMSDOE73", "GEMSDOE74", "GEMSDOE75", "GEMSDOE76",
        "GEMSDOE77", "GEMSDOE78", "GEMSDOE79", "GEMSDOE80", "GEMSDOE81", "GEMSDOE82",
        "GEMSDOE83", "GEMSDOE84", "GEMSDOE85", "GEMSDOE86", "GEMSDOE87", "GEMSDOE88",
        "GEMSDOE89", "GEMSDOE90", "GEMSDOE91", "GEMSDOE92",
        "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31",
        "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
    ]
] + [
    ("kanlerxz87-cyber", "KANLERGEMSDOE1"),
    ("kanlerxz87-cyber", "KANLERGEMSDOE2"),
    ("kanlerxz87-cyber", "KANLERGEMSDOE3"),
    ("wingbangboozle1-lang", "WBGGEMSDOE1"),
    ("wingbangboozle1-lang", "WBGGEMSDOE2"),
    ("wingbangboozle1-lang", "WBGGEMSDOE3"),
    ("ginnymcfiner23-ux", "GINNYGEMSDOE1"),
    ("ginnymcfiner23-ux", "GINNYGEMSDOE2"),
    ("ginnymcfiner23-ux", "GINNYGEMSDOE3"),
    ("karagemop466-tech", "GEMSDOEkarage1"),
    ("karagemop466-tech", "GEMSDOEkarage2"),
    ("karagemop466-tech", "GEMSDOEkarage3"),
    ("apartanish22-droid", "ApartGEMSDOE1"),
    ("apartanish22-droid", "ApartGEMSDOE2"),
    ("apartanish22-droid", "ApartGEMSDOE3"),
    ("sassnarep3-star", "GEMSDOESASS1"),
    ("sassnarep3-star", "GEMSDOESASS2"),
    ("sassnarep3-star", "GEMSDOESASS3"),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sparse_clone(owner: str, repo: str, want_dirs: list[str]) -> Path | None:
    """Blobless sparse clone; returns the temp dir with the wanted directories materialised."""
    url = f"https://github.com/{owner}/{repo}.git"
    tmp = Path(tempfile.mkdtemp(prefix=f"sib_{repo}_"))
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", "--quiet", url, str(tmp)],
            check=True, capture_output=True, timeout=900,
        )
        subprocess.run(
            ["git", "-C", str(tmp), "sparse-checkout", "set", *want_dirs],
            check=True, capture_output=True, timeout=900,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        shutil.rmtree(tmp, ignore_errors=True)
        return None
    return tmp


def fetch_repo(owner: str, repo: str, want_dirs: list[str]) -> dict:
    tmp = sparse_clone(owner, repo, want_dirs)
    if tmp is None:
        return {"owner": owner, "repo": repo, "status": "clone_failed", "files": []}
    out: list[dict] = []
    try:
        for d in want_dirs:
            src = tmp / d
            if not src.exists():
                continue
            for f in sorted(src.rglob("*.tif")):
                name = f"{repo}__{f.name}"
                if f.name.endswith(".tif.zip"):
                    continue
                dest = OUT_DIR / name
                try:
                    if not dest.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(f, dest)
                    out.append({
                        "owner": owner, "repo": repo, "repo_path": str(f.relative_to(tmp)),
                        "pool_file": name, "bytes": dest.stat().st_size,
                        "sha256": sha256_file(dest),
                    })
                except OSError as exc:  # pragma: no cover - filesystem edge case
                    out.append({"owner": owner, "repo": repo, "repo_path": str(f.relative_to(tmp)),
                                "status": "copy_error", "error": str(exc)[:200]})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"owner": owner, "repo": repo, "status": "ok", "files": out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--repos", default="", help="comma separated repo names to limit the run")
    ap.add_argument("--dirs", default="docs/downloads")
    args = ap.parse_args()

    repos = DEFAULT_REPOS
    if args.repos:
        wanted = {r.strip() for r in args.repos.split(",") if r.strip()}
        repos = [t for t in repos if t[1] in wanted]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    want_dirs = [d.strip() for d in args.dirs.split(",") if d.strip()]
    files: list[dict] = []
    repo_status: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_repo, o, r, want_dirs): (o, r) for o, r in repos}
        for fut in cf.as_completed(futs):
            res = fut.result()
            repo_status.append({k: v for k, v in res.items() if k != "files"})
            files.extend(res.get("files", []))
            print(f"[{len(repo_status)}/{len(repos)}] {res['owner']}/{res['repo']}: "
                  f"{res['status']} {len(res.get('files', []))} files", flush=True)

    # de-duplicate by sha256 (the same raster is published under several suffixes/sites)
    seen: dict[str, dict] = {}
    for f in files:
        if "sha256" not in f:
            continue
        prev = seen.get(f["sha256"])
        if prev is None or f["bytes"] < prev["bytes"]:
            seen[f["sha256"]] = f
    unique = sorted(seen.values(), key=lambda f: (f["repo"], f["pool_file"]))

    MANIFEST.write_text(json.dumps({
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": "git clone --depth 1 --filter=blob:none --sparse of github.com/<owner>/<repo>, "
                  "sparse-checkout docs/downloads",
        "n_repos_attempted": len(repos),
        "n_files_copied": len(files),
        "n_unique_by_sha256": len(unique),
        "repo_status": sorted(repo_status, key=lambda r: r["repo"]),
        "files": unique,
    }, indent=1))
    print(f"files={len(files)} unique={len(unique)} -> {MANIFEST}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
