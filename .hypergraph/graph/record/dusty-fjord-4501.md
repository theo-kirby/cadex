---
node_id: 78ebd270-f5a3-566a-b32c-40d762481831
slug: dusty-fjord-4501
title: 'Bound the dashboard run-list poll: telemetry summary per run, histories and verified checkpoints per selected run, keyed DOM rebuilds; restart the persistent Lark dashboard onto it'
created_at: '2026-09-13T11:09:08+00:00'
parents:
- quiet-pebble-5566
summary: ''
---
## What

Bounded the dashboard's run-list poll (ADR-321). `GET /api/project` used to attach every run's full telemetry — three histories of up to 512 samples and a checkpoint list whose every entry was sha256-hashed against its recorded digest — every two seconds, and the page rebuilt the whole sidebar on each poll. Now `training_telemetry(root, record, detail=False)` returns a summary (same validation and `state`, reason, latest metrics, `samples` counts, `checkpoints_reported`, `checkpoint_source`) with no histories and no checkpoint bytes read; the list serves that, and `GET /api/run/<name>` attaches the detail form for the one run requested. `review.js` polls the list then the selected run's detail, renders the telemetry panel from one response, shows a `pending` checkpoint line of the same DOM shape until the detail arrives, keys the sidebar and telemetry panel on what they show, and exposes `window.cadexReview.lastPoll()` (list bytes, detail bytes, wall time). New suite `cli/tests/test_review_history_scale.py`; two dashboard tests and the two Wren probe scripts that read history lengths from the list moved to the detail/`samples`. `docs/CLI.md` describes both forms and lists the suite; ADR-321 appended. The persistent operator service on port 8765 was restarted onto this server with no trainer active, verified over the private address in a headless browser, receipt `docs/probes/lark-fresh/scale99-evidence.json`, pinned by a new test in `test_lark_fresh_evidence.py`, and noted in `docs/probes/operator-review/README.md`.

## Why

The critic's message for this iteration: accept the Lark render-failure evidence with its bookkeeping failure qualified (done — ADR-320's receipt records it, nothing more was needed), and move to the exhaustion policy's bounded-operation rung — a headless-browser regression exercising a long run history and growing telemetry, proving bounded response size and browser work while preserving historical selection and playback, fixing any demonstrated defect in the same unit, keeping the persistent dashboard on the current Lark run, and not launching training or repeating lifecycle audits. This advances D10 (the persistent dashboard stays current and usable) and the long-term ladder rung "bounded telemetry, disk use and visible missing artifacts" under `crisp-sun-1239`. The previous short-term bet (clearance over rollout poses) is banned by the critic and was not taken. The defect the regression demonstrated before the fix: on the live Lark server the list poll was 554 KB for 13 runs and hashed 97 checkpoint files per poll, growing linearly with runs; at 60 runs ≈ 2.5 MB per two seconds. The critic's "growing telemetry" half was already bounded at the source (the trainer decimates each history to 512 points, `training/cadex_train.py:CURVE_POINTS_CAP`); the server refuses more than 512, so growth of one run's history is bounded, and the unbounded term was the run count, which is what this unit bounds.

## Method

1. Measured the persistent server before touching anything: `curl http://100.104.232.88:8765/api/project` → 554 KB in ~30 ms, 13 runs, telemetry ≈ 70 % of the bytes, 97 checkpoint entries hashed per request.
2. Server: threaded a `detail` flag through `training_telemetry`, with one `finish()` path so the early `missing`/`invalid` returns also summarise; the checkpoint verification loop runs only in detail mode; `ReviewProject.review()` asks for summaries; the `/api/run/<name>` route attaches the detail (not `ReviewProject.run()`, which the video range route calls per request and must not hash checkpoints).
3. Page: `loadDetail()` after each list poll and on selection, request-token guarded; `telemetryFor(run)` prefers a detail whose `run` matches; sidebar key `[selected, accepted revision, runs×(name, relation, status, recorded_at, revision)]`; telemetry key drops `age_s`; summary rendering shows sample counts with `loading history…`, a `#checkpoint-source[data-state=pending]` and a pending `#checkpoints li` — added after `test_browser_shows_checkpoint_provenance…` failed on a missing element during the pending window.
4. Regression: 63 runs (`_mesh_run` + 512-point `_telemetry` + 3 `_checkpoint`s each); HTTP asserts list < 12 KB/run, summary < 1.5 KB with no `curve`/`checkpoints`, detail carries 512 points and 3 `retained`, missing/invalid/mismatch states survive the summary, median list time < 2 s (measured 0.064 s); `default_run` reads the summary state. Browser: fresh visit opens the newest run with detail loaded; select `hist-007` (historical, FFmpeg-rendered video playing); MutationObserver counts nodes added by an idle `refresh()`; add 20 runs with the newest `running`+`training`; assert selection, relation and playback preserved, sidebar 84 entries, current-run names `grow-19`, idle-poll additions after ≤ before + 10 (measured 43 → 43); list bytes 367 KB → 483 KB, detail 75 KB; fresh visit selects `grow-19`; Current run button reaches it and its history grows 100 → 512 within 5 s; back to `hist-007` with its own 512 points and video.
5. Ran `cli/tests/test_review_server.py`, `test_review_lifecycle.py`, `test_review_record.py`, `test_video.py`, the new suite (91 passed, 1 skipped, then 15 targeted passed after the pending-shape fix), and the whole `cli/tests` (451 passed, 1 skipped, 7 m 19 s). The evidence test's list-size bound was loosened once (Lark's pretty-printed records are ~13 KB each) to a telemetry-share bound instead; 18 evidence tests pass.
6. Confirmed no trainer process, `systemctl --user restart cadex-operator-review.service` (new MainPID 117967, 07:00:08 EDT); list poll 170 KB in ~13 ms, detail for `lark98-final` 54 KB, 240 points, 12 retained checkpoints. Headless browser on `http://100.104.232.88:8765/`: ready in 0.75 s, `RUN lark98-final` (revision `6f826037…`, CURRENT, 8 components, detail loaded), video played through a poll and downloaded hash-equal; `lark1-final` opened HISTORICAL with its own revision and 240 points; idle poll added 62 nodes on either view; Current run button returned to `lark98-final`.

