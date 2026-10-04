---
node_id: ba1ad349-7c0f-5361-8460-23048e9aec13
slug: clear-heron-4371
title: 'orun2 S1: mesh.blender retired with the shell (ADR-496)'
created_at: '2026-10-03T12:01:42+00:00'
parents:
- lucky-haven-1081
summary: ''
---
## What
Retired `mesh.blender` (ADR-496, commit `e53b71eb`). Also fixed the heartbeat race in `cli/tests/test_video.py` that the critic asked to have fixed first.

## Why
The critic asked for two things, in this order. First, fix the `test_video.py` heartbeat race. Second, retire `mesh.blender` as horizon rung 3 of S1 (`sunny-clover-3750`). Both are done. The critic also offered retiring the Codex/pi backends as a separate commit if there was room. I did **not** take that: the iteration budget is one unit, and those backends live entirely in `shell/` (backend.py, mcp_shim.py, modes.py). What remains outside `shell/` is docs and guidance wording, which makes it its own unit.

## Method
- **test_video.py.** The stand-in trainer called `write_text` on the heartbeat, which truncates and then writes. A reader could see '' in between. It now writes a `.tmp` file and calls `replace()`.
- **Code removed.**
  - the `blender` method, `contains_blender_recipe` and `"blender"` in `APPROXIMATING_OPERATIONS` from `cadex_mesh_api.py`, plus its three imports that became unused;
  - the recipe branch and the recipe digest branch in `cadex_mesh_worker.py`;
  - the mesh pack's listing in `CadexScriptedDomains.py`;
  - the staged filenames and `CADEX_BLENDER_EXECUTABLE` forwarding in `CadexScriptedRuntime.py`;
  - the CMake install lines;
  - the architecture test's list;
  - the wording of two refusal messages in `cadex_part_api.py`.
- **Files deleted.** `cadex_blender_runner.py`, `cadex_blender_worker.py`, `examples/blender_enclosure.py` and `test_blender_recipe.py` (10 tests).
- **Docs.** `docs/BLENDER-RECIPES.md` moved to `docs/history/` behind a superseded banner. AGENTS, VISION, ARCHITECTURE, INTEGRATION, XSCRIPT, CLI and ORGANIC no longer describe the exception.
- **Users of the op.** A grep of all 284 projects in the projects directory and the jobs directory found no `mesh.blender` call and no stored `"operation": "blender"` definition. Only the example used it.
- **Stale build copies.** The install step leaves deleted files behind, so I removed the old runner/worker copies from `build/release` and the pixi env before restaging.

## Result
- **Gates.**
  - `pixi run test-engine`: 2582 passed, 56 skipped.
  - `cli/tests` with the GPU hidden: 1291 passed, 1 skipped, and `test_video.py` is clean.
  - `pixi run build-engine` and `stage-engine`: ok. The payload no longer has `cadex_blender_*`.
  - Packaged `test_cadexd_lifecycle.py`: 24 passed.
- **Protocol.** `mesh.blender` was never a cadexd op (ADR-185 added none), so `OP_ARG_SPECS` did not change. `docs/INTEGRATION.md` dropped its runtime paragraph in the same commit.
- **Not touched.** `docs/ROADMAP.md` is still untouched; its ADR-185 checkbox line at ~1441 still describes the bridge. The charter forbids hand-editing ROADMAP, and this conflicts with AGENTS.md's checkbox rule. R1's rewrite should settle it.
- **Next.** Codex/pi retirement with its own ADR, which is the rest of rung 3. After that comes the `shell/` delete commit with the licensing restatement.
- **Reconcile.** The unreconciled tail is now 3 records, which is the reconcile threshold.

Dispatch closed: 1 unit — mesh.blender retired (ADR-496), test_video heartbeat race fixed, all three gates green.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: e53b71eb62970a55f2052025ba19d74539e31138

## State Impact

- target: sunny-clover-3750 — mesh.blender retired (ADR-496, e53b71eb): op, runner, worker, example, tests removed, BLENDER-RECIPES.md to docs/history; no project used it; packaged gate 24 passed. Codex/pi retirement and the shell delete commit remain.
