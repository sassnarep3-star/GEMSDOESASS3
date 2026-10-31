"""The published pages must be reproducible from receipts, and projections must stay labelled."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_session_card_reproduces_from_receipts():
    r = subprocess.run([sys.executable, "scripts/verify_session_card.py"], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "checks reproduce" in r.stdout


def test_no_file_is_presented_as_scoring_above_the_champion():
    card = json.loads((ROOT / "evidence/session_card_20261030.json").read_text())
    champion = 0.2778
    for name, v in card["projections"]["files"].items():
        if name == "champion":
            continue
        assert v["projected_lb"] < champion, f"{name} projection claims to beat the champion"


def test_exp3_is_never_marked_submittable():
    card = json.loads((ROOT / "evidence/session_card_20261030.json").read_text())
    assert card["uniqueness"]["exp3_binary_surface"]["passes_rule_1"] is False
    assert "NOT OK" in card["decision"]["blocked"]["reason"] or card["decision"]["blocked"]["file"].endswith(".tif")
    for page in ("docs/index.html", "docs/executive-summary.html"):
        html = (ROOT / page).read_text()
        assert "NOT APPROVED TO SUBMIT" in html
        assert "NOT OK to submit" in html or "DO NOT SUBMIT" in html


def test_downloadable_file_exists_with_matching_sha():
    import hashlib
    card = json.loads((ROOT / "evidence/session_card_20261030.json").read_text())
    p = ROOT / "docs" / "downloads" / card["decision"]["file_to_download"]
    assert p.exists(), p
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    assert h.hexdigest() == card["decision"]["tif_sha256"]
