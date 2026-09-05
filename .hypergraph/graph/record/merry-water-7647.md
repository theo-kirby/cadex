---
node_id: 08b64edc-d654-5c63-8103-b846f8d2171d
slug: merry-water-7647
title: pi is the third assistant, and MCP becomes a transport rather than the architecture (ADR-175)
created_at: '2026-08-30T11:28:20+00:00'
parents:
- forest-chart-2781
summary: ''
---
## What

pi is the third assistant provider (ADR-175), and the Mesh tool seam
gained a second, non-MCP transport: `pi_tools.js`, a native pi extension
that registers the bridge's tools with `pi.registerTool()` and relays
every call over the same authenticated TCP bridge the MCP shim uses.
Owner direction: MCP must not be the only way tools reach a model, and
pi — just installed on this machine — should be a configuration option.

## Why

ADR-174 declined pi because pi will not support MCP. The owner reframed
that: the dislike of MCP is the point, not the blocker. The tool seam was
always the TCP bridge; MCP was merely its only speaker. Making pi work
required exactly the thing the owner wanted anyway — proof that MCP is a
transport, not the architecture.

## Method

Probed live against pi 0.84.4 before coding, with a scripted TCP bridge
standing in for Blender:

- `pi.registerTool()` accepts the bridge's raw JSON Schemas (no typebox
  needed); a minimal node-builtins-only extension relayed a tool call and
  the model returned the planted word.
- `-p --mode json` emits JSONL: `session` header (id), `message_update`
  with `text_delta`/`thinking_delta`, `tool_execution_start`,
  `message_end` (assistant `stopReason` vocabulary: stop, toolUse, error,
  aborted, length — `errorMessage` on error), `agent_end`,
  `agent_settled`. Translation drops thinking, streams text deltas,
  surfaces tool starts, and takes `agent_settled` as the verdict.
- Sessions: `--session-id` + `--session-dir` resumed a remembered fact
  ("417"); a missing id is created fresh, so `PiBackend` mints a UUID and
  the stale-id case needs no fallback (the inverse of Codex's ADR-174
  resume-flag trap).
- Failure: a bogus `--model` exits 1 with the message on stderr and no
  JSONL — lands in the existing "ended unexpectedly" path.
- pi installs as an npm global under nvm (`~/.nvm/versions/node/*/bin/pi`,
  a per-version dir no GUI PATH has); `find_pi` globs it newest-first and
  the subprocess PATH is prefixed with pi's dir so `#!/usr/bin/env node`
  resolves.

Then: `PiBackend` behind the same three-shape event contract;
`--no-builtin-tools` plus the hermetic flags (no extensions/skills/
context-files/prompt-templates) keep pi's own tools and the user's pi
setup out of product turns; prompt behind `--`; model is a free pattern
("" = pi's own default) as a text field in preferences and the chat
header. Image blocks convert at the seam (MCP `{data,mimeType}` → pi's
`source` block).

## Result

Live end-to-end on the user's own pi (OpenRouter default,
kimi-k2.6): tool round-trip through `pi_tools.js` (PERSIMMON returned),
session resume across turns, bogus-model failure surfaced with pi's own
words. `bl_mesh_agent.py` suite green from source, including
`test_pi_backend_speaks_the_agent_event_contract` and the extended
session-provider rules; `pixi run gate` green. The licensing guard still
carries only its pre-existing failure (two ADR-173 demo scripts).

Files: `mesh_agent/pi_tools.js` (new), `backend.py` (PiBackend, find_pi,
shared `_text_delta_frame`), `agent.py`, `spaces.py`, `__init__.py`,
`bl_mesh_agent.py`, `AGENTS.md`, `docs/BLENDER.md`, `docs/DECISIONS.md`
(ADR-175), `docs/IDEAS.md` (a bridge CLI as a third transport for
bash-first agents — the owner's musing, parked). `cli/` remains
Claude-only.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

- target: shy-crane-2573 — the Mesh tool seam has two transports over one TCP bridge: MCP (mcp_shim.py, Claude/Codex) and a native pi extension (pi_tools.js); pi is the third provider preference with a free-pattern model field, minted session ids under the ADR-174 provider tag, and pi's own tools disabled per the ADR-163 posture (ADR-175)
