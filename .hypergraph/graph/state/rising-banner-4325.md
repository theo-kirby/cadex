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

Reconcile judgement: status remains `open`: this closes the N20 subitem only. BLDC, linear actuator, solenoid, joints and compound gearing remain outstanding [rec: idle-dawn-5426].

## Negative knowledge

- [scope: Pololu #2367 catalog model | confidence: high | evidence: idle-dawn-5426] External envelope and mounting details include documented approximations; manufacturer stall ratings do not establish continuous torque, thermal performance or physical inertia. Packaged tests used a local development payload, not a portable release.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- idle-dawn-5426 — ADR-205: sourced N20 motor with real-kernel and packaged verification; broader L3 remains open
