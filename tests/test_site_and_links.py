"""Pass-2 & Pass-3 verification tests for GitHub Pages HTML, relative assets, sibling URLs, and README."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docs_pages_and_relative_links():
    docs = ROOT / "docs"
    for page_name in ("index.html", "executive-summary.html"):
        page = docs / page_name
        assert page.exists() and page.stat().st_size > 1_000
        txt = page.read_text()

        # Browser-facing code must never call localhost or 127.0.0.1
        assert "localhost" not in txt.lower()
        assert "127.0.0.1" not in txt

        # Every relative href/src must exist on disk inside docs/
        refs = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', txt)
        for ref in refs:
            if ref.startswith(("http://", "https://", "#", "mailto:", "javascript:")):
                continue
            clean_ref = ref.split("#")[0].split("?")[0]
            if not clean_ref:
                continue
            target = docs / clean_ref
            assert target.exists(), f"Broken relative link in {page_name}: {ref} -> {target}"
            assert target.stat().st_size > 0, f"Empty target file for {ref}"


def test_sibling_focus9_urls_verified_against_clones():
    """Every buffedlizard55-lab sibling link on the public pages must resolve in the sibling checkouts.

    Skips with a visible reason (not a silent pass) when the checkouts are absent. Set GEMS_SIB_ROOT
    to the directory that holds x_gNN/GEMSDOEnn-main trees (default /tmp/sib).
    """
    import os
    import pytest

    sib_root = Path(os.environ.get("GEMS_SIB_ROOT", "/tmp/sib"))
    if not sib_root.exists():
        pytest.skip(f"sibling checkouts not present at {sib_root}; set GEMS_SIB_ROOT")
    txt = (ROOT / "docs" / "index.html").read_text()
    urls = sorted(
        set(
            re.findall(
                r"https://github\.com/buffedlizard55-lab/(GEMSDOE\d+)/(?:raw|blob)/main/([^\s\"'<>]+)",
                txt,
            )
        )
    )
    missing = []
    for repo, rel in urls:
        num = repo[len("GEMSDOE"):]
        if not (sib_root / f"x_g{num}" / f"{repo}-main" / rel).exists():
            missing.append(f"{repo}/{rel}")
    assert not missing, f"Missing sibling artifacts: {missing}"


def test_no_broken_sassnarep3_sibling_links_remain():
    """The sassnarep3-star sibling repos return 404. Only correction text may still name them."""
    pages = ["README.md", "index.html", "executive-summary.html", "docs/index.html", "docs/executive-summary.html"]
    for rel in pages:
        for line in (ROOT / rel).read_text().splitlines():
            if "CORRECTED 2026-10-28" in line or "WRONG" in line:
                continue
            assert not re.search(r"github\.com/sassnarep3-star/GEMSDOE\d+/", line), f"{rel}: {line[:120]}"



def test_readme_contains_standing_prompt_and_synchronized_runcard():
    """The README must stay synchronised with the candidate it documents.

    Changed 2026-10-31 (second time): the decision moved from "portal-safe file, NOT CLEARED" to
    "this file is cleared", so the synced receipt is the current model receipt. Name, note and SHA
    are read out of that receipt, so the test cannot drift from the decision, and the verbatim
    standing-prompt phrase and the competition URL are still required.
    """
    rec = json.loads((ROOT / "evidence" / "blockinversion_model_20261031.json").read_text())
    sub = rec["submission"]
    readme = (ROOT / "README.md").read_text()
    assert sub["submission_name"] in readme
    assert sub["submission_note"] in readme
    assert sub["raster_sha256"] in readme
    assert "MUST GENERATE A UNIQUE TIFF SUBMISSION" in readme or "UNIQUE TIF SUBMISSION" in readme
    assert "https://www.drivendata.org/competitions/306/competition-doe-gems/" in readme
