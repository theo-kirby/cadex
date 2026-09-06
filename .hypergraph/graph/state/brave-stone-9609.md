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

Catalogued hardware is available as the **lib script namespace** over `CadexCatalog`, composed as parametric BREP values with source-qualified mounting interfaces and deliberately simple cosmetics (ADR-181, Phase 17) [rec: twilight-lake-8164].

**L0 fasteners/bearings and L1 servos work**: bolts, nuts, washers, inserts, clearance/tap-drill data, ball bearings, bushings, SG90/MG90S/MG996R/DS3218 servos and measured micro horns. Catalog rows cite sources and label approximate dimensions; servo actuators use rated-voltage stall torque converted once into engine units. Twenty-seven library tests include a real-kernel build of all generators, and the packaged lifecycle gate passed [rec: twilight-lake-8164].

**L2 boards work** through `lib.board` and the existing `boards`/`term` declarations: three sourced variants with placed solder-pad terminals, explicit approximations, real-kernel coverage and 47 passing packaged lifecycle/library tests. ADR-202 and ROADMAP record the slice. **L3 motors/mechanisms, catalog breadth, and manufacturer-source 25T horn/pigtail interfaces remain open.** [rec: stormy-quill-5350]

**L3 starts with `lib.gearmotor("pololu-2367")`**, discoverable through the catalog: Pololu's N20-size 100:1 MP 6 V variant without encoder. The BREP envelope includes a D shaft and mounting bores; source rows record manufacturer dimensions and qualified 6 V no-load/stall ratings. Geometry approximations are explicit and no continuous torque or inertia is inferred. Canonical and rotated motors pass real-kernel validation; engine suite 1980 passed/52 skipped, packaged lifecycle/library 54 passed with no skips. Broader L3 and catalog breadth remain open [rec: idle-dawn-5426].

**BLDC joins the catalog:** `lib.bldc("hobbywing-30415200")` carries HOBBYWING 2820 SL 550KV rear-mount dimensions, conservative shaft/collar clearance reservation and qualified no-load data. Shaft coupling fit and torque remain unsupported. Real-kernel mounting and placement probes pass; stable engine suite 1987 passed/52 skipped, packaged lifecycle/library 61 passed with no skips [rec: floral-stone-2866].

**L12 linear actuator shipped:** `lib.linear_actuator("l12-50-210-12-s", extension=...)` uses the existing LibraryPart recipe contract, with extension bounded to [0,50] mm, qualified operating specifications and unsupported-selection refusal. PROVENANCE §8d pins the manufacturer sources and omitted installation details; ADR-207 chooses revision F nominal bore centres over the older STEP models' 0.5 mm longer spacing [rec: southern-moss-9142] [rec: frosty-snow-9642]. The independent OCCT proof and actual library worker each pass 180 canonical/placed material/void probes at 0/23.5/50 mm extension, measuring 102/125.5/152 mm bore spacing in valid single solids [rec: long-heron-6915] [rec: frosty-snow-9642]. Post-build engine suite: 2002 passed/52 skipped; freshly staged packaged lifecycle/library gates: 76 passed, no skips. This local unrelocated payload is not a distributable-release claim. Broader L3 and catalog breadth remain open [rec: frosty-snow-9642].

**Solenoid evidence remains partial, with no catalog API:** PROVENANCE §8e and ADR-208/209 preserve source identities/hashes, conflicting travel claims, qualified force/duty points and exact missing interfaces. The 412 nominal exterior passes 72 canonical/placed OCCT probes; the mounting follow-up defers delivery after finding incompatible older TAU dimensions and incomplete Ledex B7 engagement/travel limits [rec: frosty-creek-6723] [rec: open-pine-9349]. Both audits pass the existing packaged lifecycle/library baseline (76 tests, no skips), with no new build, staging or full engine-suite run; this is no packaged solenoid implementation claim. Catalog breadth remains open [rec: frosty-creek-6723] [rec: open-pine-9349].

## Negative knowledge

- [scope: Pololu #2367 dimensions and packaged verification | confidence: high | evidence: idle-dawn-5426] The envelope uses the drawing’s 25.6 mm rear maximum amid conflicting product-page lengths. Filled rear geometry, 1 mm bore depth and shaft-flat transition are approximate; bore depth is not screw engagement permission. The tested stage-only payload retains local dependencies and is not a portable release.

- [scope: Actuonix L12-50-210-12-S catalog geometry | confidence: high | evidence: frosty-snow-9642] Filled internals, simplified housing/clevis transitions and omitted installation details establish no conservative collision envelope, installation fit, physical inertia, load or dynamics guarantee. S switches stop within 0.5 mm of stroke ends; geometric endpoints do not promise powered reachability.

- [scope: TAU0730TM-14 / Adafruit 412 partial exterior | confidence: high | evidence: frosty-creek-6723] Omitted mounting/coil/spring/wire geometry and approximate exterior details establish no hardware fit, collision clearance, physical inertia or performance. Gap is displacement from the drawing's held state, not a powered endpoint prediction.
- [scope: examined older TAU and Ledex B7 mounting sources | confidence: high | evidence: open-pine-9349] Older TAU mounting separation is 20 mm versus current 412's 18.2 mm; its slot geometry cannot be transplanted. B7-212-B-4 has dimensioned M3x0.5 mounting-plane centres but the examined sources lack engagement depth and maximum mechanical travel; the force plot's 0.4-inch endpoint is not a mechanical stop. This bounded search does not disprove other variants.

## Provenance

- twilight-lake-8164 — L0/L1 landed with catalog and kernel validation; L2/L3 and unsourced interfaces remain open
- stormy-quill-5350 — L2 joins L0/L1; remaining catalog and sourced-interface gaps stay open
- idle-dawn-5426 — ADR-205: catalog discovery gains sourced N20 geometry and qualified ratings; kernel and packaged checks pass
- floral-stone-2866 — BLDC catalog envelope, qualified source data and real-kernel/packaged evidence
- southern-moss-9142 — L12 source audit and nominal-centre precedence; no recipe or new implementation verification
- long-heron-6915 — independent nominal L12 OCCT construction and canonical/placed geometry proof
- frosty-snow-9642 — bounded L12 catalog variant ships with qualified specifications and full engine/packaged verification

- frosty-creek-6723 — ADR-208: sourced partial solenoid exterior passes 72 OCCT probes; missing mounting callouts prevent catalog delivery
- open-pine-9349 — ADR-209: incompatible older TAU and incomplete B7 interfaces defer solenoid delivery; joints qualification is next, existing packaged baseline passes 76 tests
