---
node_id: a46cf355-3afd-50c5-896a-6fa1a0993050
slug: rare-beacon-3440
title: V4. The page says what the agent is doing
created_at: '2026-10-05T08:57:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open orun3 charter criterion: **V4. The page says what the agent is doing.** [rec: golden-snow-6627]

- The MCP server appends one line per tool call to a project activity log: time, tool name, a short summary of the arguments, and the outcome. Arguments are never logged in full. The log is bounded (rotated or capped), and that bound is tested. [rec: golden-snow-6627]
- `test_project_tool_surface.py` is unchanged: this adds no tool, no argument and no result field. If that turns out to be impossible, the tool-surface rule in AGENTS.md applies. [rec: golden-snow-6627]
- The overlay shows the latest activity and how long ago it happened. An expanded view lists the last few entries. When nothing has happened for a while, the line says the agent is idle rather than showing a stale action as current. [rec: golden-snow-6627]
- A test drives a tool call through `cadex mcp` and reads the entry back from `/api/project`, or from a route the HTTP API pins. [rec: golden-snow-6627]

Declared target: `gap-v4-page-says-what-agent`. This node tracks the criterion as a gap; it becomes working only with measured evidence, in a causally parented record, that the criterion is met. The owner ticks the charter box; roles do not. Truncated impact wording is resolved from the full charter in the same record [rec: golden-snow-6627].

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-v4-page-says-what-agent)
