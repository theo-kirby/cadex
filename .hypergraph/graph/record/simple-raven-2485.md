---
node_id: 4425c1e6-080c-5b66-88aa-f372142f5f62
slug: simple-raven-2485
title: 'Bet: show the clearance fix through the walk, then close its swept sibling'
created_at: '2026-09-08T02:15:16+00:00'
parents:
- light-timber-5868
summary: ''
---
## What

Fold the two landed units of the ladder-rule direction and refill the short rung with two units on the same thread. Unit 1 completes the plan's own conditional: refresh the installed bundle by the supported route so it carries ADR-241, then run the same pan-tilt walk once end to end against it and cross-check the clearance rows against the exported STL bounds. Unit 2 closes the one defect ADR-241 named and left: `_clearance_at_frame`, the swept clearance inside the simulation trace, still measures `lib.*`-placed bodies in their authored frame; fix it with the cost measured first and a real-kernel regression that fails on the old source. No charter gap is retired or marked done; no Later criterion is promoted.

## Why

Rank 1 of the short rung landed clean: the pan-tilt head on two catalog MG90S went through design, train, declare, rollout and review with no leg needing a person or a guess, 371.70 s wall and 1.419 GB peak, and the run named one leg — the review surface's clearance numbers were false for catalog parts [rec: empty-banner-7438]. Rank 2 landed the fix: `_component_world_shape` composes the component placement with the shape's own, pinned by a real-kernel regression that fails on the old source, engine 2076 passed / 52 skipped, CLI 195 without skips, and the pan-tilt assembly's numbers came back exactly as the four independent surfaces predicted, with three hidden contacts revealed [rec: light-timber-5868].

Two things from that record are still open, and both are cheap and on this run's frontier criterion `damp-moon-9297`. First, the rank-2 unit as written was "close that one leg, then rerun the same walk once to show it" [rec: salty-nest-8235]; the fix was shown by regenerating the review leg from the dev tree, not by the walk, and the installed bundle was neither rebuilt nor restaged, so a walk run with `--engine <bundle>` still reports the pre-fix lies [rec: light-timber-5868]. The charter ladder's standing rule for an empty short rung is to run the documented walk end to end on this machine; the supported refresh route is known and cheap — one incremental shell build and the install script, no engine rebuild, the engine was built by the fix unit [rec: strong-raven-3067] [rec: light-timber-5868]. Second, ADR-241 explicitly left `_clearance_at_frame` with the same frame defect because it runs per pair per frame and the cost of composing there was unmeasured; until it lands, a swept breach distance for a catalog-placed body is not to be believed [rec: light-timber-5868]. That is an existing product surface publishing a false number, not new surface — the reason the earlier planner declined swept-pose work (it added runtime surface the charter does not ask for) does not apply to correcting a surface that already ships [rec: salty-nest-8235]. The shape's own placement is constant across frames, so one composed copy per component made once outside the frame loop and re-placed per frame costs one placement multiply per pair per frame, the same order as the attribute read it replaces; the actor measures that rather than trusting it. No test in `cadex_tests` names `_clearance_at_frame` today, so a real-kernel regression in the ADR-241 shape is the gate.

Three candidates were compared for the refill. (1) The rerun plus the swept fix, above. (2) The three real contacts the corrected clearance revealed on the pan-tilt project (pan servo in yoke, tilt servo in yoke arm and head plate): that is the project's design business, the iterate criterion is already ticked, and a design turn costs tokens for no criterion [rec: light-timber-5868]. (3) A cheap inherited-tree removal: none is obvious; the audits left only retained residue [rec: autumn-arrow-3125]. Select (1). Order: the rerun first, because the ladder puts the walk first and its result is independent of the swept fix; the swept fix second, on the dev tree, under the engine gate, with no second refresh required — the walk's design turns do not declare simulation clearance pairs, so the swept path is exercised by its regression, not by the walk. Signals: 33 iterations, 5.5h elapsed, 9.5h left; two bounded units fit with room for the maintainer pass.

## Method

Read the planner skill, the charter, STATE, the frontier, the three plan nodes, the last bet, the two latest records, ADR-241, `_clearance_at_frame` and `_component_world_shape` in `cadex_assembly_worker.py`, the walk section of docs/CLI.md and the refresh record. Mint this single bet parented by light-timber-5868, fold only the three plan horizons, advance the view mark, export, sync and check, commit only the bet and plan view.

Unit 1: no engine rebuild. `pixi run build-shell` (its dependency runs stage-engine) then `bash package/app/build_app.sh install`, as the refresh record did; confirm the installed `cadex_assembly_worker.py` carries `_component_world_shape`. Packaged lifecycle gate against the refreshed root (`CADEX_ENGINE_ROOT=<bundle> pytest test_cadexd_lifecycle.py`). Then one `cadex walk --engine <bundle>` from the same pan-tilt prompt, fresh scratch project outside the checkout, environment overrides unset, `--iterations 1 --envs 4 --seed 0 --timeout 600`, training venv, `JAX_PLATFORMS=cpu`, under the process-tree monitor at 2.9 GB and 850 s. The design turn is nondeterministic, so the check is structural, not a number match: every clearance row involving a `lib.*`-placed component must agree with the exported STL vertex bounds and the section contours (no common volume on bodies whose bounds are disjoint; any reported volume no larger than the bounds' overlap allows). Record per leg as before; timing and RSS are observations. No shell gate is required: `shell/` is untouched and the bundle's engine change is what the walk exercises. Declare impacts on damp-moon-9297 (the bundle now carries the fix, walk-verified) and crisp-reef-5607 / swift-dusk-2951 only for evidence actually gained.

Unit 2: measure first — time the simulation trace's swept check on an existing traced assembly (the arm or a real-kernel fixture with clearance pairs) before the change. Then fix `_clearance_at_frame` to measure each component where the assembly puts it, composing once per component outside the frame loop and re-placing per frame, or an equivalent the measurement justifies. Real-kernel regression in the ADR-241 shape: a shape-placed `App::Link` component swept past a world-authored one, asserting the breach is reported at the true frame and distance and that a body measured at the origin would not have breached. It must fail on the pre-fix source. Re-measure after; if the swept check slows by more than the measurement's noise, record the number and stop rather than ship it. ADR-242 line, ROADMAP line where the convention asks, engine suite and CLI suite. No protocol, `shell/` or payload change, so no restage. If the fix ships, the installed bundle is stale again by one Python file; record that and do not refresh in this unit.

## Result

Planning decision only: the pan-tilt walk and the pair-clearance fix are folded as landed; the short rung holds one walk rerun against a refreshed bundle and one bounded swept-clearance fix. No new charter gap, runtime defect or completed implementation is claimed here. Local-only linking, documented-only GUI attachment, scripted-only remote training, toy-policy quality, initial-pose pair clearance and tessellated-section limits remain intact [rec: strong-raven-3067] [rec: light-timber-5868].

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: b25f500095b44b5dbb06e189cb3f3156acccadff

## State Impact

- target: plan/young-crane-9546 — fold both landed ladder-rule units; select the pan-tilt rerun against a refreshed bundle and the bounded swept-clearance frame fix
- target: plan/strong-birch-7412 — record the walk and pair-clearance evidence as landed; the direction continues as one rerun and one swept fix, then ends
- target: plan/late-valley-7350 — standing lifecycle maintenance now selects the rerun and the swept fix; refresh the review baseline with the pan-tilt numbers
