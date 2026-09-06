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

**Linear actuator remains unimplemented.** All eight official Actuonix L12 STEP models have mounting-axis spacing 0.5 mm greater than revision F datasheet nominal; stroke travel agrees. ADR-207 selects nominal datasheet centres for the future L12-50-210-12-S with supplied clevis, retaining source disagreement and fit limits. The 61 passing packaged tests certify the existing baseline only [rec: southern-moss-9142].

Reconcile judgement: status remains `open`: N20 and one BLDC envelope do not close L3. Linear actuators, solenoids, joints and compound gearing remain outstanding; BLDC torque, shaft coupling fit and additional sizes remain unsupported [rec: idle-dawn-5426] [rec: floral-stone-2866] [rec: southern-moss-9142].

## Negative knowledge

- [scope: Pololu #2367 catalog model | confidence: high | evidence: idle-dawn-5426] External envelope and mounting details include documented approximations; manufacturer stall ratings do not establish continuous torque, thermal performance or physical inertia. Packaged tests used a local development payload, not a portable release.

- [scope: HOBBYWING 30415200 catalog envelope | confidence: high | evidence: floral-stone-2866] The diameter-10.5 reservation covers the full 18 mm shaft/collar projection because collar length is undimensioned; the 5 mm shaft metadata does not establish coupling-fit length. Bore depth is an assumption, not engagement permission; filled geometry is not physical inertia. Manufacturer current/power entries are limited to 46 seconds, not continuous control limits; no torque rating is inferred.
- [scope: Actuonix L12 source discrepancy | confidence: high | evidence: southern-moss-9142] The measured 0.5 mm mismatch is not established tolerance, switch allowance or a correction for all CAD surfaces. Datasheet nominal centres are the explicit ADR-207 implementation choice, not a demonstrated fit guarantee.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- idle-dawn-5426 — ADR-205: sourced N20 motor with real-kernel and packaged verification; broader L3 remains open
- floral-stone-2866 — ADR-206: sourced BLDC envelope with qualified interfaces and passing kernel/packaged verification
- southern-moss-9142 — ADR-207: measured L12 mounting disagreement; source precedence selected, implementation still open
