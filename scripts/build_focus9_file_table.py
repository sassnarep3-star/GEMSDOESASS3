#!/usr/bin/env python3
"""Build the verified download table for the nine focus sites.

For each focus site it takes the highest OWNER-REPORTED score from
registry/owner_reported_scores_focus.json, resolves the file the owner registry names,
and checks that file against (a) the local sibling-repo copy (SHA-256 recomputed here) and
(b) the historical audit record in evidence/nine_sites_executive_audit.json.
It also records whether the prompt's own label matches the file name, because several
prompt labels end in "-nan" while the registry file ends in "-allfinite" or "-zeros".

Usage:
    python scripts/build_focus9_file_table.py --pool /tmp/registry_siblings \
        --out evidence/focus9_file_table.json
The pool directory holds files named ``<repo>__<basename>`` (see fetch_sibling_registry.py).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", type=Path, required=True)
    ap.add_argument("--repo-root", type=Path, default=None,
                    help="directory holding <repo>/docs/downloads/ checkouts (preferred source)")
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "focus9_file_table.json")
    args = ap.parse_args()

    owner = json.loads((ROOT / "registry" / "owner_reported_scores_focus.json").read_text())
    audit = json.loads((ROOT / "evidence" / "nine_sites_executive_audit.json").read_text())
    audit_by_site = {s["site"]: s for s in audit["sites"]}

    best: dict[str, dict] = {}
    for e in owner["entries"]:
        cur = best.get(e["site"])
        if cur is None or e["owner_reported_score"] > cur["owner_reported_score"]:
            best[e["site"]] = e

    import numpy as np
    import rasterio

    rows = []
    pos_digest: dict[str, str] = {}
    for site in sorted(best):
        e = best[site]
        fname = Path(e["file"]).name
        repo = e["repo_dir"].replace("-main", "")
        local = args.pool / f"{repo}__{fname}"
        if args.repo_root is not None and (args.repo_root / repo / "docs" / "downloads" / fname).exists():
            local = args.repo_root / repo / "docs" / "downloads" / fname
        exists = local.exists()
        sha_local = sha256_file(local) if exists else None
        hist = audit_by_site.get(site, {}).get("historical_best", {})
        sha_audit = hist.get("sha256")
        prompt = e["prompt_name"]
        pix_hash = None
        if exists:
            with rasterio.open(local) as ds:
                pos = ds.read(1) > 0
            pix_hash = hashlib.sha256(np.packbits(pos).tobytes()).hexdigest()
        pos_digest[site] = pix_hash
        rows.append({
            "site": site,
            "positive_set_sha256": pix_hash,
            "owner_reported_score": e["owner_reported_score"],
            "evidence_class": "OWNER-REPORT (not an organizer receipt)",
            "file_to_download": fname,
            "github_url": f"https://github.com/buffedlizard55-lab/{repo}/blob/main/{e['file']}",
            "prompt_label": prompt,
            "prompt_label_matches_file": prompt in fname,
            "local_file_found": exists,
            "bytes": local.stat().st_size if exists else None,
            "sha256_recomputed": sha_local,
            "sha256_matches_audit_record": (sha_local == sha_audit) if (exists and sha_audit) else None,
            "already_submitted": True,
            "unique_for_resubmission": False,
            "holdout_dti_historical": hist.get("holdout_dti"),
        })

    for r in rows:
        r["pixel_identical_to"] = sorted(
            o["site"] for o in rows
            if o["site"] != r["site"] and r["positive_set_sha256"] and o["positive_set_sha256"] == r["positive_set_sha256"])

    out = {
        "schema_version": 1,
        "generated_from": {
            "owner_scores": "registry/owner_reported_scores_focus.json",
            "audit": "evidence/nine_sites_executive_audit.json",
            "pool": str(args.pool),
            "repo_root": str(args.repo_root) if args.repo_root else None,
        },
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    for r in rows:
        print(f"{r['site']:9s} {r['owner_reported_score']:.4f} {r['file_to_download']} "
              f"found={r['local_file_found']} audit_sha_match={r['sha256_matches_audit_record']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
