---
node_id: b0fa7e5e-3dde-5aa8-9cb5-4563a28eea4b
slug: fresh-timber-6139
title: Prove Wren missing and partial video recovery with retained historical playback
created_at: '2026-09-13T05:02:43+00:00'
parents:
- terse-walrus-5414
summary: ''
artifacts:
- docs/probes/wren-fresh/video75-evidence.json
- docs/probes/wren-fresh/video_recovery.py
- docs/probes/wren-fresh/LIFECYCLE.md
---
## What

Added and ran a reproducible headless-browser lifecycle probe against an isolated full copy of retained Wren artifacts. Updated Wren's lifecycle report, its evidence guard and the operator status with missing/partial/failed video evidence.

## Why

Advances D8 at cool-gate-3332 and preserves D10 at deep-clover-6012, following the critic's explicit Wren-only evidence request after the scheduled reconcile. No training or visual audit was repeated. The current charter reload is recorded in ot5 loop.log before iteration 38 (ce445e64a458); this work follows that inspection-only charter. The owner retains acceptance of D1–D11.

## Method

Ran `PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/video_recovery.py "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" "$HOME/cadex-projects/ot5-wren-video75-final"`. It inventories the entire source, copies it into a temporary sibling beneath cadex-projects, asserts full-copy equality and starts an isolated private-address server on an allocated port. The persistent operator server is only read.

On wren71-final, remove the retained video, replace it with its first 64 bytes, then inject an explicit failed-encoder receipt while those partial bytes remain. Observe automatic polling, unavailable player/download, 404 media endpoint and actionable CLI guidance. For each fault, select wren66-final and actually play/download its retained video, preserving playback through two polls, then return to the broken current run. Restore both original files and assert the full copied inventory matches. Finally play/download current wren71-final on the persistent URL and check the original inventory.

Compact receipt: docs/probes/wren-fresh/video75-evidence.json. Raw screenshots and receipt stay outside git in cadex-projects/ot5-wren-video75-final. The probe cleans up only its disposable server/copy, not its output evidence or the original project. Two early invocations passed the copy checks but timed out at background operator-tab playback (the first attempted harness edit used an unavailable `python` command, leaving the second invocation unchanged). Bringing the tab forward with CDP fixed the probe; the complete final invocation passed.

## Result

Three fault states passed: explicit missing, digest mismatch and failed-encoder labels, CLI recovery guidance, no video/download link, HTTP 404. wren66-final remained playable and hash-correct during each fault; restored wren71-final recovered in the same page. All 3,769 original files and the restored copy inventory matched. Persistent port 8765 remained on ot5-wren-copy54 / wren71-final, revision e9dee22bc90c428942562eeadf150ef4bcd4ab03d8e9ed96e0f959272cfa22bb, policy fa7b28b8732a6a5d7b86f3157ecfa81ab531d374c5c53a38415edde0da71b343, video a2fde70a223941d18096dc08d3559ab2cae8e0b834ad3b2cc6920487074bdcc5. The Wren-only missing/partial gap is closed by actual browser evidence, not shared Reed evidence.

Controlled artifact fault injection is not a new real encoder failure or real training interruption; those earlier experiments retain their own evidence. Same-machine private-address browser only, no second-device claim. No product behavior, dependency, engine, shell or payload change; no build required. No state nodes or generated views edited.

Verification: the real browser probe passed; fresh `pixi run python -m pytest cli/tests/test_wren_lifecycle_report.py` passed 4 tests. `setsid env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine` passed 2,110, skipped 53 in 262.12 s. `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests` collected before the report edits and finished 418 passed, 1 skipped, 1 failed in 403.95 s: its in-memory old report guard still asserted that Wren fault injection had NOT been repeated. The updated module passes all four checks in a fresh process. No full-suite rerun after that edit; report this limit rather than claiming a green full CLI run. Both suite logs and the fresh guard log are retained beside the external receipt. No demonstrated product regression remains.

Dispatch closed: 1 unit — prove Wren missing/partial/failed video recovery and retained playback without changing the persistent project.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 7fb368ffe8210183ddb64df8b5938ee3e3dad18e

## State Impact

- target: cool-gate-3332 — Wren-specific browser fault injection now proves missing, partial and failed video states, CLI recovery guidance, historical playback/download during faults and restored output recovery on an isolated full copy; all 3769 original files unchanged.
- target: deep-clover-6012 — Persistent port 8765 verified before and after Wren video faults, still serving ot5-wren-copy54 and wren71-final with hash-checked playback/download; no restart or training.
- target: silent-river-6649 — Wren lifecycle report now links its own missing/partial/failed video receipt and reproducible browser probe, closing the stated Wren-only D8 evidence gap.
