#!/usr/bin/env python3
"""Fetch the scored corpus and the focus registry with git (no REST API).

Why this exists: on 2026-10-31 the GitHub REST budget for the token was exhausted (5000/5000),
which broke both ``build_score_corpus.py`` downloads and ``fetch_focus_registry.py``.  Git smart-HTTP
(cloning from github.com) is a different transport and is not subject to the REST budget, so this
script materialises the same two caches with blobless, depth-1, sparse clones and records the same
manifest/receipt schemas:

* corpus  -> ``.cache/gems_corpus/<SITE>__<file>.tif`` + ``evidence/score_corpus_manifest_20261031.json``
* registry -> ``.cache/focus_registry/<REPO>__<file>.tif`` (SHA-256 verified against the manifest)

Matching logic is imported from ``build_score_corpus.py`` (one implementation, no fork).  Files that
already exist locally (this repository's own downloads) are copied instead of cloned.

Usage:
    python scripts/fetch_pool_via_git.py
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_score_corpus import norm, repo_of  # noqa: E402  (shared matching rule, not a fork)

GIT_CACHE = ROOT / ".cache" / "git_repos"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_clone(owner: str, repo: str) -> Path | None:
    """Blobless depth-1 clone of <owner>/<repo> into the cache; returns the work tree path."""
    dest = GIT_CACHE / f"{owner}__{repo}"
    if (dest / ".git").exists():
        return dest
    GIT_CACHE.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".partial")
    if tmp.exists():
        shutil.rmtree(tmp)
    r = subprocess.run(
        ["git", "clone", "--depth", "1", "--filter=blob:none", "--no-checkout",
         f"https://github.com/{owner}/{repo}.git", str(tmp)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"[warn] clone failed {owner}/{repo}: {r.stderr[-200:]}", file=sys.stderr)
        shutil.rmtree(tmp, ignore_errors=True)
        return None
    tmp.rename(dest)
    return dest


def list_tifs(work: Path) -> list[str]:
    r = subprocess.run(["git", "-C", str(work), "ls-tree", "-r", "HEAD", "--name-only"],
                       capture_output=True, text=True, check=True)
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip().lower().endswith(".tif")]


def checkout_files(work: Path, paths: list[str]) -> bool:
    """Fetch exactly these blobs (batched) into the work tree."""
    if not paths:
        return True
    r = subprocess.run(["git", "-C", str(work), "checkout", "HEAD", "--", *paths],
                       capture_output=True, text=True)
    return r.returncode == 0


def copy_local_if_ours(owner: str, repo: str, path: str) -> Path | None:
    """This repository's own files are already in the checkout — never clone ourselves."""
    if owner == "sassnarep3-star" and repo == "GEMSDOESASS3":
        p = ROOT / path
        return p if p.exists() else None
    return None


