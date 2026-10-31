#!/usr/bin/env python3
"""Paired comparison of two dot emitters on the held-out yardstick (no calibration needed).

Emitter A — ``emit_spaced``: descending-q greedy non-max suppression at a fixed minimum spacing,
cut at a fixed dot budget (what the candidate currently uses).

Emitter B — ``gems32.emitter.emit``: the repository's lazy-greedy maximum-expected-coverage
emitter with the metric's own marginal credit bar, run to a self-consistent prior DTI.

Both are scored on the same independent T̂_test yardstick in the same folds, so the difference is
a paired measurement.

Usage:
    python scripts/compare_emitters_20261031.py --n0 12000
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import corpus as CP, fastdti  # noqa: E402
from gems32.corpus import H, W  # noqa: E402

OUT = ROOT / "evidence" / "compare_emitters_20261031.json"


def emit_spaced(q, keep, spacing, budget=None):
    cand = np.flatnonzero(keep & (q.reshape(-1) > 0))
    order = cand[np.argsort(-q.reshape(-1)[cand], kind="stable")]
    from scipy.spatial import cKDTree
    kept_ys, kept_xs, chosen = [], [], []
    r = float(spacing)
    for s in range(0, order.size, 20000):
        chunk = order[s:s + 20000]
        cy, cx = chunk // W, chunk % W
        if kept_ys:
            tree = cKDTree(np.column_stack([np.concatenate(kept_ys), np.concatenate(kept_xs)]))
            d, _ = tree.query(np.column_stack([cy, cx]), k=1, distance_upper_bound=r + 1e-9)
            ok = ~np.isfinite(d) | (d > r)
        else:
            ok = np.ones(chunk.size, bool)
        chosen.append(chunk[ok])
        kept_ys.append(cy[ok])
        kept_xs.append(cx[ok])
        if budget is not None and sum(len(c) for c in chosen) >= budget:
            break
    sel = np.concatenate(chosen)
    if budget is not None:
        sel = sel[:budget]
    out = np.zeros(H * W, bool)
    out[sel] = True
    return out


def emit_greedy(field, support_top, prior_dti=0.26, rounds=3):
    """Repository greedy emitter, restricted to the top-``support_top`` cells of the field."""
    from gems32.emitter import emit
    f = np.asarray(field, np.float64).reshape(H, W).copy()
    if support_top and (f > 0).sum() > support_top:
        thr = np.sort(f.ravel())[-support_top]
        f[f < thr] = 0.0
    s = prior_dti
    for _ in range(rounds):
        mask, log = emit(f, prior_dti=s)
        # self-consistent DTI: TP/(0.2 D + 0.8 N) with TP = credit delivered, D = dots
        n = int(mask.sum())
        if n == 0:
            return mask, log, s
        tp = float(log.credit_delivered)
        new_s = tp / (0.2 * n + 0.8 * float(field.sum()))
        if abs(new_s - s) < 1e-4:
            s = new_s
            break
        s = new_s
    return mask, log, s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n0", type=float, default=12000.0)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--skip-fold0", action="store_true")
    ap.add_argument("--support-top", type=int, default=400000)
    args = ap.parse_args()

    n0 = float(args.n0)
    valid, cat = CP.load_grid()
    rows = CP.load_scored(valid)
    fam, _ = CP.families(rows, 0.60)
    nfam = int(fam.max()) + 1
    order = np.argsort(-np.bincount(fam, minlength=nfam))
    fold_of_fam = np.zeros(nfam, int)
    load = np.zeros(args.folds, int)
    for f in order:
        k = int(np.argmin(load)); fold_of_fam[f] = k
        load[k] += int(np.bincount(fam, minlength=nfam)[f])

    res = []
    for k in range(args.folds):
        if args.skip_fold0 and k == 0:
            continue
        test_fams = {f for f in range(nfam) if fold_of_fam[f] == k}
        test_i = [i for i in range(len(rows)) if fam[i] in test_fams]
        train_i = [i for i in range(len(rows)) if fam[i] not in test_fams]
        T_test = CP.build_T(rows, test_i, n0)
        TT = fastdti.Truth.from_mask(CP.threshold_T(T_test, valid, int(round(n0))))

        lam = CP.solve_weights(rows, n0, mu=1e-3, nonneg=True, use=train_i)
        qw = CP.field_from_weights(rows, train_i, lam)
        q = CP.conv_k(qw)

        a = emit_spaced(q, valid, 3.0, 60000)
        ia = np.flatnonzero(a)
        da = fastdti.dti_dots(ia, np.ones(ia.size), TT)

        bmask, blog, s = emit_greedy(q, args.support_top)
        ib = np.flatnonzero(bmask.reshape(-1))
        db = fastdti.dti_dots(ib, np.ones(ib.size), TT)

        # champion reference (only meaningful when its family is not in TEST)
        champ = max(range(len(rows)), key=lambda i: rows[i]["score"])
        champ_in_test = fam[champ] in test_fams
        dc = fastdti.dti_dots(rows[champ]["idx"], rows[champ]["val"].copy(), TT)

        res.append({"fold": k, "n_train": len(train_i),
                    "A_spaced": {"dots": int(ia.size), "dti": da["dti"]},
                    "B_greedy": {"dots": int(ib.size), "dti": db["dti"], "prior_dti": s},
                    "champion": {"dti": dc["dti"], "observed": rows[champ]["score"],
                                 "family_in_test": bool(champ_in_test)}})
        print(f"fold {k}: A(spaced)={da['dti']:.4f} ({ia.size}d)  B(greedy)={db['dti']:.4f} "
              f"({ib.size}d, s={s:.3f})  champ={dc['dti']:.4f} "
              f"{'(IN TEST - contaminated)' if champ_in_test else ''}", flush=True)

    good = [r for r in res if not r["champion"]["family_in_test"]]
    A = np.array([r["A_spaced"]["dti"] for r in res])
    B = np.array([r["B_greedy"]["dti"] for r in res])
    C = np.array([r["champion"]["dti"] for r in good])
    OUT.write_text(json.dumps({
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "n0": n0, "support_top": args.support_top,
        "folds": res,
        "summary": {
            "A_spaced_mean": float(A.mean()), "B_greedy_mean": float(B.mean()),
            "delta_B_minus_A": float((B - A).mean()),
            "champion_mean_on_honest_folds": float(C.mean()) if len(C) else None,
            "A_minus_champion": float(A[:len(good)].mean() - C.mean()) if len(C) else None,
        },
    }, indent=1))
    print(json.dumps(json.loads(OUT.read_text())["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
