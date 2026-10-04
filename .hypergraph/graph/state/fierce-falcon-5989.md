---
node_id: 2356687c-3bc7-59ca-b476-7bee6d687215
slug: fierce-falcon-5989
title: A1. The agent has one contract, and a way to reach the owner without waiting (orun2)
created_at: '2026-10-03T10:54:47+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Open charter criterion for run orun2: **A1. The agent has one contract, and a way to reach the owner without waiting.** - The product agent's tools (`cli/cadex_cli/tools.py`, pinned by `test_project_tool_surface.py`) and its guidance (`CadexAgentGuidance.md` plus `agent.system_prompt`) are the single source. Nothing that was only in the shell's `modes.py` is lost: - re-derive anything worth keeping, because the shell's code is GPL and must not be copied; - record what was not kept. - **The agent gains a non-blocking channel to the dashboard:** - it can flag a revision or artifact for the owner's review, or post a question; - the dashboard shows these; - the owner's answers and comments arrive in the agent's next turn; - the agent never stops to wait for an answer. - Tests pin the channel at the protocol or tool surface. Changing the surface follows AGENTS.md's tool-surface rule. [rec: winter-stone-5109]

| Half | State | Evidence |
|---|---|---|
| Non-blocking channel | removed | Was evidenced: `leave_note` into `comments.jsonl`, a *From the agent* panel, `cadex comment --reply` (ADR-512) [rec: proud-quill-5791]. Removed with `comments.py`, the relay socket and `cadex -p` (ADR-538); the person talks to their own agent directly [rec: still-ivy-2146] |
| One contract | evidenced | The guidance served by `cadex mcp` (a <2,000-char MCP `instructions` brief pointing at the whole) and printed by `cadex guidance` is the one contract; `CadexAgentGuidance.md` carries it, with `DECISION:` lines going to `DECISIONS.md` [rec: still-ivy-2146]. Not re-checked by that record: SHELL-PARITY §4's shell-only guidance points and the `ENABLE_TOOL_SEARCH` check, open before it [rec: proud-quill-5791] |

Declared target: `gap-a1-agent-has-one-contract`. Reconcile judgement: stays `working`. The channel half is retired by owner direction (ADR-538), not failed; the contract half now has a single source. The owner holds the charter checkbox [rec: still-ivy-2146].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- proud-quill-5791 — leave_note owner channel evidenced (ADR-512)
- still-ivy-2146 — channel removed (ADR-538); one contract is the cadex mcp / cadex guidance text
