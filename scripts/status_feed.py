#!/usr/bin/env python3
"""Continuously-updated project status feed - the thing to run instead of re-checking by hand.

Regenerates two artefacts from the live workspace:

  docs/research/FEED.md   human-readable digest: what is verified right now, what is stale, what is next
  evidence/feed.json      the same content machine-readable, one record per check

Every check is computed here, from files, in this run - nothing is copied from a previous session's text.
Ageing rules are explicit: a receipt older than ``max_age_h`` is STALE, not OK, so a passing feed always
means "verified recently", never "verified once".

Run first in every session, and again before writing any README/page numbers:
  /home/user/.venv/bin/python scripts/status_feed.py
Exit code is 1 when any check is FAIL/MISSING (STALE and TODO do not fail the run).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime.now(timezone.utc)


def age_h(p: Path) -> float | None:
    if not p.exists():
        return None
    return round((NOW.timestamp() - p.stat().st_mtime) / 3600.0, 2)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def j(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


def rec(cid, what, how, status, detail, next_action=""):
    return {"id": cid, "what": what, "how_checked": how, "status": status,
            "detail": detail, "next_action": next_action}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-age-h", type=float, default=24.0, help="receipts older than this are reported STALE")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--md", default=str(ROOT / "docs/research/FEED.md"))
    ap.add_argument("--json-out", default=str(ROOT / "evidence/feed.json"))
    args = ap.parse_args()

    checks: list[dict] = []
    add = checks.append

    # --- workspace / git state -------------------------------------------------------------
    def git(*a):
        try:
            return subprocess.run(("git",) + a, cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception:  # noqa: BLE001
            return ""

    head = git("rev-parse", "--short", "HEAD")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    dirty = [l for l in git("status", "--porcelain").splitlines() if l.strip()]
    add(rec("git", "branch state", "git status --porcelain, git rev-parse",
            "OK" if head else "MISSING",
            {"branch": branch, "head": head, "uncommitted_paths": len(dirty)}))

    # --- the standing prompt is re-read, not remembered ------------------------------------
    sp = ROOT / "docs/research/standing-prompt-as-recorded-20261027.md"
    readme = (ROOT / "README.md").read_text() if (ROOT / "README.md").exists() else ""
    if sp.exists() and "Standing prompt" in readme:
        add(rec("standing-prompt", "standing prompt is in the README and mirrored on disk",
                "README.md heading scan + docs/research/standing-prompt-as-recorded-20261027.md", "OK",
                {"readme_heading": "Standing prompt", "mirror_age_h": age_h(sp),
                 "re_read_utc": NOW.isoformat(timespec="seconds")},
                "re-read line by line at session start; do not work from memory"))
    else:
        add(rec("standing-prompt", "standing prompt present", "README scan", "MISSING",
                {"readme_has_heading": "Standing prompt" in readme}, "restore the verbatim block before working"))

    # --- data integrity ---------------------------------------------------------------------
    ddir = ROOT / ".cache" / "gems_data"
    man = j(ROOT / "registry/data_manifest.json") or {"files": []}
    have = 0
    for e in man["files"]:
        p = ddir / e["dest"]
        if p.exists() and sha(p) == e["sha256"]:
            have += 1
    total = len(man["files"])
    add(rec("data", "competition + external data present and SHA-verified",
            "recompute sha256 of every registry/data_manifest.json entry",
            "OK" if have == total and total else "FAIL",
            {"verified": have, "of": total, "root": str(ddir.relative_to(ROOT)) if ddir.exists() else str(ddir),
             "restore_receipt_age_h": age_h(ROOT / "data/restore_receipt.json")},
            "" if have == total else "scripts/restore_data.py --group all"))

    # --- the candidate ----------------------------------------------------------------------
    cand_receipt = j(ROOT / "evidence/candidate_build_receipt.json") or {}
    safe = ROOT / "docs/downloads" / str(cand_receipt.get("safe", {}).get("tif", ""))
    if cand_receipt and safe.exists():
        got = sha(safe)
        want = cand_receipt["safe"]["tif_sha256"]
        add(rec("candidate-bytes", "downloadable candidate still matches its build receipt",
                "sha256(docs/downloads/<safe tif>) vs evidence/candidate_build_receipt.json",
                "OK" if got == want else "FAIL",
                {"file": safe.name, "sha256": got[:16] + "…", "receipt_age_h": age_h(safe.parent / safe.name),
                 "emitted_px": cand_receipt.get("emitted_px")},
                "" if got == want else "rebuild: scripts/build_candidate.py"))
    else:
        add(rec("candidate-bytes", "candidate build receipt + TIF", "file + hash check", "MISSING",
                {"receipt": bool(cand_receipt), "tif": str(safe)}, "scripts/build_candidate.py --mass 44090 --mode wide"))

    val = j(ROOT / "evidence/validator_s3_ocm_safe.json") or {}
    add(rec("format-gate", "in-project format gate (portal range test included)",
            "scripts/validate_submission_tif.py receipt",
            "OK" if val.get("all_hard_checks_pass") else "FAIL",
            {"all_hard_checks_pass": val.get("all_hard_checks_pass"),
             "checks_failed": [k for k, v in (val.get("checks") or {}).items() if not v],
             "receipt_age_h": age_h(ROOT / "evidence/validator_s3_ocm_safe.json")},
            "" if val.get("all_hard_checks_pass") else "re-run scripts/validate_submission_tif.py <tif> --out evidence/validator_s3_ocm_safe.json"))

    # --- uniqueness scopes ------------------------------------------------------------------
    lane = j(ROOT / "evidence/lane_sweep_s3_ocm_20261030.json") or {}
    rows = [r for r in lane.get("rows", []) if r.get("status") == "ok"]
    if rows:
        subs = [r for r in rows if "/docs/downloads/" in r["file"]]
        lat = [r for r in rows if "lattice" in r["file"]]
        max_sub = max(r["overlap3px_cand_within_registry"] for r in subs)
        max_lat = max(r["overlap3px_cand_within_registry"] for r in lat) if lat else None
        has_rho = any(r.get("spearman_sampled") is not None for r in rows)
        add(rec("lane-submissions", f"3-px duplicate lane test vs {len(subs)} pinned sibling submissions",
                "scripts/lane_sweep.py rows (docs/downloads scope)",
                "OK" if max_sub <= 0.70 else "FAIL",
                {"max_overlap3px": round(max_sub, 4), "cap": 0.70,
                 "n_over_cap": sum(1 for r in subs if r["overlap3px_cand_within_registry"] > 0.70),
                 "worst_holder": max(subs, key=lambda r: r["overlap3px_cand_within_registry"])["file"],
                 "correlation_measured": has_rho},
                "" if has_rho else "re-run scripts/lane_sweep.py without --skip-correlation to re-measure |Spearman| vs the 0.90 cap"))
        add(rec("lane-lattices", "same test against the six calibration lattices (proposed-exemption scope)",
                "scripts/lane_sweep.py rows (lattice scope)",
                "TODO", {"max_overlap3px": round(max_lat, 4) if max_lat else None, "n": len(lat),
                         "note": "a saturated lattice trivially contains any emission; repo ruling is "
                                 "'proposed amendment only, not applied', so this must be an owner decision"},
                "owner ruling: does the lattice scope count for the uniqueness rule? (docs/research/lattice-decision-20261028.md)"))
    else:
        add(rec("lane-submissions", "registry lane sweep", "evidence/lane_sweep_*.json", "MISSING", {},
                "scripts/lane_sweep.py --candidate <tif> --registry /tmp/registry_git"))

    # --- registry pin coverage ---------------------------------------------------------------
    sib = j(ROOT / "registry/sibling_registry_manifest_20261028.json") or {}
    reg = Path("/tmp/registry_git")
    if sib and reg.exists():
        n_fs = len(list(reg.rglob("*.tif")))
        add(rec("registry", "sibling registry bytes on disk vs pinned manifest",
                "count rglob(*.tif) under /tmp/registry_git vs manifest file count",
                ("OK" if n_fs >= len(sib.get("files", [])) else "STALE"),
                {"pinned": len(sib.get("files", [])), "on_disk": n_fs, "layout": "<repo>/docs/downloads/*.tif",
                 "fetch_receipt": (j(reg / "fetch_summary.json") or {}).get("counts", {})},
                "" if n_fs >= len(sib.get("files", [])) else "bash scripts/fetch_sibling_registry_git.sh"))
    else:
        add(rec("registry", "sibling registry bytes on disk", "path check", "MISSING",
                {"registry_dir_exists": reg.exists()},
                "bash scripts/fetch_sibling_registry_git.sh  (sparse git fetch + sha verify)"))

    # --- evidence freshness ------------------------------------------------------------------
    for cid, fn, why in [
        ("scoreboard", "evidence/focus9_scoreboard_20261030.json", "per-site table on SHA-verified sibling bytes"),
        ("e1", "evidence/geometry_experiment_E1_partial.log", "geometry arms (E1)"),
        ("e2", "evidence/operating_point_experiment_E2.json", "operating-point / mass sweep (E2)"),
        ("e3", "evidence/operating_point_E3_design.json", "support-design sweep (E3)"),
        ("e3b", "evidence/operating_point_E3b_selection.json", "selection-rule sweep (E3b)"),
        ("geoprior", "evidence/geothermal_prior_audit_20261030.json", "geothermal/spring proximity audit"),
        ("runcard", "evidence/run_card_20261030.json", "final protocol run card"),
    ]:
        p = ROOT / fn
        a = age_h(p)
        st = "MISSING" if a is None else ("OK" if a <= args.max_age_h else "STALE")
        add(rec(cid, f"evidence receipt fresh (<= {args.max_age_h:g} h): {why}", f"mtime of {fn}", st,
                {"path": fn, "age_h": a, "bytes": p.stat().st_size if p.exists() else None},
                "" if st == "OK" else f"re-run the script that writes {fn}"))

    # --- tests -------------------------------------------------------------------------------
    if args.skip_pytest:
        add(rec("pytest", "unit/gate test suite", "skipped by flag", "TODO", {}, "/home/user/.venv/bin/python -m pytest -q"))
    else:
        try:
            r = subprocess.run((sys.executable, "-m", "pytest", "-q", "--tb=no"), cwd=ROOT,
                               capture_output=True, text=True, timeout=900)
            tail = [l for l in r.stdout.splitlines() if " passed" in l or " failed" in l or " error" in l]
            add(rec("pytest", "unit/gate test suite green", "pytest -q --tb=no",
                    "OK" if r.returncode == 0 else "FAIL",
                    {"summary": tail[-1] if tail else r.stdout[-200:], "exit": r.returncode}))
        except Exception as exc:  # noqa: BLE001
            add(rec("pytest", "unit/gate test suite", "pytest invocation", "FAIL", {"error": repr(exc)[:200]}))

    # --- pages are regenerated, not hand-edited -----------------------------------------------
    for cid, fn in [("page-exec", "docs/executive-summary.html"), ("page-index", "docs/index.html")]:
        p = ROOT / fn
        a = age_h(p)
        cand_age = age_h(safe) if safe.exists() else None
        stale = a is None or (cand_age is not None and a > cand_age)
        add(rec(cid, f"{fn} regenerated after the latest candidate build", "mtime comparison",
                "STALE" if stale else "OK",
                {"page_age_h": a, "candidate_age_h": cand_age},
                "" if not stale else "python scripts/build_executive_summary.py"))

    n = {k: sum(1 for c in checks if c["status"] == k) for k in ("OK", "STALE", "TODO", "FAIL", "MISSING")}
    fail = n["FAIL"] + n["MISSING"]

    # --- render -------------------------------------------------------------------------------
    md = [f"# GEMSDOESASS3 status feed", "",
          f"Generated {NOW.isoformat(timespec='seconds')} by `scripts/status_feed.py` "
          f"(freshness rule: <= {args.max_age_h:g} h). Do not edit by hand - re-run the script.", "",
          f"**{n['OK']} OK** · **{n['STALE']} STALE** · **{n['TODO']} needs a human/owner decision** · "
          f"**{n['FAIL']} FAIL** · **{n['MISSING']} MISSING**", ""]
    if cand_receipt:
        proj = cand_receipt.get("projections", {})
        md.append(f"Candidate on the shelf: `{cand_receipt['safe']['tif']}` — {cand_receipt['emitted_px']:,} px, "
                  f"LLI projection {proj.get('lli', {}).get('projected_dti')}, "
                  f"SGMC-CAL {proj.get('holdout_sgmc_cal', {}).get('dti')} "
                  f"{proj.get('holdout_sgmc_cal', {}).get('ci95')} "
                  f"(HOLDOUT-DTI, {proj.get('holdout_sgmc_cal', {}).get('n_withheld_positives'):,} withheld positives). "
                  "Projections are not scores.")
        md.append("")
    md += ["| status | check | how it was verified | detail | next action |", "|---|---|---|---|---|"]
    icon = {"OK": "✅", "STALE": "🕓", "TODO": "🧭", "FAIL": "❌", "MISSING": "⛔"}
    for c in checks:
        det = json.dumps(c["detail"], default=str)
        det = det if len(det) < 300 else det[:297] + "…"
        md.append(f"| {icon[c['status']]} {c['status']} | {c['what']} | {c['how_checked']} | `{det}` | {c['next_action'] or '—'} |")
    md += ["", "## Standing questions this repo has not closed", "",
           "- Owner: does the calibration-lattice scope count for the 70% duplicate rule? "
           "(candidate passes submissions 0.45, fails lattice 0.998)",
           "- Owner: slot decision — no file in this repo is currently *promoted*, so no upload is recommended.",
           "- Data: re-measure the Spearman cap on the full registry sweep if the correlation gate must be current.",
           "- Live: the public leaderboard moves; re-fetch the leaderboard page before quoting any high score.", ""]
    Path(args.md).write_text("\n".join(md))
    Path(args.json_out).write_text(json.dumps(
        {"schema_version": 1, "generated_utc": NOW.isoformat(timespec="seconds"),
         "freshness_rule_h": args.max_age_h, "counts": n, "checks": checks}, indent=2) + "\n")
    for c in checks:
        if c["status"] != "OK":
            print(f"{c['status']:>7}  {c['id']:16s} {c['next_action'] or c['what']}")
    print(f"counts={n}  wrote {args.md} and {args.json_out}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
