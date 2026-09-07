---
node_id: cf276294-dbba-523f-8a7e-8890e43e30b7
slug: rising-banner-4325
title: L3 motors and mechanisms families exist
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: superseded
## Current

Open charter criterion: **L3 motors and mechanisms families exist** over `CadexCatalog`, same test shape as the boards family, and the packaged lifecycle gate passes. [rec: empty-wolf-3962]

**First L3 motor shipped:** `lib.gearmotor("pololu-2367")` provides the sourced Pololu N20-size 100:1 MP 6 V gearmotor without encoder, with manufacturer dimensions and qualified no-load/stall ratings. Real-kernel tests build canonical and rotated solid outputs; the engine suite reports 1980 passed/52 skipped and packaged lifecycle/library tests report 54 passed with no skips [rec: idle-dawn-5426].

**BLDC mounting envelope shipped:** `lib.bldc("hobbywing-30415200")` provides the HOBBYWING Skywalker 2820 SL 550KV rear-mount envelope with sourced mounting dimensions, a conservative shaft/collar reservation and qualified no-load data. Canonical and placed mounting interfaces pass real-kernel checks; the stable engine suite passed 1987 tests/52 skipped and packaged lifecycle/library passed 61 with no skips [rec: floral-stone-2866].

**Bounded L12 linear actuator shipped:** `lib.linear_actuator("l12-50-210-12-s", extension=...)` exposes nominal mounting geometry, supplied-clevis approximation, qualified specifications and refusal of unsupported selections or extension outside [0,50] mm. ADR-207 retains datasheet precedence over the older STEP models' 0.5 mm longer mounting spacing [rec: southern-moss-9142] [rec: frosty-snow-9642]. The independent OCCT construction and actual library worker pass 180 canonical/placed probes at 0/23.5/50 mm extension with measured bore spacing 102/125.5/152 mm; all outputs are valid single solids [rec: long-heron-6915] [rec: frosty-snow-9642]. After one build/install, the engine suite passed 2002 tests/52 skipped; completed staging followed by packaged lifecycle/library gates passed 76 tests with no skips [rec: frosty-snow-9642].

**Solenoid delivery deferred:** the TAU0730TM-14 / Adafruit 412 source audit proves only a partial nominal exterior: 72 canonical/placed OCCT probes pass at 0/2.3/4.9 mm gap, with valid single solids; missing mounting callouts prevent the planned catalog contract. No solenoid API shipped [rec: frosty-creek-6723]. The follow-up finds incompatible older TAU dimensions and incomplete Ledex B7 engagement/travel evidence. ADR-209 selects joints source qualification as the next bounded L3 unit; solenoids remain open for new manufacturer evidence or a separately justified narrower contract [rec: open-pine-9349].

**Qualified SKF GE 6 C joint shipped:** the manufacturer-source and independent nominal two-ring OCCT qualification now has catalog delivery through `lib.joint("skf-ge-6-c", tilt_degrees=...)`, bounded to [-13,13] degrees and published as a two-solid compound [rec: first-wind-9707] [rec: morning-field-8202]. Actual-worker checks at -13/0/6.5/13 degrees verify analytic volumes, mounting and spherical surfaces, shaft/shoulder clearance, non-overlap and 96 canonical/placed material/void probes. Final engine suite passed 2016 tests/52 skipped; one completed build/install and staging followed by fresh packaged lifecycle/library verification passed 90 tests, no skips [rec: morning-field-8202].

**Residual coverage audited (ADR-212):** `docs/L3-COVERAGE.md` distinguishes four delivered single-SKU families from the remaining promise. Full L3 stays open: one BLDC winding has kV but no torque contract or plural common-size coverage. Solenoid mounting/travel prerequisites and ADR-209 restart conditions remain unchanged. The audit does not authorize another unspecified catalog expansion or close compound-mechanism gaps [rec: steady-rain-3009].

**N20 interfaces independently verified:** source and staged actual workers measure shaft diameter 3 mm, flat-to-opposite 2.5 mm, flat axial extent Z=1..10 mm, and mounting bores of radius 0.8 mm at X=±4.5, Y=0, Z=-1..0 mm. Canonical and rotated/translated instances pass 160 material/void probes, valid-single-solid and equal-volume checks. Full engine: 2023 passed / 52 skipped; fresh packaged lifecycle/library: 91 passed, no skips. The assumed 1 mm blind-bore depth and sharp flat transition remain approximations, with no installed-fit or screw-engagement claim. No new SKU or runtime behavior changed. The local 2.4 GB stage has 144 relocation violations and is not shippable [rec: windy-lily-2895].

**BLDC acceptance set A defined:** a reversible robot-prototype sampling set comprises shafted 28xx and hollow frameless 50 and 80 classes, not a claim of market prevalence. Each needs an independently qualified winding plus real-worker and packaged evidence; the delivered single winding does not complete this set [rec: slender-harbor-9625].

**RI50 qualification parked (ADR-223):** the manufacturer source audit and fixture follow-up add evidence in `docs/L3-COVERAGE.md`, with source URLs and hashes, but no catalog entry. Inspected ratings, fixture BOM/STEP headers and support text establish neither RI50-specific cooling, winding temperature and test duration/duty nor linkage between the rating sheet and no-Hall drawing revision. Geometry proof and delivery remain gated; full L3 stays open [rec: slender-harbor-9625] [rec: shy-hill-8139].

