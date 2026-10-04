---
node_id: 7d5d5b4d-ef74-5541-96e2-9eff2058915d
slug: icy-bramble-4392
title: 'orun2 subtraction: the live policy session leaves the engine (ADR-528)'
created_at: '2026-10-04T07:29:12+00:00'
parents:
- clever-sky-3211
summary: ''
---
## What

Retired the live policy session from the engine (ADR-528). This is the first unit of the long-term subtraction rung: an engine answer that existed only to serve the shell.

- **Protocol:** `live_open`, `live_step` and `live_close` are gone from `READ_OPS`, `OP_ARG_SPECS` and `OP_RESPONSE_SPECS`. So are the `policy` nested response spec, the three response goldens and `docs/INTEGRATION.md`'s rows, all in the same change.
- **Code:** deleted `CadexLiveSession.py` (312 lines) and `cadex_live_worker.py` (614 lines), plus the worker's bundle entry and CMake lines. Also deleted `prepare_live`, `LiveBundleUnavailable` and their helpers in `CadexScriptedRuntime`, cadexd's `_op_live_*` and `_declined_live_*`, and the live half of `_invalidate_resident_workers`.
- **Dynamics:** removed the `forces` and `endless` keywords of `CadexDynamics.evaluate_episode`. Their only caller was the live worker.
- **Tests and tooling:** removed the latency script's live lane (`CADEX_LIVE_PROJECT`). Deleted `test_cadexd_live_ops.py`, `test_dynamics_live_hook.py` and the endless half of `test_dynamics_endless_episode.py`. Its `record_steps` tests move to `test_dynamics_record_steps.py`, because `record_steps=False` still has other callers.
- **Docs:** updated ARCHITECTURE, XSCRIPT, MUJOCO §8 (now "retired") and SHELL-PARITY. The `cadex_live.py` row no longer says "the engine API stays".

Net is about 2,450 lines removed.

## Why

The critic's message asked for two things in order: first a reconcile pass, then the long-term subtraction rung ("bridge answers in cli/ and src/Mod/cadex that existed only to serve the shell"). This iteration's dispatch forbids reconciling in a work iteration ("no exceptions"), so I did not reconcile. That is a deliberate deviation from the critic's first item. The tail is now three records (lively-beacon-5538, clever-sky-3211 and this one), and a reconcile pass is due from the maintainer or a reconcile-only iteration.

The unit is the critic's second item. Of the engine's ops, the live trio had no caller anywhere in `cli/`, the dashboard, `training/` or `analysis/`. Its only client was the deleted shell's Live editor. The owner notes of 2026-10-03 drop the live session explicitly, and the parity ledger still claimed the engine half "stays". That made it the clearest shell-only engine answer.

## Method

- **Finding the target:** grepped every `OP_ARG_SPECS` op for a consumer outside `src/Mod/cadex`. The live ops had none. Then traced the closure: host, worker, `prepare_live`, and the `forces`/`endless` seams. `record_steps` was kept because `test_success_spec_*` and `test_evaluate_success_model` use it.
- **New guards:** `test_cadexd_protocol.py` asserts the ops and the `policy` spec are absent. `test_engine_purity_guardrails.py` asserts neither module is in the tree or the closure. `test_dynamics_record_steps.py::test_the_live_session_keywords_are_gone` asserts `evaluate_episode` rejects `endless`.
- **Gates:**
  - Ran `pixi run build-engine`. Install never deletes, so I removed the stale `CadexLiveSession.py` and `cadex_live_worker.py` from `build/release/Mod/cadex` and `.pixi/envs/default/Mod/cadex` by hand.
  - Ran `pixi run stage-engine` (exit 0). The payload carries neither file.
  - Ran the packaged gate: `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`.
  - Ran `pixi run test-engine` and the CLI suite with `CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`.

## Result

- **The engine no longer carries a live policy session.** `OP_ARG_SPECS` has 14 ops, and `docs/INTEGRATION.md`'s op and response tables match it.
- **Measured gates:**
  - `pixi run test-engine`: **2581 passed, 56 skipped**. The previous record had 2607/56; the difference is the deleted live suites minus the 5 tests in `test_dynamics_record_steps.py`. The skips are the same MJX-gated set.
  - CLI suite, CPU-only (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`): **1420 passed, 1 skipped** in 20m33s. The skip is `CADEX_REVIEW_HOST`, as before.
  - Packaged lifecycle gate on the rebuilt and restaged payload: **24 passed, 0 skipped**.
  - Raw-NDJSON latency bar (dev tree): `ok: true`. The `set_params` median is 0.381 s, draft display 0.482 s and preview 0.0434 s. No `live_*` keys remain in its report.

- `ROADMAP.md`'s checked "Live mode" items (ADR-109/110/136) were left alone, because the charter bars hand-editing ROADMAP. They describe work that landed and was later removed, and ADR-528 records the removal.
- **Assumption:** the owner's "live policy session is dropped" covers the engine half as well as the shell editor. Interactive pushes can return as a new dashboard design. ADR-528 names that as the reversal path.
- No new dependency. The agent tool surface is unchanged.
- **Next subtraction candidates** to audit the same way:
  - the `set_params` `cages`, `nets`, `boards` and `mounts` editor tables (cage ring-drag and the wiring editor were dropped);
  - `put_blueprint`'s `meta.recipe` "the shell reads back";
  - `inspect` scope `selection` ("shell-only").

  Each needs a check that the agent or the CLI does not use it.
- The unreconciled tail is fat: three records. Reconcile is due.

Dispatch closed: 1 unit — the live policy session's ops, host, worker and episode seams are retired from the engine (ADR-528)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 150e874de5cd15128944f17f6925eb43e3279c11

## State Impact

- target: forest-wind-0342 — The live policy session is retired from the engine (ADR-528): live_open/live_step/live_close leave OP_ARG_SPECS, OP_RESPONSE_SPECS and INTEGRATION.md; CadexLiveSession.py and cadex_live_worker.py are deleted; the payload carries neither. Engine suite 2581/56, CPU-only CLI suite 1420/1, packaged gate 24/0.
- target: salty-isle-4063 — evaluate_episode loses its live-only forces and endless keywords (ADR-528); record_steps=False stays. Reviewing a policy is rollout playback plus evaluate's disturbance tests.
