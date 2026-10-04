---
node_id: 7cac27e1-0171-55a8-90bd-c4803e15b8b4
slug: royal-quill-2455
title: 'orun2 subtraction: CadexStudio''s shell-only process entry leaves (ADR-529)'
created_at: '2026-10-04T07:59:26+00:00'
parents:
- icy-bramble-4392
summary: ''
---
## What

orun2 long-term rung 3 (subtraction now the shell is gone): the studio renderer's child-process entry leaves with the shell (ADR-529). Removed from `src/Mod/cadex/CadexStudio.py`: `REQUEST_SCHEMA` / `RESULT_SCHEMA` (`cadex-studio-request-v1` / `-result-v1`), `_blocks`, `run_request` with its `kind: render | look | blocks` paths, `main` and the `__main__` guard, plus `role_colours` and `display_objects` (ADR-449's viewport colours for the shell). `render_files` keeps its appearance-row helpers. `cadex_tests/test_studio_process.py` becomes `test_studio_standing.py`.

## Why

The critic named this unit: audit what existed only for the shell and drop `CadexStudio.py`'s process entry and its `kind: blocks` path, if no `cli/` caller needs it. The critic's fix-first request (stale shell claims in salty-isle-4063 and forest-wind-0342) is done in this record's State Impact below.

## Method

- Audit: grepped the whole tree (outside `.hypergraph/`, `docs/history/`, `DECISIONS.md`) for `run_request`, `REQUEST_SCHEMA`, `RESULT_SCHEMA`, `cadex-studio-request`, `role_colours`, `display_objects` and `inventory_value`. The only hits were the module itself, its process tests, `docs/INTEGRATION.md`/`ARCHITECTURE.md`, and `cli/tests/fake_cadexd.inventory_value` (an unrelated fake helper with the same name). `render.py`, `studio.py`, `film.py`, `video.py`, `bridge.py`, `review_server.py` and `agent.py` import the module by path and call `snapshot`, `render_files`, `look_report`, `materials`, `blueprint_sheet` and similar directly. The dashboard paints parts with `CadexStudio.materials` (ADR-522), not `role_colours`. No caller needs the entry, so the critic's fallback (move on to the next shell-only bridge answer) did not apply.
- Deleted the entry and the two viewport helpers, plus the import `sys` that only `main` used. Updated the module docstring, the `CadexFitReport.py` docstring and the `CadexAgentGuidance.md` header comment (it sits above the guidance marker, so the agent's text is unchanged) so they stop naming the shell.
- `docs/INTEGRATION.md`: the "second program in the payload" section now says the module is loaded by path and has no process entry. `docs/ARCHITECTURE.md`: the CadexStudio and CadexFitReport rows are updated. `docs/DECISIONS.md`: ADR-529.
- Tests: `test_studio_standing.py` keeps the closure test and the CMake-install test. It tests the render set and the look in process (`snapshot` + `render_files` + `write_files`, `look_report`). `test_the_shells_process_entry_stays_gone` fails if any removed name, the schema string or a `__main__` guard comes back.

## Result

- Net change: 166 insertions and 397 deletions. That is about 150 lines of engine code and 105 lines of tests, net. No cadexd op, response shape, tool surface, CLI or dashboard behaviour changed. The payload ships the same files, and its `CadexStudio.py` no longer contains the schema string (checked after stage-engine).
- `pixi run test-engine`: 2574 passed, 56 skipped.
- `pixi run build-engine` and `pixi run stage-engine`: both clean. Packaged lifecycle gate (`CADEX_ENGINE_ROOT=<payload>`, `test_cadexd_lifecycle.py`): 24 passed.
- `cli/tests`, run CPU-only (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`) after build-engine: 1420 passed, 1 skipped (20m27s).
- The tail now has one unreconciled record (this one).
- Next subtraction candidates: shell-only bridge answers and payload staging into a bundle (long-term rung 3).

Dispatch closed: 1 unit — CadexStudio's shell-only child-process entry (cadex-studio-request-v1, kind blocks, role_colours) removed under ADR-529

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: cce9f3131f041d8c25f87196d3ac2b91287661f8

## State Impact

- target: forest-wind-0342 — CadexStudio has no process entry (ADR-529): cadex-studio-request-v1, kind render/look/blocks, run_request/main and role_colours/display_objects are deleted; the CLI and dashboard load CadexStudio and CadexFitReport by path, and nothing runs them as a child process. Corrects the stale claim that the shell runs CadexStudio as a child process (the shell is deleted, ADR-498). test_studio_standing.py pins closure, install, in-process render and the entry's absence
- target: salty-isle-4063 — Corrects a stale invariant: 'nothing in shell/ imports mujoco' is moot because shell/ is deleted (ADR-498). The live invariants are CadexDynamics.py reachable from the sandboxed worker but never from cadexd, and no jax/mjx under src/Mod/cadex or in a staged payload
