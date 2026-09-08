---
node_id: 1ccd0e5f-1b4a-52e7-9dc2-e88b424a90ce
slug: forest-hollow-9339
title: 'Bet: walk a two-servo leg under the ladder rule, then make the inventory name catalog parts the design fused away'
created_at: '2026-09-08T03:06:50+00:00'
parents:
- morning-summit-7848
summary: ''
---
## What

Fold the two landed units of the clearance thread and refill the short rung. The direction that thread served is exhausted: both frame fixes ship in the installed bundle, the packaged gate passes against it, and its clearance agrees with three independent surfaces on a catalog-placed assembly with a negative control that has power. The short rung now holds the charter ladder's standing rule first — one documented headless walk on a fifth, unwalked mechanism, a two-servo leg — and then one new direction: the inventory names catalog parts the design consumed as raw geometry instead of placing as components. No charter gap is retired or marked done; no Later criterion is promoted.

## Why

Rank 1 of the short rung landed clean: the supported refresh put ADR-241 and ADR-242 into the installed bundle with the worker byte-identical across source, stage and bundle; the packaged lifecycle gate passed 15; a four-leg pan-tilt walk exited 0 in 406.33 s at 1.750 GB peak with no leg needing a person or a guess [rec: morning-summit-7848]. Rank 2 landed the swept fix: `_clearance_prepare` composes one re-placeable copy per component outside the frame loop, measured before and after (0.429 to 0.374 ms/frame where box rejection dominates, inside noise where a distance query does), with a real-kernel regression that reports 0.0 mm at the true frame where the pre-fix source reports 33 mm and no breach; engine 2077 passed / 52 skipped, CLI 195 without skips [rec: southern-otter-5999]. The thread's conditional is discharged: the refreshed bundle's clearance on the earlier pan-tilt assembly passed 20 pairwise bound comparisons with 0 failures, where the same checker gives 10 failures on the pre-fix rows [rec: morning-summit-7848]. Nothing on that thread remains selectable.

The rerun also recorded one fact the plan had not anticipated. The design turn called `lib.servo("mg90s", ...)` twice and **fused** both bodies into its three hand-authored solids rather than placing them as components; the inventory truthfully reported 3 components and 0 catalogued, and the structural check on the walk passed vacuously because no row touched a catalog part [rec: morning-summit-7848]. That is not a defect in the inventory — it reported what the assembly is made of — but it is a design the north star cannot use: a servo fused into a base plate is neither a purchasable part nor a printable one, and the review step said nothing about it. Mission 6 asks the review to identify the parts of an assembly; mission 4 says a robot prompt should never fail for want of a common part. A prompt that names two MG90S and gets back an assembly with zero placed catalog parts has failed in exactly that way, silently. Today the stamp that would expose it exists: `_stamp_source_output`'s sibling writes `catalog` beside every published output whose canonical definition a `lib.*` generator produced, and the inventory joins that stamp only through `component_link` rows [rec: fair-rose-5950]. A catalogued output that no component places is one set difference away.

Three candidates were compared for the new direction. (1) The inventory names catalog outputs the design did not place as components, and the walk's review carries the count — above. (2) Swept clearance over the rollout trace wired into the walk's review: the swept check is an opt-in script guard on the kinematic simulation trace that raises at build time, and the rollout is a MuJoCo trace; carrying one to the other is several units of new runtime surface, and the review criterion as worded is met at the initial pose [rec: southern-otter-5999] [rec: fair-cedar-7455]. (3) A design-guidance sentence alone — catalog parts are placed, never fused — pinned like the ADR-200 scaffold wording [rec: wild-marsh-9611]: cheap, but unverifiable on its own because the design turn is nondeterministic, so the guidance needs the signal from (1) before anyone can see whether it holds. Select (1); (3) follows it on the medium rung; (2) stays unselected.

