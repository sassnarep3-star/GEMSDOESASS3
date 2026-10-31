"""Shared test helpers.

Policy lock, 2026-10-31: the repository may promote exactly one raster, and the promotion must be
backed by the current model receipt. Tests that used to assert "no file may say OK TO SUBMIT" now
assert the stronger, still fail-closed property: an approval banner is only legal when the same page
names the receipt-cleared file. Nothing is weakened - an unbacked banner still fails.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "evidence" / "blockinversion_model_20261031.json"


def cleared_name() -> str:
    """The single raster the current receipt clears (fails loudly if the receipt is missing)."""
    return json.loads(RECEIPT.read_text())["submission"]["submission_name"]


def assert_no_unbacked_approval(html: str, where: str = "") -> None:
    low = html.lower()
    if "ok to submit" in low:
        assert cleared_name() in html, f"{where}: approval banner without the receipt-cleared file"


def assert_names_retired(html: str, names: tuple[str, ...], where: str = "") -> None:
    low = html.lower()
    for n in names:
        assert n in html, f"{where}: retired raster {n} is not named"
    assert "not ok to submit" in low or "superseded" in low, where
