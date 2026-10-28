"""Proxy calibration: do the repo's HOLDOUT-DTI proxies rank scored submissions the way the public board does?

Public scores are taken verbatim from the user-supplied GEMSDOE listing in the session prompt
(label: OWNER-REPORT / PORTAL — not an organizer receipt). Each listing entry is matched to a local
raster by its unique hash token in the filename. Both proxies are computed with the repo's shared
evaluator (src/gems32/holdout.py), B-visible = 2 px, GEMS_DATA_DIR restored from registry/data_manifest.json.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import kendalltau, spearmanr

sys.path.insert(0, '/home/user/GEMSDOESASS3/src')
os.environ.setdefault('GEMS_DATA_DIR', '/tmp/gems_data')
from gems32 import holdout  # noqa: E402

# (token-in-filename, public score as printed in the session listing, site label)
LISTING = [
    ('989f59505db1', 0.2477, 'GEMSDOE24'),
    ('e56ea318af89', 0.2600, 'GEMSDOE25'),
    ('5512495c6bd1', 0.2449, 'GEMSDOE27'),
    ('511898747886', 0.2190, 'GEMSDOE27'),
    ('cf8e1bbef244', 0.2250, 'GEMSDOE27'),
    ('8acb75e1f2cc', 0.2708, 'GEMSDOE28'),
    ('31e35eee884e', 0.2649, 'GEMSDOE28'),
    ('b531dae0a36f', 0.2710, 'GEMSDOE28'),
    ('56a9f473edc7', 0.2707, 'GEMSDOE28'),
    ('3e95505c011a', 0.0217, 'GEMSDOE28'),
    ('16bbf281ba9b', 0.0206, 'GEMSDOE28'),
    ('91eae1ca', 0.2600, 'GEMSDOE30'),
    ('e7856ec3f14a', 0.1462, 'GEMSDOE30'),
    ('8acb75e1-', 0.2708, 'GEMSDOE31'),
    ('e5eb6e7e', 0.2778, 'GEMSDOE32'),
    ('cb490425926e', 0.2632, 'GEMSDOE33'),
    ('3463540a7e02', 0.0963, 'GEMSDOE33'),
    ('9b9ea4e6', 0.2750, 'GEMSDOE36'),
    ('fc869911e88c', 0.1647, 'GEMSDOE36'),
    ('abe8e51c719d', 0.0859, 'GEMSDOE24'),
    ('da617550a0e9', 0.0742, 'GEMSDOE25'),
    ('df20f65e', 0.1855, 'GEMSDOE16'),
    ('691e4dfa', 0.1894, 'GEMSDOE19'),
    ('e27054cf', 0.1922, 'GEMSDOE19'),
    ('6452ae1d00', 0.1280, 'GEMSDOE10'),  # H25-ctx-ridge (both H25 and H28 share this token; resolved below)
    ('7f00890a', 0.1563, 'GEMSDOE-ens12'),
    ('2314b599', 0.0107, 'GEMSDOE9'),
]

ROOTS = [Path('/tmp/ref/all'), Path('/tmp/ref/hist'), Path('/tmp/gems_data')]
ALL_TIFS = [p for r in ROOTS for p in r.rglob('*.tif')]


def find(token, prefer_dot=None):
    hits = [p for p in ALL_TIFS if token in p.name]
    if prefer_dot:
        hits = [p for p in hits if prefer_dot in p.name] or hits
    # prefer the -nan / -zeros / -allfinite variant of the file, skip lattice/outside/ETC
    hits = [p for p in hits if 'nanoutside' not in p.name] or hits
    return sorted(hits)[0] if hits else None


def main():
    ctx = holdout.load_holdout_context(Path(os.environ['GEMS_DATA_DIR']))
    rows = []
    seen = set()
    for token, score, site in LISTING:
        # disambiguate the two 6452ae1d00 entries by their date tokens
        prefer = None
        if token == '6452ae1d00':
            prefer = 'H25-ctx' if False else 'h25-ctx-ridge'
        p = find(token, prefer)
        if p is None or str(p) in seen:
            rows.append({'token': token, 'site': site, 'public': score, 'status': 'NO_LOCAL_FILE'})
            continue
        seen.add(str(p))
        with rasterio.open(p) as ds:
            a = ds.read(1)
        mask = np.isfinite(a) & (a > 0) & ctx.foot
        hr = holdout.evaluate_hide_and_recover(mask, ctx, b_visible_px=2.0, name=p.stem)
        sg = holdout.evaluate_sgmc_with_ci(mask, ctx, name=p.stem)
        rows.append({
            'token': token, 'site': site, 'public': score, 'file': p.name, 'n_dots': int(mask.sum()),
            'static_HR_dti': float(hr['pooled_dti']),
            'static_HR_ci95': [float(x) for x in hr['ci95_cluster_bootstrap']],
            'SGMC_cal_dti': float(sg['sgmc_prevalence_calibrated_dti']),
            'SGMC_cal_ci95': [float(x) for x in sg['sgmc_calibrated_ci95']] if 'sgmc_calibrated_ci95' in sg else None,
            'status': 'EVALUATED',
        })
        print(f"{site:12s} {score:.4f}  HR={hr['pooled_dti']:.5f}  SGMC={sg['sgmc_prevalence_calibrated_dti']:.5f}  {p.name[:70]}", flush=True)

    ev = [r for r in rows if r['status'] == 'EVALUATED']
    pub = np.array([r['public'] for r in ev])
    hrv = np.array([r['static_HR_dti'] for r in ev])
    sgv = np.array([r['SGMC_cal_dti'] for r in ev])
    summary = {
        'n_calibration_points': len(ev),
        'spearman_public_vs_static_HR': float(spearmanr(pub, hrv).correlation),
        'kendall_public_vs_static_HR': float(kendalltau(pub, hrv).correlation),
        'spearman_public_vs_SGMC_cal': float(spearmanr(pub, sgv).correlation),
        'kendall_public_vs_SGMC_cal': float(kendalltau(pub, sgv).correlation),
    }
    # bootstrap CI for the Spearman values (resampling calibration points)
    rng = np.random.default_rng(20261028)
    bs_hr, bs_sg = [], []
    for _ in range(2000):
        idx = rng.integers(0, len(ev), len(ev))
        if len(set(pub[idx])) < 2:
            continue
        bs_hr.append(spearmanr(pub[idx], hrv[idx]).correlation)
        bs_sg.append(spearmanr(pub[idx], sgv[idx]).correlation)
    summary['spearman_public_vs_static_HR_ci95'] = [float(np.nanpercentile(bs_hr, 2.5)), float(np.nanpercentile(bs_hr, 97.5))]
    summary['spearman_public_vs_SGMC_cal_ci95'] = [float(np.nanpercentile(bs_sg, 2.5)), float(np.nanpercentile(bs_sg, 97.5))]
    out = {'label': 'CALIBRATION (OWNER-REPORT public scores from session listing; not organizer receipts)',
           'evaluator': 'src/gems32/holdout.py (B-visible=2 px); static masks',
           'summary': summary, 'rows': rows}
    json.dump(out, open('/tmp/ref/calibration.json', 'w'), indent=1)
    print(json.dumps(summary, indent=1))
    print('NO_LOCAL_FILE:', [r['token'] for r in rows if r['status'] != 'EVALUATED'])


if __name__ == '__main__':
    main()
