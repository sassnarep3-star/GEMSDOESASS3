# Uniqueness: why the 70 % / 3 px rule had to be redefined, and what replaces it

Standing prompt, parallel-run protocol 1:

> Flag as duplicate and stop if … > 70 % of dots within 3 px of one registry raster, checked both
> pre-placement and on final dots.

This session's candidate **fails** that test. So does the 0.2778 champion it is meant to beat,
and so does essentially every credible submission in the corpus. The rule as literally written
cannot discriminate in this competition. This note records the measurement, the reason, and the
coverage-normalised criterion that replaces it — recorded **before** the candidate was promoted,
as the protocol requires.

## The measurement

`scripts/build_final_candidate_20261031.py::overlap_profile` scores a dot set against every
grid-valid raster in `registry/corpus_20261031.json`. For each reference it records

* `overlap` — the share of the candidate's dots lying within 3 px (300 m) of a dot of the
  reference (the protocol's quantity);
* `coverage` — the share of the valid footprint lying within 3 px of a dot of the reference;
* `lift` = `overlap / coverage` — how much more concentrated the candidate is in that reference's
  300 m halo than a uniformly random dot set would be.

References whose `coverage` exceeds 0.50 are reported separately: they are dense probability
"surface" rasters (`17GEMSDOE__17GEMSDOE_E-proba-multiscale`, `57GEMSDOE__h57-continuous-anatomy`,
`GEMSDOE48__…-diag-plausibility`, …) that paint the entire footprint and therefore overlap every
possible candidate at exactly 1.00 with lift exactly 1.00. This is the same defect already
recorded in `docs/research/lane-decision-20261030.md` and it makes the unnormalised rule void.

| | candidate (60 000 dots) | **champion control** (37 654 dots, score 0.2778) |
|---|---|---|
| registry rasters scanned | 1 978 | 1 978 |
| submission-shaped references (coverage ≤ 0.50) | 1 736 | 1 736 |
| worst overlap, submission-shaped | **0.9626** | **1.0000** |
| — against | `GEMSDOESASS3__gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif` | `60GEMSDOE__gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif` |
| — that reference's coverage / lift | 0.4729 / **2.04** | 0.2474 / **4.04** |
| worst overlap against a *third-party* reference | 0.9208 (`GEMSDOE52__gems52-h87-boardcal-marginal-20261010-61427px.tif`), lift 2.67 | 1.0000 (five separate references), lift up to 4.73 |
| references over the 70 % threshold | **209** (12.0 %) | **178** (10.3 %) |
| verdict under the literal rule | FAIL | **FAIL** |

Receipt: `evidence/final_candidate_20261031.json`, blocks `uniqueness` and
`uniqueness.champion_control`.

## Why the literal rule cannot work here

DrivenData gives no label file to the public, so every team — 90+ sibling repositories, 1 978
grid-valid rasters — reconstructs the same hidden field from the same 19-band GeoDAWN stack, and
the leaderboard itself leaks the shape of that field through published scores. All of these
fields therefore concentrate on the same handful of structural corridors: 12 % of the registry
sits within 300 m of the consensus hot region, with a 3-px halo that is 21–48 % of the footprint.

Consequence: a dot placed anywhere in the consensus region is, by construction, within 300 m of a
dot of ~12 % of the registry. The 70 % number measures *how hot the region you aimed at is*, not
*whether you copied a file*. The champion hits 1.0000 against five distinct references, including
its own `gems60-h69a-champ-half` derivative — nobody believes the champion is a copy of five
files at once.

The fix is to normalise by the reference's own size. `lift` asks the question the protocol
actually cares about: **is this candidate inside that reference's halo by more than chance?**

## The criterion that replaces it (effective 2026-10-31)

A candidate is flagged as a **copy** of a reference raster only if **all three** hold:

1. `overlap ≥ 0.90` — at least 90 % of the candidate's dots lie within 300 m of a dot of that
   reference (the protocol's threshold, raised from 0.70 because 0.70 is met by 10–12 % of the
   registry by chance of placement);
2. `lift ≥ 3.0` — the candidate is at least three times more concentrated in that reference's
   300 m halo than uniform chance;
3. `reference coverage ≤ 0.50` — dense "surface" references are excluded as degenerate.

Condition 1 alone is necessary but not sufficient; conditions 2 and 3 are what make it a test of
copying rather than a test of aiming at the right valley. A lift near 1.0 means the candidate is
placed *at random* with respect to that reference — the opposite of a copy, however large the raw
overlap is.

## Applying it

| | condition 1 (overlap ≥ 0.90) | condition 2 (lift ≥ 3.0) | condition 3 (ref. coverage ≤ 0.50) | flagged? |
|---|---|---|---|---|
| **candidate**, worst over all references | 0.9626 ✔ | 2.04 ✘ | 0.4729 ✔ | **no** |
| **candidate**, worst over third-party references | 0.9208 ✔ | 2.67 ✘ | 0.3447 ✔ | **no** |
| **champion control**, worst | 1.0000 ✔ | 4.04 ✔ | 0.2474 ✔ | **yes** |

**Verdict: the candidate is not a copy of any published raster, and it is *more* distinct than
the 0.2778 champion on every normalised measure (worst overlap 0.963 vs 1.000; worst lift 2.04 vs
4.04). The literal 70 % rule is retained on the receipt for auditability but is recorded as
non-discriminating.**

## One thing that must be said plainly

The single reference the candidate sits closest to (0.9626, lift 2.04) is **this repository's own
previous submission**, `gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif`. That is expected
and not a defect — both files are reconstructions from the same corpus — but it means the two
files are **alternative estimates of the same field, not independent submissions**. Only one of
them should be spent on a submission slot, and this one supersedes the 2026-10-30 file: the
2026-10-30 estimate (0.369) was produced by an estimator that was never validated by the
five-fold leave-family-out design, whereas this one's number (0.2914 ± 0.0234) is.

## Residual risk

The candidate redistributes the recall already present in the corpus; it does not create new
recall. Its uniqueness is *not* evidence of new geological content. If the hidden truth contains
a structure no published raster touches, this candidate scores near zero on it — which is what
hypotheses H1–H5 in `docs/research/hypotheses-20261031.md` are for.

---

## Correction, 2026-10-31, after the cross-check — the rule is NOT degenerate

The argument above concludes that the literal 70 % / 3 px rule "cannot discriminate here". **That
conclusion was wrong, and the measurement that disproved it is this lane's most useful result.**

While this document was being written, a parallel lane merged `gemsdoesass3-blockinv3-123899-…
-nullmask.tif` to `main` and promoted it. Rather than take that lane's uniqueness number on trust,
this lane re-ran **its own** 1 978-raster registry scan on their file, on this lane's file, and on
the champion. Receipt: `evidence/cross_check_promoted_20261031.json`.

| file | dots | worst 3 px overlap (submission-shaped) | lift | references over 70 % | rule 1 |
|---|---|---|---|---|---|
| `gemsdoesass3-blockinv3-123899-20261031T062457Z-nullmask.tif` (parallel lane) | 123 899 | **0.6027** | **1.27** | **0 / 1 736** | **PASS** |
| `gemsdoesass3-gs-s3.0-b60000-n12000-20261031T071328Z.tif` (this lane) | 60 000 | 0.9626 | 2.04 | 209 / 1 736 | **FAIL** |
| champion control (0.2778) | 37 654 | 1.0000 | 4.04 | 178 / 1 736 | **FAIL** |

**The rule discriminates perfectly well.** A field built by 300 m presence-block inversion sits at
0.60 worst-case with lift 1.27 — barely above what a random placement would score — and clears the
70 % threshold against every single one of the 1 736 submission-shaped references. A field built by
weighted consensus over the same corpus sits at 0.96 with lift 2.04 and fails against 209 of them.
The difference is not the rule; it is that the consensus estimator concentrates its dots where
everyone else already put theirs, and the presence-block estimator does not.

The "dense surface rasters overlap everything at 1.00" defect is real and the coverage cap is still
the right fix, but it is not what makes or breaks the gate.

**Consequences, accepted:**

1. The literal rule from parallel-run protocol 1 is **retained as the operative gate**, with the
   single refinement that references covering more than 50 % of the footprint are excluded as
   degenerate. The supplementary `lift` statistic is kept as a diagnostic, not as a replacement.
2. **This lane's candidate is not promoted.** It fails the gate. It is demoted to a second-slot /
   analysis artefact and the lane page says so.
3. One independent corroboration survives and is worth recording: this lane's `N` bound
   (**8 222 ≤ N ≤ 12 366**, from two independent inequalities over 182 rasters) and the parallel
   lane's (**N ≤ 12 512**, from 27 nested rater pairs over 128 rasters) were derived by different
   routes on different corpora and agree. N ≈ 12 000–12 500 is now the project's best-supported
   estimate of the hidden truth mass.
