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

**SKF GE 6 C joint shipped:** `lib.joint("skf-ge-6-c", tilt_degrees=...)` exposes the sourced nominal two-ring spherical plain bearing as a two-solid compound, with inner tilt about canonical Y before placement, bounded to [-13,13] degrees. PROVENANCE §8f pins manufacturer revision/hash, bore/OD/width/sphere datums, abutment limits and qualified ratings; unsupported variants and invalid tilt are refused, and metadata is copy-isolated [rec: first-wind-9707] [rec: morning-field-8202]. Independent qualification and actual-worker checks cover four tilts, analytic ring volumes, bore/OD/sphere surfaces, shaft clearance, limiting shoulders, non-overlap and 96 canonical/placed material/void probes; discovery and canonical/placed compound publication are tested. Final engine suite: 2016 passed/52 skipped; after build and staging, packaged lifecycle/library: 90 passed, no skips. Catalog breadth and broader L3 remain open [rec: morning-field-8202].

**Coverage baseline audited (ADR-212):** `docs/L3-COVERAGE.md` separates nominal geometry and source ratings from coupling fit, S-switch powered reachability and physical inertia; the actuator helper belongs to `ServoPart`, not ordinary L3 `LibraryPart` values. The audit identified N20 interface verification as the smallest evidence-only gap [rec: steady-rain-3009].

**N20 interfaces independently verified:** source and staged actual workers measure shaft diameter 3 mm, flat-to-opposite 2.5 mm, flat axial extent Z=1..10 mm, and mounting bores of radius 0.8 mm at X=±4.5, Y=0, Z=-1..0 mm. Canonical and rotated/translated instances pass 160 material/void probes, valid-single-solid and equal-volume checks. Full engine: 2023 passed / 52 skipped; fresh packaged lifecycle/library: 91 passed, no skips. The assumed 1 mm blind-bore depth and sharp flat transition remain approximations, with no installed-fit or screw-engagement claim. No new SKU or runtime behavior changed. The local 2.4 GB stage has 144 relocation violations and is not shippable [rec: windy-lily-2895].

**RI50 qualification parked (ADR-223):** the manufacturer source audit and fixture follow-up add evidence in `docs/L3-COVERAGE.md`, with source URLs and hashes, but no catalog entry. Inspected ratings, fixture BOM/STEP headers and support text establish neither RI50-specific cooling, winding temperature and test duration/duty nor linkage between the rating sheet and no-Hall drawing revision. Geometry proof and delivery remain gated; full L3 stays open [rec: slender-harbor-9625] [rec: shy-hill-8139]. The fixture's populated sheet lists a pivot, rear cover, two MR148 bearings and six M2.5x4 screws; the other two sheets are empty. These documentation-only audits add no common-size completion or fresh runtime/payload verification [rec: slender-harbor-9625] [rec: shy-hill-8139].

**AT2814 alternative qualification blocked (ADR-223):** the T-MOTOR AT2814 Long Shaft KV900 manufacturer bench report and V2.0 drawing were audited in `docs/L3-COVERAGE.md`. The selected row reports 0.291 N m at 7601 rpm, 11.05 V and 27.02 A, with 68 C surface temperature after three minutes; ambient, current definition, cooling and test-to-drawing revision linkage remain unresolved. No winding qualified and no geometry proof or catalog delivery followed. Set A remains unchanged, RI50 stays parked, and full L3 remains open. The bounded motor-search sequence stops; the recorded recommendation is to replan toward residual GUI work. This documentation audit supplies no fresh runtime or payload verification [rec: mild-harvest-8460].

**Fifth-servo source audit stopped (ADR-229):** `docs/FIFTH-SERVO-AUDIT.md` pins manufacturer documents, hashes and interface blockers for HS-311 and HS-422. Neither qualifies for unchanged ServoPart: open mounting mouths cannot be reproduced by the stated circular drills; output-stack qualification is incomplete and HS-422 dimension labels conflict. Four servo rows remain; no candidate kernel proof or runtime delivery followed. Existing local-stage lifecycle/library tests pass **91, no skips**; matching catalog/API hashes do not establish whole-payload equivalence or a portable release. Replanning is required before proof or delivery [rec: hidden-ridge-7342].

**Manufacturer STEP accessory audit stopped (ADR-231):** no catalog identities or vendor assets were added. Neither horn nor pigtail qualified; source, fit and rights blockers are tracked in the manufacturer-source gap. The inspected mesh and linked-part imports do not establish the assumed script-owned raw STEP delivery path, and a raw kernel read supplies no project reopen/rebuild proof [rec: steady-reef-0162].

