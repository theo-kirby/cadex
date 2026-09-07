# Product named-angle render evidence

Verified against source: 2026-09-08. [Cadex-new]. ADR-239 follow-up.

The public `cadex render` call writes four SVGs with embedded lossless CPU
images and an accepted-revision summary. These are copies of its actual
outputs, independently implemented in the LGPL CLI; no Blender renderer,
GUI, training or remote dispatch was involved in this measurement.

From the repo root:

```sh
./cadex script --project build/render-probe-11 --set examples/lifecycle/hinged-arm/script.py --json
/usr/bin/time -l ./cadex render --project build/render-probe-11 --json
```

The curved fixture is the `curved` script literal in
`cli/tests/test_render.py`: a 10×20×3 box rotated 90° about Z and translated
(12,30,6), plus a radius-4, height-30 cylinder at (25,30,0), both grounded.
Write that script to `build/render13-curved.py`, then run:

```sh
./cadex script --project build/render13-curved --set build/render13-curved.py --json
/usr/bin/time -l ./cadex render --project build/render13-curved --json
pixi run python -m pytest cli/tests
```

Both public render commands exited 0. Warm single samples, no build; these
are developer-machine observations, not isolated benchmarks:

| Fixture | triangles | snapshot bytes | acquisition s | render s | command wall s | maximum RSS bytes |
|---|---:|---:|---:|---:|---:|---:|
| Arm | 24 | 2,602 | 0.4908 | 0.5269 | 1.81 | 176,324,608 |
| Curved | 512 | 14,078 | 0.3293 | 0.6103 | 1.62 | 140,607,488 |

Acquisition includes the display rebuild and buffer snapshot; render includes
four projections, depth tests and SVG/PNG encoding, before writing files.
Whole-command timing includes startup, initial restore and project-document
work. RSS is `time -l`'s statistic, not simultaneous process-tree memory.
The final guard recheck produced byte-identical SVGs after the aggregate
placed-vertex budget was added. These timings do not measure walk overhead: walk wiring is a later unit.
The 100,000-triangle cap is a refusal boundary, not a throughput claim;
overdraw may hit the 20-million-pixel-work cap first.

All eight images were decoded from the actual SVGs and visually inspected
as contact sheets. Arm views show the plate, seated swing and overhang;
iso lighting distinguishes adjacent faces. The rotated box and cylinder have
different front/top/right extents, a circular top silhouette and correctly
occluded overlap in the right view. The cylinder's tessellation produces
faceted lighting; this is an approximate initial-pose preview, not a drawing.
Numeric tests pin the arm swing bounds to (12,0,6)..(92,8,14), rotated box
bounds to (-8,30,6)..(12,40,9), full accepted revision/digest identity, four
distinct nonblank images and five files committed in each test project.
Crossing triangles and complete occlusion also have pixel-level tests.

`arm-*.svg`, `curved-*.svg` and their summaries retain the original revision
and relative product paths (`review/render/…`); prefixes distinguish the two
evidence copies here. They contain no project-store paths. No checkpoint or
rollout was copied. Headless review remains open for walk integration and
sections; shell-only visibility is not represented in this protocol.

Final full built-engine CLI gate: **180 passed, zero skipped**, 172.71 s,
exit 0. The external gate monitor capped the entire process tree at 900 s /
3 GiB: observed 173.3742 s and peak sampled RSS 1,160,167,424 bytes, no cutoff.
See `cli-gate.log` and `cli-gate.json`. The render subset is 19 passing tests.
No engine/payload/protocol/shell edit required another zone gate or build.
