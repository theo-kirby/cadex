---
node_id: 25b4dd4e-48df-5b44-9cfc-5d03a78942b3
slug: sweet-arbor-1947
title: A2. Cadex renders a design as a presented product
created_at: '2026-09-27T15:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot10: **A2. Cadex renders a design as a presented product.** It asks for a studio hero shot plus the existing views, material from the design, hex3 at 1024 px in under 60 s headless on the CPU, pinned tests, and before/after images ≤ 300 KB [rec: damp-dusk-8045].

Evidence [rec: happy-garden-2470] (ADR-412, commit `2cb7ec9c`):
- `cli/cadex_cli/render.py` has one pure-Python renderer, `studio`; the flat `rasterize` is deleted. It gives a `hero` view at `camera(35°, 20°)` (in `LOOK_VIEWS` and the look tool enum), key/fill/rim light on crease-aware normals (40°), a seamless gradient backdrop, a measured soft contact shadow, and 2×2 supersampled AA. `render` writes `hero.png` at 1024 px. [rec: happy-garden-2470]
- Material comes from each part's appearance role via `render.materials`; `render.classify` is the single source of the environment/purchased split. [rec: happy-garden-2470]
- hex3 (revision `c1704bfcb631…`, Ryzen 9 9950X, no display/GPU): **hero 2.2 s at 1024 px**, all five images 6.5 s. [rec: happy-garden-2470]
- `cli/tests/test_look.py` pins hero bounds, size, sampling, shadow, AA, normals, role colours, refusal of an unknown role, and hero < 300 KB. Before/after committed: `docs/probes/ot10/hex3-look_iso.png` (32,756 B) vs `hex3-studio_iso.png` (110,996 B), and `hex3-studio_hero.png` (120,991 B). [rec: happy-garden-2470]

Judgement (maintainer): status is `working` on the renderer's measured 2.2 s. The caveat is carried below rather than hidden. [rec: happy-garden-2470]

## Negative knowledge

- [scope: hex3's accepted revision on this machine, if A2's 60 s bar includes acquisition | confidence: high | evidence: happy-garden-2470, shy-clover-2326] The bar is not met end to end: `./cadex render` spends ~207 s rebuilding the tessellation before drawing (about 7 min total) against 2.2 s of rendering. A fix would draw from the accepted attempt's retained tessellation; this is acquisition work, not renderer work.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- happy-garden-2470 — studio renderer, hero 2.2 s, before/after PNGs
- shy-clover-2326 — re-confirms the 207 s acquisition cost; hero byte-identical after the proxy pass
