---
node_id: 4f3649cf-f914-5afe-bbcb-9c5472b829f1
slug: twilight-lake-8164
title: 'ADR-181: the parts library — lib script namespace, catalog, fasteners, bearings, servos (L0+L1)'
created_at: '2026-08-30T23:10:24+00:00'
parents:
- odd-banner-6071
summary: ''
---
## What

The parts library (ADR-181, ROADMAP Phase 17, slices L0+L1): catalogued
hardware as parametric part values, staged as the `lib` global in every
project script. L0 is fasteners and bearings (ISO metric bolts, nuts,
washers, heat-set inserts, clearance/tap-drill data, the common ball
bearings, a parametric bushing); L1 is the four servo classes (SG90,
MG90S, MG996R, DS3218) with datasheet mounting interfaces, measured
micro horns, effective density for `assembly.body`, and
`.actuator(joint, control_deg=...)` bounded by the manufacturer's stall
torque converted from kg·cm once, in the library.

## Why

Owner direction 2026-08-31: the product builds robots, so the agent
needs the hardware robots are built from as a library it can compose
like Lego — with real specs, so parts lists and dynamics carry
datasheet numbers rather than guesses. Three shaping decisions, made
with the owner: script vocabulary rather than a new tool (the four-op
surface of ADR-013 is untouched; the catalog rides `describe_api` as
one additive `library` response key); parametric BREP recipes from spec
tables rather than STL assets; interface-exact and cosmetically simple
(threads and knurls deliberately unmodelled).

## Method

- `CadexCatalog.py` (new): spec rows with sources cited per row —
  ISO 4762/4032/7089, DIN 7991/985, vendor insert tables, bearing
  manufacturer tables, and a web-research pass over the four servos
  (TowerPro pages, the AUS TA0132 measured SG90 drawing, Handsontec
  MG996R, official Dsservo DS3218). Values no datasheet dimensions are
  listed in the row's `approximate` field, not passed off as measured.
  Miniature bearings carry the shielded (ZZ) widths — the open ribbon
  series really is narrower — and that is stated in the table comment.
- `cadex_library_api.py` (new): one generator per family emitting
  ordinary part-domain DomainValues; placement composes roll+alignment
  quaternions into one `part.transform`; a servo's datum is the shaft
  axis at the case top, so swapping SKUs never moves a joint.
- Wiring: `_staged_globals` stages `lib` over the part and assembly
  APIs; `describe_project_api` serves the catalog (list-shaped rows so
  the response-shape golden stays stable as SKUs grow);
  `OP_RESPONSE_SPECS`, the golden fixture, `docs/INTEGRATION.md` and
  the shell client all moved in the same change per the protocol rule.
  Shell (ours only): `cadex_backend.api_overview` lists `lib` with a
  part-number summary; `describe_cad_api domain="lib"` serves the block
  with its catalog.

## Result

- `test_library.py`: 27 tests — catalog pins, recipe-tree checks,
  placement math, actuator mapping, and an end-to-end cadexd build of
  every generator (eleven solids incl. two placed servos and a horn)
  through the real kernel.
- Full engine suite: 1946+ passed; the only failure is the
  pre-existing biped-demo licensing header failure (present at HEAD,
  untouched by this work).
- Packaged gate green against the staged payload
  (`CADEX_ENGINE_ROOT` lifecycle run, 14 passed).
- Torque now reaches dynamics as data: an MG90S actuator is
  `torque_limit_nmm=176.5` (1.8 kg·cm @ 4.8 V) by construction; an
  unrated voltage is refused naming the rated ones.
- Parked deliberately: 25T horns and servo pigtail terminals (no
  dimensioned source; dsservo.com STEP files are the named next
  source), boards (L2), motors/mechanisms (L3).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

- target: NEW parts-library — new vertical under the engine: the lib script namespace over CadexCatalog (ADR-181); L0 fasteners/bearings and L1 servos landed with spec-pinned tests and a kernel-verified build; L2 boards and L3 motors/mechanisms open
- target: forest-wind-0342 — the script vocabulary gained the lib global and describe_api gained the library response key (OP_RESPONSE_SPECS, golden fixture, INTEGRATION.md and shell client moved together); servo stall torque now reaches assembly.actuator as datasheet data
- target: shy-crane-2573 — mesh_agent surfaces the library: api_overview lists lib with part numbers, describe_cad_api domain=lib serves the catalog, gate suite covers it
