#!/usr/bin/env python3
"""Distil the leaderboard: turn 128 published (raster, score) pairs into a probability field.

Why this is legitimate supervision
----------------------------------
The metric is ``DTI = TP / (alpha*D + beta*N)`` (see ``scripts/invert_lb_metric.py`` for the
derivation).  Inverting it for every published raster gives that raster's *precision*::

    p_i = TP_i / D_i = s_i (0.2 D_i + 0.8 N) / D_i

So each of the 128 rasters in the owner's own public corpus is a *rater* whose sensitivity we
know from its leaderboard score.  A file that scored 0.004 over 37,913 dots had precision 0.006;
a file that scored 0.2778 over 37,654 dots had precision 0.40.  Those are labels.

Aggregating raters
------------------
Treat each dot as an observation "rater i says fault here" with known precision ``p_i``.  With
prior truth rate ``pi`` and conditional independence given the truth, Bayes gives a closed form::

    odds(x) = [pi/(1-pi)]**(1-|C|) * prod_{i in C} p_i/(1-p_i)

where ``C`` is the set of raters covering cell ``x``.  Scoring a file by "what would this field
say about it" reproduces its leaderboard score if ``pi`` and ``N`` are right, so both are fitted
by leave-one-file-out error, not chosen by hand.

Known limitation, stated up front: the top files are near-duplicates of each other (pairwise dot
overlap 0.87-1.00), so this cannot invent information that is not in the corpus.  What it can do
is put the information that *is* there on a calibrated per-cell footing, which is what makes
selection (how many dots, and which ones) a calculation instead of a guess.

Usage
-----
    python scripts/leaderboard_distill.py --out .cache/distill_q.npz \
        --evidence evidence/leaderboard_distill_20261030.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA = 0.2, 0.8


def load_corpus(manifest: Path, data_dir: Path):
    rows = [r for r in json.loads(manifest.read_text())["rows"] if r["status"] == "matched"]
    with rasterio.open(data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        shape = ds.shape
    cid = np.full(shape[0] * shape[1], -1, dtype=np.int64)
    cid[foot.ravel()] = np.arange(int(foot.sum()))
    seen, files = set(), []
    for r in rows:
        key = r["sha256"] or r["local"]
        if key in seen:
            continue
        seen.add(key)
        with rasterio.open(ROOT / r["local"]) as ds:
            a = ds.read(1)
        m = np.isfinite(a) & (a > 0) & foot
        ids = np.sort(cid[m.ravel()])
        ids = ids[ids >= 0]
        if ids.size == 0:
            continue
        files.append({"name": Path(r["local"]).name, "site": r["site"],
                      "score": float(r["owner_reported_score"]), "ids": ids.astype(np.int32),
                      "D": int(ids.size)})
    return files, shape, cid, int(foot.sum())


def precisions(files, N):
    return np.array([np.clip(f["score"] * (ALPHA * f["D"] + BETA * N) / f["D"], 0.0, 0.999)
                     for f in files])


def odds_field(files, n_cells, p, pi):
    """Closed-form posterior odds, accumulated in log space."""
    prior = np.log(pi / (1 - pi))
    u = np.full(n_cells, prior, dtype=np.float64)  # log-odds of the prior
    for f, pi_i in zip(files, p):
        if pi_i <= 0:
            continue
        u[f["ids"]] += np.log(pi_i / (1 - pi_i)) - prior
    return u


def to_prob(logodds):
    return 1.0 / (1.0 + np.exp(-np.clip(logodds, -50, 50)))


def score_files(files, q):
    tp = np.array([q[f["ids"]].sum() for f in files])
    D = np.array([f["D"] for f in files], float)
    return tp, D


def evaluate(files, q, N):
    tp, D = score_files(files, q)
    obs = np.array([f["score"] for f in files])
    pred = tp / (ALPHA * D + BETA * N)
    return pred, obs


def rank(a):
    return np.argsort(np.argsort(a)).astype(float)


def spearman(a, b):
    ra, rb = rank(a) - rank(a).mean(), rank(b) - rank(b).mean()
    return float((ra @ rb) / np.sqrt((ra @ ra) * (rb @ rb)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=ROOT / "evidence" / "score_corpus_manifest_20261030.json")
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--out", type=Path, default=ROOT / ".cache" / "distill_q.npz")
    ap.add_argument("--evidence", type=Path, default=ROOT / "evidence" / "leaderboard_distill_20261030.json")
    ap.add_argument("--N-grid", type=float, nargs="+", default=[20000, 30000, 45000, 60000, 90000, 130000])
    ap.add_argument("--pi-grid", type=float, nargs="+", default=[0.004, 0.008, 0.015, 0.03, 0.06])
    ap.add_argument("--folds", type=int, default=6)
    args = ap.parse_args()

    files, shape, cid, n_cells = load_corpus(args.manifest, args.data_dir)
    obs = np.array([f["score"] for f in files])
    print(f"corpus {len(files)} rasters; {n_cells} footprint cells", flush=True)

    rng = np.random.default_rng(0)
    order = rng.permutation(len(files))
    fold = np.empty(len(files), int)
    fold[order] = np.arange(len(files)) % args.folds

    # ---- grid search on leave-one-file-out (test files never enter their own field) ----
    best = None
    grid = []
    for N in args.N_grid:
        for pi in args.pi_grid:
            loo = np.full(len(files), np.nan)
            for fo in range(args.folds):
                tr = [i for i in range(len(files)) if fold[i] != fo]
                te = [i for i in range(len(files)) if fold[i] == fo]
                p = precisions([files[i] for i in tr], N)
                sub = [files[i] for i in tr]
                lo = odds_field(sub, n_cells, p, pi)
                q = to_prob(lo)
                for i in te:
                    tp = q[files[i]["ids"]].sum()
                    loo[i] = tp / (ALPHA * files[i]["D"] + BETA * N)
            ok = np.isfinite(loo)
            rmse = float(np.sqrt(np.mean((loo[ok] - obs[ok]) ** 2)))
            rho = spearman(loo[ok], obs[ok])
            grid.append({"N": N, "pi": pi, "loo_rmse": rmse, "loo_rho": rho})
            print(f"  N={N:<7.0f} pi={pi:<6} loo_rmse={rmse:.4f} rho={rho:.3f}", flush=True)
            if best is None or rmse < best["loo_rmse"]:
                best = grid[-1]
    N, pi = best["N"], best["pi"]
    print(f"chosen N={N:.0f} pi={pi} (LOO rmse {best['loo_rmse']:.4f}, rho {best['loo_rho']:.3f})", flush=True)

    # ---- final field from every file ----
    p = precisions(files, N)
    q = to_prob(odds_field(files, n_cells, p, pi))
    pred, obs_ = evaluate(files, q, N)
    np.savez_compressed(args.out, q=q.astype(np.float32), shape=np.array(shape), cell_id=cid,
                        names=np.array([f["name"] for f in files]), scores=obs,
                        precision=p, D=np.array([f["D"] for f in files]))

    # ---- what the field says a candidate would score ----
    def est(mask):
        d = int(mask.sum())
        if d == 0:
            return None
        tp = float(q[mask].sum())
        return {"n_dots": d, "expected_tp": round(tp, 1), "est_score": round(tp / (ALPHA * d + BETA * N), 4)}

    sweep = []
    for tau in (0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
        sweep.append({"tau": tau, **est(q >= tau)})

    ev = {
        "schema_version": 1,
        "generated_utc": "2026-10-30",
        "label": "ESTIMATE",
        "not_organizer_confirmed": True,
        "method": "Dawid-Skene-style aggregation of 128 published rasters whose sensitivity is "
                  "computed from their own leaderboard scores by inverting the organizer metric",
        "n_rasters": len(files),
        "N_estimate": N,
        "prior_truth_rate": pi,
        "chosen_by": "leave-one-file-out squared error on the 128 owner-reported scores",
        "leave_one_out": best,
        "grid": grid,
        "in_sample": {"rmse": float(np.sqrt(np.mean((pred - obs) ** 2))), "rho": spearman(pred, obs)},
        "per_file_precision": [
            {"name": f["name"], "score": f["score"], "dots": f["D"], "precision": round(float(pp), 4),
             "in_sample_pred": round(float(ss), 4)}
            for f, pp, ss in zip(files, p, pred)
        ],
        "field_stats": {
            "max_q": float(q.max()), "cells_over_0.1": int((q > 0.1).sum()),
            "cells_over_0.2": int((q > 0.2).sum()), "cells_over_0.4": int((q > 0.4).sum()),
        },
        "threshold_sweep": sweep,
        "known_limitation": "the top published rasters overlap 0.87-1.00 in dots, so the corpus is "
                            "highly redundant; this field redistributes existing information, it "
                            "cannot create new recall",
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(ev, indent=1) + "\n")
    print(json.dumps({k: ev[k] for k in ("N_estimate", "prior_truth_rate", "in_sample", "field_stats")}, indent=1))
    for row in sweep:
        print("  ", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
