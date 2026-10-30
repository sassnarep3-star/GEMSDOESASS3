#!/usr/bin/env python3
"""Expand the calibration set: fetch additional scored sibling rasters named in the task prompt.

Each entry is (repo, display name as typed in the prompt, owner-reported score, name substring).
The score is OWNER-REPORT (typed in the task prompt); it is not an organizer receipt.  The file is
located by listing the repository's download directories and matching the substring, then fetched
with its recorded SHA-256 so the join is reproducible.

Usage:  python scripts/fetch_scored_extra.py
Writes: .cache/gems_data/focus/fetch_receipt_extra.json  (not tracked; .cache is git-ignored)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache" / "gems_data" / "focus"
OUT.mkdir(parents=True, exist_ok=True)

OWNER = "buffedlizard55-lab"
# (repo, prompt name, owner-reported score, substring to match)
TARGETS = [
    ("GEMSDOE29", "sgmc-off-catalogue-44k-20261003-c8dcd780e3fd-nan", 0.0512, "sgmc-off-catalogue-44k"),
    ("GEMSDOE29", "wormrank-d28-20261003-59dcaf6dd11d-zeros", 0.2560, "wormrank-d28"),
    ("GEMSDOE29", "efd28-repro-20261003-1cc7dc534d51-nan", 0.2600, "efd28-repro"),
    ("GEMSDOE72", "gemsdoe72-h72-1-sgmc-offcatalogue-20261020T195456Z-6e6525e5-zeros", 0.0492, "sgmc-offcatalogue"),
    ("GEMSDOE70", "gems70-p5-dual-submod300-oof38k-20261020", 0.2478, "p5-dual-submod300"),
    ("GEMSDOE76", "gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros", 0.2343, "ptcf-tiltworm"),
    ("GEMSDOE63", "cvarlw-thin-s3p17-54864-20261011T220606Z-c58f60c4-zeros", 0.2303, "cvarlw-thin"),
    ("GEMSDOE48", "h59-cover-ds-belief-b2xh33d-20261008T184547Z-b79c4c61d8d8", 0.2296, "belief-b2xh33d"),
    ("GEMSDOE49", "gate_ortho_w0.25-40k-20261006T213721Z-nan", 0.2376, "gate_ortho"),
    ("GEMSDOE46", "r11f-scarp-radiometric-fusion-00e049b51218-zeros", 0.1589, "scarp-radiometric-fusion"),
    ("GEMSDOE73", "gems73-h73-mcsc-seamfree-blakely-37654dots", 0.1917, "seamfree-blakely"),
    ("GEMSDOE75", "gems75-trlt-radon-loco-ridge-20261021-zeros", 0.1627, "trlt-radon"),
    ("GEMSDOE82", "gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros", 0.1886, "submodular-punoisyor"),
    ("GEMSDOE91", "gems91-s17-lftg-20261025T160014Z-7b6bf90844-zeros", 0.1823, "s17-lftg"),
    ("GEMSDOE67", "ovtr-ml-cover-tau3p0-20261012-nan", 0.1426, "ovtr-ml-cover"),
    ("GEMSDOE66", "gems66-lidar03-cvretrain-reliefdecile-37654dots-20261020T190152Z-zeros", 0.1152, "lidar03-cvretrain"),
    ("GEMSDOE24", "gems24-gvc1-negative-geothermal-lineament-submod", 0.0859, "gvc1-negative"),
    ("GEMSDOE27", "gems27-h29-hydrothermal-piedmont-celf", 0.2190, "hydrothermal-piedmont"),
]


def gh(*args: str) -> bytes:
    r = subprocess.run(["gh", *args], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode()[:400])
    return r.stdout


def list_downloads(repo: str) -> list[str]:
    paths: list[str] = []
    for d in ("docs/downloads", "docs/downloads/", "downloads", "docs"):
        try:
            items = json.loads(gh("api", f"repos/{OWNER}/{repo}/contents/{d}"))
        except RuntimeError:
            continue
        for it in items:
            if it["type"] == "file" and it["name"].endswith(".tif"):
                paths.append(it["path"])
    return paths


def main() -> int:
    recs = []
    for repo, name, score, sub in TARGETS:
        cands = [p for p in list_downloads(repo) if sub in Path(p).name]
        if not cands:
            recs.append(dict(repo=repo, prompt_name=name, owner_reported_score=score, status="not_found"))
            print("NOT FOUND", repo, sub)
            continue
        path = cands[0]
        dest = OUT / Path(path).name
        if not dest.exists():
            dest.write_bytes(gh("api", f"repos/{OWNER}/{repo}/contents/{path}", "-H", "Accept: application/vnd.github.raw"))
        recs.append(dict(repo=f"{OWNER}/{repo}", prompt_name=name, owner_reported_score=score,
                         path=path, file=dest.name, bytes=dest.stat().st_size,
                         sha256=hashlib.sha256(dest.read_bytes()).hexdigest(), status="ok"))
        print("ok", dest.stat().st_size, repo, score, dest.name[:70])
    (OUT / "fetch_receipt_extra.json").write_text(json.dumps(recs, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
