#!/usr/bin/env python3
"""Snapshot public GitHub main refs; never scrape DrivenData or select a slot."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from restore_audit_inputs import MANIFEST, load_manifest
from io_safety import protect_inputs

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "evidence" / "source_freshness.json")
    args = parser.parse_args()
    try:
        protect_inputs(args.out, [MANIFEST])
        focus = [e for e in load_manifest()["files"] if e["group"] == "focus"]
    except (OSError, ValueError, KeyError) as exc:
        print(f"Source snapshot failed: {exc}", file=sys.stderr)
        return 1
    rows, errors = [], []
    for e in focus:
        try:
            raw = subprocess.run(
                ["gh", "api", f"repos/{e['repo']}/commits/main", "--jq", ".sha"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            if len(raw) != 40 or any(c not in "0123456789abcdef" for c in raw):
                raise ValueError("invalid SHA in GitHub response")
            rows.append({"site": e["id"], "repo": e["repo"], "ref": "main", "main_sha": raw,
                         "historical_artifact_ref": e["ref"], "site_url": e["site_url"]})
            print(f"{e['id']}: {raw}")
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            errors.append({"site": e["id"], "error": str(exc)})
    record = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Public repository main refs only; not Pages deployments, the full raster registry, team receipts or live scores.",
        "complete": len(rows) == 9 and not errors,
        "sources": rows, "errors": errors,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if errors:
        print("Source freshness incomplete; treat unverified sources as stale/unknown.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
