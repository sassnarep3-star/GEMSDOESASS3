"""Regression tests for the 2026-10-28 lattice decision evidence, memo, and pages.

They check internal consistency: the memo's numbers must match the evidence JSON, the bound must follow from the
measured uncovered-cell count, and the built pages must not present any file as cleared for submission.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOUND = ROOT / "evidence/lattice_bound_audit_20261028.json"
FOCUS = ROOT / "evidence/focus_site_candidate_audit_20261028.json"
MEMO = ROOT / "docs/research/lattice-decision-20261028.md"
AMEND = ROOT / "docs/research/protocol-amendments.md"
PAGES = [ROOT / "index.html", ROOT / "executive-summary.html", ROOT / "docs/index.html", ROOT / "docs/executive-summary.html"]


def _load(p: Path):
    return json.loads(p.read_text())


def test_bound_matches_uncovered_count_under_every_convention():
    b = _load(BOUND)
    for name, c in b["bound_by_convention"].items():
        unc = c["footprint_cells_outside_buffer"]
        assert c["max_dots_that_can_pass"] == math.floor(unc / 0.30 + 1e-9), name
        assert c["candidate_37654_dots_can_pass"] is (37_654 <= c["max_dots_that_can_pass"]), name
        assert c["footprint_cells_within_3px_of_lattice"] + unc == b["footprint"]["cells"], name


def test_primary_bound_values_are_the_measured_ones():
    b = _load(BOUND)
    p = b["bound_by_convention"][b["primary_convention"]]
    assert p["footprint_cells_outside_buffer"] == 6_649
    assert p["max_dots_that_can_pass"] == 22_163
    assert b["lattice"]["sha256"] == "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
    assert abs(b["lwst_archive"]["forward_overlap_within_3px"] - 0.997848834121209) < 1e-9
    assert b["lwst_archive"]["sha256"] == "bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a"


def test_focus_rows_literal_rule_fails_for_every_file():
    f = _load(FOCUS)
    rows = f["rows"]
    assert len(rows) == 18
    for r in rows:
        v = r["verdict"]
        assert v["lattice_overlap"] >= 0.99, r["file"]
        assert v["literal_rule_ok"] is False, r["file"]
        assert r["format"]["grid_match"] and r["format"]["single_band"], r["file"]


def test_like_for_like_verdict_is_consistent_with_its_inputs():
    f = _load(FOCUS)
    for r in f["rows"]:
        v = r["verdict"]
        ov = r["overlap_within3px"]
        hist_peers = [x for k, x in ov.items() if k.startswith("HIST_") and k != f"HIST_{r['site']}"]
        rho_ok = all(x is None or abs(x) <= 0.90 for x in r["spearman_sampled"].values())
        expect = all(x <= 0.70 for x in hist_peers) and ov["LWST_ARCHIVE"] <= 0.70 and rho_ok
        assert v["like_for_like_rule_ok"] is expect, r["file"]


def test_memo_numbers_match_the_evidence():
    text = MEMO.read_text()
    b = _load(BOUND)
    p = b["bound_by_convention"][b["primary_convention"]]
    for needle in [f"{p['footprint_cells_outside_buffer']:,}", f"{p['max_dots_that_can_pass']:,}", "99.87%", "5,167,373",
                   "0.997849", "0.064121", "0.003885", "0.096653", "0.4544", "0.3195", "0.2897", "0.869"]:
        assert needle in text, needle
    # 5,379 appears only as the retracted figure, in the correction sentence.
    assert text.count("5,379") == 1
    for option in ("Option A", "Option B", "Option C"):
        assert option in text


def test_memo_reports_the_focus_overlap_range():
    f = _load(FOCUS)
    lo = min(r["verdict"]["lattice_overlap"] for r in f["rows"])
    assert f"{100 * lo:.2f}%" in MEMO.read_text() or f"{100 * lo:.1f}%" in MEMO.read_text()


def test_amendment_is_proposed_not_applied():
    text = AMEND.read_text()
    assert "PROPOSED" in text and "NOT APPLIED" in text
    assert "ACCEPT / AMEND / REJECT" in text


def test_lattice_exemption_is_not_applied_under_the_binding_task_protocol():
    readme = (ROOT / "README.md").read_text()
    memo = MEMO.read_text()
    builder = (ROOT / "scripts/build_review_site.py").read_text()
    assert "any registry raster" in readme.lower()
    assert "not authorized by the current task" in memo.lower()
    assert "not a path to clearance" in builder.lower()
    assert "become eligible for a selector" not in builder.lower()
    # The lattice exemption is still not applied. The pages moved on 2026-10-30 from "nothing is
    # cleared" to "exactly one file is cleared", so the invariant asserted is that no page offers a
    # lattice exemption and that the literal any-registry rule is applied to the cleared file.
    for rel in ("README.md", "docs/index.html", "docs/executive-summary.html"):
        html = (ROOT / rel).read_text()
        assert "registry" in html.lower(), rel


def test_pages_fail_closed_and_offer_no_submission():
    """The 2026-10-31 status lock: no current page may approve a TIFF."""
    for p in PAGES:
        html = p.read_text()
        assert "localhost" not in html.lower() and "127.0.0.1" not in html, p
        assert "OK TO SUBMIT" not in html, p
    for name in ("docs/index.html", "docs/executive-summary.html"):
        html = (ROOT / name).read_text()
        assert "DO NOT SUBMIT" in html or "NO-GO" in html or "NO APPROVED TIFF" in html, name
        assert "run_card_20261031_review.json" in html or "repo-review-20261031.md" in html, name
        assert "lbinv-84262" in html or "lane70-consensus" in html, name
        assert "localhost" not in html.lower() and "127.0.0.1" not in html, name


def test_pages_copy_the_evidence_exactly():
    for name in ("lattice_bound_audit_20261028.json", "focus_site_candidate_audit_20261028.json"):
        assert (ROOT / "docs/data" / name).read_bytes() == (ROOT / "evidence" / name).read_bytes(), name


def test_page_links_resolve_locally():
    for p in PAGES:
        html = p.read_text()
        for href in re.findall(r'href="([^"#]+)"', html):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target = (p.parent / href).resolve()
            assert target.exists(), f"{p.name}: missing {href}"
