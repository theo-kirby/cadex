---
node_id: ea5e4567-9455-5c56-9e69-af71ebc9539b
slug: brave-stone-9609
title: Parts library — hardware catalog and remaining families
created_at: '2026-09-05T21:41:12+00:00'
parents:
- forest-wind-0342
summary: ''
---
Status: open

## Current

Catalogued hardware is available as the **lib script namespace** over `CadexCatalog`, composed as parametric BREP values with exact mounting interfaces and deliberately simple cosmetics (ADR-181, Phase 17) [rec: twilight-lake-8164].

**L0 fasteners/bearings and L1 servos work**: bolts, nuts, washers, inserts, clearance/tap-drill data, ball bearings, bushings, SG90/MG90S/MG996R/DS3218 servos and measured micro horns. Catalog rows cite sources and label approximate dimensions; servo actuators use rated-voltage stall torque converted once into engine units. Twenty-seven library tests include a real-kernel build of all generators, and the packaged lifecycle gate passed [rec: twilight-lake-8164].

**L2 boards work** through `lib.board` and the existing `boards`/`term` declarations: three sourced variants with placed solder-pad terminals, explicit approximations, real-kernel coverage and 47 passing packaged lifecycle/library tests. ADR-202 and ROADMAP record the slice. **L3 motors/mechanisms, catalog breadth, and manufacturer-source 25T horn/pigtail interfaces remain open.** [rec: stormy-quill-5350]

**L3 starts with `lib.gearmotor("pololu-2367")`**, discoverable through the catalog: Pololu's N20-size 100:1 MP 6 V variant without encoder. The BREP envelope includes a D shaft and mounting bores; source rows record manufacturer dimensions and qualified 6 V no-load/stall ratings. Geometry approximations are explicit and no continuous torque or inertia is inferred. Canonical and rotated motors pass real-kernel validation; engine suite 1980 passed/52 skipped, packaged lifecycle/library 54 passed with no skips. Broader L3 and catalog breadth remain open [rec: idle-dawn-5426].

## Negative knowledge

- [scope: Pololu #2367 dimensions and packaged verification | confidence: high | evidence: idle-dawn-5426] The envelope uses the drawing’s 25.6 mm rear maximum amid conflicting product-page lengths. Filled rear geometry, 1 mm bore depth and shaft-flat transition are approximate; bore depth is not screw engagement permission. The tested stage-only payload retains local dependencies and is not a portable release.

## Provenance

- twilight-lake-8164 — L0/L1 landed with catalog and kernel validation; L2/L3 and unsourced interfaces remain open
- stormy-quill-5350 — L2 joins L0/L1; remaining catalog and sourced-interface gaps stay open
- idle-dawn-5426 — ADR-205: catalog discovery gains sourced N20 geometry and qualified ratings; kernel and packaged checks pass
