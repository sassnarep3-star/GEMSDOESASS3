"""Exact duplicate detection across the registry: identical positive-dot sets (XOR == 0)."""
import hashlib, json, os
from collections import defaultdict
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
cache = Path(os.environ.get("GEMS_WORK_DIR", "/tmp/gems_work")) / "registry_rasters"
rank = json.loads((ROOT / "evidence/registry_sgmc_rank_20261028.json").read_text())
groups = defaultdict(list)
for r in rank["rows"]:
    p = next(cache.rglob(r["file"]))
    with rasterio.open(p) as ds:
        m = ds.read(1) > 0.0
    key = hashlib.sha256(np.packbits(m.ravel()).tobytes()).hexdigest()
    groups[key].append({"repo": r["repo"], "file": r["file"], "sha256": r["sha256"], "n_dots": int(m.sum())})
dups = [g for g in groups.values() if len(g) > 1]
out = {"n_rasters": len(rank["rows"]), "n_distinct_dot_sets": len(groups), "n_duplicate_groups": len(dups), "groups": dups}
(ROOT / "evidence/registry_exact_duplicates_20261028.json").write_text(json.dumps(out, indent=2) + "\n")
print("rasters", out["n_rasters"], "distinct dot sets", out["n_distinct_dot_sets"], "duplicate groups", out["n_duplicate_groups"])
for g in dups:
    print(" ", [(x["repo"], x["file"][:55]) for x in g])
