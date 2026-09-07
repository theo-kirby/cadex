---
node_id: 06b3c053-0a58-5078-9536-ae29198bd741
slug: placid-delta-6677
title: 'Bet: deliver involute gearing toward the rack-and-pinion and planetary criterion'
created_at: '2026-09-07T05:19:14+00:00'
parents:
- autumn-arrow-3125
summary: ''
---
## What

Both updater units landed as separate commits and are reconciled, so short is empty. Promote mission 4's compound-mechanisms criterion (idle-tower-1624, brave-stone-9609) from long into short as three sequential bounded units: (1) one involute profile generator shared by external, internal and rack teeth, delivered as `lib.spur_gear` and `lib.rack` over a `CadexCatalog` gear-standard table with real-kernel tests; (2) `lib.rack_and_pinion` composed from those values, with a mesh test and a clearance test, plus the packaged lifecycle gate; (3) conditionally, `lib.planetary` (sun, planets, internal ring, carrier) with the same test shape. Rank the first two headless-review capabilities (assembly inventory with catalog ids; a clearance/intersection check naming pairs) at the top of medium for the next pass. Preserve every charter gap. No new direction.

## Why

Short is exhausted by evidence, not by clock: the disable commit 95c1286d and the delete commit 25445f70 both carry records with gates, and STATE reconciles through the delete. [rec: green-stone-3882] [rec: autumn-arrow-3125] Mission 3 has no qualified candidate left: the surviving-diff set, the Test tree and the updater are audited, and the recorded negative knowledge requires new qualifying evidence before another audit. [rec: proud-moon-9023] [rec: humble-tide-6752] [rec: cold-clover-8123] Mission 4 is therefore the highest-ranked mission with open, unstopped work. Its sourced searches are stopped (fifth servo, BLDC set A, manufacturer accessories), but compound gearing was never dispatched: the L3 coverage audit names gears and rack-and-pinion as a separate slice with no library values and no mesh/clearance evidence, and ROADMAP's open L3 line says involute profiles are their own slice. [rec: steady-rain-3009] [rec: hidden-ridge-7342] [rec: mild-harvest-8460] [rec: steady-reef-0162]

This slice can land where the sourced searches stopped because its provenance is a standard, not a vendor download: ISO 53 (basic rack profile: 20 degree pressure angle, addendum 1.0 m, dedendum 1.25 m, root clearance 0.25 m) and ISO 54 (preferred modules). No archive access, no licence question and no dimension conflict can block it; the only risk is geometry construction, which the real kernel tests directly. L0 already delivers fasteners and bearings the same way, so the charter's bearings and M2 to M5 rows are met and the remaining catalog-breadth gap is servo and actuator count, which stays stopped. The charter's exhaustion rule (remove more than we add) governs new directions; this is an existing done criterion, so additive code is authorized, and the bet bounds it: one profile generator, no new dependency, no protocol op change (lib is script namespace; the `describe_api` golden already covers catalog families), no shell change.

Budget: 63 iterations in 9.9 h leaves about a dozen work iterations in the remaining 5.1 h after maintainer and planner passes. Three units with at most one build each fit; the third is conditional and may be cut by the next pass. Mission 6 is next because nothing has landed for it: the assembly API carries no catalog identity on placed components, so an inventory needs the library to tag placed parts first, and the only clearance check today is the declared swept clearance validated at rebuild (ADR-130), so a CLI check will likely need a new op and its INTEGRATION.md row. Both are separate units and are ranked, not dispatched.

## Method

Unit 1, gear values. `CadexCatalog.py` gains a small gear-standard table (ISO 53 profile constants; the ISO 54 series 1 modules actually accepted) and `gear_spec`; `cadex_library_api.py` gains `spur_gear(module, teeth, face_width, *, bore=None)` and `rack(module, teeth, face_width, height)` built through the existing part API from one involute generator (sampled involute flanks joined by tip and root arcs into a closed face, then extruded). Refuse tooth counts below a documented minimum and record the undercut limit below 17 teeth in `spec["approximate"]`; the spec carries module, tooth count, pitch, base, root and tip diameters, pressure angle, tooth thickness at the pitch circle and the source citation. Tests in `test_library.py`: stubbed construction and listing (new exports and a `gears` family), and the actual-worker real-kernel shape used for N20 and the joint, asserting a valid single solid, tip diameter m(z+2) and root diameter m(z-2.5) within tolerance, volume between the root and tip cylinders, rack pitch pi times m and rack tooth height 2.25 m. Docs in the same commit: PROVENANCE 8g standard citation, L3-COVERAGE row, ROADMAP line, one ADR (next free number). Gates: full engine pytest, at most one `pixi run build-engine`, then `pixi run stage-engine` finished before the fresh packaged lifecycle gate because Python under `src/Mod/cadex/` is payload. One work record with real impacts on idle-tower-1624 and brave-stone-9609.

Unit 2, rack and pinion. Dispatched only after unit 1's committed record and green gates. `lib.rack_and_pinion(module, pinion_teeth, rack_teeth, face_width, *, backlash=0)` returns a compound of the two named solids placed at the standard centre distance (pinion pitch radius above the rack pitch line) with the spec carrying centre distance, travel per revolution and the datums. Mesh test: real-kernel common volume of pinion and rack below tolerance at five or more rotation phases with the matched rack translation. Clearance test: root clearance 0.25 m measured between tip and root, and minimum flank distance within the declared backlash bound. Same gates, docs and record shape as unit 1; packaged gate after a finished stage.

Unit 3, planetary. Dispatched only after unit 2 lands. `lib.planetary(module, sun_teeth, planet_teeth, planets, face_width)`: internal ring from the same generator with ring teeth = sun + 2 planets, the assembly condition (sun + ring) divisible by the planet count refused with a diagnostic, planets equally spaced at the sun-planet centre distance, a plain carrier plate, and the fixed-ring ratio 1 + ring/sun in the spec. Mesh and clearance tests for one sun-planet pair and one planet-ring pair, same gates, docs and record.

Not authorized in any unit: helical or profile-shifted teeth, torque or strength ratings, dynamics coupling claims, walk or scaffold changes, protocol op changes, shell changes, new dependencies, or resuming any stopped servo, motor or accessory search. Report omitted checks honestly; a failing mesh test holds the next unit rather than widening it.

This bet is parented to autumn-arrow-3125. Fold all three horizons, keep negative knowledge and provenance, advance only the plan high-water mark, export, check, sync and commit plan artifacts. No edits to records, state, STATE.md, the charter, product code or ADRs in this pass.

## Result

Decision: short becomes the three gear units above, in order, the third conditional. Medium leads with the two headless-review units ranked for promotion, then the unchanged reduction, accessory, catalog-breadth, residual GUI and L3 entries. Long records that compound gearing is now dispatched and that mission 6 is next. All charter gaps remain represented; zero new directions; no implementation or test evidence is claimed by planning.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 9c61a287bd0b19df350cc82c208b19fa0324115d

## State Impact

- target: plan/young-crane-9546 — replace the landed updater pair with three sequential gear units, the third conditional
- target: plan/strong-birch-7412 — rank the two first headless-review units at the top; record the updater pair as complete
- target: plan/late-valley-7350 — mark compound gearing as dispatched and mission 6 as next; refresh delta totals
