#!/usr/bin/env python3
"""Rebuild the repository's fail-closed status feed from the current review receipt.

This feed is intentionally local and read-only: it never invents a model score, never treats a
projection as a result, and never promotes an artifact. It checks the explicit review run card,
current checkout prerequisites, and the recorded leaderboard snapshot. The public leaderboard
snapshot must be refreshed from its official page separately; this script does not pretend to fetch
live DrivenData data or require a login.

Run: python scripts/status_feed.py [--md PATH] [--json-out PATH]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "evidence/run_card_20261031_review.json"
LEADERBOARD_PATH = ROOT / "evidence/leaderboard_snapshot_20261031.json"


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def git(*args: str) -> str:
    try:
        p = subprocess.run(("git", *args), cwd=ROOT, text=True, capture_output=True, timeout=10)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--md", default="docs/research/FEED.md")
    ap.add_argument("--json-out", default="evidence/feed.json")
    args = ap.parse_args()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    card = load_json(CARD_PATH)
    board = load_json(LEADERBOARD_PATH)
    data_manifest = load_json(ROOT / "registry/data_manifest.json")
    cache_root = ROOT / ".cache/gems_data"
    expected_data = data_manifest.get("files", [])
    present_data = sum(1 for e in expected_data if (cache_root / e.get("dest", "__missing__")).is_file())
    modules = {name: importlib.util.find_spec(name) is not None
               for name in ("numpy", "rasterio", "scipy", "sklearn", "pytest")}

    overlap = card.get("correlation_overlap_vs_registry", {})
    holdout = card.get("holdout_dti", {})
    max_rho = overlap.get("surface_max_abs_binned_spearman")
    strict_overlap = overlap.get("final_dot_max_overlap_within_3px_all_references")
    preplacement = overlap.get("surface_preplacement_check")
    uniqueness_failed = (max_rho is None or max_rho > 0.90 or strict_overlap is None
                         or strict_overlap > 0.70 or preplacement is None)
    validator = card.get("validator_output", {})
    raster = card.get("raster", {})
    candidate = card.get("new_submission", {})

    checks = [
        {
            "id": "decision",
            "evidence_class": "REPOSITORY-REVIEW",
            "status": "NEGATIVE" if card.get("verdict") == "negative" and not card.get("ok_to_submit") else "REVIEW",
            "detail": {
                "verdict": card.get("verdict"),
                "ok_to_submit": card.get("ok_to_submit"),
                "new_tif_generated": candidate.get("generated"),
                "slots_spent": card.get("submission_slots_spent")
            },
            "next_action": "Do not upload; satisfy the documented blockers before proposing a candidate."
        },
        {
            "id": "inputs",
            "evidence_class": "LOCAL-CHECK",
            "status": "OK" if expected_data and present_data == len(expected_data) else "MISSING",
            "detail": {"verified_manifest_files_present": present_data, "manifest_files": len(expected_data),
                       "cache_root": ".cache/gems_data"},
            "next_action": "Restore the authorized official feature/label cache." if present_data != len(expected_data) else ""
        },
        {
            "id": "runtime",
            "evidence_class": "LOCAL-CHECK",
            "status": "OK" if all(modules.values()) else "MISSING",
            "detail": modules,
            "next_action": "Install project dependencies in a reproducible environment before geospatial revalidation."
            if not all(modules.values()) else ""
        },
        {
            "id": "uniqueness",
            "evidence_class": "REGISTRY-MEASUREMENT (recorded; not re-run by this script)",
            "status": "FAIL" if uniqueness_failed else "OK",
            "detail": {"max_abs_binned_spearman": max_rho,
                       "references_over_0p90": overlap.get("surface_registry_count_over_0p90"),
                       "strict_max_overlap_3px": overlap.get("final_dot_max_overlap_within_3px_all_references"),
                       "max_overlap_excluding_lattice": overlap.get("final_dot_overlap_excluding_lattice"),
                       "preplacement_surface_check": overlap.get("surface_preplacement_check")},
            "next_action": "Fail candidate; do not exclude the lattice or claim a pass."
        },
        {
            "id": "holdout",
            "evidence_class": holdout.get("label", "UNAVAILABLE"),
            "status": "RECORDED-NOT-RERUN" if holdout.get("score") is not None else "MISSING",
            "detail": {"evaluator_version": holdout.get("evaluator_version"),
                       "n_withheld_positives": holdout.get("n_withheld_positives"),
                       "dti": holdout.get("score"), "ci95": holdout.get("ci95"),
                       "use": holdout.get("decision_use")},
            "next_action": "Restore data and reproduce with shared evaluator; do not treat as leaderboard score."
        },
        {
            "id": "format",
            "evidence_class": "FORMAT-RECEIPT (recorded; not re-run by this script)",
            "status": "RECEIPT-CLAIMS-PASS-NOT-PORTAL-CONFIRMED" if validator.get("format_receipt_claims_pass") else "MISSING",
            "detail": {"crs": validator.get("crs"), "shape": validator.get("shape"),
                       "transform": validator.get("transform"),
                       "no_nan_inside_footprint": validator.get("no_nan_inside_footprint"),
                       "stored_values_in_range_0_1": validator.get("stored_values_in_range_0_1"),
                       "organizer_portal_acceptance_receipt": validator.get("organizer_portal_acceptance_receipt"),
                       "artifact_sha256": raster.get("sha256")},
            "next_action": "Re-run exact-byte checks and capture the portal's acceptance receipt before any submit claim."
        },
        {
            "id": "leaderboard",
            "evidence_class": board.get("evidence_class", "UNVERIFIED"),
            "status": "SNAPSHOT" if board.get("observed_rows") else "MISSING",
            "detail": {"source": board.get("source"), "fetched_utc": board.get("fetched_utc"),
                       "top_rows": board.get("observed_rows", [])[:5],
                       "scope_note": board.get("scope_note")},
            "next_action": "Refresh manually from official public leaderboard before making a current leaderboard claim."
        },
        {
            "id": "scope",
            "evidence_class": "BUDGET-RECORD",
            "status": "OK",
            "detail": {"experiments_used_this_review": card.get("experiments_used_this_review"),
                       "submission_slots_spent": card.get("submission_slots_spent"),
                       "lane_assignment_available": False},
            "next_action": "Recover the assigned method paragraph; the protocol says not to invent it."
        }
    ]

    status_order = {"FAIL": 0, "MISSING": 1, "NEGATIVE": 2, "RECEIPT-CLAIMS-PASS-NOT-PORTAL-CONFIRMED": 3,
                    "RECORDED-NOT-RERUN": 4, "SNAPSHOT": 5, "OK": 6}
    checks.sort(key=lambda x: status_order.get(x["status"], 9))
    n = {name: sum(c["status"] == name for c in checks)
         for name in sorted({c["status"] for c in checks})}
    feed = {"schema_version": 2, "generated_utc": now, "decision": "NO-GO",
            "current_branch": git("branch", "--show-current"), "head": git("rev-parse", "--short", "HEAD"),
            "checks": checks, "counts": n,
            "note": "Local review feed only. It does not fetch DrivenData or imply portal acceptance."}

    md = ["# GEMSDOESASS3 current status feed", "",
          f"Generated {now} from the 2026-10-31 review card and local checkout.", "",
          "## Decision: NO-GO — do not submit", "",
          "This feed is fail-closed. It does not select a weekly slot or certify portal acceptance.",
          "The public leaderboard snapshot and all owner-reported per-site scores have distinct evidence classes.", "",
          f"Branch: `{feed['current_branch'] or 'unknown'}` · HEAD: `{feed['head'] or 'unknown'}` · "
          f"Candidate: `{raster.get('submission_name_archival_only', 'none')}` (archival, negative).", "",
          "| Status | Check | Evidence class | Detail | Next action |", "|---|---|---|---|---|"]
    for c in checks:
        detail = json.dumps(c["detail"], ensure_ascii=False, default=str)
        if len(detail) > 450:
            detail = detail[:447] + "…"
        md.append(f"| **{c['status']}** | {c['id']} | {c['evidence_class']} | `{detail}` | {c['next_action']} |")
    md += ["", "## Refresh policy", "",
           "`python scripts/status_feed.py` refreshes local state only. Refresh the official public leaderboard from "
           "[DrivenData](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) separately; "
           "this tool never reports per-submission organizer scores unless a receipt is explicitly saved.", ""]

    (ROOT / args.md).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / args.md).write_text("\n".join(md))
    (ROOT / args.json_out).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / args.json_out).write_text(json.dumps(feed, ensure_ascii=False, indent=2) + "\n")
    print(f"decision=NO-GO branch={feed['current_branch']} head={feed['head']} counts={n}")
    print(f"wrote {args.md} and {args.json_out}")
    return 1 if any(c["status"] in {"FAIL", "MISSING"} for c in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
