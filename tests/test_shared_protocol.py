import hashlib
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from gems57 import evaluate_holdout, grid, metric, spatial, uniqueness
from gems57.submission_writer import write_submission


def brute_components(pred, truth):
    """Independent, tiny-grid implementation of the published DTI components."""
    coords = np.argwhere(truth)
    tp = 0.0
    for gy, gx in coords:
        tp += max((pred[y, x] * max(1 - np.hypot(y - gy, x - gx) / 3, 0)
                   for y in range(pred.shape[0]) for x in range(pred.shape[1])), default=0)
    fp = 0.0
    for y in range(pred.shape[0]):
        for x in range(pred.shape[1]):
            q = max((max(1 - np.hypot(y - gy, x - gx) / 3, 0) for gy, gx in coords), default=0)
            fp += pred[y, x] * (1 - q)
    return tp, fp, len(coords) - tp


def test_shared_dti_matches_independent_brute_force_and_multiple_truth_credit():
    p = np.zeros((7, 8))
    p[1, 1], p[2, 3], p[5, 6] = .8, .4, 1.0
    truth = np.zeros_like(p, bool)
    truth[1, 2] = truth[1, 4] = truth[5, 7] = True
    result = metric.dti_exact(p, truth)
    tp, fp, fn = brute_components(p, truth)
    assert result["tp"] == pytest.approx(tp)
    assert result["fp"] == pytest.approx(fp)
    assert result["fn"] == pytest.approx(fn)
    assert result["dti"] == pytest.approx(tp / (tp + .2 * fp + .8 * fn))
    # A single prediction can improve multiple truth pixels: upstream prose
    # claiming delta TP <= the dot's individual self-credit is not general.
    two = np.zeros((3, 3), bool)
    two[1, 0] = two[1, 2] = True
    dot = np.zeros((3, 3)); dot[1, 1] = 1
    assert metric.dti_exact(dot, two)["tp"] == pytest.approx(4 / 3)
    assert metric.dti_exact(dot, two)["tp"] > 2 / 3


def test_holdout_masks_only_exact_visible_pixels_and_bootstraps_terms():
    truth = np.zeros((10, 10), bool)
    truth[1, 2] = truth[8, 8] = True
    visible = np.zeros_like(truth); visible[2, 2] = True
    p = np.zeros_like(truth, dtype=float)
    p[2, 2], p[2, 3], p[8, 8] = 1, .8, 1
    f = {"region": np.ones_like(truth), "visible": visible, "truth": truth}
    result, terms = evaluate_holdout.evaluate(p, f, np.ones_like(truth), block_side=5)
    masked = p.copy(); masked[visible] = 0
    expected = metric.dti_exact(masked, truth, valid=~visible)
    assert result["dti"] == pytest.approx(expected["dti"])
    assert result["n_emitted"] == 2  # neighbouring (2,3) remains scored
    assert terms.sum(axis=0)[3] == 2
    summary = evaluate_holdout.pooled_summary({"h1": terms, "control": terms.copy()},
                                             draws=50, candidate="h1")
    assert summary["scores"]["h1"]["withheld_positive_pixels"] == 2
    assert summary["paired_differences"]["control"]["ci95"] == [0.0, 0.0]
    malformed = terms.copy(); malformed[0, 3] += 1
    with pytest.raises(ValueError, match="same integer truth"):
        evaluate_holdout.pooled_summary({"h1": terms, "control": malformed}, draws=50, candidate="h1")


def test_whole_cross_boundary_fault_hidden_in_each_intersected_fold():
    c = np.zeros((40, 40), bool)
    c[5, 18:23] = True  # one segment straddling vertical quadrant boundary
    c[30, 5:8] = c[30, 30:33] = True
    folds = list(spatial.folds(c, np.ones_like(c), buffer_px=3))
    for fold in folds:
        assert not (fold["train"] & fold["held_all"]).any()
        assert not (fold["train"] & fold["region"]).any()
        assert fold["receipt"]["shared_train_truth_components"] == 0
    for i in (0, 1):
        assert folds[i]["held_all"][5, 18:23].all()
        assert not folds[i]["visible"][5, 18:23].any()


