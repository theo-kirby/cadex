---
node_id: cf276294-dbba-523f-8a7e-8890e43e30b7
slug: rising-banner-4325
title: L3 motors and mechanisms families exist
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion: **L3 motors and mechanisms families exist** over `CadexCatalog`, same test shape as the boards family, and the packaged lifecycle gate passes. [rec: empty-wolf-3962]

**First L3 motor shipped:** `lib.gearmotor("pololu-2367")` provides the sourced Pololu N20-size 100:1 MP 6 V gearmotor without encoder, with manufacturer dimensions and qualified no-load/stall ratings. Real-kernel tests build canonical and rotated solid outputs; the engine suite reports 1980 passed/52 skipped and packaged lifecycle/library tests report 54 passed with no skips [rec: idle-dawn-5426].

**BLDC mounting envelope shipped:** `lib.bldc("hobbywing-30415200")` provides the HOBBYWING Skywalker 2820 SL 550KV rear-mount envelope with sourced mounting dimensions, a conservative shaft/collar reservation and qualified no-load data. Canonical and placed mounting interfaces pass real-kernel checks; the stable engine suite passed 1987 tests/52 skipped and packaged lifecycle/library passed 61 with no skips [rec: floral-stone-2866].

**Bounded L12 linear actuator shipped:** `lib.linear_actuator("l12-50-210-12-s", extension=...)` exposes nominal mounting geometry, supplied-clevis approximation, qualified specifications and refusal of unsupported selections or extension outside [0,50] mm. ADR-207 retains datasheet precedence over the older STEP models' 0.5 mm longer mounting spacing [rec: southern-moss-9142] [rec: frosty-snow-9642]. The independent OCCT construction and actual library worker pass 180 canonical/placed probes at 0/23.5/50 mm extension with measured bore spacing 102/125.5/152 mm; all outputs are valid single solids [rec: long-heron-6915] [rec: frosty-snow-9642]. After one build/install, the engine suite passed 2002 tests/52 skipped; completed staging followed by packaged lifecycle/library gates passed 76 tests with no skips [rec: frosty-snow-9642].

**Solenoid delivery deferred:** the TAU0730TM-14 / Adafruit 412 source audit proves only a partial nominal exterior: 72 canonical/placed OCCT probes pass at 0/2.3/4.9 mm gap, with valid single solids; missing mounting callouts prevent the planned catalog contract. No solenoid API shipped [rec: frosty-creek-6723]. The follow-up finds incompatible older TAU dimensions and incomplete Ledex B7 engagement/travel evidence. ADR-209 selects joints source qualification as the next bounded L3 unit; solenoids remain open for new manufacturer evidence or a separately justified narrower contract [rec: open-pine-9349].

Reconcile judgement: status remains `open`: N20, BLDC and bounded L12 delivery do not close full L3. Solenoids, joints and compound gearing remain outstanding; this source audit does not establish that other solenoid variants are unsuitable [rec: idle-dawn-5426] [rec: floral-stone-2866] [rec: frosty-snow-9642] [rec: open-pine-9349].

## Negative knowledge

- [scope: Pololu #2367 catalog model | confidence: high | evidence: idle-dawn-5426] External envelope and mounting details include documented approximations; manufacturer stall ratings do not establish continuous torque, thermal performance or physical inertia. Packaged tests used a local development payload, not a portable release.

- [scope: HOBBYWING 30415200 catalog envelope | confidence: high | evidence: floral-stone-2866] The diameter-10.5 reservation covers the full 18 mm shaft/collar projection because collar length is undimensioned; the 5 mm shaft metadata does not establish coupling-fit length. Bore depth is an assumption, not engagement permission; filled geometry is not physical inertia. Manufacturer current/power entries are limited to 46 seconds, not continuous control limits; no torque rating is inferred.
- [scope: Actuonix L12 source discrepancy | confidence: high | evidence: southern-moss-9142] The measured 0.5 mm mismatch is not established tolerance, switch allowance or a correction for all CAD surfaces. Datasheet nominal centres are the explicit ADR-207 implementation choice, not a demonstrated fit guarantee.

- [scope: Actuonix L12-50-210-12-S catalog geometry | confidence: high | evidence: frosty-snow-9642] Filled internals, simplified housing/clevis transitions and omitted installation details establish no conservative collision envelope, installation fit, physical inertia, load or dynamics guarantee. S switches stop within 0.5 mm of stroke ends; geometric endpoints do not promise powered reachability.

- [scope: TAU0730TM-14 / Adafruit 412 partial exterior | confidence: high | evidence: frosty-creek-6723] Omitted mounting/coil/spring/wire geometry and approximate exterior details establish no hardware fit, collision clearance, physical inertia or performance. Gap is displacement from the drawing's held state, not a powered endpoint prediction.
- [scope: examined older TAU and Ledex B7 mounting sources | confidence: high | evidence: open-pine-9349] Older TAU mounting separation is 20 mm versus current 412's 18.2 mm; its slot geometry cannot be transplanted. B7-212-B-4 has dimensioned M3x0.5 mounting-plane centres but the examined sources lack engagement depth and maximum mechanical travel; the force plot's 0.4-inch endpoint is not a mechanical stop. This bounded search does not disprove other variants.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- idle-dawn-5426 — ADR-205: sourced N20 motor with real-kernel and packaged verification; broader L3 remains open
- floral-stone-2866 — ADR-206: sourced BLDC envelope with qualified interfaces and passing kernel/packaged verification
- southern-moss-9142 — ADR-207: measured L12 mounting disagreement; source precedence selected, implementation still open
- long-heron-6915 — independent nominal L12 OCCT construction and canonical/placed geometry proof
- frosty-snow-9642 — bounded L12 catalog variant ships with qualified specifications and full engine/packaged verification

- frosty-creek-6723 — ADR-208: sourced partial solenoid exterior passes 72 OCCT probes; missing mounting callouts prevent catalog delivery
- open-pine-9349 — ADR-209: incompatible older TAU and incomplete B7 interfaces defer solenoid delivery; joints qualification is next, existing packaged baseline passes 76 tests
