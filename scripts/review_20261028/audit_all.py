"""Independent uniqueness audit of the shipped GeoTIFF against every registry raster.

Downloads each registry raster via the GitHub API (outside the repo, into /tmp/ref/all),
verifies its SHA-256 against registry/focus_registry_manifest.json, then computes:
  * Spearman rho on the full 12,279,160-cell grid (binary -> phi == Spearman exactly)
  * fraction of shipped dots lying within 3 px (300 m) of any dot of the other raster
Writes /tmp/ref/audit_all.json.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

REPO_ROOT = Path('/home/user/GEMSDOESASS3')
SHIPPED = REPO_ROOT / 'docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif'
MAN = json.load(open(REPO_ROOT / 'registry/focus_registry_manifest.json'))
DEST = Path('/tmp/ref/all')
DEST.mkdir(parents=True, exist_ok=True)


def load(p):
    with rasterio.open(p) as ds:
        a = ds.read(1)
        return a


def dots(a):
    rr, cc = np.nonzero(a > 0)
    return np.column_stack([rr, cc]).astype(float)


ship = load(SHIPPED)
ship_dots = dots(ship)
ship_bin = (ship > 0).astype(np.float32).ravel()
ship_flat = ship.ravel()

rows = []
fails = []
for r in MAN['rasters']:
    repo, path = r['repo'], r['path']
    dest = DEST / repo / Path(path).name
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('wb') as f:
            res = subprocess.run(['gh', 'api', f'repos/buffedlizard55-lab/{repo}/contents/{path}',
                                  '-H', 'Accept: application/vnd.github.raw'], stdout=f)
        if res.returncode != 0:
            fails.append((repo, path, 'download_failed'))
            continue
    h = hashlib.sha256(dest.read_bytes()).hexdigest()
    if h != r['sha256']:
        fails.append((repo, path, 'sha_mismatch'))
        continue
    try:
        a = load(dest)
    except Exception as e:  # noqa: BLE001
        fails.append((repo, path, f'read_error:{e}'))
        continue
    if a.shape != ship.shape:
        rows.append({'repo': repo, 'path': path, 'skipped': f'shape {a.shape}'})
        continue
    a_flat = a.ravel().astype(np.float64)
    finite = np.isfinite(a_flat)
    s_flat = ship_flat.astype(np.float64)
    # Spearman over cells where both are finite (NaN outside footprint excluded)
    both = finite & np.isfinite(s_flat)
    if np.unique(a_flat[both]).size <= 2 and np.unique(s_flat[both]).size <= 2:
        rho = float(np.corrcoef(a_flat[both], s_flat[both])[0, 1]) if np.std(a_flat[both]) > 0 and np.std(s_flat[both]) > 0 else float('nan')
    else:
        rho = float(spearmanr(a_flat[both], s_flat[both]).correlation)
    other = dots(np.nan_to_num(a, nan=0.0))
    n_other = int(other.shape[0])
    if n_other == 0 or ship_dots.shape[0] == 0:
        overlap = float('nan')
    else:
        tree = cKDTree(other)
        d, _ = tree.query(ship_dots, k=1)
        overlap = float((d <= 3.0).mean())
    rows.append({'repo': repo, 'path': path, 'sha256': h, 'n_dots_other': n_other,
                 'spearman_vs_shipped': rho, 'shipped_dots_within_3px_of_other': overlap})
    print(f"{repo:10s} rho={rho:+.4f} overlap={overlap:.4f} n={n_other:6d} {Path(path).name}", flush=True)

json.dump({'shipped': str(SHIPPED.relative_to(REPO_ROOT)), 'n_rasters_compared': len(rows),
           'fails': fails, 'rows': rows}, open('/tmp/ref/audit_all.json', 'w'), indent=1)
valid = [x for x in rows if 'skipped' not in x]
mx_o = max(valid, key=lambda x: x['shipped_dots_within_3px_of_other'])
mx_r = max(valid, key=lambda x: abs(x['spearman_vs_shipped']))
print('compared', len(valid), 'fails', len(fails))
print('MAX overlap', mx_o['shipped_dots_within_3px_of_other'], mx_o['repo'], Path(mx_o['path']).name)
print('MAX |rho|', abs(mx_r['spearman_vs_shipped']), mx_r['repo'], Path(mx_r['path']).name)
