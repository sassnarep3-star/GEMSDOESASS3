import hashlib, json, subprocess
from pathlib import Path
import numpy as np, rasterio
from scipy.spatial import cKDTree
R='/home/user/GEMSDOESASS3'
dm=json.load(open(R+'/registry/data_manifest.json'))
ship=rasterio.open(R+'/docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif').read(1)
sd=np.column_stack(np.nonzero(ship>0)).astype(float)
sf=ship.ravel().astype(float)
out=[]
for e in dm['files']:
    p=e.get('path') or ''
    if not (p.startswith('inputs/') and p.endswith('.tif')): continue
    if not any(k in p for k in ['13gems_20261001','8GEMSDOE_Hedge','gems10-h25-ctx','gems10-h28-dotted','gems16-h16-1','gems19-h19-4','gemsdoe-ens12','gemsdoe9-PLACEHOLDER']): continue
    dest=Path('/tmp/ref/all/hist')/Path(p).name; dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('wb') as f:
        r=subprocess.run(['gh','api',f"repos/{e['repo']}/contents/{p}?ref={e['ref']}",'-H','Accept: application/vnd.github.raw'],stdout=f)
    if r.returncode: print('DL FAIL',p); continue
    h=hashlib.sha256(dest.read_bytes()).hexdigest()
    a=rasterio.open(dest).read(1)
    if a.shape!=ship.shape: print('SHAPE',p,a.shape); continue
    af=a.ravel().astype(float); both=np.isfinite(af)&np.isfinite(sf)
    rho=np.corrcoef(af[both],sf[both])[0,1] if np.unique(af[both]).size<=2 else float('nan')
    od=np.column_stack(np.nonzero(np.nan_to_num(a,nan=0)>0)).astype(float)
    ov=float((cKDTree(od).query(sd,k=1)[0]<=3.0).mean()) if len(od) else float('nan')
    print(f"HIST sha_ok={h==e['sha256']} rho={rho:+.4f} overlap={ov:.4f} n={len(od)} {Path(p).name}")
    out.append({'path':p,'sha_ok':h==e['sha256'],'rho':float(rho),'overlap':ov,'n':int(len(od))})
json.dump(out,open('/tmp/ref/hist8.json','w'),indent=1)
