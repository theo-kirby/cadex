---
node_id: 0a9701ac-53a4-5ddd-9062-ad83ed7a81a0
slug: noble-vale-4742
title: 'H2 unit 1: print-bed hero, parts laid flat and packed on N beds (ADR-569)'
created_at: '2026-10-06T18:25:19+00:00'
parents:
- tiny-ash-6709
summary: ''
---
## What

H2 unit 1 of 2: the print-bed hero (ADR-569). `CadexStudio.print_bed` lays every
printed part flat, packs the parts onto as many beds as needed, and draws them on the
dark mat. Each part is numbered in the H1 face, and the purchased-hardware list from the
inventory sits beside the beds. New pure functions: `printed_parts`, `purchased_rows`,
`lay_flat`, `pack_beds` (MaxRects), `print_bed`, `_compose_bed`. Nine engine tests are in
`cadex_tests/test_studio_print_bed.py`. The example image is
`docs/probes/orun4/h2-print-bed.png`.

## Why

The critic named H2 next, split into two bounded units, and this is unit 1: the layout
and render, with non-overlap, bounds and multi-bed tests, on an `orun4-biped-sts`
scratch copy. H2 is the highest-ranked open criterion. Done as asked, with no deviation.

## Method

- Dumped the accepted snapshot, fit and inventory of `~/cadex-projects/orun4-biped-sts`
  (revision `14b7223ee485`) to a pickle with a harness kept out of the repo
  (`/tmp/h2/dump.py`, which uses `_engine_session`, `acquire_snapshot` and
  `_published_blocks`). Iterated renders from that pickle.
- **Printed parts:** sources the inventory calls uncatalogued, minus
  `derived_catalog_sources` (cut purchases) and minus fit world geometry. With no
  inventory, it refuses.
- **Seat:** the largest flat face (triangles binned by normal at 1/400 and plane at
  0.2 mm) whose plane has every vertex on one side. Either winding is accepted. The 64
  largest faces are tried, and if none fits the part keeps its assembled attitude. The
  part is then turned to its minimum-area footprint rectangle over the hull's edges, long
  side along X.
- **Pack:** row packing first put 10 parts on 2 beds, with a lot of empty space. I
  replaced it with MaxRects best-short-side-fit, largest first, quarter turns allowed.
  Each part grows by the gap inside a bed shrunk by the gap. A part too big for any bed
  gets its own bed and is listed under `not_fitting`, as is a part taller than the bed.
- **Camera:** first tried 0°/58°, which looked flat; switched to 20°/50°. Labels first
  sat on each part's top, but tall parts' labels collided. They now sit at the footprint
  centre at half height, and a badge that lands on an earlier one steps down.

## Result

What is true now:

- On the scratch copy at 256 × 256 mm, 10 printed parts go on **2 beds**: bed 1 is 89%
  covered once each part is grown by the 6 mm gap, and `foot_r` spills onto bed 2. At
  300 mm they all fit on **1 bed**. The image lists 10 hardware rows from `catalog_counts`
  (6 × servo sts3215, bolts, boards, battery). One render takes **6.0 s**; the PNG is
  **223 KB** and 1536 × 1024. All 10 parts seat on a flat face: the deck on its 6206 mm²
  face, the pelvis on its 7703 mm² face, and the hip brackets stand 54 mm tall on their
  back plates.
- `test_studio_print_bed.py`: 9 passed. It covers the seat, the rejected face with
  material beyond it, the no-seat fallback, non-overlap and bounds over 40 random
  packings, the multi-bed and oversize cases, the parts split and the refusals.
- Gates at this commit: `pixi run build-engine` (CadexStudio.py installed);
  `pixi run test-engine` **2611 passed, 58 skipped** (5 m 43 s); the CLI suite with
  the GPU hidden, in thirds: **400 passed** (2 m 46 s), **353 passed, 1 skipped**
  (5 m 31 s), **443 passed** (2 m 08 s). I did not stage or run the packaged lifecycle
  gate: no op or protocol changed, and `cadexd` never imports `CadexStudio` (ADR-445).

Assumptions:

- A 256 mm desktop bed and a 6 mm gap, both parameters, stated in the image.
- The print orientation is the slicer's "lay on face" default, not a judgment on
  strength or overhang.

Next unit (H2 unit 2): call `print_bed` and the existing hero when `evaluate` passes,
store both beside the evaluation, list them in `/api/project`, show them in the 2D
viewport, and test a passing and a failing evaluation. The tail is 1 record; no reconcile
is needed yet.

Dispatch closed: 1 unit — H2 print-bed hero: parts laid flat, MaxRects-packed on N beds, hardware list (ADR-569)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: f3903327618ad36db122f6e5abb62b19098ae75c

## State Impact

- target: dry-vale-5761 — Unit 1 of 2 landed (ADR-569, commit f3903327): CadexStudio.print_bed lays printed parts flat on their largest flat face, MaxRects-packs them on 256 mm beds (2 beds for the scratch reference copy, 1 at 300 mm), numbers them and lists inventory hardware; 9 engine tests pin seat, non-overlap, bounds, multi-bed. Open: hook both heroes to a passing evaluate, /api/project and the 2D viewport.