## Result

True now: the run list's cost is bounded per run (record bytes plus a < 1.5 KB telemetry summary) and reads no checkpoint bytes; histories and verified checkpoints are served one run per request; an idle poll rebuilds neither the sidebar nor the telemetry panel unless they changed. The persistent operator URL serves `ot5-lark-copy85` with `lark98-final` selected by default on the new server; historical browsing and playback verified after the restart. All CLI suites green; engine suites untouched (no change under `src/`).

Concerns and assumptions for the next iteration:
- The `telemetry` object in `/api/project` runs no longer carries `curve`, `loss_curve`, `episode_steps_curve` or `checkpoints`. Any script reading them from the list must use `/api/run/<name>` (or `samples`). I moved the two dashboard tests and the two Wren probes; `docs/probes/lark-fresh/*.py` did not read them. The old Wren receipts on disk are unchanged and still valid as history.
- The served list is still O(runs) in record bytes (~13 KB per Lark run, pretty-printed JSON). At several hundred runs that is a few MB per poll; the next bounded-operation step, if needed, is compact JSON or a paged list — not taken here because no project is near it.
- The evidence test bounds the list at 20 KB per run and telemetry at < 10 % of it; the fixture suite bounds 12 KB per run.
- No new dependency. No protocol op, payload or `shell/` change.
- Unreconciled tail is now 2 records (`quiet-pebble-5566` and this one); a reconcile is due after three.

Handoff for the next model: I tried the critic's bounded-operation unit directly — measure the live server, cut the list to summaries, prove it in a 60-run browser regression, restart and re-verify the persistent URL. Next I would take the remaining bounded-operation edges in order of measured cost: (a) the per-request `runs/` directory walk in `ReviewProject.run()` also re-reads the whole project review just to compute `relation` (one `read_accepted_identity` would do) — measure before changing; (b) disk-use visibility for retained videos/checkpoints per run in the artifacts panel; (c) if a project ever exceeds ~100 runs, compact JSON for the list. Do not restart a training run for receipts; D10's live requirement is satisfied by keeping the systemd service on the current Lark copy.

Dispatch closed: 1 unit — the dashboard's run-list poll is bounded (summary telemetry per run, detail per selected run, keyed DOM rebuilds), pinned by a 63-run browser regression, and the persistent Lark dashboard was restarted onto it and re-verified over the private address.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 550c7ce8cd21d988ab61037de4fbe2aaf13dee92

## State Impact

- target: deep-clover-6012 — Persistent port 8765 restarted (no trainer active) onto the ADR-321 server: the run list carries a bounded telemetry summary per run and reads no checkpoint bytes; a fresh private-address visit still selects lark98-final with its full detail, playing/hash-equal video and historical lark1-final browsing (scale99-evidence.json)
- target: dawn-delta-4361 — Telemetry histories and digest-verified checkpoints travel with /api/run/<name> for the selected run only; /api/project carries state, latest metrics, sample and checkpoint counts. Panel renders from one response with a pending checkpoint line until the detail arrives; growth of the current run's history still appears within five seconds while a historical run stays selected (test_review_history_scale.py)
- target: chilly-union-8972 — review_server.training_telemetry(detail=False) summary form (ADR-321); review.js polls list then detail, keys sidebar and telemetry rebuilds, exposes cadexReview.lastPoll(); a 63-run browser regression pins bounded list bytes and constant idle-poll DOM work (43 nodes before and after a 20-run growth)
