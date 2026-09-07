---
node_id: 718ffd8e-ce94-5d1a-8535-ba1fdb377f7c
slug: idle-tower-1624
title: Compound mechanisms exist as parametric library values
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: superseded
## Current

Open charter criterion: **Compound mechanisms exist as parametric library values** built from catalog parts: a rack and pinion and a planetary gearbox at least, each with a mesh and clearance test. Declared target `gap-compound-mechanisms-exist-as-parametric`; the node becomes working only with evidence that the whole criterion is met [rec: empty-wolf-3962].

**Involute gear and rack exist as library values (ADR-233):** `lib.spur_gear` and `lib.rack` over `CadexCatalog.gear_spec`, one involute generator shared by both, provenance ISO 53 (basic rack profile) and ISO 54 (preferred modules). Verified on the source tree, one rebuilt engine and a fresh staged payload: full engine suite 2050 passed / 52 skipped; fresh packaged lifecycle/library gate 107 passed, no skips [rec: wild-beacon-4213].

**Rack and pinion composed (ADR-234):** `lib.rack_and_pinion` builds the ADR-233 gear and rack as one two-solid compound at the standard centre distance, with backlash realised as a radial shift of `backlash/(2 tan 20°)` and any phase reachable through `rotation_degrees`. `CadexCatalog.rack_and_pinion_spec` carries centre distance, root clearance, travel per revolution and per degree, rack length and nested member specs. Real-kernel mesh test: zero common volume at nine phases for three configurations; tip-to-root clearance 0.25 m plus the shift both ways; flank gap equal to backlash·cos 20°/2 within chord sag. Two negative controls collide as required (half-pitch rack slide 182.0 mm³; unshifted z12 pinion 0.061 mm³). Full engine suite 2061 passed / 52 skipped; fresh packaged lifecycle/library gate 119 passed, no skips [rec: mellow-garden-0940].

**Planetary gearbox: qualification stopped at a measured planet–ring interference (ADR-235).** The proposed composition (module 1, sun18/planet18/ring54, three planets, width 6 mm, centre distance 18 mm, ring cut by a virtual external gear) was tested as one bounded experiment at its first phase: sun–planet common volume 0 with minimum gap 0.0024 mm, but planet–ring common volume 0.000354806 mm³ against the 1e-6 mm³ bound, gap 0 — qualified=false. All four root-circle clearances are 0.25 mm within 6e-15, and both half-pitch negative controls collide (23.46 and 41.86 mm³), so the measurement detects bad meshes. A standalone real-kernel probe (`docs/experiments/planetary_mesh_probe.py`, run under `FreeCADCmd -c`) reproduces the number independently of the proposed API, and identically against `git archive HEAD src/Mod/cadex`, so the failure is in the ring composition, not in the uncommitted patch. Chordal cutout error is a candidate cause only, not a diagnosis. No planetary API was published, no engine source changed, no build, stage, full suite or packaged gate was run after the failure. The three pre-existing uncommitted planetary edits (CadexCatalog.py, cadex_library_api.py, test_library.py) were preserved rather than adopted or discarded, together with their pre-existing failure in `test_planetary_spec_numbers` (expects one "radial line" warning, gets three; 12 passed / 1 failed on the targeted selection). Before resuming, that proposal and its test failure must be resolved explicitly; the mesh tolerance is not to be loosened and the current ring profile is not qualified [rec: proud-cliff-9629].

**Remaining:** the planetary gearbox (sun, planets, internal ring from the same generator, carrier) with mesh and clearance tests is the last open half of the criterion, and ADR-235 records the first attempt failing at its first phase [rec: mellow-garden-0940] [rec: proud-cliff-9629]. Judgement: the criterion is not met, because the charter names both mechanisms.

## Negative knowledge

- [scope: ADR-233/234 gear, rack and rack-and-pinion values | confidence: high | evidence: wild-beacon-4213, mellow-garden-0940] These are geometric mesh and clearance proofs only: no strength, torque, load, stiffness or efficiency rating, no helical or profile-shifted teeth. Backlash is bounded to 0.1 module and is a radial shift, not tooth thinning. Tooth counts below 17 undercut; the z12 control interferes at phase 0.
- [scope: the ADR-235 internal-ring composition, m1 sun18/planet18/ring54 at phase 0 | confidence: high | evidence: proud-cliff-9629] Cutting the ring's tooth spaces with a virtual external gear from the existing spur generator gives correct 0.25 mm root-circle clearances but an overlapping planet–ring mesh (3.5e-4 mm³). Only the first phase was measured; no later phase, other tooth count or other module was tried, so this does not show that the approach cannot work — only that this configuration does not.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- wild-beacon-4213 — ADR-233 gear and rack slice verified on the full suite, real kernel and fresh payload (2050/52, 107/0)
- mellow-garden-0940 — ADR-234 rack and pinion composed with real-kernel mesh and clearance evidence (2061/52, 119/0); planetary remains open
- proud-cliff-9629 — ADR-235: planetary qualification stopped at a measured, independently reproduced planet–ring interference; no API published, uncommitted proposal and its test failure preserved


## Superseded

Parked by the operator before nt3 (2026-09-07). The criterion moved to `## Later criteria` in the charter, where it seeds no gap. It is not abandoned: the human promotes it back into `## Done criteria` when the nt3 frontier — the lifecycle walk and the headless review calls — lands or blocks. Reconcile judgement: the ADR-235 experiment [rec: proud-cliff-9629] was recorded on `ouroboros/nt2` before the parking and declared this node "remains open"; its evidence is folded above, but the status stays `superseded` because the operator's parking is the later and higher decision, and the experiment changed no evidence in the criterion's favour.
