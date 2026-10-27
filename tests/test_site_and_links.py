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
        assert page.exists() and page.stat().st_size > 5_000
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
    ref_root = Path("/tmp/ref_repos")
    if not ref_root.exists():
        return
    txt = (ROOT / "docs" / "index.html").read_text()
    urls = sorted(
        set(
            re.findall(
                r"https://github\.com/sassnarep3-star/(GEMSDOE\d+)/(?:raw|blob)/main/([^\s\"'<>]+)",
                txt,
            )
        )
    )
    assert len(urls) == 18
    for repo, rel in urls:
        local_p = ref_root / repo / rel
        assert local_p.exists(), f"Missing verified sibling artifact {repo}/{rel}"


def test_readme_contains_standing_prompt_and_synchronized_runcard():
    rc = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    readme = (ROOT / "README.md").read_text()
    assert rc["submission_name"] in readme
    assert rc["submission_note"] in readme
    assert rc["raster_sha256"] in readme
    assert "PARALLEL-RUN PROTOCOL" in readme
    assert "MUST GENERATE A UNIQUE TIF SUBMISSION" in readme
    assert "https://www.drivendata.org/competitions/306/competition-doe-gems/" in readme
