import json
from pathlib import Path
import numpy as np
import rasterio
from scipy.spatial import cKDTree

R = Path('/tmp/ref')
ALL = R / 'all'
ship = rasterio.open('/home/user/GEMSDOESASS3/docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif').read(1)


def find(name_part, repo=None):
    hits = []
    for p in ALL.rglob('*.tif'):
        if name_part in p.name and (repo is None or p.parent.name == repo):
            hits.append(p)
    if not hits:
        for p in R.rglob('*.tif'):
            if name_part in p.name:
                hits.append(p)
    return hits


def load(p):
    return np.nan_to_num(rasterio.open(p).read(1), nan=0.0)


def ov(a, b):
    da = np.column_stack(np.nonzero(a > 0)).astype(float)
    db = np.column_stack(np.nonzero(b > 0)).astype(float)
    if len(da) == 0 or len(db) == 0:
        return float('nan')
    return float((cKDTree(db).query(da, k=1)[0] <= 3.0).mean())


champ = load(find('e5eb6e7e-zeros')[0])
pairs = {
    'champion_vs_shipped': (champ, ship),
    'champion_vs_GEMSDOE36_anderson_zeros': (champ, load(find('9b9ea4e6-zeros')[0])),
    'champion_vs_GEMSDOE28_h36-1_allfinite': (champ, load(find('b531dae0a36f-allfinite')[0])),
    'champion_vs_GEMSDOE31_h27-4_allfinite': (champ, load(find('8acb75e1-allfinite', 'GEMSDOE31')[0])),
    'champion_vs_GEMSDOE33_h33d_zeros_or_plain': (champ, load(find('cb490425926e.tif', 'GEMSDOE33')[0])),
    'champion_vs_GEMSDOE25_h31': (champ, load(find('c213681203f6-zeros')[0])),
    'champion_vs_GEMSDOE27_topo_gap_allfinite': (champ, load(find('5512495c6bd1-allfinite')[0])),
    'champion_vs_GEMSDOE30_d28_offcat': (champ, load(find('91eae1ca.tif', 'GEMSDOE30')[0])),
    'shipped_vs_GEMSDOE24_h25-1_d1-5_nan': (ship, load(find('989f59505db1-nan')[0])),
}
res = {}
for k, (a, b) in pairs.items():
    if a is None or b is None:
        continue
    res[k] = {'overlap_a_within_3px_of_b': ov(a, b), 'n_a': int((a > 0).sum()), 'n_b': int((b > 0).sum()),
              'xor_positive_pixels': int(((a > 0) ^ (b > 0)).sum())}
    print(k, res[k])

# identical-pixel checks requested by README IR-SASS3-02
for name_a, name_b in [
    ('e56ea318af89-zeros', 'e56ea318af89-nan'),
]:
    pa = find(name_a)
    pb = find(name_b)
    print(name_a, [str(x) for x in pa][:2], name_b, [str(x) for x in pb][:2])
    if pa and pb:
        a, b = load(pa[0]), load(pb[0])
        print('XOR', int(((a > 0) ^ (b > 0)).sum()))

json.dump(res, open('/tmp/ref/pairs.json', 'w'), indent=1)
