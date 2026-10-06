---
node_id: d812aa45-7348-58bd-8294-4d45b9de3d05
slug: strong-quartz-7302
title: D1. The 3D viewport pans
created_at: '2026-10-06T07:42:23+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun4: **D1. The 3D viewport pans.** Shift-drag and middle-drag pan; on touch a two-finger drag pans and a pinch zooms; **Fit** resets. The gesture is listed in `docs/DASHBOARD.md` and covered by a browser test through `cli/cadex_cli/browser.py`. The human owns the checkbox [rec: light-mist-9160].

**Evidence complete, pending the owner's tick** [rec: glad-basin-7496]. ADR-561. `review_scene.js` gains `pan(dx,dy)`: it moves the camera target through the view plane at the field of view's mm per pixel, so the point under the pointer follows the pointer. Shift-drag or middle-button drag pans. Two fingers pan by their midpoint, and their spread still zooms. Fit rebuilds the whole camera, which resets the pan. `browser.py` `drag()` now takes `button` and `modifiers`, and there is a new `two_finger_drag()`. Test: `test_review_server.py::test_browser_pans_by_shift_middle_and_two_fingers_and_fit_resets`. In headless Chromium, a shift-drag of (120, 40) px moves the model's screen point by the drag, within 12 px. Yaw, pitch and distance do not change. A middle-drag pans back, and Fit restores the fitted camera exactly. On touch, a two-finger drag pans without zooming, and a pinch zooms. The test fails on the pre-change page. Gates: test-engine 2598 passed, 58 skipped; cli/tests 1194 passed, 1 skipped. JS only: no route, protocol or tool-surface change. A later commit fixed the pan comment to cite ADR-561, not ADR-560 [rec: lucky-peak-7846].

Judgement (maintainer): status `working`, not closed, because the human owns the checkbox. This follows the convention of earlier dashboard criteria [rec: glad-basin-7496].

## Negative knowledge

None yet.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-d1-3d-viewport-pans-shift)
- glad-basin-7496 — D1 implemented and browser-tested; evidence complete pending owner tick
