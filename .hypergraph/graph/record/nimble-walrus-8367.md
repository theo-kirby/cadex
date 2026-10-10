---
node_id: 21462bbc-980c-57b1-9e20-16dcc83f0a96
slug: nimble-walrus-8367
title: 'Panel system rebuilt: declared panels, envelope/panel worker ops, fit.panels fails bad panels (ADR-633..637)'
created_at: '2026-10-10T19:33:15+00:00'
parents:
- golden-flame-1650
summary: ''
---
## What

The panel system rebuilt to `docs/ARCHITECTURE-REVIEW.md` recommendations 1 and 2
(ADR-633..637). Panels are declared (`assembly.component(..., role="panel",
covers=[...])`, apart from `appearance`), cut in the part worker from an envelope of
what they cover (`part.envelope` + `part.panel`, new `CadexEnvelope.py`), screwed to
the frame on bosses cast exactly onto its BREP with screws `part.mate`d onto published
fastener frames, and judged by `fit.panels`, where a floating, colliding (at rest or
through a swept joint) or unmounted panel fails the fit. `lib.panel` and the recipe
sampler `CadexPanels.sample` are deleted (CadexPanels.py 1,410 lines out, 335 in;
cadex_library_api.py 44 out; CadexEnvelope.py 1,535 new). `lib.housing` is kept.

## Why

Nine creature runs kept no `lib.panel`: a convex sleeve lofted along one axis round the
frame too, from points a second CSG kernel read; no motion, no openings, bosses that
missed. The shell check judged colour, not role, on a median gap, and was advisory.

## Method

Envelope: covered solids (and declared hinge/slider sweeps) tessellated, parity-filled
on a voxel grid in the panel's frame, closed by a rolling ball with two EDTs (or the
convex hull by its face planes, `radius="hull"`), distanced. Panel: first crossing from
`side` as a height field; region by `max_angle`, `within`, openings (swept parts,
cones, holes); outline contoured, Chaikin-cut, drawn as a pcurve on a B-spline surface
smoothed to radius/3 without entering the clearance; thickened by `makeOffsetShape`;
skirt (`flange=mm|"frame"`) of four sewn ruled faces under a small overhang, cut short
by the envelope, opening keep-outs and the frame; seams as slab commons; bosses sifted
on voxels, spread farthest-first, cast exactly (centre + rim), counterbored for one
stocked screw, pilots for the frame, `avoid=` other panels' screw paths.
Measurement (assembly worker): p10..max inner-face gap to covers+welded parts, air
volume and egg ratio, wall by Möller-Trumbore rays, coverage by rays, size, points.

Probes on scratch copies under `ulimit -v 25000000`, images by the engine's studio
renderer: `docs/probes/panels/` (README, scripts, fit JSON, before/after PNGs).

OOM incident (ADR-637): two probe `FreeCADCmd` runs started directly (no worker
RLIMIT_AS) reached 58-60 GB and were OOM-killed, taking the tmux session down. Under a
cap the cause was a fused skirt returned as a "valid" solid 1e29 mm across that was
then tessellated; also an unbatched triangle-column expansion. Fixed by counting before
allocating (voxels, column pairs in 2 M batches, sweep poses, hull planes), refusing
shapes far larger than their field, and RLIMIT_AS (6 GB) in the kernel test driver.
Probe peaks after: 1.0-1.7 GB.

## Result

- Electronics cover (2S pack + ESP32 on a deck): two pieces, 15 mm skirt to the deck,
  six M2x8 seated by counterbore depth, nearest approach 1.39-1.75 mm at c = 1.5.
- Gantry enclosure (hull, lid + 3 sides, seamed for a 256 mm bed, 24 M3x8): fit pass,
  sweep pass, 8 pieces pass, egg 1.41-1.60, seams 0.6 mm. Without `avoid=` the check
  named three screws meeting in one corner post.
- Leopard (cfix-leopard-a copy): rear cover (2 pieces), front keel cover, head cover
  with a motion opening round the nodding neck link: fit pass, 4 panels pass, p90 3.5-10.0
  mm, egg 1.08-1.13. The first draft failed correctly (front cover through the neck
  drive; head cover struck in motion). Covers are lids on a slim keel; side panels with
  openings round each hip housing are not done.
- Cost: panel plans 2-15 s; fit pairs against large frames tens of CPU-s; leopard build
  430 s on a raised 1200 s budget.
- Suites (CPU-only): test-engine 2790 passed, 62 skipped (under `ulimit -v 25000000`); cli/tests 1258 passed, 1 skipped, 1 failed (a progress-line test pinned to the old shells phrase, then fixed: 6 passed). Under the 25 GB cap the browser tests cannot start Chromium, so cli/tests ran uncapped (its engines are cadexd workers, capped themselves).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: worktree-agent-a4f442c933785d7ba
- commit: 9204f4d359b0a88efe5c126c18766bff3f94a9d2

## State Impact

- target: idle-lantern-9094 — Panels are declared (role="panel", covers=[...]) and cut in the worker from an envelope of what they cover (part.envelope/part.panel, CadexEnvelope.py): rolling-ball closing or hull, skirt, seams, motion openings, bosses cast onto the frame BREP for one stocked screw, screws mated onto published fastener frames; fit.panels fails floating, colliding (static or swept) and unmounted panels. lib.panel and CadexPanels.sample deleted. Proved on an electronics cover, a gantry enclosure and the leopard (docs/probes/panels). Limits: one side's height field per panel, vertical skirts, butt seams; leopard side panels round hip housings not done; panel builds cost seconds and the fit pairs against large frames tens of CPU-s. Panel plan memory is bounded (ADR-637) after two uncapped probes OOM-killed the box.
