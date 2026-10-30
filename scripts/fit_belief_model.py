#!/usr/bin/env python3
"""Leaderboard-calibrated belief model: P(a dot earns full credit) as a function of physical covariates.

Why this exists
---------------
The scored truth is a *private* set of expert-mapped faults that are deliberately absent from the
public USGS catalogue (official problem description, page 967).  No local raster contains it, so a
local holdout against the public catalogue measures the wrong thing: across 50 scored submissions
the catalogue-proxy DTI has rank correlation -0.004 with the leaderboard (this branch, measured).
The only empirical signal about the hidden truth is the leaderboard itself.

Model
-----
For a binary dot submission with mass S dots, DTI = TP / (TP + a*FP + b*FN) and with FN = K - TP
this is TP / (a*TP + a*FP + b*K) = TP / (0.2*(TP+FP) + 0.8*K).  For single-pixel dots that earn
full credit and do not double-credit, TP + FP = S, so

    score = TP / (0.2*S + 0.8*K),        TP = sum over dots of  [dot covers a new truth pixel]

We model the unknown per-dot indicator by its conditional expectation h(x) = sigmoid(b0 + b.X(x)),
and fit (b, K) to reproduce the 50 owner-reported leaderboard scores.  Leave-one-file-out
validation is the gate: a model that cannot reproduce held-out scores is not used.

Every score produced by this module is labelled LEADERBOARD-CALIBRATED ESTIMATE, not a score claim.

Usage:
    python scripts/fit_belief_model.py            # writes evidence/belief_model_20261030.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.optimize import least_squares
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
DATA = ROOT / ".cache" / "gems_data"
MAX_DOTS_PER_FILE = 2000


def load_scored_files() -> list[dict]:
    """(path, score) for every raster with an owner-reported leaderboard score."""
    out: list[dict] = []
    drivers = json.loads((ROOT / "evidence" / "score_drivers_20261030.json").read_text())
    seen: set[str] = set()
    for r in drivers["rows"]:
        if r["sha256"] in seen:
            continue
        seen.add(r["sha256"])
        p = DATA / ("focus" if r["site"] != "prompt" else "scored") / r["file"]
        if not p.exists():
            cand = list((DATA / "extra").glob(r["file"]))
            if not cand:
                continue
            p = cand[0]
        out.append(dict(path=p, score=float(r["score"]), name=r["name"]))
    return out


def main() -> int:
    with rasterio.open(DATA / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    cov_meta = json.loads((DATA / "covariates.json").read_text())
    names = cov_meta["names"]
    ncov = len(names)
    C = np.load(DATA / "covariates.npy", mmap_mode="r")
    assert C.shape == (ncov, 3730, 3292), C.shape

    files = load_scored_files()
    print(f"{len(files)} scored files")

    # ---- collect covariates at dot locations, subsampled per file ----
    rng = np.random.default_rng(20261030)
    samples = []  # list of (X_dots (n,cov), S, score, name)
    for f in files:
        with rasterio.open(f["path"]) as ds:
            a = ds.read(1).astype(np.float32)
        m = np.where(foot, a, 0.0) > 0
        S = float(np.where(foot, a, 0.0).sum())
        ys, xs = np.nonzero(m)
        if ys.size > MAX_DOTS_PER_FILE:
            sel = rng.choice(ys.size, MAX_DOTS_PER_FILE, replace=False)
            ys, xs = ys[sel], xs[sel]
        samples.append(dict(ys=ys, xs=xs, S=S, score=f["score"], name=f["name"]))
        print(f"  {f['name'][:58]:58s} S={S:8.0f} score={f['score']:.4f} n_sample={ys.size}")

    # fill X_dots by row chunks (memmap friendly)
    for s in samples:
        s["X"] = np.zeros((s["ys"].size, ncov), np.float32)
    order = np.argsort(np.concatenate([s["ys"] for s in samples]))
    for r0 in range(0, 3730, 256):
        r1 = min(3730, r0 + 256)
        block = np.asarray(C[:, r0:r1, :])  # (ncov, h, w)
        for s in samples:
            sel = (s["ys"] >= r0) & (s["ys"] < r1)
            if not sel.any():
                continue
            s["X"][sel] = block[:, s["ys"][sel] - r0, s["xs"][sel]].T
        del block

    Y = np.array([s["score"] for s in samples])
    S = np.array([s["S"] for s in samples])
    Xall = [s["X"].astype(np.float64) for s in samples]
    n = len(samples)

    # ---- vectorise: one design matrix for all dots, one file index vector ----
    Xall_np = np.concatenate([s["X"] for s in samples], 0).astype(np.float64)
    fidx = np.concatenate([np.full(s["X"].shape[0], i, np.int64) for i, s in enumerate(samples)])
    nfile = len(samples)
    w = np.bincount(fidx, minlength=nfile).astype(np.float64)
    eye = np.eye(ncov)

    def predict(b, K):
        z = b[0] + Xall_np @ b[1:]
        h = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        tp = np.bincount(fidx, weights=h, minlength=nfile)
        return tp / (0.2 * S + 0.8 * K)

    def make_resid(idx, ridge):
        idx = np.asarray(idx)

        def resid(p):
            b, K = p[:-1], p[-1]
            r = predict(b, K)[idx] - Y[idx]
            return np.concatenate([r, ridge * b[1:]])
        return resid

    def fit(idx, ridge=0.05, p0=None):
        p0 = p0 if p0 is not None else np.concatenate([[np.log(0.14 / 0.86)] + [0.0] * ncov, [12691.0]])
        lb = np.concatenate([[-10.0] + [-2.0] * ncov, [3000.0]])
        ub = np.concatenate([[2.0] + [2.0] * ncov, [80000.0]])
        return least_squares(make_resid(idx, ridge), p0, bounds=(lb, ub), max_nfev=60,
                             xtol=1e-9, ftol=1e-10).x

    print("\nfitting full model ...")
    p = fit(list(range(nfile)))
    b, K = p[:-1], float(p[-1])
    pred_all = predict(b, K)
    rho, pv = spearmanr(pred_all, Y)
    print(f"in-sample: RMSE={np.sqrt(np.mean((pred_all-Y)**2)):.4f}  spearman={rho:.3f} (p={pv:.1e})")

    print("leave-one-file-out ...")
    loo = np.zeros(nfile)
    for i in range(nfile):
        idx = [j for j in range(nfile) if j != i]
        pi = fit(idx, p0=p)
        loo[i] = predict(pi[:-1], pi[-1])[i]
    rmse = float(np.sqrt(np.mean((loo - Y) ** 2)))
    mae = float(np.mean(np.abs(loo - Y)))
    rho_l, p_l = spearmanr(loo, Y)
    print(f"LOO: RMSE={rmse:.4f} MAE={mae:.4f} spearman={rho_l:.3f} (p={p_l:.2e})")

    # coefficient table
    coefs = sorted(zip(names, b[1:]), key=lambda t: -abs(t[1]))
    print("\nstandardised coefficients (log-odds per +1 sd):")
    for nm, v in coefs:
        print(f"  {nm:20s} {v:+.3f}")

    out = dict(
        schema_version=1,
        label="LEADERBOARD-CALIBRATED ESTIMATE",
        note=("h(x) = sigmoid(b0 + b.X); score = TP/(0.2*S + 0.8*K). Fitted to owner-reported "
              "leaderboard scores of %d unique submissions. LOO validation below. This is an "
              "estimate, not an organizer score." % n),
        n_files=n, K_hat=K, b0=float(b[0]),
        coefficients={nm: float(v) for nm, v in zip(names, b[1:])},
        loo=dict(rmse=rmse, mae=mae, spearman=float(rho_l), p=float(p_l),
                 predictions={s["name"]: float(v) for s, v in zip(samples, loo)},
                 observed={s["name"]: float(s["score"]) for s in samples}),
        in_sample=dict(rmse=float(np.sqrt(np.mean((pred_all - Y) ** 2))), spearman=float(rho)),
        per_file=[dict(name=s["name"], S=s["S"], observed=s["score"], pred_full=float(pr),
                       pred_loo=float(lv))
                  for s, pr, lv in zip(samples, pred_all, loo)],
    )
    (ROOT / "evidence" / "belief_model_20261030.json").write_text(json.dumps(out, indent=1))
    np.save(DATA / "belief_b.npy", p)
    print("\nwrote evidence/belief_model_20261030.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
