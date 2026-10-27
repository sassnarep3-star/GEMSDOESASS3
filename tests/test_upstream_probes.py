import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import probe_upstream

ROOT = Path(__file__).resolve().parents[1]


def test_rejects_unpinned_and_dirty_upstream_without_running_code(monkeypatch, tmp_path):
    def wrong_commit(*args, **kwargs):
        return SimpleNamespace(stdout="not-the-pinned-commit\n")
    monkeypatch.setattr(probe_upstream.subprocess, "run", wrong_commit)
    with pytest.raises(ValueError, match="expected unmodified"):
        probe_upstream.probe(tmp_path)
    responses = iter([SimpleNamespace(stdout=probe_upstream.PIN + "\n"),
                      SimpleNamespace(stdout=" M src/gems32/holdout.py\n")])
    monkeypatch.setattr(probe_upstream.subprocess, "run", lambda *a, **kw: next(responses))
    with pytest.raises(ValueError, match="worktree is not clean"):
        probe_upstream.probe(tmp_path)


def test_recorded_probes_are_synthetic_and_blocking():
    report = json.loads((ROOT / "evidence/upstream_probe.json").read_text())
    assert report["template_commit"] == probe_upstream.PIN
    assert report["writer"]["forwarded_binary_mask"] == [[1, 1], [0, 0]]
    assert report["empty_truth_holdout"]["fold_false_positive_mass"] == 1
    assert report["empty_truth_holdout"]["pooled_block_false_positive_mass"] == 0
    assert report["surface_gate"]["preview_dot_overlap"] == 1
    assert report["surface_gate"]["gate_returned_pass"]
    assert not report["upstream_modified"]
    assert "no geological experiment" in report["kind"]


def test_probe_cli_cannot_write_to_template(monkeypatch, tmp_path):
    import sys
    source = tmp_path / 'scripts/evaluate_holdout.py'
    source.parent.mkdir(); source.write_text('original')
    monkeypatch.setattr(sys, 'argv', ['probe_upstream.py', '--template-dir', str(tmp_path), '--out', str(source)])
    assert probe_upstream.main() == 1
    assert source.read_text() == 'original'
