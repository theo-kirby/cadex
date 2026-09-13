---
node_id: 4c6cf1ba-efca-5a95-9aaa-9e707fbe5aaf
slug: sweet-anchor-6246
title: Prove Wren encoder failure and recovery during real GPU training
created_at: '2026-09-13T05:52:24+00:00'
parents:
- loyal-canyon-2866
summary: ''
artifacts:
- docs/probes/wren-fresh/render79-evidence.json
- docs/probes/wren-fresh/RENDER-FAILURE.md
---
## What

Exercised real encoder failure and recovery during bounded Wren GPU training on the persistent private-network dashboard. Delivered the reproducible browser fault probe, compact receipt and user-facing report; updated the published operator status and lifecycle evidence index.

## Why

Advances candid-harvest-2614 (D4) and deep-clover-6012 (D10), following loyal-canyon-2866 and the critic's request for actual render-failure isolation rather than missing-file injection. The planned unit was one experiment, including probe corrections and validation. This is a checkpoint re-render failure: an earlier verified recording remains available while the latest rendering outcome fails.

The critic also requested resolving pending plan impacts before work. This dispatch explicitly forbids reconcile, hypergraph update, state/view edits and generated plan changes, with no exceptions. I did not fold the plan. The old clearance/section work is outside this charter and was not pursued. The pending small-wind-0172 short-plan correction is superseded by the explicit current-horizon impacts on this record, for the next authorized reconcile to fold without a separate planner. No charter checkbox or generated view was edited.

## Method

Commands and procedure are in docs/probes/wren-fresh/RENDER-FAILURE.md. `train.py PROJECT wren79 URL AUTHORED_BY` used the accepted product-agent-authored 90 mm Wren design, 240 iterations, 1024 environments, seed 0, checkpoint every 20, independent 1800-second timeout and systemd MemoryMax=20G. `render_failure.py PROJECT wren79 URL` waited for engine-verified checkpoint publication, then invoked the normal renderer with a temporary ffmpeg executable that exits 73, scoped only to that renderer's PATH. The renderer validated/placed the real rollout, captured frames, failed at encoding and wrote its own failed video.json. No telemetry, model, run outcome or video receipt was edited to manufacture the failure.

Two browser pages used the persistent private-network port 8765: active training followed automatic polling, and the checkpoint showed encoder failure plus CLI recovery guidance and its earlier retained video. The probe verified exact trainer PID/start-tick continuity, four distinct live browser updates, checkpoint and historical wren71-final playback/download, then retried with the real encoder and decoded/played/downloaded the verified output while training stayed active. The experiment independently finished training and verified/published the final-policy recording. Browser checks are same-machine private-address observations, not a second-device test.

Raw project-local receipts include evidence/wren79-checkpoint20-render-failure.json, the two earlier failed observer receipts, wren79-experiment-result.json, wren79-observe.json, checkpoint/final browser checks and prior-file inventory; large policies, rollouts and videos stay in the external project. docs/probes/wren-fresh/render79-evidence.json retains portable compact facts and artifact hashes.

## Result

Successful failure-isolation window: failed encoding took 4.056 s, starting at training update 74. The browser observed 78, 80, 82, 84 with reward/loss histories 79, 81, 83, 85 and no reload. The sole trainer remained PID 3559899/start tick 100682276 through the checked window; it reached update 85 after failure/history checks and 96 after verified recovery playback/download. The page explicitly said Recorded video render: failed / FFmpeg encoding failed with CLI retry guidance, separately from Video files: available (1/1 retained). Earlier checkpoint and wren71-final recordings remained playable/downloadable.

The recovered checkpoint and final recordings each fully decoded to 81 frames at 10 fps (8.1 encoded seconds for 8 simulation seconds, seed 0). Checkpoint policy fdf59bb967773ce39fae259855cd9e7292edc491ebff862eff09dbda97eb334f, playback revision a81937e7391b28c294a377819bf5d686589469a7d07eedbb5b87d1ee6e56bc4b, recovery video c981147c51b859f76fb536996a2f7516077e82e95fe83e6a86e86db77b2accdb. Final policy d170b78ab1a360c2e6e2e0f6529542841315f615a8b5d66b435898abccd767f2, playback revision 0d78fae96c2279e94b734225605b3fa6261c8e755794b9c1368fd639f747c0f7, video 9c74f4cba35f6ef350550052ab717435e429d162b93604efa213237a944cc9b8. Final witness error 8.71585e-08 is below 1e-04. The existing shared style and its digest remain recorded; no new reference comparison or gait claim.

