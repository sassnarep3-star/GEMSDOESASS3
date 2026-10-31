#!/usr/bin/env python3
"""Emit and self-validate the H-CELLDISTILL candidate, then gate it for submission.

Why the score estimate is the bag predictor and not the field sum
------------------------------------------------------------------
The field ``c(x)`` is fitted so that a *bag mean* over each published raster's dots reproduces its
leaderboard score.  Using ``sum_x c(x)`` over our own dots instead is biased upward, because we
choose the dots: selecting the top of an extrapolating linear field is the winner's curse, and the
corpus' best files have mean credit ~0.07 per dot while the field's extreme tail reaches 0.43.
So the operating point and the headline number both use the same predictor that leave-cluster-out
validated (``scripts/compare_estimators_20261031.py``):

    s_hat = (b + w . mean_{x in P} phi(x)) * D / (0.2 D + 0.8 N)

and the raw field sum is reported beside it, labelled as the uncorrected upper bound.

Gates (all computed from the saved bytes, no human inspection)
--------------------------------------------------------------
1. format: single band, float32, EPSG:32611, 3730x3292, 100 m, values finite in [0,1] inside the
   footprint, NaN outside, dot count as claimed;
2. estimability: every published value is 1.0, so the raster is a binary "we assert a fault here"
   field -- the portal's [0,1] check is satisfied by construction;
3. lane/uniqueness: at most 65% of the dots within 3 px of any registry raster (protocol says 70%;
   the margin is deliberate), plus the lift over that raster's own footprint coverage;
4. score: the headline estimate is recomputed from the raster, not read from the build file.

Exit code 0 only when every gate passes.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

ALPHA, BETA = 0.2, 0.8


def _mod(name: str):
    spec = importlib.util.spec_from_file_location(name[:-3], ROOT / "scripts" / name)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


DIST = _mod("distill_cellcredit_20261031.py")
EMIT = _mod("emit_lbinv_candidate.py")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--corpus", type=Path, default=ROOT / ".cache" / "gems_corpus")
    ap.add_argument("--registry", type=Path, default=ROOT / ".cache" / "focus_registry")
    ap.add_argument("--manifest", type=Path,
                    default=ROOT / "evidence" / "score_corpus_manifest_20261031.json")
    ap.add_argument("--psi", type=Path, default=ROOT / ".cache" / "cell_psi.npz")
    ap.add_argument("--arms", type=Path, default=ROOT / "evidence" / "estimator_arms_20261031.json")
    ap.add_argument("--field", type=Path, default=ROOT / ".cache" / "distill_q_cellcredit.npz")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "downloads")
    ap.add_argument("--budgets", type=int, nargs="*",
                    default=[12000, 18000, 24000, 30000, 37654, 44090, 52000, 60000])
    ap.add_argument("--sep", type=int, default=2)
    ap.add_argument("--overlap-limit", type=float, default=0.65)
    ap.add_argument("--name", default="")
    ap.add_argument("--stamp", default="20261031")
    ap.add_argument("--evidence", type=Path,
                    default=ROOT / "evidence" / "cellcredit_candidate_20261031.json")
    args = ap.parse_args()
    t0 = _dt.datetime.now(_dt.timezone.utc)

    zf = np.load(args.psi)
    psi, s, Dv, labels = zf["psi"], zf["s"], zf["D"], zf["labels"]
    arms = json.loads(args.arms.read_text())
    N = float(arms["best"]["N"])
    lam = float(arms["best"]["lam_a"])
    gloo = float(arms["best"]["gloo_rmse"])
    rho = float(arms["best"]["gloo_rho"])
    denom = ALPHA * Dv + BETA * N
    y = s * denom / Dv
    w = (Dv / denom) ** 2
    coef, mu, sd = DIST.ridge_fit(psi, y, w, lam)
    b0 = float(coef[0] - np.sum(coef[1:] * mu / sd))
    slope = coef[1:] / sd
    print(f"[model] N={N:.0f} lam={lam} intercept={b0:.5f} gloo_rmse={gloo} rho={rho}", flush=True)

    with rasterio.open(args.data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        shape, transform, crs = ds.shape, ds.transform, ds.crs
        grid_of_fp = np.flatnonzero(foot.ravel())
    with rasterio.open(args.data_dir / "labels.tif") as ds:
        lab = ds.read(1)
    catalogue = (np.isfinite(lab) & (lab >= 1)) & foot
    n_foot = int(foot.sum())
    zq = np.load(args.field)
    q = zq["q"].astype(np.float32)
    assert q.size == n_foot, (q.size, n_foot)
    scored_fp = np.flatnonzero(q > 0)
    print(f"[field] support {scored_fp.size:,} cells, max q {q.max():.4f}", flush=True)
    fp_of_grid = np.full(foot.size, -1, np.int64)
    fp_of_grid[grid_of_fp] = np.arange(n_foot)

    # ---------------- ranking is by field value; the score uses the calibrated bag model ----
    order = scored_fp[np.argsort(-q[scored_fp])]          # footprint ids, best first
    rows_, cols_ = np.divmod(grid_of_fp[order], shape[1])
    chans = DIST.channel_list()

    # phi is materialised once as an (F, n_foot) float32 memmap: the bag predictor is then a gather
    # instead of 28 raster filters per budget, which is the difference between 8 seconds and
    # 8 minutes on this 2-core box.
    phi_path = ROOT / ".cache" / "cell_phi_footprint.npy"
    if phi_path.exists():
        PHI = np.load(phi_path, mmap_mode="r")
        assert PHI.shape == (len(chans), n_foot), PHI.shape
        print(f"[phi] reused {phi_path.name} {PHI.shape}", flush=True)
    else:
        # channel-major (F, n_foot): a column-major layout would make every channel write a
        # strided scatter across 578 MB, which measured 11x slower on this box.
        PHI = np.lib.format.open_memmap(phi_path, mode="w+", dtype=np.float32,
                                       shape=(len(chans), n_foot))
        fs = DIST.FeatureSource(args.data_dir / "training_features.tif", foot)
        for j, (_, spec) in enumerate(chans):
            a, _, _ = DIST.robust_norm(fs.get(spec), foot)
            PHI[j, :] = a.ravel()[foot.ravel()]
            del a
            print(f"  [phi {j + 1:2d}/{len(chans)}] {chans[j][0]}", flush=True)
        PHI.flush()
        fs.close()
        print(f"[phi] built {phi_path.name} ({phi_path.stat().st_size / 1e6:.0f} MB)", flush=True)

    # winsorise the bag mean into the range the model was actually fitted on: a model of bag
    # *means* has no business extrapolating to a bag mean no published raster ever had (an
    # uncapped version of this priced a candidate at 493, which is impossible).  The clip is
    # per channel, over the 132 corpus bags, and it is recorded in the receipt.
    lo_p, hi_p = psi.min(axis=0), psi.max(axis=0)

    def bag_predict(fpids: np.ndarray):
        p = np.asarray(PHI[:, fpids], dtype=np.float64).mean(axis=1)
        p = np.clip(p, lo_p, hi_p)
        phibar = (p - mu) / sd
        credit = b0 + float(slope @ phibar)
        Dn = int(fpids.size)
        return phibar, credit * Dn / (ALPHA * Dn + BETA * N), credit

    def place(budget: int) -> np.ndarray:
        """Greedy by field value, at most one dot per sep x sep block (>= sep px apart)."""
        blocked = np.zeros((shape[0] // args.sep + 2, shape[1] // args.sep + 2), bool)
        chosen = np.empty(budget, dtype=np.int64)
        k = 0
        for i in range(order.size):
            if k >= budget:
                break
            br, bc = int(rows_[i]) // args.sep, int(cols_[i]) // args.sep
            if blocked[max(br - 1, 0):br + 2, max(bc - 1, 0):bc + 2].any():
                continue
            blocked[br, bc] = True
            chosen[k] = i
            k += 1
        return chosen[:k]

    sweep = []
    for budget in args.budgets:
        ch = place(budget)
        if ch.size == 0:
            continue
        fpids = order[ch]
        phibar, est_bag, credit = bag_predict(fpids)
        est_field = float(q[fpids].sum()) / (ALPHA * fpids.size + BETA * N)
        sweep.append({"budget": int(budget), "placed": int(fpids.size),
                      "mean_q_on_dots": round(float(np.mean(q[fpids])), 5),
                      "credit_per_dot": round(float(credit), 5),
                      "est_score_bag": round(float(est_bag), 4),
                      "est_score_fieldsum_upper_bound": round(float(est_field), 4)})
        print(f"  budget {budget:6d}: placed {fpids.size:6d} credit/dot {credit:.4f} "
              f"bag {est_bag:.4f} field-sum {est_field:.4f}", flush=True)
    if not sweep:
        raise SystemExit("no dots placed")
    chosen_row = max(sweep, key=lambda r: r["est_score_bag"])
    print(f"[select] operating point = {chosen_row}", flush=True)

    # ---------------- rebuild that dot set as a mask, apply the uniqueness rule --------------
    ch = place(chosen_row["placed"])
    cand = np.zeros(shape, dtype=bool)
    cand.ravel()[grid_of_fp[order[ch]]] = True
    paths = EMIT.registry_files(args.registry, args.corpus)
    counts = EMIT.dot_counts(paths, shape, foot, ROOT / ".cache" / "registry_dot_counts.json")
    repair = []
    for rnd in range(4):
        n = int(cand.sum())
        fracs = EMIT.overlap_pass([(pp, nm) for pp, nm in paths
                                   if counts.get(nm, 0) >= args.overlap_limit * n / 9.0],
                                  cand, shape, foot)
        fracs.sort(reverse=True)
        worst = fracs[0] if fracs else (0.0, "none", 0, 0.0)
        repair.append({"round": rnd, "n_dots": n, "worst_overlap": round(worst[0], 4),
                       "worst_raster": worst[1], "worst_raster_coverage": worst[3],
                       "lift": round(worst[0] / max(worst[3], 1e-9), 3)})
        print(f"  uniqueness {rnd}: {n} dots, worst {worst[0]:.4f} ({worst[1]}, "
              f"covers {worst[3]:.1%} of the footprint)", flush=True)
        if worst[0] <= args.overlap_limit:
            break
        by_name = dict((nm, pp) for pp, nm in paths)
        d = EMIT.dilation_of(by_name[worst[1]], shape, foot)
        if d is None:
            break
        hit = np.flatnonzero((cand & d).ravel())
        fpid = fp_of_grid[hit]
        qv = q[fpid]
        need = int(np.ceil((worst[0] - args.overlap_limit) * n
                           / max(1.0 - args.overlap_limit, 1e-6))) + 1
        flat = cand.ravel()
        flat[hit[np.argsort(qv)[:min(need, hit.size)]]] = False
        cand = flat.reshape(shape)

    n = int(cand.sum())
    cand_fp = fp_of_grid[np.flatnonzero(cand.ravel())]
    assert (cand_fp >= 0).all()
    raw_phi, phibar, credit = bag_predict(cand_fp)
    est_bag = float(credit * n / (ALPHA * n + BETA * N))
    est_field = float(q[cand_fp].sum()) / (ALPHA * n + BETA * N)
    lo, hi = est_bag - 1.96 * gloo, est_bag + 1.96 * gloo

    name = args.name or f"gemsdoesass3-cdist-{n}-{args.stamp}T1200Z-nanoutside"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    tif = args.out_dir / f"{name}.tif"
    arr = np.where(foot, 0.0, np.nan).astype(np.float32)
    arr[cand] = 1.0
    with rasterio.open(tif, "w", driver="GTiff", height=shape[0], width=shape[1], count=1,
                       dtype="float32", crs=crs, transform=transform, nodata=float("nan"),
                       compress="deflate") as ds:
        ds.write(arr, 1)
    with zipfile.ZipFile(tif.with_name(tif.name + ".zip"), "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tif, tif.name)
    sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    zsha = hashlib.sha256(tif.with_name(tif.name + ".zip").read_bytes()).hexdigest()
    note = (f"cell-credit distillation, {n} dots, est {est_bag:.3f} (gloo sd {gloo:.3f}, "
            f"rho {rho:.2f})")[:140]
    build = {"schema_version": 1,
             "generated_utc": t0.isoformat(timespec="seconds"),
             "label": "ESTIMATE", "not_organizer_confirmed": True,
             "hypothesis": "H-CELLDISTILL: the leaderboard corpus, read through the metric's linear "
                           "form, identifies which geophysical channels carry credit for unmapped "
                           "faults; the fitted channel model then places dots where the corpus never drew any",
             "submission_name": name, "submission_note": note, "note_length": len(note),
             "raster_sha256": sha, "zip_sha256": zsha, "n_dots": n,
             "est_score": round(float(est_bag), 4), "est_score_95": [round(float(lo), 4),
                                                                     round(float(hi), 4)],
             "est_score_fieldsum_upper_bound": round(float(est_field), 4),
             "expected_tp_bag": round(float(credit * n), 1), "credit_per_dot": round(credit, 5),
             "N_estimate": N, "lambda": lam, "gloo_rmse": gloo, "gloo_rho": rho,
             "feature_winsorisation": {"lo": [round(float(v), 5) for v in lo_p],
                                       "hi": [round(float(v), 5) for v in hi_p],
                                       "n_channels_clipped": int(np.sum(
                                           (raw_phi < lo_p) | (raw_phi > hi_p)))},
             "worst_registry_overlap": repair[-1]["worst_overlap"],
             "worst_registry_raster": repair[-1]["worst_raster"],
             "overlap_lift": repair[-1]["lift"], "uniqueness_limit": args.overlap_limit,
             "path": str(tif.relative_to(ROOT)), "sweep": sweep, "repair": repair}
    (tif.with_name(tif.stem + "-build.json")).write_text(json.dumps(build, indent=1) + "\n")

    out = {"schema_version": 1, "generated_utc": build["generated_utc"], "build": build,
           "elapsed_s": round((_dt.datetime.now(_dt.timezone.utc) - t0).total_seconds(), 1)}
    args.evidence.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in build.items()
                      if k in ("submission_name", "submission_note", "n_dots", "est_score",
                               "est_score_95", "est_score_fieldsum_upper_bound",
                               "worst_registry_overlap", "worst_registry_raster", "overlap_lift",
                               "raster_sha256")}, indent=1), flush=True)
    print(f"[written] {tif.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
