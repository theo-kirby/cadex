---
node_id: c9c2ee79-7171-5dee-be9f-324e511d4c89
slug: rough-water-0848
title: The app's viewport paints each part in its appearance role (ADR-449)
created_at: '2026-09-29T12:10:24+00:00'
parents:
- crimson-trail-6068
summary: ''
---
## What
GUI-parity slice 4 (ADR-449): the app's viewport paints each part in its appearance role (shell / mechanism / accent, in the assembly's palette), by the engine's own rule.

## Why
The owner asked to bring the GUI app up to the CLI (warm-spire-8762). The viewport drew every part in default grey, so the design on screen was not the design `look` judged.

## Method
- Engine: `CadexStudio.role_colours(display, fit, inventory)` resolves roles from the display map alone; `render_files` shares its row helper. A studio `blocks` request with `display` returns `appearance`.
- Shell: new `mesh_agent/cadex_roles.py`, a `cadex_views` record (`roles`, order 10), settled accepts only, worker thread + timer. One object-linked material per role, tagged `cadex_role`; user materials are never painted over. `measure_blocks` passes the accepted display and caches its result per revision. `cadex_hydrate._build_mesh` adds one empty material slot so roles survive mesh swaps.
- Verified: `pixi run build-engine && stage-engine && build-shell && gate`; engine suite; CLI render/look/sheet/inventory tests with CADEX_ENGINE_ROOT on the payload.

## Result
- Engine suite: 2295 passed, 54 skipped (3 new tests in test_studio_process.py, incl. viewport colours == render colours).
- CLI test_render/look/sheet/inventory: 70 passed.
- Gate: all 7 new checks in `test_the_viewport_paints_each_part_in_its_role` pass; roles survive a reshape; a user material is kept. Paint 0.001 s (blocks reused from the agent's build cache). Slider median 0.549 s (bar 0.65). The only failures are the 8 pre-existing restore-lockout ones on clean main.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: gui/role-materials
- commit: 7305273a0e749f4034b10d7e4c2e79f5d57bf783

## State Impact

- target: shy-crane-2573 — the app's viewport paints each part in its appearance role and palette (shell/mechanism/accent) by the engine's CadexStudio.role_colours, via the studio blocks request; object-linked materials, user materials kept, settled accepts only, slider latency unmoved (ADR-449)