**Gears family shipped (ADR-233, ADR-234):** `lib.spur_gear` and `lib.rack` over `CadexCatalog.gear_spec` (ISO 53 profile constants, ISO 54 series 1 modules) share one involute generator, verified on the source suite, a rebuilt engine and a fresh staged payload (2050 passed / 52 skipped; packaged lifecycle/library 107, no skips) [rec: wild-beacon-4213]. `lib.rack_and_pinion` composes them over `CadexCatalog.rack_and_pinion_spec` (centre distance, backlash as a radial shift, root clearance, travel per revolution and per degree, rack length, nested member specs) as a two-solid compound placed like every other library value, with `bore`, `rack_height` and `rotation_degrees` keywords; the composition lives in the `gears` family notes, so the `describe_api` golden did not move. Fresh packaged lifecycle/library gate: 119 passed, no skips. Compound-mechanism progress is tracked on idle-tower-1624 [rec: mellow-garden-0940].

## Negative knowledge

- [scope: Pololu #2367 dimensions and packaged verification | confidence: high | evidence: idle-dawn-5426] The envelope uses the drawing’s 25.6 mm rear maximum amid conflicting product-page lengths. Filled rear geometry, 1 mm bore depth and shaft-flat transition are approximate; bore depth is not screw engagement permission. The tested stage-only payload retains local dependencies and is not a portable release.

- [scope: Actuonix L12-50-210-12-S catalog geometry | confidence: high | evidence: frosty-snow-9642] Filled internals, simplified housing/clevis transitions and omitted installation details establish no conservative collision envelope, installation fit, physical inertia, load or dynamics guarantee. S switches stop within 0.5 mm of stroke ends; geometric endpoints do not promise powered reachability.

- [scope: TAU0730TM-14 / Adafruit 412 partial exterior | confidence: high | evidence: frosty-creek-6723] Omitted mounting/coil/spring/wire geometry and approximate exterior details establish no hardware fit, collision clearance, physical inertia or performance. Gap is displacement from the drawing's held state, not a powered endpoint prediction.
- [scope: examined older TAU and Ledex B7 mounting sources | confidence: high | evidence: open-pine-9349] Older TAU mounting separation is 20 mm versus current 412's 18.2 mm; its slot geometry cannot be transplanted. B7-212-B-4 has dimensioned M3x0.5 mounting-plane centres but the examined sources lack engagement depth and maximum mechanical travel; the force plot's 0.4-inch endpoint is not a mechanical stop. This bounded search does not disprove other variants.

- [scope: SKF GE 6 C nominal catalog geometry and delivery payload | confidence: high | evidence: first-wind-9707, morning-field-8202] Omitted chamfers, liner and running clearance establish no fit, tolerance, physical inertia, load or dynamics guarantee. The tested 2.4 GB local development payload retains 248 external-path relocation violations and is not a portable release.

- [scope: inspected CubeMars RI50 KV100 no-Hall sources and fixture | confidence: high | evidence: slender-harbor-9625, shy-hill-8139] Ambient limits and STEP export dates do not establish torque-test conditions or rating/drawing revision equivalence. The fixture BOM contains mechanical items only; DWG annotations and the installation video remain unverified, so the audit does not exhaust all possible evidence. The frameless rotor/stator cannot use the existing shaft/collar recipe; no geometry, fit, physical-inertia or powered-behavior claim follows.

- [scope: ADR-233/234 gears family | confidence: high | evidence: wild-beacon-4213, mellow-garden-0940] Standalone values and a geometric mesh only: no strength, torque, load, stiffness or efficiency rating. Tooth counts below 17 undercut and are only warned.

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
- first-wind-9707 — ADR-210: manufacturer datums and nominal two-ring OCCT qualification support conditional joint delivery
- morning-field-8202 — ADR-211: bounded joint catalog compound ships with actual-worker, discovery and fresh packaged verification; broader gaps remain open
- steady-rain-3009 — ADR-212: 90-test existing packaged baseline and explicit per-family evidence limits
- windy-lily-2895 — independent N20 interface measurements and probes in source/staged workers; passing suites and local relocation limits
- slender-harbor-9625 — BLDC set A and hashed RI50 source audit; thermal/revision qualification blocks delivery
- shy-hill-8139 — bounded fixture/support follow-up leaves qualification gaps; RI50 parked with unread-source limits
- mild-harvest-8460 — AT2814 source audit leaves current/thermal/revision gaps; no qualified winding or catalog delivery, bounded motor searches stopped
- hidden-ridge-7342 — ADR-229 source/interface blockers stop fifth-servo delivery; existing packaged baseline passes 91 tests
- steady-reef-0162 — no accessory identities added; existing imports do not establish script-owned raw STEP delivery
- wild-beacon-4213 — ADR-233 gears family (spur gear, rack) verified on the staged payload; standalone values, no rating
- mellow-garden-0940 — ADR-234 rack_and_pinion composition over rack_and_pinion_spec, verified on the fresh payload; geometric mesh only
