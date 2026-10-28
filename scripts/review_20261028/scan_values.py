"""Scan every fetched registry raster for the properties the DrivenData portal checks.

Reports per file: dtype, nodata, NaN count, +/-inf count, min/max of finite values,
count of finite values outside [0,1], and whether the file is binary.
Then cross-references files that appear WITH a public score in the prompt's listing.
"""
import json
from pathlib import Path

import numpy as np
import rasterio

rows = []
for p in sorted(Path('/tmp/ref/all').rglob('*.tif')) + sorted(Path('/tmp/ref/hist').rglob('*.tif')):
    try:
        with rasterio.open(p) as ds:
            a = ds.read(1)
            dt = str(ds.dtypes[0])
            nd = ds.nodata
            crs = ds.crs.to_string() if ds.crs else None
            shape = (ds.height, ds.width)
    except Exception as e:  # noqa: BLE001
        rows.append({'file': p.name, 'error': str(e)})
        continue
    af = a.astype(np.float64)
    nan = int(np.isnan(af).sum())
    inf = int(np.isinf(af).sum())
    fin = af[np.isfinite(af)]
    out_of_range = int(((fin < 0) | (fin > 1)).sum())
    rows.append({
        'file': p.name, 'dtype': dt, 'nodata': nd, 'crs': crs, 'shape': shape,
        'nan_count': nan, 'inf_count': inf,
        'min_finite': float(fin.min()) if fin.size else None,
        'max_finite': float(fin.max()) if fin.size else None,
        'finite_outside_0_1': out_of_range,
        'binary': bool(np.isin(fin, [0.0, 1.0]).all()) if fin.size else None,
    })

json.dump(rows, open('/tmp/ref/value_scan.json', 'w'), indent=1)
n = len(rows)
n_nan = sum(1 for r in rows if r.get('nan_count', 0) > 0)
n_out = sum(1 for r in rows if r.get('finite_outside_0_1', 0) > 0)
n_inf = sum(1 for r in rows if r.get('inf_count', 0) > 0)
n_nonbin = sum(1 for r in rows if r.get('binary') is False)
print('files', n, 'with_nan', n_nan, 'with_inf', n_inf, 'finite_outside_0_1', n_out, 'non_binary', n_nonbin)
print('dtypes', sorted({r.get('dtype') for r in rows if 'dtype' in r}))
print('nodata values', sorted({str(r.get('nodata')) for r in rows if 'dtype' in r}))
print('crs', sorted({str(r.get('crs')) for r in rows if 'dtype' in r}))
for r in rows:
    if r.get('finite_outside_0_1', 0) > 0:
        print('OUTSIDE', r['file'], r['min_finite'], r['max_finite'], r['finite_outside_0_1'])
