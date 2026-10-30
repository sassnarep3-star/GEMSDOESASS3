#!/usr/bin/env bash
# Fetch the pinned sibling submission rasters through the git protocol.
#
# Why: the REST contents route used by scripts/fetch_sibling_registry_rasters.py is rate limited
# (460 files x 1 call exhausted the token on 2026-10-30; see evidence/registry_siblings_fetch_receipt.json
# tally {"failed": 460} with "API rate limit exceeded").  `git fetch --filter=blob:none --depth 1`
# downloads only the blobs under docs/downloads and does not count against the REST limit.
#
# Output: $OUT/<repo>/<basename>  (default /tmp/registry_git).  Every file is SHA-256 checked
# against registry/sibling_registry_manifest_20261028.json; mismatches are reported, not used.
set -uo pipefail
OUT="${1:-/tmp/registry_git}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MAN="$ROOT/registry/sibling_registry_manifest_20261028.json"
mkdir -p "$OUT"
repos=$(python3 - "$MAN" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
for r,v in m["source_repos"].items():
    print(r, v["commit"])
PY
)
echo "$repos" | while read -r repo sha; do
  [ -z "${repo:-}" ] && continue
  d="$OUT/$repo"
  if [ -d "$d/.git" ]; then echo "cached $repo"; continue; fi
  mkdir -p "$d"
  ( cd "$d" \
    && git init -q \
    && git remote add origin "https://github.com/buffedlizard55-lab/$repo" \
    && git fetch -q --depth 1 --filter=blob:none origin "$sha" \
    && git sparse-checkout init --cone 2>/dev/null \
    && git sparse-checkout set docs/downloads inputs 2>/dev/null \
    && git checkout -q FETCH_HEAD ) \
    && echo "ok $repo" || echo "FAIL $repo"
done
python3 - "$MAN" "$OUT" <<'PY'
import hashlib, json, sys
man, out = json.load(open(sys.argv[1])), sys.argv[2]
from pathlib import Path
got = {}
for e in man["files"]:
    repo, rest = e["path"].split("/", 1)
    p = Path(out) / repo / rest
    if p.is_file():
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        got.setdefault("match" if h == e["sha256"] else "mismatch", []).append(str(p))
    else:
        got.setdefault("missing", []).append(e["path"])
print(json.dumps({k: len(v) for k, v in got.items()}, indent=None))
if got.get("mismatch"):
    print("MISMATCHES:", got["mismatch"][:5])
Path(out + "/fetch_summary.json").write_text(json.dumps(
    {"n_match": len(got.get("match", [])), "n_mismatch": len(got.get("mismatch", [])),
     "n_missing": len(got.get("missing", [])), "mismatches": got.get("mismatch", [])[:50]}, indent=1))
PY
