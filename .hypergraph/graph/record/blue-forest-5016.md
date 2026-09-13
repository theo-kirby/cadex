---
node_id: eb8f5209-c868-55b9-85b7-44b3fe32a4e1
slug: blue-forest-5016
title: Distinguish current video availability from recorded render outcome
created_at: '2026-09-13T05:13:46+00:00'
parents:
- fresh-timber-6139
summary: ''
artifacts:
- docs/probes/wren-fresh/video76-evidence.json
- docs/probes/wren-fresh/video_recovery.py
---
## What

Fixed the dashboard video list to lead with current file availability and a retained/recorded count, separately from the labelled recorded render outcome (ADR-310). Added browser regressions for missing, truncated, restored and mixed video collections and historical playback/download. Updated CLI documentation, the Wren recovery probe, lifecycle report and published operator status.

## Why

Advances D8 at cool-gate-3332 and preserves D10 at deep-clover-6012, following fresh-timber-6139 and the critic's exact request. The saved render receipt accurately said ready even after files disappeared, but leading with that outcome implied playable output. This unit fixes the exposed product ambiguity without changing authoritative run records or accepted geometry. No deviation from the critic's request.

## Method

Use the reader's existing resolved file checks for the headline: available, unavailable, or partly available. Keep the stored receipt separately labelled Recorded video render. The existing video identity key preserves playback on unchanged polls; restored bytes change availability on automatic polling.

Browser regression uses an independently rendered fixture, removes its video, truncates it to 64 bytes, restores its bytes after each fault, and checks the first list item, receipt, retry guidance, absent broken player/download, recovered download digest and one navigation. During each fault a retained historical run plays, downloads with the correct digest and keeps the same playing element across refresh. A second missing recording verifies the mixed collection count. Initial targeted invocation had a fixture helper argument collision (run used as both positional path and keyword); fixed the fixture record directly. The final targeted invocation passed both selected browser tests in 15.85 s.

Real artifacts: ran `PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python docs/probes/wren-fresh/video_recovery.py "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" "$HOME/cadex-projects/ot5-wren-video76"`. Its disposable full copy tests missing/partial/failed output, explicit unavailable headlines and unchanged recorded outcomes, restored playback, and historical wren66-final playback/download. The persistent URL is read before and after and its available headline is asserted. Compact receipt: docs/probes/wren-fresh/video76-evidence.json; raw receipt, screenshots and suite logs are outside git under cadex-projects/ot5-wren-video76.

## Result

The misleading ready headline is removed. Missing and truncated Wren output now leads with Video files: unavailable (0/1 retained), while the saved ready receipt remains explicitly historical. Recovery and historical playback/download pass. Persistent private port 8765 still serves ot5-wren-copy54 / wren71-final at revision e9dee22bc90c428942562eeadf150ef4bcd4ab03d8e9ed96e0f959272cfa22bb; the current video download matches a2fde70a223941d18096dc08d3559ab2cae8e0b834ad3b2cc6920487074bdcc5. All 3,769 source files are unchanged. The service stays active; no training, working-project switch or restart. Fresh page loads receive the edited static JS directly from the existing service. Same-machine private-address evidence only; no second-device claim. No dependency, protocol, payload, engine or shell change and no build required.

Verification against the final edited product/test/document tree: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests` passed 421, skipped 1 in 411.84 s. `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine` passed 2,110, skipped 53 in 260.78 s. No failures. `git diff --check` passes. The unreconciled tail gains this one record; no state nodes or generated views were edited.

Dispatch closed: 1 unit — distinguish current video availability from recorded render outcome with browser recovery and persistent Wren verification.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: cc8e9d2b615e0bdec6574dee72933d5af3f613fa

## State Impact

- target: cool-gate-3332 — Video lists now lead with verified current availability and counts separately from recorded render outcomes; browser regressions cover missing, truncated, restored and mixed files with historical playback preserved. Full CLI suite passes 421 tests.
- target: deep-clover-6012 — Persistent Wren operator URL verified with available current video, unchanged project and run identity and hash-checked playback/download; service remains active and all 3769 source files unchanged.
