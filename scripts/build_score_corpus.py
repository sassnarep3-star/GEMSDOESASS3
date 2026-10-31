#!/usr/bin/env python3
"""Build a score-calibrated corpus of published sibling submission rasters.

Why this exists
---------------
Every previous session tried to *guess* which proxy (hide-and-recover, SGMC, lattice)
corresponds to the DrivenData leaderboard.  This script replaces guessing with
measurement: it downloads every sibling raster whose file name the owner published
together with a leaderboard score, and writes one manifest that pairs

    (raster path, sha256, positive-pixel count, grid statistics)  <->  owner-reported score

That table is the only external supervision available without organisers' receipts,
and it is what lets this repo *estimate* a score instead of asserting one.

What it does
------------
1. Reads ``registry/published_score_table_20261030.json`` (OWNER-REPORT scores typed by
   the owner next to public file names).
2. For each named repository, lists the git tree once (``gh api .../git/trees``).
3. Matches each token to file names after stripping published status suffixes.
4. Downloads matched blobs (``gh api .../contents``, raw media type) into ``--out``.
5. Writes ``--manifest`` with per-entry status: matched / unmatched / ambiguous.

Network: api.github.com only, via the authenticated ``gh`` CLI.  Nothing is written
inside the repository tree except the manifest.

Usage
-----
    python scripts/build_score_corpus.py --out .cache/gems_corpus \
        --manifest evidence/score_corpus_manifest_20261030.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLE = ROOT / "registry" / "published_score_table_20261030.json"

# Explicit owner for every site label that is NOT buffedlizard55-lab/<site>.
OWNER_OVERRIDES = {
    "KANLERGEMSDOE2": ("kanlerxz87-cyber", "KANLERGEMSDOE2"),
    "KANLERGEMSDOE1": ("kanlerxz87-cyber", "KANLERGEMSDOE1"),
    "KANLERGEMSDOE3": ("kanlerxz87-cyber", "KANLERGEMSDOE3"),
    "WBGGEMSDOE1": ("wingbangboozle1-lang", "WBGGEMSDOE1"),
    "WBGGEMSDOE2": ("wingbangboozle1-lang", "WBGGEMSDOE2"),
    "WBGGEMSDOE3": ("wingbangboozle1-lang", "WBGGEMSDOE3"),
    "GEMSDOEkarage1": ("karagemop466-tech", "GEMSDOEkarage1"),
    "GEMSDOEkarage2": ("karagemop466-tech", "GEMSDOEkarage2"),
    "GEMSDOEkarage3": ("karagemop466-tech", "GEMSDOEkarage3"),
    "ApartGEMSDOE1": ("apartanish22-droid", "ApartGEMSDOE1"),
    "ApartGEMSDOE2": ("apartanish22-droid", "ApartGEMSDOE2"),
    "ApartGEMSDOE3": ("apartanish22-droid", "ApartGEMSDOE3"),
    "GEMSDOESASS1": ("sassnarep3-star", "GEMSDOESASS1"),
    "GEMSDOESASS2": ("sassnarep3-star", "GEMSDOESASS2"),
    "GEMSDOESASS3": ("sassnarep3-star", "GEMSDOESASS3"),
    "EUGGEMSDOE1": ("eugboogieman123-ops", "EUGGEMSDOE1"),
    "EUGGEMSDOE2": ("eugboogieman123-ops", "EUGGEMSDOE2"),
    "EUGGEMSDOE3": ("eugboogieman123-ops", "EUGGEMSDOE3"),
    "GINNYGEMSDOE1": ("ginnymcfiner23-ux", "GINNYGEMSDOE1"),
    "GINNYGEMSDOE2": ("ginnymcfiner23-ux", "GINNYGEMSDOE2"),
    "GINNYGEMSDOE3": ("ginnymcfiner23-ux", "GINNYGEMSDOE3"),
}

SUFFIX_RE = re.compile(
    r"[-_](nan|zeros|allfinite|hard|nanoutside|zero|finite|outside)$", re.IGNORECASE
)


def norm(s: str) -> str:
    """Lower-case and strip one or more published status suffixes and the .tif extension."""
    s = s.lower()
    for _ in range(3):
        s2 = re.sub(r"\.tiff?$", "", s)
        s2 = SUFFIX_RE.sub("", s2)
        if s2 == s:
            break
        s = s2
    return s


def gh_json(args: list[str]) -> dict:
    out = subprocess.run(["gh", "api", *args], capture_output=True, check=True)
    return json.loads(out.stdout)


def repo_of(site: str) -> tuple[str, str]:
    if site in OWNER_OVERRIDES:
        return OWNER_OVERRIDES[site]
    return ("buffedlizard55-lab", site)


def list_tifs(owner: str, repo: str) -> list[str]:
    ref = gh_json([f"repos/{owner}/{repo}"])["default_branch"]
    tree = gh_json([f"repos/{owner}/{repo}/git/trees/{ref}?recursive=1"])
    return [t["path"] for t in tree.get("tree", []) if t["type"] == "blob" and t["path"].lower().endswith(".tif")]


def download(owner: str, repo: str, path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    with tmp.open("wb") as fh:
        subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/contents/{path}",
             "-H", "Accept: application/vnd.github.raw"],
            stdout=fh, check=True,
        )
    tmp.replace(dest)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / ".cache" / "gems_corpus")
    ap.add_argument("--manifest", type=Path,
                    default=ROOT / "evidence" / "score_corpus_manifest_20261030.json")
    ap.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    ap.add_argument("--only", nargs="*", default=None, help="restrict to these site labels")
    ap.add_argument("--max-per-entry", type=int, default=1)
    args = ap.parse_args()

    table = json.loads(args.table.read_text())
    entries = table["entries"]
    if args.only:
        keep = set(args.only)
        entries = [e for e in entries if e["site"] in keep]

    trees: dict[tuple[str, str], list[str]] = {}
    rows = []
    for i, e in enumerate(entries, 1):
        owner, repo = repo_of(e["site"])
        key = (owner, repo)
        if key not in trees:
            try:
                trees[key] = list_tifs(owner, repo)
            except subprocess.CalledProcessError as exc:  # repo missing / renamed
                trees[key] = []
                print(f"[warn] cannot list {owner}/{repo}: {exc}", file=sys.stderr)
        tok = norm(e["token"])
        hits = [p for p in trees[key] if tok in norm(p)]
        # Prefer docs/downloads copies, then the shortest path.
        hits.sort(key=lambda p: (0 if "/docs/downloads/" in p else 1, len(p)))
        hits = hits[: args.max_per_entry]
        row = {
            "site": e["site"],
            "repo": f"{owner}/{repo}",
            "token": e["token"],
            "owner_reported_score": e["owner_reported_score"],
            "status": "unmatched",
            "path": None,
            "sha256": None,
            "local": None,
        }
        if len(hits) == 1:
            path = hits[0]
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{e['site']}__{Path(path).name}")
            dest = args.out / safe
            if not dest.exists():
                try:
                    download(owner, repo, path, dest)
                except subprocess.CalledProcessError as exc:
                    print(f"[warn] download failed {owner}/{repo}/{path}: {exc}", file=sys.stderr)
            if dest.exists():
                row.update(
                    status="matched",
                    path=path,
                    sha256=sha256_file(dest),
                    local=str(dest.relative_to(ROOT)) if dest.is_relative_to(ROOT) else str(dest),
                )
            else:
                row["status"] = "download_failed"
        elif len(hits) > 1:
            row["status"] = "ambiguous"
            row["candidates"] = hits
        rows.append(row)
        score = e["owner_reported_score"]
        print(f"[{i:3d}/{len(entries)}] {row['status']:14s} {score:.4f}  {e['token'][:70]}")

    matched = [r for r in rows if r["status"] == "matched"]
    uniq_hashes = {r["sha256"] for r in matched}
    man = {
        "schema_version": 1,
        "score_label": "OWNER-REPORT",
        "provenance": table["provenance"],
        "source_table": str(Path(args.table).resolve().relative_to(ROOT)) if Path(args.table).resolve().is_relative_to(ROOT) else str(args.table),
        "n_entries": len(rows),
        "n_matched": len(matched),
        "n_unique_rasters": len(uniq_hashes),
        "rows": rows,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(man, indent=1) + "\n")
    print(f"\nmatched {len(matched)}/{len(rows)} entries, {len(uniq_hashes)} unique rasters")
    print(f"manifest -> {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
