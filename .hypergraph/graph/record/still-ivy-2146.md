---
node_id: 74e2fd42-bf97-534c-8de6-9801d1f9b6d3
slug: still-ivy-2146
title: Read-only dashboard, cadex mcp, and Ouroboros out of the product (ADR-536–538)
created_at: '2026-10-04T14:32:07+00:00'
parents:
- careful-glacier-8772
summary: ''
---
## What
Owner direction (2026-10-04): Cadex is the engine, a read-only dashboard, and agent bindings any agent uses; Ouroboros is not part of Cadex. Three changes on branch `read-only-dashboard`:
- ADR-536: no product file names Ouroboros (runs listing `/api/runs` and `/r/`, `cadex app --runs`, `tools/operator_review*`, `docs/OPERATOR-REVIEW.md` removed).
- ADR-537: the dashboard writes nothing; no POST routes, no write token, no chat, sliders or verdict buttons. Any non-GET/HEAD is 501.
- ADR-538: Cadex has no agent of its own. `cadex -p`, `agent.py`, `turn_store.py`, `comments.py`, `leave_note`, `walk --prompt` and the relay socket are gone. New `cadex mcp --project DIR` (MCP stdio server; engine opened on first call, released after `--idle`, one PROGRESS row + commit per session that accepted a build) and `cadex guidance` (whole guidance; the MCP `instructions` are a <2,000-char brief pointing at it, because Claude Code caps instructions at 2,048 chars by default).

## Why
The owner's interface is converging on an agent of their choice (Claude Code, Codex, Pi) paired with the dashboard as a view. A second agent loop, a chat in the page and an async owner channel duplicated that.

## Method
Edited `cli/cadex_cli/{__main__,mcp,guidance,bridge,tools,review_server,session,report,project_docs,walk}.py` and `review_static/`; engine guidance `CadexAgentGuidance.md` (DECISION: lines -> DECISIONS.md). Drove `cadex mcp` over real stdio on a one-box plate. Ran `pixi run test-engine` and `pixi run python -m pytest cli/tests` (CUDA hidden).

## Result
- `cadex mcp` over stdio against the dev engine: initialize 0.05 s, 14 tools, cold write_script 0.4 s; after a 3 s idle the engine closed and landed `| mcp | 9aafd182 | ... | mcp: write_script |` plus commit `cadex mcp: write_script`; set_params after reopen 0.5 s.
- Engine suite: 2576 passed, 58 skipped.
- CLI suite: 1119 passed, 1 skipped (commit aa8bcbb2).
- Removed tests of frozen ot7/ot8 probe runners that drove `cadex -p` (can no longer run).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: read-only-dashboard
- commit: aa8bcbb293457064008fd4784468591f759d6a48

## State Impact

- target: chilly-union-8972 — the CLI drives no agent: cadex -p, agent.py, turn store and owner channel removed; cadex mcp (MCP stdio, idle release, row+commit per session) and cadex guidance are how any agent drives a project (ADR-538)
- target: twilight-aspen-1541 — superseded: the dashboard is read-only (ADR-537); steering happens in the person's own agent
- target: fierce-falcon-5989 — superseded in part: the owner channel (leave_note, comments) is removed (ADR-538); the one contract is the guidance served by cadex mcp/cadex guidance
- target: swift-nest-0229 — superseded: Ouroboros runs are no longer listed in the dashboard (ADR-536)
- target: deep-clover-6012 — superseded: tools/operator_review.py is deleted (ADR-536)
