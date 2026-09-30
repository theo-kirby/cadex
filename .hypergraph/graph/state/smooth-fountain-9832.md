---
node_id: a42d8504-4b29-5497-8c42-2d9874704b88
slug: smooth-fountain-9832
title: R1. A quadruped walks with real steps
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **R1. A quadruped walks with real steps.** - The final pre-registered confirmation evaluation passes the frozen walk spec on every evaluation seed, and meets the video judge's bar. - The policy is installed, verified and reopened through the supported path, on an accepted design. That design may be one of ot10's, copied into a new `ot11-*` project. - Every earlier training run and evaluation is published, including the failures. [rec: kind-spire-3578]

Declared target: `gap-r1-quadruped-walks-real-steps`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

**R1 is started; nothing is evaluated yet** [rec: lively-ledge-7354].

- **Project.** `ot11-quad-1`, a `cp -a` copy of `ot10-quadruped-3-w2` at accepted revision `84ff4c98…`. The mechanism is fixed for the session because HIP_MM (96.7006), WEIGHT_N and SPEC_LIFT are this model's; reopening it later is its own recorded decision [rec: lively-ledge-7354].
- **Spec.** The frozen walk spec as a thirteen-predicate xscript block with a commanded-speed goal in [0.6, 1.0] hip heights/s (`retained/walk-spec-block.txt`, sha256 `487416af…`); W3 as `speed_ratio` in [0.75, 1.25], W4 as `lateral_ratio` ≤ 0.25 plus `max_heading_deg` ≤ 45; 10 s, tilt 0–3°, one 0.05–0.20 × weight shove for 0.15 s between 3 s and 7 s. It appears verbatim in the accepted script (revision `db1cfc96…`); an evaluation whose spec block differs from the retained one is void [rec: lively-ledge-7354].
- **Session.** Walk loop pre-registered and committed before GPU time (`626141c8`: `retained/p4-quad-1-preregistration.json`, `prompts/walk.loop.prompt.txt` `13386046…`); unchanged `runner/rounds.py`, at most 4 runs of ≤ 2400 s each, stop-on-collapse, claude-opus-5-5 with no fallback; output in `~/cadex-projects/ot11-notes/quad-1/`. The prompt says nothing about how to reward a gait [rec: lively-ledge-7354].
- **Round 1** `r1-clearance` (seed 7, 1000 it × 2048 envs, 2350 s budget) is registered and training. The agent's design charges foot-height error × foot speed, feet sinking and diagonal desync; it hit the 16-reward-term limit and an "expression is too complex" refusal and restructured to 15 terms on its own; its MJCF differs from `w2-2`'s only by added foot `subtreecom`/`subtreelinvel` sensors [rec: lively-ledge-7354].
- **While the session is alive** (`pgrep -f "rounds.py --project ot11-quad-1"`, up to ~3 h), no other GPU job is started [rec: lively-ledge-7354].

## Negative knowledge

- [scope: checking an xscript edit on a project copy | confidence: high | evidence: lively-ledge-7354] `cadex params` rewrites `script.py` from the accepted revision, so a hand edit followed by `params` is silently lost; the spec check was redone with `cadex script --set`.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- lively-ledge-7354 — R1 started: ot11-quad-1 copied, full walk spec with speed goal pre-registered (626141c8), round 1 r1-clearance training
