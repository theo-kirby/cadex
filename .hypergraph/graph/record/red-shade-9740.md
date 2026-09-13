---
node_id: 6e01994c-e59a-58f0-b297-27faa76a40d9
slug: red-shade-9740
title: Bound aggregate review disk traversal, expose partial sizes and preserve playback when detail arrives
created_at: '2026-09-13T11:55:40+00:00'
parents:
- civic-nest-8285
summary: ''
artifacts:
- docs/probes/lark-fresh/disk102-evidence.json
---
## What

Correct ADR-322 disk accounting: one lazy directory traversal allowance shared across the run and every directory reference, with partial reference and shared byte counts labelled as lower bounds in the API and browser. Keep the persistent Lark review server on the corrected reader.

## Why

Criterion D10: reliable current-run review on the persistent operator dashboard, within the charter's bounded-operation maintenance rung. Bet: fixing the demonstrated traversal and partial-size defects is the smallest useful D10 change; do this before another experiment. This follows the critic's specific instruction to fix iteration 100 first, not the stale PLAN clearance bet. The request to reconcile afterward conflicts with this dispatch's explicit prohibition on state writes/reconcile; record corrected impacts for the next authorized reconcile instead. In particular, chilly-union-8972 and crisp-sun-1239 must not use civic-nest-8285 alone as evidence of bounded disk accounting.

## Method

Replace eagerly sorted recursive scans with lazy iterative scandir consumption, stopping before requesting entries beyond the allowance. Pass a single budget through the run walk, artifact directories, project artifact directories, videos and retained project docs. Report aggregate entries_visited; reference status truncated and lower_bound; shared_lower_bound on partial shared sums. Preserve the run total's own status if it completed before references exhausted the budget. Show “at least” and “truncated” in reference cells and shared-reference rows, including zero-byte lower bounds.

Instrument actual scandir yields across a run and three directory references: a 12-entry allowance visits exactly 12 entries, fully counts the first reference (40 bytes), partially counts the second (15 bytes), and does not enumerate the third (0 bytes). The shared 55-byte sum is explicitly a lower bound. A headless browser regression checks the exhausted reference's “at least 0 B · truncated” cell and shared rows. The first full suite run exposed a related ADR-322 defect: a delayed disk detail changed the video rebuild key and detached an already-playing historical player. Instrumentation observed keptConnected=false, currentTime=0.014963 and a replacement paused player. Disk sizes now update text spans outside the media rebuild key. A browser regression blocks the detail response until playback starts, releases it, and asserts the same playing element acquires its size. Existing coverage checks permitted paths, hard links, complete sizes, missing/refused references and historical playback.

Commands: `pixi run python -m pytest cli/tests/test_review_disk_use.py -q`; `pixi run python -m pytest cli/tests -q`. Restarted only the existing review service with the documented `cadex review --project PROJECT --host PRIVATE_IP --port 8765` command. Headless Chromium via cli/tests/cdp_browser.py opened the private URL, compared current disk count against API, played the historical checkpoint through refresh, and returned to current. Retained compact receipt: docs/probes/lark-fresh/disk102-evidence.json; operator status: docs/probes/lark-fresh/README.md. No training active or started.

## Result

Final focused checks: 9 passed in 37.28s (all disk-use tests plus the previously failing video-availability test).
Final full CLI suite: 461 passed, 1 skipped in 462.47s (exit 0). The initial video failure is resolved; no known new broken tree.
Persistent private port 8765 still serves ot5-lark-copy85; a fresh visit selects lark98-final. Its count is 917305 bytes in 37 files, with 61 aggregate directory entries visited. Historical lark98-checkpoint20 playback survives refresh, the route back to current works, and restart preserved all run names. Receipt timestamp: 2026-09-13T11:47:41.699146+00:00. This is a headless browser on the server using the private address, not a second-device test. No new criterion is claimed wholly completed and no checkbox/state node was edited.

Handoff: iteration 100 tried independent capped walks but sorted entire directories first and silently presented truncated reference counts as complete; this unit corrects those defects with measured evidence. Next, an authorized reconcile should correct the two named state claims using this record rather than promote the rejected original evidence. Subsequent work should follow the D1-D11 lifecycle maintenance frontier, not the stale clearance bet. Limits: this bounds directory entries, not total request duration or direct-reference stat calls; reaching the limit exactly is conservatively a lower bound; scan order and therefore partial subsets follow filesystem enumeration. No dependency, engine, payload or shell change; no full build. The initial full suite was not green: 459 passed, 1 skipped, 1 failed in 454.90s, at test_video_availability_tracks_missing_partial_restored_and_history waiting for keptVideo.currentTime > 0.1. Two isolated retries reproduced it; one pre-change CLI baseline run passed. Diagnostic instrumentation established the detached player, and the final implementation fixes its disk-detail trigger rather than weakening the test.

Dispatch closed: 1 unit — bound aggregate disk traversal and label truncated reference sizes honestly on the persistent dashboard.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 17fbd09b46188cd4c66f424d7e768cbe316179d4

## State Impact

- target: chilly-union-8972 — Correct ADR-322 with a single lazy directory-entry budget across the run and every directory reference, explicit lower-bound reference/shared sizes, and disk-size updates that preserve playback; final CLI suite 461 passed, 1 skipped. civic-nest-8285 alone did not establish bounded accounting.
- target: crisp-sun-1239 — D10 maintenance correction verified on persistent Lark dashboard: bounded aggregate enumeration and honest partial sizes, plus no player replacement when disk detail arrives. Correct the prior bounded-operation claim using this evidence, not civic-nest-8285 alone.
- target: deep-clover-6012 — Persistent port 8765 remains on ot5-lark-copy85 with lark98-final current; corrected disk reader verified with 61 visited entries and historical checkpoint playback preserved through refresh. No working-project switch or new training in this unit.
