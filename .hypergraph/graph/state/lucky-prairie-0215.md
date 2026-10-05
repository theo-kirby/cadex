---
node_id: 56c3b7df-f631-5bd3-a580-a8bac365847e
slug: lucky-prairie-0215
title: W1. The whole lifecycle is watchable, on a real robot
created_at: '2026-10-05T08:57:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open orun3 charter criterion: **W1. The whole lifecycle is watchable, on a real robot.** [rec: golden-snow-6627]

- On `orun3-biped`, a copy of `~/cadex-projects/ot5-biped`: 1. the agent accepts at least two new design revisions through `cadex mcp`; 2. a short `cadex walk` training leg runs on the 5090 with checkpoints on; 3. `evaluate` runs on the result. [rec: golden-snow-6627]
- The dashboard, opened before step 1 and never reloaded, shows each stage in the overlay, the revisions on the timeline, and at least three checkpoint rollouts. Screenshots are taken at each stage. [rec: golden-snow-6627]
- Both full suites pass, and so does the packaged lifecycle gate if the run touched the protocol or the payload. [rec: golden-snow-6627]

Declared target: `gap-w1-whole-lifecycle-watchable-real`. It becomes working only with measured evidence, in a causally parented record, that the criterion is met. The owner ticks the charter box; roles do not. [rec: golden-snow-6627]

### First attempt (not met) [rec: solemn-fox-1118]

Measured on a never-reloaded page (one navigation entry), driver an uncommitted MCP-client script acting as the agent:
- **Shown:** `designing` (revisions 16 and 17 within one poll, feet tinted on the timeline against a revision-15 ghost; Revisions menu agreed), `training` (overlay on run `orun3-w1b` 4 s after `cadex walk` started; 120 iterations at 1024 envs on the 5090, walk exit 0 in 581 s; **5 checkpoint rollouts ready** during training, iterations 20–100), and `failed` (the first walk's ungrounded-channel refusal, exit 3). The second leg ran with `--allow-ungrounded` — a reversible assumption that grounding is design work, not watching. [rec: solemn-fox-1118]
- **Gap 1, product defect: `evaluate` is invisible.** The evaluation directory exists ≈0.23 s of a ≈68 s MCP call (the rest is the session's engine build), so the 2 s poll never sees `evaluating`; the activity log (ADR-549) writes a call only on return. Suggested fix: log a call's start as an in-flight activity entry and read an in-flight `evaluate` as `evaluating` (no tool-surface change). [rec: solemn-fox-1118]
- **Gap 2, driver error: no checkpoint played live.** The driver's Revisions-menu pick set `ckpt.chosenSource` (`review.js:938`), and ADR-545 holds a hand pick for the visit; on a fresh page the follow plays the same traces. Re-run should pick `run:<run>` in `#view3d-source`, or an ADR decides whether a new run overrides a hand pick. [rec: solemn-fox-1118]
- Partial screenshots: `docs/probes/orun3/w1-try-{designing-timeline,training,failed}.png`. Suites not run (no code changed); still owed on the final run. [rec: solemn-fox-1118]

## Negative knowledge

- [scope: `orun3-biped` as copied from `ot5-biped` | confidence: medium | evidence: solemn-fox-1118] Its policy channels are not grounded in onboard sensors, so `cadex walk` refuses training without `--allow-ungrounded`.
- [scope: a short `evaluate` through `cadex mcp` with the ADR-549 return-only activity log and the 2 s poll | confidence: high | evidence: solemn-fox-1118] The `evaluating` stage and the call's activity line are not observable while the call runs.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-w1-whole-lifecycle-watchable-real)
- solemn-fox-1118 — first full attempt: designing/training/failed shown, evaluate invisible, live checkpoint play blocked by a menu pick
