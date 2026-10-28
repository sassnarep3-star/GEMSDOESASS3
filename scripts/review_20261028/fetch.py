import hashlib, json, subprocess
from pathlib import Path

man = json.load(open('/home/user/GEMSDOESASS3/registry/focus_registry_manifest.json'))
want = [
    ('GEMSDOE32', 'docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif'),
    ('GEMSDOE32', 'docs/downloads/gemsdoe32-h36-1c-tdr-pds-steger-37654-20261026T012000Z-9ff9d6e2-zeros.tif'),
    ('GEMSDOE25', 'docs/downloads/gems25-h31-aniso-scarp-b2-d2-8-20261025-c213681203f6-zeros.tif'),
    ('GEMSDOE24', 'docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif'),
    ('GEMSDOE24', 'docs/downloads/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif'),
    ('GEMSDOE28', 'docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif'),
    ('GEMSDOE31', 'docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif'),
    ('GEMSDOE33', 'docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif'),
    ('GEMSDOE36', 'docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif'),
    ('GEMSDOE27', 'docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif'),
    ('GEMSDOE30', 'docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif'),
]
reg = {(r['repo'], r['path']): r for r in man['rasters']}
out = []
for repo, path in want:
    r = reg.get((repo, path))
    if r is None:
        print('MISSING IN REGISTRY', repo, path)
        continue
    dest = Path('/tmp/ref') / repo / Path(path).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('wb') as f:
        subprocess.run(['gh', 'api', f'repos/buffedlizard55-lab/{repo}/contents/{path}',
                        '-H', 'Accept: application/vnd.github.raw'], stdout=f, check=True)
    h = hashlib.sha256(dest.read_bytes()).hexdigest()
    ok = h == r['sha256']
    print('OK ' if ok else 'SHA MISMATCH', repo, Path(path).name, dest.stat().st_size, h[:12],
          'registry', r['sha256'][:12], 'positives', r['positive_pixels'])
    out.append({'repo': repo, 'path': path, 'local': str(dest), 'sha_ok': ok, 'sha': h})
json.dump(out, open('/tmp/ref/fetched.json', 'w'), indent=1)
