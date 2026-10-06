---
node_id: c70c2b04-c57f-5acd-9d91-f07d059215f6
slug: staid-slope-4052
title: D2. Status is its own editor
created_at: '2026-10-06T07:42:23+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun4: **D2. Status is its own editor.** The stage overlay (ADR-542) becomes an editor, `data-editor="status"`, shown as **Status** beside the 3D and 2D viewports and placeable in any area. The default layout gives it its own area beside the 3D viewport on desktop and a tab on a phone; the 3D viewport keeps the checkpoint scrubber and revision timeline. All of ADR-542's content, its tests and the `docs/DASHBOARD.md` rows move with it. The human owns the checkbox [rec: light-mist-9160].

**Evidence complete, awaiting the owner's tick** (ADR-572, commit `adb94bb1`) [rec: neat-isle-1523]. Reconcile judgement: status `working`.

- `#editor-status` holds the stage chip (area header) and the body (line, run, activity, stats, sparklines, warning); every `#overlay-*` hook is now `#status-*`. `ORDER = ['view3d', 'status', 'view2d']`; the default desk layout is a row split, 3D 0.75 / Status 0.25; layout key moved to `cadex.layout.v4`. Collapse, `setOverlayCollapsed` and `cadex.overlay` are removed. The 3D viewport keeps the checkpoint scrubber, revision timeline, playback and model-status line [rec: neat-isle-1523].
- Measured in Chromium (`cli/cadex_cli/browser.py`): at 1400×900 Status is 317×769 beside a 951×769 3D viewport; at 390×844 the Status tab is 390×756 with no horizontal overflow; dragging Status onto 3D swaps them and Reset restores the default. `test_review_overlay.py` renamed to `test_review_status.py` [rec: neat-isle-1523].
- Gates: test-engine 2611 passed / 58 skipped; CLI suite 1203 passed / 1 skipped in thirds, GPU hidden. No engine, route, protocol op or tool schema changed [rec: neat-isle-1523].

## Negative knowledge

- [scope: `test_designing_turns_idle_once_the_window_passes` in `test_review_status.py` | confidence: medium | evidence: neat-isle-1523] A known minute-boundary flake moved with the rename from `test_review_overlay.py`; left alone.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-d2-status-own-editor-stage)
- neat-isle-1523 — ADR-572: Status editor beside the 3D viewport, tab on a phone, Chromium-measured; suites green
