---
node_id: fad56f30-8fff-5604-bcbf-8d8d417e9278
slug: crisp-glacier-6395
title: 'Prehistory: the wiring workstream — routed harnesses, terminals and a node editor'
created_at: '2026-08-09T15:16:12+00:00'
parents:
- open-dew-7293
summary: 'Eight days on no phase: procedural routing, terminals, solder joints, declared nets and boards, and Blender''s stock node editor brought back for wiring.'
---
## What

An independent workstream that landed on **no phase** and ran in the background
of everything else for eight days: ADR-056, 057, 062, 063, 064, 065, 066, 067,
074, 113, 114, 115, 117, 118, 119, 120, 121, 122. Procedural wire routing,
geometry-anchored terminals, solder joints, a declared connection table, a
declared board table, and a wiring editor drawn in Blender's node editor.

## Why

Branches from the standalone era rather than following it. The author wanted the
app to model an electronic assembly — connect terminals, define boards, simulate
the harness — and the routing had to be procedural, because a hand-authored
harness is not parametric.

**It is also why a piece of Blender came back.** The teardown had ripped a great
deal out, including the node-based system Blender ships for geometry nodes. The
wiring editor re-registers that stock node editor for exactly one Python tree
type (ADR-066), so the editor menu gains "Wiring" and stays short. Removing
something and then bringing it back for a different purpose is a pattern this
project uses deliberately, not an accident.

## Method

Six pure-Python, FreeCAD-free, kernel-neutral modules, staged into the sandboxed
worker bundle **by filename** rather than imported: `CadexRouting.py` (a lazy
26-connected A* on an integer lattice, clearance by lattice dilation, a
line-of-sight shortcut, sag, bounded by a probe budget — occupancy arrives as an
`occupied(i,j,k)` callback, so the whole algorithm is unit-testable headless),
`CadexBundle.py` (a rotation-minimising frame carried by double reflection,
twisted and flat conductor offsets, a numeric solve for the lay radius at which
no two conductors interpenetrate), `CadexTerminals.py`, `CadexSolder.py`,
`CadexNets.py` and `CadexBoards.py`.

**No protocol change for any of it.** `part.*` and `assembly.*` are the xscript
surface, not the op table — which is the standing reason this much capability
cost so little contract.

## Result

`wcv8.cadex` is wired with 22 conductors across seven routes: a twisted battery
pair, three twisted phases per motor, and two four-way flat ribbons.

The solder joint became **one solid of revolution** in ADR-064 — a closed
outline, one face, one `revolve`, and no boolean at all — which deleted the
fuse, the cut, `CUT_OVERSHOOT_MM` and every kernel hazard the previous design had
documented: nine OCC calls per joint down to three, and eight joints on the probe
plate from 54 ms to 20.9 ms. The risk moved out of OCC and into pure Python,
where it is decidable headless over a parameter sweep.

**Three defects that only real use found**, and they are the most reusable part
of this record:
- The published registry dropped the two fields the endpoint join is made of, so
  a script predating `nets()` drew every board and not one wire — hidden by a
  fixture that disagreed with its producer (ADR-113).
- A board with two headers is two terminal *sets* that shared the component's
  name, so the canvas gave one set's sockets to the other and every declared wire
  lost an end: two boards, no links, `applying…` stuck in the header for the life
  of the `.blend` (ADR-115).
- The push started a lifecycle nobody polled, so the revision guard never
  advanced and every apply after the first was refused `STALE_PROGRAM_REVISION`
  **in silence** — twenty wires dragged built one cable, and the next refresh
  wiped the other nineteen off the canvas (ADR-122).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW wiring-harness — routed cables and bundles, geometry-anchored terminals, solder joints, declared nets and boards, and a wiring editor; experimental, with several stated limits.
- target: NEW shell — the Wiring editor, and the pick gestures that write table rows rather than script text.
