---
node_id: 26d5d4b5-7ef3-5cdc-ac2e-f6231bbddab0
slug: first-moss-9524
title: 'The worker computes an exploded view itself; CommandCreateView leaves the engine''s authoring path (ADR-197): Phase 8''s non-mechanical item resolved'
created_at: '2026-09-06T11:16:29+00:00'
parents:
- fierce-moss-6382
summary: ''
---
## What

Resolved the exploded-view import in `cadex_assembly_worker.py` — Phase 8's one "non-mechanical" item and a named nt1 done criterion. `_execute_native_exploded_view` is now `_execute_exploded_view`: the worker computes FreeCAD's exploded-view rule itself (`ExplodedView._calculateExplodedPlacements`, ported) instead of instantiating `CommandCreateView`'s `ExplodedView`/`ExplodedViewStep` proxies on candidate document objects and reading placements back out of a private method once per move. The `native_readback` block leaves the `cadex-assembly-exploded-view-v1` data (nothing read it; the publisher's keys are unchanged, so the schema tag stays). ADR-197. A new real-kernel lifecycle test pins the radial rule from wire data only. ROADMAP Phase 8 item ticked; `docs/FREECAD.md` §5 question closed.

The audit changed the premise: `src/Mod/Assembly/CMakeLists.txt` installs `CommandCreateView.py` outside its `if(BUILD_GUI)` blocks, so deleting `src/Gui` never would have removed it. The real thing was the shape — the engine's authoring path leaning on a `Command*` module for forty lines of arithmetic. The publisher (`CadexScriptedDomainPublication.py`) still imports the module to build the native document object, which is what a published view *is*; that import is not a Phase 8 obstacle and is left alone.

## Why

Target: `round-glacier-2865` (inherited-tree reduction), the negative-knowledge line "the deletion is not mechanical: cadex_assembly_worker.py imports GUI-lineage code" and mission item 3's criterion "the exploded-view import is resolved, or a record node says why not". The lifecycle frontier on `calm-peak-5247` closed with `fierce-moss-6382`, and the file-lifecycle criteria were met before this run, so item 3 held the smallest open unit. Chosen over the Cycles delete commit because it needs no shell build and no inherited-tree edit — ADR-149 had already named the port as the eventual out. Assumptions written here: the native leader-line quirk (the start is the *solved* bounding-box centre in every move a component reappears in) is kept rather than fixed, because the shell interpolates those lines; and the schema tag is not bumped for dropping an unread diagnostic block.

Iterations #75–#81 of this run landed nothing but the session-limit message (the overseer's "same error three times"); that path was the quota, not code, and it had reset by this iteration.

## Method

Read the worker's function, `CommandCreateView`'s calculation and `UtilsAssembly.getObject`/`getComAndSize`/`saveAssemblyPartsPlacements`, the publisher's use of the data, the Assembly CMake install list and the ADR-047/ADR-149 history. Captured a baseline display record from the unmodified engine over raw NDJSON (a normal move, a radial move on both components, a second normal move), ported the calculation, re-ran the probe, and compared every float to 1e-12. Added `test_cadexd_exploded_view_radial_move_is_freecads_arithmetic` (asserts end − start = (start − centre) × 4d/diagonal for both leader lines and the same push on the poses, from wire data only — no radial move had ever run under a real kernel in a test), dropped the fixture's `native_readback` line in the surface-architecture test, wrote ADR-197, ticked the ROADMAP item, closed the FREECAD.md §5 question and moved its date. Gates: `pixi run test-engine` and `pixi run python -m pytest cli/tests`; both resolve the engine from the source tree, so no build was needed.

## Result

Commit `33dad035`. `pixi run test-engine`: **1967 passed, 52 skipped, 1 failed** in 271 s — the failure is `test_nothing_from_the_analysis_tree_reaches_a_staged_payload`, which found `bin/ccx` in a *half-staged* `build/engine` payload (no `cadex-engine.json`, an unpruned `bin/` of 918 entries, directory mtime 08:43, after the last real commit at 08:38): an aborted `stage-engine`, not this change. Re-running `pixi run stage-engine` produced a proper payload (manifest, four binaries, 2.4 GB) and the test passes on it. `pixi run python -m pytest cli/tests`: **117 passed** in 95 s. Packaged gate (`CADEX_ENGINE_ROOT=<payload> pytest test_cadexd_lifecycle.py`): **15 passed** — but that payload carried the *pre-port* worker, because staging copies the installed engine; so this unit spent its one build: `pixi run build-engine` (install only, no C++ change), `pixi run stage-engine` again, and the packaged gate on the payload that now carries `_execute_exploded_view` and no `CommandCreateView` import: **15 passed**; the analysis payload test passes on it too. The tree is clean.

Probe: before and after the port, identical display records — 3 stages, 4 leader lines, bounds and final poses — to 1e-12, radial move included. The worker's `CommandCreateView` import is gone; the publisher's remains by decision. No protocol op changed, no golden moved, no `shell/` diff, no inherited-tree edit, no build.

Found on the way and owed: **ADR-196 has no entry in `docs/DECISIONS.md`.** The Cycles disable commit (iteration #55, `70591c1e`) cites it from `docs/BLENDER-TREE.md`, `docs/ROADMAP.md` and `package/app/build_app.sh`, but the log stops at ADR-195 before this one. The next inherited-tree unit should write that entry before the Cycles delete commit. Unreconciled tail after this node: two.

Dispatch closed: 1 unit — the worker computes an exploded view itself and no longer imports `CommandCreateView` (ADR-197); Phase 8's non-mechanical item resolved; radial rule pinned under a real kernel.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: 33dad035689d6c7c0f6cc87f85e4669236b8b84a

## State Impact

- target: round-glacier-2865 — the Phase 8 negative-knowledge line is retired: cadex_assembly_worker.py no longer imports CommandCreateView (ADR-197, 2026-09-06); the module installs regardless of BUILD_GUI, and only the publisher still imports it to build the native document object, which deleting src/Gui does not touch. Phase 8's one non-mechanical item is resolved; the delete commit is mechanical again. Owed: ADR-196 (the Cycles disable, iteration #55) has no DECISIONS.md entry yet
- target: forest-wind-0342 — the assembly worker computes exploded views itself (FreeCAD's rule ported, ADR-197), byte-equivalent to the native readback to 1e-12 and pinned by a real-kernel radial test; the native_readback block left the exploded-view data; no protocol change
