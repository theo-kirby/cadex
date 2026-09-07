---
node_id: c0cba2e7-6baf-528a-9ec4-c2f5ce86051a
slug: silver-key-8483
title: Named-angle CPU render CLI delivers revision-bearing depth-tested views
created_at: '2026-09-07T23:28:08+00:00'
parents:
- brave-delta-4193
summary: ''
artifacts:
- docs/probes/named-angle/product-render/README.md
- docs/probes/named-angle/product-render/cli-gate.log
- docs/probes/named-angle/product-render/cli-gate.json
- docs/probes/named-angle/product-render/arm-summary.json
- docs/probes/named-angle/product-render/curved-summary.json
- docs/probes/named-angle/product-render/arm-front.svg
- docs/probes/named-angle/product-render/arm-top.svg
- docs/probes/named-angle/product-render/arm-right.svg
- docs/probes/named-angle/product-render/arm-iso.svg
- docs/probes/named-angle/product-render/curved-front.svg
- docs/probes/named-angle/product-render/curved-top.svg
- docs/probes/named-angle/product-render/curved-right.svg
- docs/probes/named-angle/product-render/curved-iso.svg
---
## What

Delivered `cadex render --project PROJECT --json`: one CPU-only call writes
front/top/right/iso SVG previews and a revision-bearing summary under
`review/render/`. Added independent LGPL rendering and bounded buffer snapshot
code, CLI dispatch, 19 render tests, CLI documentation, an ADR-239 follow-up,
a ROADMAP checkbox and eight inspected product-image evidence copies.
Walk wiring remains a separate unit; no engine, protocol, payload or shell
source changed.

## Why

Advance charter criterion “The agent can see its work without a screen”
(damp-moon-9297), short-plan item 2, following the successful arm rerun
brave-delta-4193 and ADR-239's recorded renderer choice. Pixel-center depth
resolves the centroid painter's crossing/overlap failure without a graphics
runtime or new dependency. SVG is a wrapper for a lossless 512px CPU image,
not a claim of analytic vector drawings. Preserve initial solved placements,
exclude definition copies, and explicitly state that shell-only visibility
is not in the protocol rather than inventing GUI state.

The overseer requested a maintainer/planner pass before implementation. This
work dispatch explicitly forbids reconcile, state edits and edits to
.ouroboros; follow that stronger contributor constraint and leave the separate
maintainer pass outstanding. Pre-work graph check found two unreconciled record
nodes, not the overseer's claimed three. No human question, delegation,
reconcile or plan/state/charter edit.

## Method

`cli/cadex_cli/render.py` snapshots the successful accepted display immediately
after standard-quality rebuild while the normal CLI project lock is held,
before any later engine request. Validate little-endian layouts, finite
coordinates, triangle indices, solved matrices and bounds. Bound display count,
total byte input, vertices per source, aggregate placed vertices, placed
triangles and bounding-box pixel work per view. Cache source geometry, apply
solved matrices once and suppress the unposed source copies. Missing meshes
and poses fail, with no guessed fallback. Orthographic projection, barycentric
depth, flat directional lighting and standard-library PNG encoding produce
SVGs; output names, revision, digest, bounds, camera bases, approximation,
coverage and timing land in summary.json. Geometry/render refusals do not
write partial new views; old successful files can remain and retain their
revision. Shell coordination remains subject to the documented unshared-lock
limitation.

Pixel tests cover crossing triangles and complete occlusion in either order.
Buffer tests cover invalidation after snapshot, malformed layout/sidecar,
nonfinite coordinates, missing tessellation, bad indices/revision/pose and
byte/triangle/aggregate-instance/pixel-work refusals. Real-engine public CLI
tests cover the hinged arm, a rotated/translated box with a curved cylinder,
standalone geometry, empty-project refusal, repeatability, distinct nonblank
image contents, accepted revision/digest fidelity and five committed project
files plus PROGRESS.md.

Reproduction commands, raw SVGs and their summaries live under
`docs/probes/named-angle/product-render/`. Run the documented hinged-arm
`cadex script`, then `/usr/bin/time -l ./cadex render --project
build/render-probe-11 --json`. Repeat with the curved fixture from test_render.py
at build/render13-curved. Decode the actual embedded PNGs with existing Pillow
for inspection only; no renderer dependency installed. Inspect both four-view
contact sheets. Recheck after the aggregate vertex guard and assert all eight
SVGs byte-identical to the inspected copies. No GUI launch, remote dispatch,
checkpoint/rollout commit or full build. Final CLI gate uses the existing local
training venv and an external 900-second / 3-GiB sampled process-tree cutoff
for the whole suite, stronger than the per-training-run budget.

## Result

Both public render calls exited 0. Final warm developer-machine samples:
arm: 24 triangles, 2,602 input bytes, acquisition 0.4908 s, rendering 0.5269 s,
whole command 1.81 s, time -l maximum RSS 176,324,608 bytes. Curved assembly:
512 triangles, 14,078 input bytes, acquisition 0.3293 s, rendering 0.6103 s,
whole command 1.62 s, maximum RSS 140,607,488 bytes. Acquisition includes display
rebuild and snapshot; rendering includes four projections/depth tests/encoding,
before file writes. These are not isolated throughput benchmarks or walk-overhead
measurements. The triangle cap is not a claim of supported interactive scale;
overdraw can hit the pixel cap first.

Arm bounds retain base (0,0,0)..(60,60,6) and swing
(12,0,6)..(92,8,14), with two posed components and no source copies. Rotated
box bounds are (-8,30,6)..(12,40,9); the cylinder's circular top silhouette,
faceted lighting and right-view occlusion were visually inspected. All eight
views are nonblank and bear the accepted revision. Subpixel geometry can be
missed; no transparency, analytic edges, dimensions, engineering-drawing
accuracy, shell visibility or motion-envelope review is claimed.

Final full built-engine CLI gate exit 0: 180 passed, zero skipped, 172.71 s.
External whole-suite monitor: 173.3742 s, sampled peak tree RSS 1,160,167,424
bytes, no 900-second / 3-GiB cutoff. The final render subset is 19 passed in
8.84 s. Earlier full runs passed 177 and 179 tests before the last defensive
cases/aggregate-instance guard; the final 180-test run covers the final source.
No failures or baseline differences. Gate log and monitor receipt are retained
beside the SVG evidence. No engine/protocol/payload/shell zone change means
no build, packaged gate or shell gate is required. git diff --check passes;
pre-record graph export/check exits 0 with no violations or warnings, and
post-mint export/check must pass before the single commit.

Next: wire the delivered render call into walk review, project scaffold and
mode-artifact table as short-plan item 3; retain inventory/clearance and evidence
on arm/carriage. Named-plane sections and their walk integration remain open
before the charter review criterion can be ticked. This unit does not close
the criterion or the whole goal. The tail becomes three unreconciled records;
a separate maintainer/planner pass is due. No failed leg remains.
Dispatch closed: 1 unit — delivered and inspected bounded, revision-bearing named-angle CPU render CLI with tested depth handling.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 2202fd69946f9903742f2f9ac2360ce39c455fb1

## State Impact

- target: damp-moon-9297 — Delivered cadex render: bounded accepted snapshots, front/top/right/iso SVGs, solved placements and pixel depth; inspected arm/curved images and full CLI gate 180 passed, zero skipped. Walk integration and sections remain open.
- target: chilly-union-8972 — New CPU-only render command writes five generated project review files with revision and approximation metadata; no graphics dependency or engine/protocol change.
