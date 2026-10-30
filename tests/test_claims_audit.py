"""Every number asserted in prose must reconcile with an evidence receipt.

`scripts/claims_audit.py` pins each claim to the receipt it came from (value equality) and to the documents that
render it (string presence). This test runs it in-process, so a stale digit in the README, the lane report or a
generated page fails CI rather than shipping. Exit conditions are the script's: value mismatch OR missing prose.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("claims_audit", ROOT / "scripts" / "claims_audit.py")
ca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ca)


def test_every_pinned_claim_matches_its_receipt():
    rows = list(ca.build_claims())
    bad = [c[0] for c in rows if c[1] != c[2]]
    assert rows, "no claims pinned"
    assert len(rows) >= 45, f"the claim set shrank to {len(rows)}; do not thin this audit to make it pass"
    assert not bad, f"receipt/prose value drift: {bad}"


def test_every_pinned_claim_is_actually_rendered_in_the_docs():
    texts = {p: (ROOT / p).read_text() for p in ca.PROSE if (ROOT / p).is_file()}
    missing = []
    for cid, _receipt, _expect, renderings, _note in ca.build_claims():
        if not renderings:
            continue
        if not any(any(s in t for s in renderings) for t in texts.values()):
            missing.append(cid)
    assert not missing, f"claims present in receipts but not rendered in README/report/pages: {missing}"


def test_audit_script_writes_a_clean_receipt_and_exits_zero():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/claims_audit.py"),
                           "--out", "/tmp/claims_audit_ci.json"],
                          cwd=ROOT, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = json.loads(Path("/tmp/claims_audit_ci.json").read_text())
    assert out["mismatches"] == []
    assert out["claims"] == out["reconciled"] > 0
    # the two classes of number we can never verify locally must stay declared as such
    ids = {e["claim"][:20] for e in out["external_claims_not_locally_verifiable"]}
    assert any("leaderboard" in c for c in ids), out["external_claims_not_locally_verifiable"]
