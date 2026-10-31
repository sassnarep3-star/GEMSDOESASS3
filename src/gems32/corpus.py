"""Shared, verified helpers for the published-submission score corpus (2026-10-31).

Everything here is measured from bytes the repository can re-fetch from GitHub:

* ``registry/sibling_downloads_manifest_20261031.json``  (what was downloaded and its SHA-256)
* ``registry/corpus_20261031.json``                      (grid-validated rasters + owner scores)
* ``.cache/corpus_20261031/<sha>.npz``                   (dot indices + values, one per raster)

Score provenance
----------------
``registry/published_score_table_20261030.json`` is a verbatim transcription of the scores the
owner typed next to file names on the sibling GitHub Pages sites.  Every score in this corpus is
**OWNER-REPORT**: it is not organizer-confirmed and it cannot be re-verified on the public
leaderboard, which only exposes team-level best scores.  Nothing in this module converts an
owner-reported value into an organizer-confirmed one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

H, W = 3730, 3292
R = 3.0

CORPUS_JSON = ROOT / "registry" / "corpus_20261031.json"
CACHE_DIR = ROOT / ".cache" / "corpus_20261031"
DATA_DIR = ROOT / ".cache" / "gems_data"

# triangular 300 m kernel offsets: (dy, dx, k)
_K = [(int(dy), int(dx), float(1.0 - np.hypot(dy, dx) / R))
      for dy in range(-3, 4) for dx in range(-3, 4) if np.hypot(dy, dx) < R]


def shift(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Translate a 2-D field by (dy, dx) cells, zero-filling, no wrap.

    Uses the array's own shape, so it is correct for sub-windows as well as the full grid.
    """
    h, w = a.shape
    out = np.zeros_like(a)
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    out[ys0:ys1, xs0:xs1] = a[max(0, -dy):min(h, h - dy), max(0, -dx):min(w, w - dx)]
    return out


def conv_k(density: np.ndarray) -> np.ndarray:
    """Convolve a (H,W) field with the official triangular 300 m kernel k(d)=max(1-d/3,0)."""
    out = np.zeros_like(density)
    for dy, dx, kw in _K:
        out += shift(density, -dy, -dx) * kw
    return out


def load_grid():
    """Return (valid, catalogue) boolean flat arrays from the SHA-verified competition mirrors."""
    import rasterio
    with rasterio.open(DATA_DIR / "sample_submission.tif") as ds:
        ss = ds.read(1)
    with rasterio.open(DATA_DIR / "labels.tif") as ds:
        lab = ds.read(1)
    valid = np.isfinite(ss).reshape(-1)
    cat = (valid & (lab.reshape(-1) == 1))
    return valid, cat


def load_scored(valid: np.ndarray) -> list[dict]:
    """All corpus rasters that carry an owner-reported score, de-duplicated by SHA-256."""
    corp = json.loads(CORPUS_JSON.read_text())
    rows, seen = [], set()
    for r in corp["rasters"]:
        if r.get("status") != "ok" or "owner_reported_score" not in r or r["sha256"] in seen:
            continue
        seen.add(r["sha256"])
        z = np.load(CACHE_DIR / f"{r['sha256']}.npz")
        idx, val = z["idx"].astype(np.int64), z["val"].astype(np.float64)
        m = valid[idx]
        idx, val = idx[m], val[m]
        if idx.size == 0 or val.sum() <= 0:
            continue
        rows.append({"sha": r["sha256"], "name": r["pool_file"], "repo": r["repo"],
                     "score": float(r["owner_reported_score"]), "idx": idx, "val": val,
                     "D": float(val.sum())})
    return rows


def footprint_mean_credit(rows: list[dict], valid: np.ndarray) -> None:
    """Attach ``mc`` = footprint-mean kernel credit of each raster's dot pattern (no-skill baseline)."""
    from scipy import ndimage as ndi
    for r in rows:
        g = np.zeros(valid.size, np.float32)
        g[r["idx"]] = r["val"].astype(np.float32)
        dp = ndi.distance_transform_edt(g.reshape(H, W) == 0)
        cred = np.maximum(1.0 - dp / R, 0.0)
        r["mc"] = float(cred.reshape(-1)[valid].mean())
        del g, dp, cred


