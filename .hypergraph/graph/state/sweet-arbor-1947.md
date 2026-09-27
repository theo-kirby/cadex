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

- **Scope of the 60 s bar.** The owner's charter clarifies that the bar covers drawing once the accepted revision's tessellation is acquired; the rebuild is reported separately [rec: strong-summit-4135]. `ot10-hexapod-1`: drawing 5.9 s (hero 2.1 s), rebuild 29.3 s, whole command 63.7 s. hex3: rebuild ~207 s, whole command ~7 min [rec: soft-spark-6990].

Judgement (maintainer): status stays `working`. The drawing meets the bar on both designs. soft-spark-6990 claimed A2 was incomplete on whole-command time. strong-summit-4135 withdrew that claim under the clarified charter, so it is not carried. The rebuild figures remain as separate measurements [rec: soft-spark-6990] [rec: strong-summit-4135].

## Negative knowledge

- [scope: `./cadex render` whole-command time on this machine | confidence: high | evidence: happy-garden-2470, shy-clover-2326, soft-spark-6990] Acquiring the tessellation dominates: ~207 s rebuild on hex3 and 29.3 s on ot10-hexapod-1, against 2–6 s of drawing. This is outside A2's bar as clarified [rec: strong-summit-4135]. Speeding it up means drawing from the accepted attempt's retained tessellation, which is acquisition work, not renderer work.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- happy-garden-2470 — studio renderer, hero 2.2 s, before/after PNGs
- shy-clover-2326 — re-confirms the 207 s acquisition cost; hero byte-identical after the proxy pass
- soft-spark-6990 — whole-command render timings: 63.7 s on ot10-hexapod-1 (29.3 s rebuild, 5.9 s draw)
- strong-summit-4135 — the owner's clarified bar excludes the rebuild; soft-spark's incompleteness claim withdrawn
