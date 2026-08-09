---
node_id: 3f72f3a6-8aa7-59b2-a63f-088df9dfceb0
slug: simple-hollow-8675
title: 'Prehistory: the process boundary — cadexd, the Blender shell, and the Qt shell''s deletion'
created_at: '2026-08-09T15:15:58+00:00'
parents:
- civic-horizon-2730
summary: 'Phases 5-7 in one day: the engine became a headless NDJSON service, the Blender add-on became the product, and the Qt shell plus the provider stack were deleted.'
---
## What

Phases 5, 6 and 7 in a single day — 35 commits, ADR-017…ADR-024. The engine
became **cadexd**: a per-project headless `FreeCADCmd` service speaking
`cadex-cadexd-v1` NDJSON over stdio. The Blender add-on `mesh_agent` became its
client and therefore the product. Then the interim Qt shell and the entire
provider stack were deleted.

## Why

Follows the teardown, and depended on it: a single script format plus a
digest-verified rebuild is what made the engine separable at all. Separating it
is also what let the Blender shell be the product without dragging the engine
across the GPL boundary.

## Method

`cadexd.py` + `CadexdProtocol.py`: serial dispatch, a `CADEXD_BUSY` refusal for
a second modelling request, mid-run `cancel`, stdin-EOF lifetime, an fd-1 hijack
so only protocol frames reach the parent, and a digest-verified restore pass on
every open (ADR-017). The Qt shell was deliberately made the *first* protocol
client — to prove the boundary — and then removed (ADR-018, ADR-021).
`BUILD_GUI=OFF` for release and package configs (ADR-022), which doubles as the
disable commit for `src/Gui` under the removal protocol. The engine payload with
a `cadex-engine.json` discovery manifest landed here too (ADR-023).

## Result

Measured, not asserted: picking fidelity **372/372** against a ≥99 % bar,
slider-drag median **0.548 s** against a 0.65 s bar, restart rehydration, and
`kill -9` → respawn → restore digest equality with a mid-run cancel.

The subtraction was large: 57 Python modules → 34, 36 test files / 425 tests →
20 / 154, and `requirements.txt` deleted outright because the engine had no
third-party Python dependency left. A release build produces `FreeCADCmd` and
`CadexGeometryWorker` **and no application**.

The boundary is a *process* boundary, and tests pin it rather than convention:
`test_engine_purity_guardrails.py` asserts cadexd's transitive import closure
equals a declared list, and that nothing under `src/Mod/cadex/**` imports
`PySide*`, `FreeCADGui`, `tool_impl` or `jsonschema`. ADR-027 later pinned the
*response* half of the protocol with golden fixtures, after finding that
`OP_ARG_SPECS` pinned requests only while the shell read ~50 unasserted response
keys.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW engine — the engine runs as cadexd behind a test-pinned NDJSON protocol, with no GUI and no provider stack.
- target: NEW shell — the Blender add-on `mesh_agent` is the product UI and the protocol's first real client.
