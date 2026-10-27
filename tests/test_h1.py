import inspect
import numpy as np
import pytest

from lane_h1 import make_fields, sample_offset
from evidence_io import choose_output
from run_h1 import leakage_canaries, write_card


def test_offsets_do_not_wrap_at_edges():
    a = np.arange(20).reshape(4, 5)
    for dy, dx in ((1, 2), (-2, -1), (0, 0), (9, 0), (0, -9)):
        actual = sample_offset(a, dy, dx)
        for y in range(4):
            for x in range(5):
                yy, xx = y + dy, x + dx
                expected = a[yy, xx] if 0 <= yy < 4 and 0 <= xx < 5 else 0
                assert actual[y, x] == expected


def test_h1_fields_are_bounded_and_have_no_label_input():
    rng = np.random.default_rng(32)
    r = rng.normal(0, 150, (65, 67)).astype(np.float32)
    z = rng.normal(0, 50, (65, 67)).astype(np.float32)
    footprint = np.ones_like(r, bool)
    r[20, 20] = np.nan
    z[50, 50] = -3.4e38  # finite GeoTIFF nodata sentinel
    r[45, 12] = 1e25    # finite but its square would overflow float32
    with np.errstate(all="raise"):
        fields, support = make_fields(r, z, footprint)
    assert support.any() and not support[20, 20] and not support[50, 50]
    assert "catalogue" not in inspect.signature(make_fields).parameters
    assert len(fields) == 10
    for field in fields.values():
        assert np.isfinite(field).all()
        assert (field >= 0).all() and (field <= 1).all()
        assert np.all(field[~support] == 0)


def test_invalid_or_insufficient_support_fails_closed():
    with pytest.raises(ValueError, match="share a 2-D grid"):
        make_fields(np.zeros((5, 5)), np.zeros((4, 5)), np.ones((5, 5)))
    with pytest.raises(ValueError, match="no fully supported"):
        make_fields(np.zeros((5, 5)), np.zeros((5, 5)), np.ones((5, 5)))


def test_negative_auc_direction_is_also_a_leakage_alarm():
    truth = np.zeros((4, 4), bool)
    truth[0, :] = True
    f = {"slice": np.s_[:, :], "fold": {"region": np.ones_like(truth),
         "visible": np.zeros_like(truth), "truth": truth}, "receipt": {"fold": 0}}
    rows = leakage_canaries({"inverse_label": (~truth).astype(float)},
                             np.ones_like(truth), [f])
    assert rows[0]["auc"] == 0.0
    assert rows[0]["direction_free_auc"] == 1.0  # must trip >0.90


def test_canary_rejects_nonfinite_features():
    truth = np.eye(4, dtype=bool)
    f = {"slice": np.s_[:, :], "fold": {"region": np.ones_like(truth),
         "visible": np.zeros_like(truth), "truth": truth}, "receipt": {"fold": 0}}
    with pytest.raises(ValueError, match="non-finite"):
        leakage_canaries({"bad": np.full((4, 4), np.nan)}, np.ones_like(truth), [f])


def test_receipts_never_overwrite_existing_evidence(tmp_path):
    existing = tmp_path / "published.json"
    existing.write_text('{"original": true}\n')
    with pytest.raises(FileExistsError):
        choose_output(existing, str(existing))
    with pytest.raises(FileExistsError):
        write_card({"new": True}, existing)
    assert existing.read_text() == '{"original": true}\n'
    new = choose_output(tmp_path / "missing.json")
    write_card({"negative": True}, new)
    assert '"negative": true' in new.read_text()
    assert not list(tmp_path.glob("*.partial"))
