---
node_id: 11f2d1fd-2241-52f3-8bb5-32e6e4283f54
slug: easy-badger-5812
title: 'Record iterations 104 and 106 (ADR-324): browser recovery on the real Lark video, server-side interruption on the synthetic one, CLI suite green'
created_at: '2026-09-13T13:08:07+00:00'
parents:
- fierce-bloom-1023
summary: ''
artifacts:
- docs/probes/lark-fresh/download104-evidence.json
- docs/probes/lark-fresh/download106-evidence.json
---
## What

The missing causal record and handoff for iterations 104 and 106 (ADR-324, commits `1f823ca6` and `64fc3388`), both of which landed with "no record". It reports the required CLI-suite result those iterations never reported, verifies the persistent Lark dashboard's identity, and separates the two kinds of evidence ADR-324 rests on: browser-side recovery on the real Lark video, and server-side mid-transfer interruption on a synthetic 48 MiB video. It also leaves the handoff the critic asked for, with one new bet on a different criterion.

## Why

Criterion D4 (recording/review reliability) and D10 (the persistent operator dashboard), under the charter's maintenance rung. The critic's message named two fixes first: iteration 106 has no causal record, and its required CLI-suite results were never reported. Iteration 104 has the same hole, so this record covers both units of ADR-324 work. The critic then asked for a reconcile; this dispatch forbids the reconcile skill, `hypergraph update`, state edits and STATE.md edits in a work iteration, so this record is the contributor half only: with `red-shade-9740` and `fierce-bloom-1023` it makes three unreconciled records, which is the charter's threshold for the next iteration to be the reconcile pass. That is the deviation: recorded, not reconciled.

No code, test or probe was added in this iteration. The quality bar reserves bookkeeping for reconcile passes, but the critic's fix-first instruction was explicit, iteration 105 already burned one turn producing nothing, and adding an unrequested maintenance task on top would have been exactly what the critic warned against. The unit is therefore: verification that was owed, plus the record that was owed.

The bet the critic banned is the interrupted-download thread (ADR-323/324 downloads on D4). The new bet is on D6 and is written in `## Result`.

## Method

Read the two unrecorded commits, their ADR text, receipts (`docs/probes/lark-fresh/download104-evidence.json`, `download106-evidence.json`) and the regressions they added. Ran the required suite for the `cli/` zone at the current head: `pixi run python -m pytest cli/tests -q` — 470 passed, 1 skipped in 472.45 s, exit 0 (the 104 and 106 regressions are included in that count). `git status` was clean before and after; no engine, payload or shell change was made in 104, 106 or here, so those gates were not run.

Verified the persistent server without restarting it: PID 325201 is `python -m cadex_cli review --project ~/cadex-projects/ot5-lark-copy85 --host <private IP> --port 8765`, listening on the Tailscale address only; `GET /api/project` answers project `ot5-lark-copy85`, accepted digest `c039961cd41d…`, 13 runs, and `default_run()` applied to that response — the server's own fresh-visit rule — returns `lark98-final` (status `ok`, no trainer active). This is an HTTP check on the same machine, not a browser and not a second device; the browser receipts are 104's and 106's.

What ADR-324 established, kept apart:

- **Server-side, synthetic.** A 48 MiB retained video and a client that resets the socket after the response head reproduced the defect on the pre-fix code: a twenty-line socketserver traceback per cancellation with the request already logged as a completed 200. After the fix, `_send_file` logs one line naming bytes sent of bytes owed, the whole file downloads byte-identical afterwards and a byte-range request answers 206 (`test_an_interrupted_download_is_one_log_line_not_a_traceback`). Iteration 106 added the same interruption originated by Chromium: network throttled, `Browser.cancelDownload` while the server still has bytes to write, one log line, no traceback, fresh download byte-identical (`test_browser_cancelled_download_is_logged_once_and_the_next_download_completes`); 104's Chromium regression keeps the page polling through the interruption (`test_browser_interrupted_download_leaves_polling_and_a_fresh_download_working`).
- **Browser-side, real video.** On the persistent Lark dashboard the real `lark98-final` video is 14,003 bytes and is written whole before any cancel can reach the server, so it cannot exercise the server's mid-transfer path. What it does establish: with the page throttled to 1,024 B/s the browser cancelled at 1,500 of 14,003 bytes; the page polled once before and three times after with freshness `live`; the playing video kept playing through the cancel and the fresh download; the fresh download was hash-equal to the retained file (`6c0bf873dc95…`) with no partial file left; the server log gained no line and no traceback. Identity, 81 differing decoded frames, historical `lark98-checkpoint20` selection and the route back to current passed in the same session. Both receipts are pinned by `test_download104_receipt_…` and `test_download106_receipt_…` in `cli/tests/test_lark_fresh_evidence.py`.

