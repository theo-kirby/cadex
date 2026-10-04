---
node_id: e513cce3-f395-50a8-8306-0178e8adfd5b
slug: gentle-hawk-3921
title: 'orun2 subtraction: the engine stops reading a FreeCAD preference group for its budgets (ADR-530)'
created_at: '2026-10-04T08:40:49+00:00'
parents:
- royal-quill-2455
summary: ''
---
## What

The missing record for ADR-530 (iteration 62, commit `381549f7`, committed as "no record"). `CadexEngineSettings` stopped reading the FreeCAD preference group `User parameter:BaseApp/Preferences/Mod/cadex`. Removed: `PREFERENCE_GROUP`, `preferences`, `load_engine_budgets` and the `FreeCAD` import. `default_budgets()` returns the two constants (300 s, 6144 MB). `resolve_budgets` takes each positive caller budget per field and otherwise uses the default. `CadexScriptedRuntime`'s fallback calls `default_budgets`. Eight files changed: 105 insertions, 155 deletions. Iteration 62 changed no code; this iteration reran every gate on the committed tree.

## Why

The critic asked for this first: write ADR-530's record with measured engine-suite, CLI-suite (GPU hidden) and packaged-gate results on a restaged payload, then reconcile. **I did not reconcile.** This iteration's dispatch rules forbid the hypergraph-reconcile skill in a work iteration "no exceptions", and the dispatch rules are the harder constraint. The tail now holds two unreconciled records (`royal-quill-2455` and this one). The next reconcile slot should fold both. The critic's next branch was "if `nvidia-smi` reaches the driver, rerun W1 step 7". It still fails ("couldn't communicate with the NVIDIA driver"), so W1 step 7's GPU half stays blocked. The REPORT.md refresh and the done claim are the next unit, after the reconcile.

## Method

- Audit: `git grep` for `ScriptedTimeoutSeconds|ScriptedMemoryLimitMB|Preferences/Mod/cadex|load_engine_budgets|PREFERENCE_GROUP`, excluding `docs/DECISIONS.md`, `docs/history` and `.hypergraph`. The only hit is the absence test itself (`test_engine_defaults_and_envelopes.py:109`, `test_the_engine_reads_no_preference_group`).
- `pixi run test-engine`.
- `pixi run build-engine`, then `pixi run stage-engine`. Then the packaged lifecycle gate: `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`. Checked that the staged `CadexEngineSettings.py` contains neither `ParamGet` nor `ScriptedTimeoutSeconds`.
- `CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests`, run after build-engine.
- `nvidia-smi`: fails to reach the driver.

## Result

- `pixi run test-engine`: 2574 passed, 56 skipped (6m11s).
- build-engine and stage-engine: both clean. Payload at `build/engine/cadex-engine-0.0.0-linux-x64` (3.2G), and mujoco 3.10.0 imports from it. The staged settings module contains neither the preference keys nor `ParamGet`.
- Packaged lifecycle gate: 24 passed (25s).
- `cli/tests`, CPU-only: 1420 passed, 1 skipped (20m51s).
- What is true now: the engine contains no `App.ParamGet` call for budgets. Budgets come from the caller (the project's `agent.json` or CLI flags, ADR-517) or from the engine's constants. No cadexd op, response shape, tool surface or dashboard behaviour changed.
- Concerns:
  - Reconcile is overdue. The frontier has not moved in 8 iterations, and the tail holds 2 records. I did not run it because this dispatch forbids it.
  - The GPU driver is still unreachable, so W1 step 7's GPU rerun stays blocked.
  - Next unit after reconcile: refresh REPORT.md's defects and the criteria evidence, then claim done for critic review without ticking any boxes.

Dispatch closed: 1 unit — ADR-530 recorded with fresh gates (engine 2574 passed, packaged gate 24 passed, CLI 1420 passed CPU-only); reconcile deferred to its own slot

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 381549f7023e4ec9acd8038d88f1c1a13cb4e463

## State Impact

- target: forest-wind-0342 — The engine reads no FreeCAD preference group (ADR-530): CadexEngineSettings has no PREFERENCE_GROUP/preferences/load_engine_budgets and no FreeCAD import; sandbox budgets come from the caller (project agent.json or CLI flags, ADR-517) per positive field, else the engine constants 300 s and 6144 MB; test_the_engine_reads_no_preference_group pins the absence. Engine suite 2574 passed, packaged gate 24 passed, cli/tests 1420 passed CPU-only
