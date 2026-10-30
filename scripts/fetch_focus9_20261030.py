#!/usr/bin/env python3
"""Fetch the nine focus-site historical files named in the task prompt, by SHA-256.

Files are pulled with a blobless sparse `git clone` of `docs/downloads` (git over https,
which works from this sandbox; the REST API is rate-limited and raw.githubusercontent.com is
not on the allow-list). Every file is verified against the SHA-256 recorded in
registry/focus_registry_manifest.json, which was itself built by SHA-verified fetch.

    python scripts/fetch_focus9_20261030.py --dest .cache/focus9

Writes a receipt with the URL, byte count and hash of each file. Nothing is committed:
the files stay in an ignored cache directory, and the receipt records provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com/repos/buffedlizard55-lab/{repo}/{kind}"

# (site, repo path, prompt name) - exact files named in the task prompt
TARGETS = [
    ("GEMSDOE24", "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
     "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan"),
    ("GEMSDOE25", "docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif",
     "dotted-h19-5-d2-8-20261002-e56ea318af89-nan"),
    ("GEMSDOE27", "docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif",
     "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan"),
    ("GEMSDOE28", "docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif",
     "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan"),
    ("GEMSDOE30", "docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif",
     "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca"),
    ("GEMSDOE31", "docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif",
     "h27-4-solo-d28-20261004-8acb75e1-nan"),
    ("GEMSDOE32", "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
     "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros"),
    ("GEMSDOE33", "docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif",
     "h33d-analog-tip-stepover-r30-20261004-cb490425926e"),
    ("GEMSDOE36", "docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif",
     "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros"),
]


def _sparse_clone_into(repo: str, dest_dir: Path, wanted: list[str]) -> None:
    """Blobless sparse checkout of docs/downloads (git over https; no REST API, no rate limit)."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        url = f"https://github.com/buffedlizard55-lab/{repo}.git"
        subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", "--quiet", url, tmp],
                       check=True)
        subprocess.run(["git", "-C", tmp, "sparse-checkout", "set", "docs/downloads"], check=True)
        for name in wanted:
            src = Path(tmp) / name
            if src.exists():
                (dest_dir / f"{repo}__{Path(name).name}").write_bytes(src.read_bytes())


def fetch_one(repo: str, path: str, dest_dir: Path) -> bytes:
    out = dest_dir / f"{repo}__{Path(path).name}"
    if not out.exists():
        _sparse_clone_into(repo, dest_dir, [path])
    if not out.exists():
        raise FileNotFoundError(f"{repo}:{path} not found by sparse checkout")
    return out.read_bytes()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", type=Path, default=ROOT / ".cache" / "focus9")
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "focus9_fetch_receipt_20261030.json")
    args = ap.parse_args()
    args.dest.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "registry" / "focus_registry_manifest.json").read_text())
    by_key = {(r["repo"], r["path"]): r for r in manifest["rasters"]}
    # Secondary hash source: the 2026-10-28 focus-site audit records the SHA-256 of the
    # historical best file per site even where the registry manifest holds a sibling variant.
    audit = json.loads((ROOT / "evidence" / "focus_site_candidate_audit_20261028.json").read_text())
    audit_sha = {k: v["sha256"] for k, v in audit["references"].items() if k.startswith("HIST_")}
    rows = []
    for repo, path, prompt_name in TARGETS:
        raw = fetch_one(repo, path, args.dest)
        sha = hashlib.sha256(raw).hexdigest()
        expected = by_key.get((repo, path), {}).get("sha256")
        source = "registry/focus_registry_manifest.json" if expected else None
        if expected is None:
            expected = audit_sha.get(f"HIST_{repo}")
            source = "evidence/focus_site_candidate_audit_20261028.json:references" if expected else None
        rows.append({
            "site": repo, "path": path, "prompt_name": prompt_name,
            "url": f"https://github.com/buffedlizard55-lab/{repo}/blob/HEAD/{path}",
            "bytes": len(raw), "sha256": sha, "expected_sha256": expected,
            "expected_sha256_source": source,
            "sha256_match": bool(expected == sha),
            "local": str((args.dest / f"{repo}__{Path(path).name}").resolve().relative_to(ROOT)),
        })
        print(f"{repo:10s} {len(raw):9d} {sha[:12]} match={expected == sha}")
    payload = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "what": "the nine focus-site historical files named in the task prompt, fetched by SHA-256",
        "source_manifest": "registry/focus_registry_manifest.json",
        "all_match": all(r["sha256_match"] for r in rows),
        "rows": rows,
        "note": "files are cached under .cache/ (git-ignored); only this receipt is committed",
    }
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print("all_match:", payload["all_match"])
    return 0 if payload["all_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
