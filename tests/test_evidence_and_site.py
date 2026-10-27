import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]


def strict_json(path):
    def reject(value):
        raise ValueError(f"non-standard JSON constant {value}")
    return json.loads((ROOT / path).read_text(), parse_constant=reject)


def test_run_card_remains_negative_and_contains_real_evidence():
    card = strict_json("evidence/h1-run-card.json")
    assert card["verdict"] == "negative" and card["ok_to_submit"] is False
    assert card["experiments_used"] == 1 and card["weekly_slots_used"] == 0
    assert card["raster_sha256"] is None and card["submission_name"] is None
    assert all(card["validator_output"][x] is None for x in
               ("no_nan_inside", "range_0_1", "crs_shape_transform_match"))
    assert len(card["note"]) <= 140
    overlap = card["correlation_overlap_vs_registry"]
    assert overlap["duplicate"] and overlap["fraction_of_positive_surface_within_3px"] == 1.0
    assert "NOT RUN" in overlap["final_dot_comparison"]
    evaluation = card["holdout_dti"]
    assert evaluation["evidence_class"] == "HOLDOUT-DTI"
    assert evaluation["evaluator_version"] == "gems57-pooled-hide-v2"
    h1 = evaluation["scores"]["h1_surface"]
    terrain = evaluation["scores"]["terrain_control"]
    assert h1["withheld_positive_pixels"] == terrain["withheld_positive_pixels"] == 60988
    assert h1["dti"] < terrain["dti"]
    assert h1["ci95"][0] <= h1["dti"] <= h1["ci95"][1]
    assert evaluation["paired_differences"]["terrain_control"]["ci95"][1] < 0
    original = card["feature_canaries"]["rows"]
    raw = card["post_stop_verification"]["raw_input_canaries"]
    assert len(original) == 40 and len(raw) == 8
    for row in original + raw:
        assert row["direction_free_auc"] == pytest.approx(max(row["auc"], 1 - row["auc"]))
        assert row["direction_free_auc"] <= .90
    assert {r["feature"] for r in raw} == {"raw_rtp", "raw_detrended_elevation"}
    verification = card["post_stop_verification"]["independent_overlap_verification"]
    assert verification["measurements_agree"] and verification["independent_overlap"] == 1
    assert verification["surface_sha256"] == card["surface_sha256"]
    for key in ("audit_file",):
        path = ROOT / verification[key]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == verification["audit_sha256"]
    raw_path = ROOT / card["post_stop_verification"]["audit_file"]
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == card["post_stop_verification"]["audit_sha256"]


def test_nine_historical_audit_matches_pinned_manifest_and_is_never_recommended():
    audit, manifest = strict_json("docs/data/focus-nine-audit.json"), strict_json("registry/focus-nine.json")
    assert audit["reported_values_are_not_organizer_receipts"]
    expected = {r["site"]: r for r in manifest["rows"]}
    assert set(expected) == {f"GEMSDOE{x}" for x in (24, 25, 27, 28, 30, 31, 32, 33, 36)}
    assert len(audit["rows"]) == 9
    for row in audit["rows"]:
        pinned = expected[row["site"]]
        assert row["sha256"] == pinned["sha256"] and row["ref"] == pinned["ref"]
        assert len(row["sha256"]) == 64 and row["reported_value"] == pinned["reported_value"]
        assert row["max_fraction_within_3px"] > .70
        assert row["unique_by_protocol_among_these_nine"] is False
        assert row["estimated_organizer_score"] is None and "AUDIT ONLY" in row["recommendation"]
        assert len(row["overlap_by_other_site"]) == 8
    by_site = {r["site"]: r for r in audit["rows"]}
    assert "GEMSDOE30" in by_site["GEMSDOE25"]["exact_support_matches_within_nine"]
    lineage = audit["h33_lineage"]
    assert lineage["removed_pixels"] == lineage["removed_within_2px_of_catalogue"] == 2545
    assert lineage["added_pixels"] == lineage["removed_outside_2px_of_catalogue"] == 0


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.ids = set()
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d: self.ids.add(d["id"])
        for key in ("href", "src"):
            if key in d: self.links.append((tag, d[key]))


def test_local_site_links_resolve_and_download_is_disabled():
    pages = [ROOT / "index.html", ROOT / "executive-summary.html", ROOT / "parallel-h1.html", ROOT / "parallel-h1-guide.html"]
    parsers = {}
    for page in pages:
        parser = Links(); parser.feed(page.read_text()); parsers[page] = parser
    for page, parser in parsers.items():
        for tag, link in parser.links:
            u = urlsplit(link)
            if u.scheme or u.netloc: continue
            target = (page.parent / unquote(u.path)).resolve() if u.path else page
            if target.is_dir(): target = target / "index.html"
            assert target.exists(), f"{page.name}: broken {tag} link {link}"
            if u.fragment and target in parsers:
                assert u.fragment in parsers[target].ids, f"{page.name}: missing #{u.fragment}"
    home = pages[0].read_text()
    assert "DO NOT SUBMIT" in home.upper() and "Submission file unavailable" in home
    assert not any(link.lower().endswith((".tif", ".zip")) for _, link in parsers[pages[0]].links)
    assert "0.2778" in home and "user-reported" in home.lower()
    assert "0.4544" in home and "27 October 2026" in home
    assert not list(ROOT.glob("*.tif"))


def test_earlier_reviews_are_preserved_but_clearly_superseded():
    for path in ("docs/EXECUTIVE_SUMMARY.md", "docs/review-2026-10-27.md"):
        text = (ROOT / path).read_text()
        assert "Historical preliminary review" in text[:400]
        assert "h1-run-card.json" in text[:400]
    legacy = (ROOT / "docs/index.html").read_text()
    assert "ARCHIVED REVIEW" in legacy and "../index.html" in legacy
    assert "h1-run-card.json" in legacy
    old = strict_json("evidence/negative_run_card.json")
    assert old["verdict"] == "negative" and old["raster_sha256"] is None
    guide = (ROOT / "executive-summary.html").read_text()
    assert "policies conflict" in guide and "does not establish compliance" in guide