Training exited 0 with 240 updates, state done, 718.999 s launch-to-exit wall time. Sampled cgroup host peak 7413522432 bytes stayed below the cap; whole-GPU sampled peak 15120 MiB includes tests/browser load. All 703 earlier run/asset files remained byte-identical. The persistent server stays on ot5-wren-copy54, now 21 runs, new visits selecting wren79-final; historical checkpoint selection and return-to-current passed. Service PID 3308131 remains active without restart.

Concern and correction: the first observer correctly caught a second trainer launched by a concurrently running CLI live test. This violated the one-trainer experiment boundary; it is not erased by the later pass. I stopped both suites and the CLI test process tree, confirmed only the original Wren trainer remained, and repeated within that same GPU run. The second observer saw 58,60,62,64 but failed an overly strict assertion that its initial sample must exceed the pre-render iteration; checkpoint publication can legitimately hold that sample steady. Corrected the probe to require three subsequent updates. Both excluded receipts remain retained; the successful window uses the corrected probe with no suite running. No product defect was demonstrated. Full suites were rerun sequentially after GPU training, as the new instructions require.

No new dependency, product/protocol/payload/shell change, full build or inherited-tree change. The no-python shell alias initially prevented an unused train.py edit; the experiment instead uses the standalone committed observer. No train.py change landed. This unit supplies real D4 failure/recovery evidence with the stated limits; it does not claim whole-charter completion.

Final sequential validation with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1: `pixi run python -m pytest cli/tests` passed 422, skipped 1 in 413.18 s; `pixi run test-engine` passed 2110, skipped 53 in 252.38 s. No failures in these completed runs. The initial interrupted overlapping suites are not passes. Python compile and git diff --check pass.

Dispatch closed: 1 unit — prove real Wren checkpoint encoder-failure isolation and verified recovery on the persistent dashboard, with disclosed probe errors and final policy publication.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: a7c445d7c8c50e6af4b040fe42ca46be9608f5c8

## State Impact

- target: candid-harvest-2614 — D4 real Wren checkpoint re-render encoder failure is visible with CLI guidance while unchanged trainer advances through browser updates 78,80,82,84; verified retry plays/downloads at update 96 and final video is retained after 240 updates. Initial test-trainer overlap and probe assertion failure are excluded and disclosed; full sequential CLI 422 and engine 2110 pass.
- target: deep-clover-6012 — Persistent private port 8765 stayed on ot5-wren-copy54 through wren79 training/failure/recovery/completion; fresh visits select active wren79 then wren79-final at revision 0d78fae96c2279e94b734225605b3fa6261c8e755794b9c1368fd639f747c0f7. All 703 older run/asset files preserved; server remains active without restart, now 21 runs.
- target: silent-river-6649 — Wren lifecycle report links real GPU encoder-failure and recovery receipt and now identifies current wren79-final; prior lifecycle and gait comparisons remain historical with no new gait claim.
- target: plan/young-crane-9546 — Supersede pending small-wind-0172 correction and retire clearance/section/scaffold work from this charter horizon. Wren D1-D11 evidence is assembled, including real render-failure recovery with disclosed overlap limits. Next work must maintain D10 and repeat lifecycle or fix a demonstrated recording/review defect under the exhaustion policy; reconcile only in an explicitly authorized dispatch.
- target: plan/strong-birch-7412 — Replace old non-charter horizon with bounded review-lifecycle maintenance: independently repeat project creation/revision/training/review, preserve portable history across restart/copy/failure, improve bounded telemetry and artifact retention based on demonstrated defects. No gait research or parked catalog work.
- target: plan/late-valley-7350 — Restrict long horizon to charter exhaustion policy: clean-project lifecycle repeats, bounded longer-history operation, browser/video/lifecycle regression closure and truthful documentation. Existing D1-D11 evidence does not authorize replacement shell/engine, clearance, catalog or gait research.
