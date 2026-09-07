---
node_id: 718ffd8e-ce94-5d1a-8535-ba1fdb377f7c
slug: idle-tower-1624
title: Compound mechanisms exist as parametric library values
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion: **Compound mechanisms exist as parametric library values** built from catalog parts: a rack and pinion and a planetary gearbox at least, each with a mesh and clearance test. Declared target `gap-compound-mechanisms-exist-as-parametric`; the node becomes working only with evidence that the whole criterion is met [rec: empty-wolf-3962].

**Involute gear and rack exist as library values (ADR-233):** `lib.spur_gear` and `lib.rack` over `CadexCatalog.gear_spec`, one involute generator shared by both, provenance ISO 53 (basic rack profile) and ISO 54 (preferred modules). Verified on the source tree, one rebuilt engine and a fresh staged payload: full engine suite 2050 passed / 52 skipped; fresh packaged lifecycle/library gate 107 passed, no skips. `pixi run gate` and ctest were not run because no `shell/` or C++ line changed [rec: wild-beacon-4213].

**Rack and pinion composed (ADR-234):** `lib.rack_and_pinion` builds the ADR-233 gear and rack as one two-solid compound at the standard centre distance, with backlash realised as a radial shift of `backlash/(2 tan 20°)` and any phase reachable through `rotation_degrees` (pinion turns, rack slides the matching travel). `CadexCatalog.rack_and_pinion_spec` carries centre distance, root clearance, travel per revolution and per degree, rack length and nested member specs. Real-kernel mesh test: zero common volume at nine phases for three configurations (m2z20r10 backlash 0, m1z24r12 backlash 0.05 bore 4, m2z20r10 backlash 0.2 bore 6); tip-to-root clearance 0.25 m plus the shift both ways; flank gap equal to backlash·cos 20°/2 within chord sag (at most 4.5e-4·m). Two negative controls collide as required: a half-pitch rack slide (182.0 mm³) and an unshifted z12 pinion (0.061 mm³, the ADR-233 undercut warning now measured). Full engine suite pre-build 2061 passed / 52 skipped (the single failure was the cadexd publication test against the not-yet-rebuilt engine and passed after the build); fresh packaged lifecycle/library gate 119 passed, no skips [rec: mellow-garden-0940].

**Remaining:** the planetary gearbox (sun, planets, internal ring from the same generator, carrier) with mesh and clearance tests is the last open half of the criterion [rec: mellow-garden-0940]. Judgement: the criterion stays `open` until it lands, because the charter names both mechanisms.

## Negative knowledge

- [scope: ADR-233/234 gear, rack and rack-and-pinion values | confidence: high | evidence: wild-beacon-4213, mellow-garden-0940] These are geometric mesh and clearance proofs only: no strength, torque, load, stiffness or efficiency rating, no helical or profile-shifted teeth. Backlash is bounded to 0.1 module and is a radial shift, not tooth thinning. Tooth counts below 17 undercut; the z12 control interferes at phase 0.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- wild-beacon-4213 — ADR-233 gear and rack slice verified on the full suite, real kernel and fresh payload (2050/52, 107/0)
- mellow-garden-0940 — ADR-234 rack and pinion composed with real-kernel mesh and clearance evidence (2061/52, 119/0); planetary remains open
