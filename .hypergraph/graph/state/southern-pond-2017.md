---
node_id: f8bc2220-1f20-556c-b394-42537fd6e810
slug: southern-pond-2017
title: D3. Layouts come from one-click presets, and areas move like Blender's
created_at: '2026-10-06T07:42:23+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun4: **D3. Layouts come from one-click presets, and areas move like Blender's.** A layout control offers at least: single, side by side, stacked, 2 over 1 and 1 over 2, three columns, three rows, quad — each filling its areas with editors in a sensible order, in one click. Areas still drag to dock/swap and resize by edges, with a visible drag handle and a drop preview. A browser test applies every preset, asserts area count and geometry, then drags one area onto another. Layout stays per-browser (B5); a reset returns to the default. The human owns the checkbox [rec: light-mist-9160].

**Evidence complete, awaiting the owner's tick** (ADR-573, commit `70304ce6`) [rec: cold-mist-9459]. Reconcile judgement: status `working`.

- `layout.js` `preset(name)` over eight shapes (single, side, stacked, two_over_one, one_over_two, columns, rows, quad), equal shares, filled in reading order 3D → Status → 2D → `empty`. View → Layout shows eight icon buttons (`#layout-presets button[data-preset]`) under Reset; one click applies and closes the menu [rec: cold-mist-9459].
- An `empty` pseudo-editor (any count) shows the editor picker and a hint; `show(type)` fills an empty area before splitting. Quad's fourth area is empty because an area moves its editor's own DOM (ADR-534) and a second 2D viewport would need a second sheet stage — ADR-573 records the choice and how to undo it [rec: cold-mist-9459].
- The grip is stronger (80 % → 100 % on hover, grab cursor); the drop preview names its landing (Swap / Dock left / right / above / below) [rec: cold-mist-9459].
- `cli/tests/test_review_layout.py` (Chromium): all eight presets by click, area counts 1,2,2,3,3,3,3,4 and geometry within ±2.5 %, picker on every area, layout kept in `cadex.layout.v4` across reload, a "Dock right" drag, Reset restores the default; fails without the change [rec: cold-mist-9459].
- Gates: test-engine 2611 passed / 58 skipped; CLI suite green in thirds (392 / 324+1 skipped / 488), GPU hidden. No route, localStorage key, engine module, protocol op, tool schema or dependency changed [rec: cold-mist-9459].
- One screenshot per preset is in `docs/probes/orun4/d3-preset-*.png` [rec: eager-sage-0150].

## Negative knowledge

None yet.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-d3-layouts-come-from-one)
- cold-mist-9459 — ADR-573: eight one-click presets, empty areas, labelled drop preview, Chromium-measured; suites green
- eager-sage-0150 — the eight preset screenshots committed under docs/probes/orun4/
