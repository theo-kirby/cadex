---
node_id: 2ea34d38-3ca0-5437-83d9-b2c93724fcc9
slug: eager-basin-6116
title: The chat shows the running turn and the session's cost (ADR-453)
created_at: '2026-09-29T12:34:09+00:00'
parents:
- peaceful-sail-5197
summary: ''
---
## What
GUI-parity slice 8 (ADR-453): the app's chat shows the running turn's clock and tool count, and after each turn its tokens and cost plus the conversation's totals.

## Why
Watch long agent runs in the app (warm-spire-8762): a 20-minute turn read "Thinking…" throughout, like a hang, and its cost was invisible.

## Method
- `agent.py`: `turn_stats` / `session_stats`; `usage_from` normalizes Claude Code (`usage`, `total_cost_usd`), Codex (`turn.completed` usage, now passed on by the backend) and pi (per-message usage, now summed by the backend) with the prompt counted cache-inclusive; 1 s redraw while busy; reset on new conversation.
- `ui.py`: `Thinking…  2m 10s · 14 tools`; after a turn, `last turn: …` and `session: …` lines.
- Backends add `usage` to result frames only when non-empty, so frame-exact translator tests hold.

## Result
- No-engine suite: exit 0, 14 new checks.
- `pixi run gate`: only the 8 pre-existing restore-lockout failures. First run's slider median 0.603 s (two outliers, 0.814 and 0.721); rerun 0.556 s. Judged machine noise: slice 8 does not touch the slider path.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: gui/session-monitor
- commit: 6ad529aefd663bde92aa3901ed2d685e9b333d9f

## State Impact

- target: shy-crane-2573 — the app's chat shows the running turn's clock and tool count, and each turn's and the session's tokens and cost as the harness reports them (Claude Code, Codex, pi normalized) (ADR-453)
