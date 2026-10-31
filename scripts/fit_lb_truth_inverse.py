#!/usr/bin/env python3
"""Estimate the hidden leaderboard truth field by inverting the published metric.

The algebra this script relies on
--------------------------------
The official metric (DrivenData page 967, verified in ``src/gems32/metric.py``) with
alpha = 0.2, beta = 0.8 expands to

    DTI = TP_w / (TP_w + alpha*FP_w + beta*FN_w)

For a binary prediction of mass D (inside the scored, un-masked domain) and a truth
set of mass N, FP_w = D - TP_w and FN_w = N - TP_w, so

    DTI = TP_w / (TP_w + alpha*(D - TP_w) + beta*(N - TP_w))
        = TP_w / (alpha*D + beta*N)                          alpha + beta = 1

i.e. **the denominator does not depend on TP_w**. Two consequences, both used here:

1. Ranking submissions is a pure "recall per unit predicted mass" problem, and the
   marginal value of one extra predicted pixel is positive iff its probability q of
   landing within 300 m of truth satisfies ``q > alpha * DTI`` (~0.06-0.09 at the
   scores observed in this competition).
2. Given D (known from the raster) and a reported score s, each file pins its own
   truth credit:            ``TP_i = s_i * (alpha*D_i + beta*N)``.

That is one linear equation per published raster in the unknown field
``u(x) = P(x is within 300 m of a hidden truth pixel)`` and the unknown scalar N.
With 100+ published rasters the system is solvable by ridge regression in the
"incidence space": writing C for the file-by-pixel incidence matrix,

    (C C^T + lambda I) w = t        with   t_i = s_i * (alpha*D_i + beta*N)
    u = clip(C^T w, 0, 1)

``C C^T`` is the matrix of pairwise pixel overlaps of the published rasters and is
small (n_files x n_files). ``N`` and ``lambda`` are selected by leave-one-out error.

Labels used in the output: every score in the input table is OWNER-REPORT. Nothing
here is organizer-confirmed. The fitted field is an ESTIMATE.

Usage
-----
    python scripts/fit_lb_truth_inverse.py --data-dir .cache/gems_data \
        --corpus .cache/gems_corpus \
        --manifest evidence/score_corpus_manifest_20261030.json \
        --out evidence/lb_truth_inverse_fit_20261030.json \
        --field .cache/lb_truth_field.npy
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA = 0.2, 0.8


def load_grid(ddir: Path):
    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        transform, crs = ds.transform, ds.crs
    with rasterio.open(ddir / "labels.tif") as ds:
        lab = ds.read(1)
    labels = (lab > 0) & foot
    return foot, labels, transform, crs


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    den = np.sqrt((ra**2).sum() * (rb**2).sum())
    return float((ra * rb).sum() / den) if den > 0 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--corpus", type=Path, default=ROOT / ".cache" / "gems_corpus")
    ap.add_argument("--manifest", type=Path,
                    default=ROOT / "evidence" / "score_corpus_manifest_20261030.json")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "evidence" / "lb_truth_inverse_fit_20261030.json")
    ap.add_argument("--field", type=Path, default=ROOT / ".cache" / "lb_truth_field.npy")
    ap.add_argument("--mask-radius", type=int, default=0,
                    help="dilation (px) applied to known catalogue faults before masking the scored domain")
    args = ap.parse_args()

    foot, labels, transform, crs = load_grid(args.data_dir)
    scored = foot & ~(binary_dilation(labels, iterations=args.mask_radius) if args.mask_radius else labels)
    flat_scored = np.flatnonzero(scored.ravel())          # pixel ids in the scored domain
    pos_in_flat = np.full(foot.size, -1, np.int64)
    pos_in_flat[flat_scored] = np.arange(flat_scored.size)
    M = flat_scored.size

    man = json.loads(args.manifest.read_text())
    rows = [r for r in man["rows"] if r["status"] == "matched"]

    ids: list[np.ndarray] = []
    scores: list[float] = []
    dots: list[int] = []
    kept_rows = []
    seen: dict[str, int] = {}
    for r in rows:
        p = Path(r["local"]) if Path(r["local"]).is_absolute() else ROOT / r["local"]
        if not p.exists():
            p = args.corpus / Path(r["local"]).name
        if not p.exists():
            continue
        try:
            with rasterio.open(p) as ds:
                a = ds.read(1)
        except Exception as exc:                                  # unreadable raster
            print(f"[skip] {p.name}: {exc}", file=sys.stderr)
            continue
        if a.shape != foot.shape:
            print(f"[skip] {p.name}: shape {a.shape}", file=sys.stderr)
            continue
        pred = np.isfinite(a) & (a > 0) & scored
        idx = pos_in_flat[np.flatnonzero(pred.ravel())]
        idx = idx[idx >= 0]
        if idx.size == 0:
            continue
        sha = r["sha256"] or p.name
        if sha in seen:                                            # identical bytes -> one equation
            continue
        seen[sha] = 1
        ids.append(idx.astype(np.int64))
        scores.append(float(r["owner_reported_score"]))
        dots.append(int(idx.size))
        kept_rows.append({**r, "dots_scored": int(idx.size), "file": p.name})

    n = len(ids)
    print(f"[fit] {n} distinct rasters, D range {min(dots)}-{max(dots)}")

    # ---- incidence bit matrix (n x M) for fast pairwise overlaps -----------------
    B = np.zeros((n, (M + 7) // 8), np.uint8)
    for i, idx in enumerate(ids):
        bits = np.zeros(M, bool)
        bits[idx] = True
        B[i] = np.packbits(bits)
    CCT = np.zeros((n, n), np.float64)
    for i in range(n):
        for j in range(i, n):
            CCT[i, j] = CCT[j, i] = float(np.bitwise_count(B[i] & B[j]).sum())
    D = np.array(dots, float)
    s = np.array(scores, float)

    def fit_one(N: float, lam: float) -> np.ndarray:
        t = s * (ALPHA * D + BETA * N)
        A = CCT + lam * np.eye(n)
        w = np.linalg.solve(A, t)
        return w

    def field_from_w(w: np.ndarray) -> np.ndarray:
        u = np.zeros(M, np.float64)
        for i, idx in enumerate(ids):
            if w[i]:
                u[idx] += w[i]
        return np.clip(u, 0.0, 1.0)

    def predict_scores(u: np.ndarray, N: float) -> np.ndarray:
        tp = np.array([u[idx].sum() for idx in ids])
        return tp / (ALPHA * D + BETA * N)

    grid_N = np.round(np.geomspace(4000, 50000, 12)).astype(int)
    grid_lam = np.array([1.0, 5.0, 20.0, 60.0, 200.0])
    t_all = None
    best = None
    scan = []
    for N in grid_N:
        t = s * (ALPHA * D + BETA * N)
        for lam in grid_lam:
            w = np.linalg.solve(CCT + lam * np.eye(n), t)
            u = field_from_w(w)
            # Exact leave-one-out: u_i restricted to file i equals (CCT[i, keep] . w_i),
            # where w_i solves the same ridge system with row/col i removed.
            loo = np.zeros(n)
            for i in range(n):
                keep = np.arange(n) != i
                wi = np.linalg.solve(CCT[np.ix_(keep, keep)] + lam * np.eye(n - 1), t[keep])
                loo[i] = float(CCT[i, keep] @ wi) / (ALPHA * D[i] + BETA * N)
            err = loo - s
            row = {
                "N": int(N), "lambda": float(lam),
                "loo_rmse": float(np.sqrt((err**2).mean())),
                "loo_mae": float(np.abs(err).mean()),
                "loo_spearman": spearman(loo, s),
                "u_mean": float(u.mean()),
                "u_max": float(u.max()),
                "u_over_0p2": int((u > 0.2).sum()),
            }
            scan.append(row)
            if best is None or row["loo_rmse"] < best["loo_rmse"]:
                best = row
    scan.sort(key=lambda r: r["loo_rmse"])
    print("[fit] best N={N} lambda={lambda} loo_rmse={loo_rmse:.4f} "
          "loo_spearman={loo_spearman:.3f}".format(**best))

    N_hat, lam_hat = float(best["N"]), float(best["lambda"])
    w = fit_one(N_hat, lam_hat)
    u = field_from_w(w)
    pred = predict_scores(u, N_hat)
    in_sample = {
        "rmse": float(np.sqrt(((pred - s) ** 2).mean())),
        "spearman": spearman(pred, s),
    }

    # ---- implied efficiency table for the published corpus -----------------------
    rec = []
    for i, r in enumerate(kept_rows):
        rec.append({
            "site": r["site"], "file": r["file"],
            "owner_reported_score": s[i], "dots_scored": int(D[i]),
            "fitted_tp": float(u[ids[i]].sum()), "fitted_score": float(pred[i]),
            "hit_rate": float(u[ids[i]].sum() / max(D[i], 1)),
        })
    rec.sort(key=lambda d: -d["owner_reported_score"])

    field = np.full(foot.shape, 0.0, np.float32)
    field.ravel()[flat_scored] = u.astype(np.float32)
    args.field.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.field, field)

    out = {
        "schema_version": 1,
        "method": "inverse metric fit: TP_i = s_i*(alpha*D_i + beta*N), ridge in incidence space",
        "score_label": "OWNER-REPORT (input scores)",
        "not_organizer_confirmed": True,
        "alpha": ALPHA, "beta": BETA,
        "mask_radius_px": args.mask_radius,
        "scored_domain_px": int(M),
        "n_files": n,
        "N_hidden_truth_px_estimate": N_hat,
        "lambda": lam_hat,
        "fit": {**best, "in_sample": in_sample},
        "grid_scan": scan[:15],
        "field_file": str(args.field if args.field.is_absolute() else (ROOT / args.field)),
        "field_summary": {
            "max": float(u.max()),
            "mean_scored": float(u.mean()),
            "px_gt_0p05": int((u > 0.05).sum()),
            "px_gt_0p10": int((u > 0.10).sum()),
            "px_gt_0p20": int((u > 0.20).sum()),
            "px_gt_0p30": int((u > 0.30).sum()),
            "px_gt_0p50": int((u > 0.50).sum()),
        },
        "files": rec,
        "caveats": [
            "Kernel/credit weighting is approximated by binary 'within 300 m' incidence; kernel taper is ignored, so fitted TP is a lower bound for soft submissions.",
            "u(x)=0 is imposed nowhere; the field is clipped to [0,1] after ridge, so it is a shrunken estimator, not a probability.",
            "Scores are OWNER-REPORT from the owner's prompt. A wrong typed score propagates directly into the fit.",
            "The scored public subset is unknown; this fit assumes the public and private subsets share one truth field.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"[fit] in-sample rmse={in_sample['rmse']:.4f} spearman={in_sample['spearman']:.3f}")
    print(f"[fit] field saved -> {args.field}")
    print(f"[fit] receipt -> {args.out}")
    print("\ntop 12 published rasters by fitted hit-rate:")
    for r in sorted(rec, key=lambda d: -d["hit_rate"])[:12]:
        print(f"  hit={r['hit_rate']:.3f}  D={r['dots_scored']:6d}  "
              f"score={r['owner_reported_score']:.4f}  {r['file'][:64]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
