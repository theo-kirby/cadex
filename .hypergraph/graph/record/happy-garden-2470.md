---
node_id: 48d1219d-6f42-5268-8a34-e60476be8482
slug: happy-garden-2470
title: 'ot10 A2: studio renderer for render and look; hex3 hero 1024 px in 2.2 s'
created_at: '2026-09-27T16:31:19+00:00'
parents:
- terse-falcon-8320
summary: ''
---
## What
ot10 A2: `cadex render` and the agent's `look` now draw a studio render instead of a flat-shaded screenshot (ADR-412, commit `2cb7ec9c`). It has:
- a low three-quarter `hero` view, and `render` writes it as `hero.png` at 1024 px;
- light that makes curvature read;
- a seamless backdrop and a measured soft contact shadow;
- 2×2 supersampled antialiasing;
- material taken from each part's appearance role.

## Why
The critic named A2 (short rung 2) as the next unit. This is that unit, as asked:
- headless, CPU-only and no new dependency;
- hex3 measured at 1024 px on a /tmp copy;
- before and after PNGs of the same view;
- output shape, limits and refusals pinned by tests;
- a clean role hook for A3 instead of a fixed two-colour split.

It serves `sweet-arbor-1947` (A2) and prepares `warm-basin-7003` (A3).

## Method
- **Renderer.** `cli/cadex_cli/render.py` has one pure-Python renderer, `studio`. The CLI promises no compiled dependency, so numpy was ruled out.
  - A scanline depth pass keeps a triangle id per subsample, at 2×2 subsamples per pixel. Only visible subsamples are shaded, then box-filtered down.
  - Lighting is a key, a fill and a rim light, with a Blinn highlight per role finish and a small sky sheen.
  - Normals are interpolated. Each corner averages the adjacent faces within 40° of its own face, so fillets shade smooth and boxes keep their edges.
  - The backdrop is a vertical gradient.
  - The contact shadow comes from a top-down map of the lowest surface over each cell above the floor. It has a tight term and a wide term, each blurred twice with a box blur. It is applied only when the camera is above the floor.
- **Deleted.** The flat `rasterize` is gone, and its tests now drive `studio`.
- **Views.**
  - `HERO` = `camera(35°, 20°)`, added to `LOOK_VIEWS` and to the look tool's enum and description.
  - `write_render` adds `hero.png` at 1024 px. Its summary gains `hero`, `environment` and `appearance`.
- **Materials.**
  - `render.materials` resolves a declared `appearance` role, then a `palette` override, then the inventory default: purchased → mechanism graphite `#2F3237`, printed → shell bone `#E9E6DF`. With no inventory, the index colours stay.
  - `render.classify` is now the one place that derives the environment and purchased sets from fit and inventory. The bridge and `render` both use it, so `render` now leaves the floor out as well.
- **Tests.** New tests in `cli/tests/test_look.py`:
  - hero angle bounds, size, 4 samples per pixel and a stepless backdrop;
  - the contact shadow darkens only the floor under the design, and is absent at elevation 0;
  - antialiasing: 2 colours per row at 1 sample, more than 2 at 4;
  - crease-aware normals on a cube and on a 24-sided cylinder;
  - role colours by default and by declaration, a palette override, and refusal of an unknown role;
  - `render` writes a 1024 px `hero.png` under 300 KB.

  The existing budget and refusal tests still hold.
- **Docs.** Updated `docs/CLI.md`, `docs/DESIGN-LANGUAGE.md` §7, `docs/probes/ot10/README.md` (a new A2 before/after section) and ADR-412.

## Result
- **hex3, measured.** Accepted revision `c1704bfcb631…`, /tmp copy, `./cadex render --json` on a Ryzen 9 9950X with Python 3.11, no display and no GPU. The four 512 px views plus the 1024 px hero took **6.5 s** (`render_seconds`); the hero alone took **2.2 s**. That is 106,326 drawn triangles and 4.1M subsample visits. Acquiring the tessellation took another **207 s**: that is the engine rebuild, unchanged by this unit. The whole command took 6 min 59 s.
- **Images committed:**
  - `docs/probes/ot10/hex3-studio_iso.png` (768 px iso, 110,996 B). It sits beside the baseline's `hex3-look_iso.png` (the same view, flat, 32,756 B).
  - `docs/probes/ot10/hex3-studio_hero.png` (1024 px, 120,991 B).
  - Both are under 300 KB.
- **Suites.** `pixi run test-engine`: 2209 passed, 53 skipped. `pixi run python -m pytest cli/tests`: 976 passed, 1 skipped. There is no engine, protocol or payload change, so the packaged gate is not needed.

Concerns for the next iteration:
- **The 60 s bar.** If A2's 60 s bar is read as including acquisition, it is not met: the 207 s rebuild dominates. The renderer itself is 2.2 s. A fix would draw from the accepted attempt's retained tessellation rather than a rebuild. That is engine or CLI acquisition work, not renderer work.
- **Not re-scored.** hex3 is not re-scored. The frozen baseline stands. No judge call was made in this unit.
- **Appearance of `look` has changed.** Every `look` image the product agent sees is now a studio image, and printed parts are bone, not orange. The A4 overlay text still says nothing about roles, and A3 must fill `appearance` from xscript.
- **Tail.** Unreconciled tail: 2 records.

Dispatch closed: 1 unit — A2 studio renderer (hero, lighting, backdrop, contact shadow, AA, material by role) in render and look, hex3 hero 2.2 s at 1024 px

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 2cb7ec9ce1be2c7a12b866a760a9b4e4ec45c0a1

## State Impact

- target: sweet-arbor-1947 — render and look draw a studio image (hero view at 20°/35°, key/fill/rim light on crease-smoothed normals, seamless backdrop, measured contact shadow, 2x2 AA, material by role); hex3 renders at 1024 px in 2.2 s (all five images 6.5 s) after a 207 s engine rebuild for acquisition; before/after PNGs committed (ADR-412, 2cb7ec9c)
- target: warm-basin-7003 — render.materials takes an appearance role map and palette (shell/mechanism/accent, defaults bone/graphite/orange from purchased vs printed); xscript declaration, inventory carriage and the proxies remain open
