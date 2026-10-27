#!/usr/bin/env python3
"""Restore only the pinned, publicly available owner-mirror audit rasters.

These are NOT organizer-authenticated data and do NOT constitute the complete
parallel registry or the shared cached feature stack. Downloads never become
valid until their pinned SHA-256 matches. Public inputs can be fetched anonymously
or with a GitHub Actions GH_TOKEN; raw bytes are never decoded as UTF-8.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "audit_manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path = MANIFEST) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), list):
        raise ValueError("invalid audit manifest")
    return manifest


def stream_github_raw(endpoint: str, stream, *, timeout: int = 90) -> None:
    """Stream GitHub API response bytes without charset conversion."""
    if not endpoint.startswith("repos/"):
        raise ValueError("expected a GitHub repository API endpoint")
    headers = {"Accept": "application/vnd.github.raw+json", "User-Agent": "gems-field-notes-audit"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/{endpoint}", headers=headers)
    with urlopen(request, timeout=timeout) as response:
        shutil.copyfileobj(response, stream, length=1 << 20)


def restore(entry: dict, target_dir: Path) -> str:
    repo, ref, path = entry["repo"], entry["ref"], entry["path"]
    name, expected = entry["destination"], entry["sha256"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("invalid repository")
    if not re.fullmatch(r"[0-9a-f]{40}", ref) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("un-pinned reference or invalid SHA-256")
    if Path(name).name != name or Path(path).is_absolute() or ".." in Path(path).parts:
        raise ValueError("unsafe source/destination path")
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / name
    if dest.is_file() and sha256_file(dest) == expected:
        return "verified cached"
    temp = dest.with_name(dest.name + ".partial")
    endpoint = f"repos/{repo}/contents/{quote(path, safe='/')}?ref={ref}"
    try:
        # GitHub labels raw bytes with charset=utf-8. Newer gh versions may try
        # to transcode binary TIFFs; the shared streamer keeps bytes unchanged.
        with temp.open("wb") as stream:
            stream_github_raw(endpoint, stream)
        actual = sha256_file(temp)
        if actual != expected:
            raise ValueError(f"SHA-256 mismatch for {entry['id']}: {actual} != {expected}")
        os.replace(temp, dest)
    finally:
        temp.unlink(missing_ok=True)
    return "restored & verified"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=("preflight", "focus", "spotcheck", "all"), default="all")
    parser.add_argument("--target", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    try:
        entries = load_manifest()["files"]
        selected = [e for e in entries if args.group == "all" or e["group"] == args.group]
        if not selected:
            raise ValueError("no inputs in requested group")
        for entry in selected:
            print(f"{entry['id']}: {restore(entry, args.target)}", flush=True)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Restore failed; no unchecked input accepted: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
