---
node_id: 66061199-126a-5243-97c7-46700adbf953
slug: flat-river-8853
title: 'Bet: close the planetary gearbox and open headless review with the assembly inventory'
created_at: '2026-09-07T06:09:04+00:00'
parents:
- mellow-garden-0940
summary: ''
---
## What

Short's first two gear units landed with records and green gates and are reconciled, so rank 3 loses its condition: dispatch `lib.planetary` now as rank 1, exactly as specified in placid-delta-6677. Promote mission 6 from medium into short behind it: rank 2 is the assembly inventory with catalog ids as one CLI call with a project-local output file; rank 3 is the clearance and intersection check naming offending pairs, conditional on rank 2 landing and on the loop signals leaving room for a unit that adds one read op. Medium keeps the remaining headless-review calls (render, section) and every stopped or blocked mission 3 and mission 4 entry unchanged. Preserve every charter gap. No new direction.

## Why

Evidence, not clock, empties the top of short: rank 1 (involute gear and rack, ADR-233) closed with 2050/52 on the full suite and 107/0 on the fresh payload [rec: wild-beacon-4213]; rank 2 (rack and pinion, ADR-234) closed with zero common volume at 27 phase builds, 0.25 m plus shift root clearance both ways, flank gap within chord sag, two negative controls, 2061/52 pre-build and 119/0 packaged [rec: mellow-garden-0940]. The reconcile at 1918ebda folded both into idle-tower-1624 and brave-stone-9609, and STATE names the planetary gearbox as the last open half of the compound-mechanisms criterion. The bet that dispatched the sequence said rank 3 runs only after rank 2 lands with its record [rec: placid-delta-6677]; that condition is met, so the unit is dispatched unchanged rather than re-specified. Its one new construction is an internal-tooth ring from the same generator, which the rack-and-pinion evidence makes cheap to test with the same mesh and clearance shape.

Mission 6 is next because nothing has landed for it and it is the charter's own review step for the walk; the prior bet ranked its first two calls at the top of medium for promotion once the gear units land or are held [rec: placid-delta-6677]. Verified premises this pass: `LibraryPart` already carries `family` and `part_number` on every library value, and `assembly.component` links a `source` mapping to another domain's output, so the inventory needs the part domain to publish catalog identity on library outputs and an `inspect` scope to walk components back to their sources; `inspect` takes `scope` as a string argument, so a new scope is an argument value inside the existing op and needs no `OP_ARG_SPECS` change. The only clearance check today is the declared swept clearance validated at rebuild (ADR-130), so a pair-naming check needs one read op with its INTEGRATION.md row, shell client update and response golden in one commit; that is a bigger unit and is ranked last and conditional. Both are argument-level or single-op changes that fit the charter's remove-more-than-we-add bar only because they are existing done criteria, not new directions.

Budget: 66 iterations in 10.7 h leaves 4.3 h, about two to three work units after maintainer and planner passes. Three ranks, the third conditional, is the right size: the planetary is one unit with one build; the inventory is one unit; the clearance op fits only if both land quickly. Mission 3 stays in medium with no qualified candidate [rec: proud-moon-9023] [rec: cold-clover-8123] [rec: autumn-arrow-3125]; the stopped servo, motor and accessory searches stay stopped [rec: hidden-ridge-7342] [rec: steady-reef-0162]. No charter gap is retired, blocked or superseded by this pass.

## Method

Rank 1, planetary. `lib.planetary(module, sun_teeth, planet_teeth, planets, face_width)`: internal ring from the ADR-233 generator with ring teeth = sun + 2·planet, refuse (sun + ring) not divisible by the planet count with a diagnostic, planets equally spaced at the sun–planet centre distance, a plain carrier plate, the fixed-ring ratio 1 + ring/sun in the spec, one compound placed like every other library value; `CadexCatalog.planetary_spec` derives the numbers the way `rack_and_pinion_spec` does. Mesh and clearance tests for one sun–planet pair and one planet–ring pair in the real-kernel shape of ADR-234, with at least one negative control. Docs in the same commit: ADR-235, PROVENANCE §8g, L3-COVERAGE, ROADMAP, XSCRIPT; the `describe_api` golden only if the family listing moves. Gates: full engine pytest, at most one `pixi run build-engine`, `pixi run stage-engine` finished before the fresh packaged lifecycle/library gate. One work record with impacts on idle-tower-1624 and brave-stone-9609; a passing planetary closes the compound-mechanisms criterion and the record says so.

Rank 2, assembly inventory. Dispatched after rank 1's committed record. The part domain publishes `family` and `part_number` on library-value outputs; a new `inspect` scope walks an assembly output's components to their sources and returns the placed parts with catalog ids, placement and source output name; `cadex` exposes it as one CLI call that writes the inventory into the project directory (a documented path and filename, JSON plus a short Markdown table), and `docs/CLI.md` gains the row in the same commit. Tests: stubbed protocol coverage for the scope, a real-kernel test that assembles two library values and reads the inventory back with both ids, and the packaged lifecycle gate after a finished stage. Not authorized: an `OP_ARG_SPECS` change, a shell change beyond none, a walk or scaffold change. If the walk's review step is to use it, that is a later unit that carries `project_docs.py` and its test together [rec: wild-marsh-9611].

Rank 3, clearance and intersection check, conditional. Only after rank 2 lands with its record and only if the loop signals leave room. One read op that takes an assembly output and returns the pairs of placed solids whose common volume exceeds a tolerance or whose minimum distance falls below a declared clearance, named by component label and catalog id; INTEGRATION.md row, `OP_ARG_SPECS`, shell client update and response golden in the same commit (methodology rule 6); `cadex` writes the report into the project directory. Real-kernel test with one interfering and one clear pair; packaged gate after a finished stage. If the budget does not allow it, it returns to medium with this specification.

Not authorized in any unit: new dependencies, helical or profile-shifted teeth, torque or strength ratings, dynamics coupling claims, render or section views, resuming any stopped servo, motor or accessory search. Report omitted checks honestly; a failing mesh test holds the next rank rather than widening it.

This bet is parented to mellow-garden-0940. Fold all three horizons, keep negative knowledge and provenance, advance only the plan high-water mark, export, check, sync and commit plan artifacts. No edits to records, state, STATE.md, the charter, product code or ADRs in this pass.

## Result

Decision: short becomes planetary (unconditional), assembly inventory, then the conditional clearance op. Medium's headless-review entry now holds only render and section, waiting on headless-renderer evidence; its reduction, accessory, catalog-breadth, residual GUI and L3 entries are unchanged except to record the rack and pinion as landed. Long records that the compound-mechanisms criterion is one unit from closure and that mission 6 is dispatched. All charter gaps remain represented; zero new directions; no implementation or test evidence is claimed by planning.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 1918ebda78f97056877543d1d2e9f7d016aba9e0

## State Impact

- target: plan/young-crane-9546 — planetary becomes rank 1 unconditional; assembly inventory and conditional clearance op promoted from medium
- target: plan/strong-birch-7412 — headless-review entry reduced to render and section; rack and pinion recorded as landed
- target: plan/late-valley-7350 — compound mechanisms one unit from closure; mission 6 dispatched
