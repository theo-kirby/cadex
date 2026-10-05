---
node_id: a46cf355-3afd-50c5-896a-6fa1a0993050
slug: rare-beacon-3440
title: V4. The page says what the agent is doing
created_at: '2026-10-05T08:57:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun3: **V4. The page says what the agent is doing.** The MCP server appends one bounded line per tool call (time, tool, short argument summary, outcome) to a project activity log whose bound is tested; `test_project_tool_surface.py` stays unchanged; the overlay shows the latest activity and its age, an expanded list of the last few entries, and "idle" rather than a stale action; a test drives a call through `cadex mcp` and reads it back from `/api/project` [rec: golden-snow-6627]. The human owns the checkbox.

**Met on evidence** [rec: early-crow-5889]. Reconcile judgement: status `working`, because both halves landed and every V4 bullet has evidence, following V1/V2/V3 precedent.

- **Write half (ADR-549, commit `ba015523`).** Every `cadex mcp` tool call, failed calls included, appends one line (t, tool, summarised args, outcome, detail, ms) to git-ignored `review/activity.jsonl`, capped at 64 KiB and rotating to the newest 32 KiB (tested). `/api/project` carries `activity` (newest 10, or `available: false` with a reason). An end-to-end test drives `cadex mcp` against the real engine and reads entries back. `test_project_tool_surface.py` is unchanged [rec: forest-walrus-2370].
- **Page half (ADR-550, commit `50dce958`).** The overlay shows the newest call and its age, a recent-calls list of five, "idle" after 300 s, and the absence when there is no log; a browser test rewrites the fixture log. At 390 px the expanded overlay is 280 × 210 px, 20.8% of the viewport (bar 25%); collapsed it stays 40 px [rec: early-crow-5889].
- Suites with the GPU hidden: engine 2585 passed, 58 skipped; cli 1159 passed, 1 skipped; `test_review_overlay.py` 10 passed [rec: early-crow-5889].

**Open ends:** the collapsed overlay shows only the stage line, so activity is seen only when expanded — chosen to keep V1's "collapses to one line" [rec: early-crow-5889]. P1's route contract must list `activity` as a top-level key of `/api/project` [rec: forest-walrus-2370].

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-v4-page-says-what-agent)
- forest-walrus-2370 — ADR-549 bounded per-call activity log, read in /api/project; end-to-end test
- early-crow-5889 — ADR-550 overlay activity line, recent calls, 5-minute idle; V4 evidence complete