def fetch_corpus(table_path: Path, out: Path, manifest_path: Path) -> dict:
    table = json.loads(table_path.read_text())
    entries = table["entries"]
    out.mkdir(parents=True, exist_ok=True)

    # group entries by repo, clone once
    by_repo: dict[tuple[str, str], list[dict]] = {}
    for e in entries:
        by_repo.setdefault(repo_of(e["site"]), []).append(e)

    trees: dict[tuple[str, str], list[str]] = {}
    work_of: dict[tuple[str, str], Path] = {}
    for (owner, repo) in by_repo:
        if owner == "sassnarep3-star" and repo == "GEMSDOESASS3":
            trees[(owner, repo)] = [str(p.relative_to(ROOT)) for p in (ROOT / "docs" / "downloads").glob("*.tif")]
            continue
        work = ensure_clone(owner, repo)
        if work is None:
            trees[(owner, repo)] = []
            continue
        work_of[(owner, repo)] = work
        trees[(owner, repo)] = list_tifs(work)

    rows = []
    for i, e in enumerate(entries, 1):
        owner, repo = repo_of(e["site"])
        key = (owner, repo)
        tok = norm(e["token"])
        hits = [p for p in trees.get(key, []) if tok in norm(p)]
        hits.sort(key=lambda p: (0 if "/docs/downloads/" in p else 1, len(p)))
        hits = hits[:1]
        row = {
            "site": e["site"], "repo": f"{owner}/{repo}", "token": e["token"],
            "owner_reported_score": e["owner_reported_score"], "status": "unmatched",
            "path": None, "sha256": None, "local": None,
        }
        if len(hits) == 1:
            path = hits[0]
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{e['site']}__{Path(path).name}")
            dest = out / safe
            src = copy_local_if_ours(owner, repo, path)
            if src is not None:
                if not dest.exists():
                    shutil.copyfile(src, dest)
            elif key in work_of:
                if not dest.exists():
                    if checkout_files(work_of[key], [path]):
                        shutil.copyfile(work_of[key] / path, dest)
            if dest.exists():
                row.update(status="matched", path=path, sha256=sha256_file(dest),
                           local=str(dest.relative_to(ROOT)))
            else:
                row["status"] = "download_failed"
        elif len(hits) > 1:
            row["status"] = "ambiguous"
            row["candidates"] = hits
        rows.append(row)
        print(f"[{i:3d}/{len(entries)}] {row['status']:14s} {e['owner_reported_score']:.4f}  {e['token'][:66]}", flush=True)

    matched = [r for r in rows if r["status"] == "matched"]
    man = {
        "schema_version": 1,
        "score_label": "OWNER-REPORT",
        "provenance": str(table.get("provenance", "")),
        "source_table": str(table_path.relative_to(ROOT)),
        "fetch_method": "git blobless clone (REST-independent), scripts/fetch_pool_via_git.py",
        "n_entries": len(rows), "n_matched": len(matched),
        "n_unique_rasters": len({r["sha256"] for r in matched}),
        "rows": rows,
    }
    manifest_path.write_text(json.dumps(man, indent=1) + "\n")
    print(f"corpus: matched {len(matched)}/{len(rows)}, unique {man['n_unique_rasters']} -> {manifest_path}")
    return man


def fetch_registry(manifest_path: Path, out: Path, receipt_path: Path) -> dict:
    man = json.loads(manifest_path.read_text())
    rasters = man["rasters"]
    out.mkdir(parents=True, exist_ok=True)
    by_repo: dict[str, list[dict]] = {}
    for r in rasters:
        by_repo.setdefault(r["repo"], []).append(r)
    work_of: dict[str, Path] = {}
    for repo in by_repo:
        work = ensure_clone("buffedlizard55-lab", repo)
        if work is not None:
            work_of[repo] = work

    rows = []
    for repo, items in by_repo.items():
        paths = [r["path"] for r in items]
        if repo in work_of:
            checkout_files(work_of[repo], paths)
        for r in items:
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{r['repo']}__{Path(r['path']).name}")
            dest = out / safe
            if not dest.exists() and repo in work_of:
                src = work_of[repo] / r["path"]
                if src.exists():
                    shutil.copyfile(src, dest)
            if dest.exists():
                got = sha256_file(dest)
                status = "fetched" if got == r["sha256"] else "hash_mismatch"
            else:
                got, status = "", "fetch_failed"
            rows.append({"repo": r["repo"], "path": r["path"], "sha256": r["sha256"],
                         "local": str(dest), "status": status, "got_sha256": got})
        ok = sum(1 for x in rows if x["status"] in ("fetched", "present"))
        print(f"[registry] {repo}: running total verified {ok}/{len(rows)}", flush=True)

    ok = [x for x in rows if x["status"] in ("fetched", "present")]
    receipt = {
        "schema_version": 1,
        "source_manifest": str(manifest_path.relative_to(ROOT)),
        "fetch_method": "git blobless clone (REST-independent), scripts/fetch_pool_via_git.py",
        "n_requested": len(rows), "n_verified": len(ok),
        "label": "MEASURED (SHA-256 verified local copies of the public sibling rasters)",
        "rows": sorted(rows, key=lambda x: (x["repo"], x["path"])),
    }
    receipt_path.write_text(json.dumps(receipt, indent=1) + "\n")
    print(f"registry: verified {len(ok)}/{len(rows)} -> {receipt_path}")
    return receipt


def main() -> int:
    fetch_corpus(ROOT / "registry" / "published_score_table_20261031.json",
                 ROOT / ".cache" / "gems_corpus",
                 ROOT / "evidence" / "score_corpus_manifest_20261031.json")
    fetch_registry(ROOT / "registry" / "focus_registry_manifest.json",
                   ROOT / ".cache" / "focus_registry",
                   ROOT / "evidence" / "focus_registry_fetch_20261031.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
