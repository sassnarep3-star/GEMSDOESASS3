from pathlib import Path
import math

import numpy as np
import pytest
from scipy.stats import spearmanr

from audit_focus import binary_spearman
from registry_preflight import bound, evaluate
from restore_audit_inputs import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def test_strict_70_percent_boundary():
    equal = bound(10, 3, 20)
    assert equal["minimum_overlapping_dots"] == 7
    assert equal["minimum_overlap_fraction"] == 0.7
    assert equal["forced_duplicate_stop"] is False
    assert equal["first_forced_stop_budget"] == 11
    above = bound(11, 3, 20)
    assert above["minimum_overlapping_dots"] == 8
    assert above["forced_duplicate_stop"] is True


def test_no_proof_does_not_claim_pass():
    no_proof = bound(3, 5, 20)
    assert no_proof["minimum_overlapping_dots"] == 0
    assert no_proof["forced_duplicate_stop"] is False
    assert "NOT a novelty pass" in no_proof["interpretation"]
    assert bound(3, 20, 20)["first_forced_stop_budget"] is None
    assert bound(1, 0, 20)["forced_duplicate_stop"] is True


@pytest.mark.parametrize("k,u,total", [(0, 0, 10), (11, 0, 10), (1, -1, 10),
                                      (1, 11, 10), (1, 0, 0), (True, 0, 10), (1.0, 0, 10)])
def test_reject_invalid_counts(k, u, total):
    with pytest.raises(ValueError):
        bound(k, u, total)


def test_binary_spearman_agrees_with_scipy_ties():
    rng = np.random.default_rng(123)
    a = rng.random((25, 30)) < 0.15
    b = rng.random((25, 30)) < 0.2
    fp = rng.random((25, 30)) > 0.25
    assert binary_spearman(a, b, fp) == pytest.approx(spearmanr(a[fp], b[fp]).statistic)
    assert binary_spearman(a, a, fp) == pytest.approx(1.0)
    assert binary_spearman(np.zeros_like(a), b, fp) is None
    with pytest.raises(ValueError):
        binary_spearman(a, b, np.zeros_like(fp))


@pytest.mark.skipif(not (ROOT / "data/raw/template.tif").exists(), reason="pinned mirrors not restored")
def test_real_lattice_witness_reproduces_bound():
    template = ROOT / "data/raw/template.tif"
    lattice = ROOT / "data/raw/lattice.tif"
    assert sha256_file(template) == "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
    assert sha256_file(lattice) == "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
    result = evaluate(template, lattice, 37654)
    assert result["footprint_pixels"] == 5167373
    assert result["covered_footprint_pixels"] == 5160724
    assert result["uncovered_pixels"] == 6649
    assert result["minimum_overlapping_dots"] == 31005
    assert math.isclose(result["minimum_overlap_fraction"], 31005 / 37654)
    assert result["first_forced_stop_budget"] == 22164
    assert result["forced_duplicate_stop"] is True


def test_preflight_output_cannot_overwrite_verified_input(monkeypatch, tmp_path):
    import sys
    import hashlib
    import registry_preflight
    t, w = tmp_path / 'template.tif', tmp_path / 'witness.tif'
    t.write_bytes(b'template'); w.write_bytes(b'witness')
    entries = [{'id': 'template', 'destination': t.name, 'sha256': hashlib.sha256(t.read_bytes()).hexdigest()},
               {'id': 'lattice', 'destination': w.name, 'sha256': hashlib.sha256(w.read_bytes()).hexdigest()}]
    monkeypatch.setattr(registry_preflight, 'load_manifest', lambda: {'files': entries})
    monkeypatch.setattr(registry_preflight, 'MANIFEST', tmp_path / 'manifest.json')
    monkeypatch.setattr(sys, 'argv', ['registry_preflight.py', '--data-dir', str(tmp_path), '--out', str(w)])
    assert registry_preflight.main() == 1
    assert w.read_bytes() == b'witness'
