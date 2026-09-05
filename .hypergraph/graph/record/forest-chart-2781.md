---
node_id: 628247ab-e0dc-5574-b236-a9b2262c6e3f
slug: forest-chart-2781
title: 'The assistant becomes a preference: Codex joins Claude Code behind one event contract (ADR-174)'
created_at: '2026-08-30T10:33:06+00:00'
parents:
- weathered-sand-9705
summary: ''
---
## What

The shell's assistant is now a preference: Claude Code (Anthropic, the
default) or Codex (OpenAI), each with its own model picker, in the add-on
preferences and mirrored in the chat editor's header. ADR-174. User
direction: the assistant should not require a Claude subscription
specifically. pi was considered and declined — its author states it will
not support MCP, and the Mesh tools reach the model only through MCP.

## Why

Until now the shell hard-coded one agent CLI (`claude -p`). A user with a
ChatGPT subscription and no Claude one had no assistant at all. Both
choices stay agent CLIs the user is already logged into: no provider
stack, no API key, no model loop of ours — the ADR-030 posture is
unchanged, only the CLI seat became pluggable.

## Method

The seam is the event contract, not an abstraction layer: `agent.py`
understands exactly three stream shapes (text deltas, tool_use notices, a
final result), and the new `CodexBackend` translates `codex exec --json`
JSONL onto them rather than teaching the agent a second vocabulary.

Every mechanical difference was verified live against codex-cli 0.142
before being coded, then test-pinned:

- No `--system-prompt` flag exists; the system prompt travels as
  `AGENTS.md` in a private `-C` workdir (verified: a fact planted there
  came back).
- The MCP shim is wired in as `-c mcp_servers.mesh.*` overrides.
  `default_tools_approval_mode = "approve"` is load-bearing: `codex exec`
  is non-interactive and auto-declines any tool call held for approval
  ("user cancelled MCP tool call"), which silently disarms every Mesh
  tool. Found by running a scripted MCP server against the real CLI;
  the fix was located in codex-rs source (`mcp_types.rs`).
- Codex's own shell tool cannot be removed; it runs under
  `--sandbox read-only` so mutations only arrive through the bridge.
- `exec resume <thread-id>` accepts fewer flags than `exec` — `-C`,
  `--sandbox` and `--color` are rejected outright by clap, the turn
  produces nothing, and the resume fallback silently downgrades every
  follow-up to a fresh conversation. Found because a live resume test
  answered "I don't know" to a remembered fact; the sandbox rides in as
  `-c sandbox_mode="read-only"` on resume instead.
- Models gpt-5.5 (default), gpt-5.4, gpt-5.4-mini each verified accepted
  on ChatGPT auth; gpt-5.3-codex and older are refused for that auth and
  are not offered.

Session identity: the .blend transcript now carries `session_provider`
beside `session_id` (untagged saves predate providers and are Claude's);
a freshly built backend adopts only a matching saved session, and
switching the provider drops the backend and its session — the visible
transcript stays, the chat says so.

## Result

Live end-to-end runs of the real `CodexBackend` + `mcp_shim.py` against a
scripted TCP bridge: tool call round-trip (the model returned the planted
word through the shim), resume with context retained ("417" recalled),
stale-session fallback to a fresh conversation with the `resume_failed`
notice emitted. `pixi run gate` green (`ok: true`);
`bl_mesh_agent.py` suite green from source including two new tests
(`test_codex_backend_speaks_the_agent_event_contract`,
`test_a_session_resumes_only_into_the_cli_that_minted_it`).
`test_licensing_compliance.py` has one pre-existing failure (two ADR-173
demo scripts missing SPDX headers) unrelated to this work.

Files: `mesh_agent/backend.py` (CodexBackend, find_codex, shared
docstring), `agent.py` (provider dispatch, session adoption, provider
switch), `history.py` (`session_provider`), `spaces.py` (header pickers),
`__init__.py` (preferences), `shell/tests/python/bl_mesh_agent.py`,
`AGENTS.md`, `docs/BLENDER.md`, `docs/DECISIONS.md` (ADR-174). The
`cli/` front end is unchanged and remains Claude-only.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

- target: shy-crane-2573 — the assistant is now a provider preference: Claude Code (default) or Codex (OpenAI), per-provider model picker in preferences and the chat header; one three-shape event contract, CodexBackend translates into it; .blend sessions carry session_provider so a session resumes only into the CLI that minted it (ADR-174)
