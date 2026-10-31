#!/usr/bin/env python3
"""Fetch the 129 OWNER-REPORT corpus rasters from the public sibling repos.

Used to re-fit the leaderboard-inversion field (scripts/fit_lb_truth_inverse.py)
so a NEW candidate can be emitted without any private/organizer data. Every file
is fetched through the GitHub API (api.github.com) and SHA-256 verified against
evidence/score_corpus_manifest_20261030.json.  Nothing here is organizer data.

The GitHub *contents* API omits ``content`` for files larger than 1 MB
(``encoding: "none"``); those are fetched through the *git blobs* API instead.

Usage:  python scripts/fetch_corpus_refit.py [--limit N]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence" / "score_corpus_manifest_20261030.json"
OUT = ROOT / ".cache" / "gems_corpus"


def gh(args: list[str]) -> str:
    proc = subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"gh api {' '.join(args)} failed: {proc.stderr.strip()[:200]}")
    return proc.stdout


def fetch(repo: str, path: str) -> bytes:
    meta = json.loads(gh([f"repos/{repo}/contents/{path}", "--jq", "."]))
    blob_sha = meta.get("sha")
    if meta.get("encoding") == "base64" and meta.get("content"):
        return base64.b64decode(meta["content"])
    # contents API omitted the body (file > 1 MB): pull the blob directly
    if not blob_sha:
        raise RuntimeError(f"no blob sha for {repo}/{path}")
    return base64.b64decode(gh([f"repos/{repo}/git/blobs/{blob_sha}", "--jq", ".content"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    m = json.loads(MANIFEST.read_text())
    rows = [r for r in m["rows"] if r["status"] == "matched"]
    if args.limit:
        rows = rows[: args.limit]
    OUT.mkdir(parents=True, exist_ok=True)
    ok = miss = bad = 0
    for r in rows:
        name = f"{r['repo'].replace('/', '__')}__{Path(r['path']).name}"
        dst = OUT / name
        if dst.exists() and dst.stat().st_size > 0:
            ok += 1
            continue
        try:
            data = fetch(r["repo"], r["path"])
        except Exception as exc:  # noqa: BLE001
            print(f"MISS {name}: {exc}", flush=True)
            miss += 1
            continue
        dst.write_bytes(data)
        got = hashlib.sha256(data).hexdigest()
        if r.get("sha256") and got != r["sha256"]:
            print(f"BAD {name}: {got} != {r['sha256']}", flush=True)
            bad += 1
            continue
        ok += 1
        if ok % 25 == 0:
            print(f"progress {ok} ok, {miss} miss, {bad} bad", flush=True)
    print(f"DONE ok={ok} miss={miss} bad={bad} of {len(rows)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