def test_literal_three_pixel_overlap_and_incomplete_inventory_fail_closed(tmp_path):
    prior = np.zeros((12, 12), np.float32); prior[5, 5] = 1
    mine = np.zeros_like(prior); mine[5, 8] = 1  # exactly 3 pixels
    assert uniqueness.dot_overlap(mine, prior) == 1.0
    mine[:] = 0; mine[0, 0] = 1
    assert uniqueness.dot_overlap(mine, prior) == 0.0
    path = tmp_path / "old.tif"
    with rasterio.open(path, "w", driver="GTiff", width=12, height=12, count=1,
                       dtype="float32", crs="EPSG:32611", transform=from_origin(0, 1200, 100, 100)) as ds:
        ds.write(prior, 1)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    legacy_partial = [{"repo": "test", "file": str(path), "sha256": digest}]
    result = uniqueness.compare_array_to_registry(mine, legacy_partial, np.ones_like(mine, bool))
    assert not result["complete_accessible_scan"] and not result["unique"] and result["stop_required"]
    complete = {"rasters": [{"repo_first": "test", "sources": ["test prior"],
                             "cache_file": str(path), "sha256": digest}],
                "complete_accessible_scan": True, "errors": []}
    report = uniqueness.compare_array_to_registry(mine, complete, np.ones_like(mine, bool))
    assert report["unique"] and not report["stop_required"]
    mine[:] = 0; mine[5, 8] = 1
    blocked = uniqueness.compare_array_to_registry(mine, complete, np.ones_like(mine, bool))
    assert blocked["duplicate_count"] == 1 and not blocked["unique"] and blocked["stop_required"]


@pytest.mark.parametrize("bad", [np.nan, np.inf, -0.01, 1.01])
def test_writer_rejects_invalid_values_without_writing(tmp_path, bad):
    a = np.zeros((2, 2), np.float32); a[0, 0] = bad
    with pytest.raises(ValueError, match="finite and in"):
        write_submission(tmp_path / "bad.tif", a, tmp_path / "missing.tif",
                         np.ones_like(a, bool), name="test", note="test")
    assert not list(tmp_path.iterdir())


def test_shared_writer_roundtrip_on_synthetic_full_grid(tmp_path):
    # A synthetic temporary test fixture, never an eligible competition raster.
    sample = tmp_path / "sample.tif"
    a = np.zeros(grid.SHAPE, np.float32)
    with rasterio.open(sample, "w", driver="GTiff", height=grid.HEIGHT, width=grid.WIDTH,
                       count=1, dtype="float32", crs=grid.CRS_EPSG, transform=grid.TRANSFORM,
                       compress="deflate") as ds:
        ds.write(a, 1)
    a[100, 100] = np.float32(.5)
    output = tmp_path / "synthetic.tif"
    receipt = write_submission(output, a, sample, np.ones(grid.SHAPE, bool),
                               name="synthetic test only", note="Not a competition candidate")
    assert receipt["validator"]["all_checks_passed"]
    assert receipt["template_report"]["ok"]
    assert not receipt["promoted"] and not receipt["approved_for_weekly_slot"]
    assert receipt["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    with rasterio.open(output) as ds:
        assert ds.count == 1 and ds.dtypes == ("float32",)
        assert ds.shape == grid.SHAPE and ds.crs.to_epsg() == 32611 and ds.transform == grid.TRANSFORM
        assert ds.read(1, window=((100, 101), (100, 101)))[0, 0] == .5
    with zipfile.ZipFile(output.with_suffix(".zip")) as z:
        assert z.namelist() == [output.name]
        assert z.read(output.name) == output.read_bytes()
    with pytest.raises(FileExistsError):
        write_submission(output, a, sample, np.ones(grid.SHAPE, bool), name="test", note="test")
