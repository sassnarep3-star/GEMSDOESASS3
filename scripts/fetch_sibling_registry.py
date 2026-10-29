#!/usr/bin/env python3
"""Rebuild the uniqueness pool of public GEMSDOE sibling rasters from GitHub.

Why this exists
---------------
The Protocol-Rule-1 lane check needs every previously submitted raster on disk. The
registry is not stored in this repo (rasters are large and some are competition inputs).
This script re-creates the pool from the public sibling repositories listed in
``registry/sibling_repos.txt`` so anyone can re-run ``scripts/independent_uniqueness_audit.py``.

What it copies (into ``--out``, flat directory, names prefixed ``owner__repo__``)
-------------------------------------------------------------------------------
1. Every ``*.tif`` under ``docs/downloads/`` (blobless sparse clone, depth 1).
2. Every ``*.tif`` elsewhere in the repo whose size is <= ``--max-outside-bytes``
   (default 2.5 MB; partial clone with ``--filter=blob:limit``).
   Files whose names look like competition inputs or USGS catalogue layers are EXCLUDED
   (labels, sample/example submissions, existing faults, catalogue/qfaults layers).
   They are not submissions and must not be used as a uniqueness reference.

It then writes ``--manifest`` with the path, size and SHA-256 of every copied file.
Network: github.com only (git clone). Nothing is written into the repository tree
except the manifest, which is written where you point ``--manifest``.

Usage
-----
    python scripts/fetch_sibling_registry.py --out /tmp/full_pool \
        --manifest registry/sibling_pool_manifest.json [--only owner/repo ...] [--limit N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_LIST = ROOT / "registry" / "sibling_repos.txt"
EXCLUDE_RE = re.compile(
    r"(labels|sample_submission|example_submission|existing_faults|catalogue|qfaults|proxy_window)",
    re.IGNORECASE,
)


def read_repos(path: Path) -> list[tuple[str, str]]:
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        owner, repo = line.split()[:2]
        out.append((owner, repo))
    return out


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def fetch_docs_downloads(owner: str, repo: str, workdir: Path) -> list[tuple[str, Path]]:
    """Return [(repo_path, local_tmp_file)] for TIFs under docs/downloads."""
    d = workdir / f"{owner}__{repo}__dl"
    url = f"https://github.com/{owner}/{repo}.git"
    r = git("clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout", url, str(d))
    if r.returncode != 0:
        return []
    git("sparse-checkout", "init", "--cone", cwd=d)
    git("sparse-checkout", "set", "docs/downloads", cwd=d)
    if git("checkout", "-q", cwd=d).returncode != 0:
        return []
    out = []
    for f in sorted((d / "docs" / "downloads").glob("*.tif")):
        out.append((f"docs/downloads/{f.name}", f))
    return out


def fetch_outside_small(owner: str, repo: str, workdir: Path, max_bytes: int) -> list[tuple[str, Path]]:
    """Return [(repo_path, local_tmp_file)] for small TIFs outside docs/downloads (partial clone)."""
    d = workdir / f"{owner}__{repo}__small"
    url = f"https://github.com/{owner}/{repo}.git"
    r = git("clone", "-q", "--depth", "1", f"--filter=blob:limit={max_bytes}", "--no-checkout", url, str(d))
    if r.returncode != 0:
        return []
    lst = git("ls-tree", "-r", "-l", "HEAD", cwd=d)
    out = []
    for line in lst.stdout.splitlines():
        # format: "<mode> <type> <sha> <size>\t<path>"
        meta, path = line.split("\t", 1)
        size = int(meta.split()[3]) if meta.split()[3] != "-" else -1
        if not path.lower().endswith(".tif") or path.startswith("docs/downloads/"):
            continue
        if size < 0 or size > max_bytes or EXCLUDE_RE.search(os.path.basename(path)):
            continue
        dst = workdir / f"{owner}__{repo}__small__{path.replace('/', '__')}"
        with dst.open("wb") as fh:
            p = subprocess.run(["git", "cat-file", "blob", f"HEAD:{path}"], cwd=d, stdout=fh, check=False)
        if p.returncode == 0:
            out.append((path, dst))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True, help="flat output directory for the pool")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--only", nargs="*", default=None, help="owner/repo filters")
    ap.add_argument("--limit", type=int, default=None, help="only the first N repos (smoke tests)")
    ap.add_argument("--max-outside-bytes", type=int, default=2_500_000)
    args = ap.parse_args(argv)

    if shutil.which("git") is None:
        print("git is required", file=sys.stderr)
        return 2
    repos = read_repos(REPO_LIST)
    if args.only:
        wanted = set(args.only)
        repos = [(o, r) for o, r in repos if f"{o}/{r}" in wanted]
    if args.limit:
        repos = repos[: args.limit]

    args.out.mkdir(parents=True, exist_ok=True)
    entries = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="gemsdoe_sib_") as tmp:
        workdir = Path(tmp)
        for owner, repo in repos:
            got = []
            try:
                got += fetch_docs_downloads(owner, repo, workdir)
                got += fetch_outside_small(owner, repo, workdir, args.max_outside_bytes)
            except Exception as exc:  # keep going; record the failure
                failures.append({"repo": f"{owner}/{repo}", "error": str(exc)[:200]})
                continue
            for repo_path, local in got:
                # docs/downloads names are unique per folder; other paths keep their full path
                # in the name so that identically named files in different folders cannot collide.
                tail = os.path.basename(repo_path) if repo_path.startswith("docs/downloads/") else repo_path.replace("/", "__")
                dst = args.out / f"{owner}__{repo}__{tail}"
                if repo_path.startswith("docs/downloads/"):
                    shutil.copy2(local, dst)
                else:
                    shutil.move(str(local), dst)
                entries.append({
                    "repo": f"{owner}/{repo}",
                    "repo_path": repo_path,
                    "pool_file": dst.name,
                    "bytes": dst.stat().st_size,
                    "sha256": sha256_file(dst),
                })
            # free the partial clones as we go
            for p in workdir.iterdir():
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
            print(f"[fetch] {owner}/{repo}: {len(got)} tif", flush=True)

    manifest = {
        "schema_version": 1,
        "repo_list": str(REPO_LIST.relative_to(ROOT)),
        "max_outside_bytes": args.max_outside_bytes,
        "excluded_name_pattern": EXCLUDE_RE.pattern,
        "n_files": len(entries),
        "n_repos_requested": len(repos),
        "failures": failures,
        "files": entries,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"wrote {args.manifest} ({len(entries)} files, {len(failures)} failures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
