---
node_id: 0c5fcb25-107c-5314-a775-115e1bbfb709
slug: placid-lily-5624
title: Named-plane section CLI preserves cavities in accepted solved geometry
created_at: '2026-09-07T23:59:42+00:00'
parents:
- witty-brook-9419
summary: ''
artifacts:
- docs/probes/named-section/README.md
- docs/probes/named-section/section.svg
- docs/probes/named-section/summary.json
- docs/probes/named-section/cli-gate.log
- docs/probes/named-section/targeted-gate.log
---
## What

Delivered `cadex section --plane XY|XZ|YZ --offset-mm N`: a headless accepted-tessellation cut, with revision-bearing filled SVG and JSON committed under the project. ADR-240 and the ROADMAP delivery checkbox document this single unit. Walk integration is deliberately separate.

## Why

Advances charter criterion **The agent can see its work without a screen**, target damp-moon-9297, following witty-brook-9419's first short unit. The reversible choice is a qualified tessellation cut over the existing accepted display contract rather than a new exact-section engine/protocol surface. No exact headless section operation is exposed today. The overseer requested reconciliation first, but this dispatch explicitly forbids reconciliation without exception; no state, STATE.md, plan or charter was edited.

## Method

Independently authored LGPL CLI code reuses render.snapshot's bounded, validated world-space triangles. A small per-object triangle-count metadata field retains ownership without relying on palette colors. Intersect triangles with the named world plane, snap endpoints to a 1e-6 mm grid, require degree-two closed contour graphs, and fill all loops per object with SVG even-odd parity. No graphics library or engine import enters the product. Accepted revision/digest, solved placements, contour coordinates, plane/offset/units, acquisition and contour timings, approximation and limits are retained.

Plane vertex/edge/face contacts within tolerance, open/branched cuts, duplicate and collapsed segments return unsupported reports with reasons and available=false. Outside planes return empty. Acquisition/revision/invalid-input/write failures remain command errors; retained old files are not interpreted as successful results. These reports do not certify solid validity, self-intersection absence, union across overlapping objects or swept motion.

Ran `pixi run python -m pytest cli/tests -q`: 188 passed, zero skipped, 185.02 s. It exercised the built development engine and the suite's existing local toy CPU training/walk regressions. After a linear contour-traversal refinement and adding the sloped-face test, ran `pixi run python -m pytest cli/tests/test_section.py -q`: 7 passed, zero skipped, 5.35 s. No engine/protocol/payload/shell edit or full build; no GUI or remote dispatch. Whole-command memory was not sampled.

The real-engine fixture is a 20x20x10 mm block with radius-4 through hole, rotated 90 degrees around Z and translated (30,40,5). XY at 8 mm yields two closed contours with areas approximately 400 and 50.265 mm² and correct placed bounds; XY at 18 mm is empty, and at 5 mm unsupported. Tests verify accepted revision/digest and actual project git tracking. Synthetic tests cover all three planes, open geometry, contacts, cavities, sloped tetrahedron offsets and retained files after refusal. Initial fixture syntax incorrectly used DomainValue.translate; corrected to the documented part.transform before successful gates.

Actual SVG/JSON and both gate logs are retained under docs/probes/named-section/. Rasterized the SVG headlessly with a temporary inspection-only CairoSVG environment and existing pixi libcairo, then visually inspected the filled square, clear circular cavity, boundary strokes and label. Initial CairoSVG import could not locate libcairo; the existing pixi library search path resolved it. Sample acquisition 0.3268 s and contour generation 0.000697 s exclude SVG serialization and writes and are observations, not benchmarks.

## Result

Section delivery is verified and the tree is green. The headless-review criterion remains open: next wire the section snapshot into walk review, update the scaffold and mode artifacts together, preserve empty/unsupported/error and revision semantics, then separately rehearse both mechanisms with meaningful interior cuts and tracked outputs. No lifecycle walk integration claim is made here. This record joins the one-node unreconciled tail; the separate maintainer owns reconciliation.

Dispatch closed: 1 unit — named-plane section CLI with qualified cavity-preserving cuts and built-engine verification.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: c21b0cf3b161bb55ab3816563b31af741d63bb08

## State Impact

- target: damp-moon-9297 — Delivered and tested named-plane tessellation section CLI, preserving placements/cavities with explicit empty and unsupported reports; walk wiring and two-mechanism complete review evidence remain open.
- target: chilly-union-8972 — Added section subcommand writing committed revision-bearing SVG and JSON under review/section; full built-engine CLI suite 188 passed, final section suite 7 passed.
