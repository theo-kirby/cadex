---
node_id: af41b867-f326-5d6f-b03b-4265faf06b29
slug: clear-banner-8342
title: The wiring and electronic-assembly surface
created_at: '2026-08-09T15:22:27+00:00'
parents:
- forest-wind-0342
summary: ''
---
Status: working

## Current

Procedural wire routing and the electronic-assembly surface, marked **experimental** in `docs/ARCHITECTURE.md` and carrying stated limits rather than hidden ones [rec: crisp-glacier-6395].

- Six pure-Python, FreeCAD-free, kernel-neutral modules, staged into the sandboxed worker **by filename** rather than imported: routing (`part.cable`), multi-conductor bundles, geometry-anchored terminals, solder joints, a declared connection table (`nets`) and a declared board table (`boards`). All of it is unit-testable headless [rec: crisp-glacier-6395].
- **None of it cost a protocol change.** `part.*` and `assembly.*` are the xscript surface, not the op table — the standing reason this much capability cost so little contract [rec: crisp-glacier-6395].
- The Wiring editor is Blender's **stock node editor re-registered for exactly one Python tree type**, which is also the clearest example of the project removing something in the teardown and bringing it back later for a different purpose [rec: crisp-glacier-6395] [rec: civic-horizon-2730].
- The solder joint is one **solid of revolution** — a closed outline, one face, one `revolve`, no boolean at all — which deleted every kernel hazard its predecessor documented: nine OCC calls per joint down to three, eight joints from 54 ms to 20.9 ms [rec: crisp-glacier-6395].
- `wcv8.cadex` is the worked example: 22 conductors across seven routes [rec: crisp-glacier-6395].

The live list of stated limits is the off-phase section of `docs/ROADMAP.md` — several are deferred by decision (a bundle as an editable graph concept, mesh hole detection, colouring solder differently from wire) and at least one is a known defect left unfixed because fixing it moves accepted digests [rec: crisp-glacier-6395].

## Negative knowledge

- [scope: tests over published registries | confidence: high | evidence: crisp-glacier-6395] A fixture that disagrees with its producer hides the defect it was written to catch: the published registry dropped the two fields the endpoint join is made of and every wire vanished from the canvas while the suite stayed green. Drive the real producer.
- [scope: shell-to-engine applies | confidence: high | evidence: crisp-glacier-6395] Starting a lifecycle and not polling it makes every apply after the first fail STALE_PROGRAM_REVISION silently. Twenty wires dragged built one cable, and the next refresh wiped the other nineteen off the canvas.
- [scope: mesh obstacles in routing | confidence: medium | evidence: crisp-glacier-6395] Mesh obstacles are bounding boxes, so a component cannot avoid itself as a mesh — its own pad is inside its own box and the wire is refused at its own port. Pass such a body as a part solid instead, where the import converts at all.

## Provenance

- crisp-glacier-6395 — the whole workstream, its modules, its worked example and the three defects real use found
- civic-horizon-2730 — the teardown that removed the node editor this surface brought back
