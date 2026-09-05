---
node_id: 671fa7ba-135b-5817-b2bd-220f59fcca78
slug: twilight-isle-0370
title: Hydrate the model on file open (ADR-186)
created_at: '2026-09-05T22:19:48+00:00'
parents:
- misty-pond-0507
summary: ''
---
## What

Opening a `.blend` beside an existing `.cadex` now hydrates the model (ADR-186). `load_post` → `on_file_changed` (unchanged) → `cadex_backend.queue_open`: for a saved file whose project directory exists, the open is queued and a timer-driven pump — the drag and refine pumps' shape — runs the restore-verified `open_project` and the display `rebuild` on a worker thread, hydrating on the main thread. `ensure_open` drains a queued open for its root before doing anything else, so a tool call racing the queue never issues a second `open_project`. A failed open lands in the parameters panel's alert row, as a chat status line, and as `open_failure_code` on the per-root `_State` — the hook the lockout re-accept box (the next unit) needs. Gate test `test_opening_a_file_hydrates` drains the queue by hand and asserts `model_objects_on_open > 0`; the number lands in the gate report with `hydrate_on_open_seconds`.

Files: `shell/scripts/startup/mesh_agent/cadex_backend.py` (`_adopt_open` shared by both openers, `_opens`/`queue_open`/`pending_open`/`open_now`/`_open_pump`/`_finish_open`, `close_all` clears the slots, `_State.open_failure_code`), `shell/scripts/startup/mesh_agent/__init__.py` (one guarded call in `_load_post_handler`), `shell/tests/python/bl_mesh_agent_cadex.py` (the test and its workdir), `docs/DECISIONS.md` ADR-186, `docs/ROADMAP.md` (the "Later" item becomes a ticked landed item), `docs/ARCHITECTURE.md`, `docs/BLENDER.md`.

## Why

Ouroboros run nt1, iteration 2, the first work unit. Target: the goal's priority 1 (file lifecycle, `simple-willow-8989`, status broken) and the first rung of its horizon ladder: hydrate on open with a test. ADR-073 measured `model_objects_on_open = 0` in the shipped bundle and named three reasons the one-line fix was wrong; each is answered in ADR-186 §1 rather than waved off. Assumptions taken alone (question policy: the reversible option): Save-As does NOT queue an open (saving model A over `b.blend` beside a `b.cadex` would otherwise repaint the viewport with model B on the spot — the pre-existing derived-root semantics stay where the next request finds them); an unsaved scene's temporary root never queues (`bpy.data.filepath` guard — it is keyed by scene name and survives File > New); `ensure_open` ignores the outcome of the open it drained, because a failed queued open is exactly where the caller wants its own report and, for `write_script`, its own `restore: False` reopen.

## Method

Read the state node, ADR-073, the `load_post` handler, `on_file_changed`, `ensure_open`, `Lifecycle`, the drag/refine pumps and the four existing gate tests that call `open_mainfile`. Refactored `ensure_open`'s adoption step into `_adopt_open` so the pump and the synchronous opener share one meaning of "opened". Built the pump as three phases (queued → opening → rebuilding) with the drag pump's project-still-current rule at every step; `rebuild` reuses `Lifecycle` unguarded, exactly as `begin_rebuild_model` does. Wrote the gate test to (a) prove File > New does not queue against the unsaved temp root, (b) reopen a saved file in a fresh session, delete the baked objects, drain, and count BREP objects, (c) check the restore pass ran and matched and the sliders came from the engine, (d) prove `ensure_open` keeps the child, and (e) race a `set_params` against a fresh queue. Ran `pixi run gate` (the full `bl_mesh_agent_cadex.py` suite against the built bundle, add-on from source) and the engine's licensing test.

## Result

`pixi run gate` (full `bl_mesh_agent_cadex.py` suite against the built bundle, engine from the bundle, add-on from source): **OK, exit 0, 1113 checks ok, 0 FAIL**. Gate report: `model_objects_on_open = 1` (the baseline plate, after the baked objects were deleted so only the engine's reply could put it there), `hydrate_on_open_seconds = 2.032` (queue → hydrated, including the fresh FreeCADCmd child, the restore pass and the display rebuild; the existing `open_seconds` on the synchronous path is 2.037 on the same run, so the pump adds nothing), `restore = {performed: true, matches_accepted: true}`. The new test's 24 checks all pass, including the File > New negative and the `set_params` racing a fresh queue.

`test_licensing_compliance.py`: 10 passed, 1 skipped — our diff is entirely under `mesh_agent/` and `shell/tests/python/`, `docs/BLENDER-TREE.md` §2a untouched. Existing `open_mainfile` tests keep passing unchanged: a queued open holds no engine state until drained, so their `open_roots() == []` assertions after a load still hold. The unreconciled tail is 3 nodes after this one (two directives plus this), which meets the reconcile trigger; a maintainer pass is due.

Dispatch closed: 1 unit — hydrate on file open landed (ADR-186) with a gate test asserting model_objects_on_open > 0; next: the lockout re-accept box (the failure code is now cached on the per-root state), then the `.cxpolicy` Save-As suffix.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: faf6e3ef6d2075c565010a9f1c7c2a059f208342

## State Impact

- target: simple-willow-8989 — The first of the two open failures is fixed (ADR-186): load_post -> on_file_changed -> queue_open queues the open of a saved .blend's existing .cadex, and a timer-driven pump (drag/refine shape) runs the restore-verified open_project and the display rebuild off the main thread, hydrating on it. Gate test test_opening_a_file_hydrates asserts model_objects_on_open > 0 (measured 1, 2.03 s queue-to-hydrated, equal to the synchronous open_seconds). ensure_open drains a queued open rather than racing it. A failed open at load now reaches the parameters panel's alert row, a chat status line, and open_failure_code on the per-root _State -- the hook the lockout re-accept box needs. Negative knowledge to retire: 'Do not assume a file open hydrates the model' no longer holds for a saved file beside an existing project; it still holds for Save-As (deliberately not queued) and an unsaved scene. Still broken: the digest lockout with no button back (the code is now cached; the box is the next unit) and the .cxpolicy Save-As suffix.
