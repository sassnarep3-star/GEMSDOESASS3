from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from geotiff_audit import template_geometry, validate_tif


def make_tif(path, values, mask=None, *, internal=True, nodata=None, crs="EPSG:32611",
             transform=None, count=1, dtype="float32"):
    values = np.asarray(values, dtype=dtype)
    profile = dict(driver="GTiff", width=values.shape[1], height=values.shape[0], count=count,
                   dtype=dtype, crs=crs, transform=transform or from_origin(1000, 2000, 100, 100), nodata=nodata)
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=internal):
        with rasterio.open(path, "w", **profile) as ds:
            for band in range(1, count + 1):
                ds.write(values, band)
            if mask is not None:
                ds.write_mask(np.asarray(mask, dtype=np.uint8) * 255)
    return path


@pytest.fixture
def example(tmp_path):
    fp = np.zeros((5, 6), bool)
    fp[1:4, 1:5] = True
    template = make_tif(tmp_path / "sample.tif", np.zeros(fp.shape), fp)
    return tmp_path, fp, template


def test_valid_internal_mask_keeps_raw_array_finite_and_probabilities(example):
    tmp, fp, template = example
    values = np.zeros(fp.shape, np.float32)
    values[1, 1], values[1, 2] = 0.2, 0.9
    candidate = make_tif(tmp / "candidate.tif", values, fp)
    report = validate_tif(candidate, template)
    assert report["local_official_profile_pass"]
    assert report["raw_whole_array_finite_range_pass"]
    assert report["checks"]["single_file"]
    assert not report["submission_approved"]
    assert report["organizer_acceptance"] == "unknown"
    with rasterio.open(candidate) as ds:
        assert ds.read(1)[1, 1] == pytest.approx(0.2)
        assert ds.read(1)[1, 2] == pytest.approx(0.9)


def test_nan_outside_and_allfinite_unmasked_are_reported_separately(example):
    tmp, fp, template = example
    values = np.zeros(fp.shape, np.float32)
    values[~fp] = np.nan
    nan_tif = make_tif(tmp / "nan.tif", values, nodata=np.nan)
    report = validate_tif(nan_tif, template)
    assert report["local_official_profile_pass"]
    assert not report["raw_whole_array_finite_range_pass"]
    assert report["raw_nonfinite"] == int((~fp).sum())
    zeros = make_tif(tmp / "zeros.tif", np.zeros(fp.shape))
    report = validate_tif(zeros, template)
    assert report["raw_whole_array_finite_range_pass"]
    assert not report["checks"]["outside_null_or_nan"]
    assert not report["local_official_profile_pass"]


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, -3.4028235e38, -0.1, 1.001])
def test_inside_invalid_value_fails_without_repair(example, bad):
    tmp, fp, template = example
    values = np.zeros(fp.shape, np.float32)
    values[2, 2] = bad
    candidate = make_tif(tmp / "bad.tif", values, fp)
    report = validate_tif(candidate, template)
    assert not report["checks"]["inside_values_in_0_1"]
    assert not report["local_official_profile_pass"]
    with rasterio.open(candidate) as ds:
        actual = ds.read(1)[2, 2]
        assert (np.isnan(actual) if np.isnan(bad) else actual == np.float32(bad))


def test_masked_inside_is_not_a_valid_prediction(example):
    tmp, fp, template = example
    badmask = fp.copy(); badmask[2, 2] = False
    candidate = make_tif(tmp / "masked.tif", np.zeros(fp.shape), badmask)
    report = validate_tif(candidate, template)
    assert not report["checks"]["inside_mask_valid"]
    assert report["inside_invalid_mask"] == 1


def test_external_mask_sidecar_is_not_single_file(example):
    tmp, fp, template = example
    candidate = make_tif(tmp / "sidecar.tif", np.zeros(fp.shape), fp, internal=False)
    assert Path(str(candidate) + ".msk").exists()
    report = validate_tif(candidate, template)
    assert not report["checks"]["single_file"]
    assert not report["local_official_profile_pass"]


@pytest.mark.parametrize("kwargs,check", [({"dtype": "uint8"}, "float32"),
                                           ({"count": 2}, "single_band"),
                                           ({"crs": "EPSG:4326"}, "crs_matches"),
                                           ({"transform": from_origin(1010, 2000, 100, 100)}, "transform_matches")])
def test_wrong_metadata_fails(example, kwargs, check):
    tmp, fp, template = example
    candidate = make_tif(tmp / "wrong.tif", np.zeros(fp.shape), fp, **kwargs)
    assert not validate_tif(candidate, template)["checks"][check]


def test_shape_mismatch_fails_closed(example):
    tmp, fp, template = example
    candidate = make_tif(tmp / "shape.tif", np.zeros((2, 2)))
    report = validate_tif(candidate, template)
    assert not report["checks"]["shape_matches"]
    assert not report["local_official_profile_pass"]


