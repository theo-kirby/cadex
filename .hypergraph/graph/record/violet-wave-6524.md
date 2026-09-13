---
node_id: f0bc61a2-4f72-5707-9461-9bfcaa9529cc
slug: violet-wave-6524
title: Refresh accepted geometry with live review identity
created_at: '2026-09-13T02:52:32+00:00'
parents:
- calm-grove-2647
summary: ''
artifacts:
- docs/probes/wren-fresh/MODEL-REFRESH.md
- docs/probes/wren-fresh/model62-evidence.json
---
## What

Fixed the live accepted view updating revision/parameter labels while retaining old geometry (ADR-307). Polling now reloads the selected model when its revision or digest changes. Added two failing-then-passing Chromium regressions and documented the behavior and persistent Wren verification.

## Why

Follows calm-grove-2647 and advances D2/D10 (shy-meadow-0959, deep-clover-6012). The critic requested Wren's product-agent revision or, while capacity remained unavailable, one demonstrated lifecycle defect. Orientation recorded 22:38:53 local time before the retained provider refusal's 22:40 reset. No provider retry was made before the reset, and no refusal/preservation audit is counted as progress. Chose the concrete-defect fallback immediately rather than waiting on the clock. The reset passed during this unit; continuing the one chosen fix respects the one-unit dispatch. A subsequent iteration can attempt the product-agent revision once; elapsed reset time does not prove capacity. Wren's authorship gap remains unchanged.

## Method

Read the actor contract, graph protocol, vision and recording skill. Reproduced both existing-accepted and initially-empty cases in test_browser_accepted_geometry_tracks_live_identity: after publishing revision A, the visible identity was A while the loaded model stayed B or null. Both tests failed on the original source. Compare selected view/revision/digest across each project poll instead of comparing only the view name. Browser tests check the new 40 mm cube's 45 mm world X bound after placement, deliberately changed camera preservation on an unchanged poll, and the retained historical run's own revision.

Used the project-local evidence/model62/browser.py on the persistent private address and port 8765: default wren57-retry, current/accepted/historical document reading through 6.5 seconds of automatic polling each, and return-to-current. The project-local check_video.py fully decoded the existing retry recording, checked model parameters/components/curves, played across three polls and downloaded with the retained hash. Inspected its playback screenshot. No temporary server, service restart, acceptance edit, authoring turn or experiment training. Raw regression failures, probes, screenshots and gate logs stay project-local; compact evidence and user-facing report are committed.

## Result

The accepted viewport follows identity changes, including the first acceptance in an already-open empty view. Unchanged polling preserves camera and selected historical model identity. Persistent service still serves ot5-wren-copy54, default wren57-retry, revision 79f86c69bfc38dbf650f266446f256a72dd5547f3eaa386c7328ce85c81224fa; historical wren2-final remains 26332a5955e3a044b968e3ec14eec809d2090dfe10922c4f242c1a5a12bdc477. Retry video SHA-256 4d418967d41c1fe39b3ec2fa6945a0e8b5cf18343c4e3f5b1d0cf3dffbc3945e matches the download, with 81 decoded frames at 10 fps, 8.1 encoded seconds for eight simulation seconds. Eight components and 110 mm feet remain visible. Acceptance-transition evidence is fixture-based; persistent Wren checks are read-only and same-machine private-network, not a real new acceptance, second-device test or new D11 assessment. No new dependency, build, engine/protocol/payload/shell change, new training or gait claim. The contributor tail reaches three records; no reconciliation or state/view edit performed under this dispatch's prohibition.

Verification: OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests passed 403 tests, 1 skipped in 387.61 s; sequential pixi run test-engine under the same thread bounds passed 2110 tests, 53 skipped in 254.05 s. Both exit 0. The initial regression failed twice on old source in 2.81 s; the targeted fix passed twice in 3.66 s; the later strengthened camera check passed in the full suite. Service active and git diff --check pass. Hypergraph export/check runs before commit.

Dispatch closed: 1 unit — reload accepted geometry on live identity changes with browser regression and persistent Wren evidence.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 221718584777aa48c03cbedac92662dddf573627

## State Impact

- target: shy-meadow-0959 — Browser polling reloads geometry on selected revision or digest change, including first acceptance; two old-source failures and full-suite regressions verify bounds and camera preservation (ADR-307).
- target: deep-clover-6012 — Persistent ot5-wren-copy54 remains on wren57-retry; current accepted historical document and retry playback download checks pass after the refresh fix, service stays active.
