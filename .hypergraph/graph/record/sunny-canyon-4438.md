---
node_id: 5271a829-8693-5b3d-bf77-a54f3a0e8e90
slug: sunny-canyon-4438
title: Prove Wren saved-project reopen and persistent dashboard restart
created_at: '2026-09-13T04:11:03+00:00'
parents:
- red-jasper-1884
summary: ''
artifacts:
- docs/probes/wren-fresh/RESTART.md
- docs/probes/wren-fresh/restart69-evidence.json
---
## What

Completed the current Wren working copy's D6 save/reopen and persistent dashboard restart proof using its retained real artifacts. Finished the uncommitted restart helper, browser regression and receipt guard found on arrival, reran the helper against the actual private port 8765, and added RESTART.md plus links in the Wren, operator-review and CLI documentation. No product behavior, dependency, training run or accepted design changed.

## Why

The critic explicitly selected this unit: prove the saved current Wren project survives engine reopen and a dashboard restart, checking identities, histories, curves and playable/downloadable videos through the persistent private URL. This follows red-jasper-1884's completed product-agent revision and retained videos. The initial dirty tree contained a partial attempt at exactly this task; I reviewed and completed it rather than discarding it. Assumption: headless save is the already-persisted accepted project and CLI-produced review artifacts, not a desktop save action. No new acceptance is necessary to test reopening those saved bytes.

## Method

Final real-project command (from checkout):

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/restart.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" \
  restart69-final > /tmp/restart69-final.json
```

Exit 0. Its compact stdout is committed as docs/probes/wren-fresh/restart69-evidence.json; full receipt and two screenshots remain project-local in evidence/restart69-final. The fresh-page screenshot was inspected. Earlier rerun evidence is retained in evidence/restart69-verified. The final helper includes bounded restart polling and emits its compact schema directly rather than requiring manual receipt transformation.

The helper hashes 2,004 files excluding its own evidence directory and git metadata, opens all 15 runs plus ACCEPTED NOW in headless Chromium, compares browser identities and all three histories with the API, and plays/downloads the current video. Two fresh cadexd processes (3255241 and 3255319) restore the served saved project in place. It asserts accepted revision/digest/contract/attempt unchanged, and all non-candidate files unchanged. It then restarts the existing cadex-operator-review user service while keeping that page open, checks automatic recovery, unchanged selection and the same playing video element, opens a new page, and compares all displayed views. API comparison also covers retained specs/decisions and run metadata. Fresh-page current and historical videos play and download with recorded SHA-256 hashes.

The fixture browser regression now checks fresh-visit selection and every recorded run's revision, digest, relation, outcome and video identities before/after restart. Its existing independent telemetry producer still checks no stop or duplication. The initial assertion expected RUN sample, but this fixture's recorded current run is second; targeted execution exposed that incorrect test assumption, which is corrected to RUN second. This was a test authoring failure, not a product defect.

## Result

The saved accepted identity is still revision de9692bd4ee57c387b17adf5ac10d67f0f7db5f76f2529f860a85d3121261e47, digest cd99e3be15558082959904398942bda2e7ee962ff1f39ee51f3658ea9bc9d46c. Restore preserves the accepted attempt and all of its bytes. Normal candidate rotation adds 42 files and prunes 42 while updating the manifest timestamp; no other file changes. Dashboard restart itself changes no project file.

The persistent service changed PID 3252132 to 3255404, answered after 1.05 seconds, and the open page showed stale at 0.13 seconds before recovering without navigation and keeping playback. All 16 model views loaded and compared equal. Fresh visits still select wren66-final, 90 mm feet, 240 points in each history. The current video digest is 802baa759c98e52ba1067cab1f39e28dc72d3fee7c82b073b285bffe0a82470a; historical checkpoint20 is 682f41bf1ce4846686fba681512f04e3defee83ec12e930e7dc546498016e533. Both retain their distinct model/policy identities and seed 0, eight simulation seconds, 8.1 encoded seconds. Old failed/stale histories remain distinct. Port 8765 stays serving ot5-wren-copy54 afterward; published operator status links the proof.

Limits: no trainer ran before or after the real check, so this adds no real-GPU restart-during-training claim. That concurrency check here is synthetic producer evidence. Same-machine private-address browser evidence only, no second device or desktop save claim. No new D11 similarity comparison, no new dependency. The unreconciled tail was two records on arrival; this work records a third without writing state or reconciling.

Verification: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine` passed 2,110 tests, 53 skipped in 262.03 s. `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests -q` completed 413 passed, one skipped, one failed in 399.58 s: its collected pre-fix RUN sample expectation was the sole failure. The corrected final-source focused run of test_review_lifecycle.py and test_wren_fresh_evidence.py passed all 14 tests in 15.09 s. This is not a claim that the original full-suite invocation was green. The failed case was rerun afterward via `pixi run python -m pytest cli/tests --lf -q` with the same thread limits. No build: only tests, probe and documentation changed, with no protocol/payload or shell edits. Logs are retained under the project's evidence/restart69-final directory. `git diff --check` passed.
The post-suite failed-case rerun passed: one passed, 13 deselected in 9.54 s. No unresolved failure remains from this unit.

Dispatch closed: 1 unit — Wren's retained saved project survives two engine reopens and a persistent-dashboard restart with all histories and playable/downloadable videos preserved

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 8ea091de830fd925e317a05346320d50c91ce926

## State Impact

- target: clever-field-7845 — Current Wren copy D6 retained-artifact proof passes: two in-place engine restores preserve accepted identity and bytes; persistent-service restart preserves all 15 browser run views, curves and current/historical video downloads; no real trainer active during this check
- target: deep-clover-6012 — Port 8765 remains on ot5-wren-copy54 with wren66-final default after measured restart; open playing page recovers without navigation, fresh visits retain the current identity, operator status updated
