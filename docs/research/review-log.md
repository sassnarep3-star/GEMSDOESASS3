# Three implementation / review passes

All checks are local unless an external source is explicitly named. No competition upload was attempted.

## Pass 1 — scientific implementation and negative decision

- Recorded four hypotheses and fixed H1 before building the surface. Restored the pinned shared template and owner mirror, then evaluated H1 and the controls on component-buffered quadrant folds using the shared pooled evaluator.
- Measured the historical nine-file supports and H33/H27 lineage. Checked one registered pre-placement witness. The literal 100% surface overlap required stopping before dots; no candidate TIFF or slot was created.
- Review finding: the initial canary covered all derived features but not the two raw bands individually. Do not claim this was a complete pre-score raw-input check.

## Pass 2 — independent verification and corrections

- Tested raw RTP and detrended elevation individually after the stop, without tuning or emitting dots. Rechecked AUC in either direction. The largest raw direction-free AUC was 0.566527 and the largest derived direction-free AUC was 0.617677. The negative decision remained unchanged.
- Reconstructed the exact recorded surface hash in a verification-only process. An independent Euclidean distance transform confirmed that all 4,942,792 positive surface cells are within three pixels of the witness. A separate coverage check found that witness does **not** cover every allowed footprint cell, so no universal impossibility is claimed.
- Added a finite-sentinel/overflow guard and made future runs test raw as well as derived bands. Recorded actual cached-band extrema, which prove the new guard does not change the tested data. The original run card preserves when each check occurred.
- Identified an incorrect inequality in the shared metric's *prose*. A synthetic regression test demonstrates it without changing the shared implementation. Upstream push and an attempted issue filing were denied; the scorer used here was verified against an independent calculation.

## Pass 3 — product, reproducibility and safety review

- Built the static, responsive dashboard and the executive-summary/submission guide; verified that all nine names match the pinned audit. An initial draft misnamed several historical methods; those labels were corrected against the manifest before publication.
- Corrected the historical audit so an overlap pass cannot accidentally be interpreted as a full uniqueness pass when rank correlation was not checked. Added hash checks to its mirror inputs. Reproductions now write separate timestamped receipts instead of overwriting published evidence.
- Ran **19 Python tests** and the JavaScript DOM/fallback test. These cover the official-formula DTI against a brute-force toy implementation, whole-component withholding, exact visible masking, paired bootstrap bookkeeping, literal three-pixel overlap, incomplete-registry failure, synthetic full-grid writer roundtrip and invalid-value rejection, published evidence consistency, site links and the disabled download. Rasterio emitted two upstream pending-deprecation warnings; there were no test failures.
- Exercised both pages in headless Chromium at 1440 px and 390 px: HTTP 200, nine rows, no page errors, disabled download, and no document-level horizontal overflow. The comparison table is separately scrollable on small screens. A WCAG 2 A/AA and 2.1 A/AA axe scan reported **zero automated violations** after color-contrast and accessible-name corrections; an automated scan is not a full accessibility certification.
- Headless sandbox TLS could not authenticate the public GitHub API, and the interface correctly displayed “Feed unavailable”; the successful metadata rendering and offline behavior were also tested with deterministic mocks. The GitHub feed is repository activity only, not an organizer-score feed. DrivenData is never scraped by the site.
- Other review PRs were merged concurrently. Their initial review documents and negative review card are preserved as historical snapshots and visibly marked as superseded; this README and current dashboard describe the later H1 work. Those reviewers did not select an unassigned lane; H1 was provisional, not coordinator-assigned, and future parallel work should obtain an explicit assignment.
- Rechecked the official outside-bounds null/NaN language against the shared writer's all-finite zero exterior. The apparent conflict must be resolved against an authenticated sample and upstream template before any release; local writer tests are not a compliance verdict.
- Remaining blockers include organizer data/receipt provenance, full registry and prior-best coverage, shared-template write access, and current quota/selector approval. None was relaxed for publication.
