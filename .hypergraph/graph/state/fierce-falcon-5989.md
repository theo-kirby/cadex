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
| Non-blocking channel | evidenced | Bridge tool `leave_note(type flag\|question, text, artifact?)` appends to `comments.jsonl` and returns at once; the dashboard's *From the agent* panel lists notes and serves the flagged file; the owner answers with `cadex comment --reply`, which reaches the next turn quoting the note. Pinned by `test_project_tool_surface.py`, `test_owner_channel.py` and a Chromium test against a real engine (ADR-512, commit ed1c6e1d) [rec: proud-quill-5791] |
| One contract | open | SHELL-PARITY §4's shell-only guidance points and the `ENABLE_TOOL_SEARCH` check are still to settle [rec: proud-quill-5791] |

Declared target: `gap-a1-agent-has-one-contract`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: flipped `open` → `working` — the channel half has measured evidence; the one-contract half is open [rec: proud-quill-5791].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- proud-quill-5791 — leave_note owner channel evidenced (ADR-512)
