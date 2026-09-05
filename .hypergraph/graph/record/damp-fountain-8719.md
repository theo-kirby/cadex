---
node_id: 1eae4e4a-36b0-5fe3-8e3b-2a70c6ffdef2
slug: damp-fountain-8719
title: 'ADR-180: the per-turn tool-call limit is removed — a hard turn is allowed to be long'
created_at: '2026-08-30T22:16:35+00:00'
parents:
- merry-water-7647
summary: ''
---
## What

Removed the per-turn tool-call limit from the `mesh_agent` add-on
(ADR-180). The agent loop no longer stops a turn after N tool calls; the
"Tool Call Limit" preference is gone from the add-on preferences.

## Why

Owner direction. A difficult prompt legitimately takes many tool calls,
and the cap (default 25) would interrupt mid-work with "Tool call limit
reached ... Summarize progress and stop", forcing the user to type
"continue". The stop served no product purpose: the user can always press
Stop, and the engine already enforces its own per-run time and memory
budgets, so a runaway turn is bounded where it costs resources.

## Method

Deleted `DEFAULT_TOOL_CAP`, the `_tool_cap()` resolver and the
unconditional cap check in `agent.py`, and the `max_tool_calls`
preference plus its UI row in `__init__.py`. Kept `tool_cap_override` —
already documented as a test/injection hook — and made
`_handle_tool_request` enforce it only when set: `test_tool_call_cap`
(bl_mesh_agent.py), the cadex gate suite and the eval harness use it to
bound a runaway mock or benchmark turn. The `_tool_calls` counter stays
because the eval harness reads it.

## Result

In normal use a turn has no tool-call limit. Verified:
`package/app/build_app.sh gate tests/python/bl_mesh_agent.py` green —
the cap test now exercises the override path — and `pixi run gate` green
against the built bundle (CADEX-BLENDER-GATE ok: true). ADR-180 appended
to docs/DECISIONS.md.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

- target: shy-crane-2573 — the per-turn tool-call cap and its preference are removed (ADR-180); turns run unlimited in normal use, tool_cap_override remains as the test/eval bound
