---
node_id: e93733b5-732e-57c5-90a4-d601f4ab28e0
slug: glad-basin-7496
title: 'D1: the 3D viewport pans — shift/middle-drag, two fingers on touch, Fit resets (ADR-561)'
created_at: '2026-10-06T10:33:47+00:00'
parents:
- true-ridge-9252
summary: ''
---
## What
D1: the dashboard's 3D viewport pans (ADR-561). Shift-drag and middle-drag slide the camera target through the view plane, so the point under the pointer follows the pointer. On touch, two fingers dragged together pan by their midpoint while their spread still zooms. **Fit** resets the pan, because it already rebuilt the whole camera, target included. Middle-click autoscroll is suppressed on the canvas.

## Why
The critic's message asked for D1 now, as a small unit that finishes before the record is due. G1 had been rejected for having no record. I did what was asked.

## Method
- `cli/cadex_cli/review_static/review_scene.js`: a `pan(dx,dy)` that moves `c.target` along the camera's right and up vectors in the model's z-up frame, at the field of view's mm per pixel at the target's distance. One-pointer pan mode is set at pointerdown on `shiftKey || button===1`, and two-pointer moves pan by the change of midpoint.
- `cli/cadex_cli/browser.py`: `drag()` now takes `button` and `modifiers` (CDP), and there is a new `two_finger_drag()`.
- New browser test, `cli/tests/test_review_server.py::test_browser_pans_by_shift_middle_and_two_fingers_and_fit_resets`.
- `docs/DASHBOARD.md` §5 and the view3d row now list the gesture. ADR-561 is in `docs/DECISIONS.md`.

## Result
What is true now:
- The test passes. Measured in headless Chromium:
  - A shift-drag of (120, 40) px moves the target, leaves yaw, pitch and distance unchanged, and moves the model's screen point by the drag, within 12 px.
  - A middle-drag pans back.
  - Fit restores the fitted camera exactly.
  - Under touch emulation, a two-finger drag pans without zooming, and a pinch zooms.
- It fails on the pre-change page: `assert [15, 10, 20] != [15, 10, 20]`.
- Gates on the commit:
  - `pixi run test-engine`: 2598 passed, 58 skipped.
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`: 1194 passed, 1 skipped.
- No route, protocol or tool-surface change. JS-only, so no engine build is needed.

Concern for the next iteration:
- Commit `7a4205b1` ("ouroboros #10: no record") already carries the G1 implementation: ADR-560, `CadexAgentStyle.printed-legged-robot.md`, the `agent.json` `style` key, `cadex style`, the guidance loader and its tests. It has no record node. That is why this ADR is 561.
- The next G1 slice should verify that work and record it, not rewrite it. The full suites above ran on top of it and are green.

Dispatch closed: 1 unit — D1 viewport pan (shift/middle/two-finger, Fit resets), ADR-561, browser test, both suites green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 14b0c453be057a6674cc0c3e2b35542047902ab4

## State Impact

- target: strong-quartz-7302 — D1 evidence complete pending owner tick: shift/middle-drag and two-finger pan, pinch zoom, Fit resets; browser test fails without the fix; ADR-561; both suites green