## Result

True now: ADR-324 is on the persistent server (restarted onto it in 104; 106 did not restart), the server keeps serving `ot5-lark-copy85` with `lark98-final` as the fresh-visit default, and the `cli/` suite at head is green (470 passed, 1 skipped, exit 0). Iterations 104 and 106 are now recorded; the unreconciled tail is three records and the next iteration is the reconcile pass by the charter's own rule. No training ran, no project was mutated, no dependency, engine, payload or shell change.

Honest limit: the real-video receipt proves browser recovery, not server-side interruption; the server-side case rests on the synthetic 48 MiB regressions only, because no retained Lark video is large enough to be mid-transfer when a cancel arrives. That is a property of the fixture size, not a gap in the fix.

Handoff for the next model. What has been tried since the Lark lifecycle report closed (iterations 96–106): dashboard restart during real training (D6), encoder-failure isolation during real training (D4/D8), bounded run-list poll and disk accounting (D3/D10), Unicode download names and interrupted downloads (D4). Every D1–D11 node is `working` with Lark evidence; the frontier's checkboxes are owner-owned, so the "55 iterations without movement" streak is structural, and the critic is right that more download-path maintenance will not change it. What I would try next, one bet, different criterion: **D6, engine restart during active training** — the one D6 gap the state node names as undemonstrated. Start one bounded Lark GPU run on the working copy (≤ 240 updates, `MemoryMax=20G`, explicit timeout), restart the per-project `cadexd` (not the trainer, not the dashboard) mid-run through the public CLI, and prove on the persistent URL that accepted identity, specs, curves, the trainer PID and telemetry continuity survive, with a browser receipt and a reusable probe beside `docs/probes/lark-fresh/restart_training.py`. If that also cannot move a checkbox, the honest next step is to write, in the Lark README, a one-paragraph owner-facing acceptance request per criterion listing the exact receipt to tick, since only the owner can move this frontier. Criteria that look blocked on evidence this machine cannot produce: D1, D6, D7, D11 each carry a "no second-device test" limit; no second device is available here, and no claim of one should be made.

Dispatch closed: 1 unit — record iterations 104 and 106 (ADR-324) with the owed CLI-suite result, verified persistent Lark identity, and a D6 handoff bet.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 958eb64595e2b098c97f1719d181c16469105eb3

## State Impact

- target: candid-harvest-2614 — D4 maintenance (ADR-324, iterations 104/106): a client that cancels a video download mid-transfer costs one log line, no traceback, and the next whole or byte-range request serves the file. Server-side mid-transfer interruption is pinned by raw-socket and browser-cancel regressions on a synthetic 48 MiB video; the real 14 KB lark98-final video establishes browser-side recovery only (cancel at 1,500 of 14,003 bytes, polling and playback continue, fresh download hash-equal). cli/ suite at head: 470 passed, 1 skipped, exit 0.
- target: chilly-union-8972 — ADR-324: review_server's _send_file and do_GET treat BrokenPipeError and ConnectionResetError as the client's decision (one log line naming bytes sent of bytes owed); regressions cover raw-socket reset, browser cancel, 206 resume and page polling through the interruption. cli/ suite 470 passed, 1 skipped.
- target: deep-clover-6012 — Persistent port 8765 still serves ot5-lark-copy85 on the ADR-324 server (restarted in 104, not since); a fresh visit selects lark98-final with no trainer active, verified over HTTP with the server's own default_run rule in iteration 107 and by browser receipts in 104 and 106. No working-project switch, no training.
- target: crisp-sun-1239 — Iterations 104 and 106 are now recorded; the unreconciled tail is three records, so the next iteration is the reconcile pass. Handoff bet on a different criterion: D6 engine restart during active training, the one D6 gap still undemonstrated. Remaining same-machine-only limits on D1/D6/D7/D11 are stated, not claimed.