def test_template_wrong_crs_and_resolution_fail(tmp_path):
    one = make_tif(tmp_path / "crs.tif", np.zeros((2, 2)), crs="EPSG:4326")
    with pytest.raises(ValueError, match="EPSG:32611"):
        template_geometry(one)
    two = make_tif(tmp_path / "res.tif", np.zeros((2, 2)), transform=from_origin(0, 100, 10, 10))
    with pytest.raises(ValueError, match="100 m"):
        template_geometry(two)


def test_unmasked_infinity_outside_is_not_null(example):
    tmp, fp, template = example
    values = np.zeros(fp.shape, np.float32)
    values[~fp] = np.nan
    values[0, 0] = np.inf
    candidate = make_tif(tmp / 'infinity.tif', values, nodata=np.nan)
    report = validate_tif(candidate, template)
    assert not report['checks']['outside_null_or_nan']
    assert not report['local_official_profile_pass']
    assert not report['raw_whole_array_finite_range_pass']


def test_masked_registry_pixels_cannot_prove_a_duplicate(example):
    from registry_preflight import evaluate
    from audit_focus import load_support
    tmp, fp, template = example
    values = np.zeros(fp.shape, np.float32); values[2, 2] = 1
    mask = fp.copy(); mask[2, 2] = False
    witness = make_tif(tmp / 'witness.tif', values, mask)
    with pytest.raises(ValueError, match='masked pixels'):
        evaluate(template, witness, 10)
    with pytest.raises(ValueError, match='masked historical'):
        load_support(witness, template_geometry(template))


def test_cli_never_overwrites_candidate_template_or_hardlink(example, monkeypatch):
    import sys
    import geotiff_audit
    tmp, fp, template = example
    candidate = make_tif(tmp / 'candidate.tif', np.zeros(fp.shape), fp)
    alias = tmp / 'hardlink.tif'; alias.hardlink_to(candidate)
    original, template_original = candidate.read_bytes(), template.read_bytes()
    for output in [candidate, template, alias]:
        monkeypatch.setattr(sys, 'argv', ['geotiff_audit.py', str(candidate), '--template', str(template), '--out', str(output)])
        assert geotiff_audit.main() == 1
        assert candidate.read_bytes() == original
        assert template.read_bytes() == template_original


def test_cli_requires_both_profiles_but_does_not_predict_portal_result(example, monkeypatch, capsys):
    import sys
    import geotiff_audit
    tmp, fp, template = example
    values = np.zeros(fp.shape, np.float32); values[~fp] = np.nan
    nan_tif = make_tif(tmp / 'nan-outside.tif', values, nodata=np.nan)
    monkeypatch.setattr(sys, 'argv', ['geotiff_audit.py', str(nan_tif), '--template', str(template)])
    assert geotiff_audit.main() == 2
    output = capsys.readouterr().out
    assert '"local_official_profile_pass": true' in output
    assert '"raw_whole_array_finite_range_pass": false' in output
    assert '"organizer_acceptance": "unknown"' in output
    finite_tif = make_tif(tmp / 'masked-finite.tif', np.zeros(fp.shape), fp)
    monkeypatch.setattr(sys, 'argv', ['geotiff_audit.py', str(finite_tif), '--template', str(template)])
    assert geotiff_audit.main() == 0
    assert '"submission_approved": false' in capsys.readouterr().out


def test_pinned_analysis_rejects_unhashed_mask_sidecars(example):
    from registry_preflight import evaluate
    from audit_focus import load_support
    tmp, fp, template = example
    values = np.zeros(fp.shape, np.float32); values[2, 2] = 1
    witness = make_tif(tmp / 'witness-sidecar.tif', values, fp, internal=False)
    with pytest.raises(ValueError, match='external sidecars'):
        evaluate(template, witness, 10)
    with pytest.raises(ValueError, match='external sidecars'):
        load_support(witness, template_geometry(template))
    bad_template = make_tif(tmp / 'sample-sidecar.tif', values, fp, internal=False)
    with pytest.raises(ValueError, match='external sidecars'):
        template_geometry(bad_template)


def test_cli_report_cannot_overwrite_candidate_sidecar(example, monkeypatch):
    import sys
    import geotiff_audit
    tmp, fp, template = example
    candidate = make_tif(tmp / 'candidate-sidecar.tif', np.zeros(fp.shape), fp, internal=False)
    sidecar = Path(str(candidate) + '.msk'); old = sidecar.read_bytes()
    monkeypatch.setattr(sys, 'argv', ['geotiff_audit.py', str(candidate), '--template', str(template), '--out', str(sidecar)])
    assert geotiff_audit.main() == 1
    assert sidecar.read_bytes() == old