**AT2814 alternative qualification blocked (ADR-223):** the T-MOTOR AT2814 Long Shaft KV900 manufacturer bench report and V2.0 drawing were audited in `docs/L3-COVERAGE.md`. The selected row reports 0.291 N m at 7601 rpm, 11.05 V and 27.02 A, with 68 C surface temperature after three minutes; ambient, current definition, cooling and test-to-drawing revision linkage remain unresolved. No winding qualified and no geometry proof or catalog delivery followed. Set A remains unchanged, RI50 stays parked, and full L3 remains open. The bounded motor-search sequence stops; the recorded recommendation is to replan toward residual GUI work. This documentation audit supplies no fresh runtime or payload verification [rec: mild-harvest-8460].

## Negative knowledge

- [scope: Pololu #2367 catalog model | confidence: high | evidence: idle-dawn-5426] External envelope and mounting details include documented approximations; manufacturer stall ratings do not establish continuous torque, thermal performance or physical inertia. Packaged tests used a local development payload, not a portable release.

- [scope: HOBBYWING 30415200 catalog envelope | confidence: high | evidence: floral-stone-2866] The diameter-10.5 reservation covers the full 18 mm shaft/collar projection because collar length is undimensioned; the 5 mm shaft metadata does not establish coupling-fit length. Bore depth is an assumption, not engagement permission; filled geometry is not physical inertia. Manufacturer current/power entries are limited to 46 seconds, not continuous control limits; no torque rating is inferred.
- [scope: Actuonix L12 source discrepancy | confidence: high | evidence: southern-moss-9142] The measured 0.5 mm mismatch is not established tolerance, switch allowance or a correction for all CAD surfaces. Datasheet nominal centres are the explicit ADR-207 implementation choice, not a demonstrated fit guarantee.

- [scope: Actuonix L12-50-210-12-S catalog geometry | confidence: high | evidence: frosty-snow-9642] Filled internals, simplified housing/clevis transitions and omitted installation details establish no conservative collision envelope, installation fit, physical inertia, load or dynamics guarantee. S switches stop within 0.5 mm of stroke ends; geometric endpoints do not promise powered reachability.

- [scope: TAU0730TM-14 / Adafruit 412 partial exterior | confidence: high | evidence: frosty-creek-6723] Omitted mounting/coil/spring/wire geometry and approximate exterior details establish no hardware fit, collision clearance, physical inertia or performance. Gap is displacement from the drawing's held state, not a powered endpoint prediction.
- [scope: examined older TAU and Ledex B7 mounting sources | confidence: high | evidence: open-pine-9349] Older TAU mounting separation is 20 mm versus current 412's 18.2 mm; its slot geometry cannot be transplanted. B7-212-B-4 has dimensioned M3x0.5 mounting-plane centres but the examined sources lack engagement depth and maximum mechanical travel; the force plot's 0.4-inch endpoint is not a mechanical stop. This bounded search does not disprove other variants.

- [scope: SKF GE 6 C nominal catalog geometry and delivery payload | confidence: high | evidence: first-wind-9707, morning-field-8202] Omitted chamfers, liner and running clearance establish no fit, tolerance, physical inertia, load or dynamics guarantee. The tested 2.4 GB local development payload retains 248 external-path relocation violations and is not a portable release.

- [scope: inspected CubeMars RI50 KV100 no-Hall sources and fixture | confidence: high | evidence: slender-harbor-9625, shy-hill-8139] Ambient limits and STEP export dates do not establish torque-test conditions or rating/drawing revision equivalence. The fixture BOM contains mechanical items only; DWG annotations and the installation video remain unverified, so the audit does not exhaust all possible evidence. The frameless rotor/stator cannot use the existing shaft/collar recipe; no geometry, fit, physical-inertia or powered-behavior claim follows.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- idle-dawn-5426 — ADR-205: sourced N20 motor with real-kernel and packaged verification; broader L3 remains open
- floral-stone-2866 — ADR-206: sourced BLDC envelope with qualified interfaces and passing kernel/packaged verification
- southern-moss-9142 — ADR-207: measured L12 mounting disagreement; source precedence selected, implementation still open
- long-heron-6915 — independent nominal L12 OCCT construction and canonical/placed geometry proof
- frosty-snow-9642 — bounded L12 catalog variant ships with qualified specifications and full engine/packaged verification

- frosty-creek-6723 — ADR-208: sourced partial solenoid exterior passes 72 OCCT probes; missing mounting callouts prevent catalog delivery
- open-pine-9349 — ADR-209: incompatible older TAU and incomplete B7 interfaces defer solenoid delivery; joints qualification is next, existing packaged baseline passes 76 tests
- first-wind-9707 — ADR-210: manufacturer datums and nominal two-ring OCCT qualification support conditional joint delivery
- morning-field-8202 — ADR-211: bounded joint catalog compound ships with actual-worker, discovery and fresh packaged verification; broader gaps remain open
- steady-rain-3009 — ADR-212: four-family coverage/evidence audit preserves residual BLDC scope and deferred solenoid delivery
- windy-lily-2895 — independent N20 interface measurements and probes in source/staged workers; passing suites and local relocation limits
- slender-harbor-9625 — BLDC set A and hashed RI50 source audit; thermal/revision qualification blocks delivery
- shy-hill-8139 — bounded fixture/support follow-up leaves qualification gaps; RI50 parked with unread-source limits
- mild-harvest-8460 — AT2814 source audit leaves current/thermal/revision gaps; no qualified winding or catalog delivery, bounded motor searches stopped


## Superseded

Parked by the operator before nt3 (2026-09-07). The criterion moved to `## Later criteria` in the charter, where it seeds no gap. It is not abandoned: the human promotes it back into `## Done criteria` when the nt3 frontier — the lifecycle walk and the headless review calls — lands or blocks. No evidence about the criterion itself changed.
