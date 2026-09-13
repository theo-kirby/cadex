---
node_id: 966c48c4-45a3-5f60-881c-89a4c728fbfe
slug: soft-forest-5662
title: 'Backfill: iteration 81 made every CLI modelling write carry the standard tessellation request (ADR-312)'
created_at: '2026-09-13T06:46:36+00:00'
parents:
- honest-rain-3132
summary: ''
---
## What

Backfill of iteration 81, whose code landed in commit `2d007d35` together with the iteration-80 backfill record and without a record of its own. Iteration 81 fixed the second defect Lark exposed: the agent's modelling calls through the CLI bridge omitted `display`, so a project straight out of `cadex -p` had an accepted attempt with BREP outputs and no tessellation, and the review dashboard said `accepted attempt retained no tessellation` until a public `cadex render` republished it (ADR-312).

## Why

The critic asked for iteration 81's causal record with its D2 impact and actual gate results before any new unit. Iteration 81's own CLI-suite log (`/tmp/cli-suite-81.log`) ends at 49 percent with no summary line, so that run was never a recorded pass; this record reports the suites as run by iteration 82 on the unchanged committed tree.

## Method

`cli/cadex_cli/tools.py` moves `display` from the omitted set to the injected set and exposes `STANDARD_DISPLAY` (`quality: standard`, no edges — the request `cadex params` already makes, ADR-293) and `injects_display`, decided from `OP_ARG_SPECS` rather than a second op list. `cli/cadex_cli/bridge.py` overrules any `display` the model supplies and injects the constant on every op that takes it (`write_script`, `edit_script`, `set_params`, `rebuild`), still dropping the reply's `display` block from what the model sees; `cadex script --set` asks for the same. Regressions: `cli/tests/test_mcp_protocol.py` asserts the constant reaches the four ops and never `describe_api`/`inspect`, and that the list is the protocol's; `cli/tests/test_review_server.py` writes a first script through the bridge on a fresh project through the built engine, confirms the ADR-311 staging shape, and asserts the dashboard draws the model with no `review/` render present — it failed on the old bridge with `retained no tessellation`. Cost measured on Lark's eight solids on a scratch copy, three writes each way: 0.45–0.60 s without tessellation, 0.44–0.49 s with. `docs/CLI.md`, `docs/HEADLESS-BIPED-REVIEW.md`, the Lark probe README and the operator status README were updated; `docs/probes/lark-fresh/tessellation81.json` records a fresh headless-browser visit to the persistent private-network URL afterwards (service PID unchanged, not restarted; Lark's accepted attempt untouched, eight components, 96 triangles, twenty parameters, zero runs).

## Result

A project straight out of the product agent's turn has a model to show on the review dashboard; `accepted attempt retained no tessellation` now names a project accepted before ADR-312 or through a `restore` replay alone. Reading a project still rebuilds nothing. No dependency, protocol, payload, engine or shell change. Lark's accepted revision `753cf0cc4600…` and digest `3b704a3fc1c4…` are unchanged.

Gate results, run by iteration 82 on commit `2d007d35` (the tree iteration 81 committed, unchanged): `pixi run python -m pytest cli/tests` — 433 passed, 1 skipped in 413.64 s, exit 0 (`/tmp/ot5-82-cli.log`); `pixi run test-engine` — 2110 passed, 53 skipped in 268.99 s, exit 0 (`/tmp/ot5-82-engine.log`). Iteration 81's own CLI-suite log ended at 49 percent without a summary, so its run is not a recorded pass.

Dispatch closed: 1 unit — every CLI modelling write carries the standard tessellation request (ADR-312), with an engine-backed browser regression on a fresh project; both suites green on the committed tree.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 2d007d3546173f91e115d0fab0eddebb5fbab127

## State Impact

- target: shy-meadow-0959 — D2: a project straight out of the product agent's turn has a model to show; the bridge injects the standard tessellation request on write_script, edit_script, set_params and rebuild (ADR-312), proven by an engine-backed headless-browser regression on a fresh project that failed on the old bridge; gates run by iteration 82 on the committed tree: CLI 433 passed/1 skipped, engine 2110 passed/53 skipped.
- target: crisp-sun-1239 — The second defect Lark's clean-project repeat exposed (no tessellation from the agent's writes) is fixed (ADR-312); Lark's accepted identity is unchanged and the persistent port 8765 page was re-verified without a service restart.
