from html.parser import HTMLParser
import io
import hashlib
import json
from pathlib import Path

import pytest

from restore_audit_inputs import load_manifest, restore

ROOT = Path(__file__).resolve().parents[1]


def entry(payload=b"content"):
    return dict(id="test", repo="owner/repo", ref="a" * 40, path="data/file.tif",
                destination="file.tif", sha256=hashlib.sha256(payload).hexdigest())


def test_restore_hash_verifies_and_uses_cache(tmp_path, monkeypatch):
    calls = []
    def fake(request, timeout):
        calls.append(request.full_url)
        return io.BytesIO(b"content")
    monkeypatch.setattr("restore_audit_inputs.urlopen", fake)
    assert restore(entry(), tmp_path) == "restored & verified"
    assert (tmp_path / "file.tif").read_bytes() == b"content"
    assert restore(entry(), tmp_path) == "verified cached"
    assert len(calls) == 1


def test_restore_bad_hash_never_replaces_existing(tmp_path, monkeypatch):
    existing = tmp_path / "file.tif"; existing.write_bytes(b"old invalid file")
    def fake(request, timeout):
        return io.BytesIO(b"wrong bytes")
    monkeypatch.setattr("restore_audit_inputs.urlopen", fake)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        restore(entry(), tmp_path)
    assert existing.read_bytes() == b"old invalid file"
    assert not (tmp_path / "file.tif.partial").exists()


def test_unsafe_manifest_entry_rejected(tmp_path):
    e = entry(); e["destination"] = "../escape.tif"
    with pytest.raises(ValueError, match="unsafe"):
        restore(e, tmp_path)
    e = entry(); e["ref"] = "main"
    with pytest.raises(ValueError, match="un-pinned"):
        restore(e, tmp_path)
    e = entry(); e["path"] = "../secret"
    with pytest.raises(ValueError, match="unsafe"):
        restore(e, tmp_path)


def test_manifest_and_run_card_are_fail_closed():
    manifest = load_manifest()
    focus = [e for e in manifest["files"] if e["group"] == "focus"]
    assert len(focus) == len({e["id"] for e in focus}) == 9
    card = json.loads((ROOT / "evidence/run_card.json").read_text())
    assert card["verdict"] == "negative"
    assert card["raster_sha256"] is None
    assert card["holdout_dti"]["value"] is None
    assert card["submission_name"] is None
    assert card["submission_note"] is None
    assert card["separate_selector_approval"] is False
    audit = json.loads((ROOT / "evidence/focus_audit.json").read_text())
    assert audit["n_directed_comparisons"] == len(audit["comparisons"]) == 72
    assert audit["all_directed_comparisons_duplicate"]
    assert card["correlation_overlap_vs_registry"]["minimum_historical_directed_3px_overlap"] == audit["min_directed_3px_overlap"]
    assert len(audit["spotchecked_promotions"]) == 4
    assert all(x["literal_duplicate"] for x in audit["spotchecked_promotions"])


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for name in ("href", "src"):
            if name in attrs:
                self.links.append(attrs[name])


@pytest.mark.parametrize("name", ["index.html", "executive-summary.html", "research.html"])
def test_local_static_site_links_exist(name):
    parser = LinkParser(); parser.feed((ROOT / name).read_text())
    for link in parser.links:
        if link.startswith(("#", "https://", "http://", "mailto:")):
            continue
        target = link.split("#", 1)[0].split("?", 1)[0]
        assert (ROOT / target).is_file(), f"{name}: broken local asset {link}"


def test_audit_cli_cannot_overwrite_its_manifest(monkeypatch, tmp_path):
    import sys
    import audit_focus
    manifest = tmp_path / 'manifest.json'; manifest.write_text('original')
    monkeypatch.setattr(audit_focus, 'MANIFEST', manifest)
    monkeypatch.setattr(audit_focus, 'load_manifest', lambda: {'files': []})
    monkeypatch.setattr(sys, 'argv', ['audit_focus.py', '--out', str(manifest)])
    assert audit_focus.main() == 1
    assert manifest.read_text() == 'original'


def test_source_snapshot_cannot_overwrite_its_manifest(monkeypatch, tmp_path):
    import sys
    import refresh_sources
    manifest = tmp_path / 'manifest.json'; manifest.write_text('original')
    monkeypatch.setattr(refresh_sources, 'MANIFEST', manifest)
    monkeypatch.setattr(sys, 'argv', ['refresh_sources.py', '--out', str(manifest)])
    assert refresh_sources.main() == 1
    assert manifest.read_text() == 'original'


def test_parallel_review_snapshots_are_preserved_and_marked_superseded():
    for name in ['docs/index.html', 'docs/submission-guide.html', 'docs/EXECUTIVE_SUMMARY.md', 'docs/review-2026-10-27.md']:
        text = (ROOT / name).read_text()
        assert 'Historical parallel-session' in text
        assert 'DO NOT SUBMIT' in text or 'no file is approved' in text
    old_card = json.loads((ROOT / 'evidence/negative_run_card.json').read_text())
    assert old_card['historical_snapshot'] is True
    assert old_card['superseded_by'] == 'evidence/run_card.json'
    assert old_card['verdict'] == 'negative'


def test_binary_bytes_are_not_transcoded(tmp_path, monkeypatch):
    payload = b'\xff\xfe\x00\x80' * 100
    monkeypatch.setattr('restore_audit_inputs.urlopen', lambda request, timeout: io.BytesIO(payload))
    assert restore(entry(payload), tmp_path) == 'restored & verified'
    assert (tmp_path / 'file.tif').read_bytes() == payload


def test_interrupted_download_keeps_existing_file_and_cleans_partial(tmp_path, monkeypatch):
    existing = tmp_path / 'file.tif'; existing.write_bytes(b'old invalid file')
    class Broken(io.BytesIO):
        def read(self, size=-1):
            raise OSError('interrupted')
    monkeypatch.setattr('restore_audit_inputs.urlopen', lambda request, timeout: Broken())
    with pytest.raises(OSError, match='interrupted'):
        restore(entry(), tmp_path)
    assert existing.read_bytes() == b'old invalid file'
    assert not (tmp_path / 'file.tif.partial').exists()


def test_parallel_bootstrap_uses_the_same_binary_safe_streamer(tmp_path, monkeypatch):
    import bootstrap_template
    payload = b'\xff\x80\x00' * 50
    requests = []
    def fake(endpoint, out, *, timeout):
        requests.append(endpoint); out.write(payload)
    monkeypatch.setattr(bootstrap_template, 'stream_github_raw', fake)
    target = tmp_path / 'input.tif'
    bootstrap_template.fetch_file('repos/owner/repo/contents/a.tif?ref=pinned', target, hashlib.sha256(payload).hexdigest())
    assert target.read_bytes() == payload
    assert len(requests) == 1
