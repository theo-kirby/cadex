---
node_id: d254fd81-3ccf-5d5b-9612-63f23c43dabb
slug: loyal-canyon-2866
title: Preserve deliberate historical playback when a new failed attempt arrives
created_at: '2026-09-13T05:24:28+00:00'
parents:
- blue-forest-5016
summary: ''
artifacts:
- docs/probes/wren-fresh/current77-evidence.json
---
## What

Added a D10 browser regression for publishing a new failed attempt while an existing page deliberately plays a historical video. Updated the published operator status and retained a compact private-address browser receipt.

## Why

Advances deep-clover-6012 (D10) following blue-forest-5016 and the critic's requested coverage. Existing tests relabelled an already-listed run during playback or published a current video; this test publishes a distinct new failed run after deliberate historical selection and observes automatic polling. No deviation from the requested work. Reconcile is explicitly forbidden by this dispatch, even though the tail reaches three records; it is left to a separately authorized pass.

## Method

`test_browser_historical_playback_survives_published_failed_attempt` renders a fixture video with the real renderer, opens the current successful run, deliberately selects the historical video, and starts muted looping playback. It creates a new run directory and failed record with a later timestamp. Waits for the current-run banner and counts two subsequent automatic project fetches without invoking refresh. Requires cumulative video time to advance, identical video element and revision, historical label, and a hash-matching download. A fresh browser page selects the new failed attempt with its own revision and no substituted video. Returning the old page to current selects that same failed attempt and revision without navigation.

Targeted command: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests/test_review_server.py -k historical_playback_survives_published -q` passed 1, deselected 41 in 8.92 s.

Persistent verification used `PYTHONPATH=cli:cli/tests:docs/probes/wren-fresh OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python` with HeadlessBrowser and the existing video_recovery.play helper, opening `http://$(tailscale ip -4):8765/`. Compared project/default identity with ot5-wren-copy54 / wren71-final, played and downloaded the current video against its project-local video.json, selected historical wren66-final and repeated, then returned to current. Receipt: docs/probes/wren-fresh/current77-evidence.json. The failed-attempt publication is synthetic fixture coverage; no failed Wren training is claimed in this iteration.

## Result

Historical playback survives a newly published failure with actual automatic polling; fresh and return-to-current selection agree on the new failed attempt. Persistent private port 8765 still serves ot5-wren-copy54 / wren71-final at revision e9dee22bc90c428942562eeadf150ef4bcd4ab03d8e9ed96e0f959272cfa22bb. Current and historical downloads match a2fde70a223941d18096dc08d3559ab2cae8e0b834ad3b2cc6920487074bdcc5 and 802baa759c98e52ba1067cab1f39e28dc72d3fee7c82b073b285bffe0a82470a. The persistent service stays running; no restart, training, working-project switch or project writes. Same-machine private-address evidence only. No new dependency, product behavior change, removal, protocol/payload change or build.

Full validation on the final test/document tree: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests` passed 422, skipped 1 in 422.69 s; `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine` passed 2110, skipped 53 in 261.47 s. No failures. `git diff --check` passes. The unreconciled tail now reaches three records; no state node or generated view was edited.

Dispatch closed: 1 unit — strengthen D10 coverage for new failed attempts during deliberate historical playback and verify the persistent Wren dashboard.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 4ff130a39b852f60a805678543542067fbe6bf7e

## State Impact

- target: deep-clover-6012 — D10 browser regression publishes a distinct failed attempt during deliberate historical playback; automatic polling preserves selection and advancing playback, while fresh and return-to-current views select the same failure. Persistent Wren current and historical playback/download verified; CLI 422 passed, engine 2110 passed.