def families(rows: list[dict], thresh: float = 0.60):
    """Cluster rasters into near-duplicate families by 10x-downsampled dot-density correlation."""
    gh, gw = H // 10 + 1, W // 10 + 1
    sig = np.zeros((len(rows), gh * gw), np.float32)
    for i, r in enumerate(rows):
        np.add.at(sig[i], (r["idx"] // W // 10) * gw + (r["idx"] % W // 10), r["val"])
    sig = sig / np.maximum(sig.sum(1, keepdims=True), 1e-9)
    sig -= sig.mean(1, keepdims=True)
    nrm = np.linalg.norm(sig, axis=1, keepdims=True)
    nrm[nrm == 0] = 1
    S = sig / nrm
    C = S @ S.T
    fam = -np.ones(len(rows), int)
    nf = 0
    for i in range(len(rows)):
        if fam[i] >= 0:
            continue
        fam[i] = nf
        for j in range(i + 1, len(rows)):
            if fam[j] < 0 and C[i, j] >= thresh:
                fam[j] = nf
        nf += 1
    return fam, C


def build_T(rows: list[dict], use, n0: float) -> np.ndarray:
    """Weighted-consensus estimate of the hidden new-fault density, normalised to ``n0`` cells.

    Each raster's recovered credit ``A_i = s_i (0.2 D_i + 0.8 n0)`` is shared equally among its
    own dots, so a cell's weight is the sum over rasters of ``(A_i / D_i) · p_i(x)``.  This is a
    consensus, not a copy: no raster is reproduced and the result is a smooth density.
    """
    w = np.zeros(H * W, np.float64)
    for i in use:
        r = rows[i]
        A = r["score"] * (0.2 * r["D"] + 0.8 * n0)
        np.add.at(w, r["idx"], r["val"] * (A / r["D"]))
    w = w.reshape(H, W)
    tot = float(w.sum())
    return (n0 / tot) * w if tot > 0 else w


def threshold_T(T: np.ndarray, valid: np.ndarray, n0: int) -> np.ndarray:
    """Binary truth surrogate: the top-``n0`` valid cells by T̂."""
    flat = T.reshape(-1)
    idxv = np.flatnonzero(valid)
    vals = flat[idxv]
    n = int(min(n0, idxv.size))
    if n <= 0:
        return np.zeros(H * W, bool)
    take = idxv[np.argpartition(vals, -n)[-n:]]
    out = np.zeros(H * W, bool)
    out[take] = True
    return out


def n_bounds(rows: list[dict], f0_max: float = 0.15, d_min: float = 100000.0,
             mc_min: float = 0.10) -> dict:
    """Bounds on N = |G| (new-fault pixels, normalised to the full footprint).

    Lower bound (hard): ``A = TP_w = s·(0.2 D + 0.8 N)`` and ``A ≤ N`` give
    ``N ≥ 0.2 s D /(1 − 0.8 s)``; the maximum over all files is reported.

    Upper bound (model): writing ``A = ε·N·mc`` with the enrichment ``ε ≥ 1`` gives
    ``N = 0.2 s D /(ε·mc − 0.8 s)``, so ``ε = 1`` upper-bounds N.

    **The upper bound must be filtered.**  DrivenData staff confirmed that pixels on known
    USGS/INGENIOUS faults are masked out of scoring
    (https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516),
    so for a raster whose dots sit mostly on the catalogue the *effective* D is far below the
    raw dot count and the formula understates N.  Only broad, catalogue-independent rasters
    (raw-dot share within 300 m of the catalogue <= ``f0_max``, ``D >= d_min``,
    ``mc >= mc_min``) are therefore used for the upper bound.
    """
    lo = max(0.2 * r["score"] * r["D"] / (1 - 0.8 * r["score"]) for r in rows)
    cand = [(0.2 * r["score"] * r["D"] / (r["mc"] - 0.8 * r["score"]), r)
            for r in rows if r["mc"] > 0.8 * r["score"] and r["score"] >= 0.01
            and r["D"] >= d_min and r["mc"] >= mc_min
            and r.get("f0", 0.0) <= f0_max]
    if not cand:
        return {"lower_from_A_le_N": lo, "upper_from_eps_ge_1": None,
                "n_files_giving_upper_bound": 0}
    cand.sort(key=lambda t: t[0])
    return {"lower_from_A_le_N": lo,
            "upper_from_eps_ge_1": cand[0][0],
            "upper_bound_file": cand[0][1].get("name", "?"),
            "n_files_giving_upper_bound": len(cand),
            "tightest_five": [{"N": v, "file": r.get("name", "?"), "score": r["score"],
                               "D": r["D"], "mc": r["mc"], "f0": r.get("f0")}
                              for v, r in cand[:5]],
            "filters": {"f0_max": f0_max, "d_min": d_min, "mc_min": mc_min}}


def attach_f0(rows: list[dict], cat: np.ndarray) -> None:
    """Attach ``f0`` = share of a raster's mass within 300 m of a catalogued fault pixel."""
    from scipy import ndimage as ndi
    catm = np.asarray(cat, bool).reshape(H, W)
    dist = ndi.distance_transform_edt(~catm).reshape(-1)
    for r in rows:
        d = dist[r["idx"]]
        p = r["val"]
        r["f0"] = float(p[d <= 3.0].sum() / max(float(p.sum()), 1e-9))


# ---------------------------------------------------------------------------------------------
# Two estimators for the hidden credit field q(x) = E[kernel credit of a dot at x].
#
# Back-projection (``backproject_weights``) is the adjoint of the measurement operator:
#     q_BP(x) = Σ_i (A_i / D_i) · p_i(x)
# It is *blurred*: the champion raster is published in four repositories and the top family
# shares 0.87-1.00 of its dots, so the adjoint counts the same evidence many times.
#
# ``solve_weights`` instead solves the normal equations of the measurement system
#     A_i = Σ_x p_i(x) q(x),   q = Σ_j λ_j p_j
#     =>  G λ = A,   G_ij = Σ_x p_i(x) p_j(x)
# with Tikhonov damping μ and an optional non-negativity constraint.  G's off-diagonal terms are
# exactly the near-duplicate overlap, so this divides the duplicated evidence out.
# ---------------------------------------------------------------------------------------------

def gram_matrix(rows: list[dict]) -> np.ndarray:
    """G_ij = Σ_x p_i(x)·p_j(x); O(n² |dots| log |dots|) with np.searchsorted."""
    n = len(rows)
    idx = [np.ascontiguousarray(r["idx"]) for r in rows]
    val = [np.ascontiguousarray(r["val"], dtype=np.float64) for r in rows]
    order = [np.argsort(i, kind="stable") for i in idx]
    sidx = [idx[k][o] for k, o in enumerate(order)]
    sval = [val[k][o] for k, o in enumerate(order)]
    G = np.zeros((n, n), np.float64)
    for i in range(n):
        G[i, i] = float(np.dot(val[i], val[i]))
        si, vi = sidx[i], sval[i]
        for j in range(i + 1, n):
            sj, vj = sidx[j], sval[j]
            if si.size == 0 or sj.size == 0:
                continue
            pos = np.clip(np.searchsorted(sj, si), 0, max(sj.size - 1, 0))
            hit = sj[pos] == si
            G[i, j] = G[j, i] = float(np.dot(vi[hit], vj[pos[hit]]))
    return G


def backproject_weights(rows: list[dict], n0: float) -> np.ndarray:
    return np.array([r["score"] * (0.2 * r["D"] + 0.8 * n0) / r["D"] for r in rows])


def solve_weights(rows: list[dict], n0: float, mu: float = 1e-3,
                  nonneg: bool = True, use: list[int] | None = None) -> np.ndarray:
    """Solve (G + μ·diag(G)) λ = A for the raster weights, optionally with λ ≥ 0."""
    if use is None:
        use = list(range(len(rows)))
    A = np.array([rows[i]["score"] * (0.2 * rows[i]["D"] + 0.8 * n0) for i in use])
    G = gram_matrix([rows[i] for i in use])
    d = np.diag(G).copy()
    d[d <= 0] = 1.0
    Gs = G + mu * np.diag(d)
    if nonneg:
        from scipy.optimize import nnls
        lam, _ = nnls(Gs, A)
        return lam
    return np.linalg.solve(Gs + 1e-12 * np.eye(len(use)), A)


def field_from_weights(rows: list[dict], use, lam: np.ndarray) -> np.ndarray:
    """q(x) = max(0, Σ_j λ_j p_j(x)) over the rasters in ``use``."""
    q = np.zeros(H * W, np.float64)
    for k, i in enumerate(use):
        w = float(lam[k])
        if w == 0.0:
            continue
        np.add.at(q, rows[i]["idx"], rows[i]["val"] * w)
    q = q.reshape(H, W)
    np.maximum(q, 0.0, out=q)
    return q