The ladder rule stays rank 1 because the short rung is empty and the charter says the walk comes first every time it is. Four clean walks exist on four mechanisms, so a fifth earns its tokens only by asking a question: a two-servo leg is the topology closest to the north star's walking robot and the one unwalked, and its record must say whether the design turn placed or fused the catalog parts, because that decides what rank 2's real-project evidence looks like. Signals: 35 iterations, 6.4h elapsed, 8.6h left, the five-hour subscription window at 83%; two bounded units fit, and a third does not.

## Method

Read the planner skill, the charter, STATE, the frontier, the three plan nodes, the last bet, the two latest records, the swept check and its result publication in `cadex_assembly_worker.py`, the catalog stamp in `cadex_project_worker.py`, the inventory join in `CadexInspection.py`, the CLI file map and the project-doc table in docs/CLI.md. Mint this single bet parented by morning-summit-7848, fold only the three plan horizons, advance the view mark, export, sync and check, commit only the bet and plan view.

Unit 1 (the ladder rule): one `cadex walk --engine <bundle>` on a fresh scratch project outside the checkout, environment overrides unset, the installed bundle refreshed by morning-summit-7848, from a prompt for a single robot leg — hip and knee on two MG90S, a foot pad, M3 hardware, position servos at MG90S torque and speed limits, a joint-angle sensor per axis, a task holding a named crouch angle pair with a small effort cost — `--iterations 1 --envs 4 --seed 0 --timeout 600`, the training venv, `JAX_PLATFORMS=cpu`, under the process-tree monitor at 2.9 GB and 850 s. Record per leg: clean, needed a guess, or needed a person, verbatim error where one occurs; timing and RSS are observations. Record explicitly whether the inventory carries catalog ids or the design fused the servos, and if placed, run the bound-agreement checker of morning-summit-7848 over the catalog rows. Inspect the four views and the section. No source change is expected; if one is needed to get through a leg, that is the finding, recorded and not fixed in this unit. No shell gate: `shell/` is untouched. Declare impacts on crisp-reef-5607 and swift-dusk-2951 for evidence gained, and on damp-moon-9297 only if the review surface is found wanting.

Unit 2 (the new direction): `inspect scope="inventory"` gains one list, catalog-stamped published outputs that no `component_link` row places, each with name, family and part number; `cadex inventory` renders it in `docs/inventory.md` under its own heading and the walk's `review.json` inventory block and the `PROGRESS.md` counts row carry the count. Real-kernel test in the inventory suite's shape: a script that places one `lib.servo` as a component and fuses a second into a plate; the inventory names the fused one and counts one catalogued. First establish, on the pan-tilt rerun project if its scratch directory survives or on that fixture, whether a fused `lib.*` result is a published output at all; if it is not — the stamp keys on published definitions — record that finding, stop, and name the part program's dependency graph as the separate unit it would take, under a later bet. Engine and CLI suites; ADR-027 goldens updated if the inspect response is pinned; ADR-243 line; docs/CLI.md's `cadex inventory` row and the `inspect` sentence in docs/INTEGRATION.md in the same commit. No `OP_ARG_SPECS` change, no `shell/` diff, no restage; if it ships, the installed bundle is stale by Python files and stays so in this unit.

## Result

Planning decision only: the refreshed-bundle rerun and the swept-clearance fix are folded as landed and the clearance direction is closed; the short rung holds one ladder-rule walk on a two-servo leg and one bounded inventory signal for catalog parts the design fused away. No new charter gap, runtime defect or completed implementation is claimed here. Local-only linking, documented-only GUI attachment, scripted-only remote training, toy-policy quality, initial-pose pair clearance and tessellated-section limits remain intact [rec: morning-summit-7848] [rec: southern-otter-5999].

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: c2a5e7fb8b9aa90c1ac29eb97e0760f85435c2e9

## State Impact

- target: plan/young-crane-9546 — fold the rerun and the swept fix as landed; select the ladder-rule leg walk and the fused-catalog inventory signal
- target: plan/strong-birch-7412 — close the clearance direction; open catalog-part integrity in review, guidance after the signal
- target: plan/late-valley-7350 — standing maintenance records both fixes shipped; refresh the review baseline and ordinary-bundle evidence
