---
node_id: 059f744b-b42e-5804-84c2-5f3047d40f77
slug: gilded-trail-2519
title: 'The rehearsal closes the round: one prompt, both traps dodged, two tool-surface gaps named'
created_at: '2026-08-29T13:40:11+00:00'
parents:
- staid-valley-0501
summary: ''
---
## What

The close of the local-training-loop round (commits 1b123535, 3dd84961 on
PR #12): the README/VISION/ROADMAP refresh, the final verification sweep,
and the **North Star rehearsal** — the balance-toy arc repeated on a fresh
project (`~/cadex-balance-ns`) as a single prompt to the product agent,
with the training and asset-staging legs supplied by a human when the
agent hit its tool boundary.

## Why

Owner decision in the round's plan: drive the arc by hand first (ADR-170),
then rehearse it agent-driven and log every place it needed help — those
places are the follow-up work the North Star needs.

## Method

- One `./cadex -p` prompt: the toy, the assembly, the MJCF export, the
  task, "train it if you can", with the two §7b traps given one sentence
  each. Then trained the produced bundle from the venv (400 it × 64 envs,
  44.3 s, reward −0.97 → +5.41 per step), resumed the turn with the
  sha256, staged the asset through cadexd `put_asset` when the agent
  reported it had no such tool, and resumed again with "go".
- Final sweep before that: engine suite 1910 passed / 46 skipped,
  `pixi run gate` OK, venv suites 46 passed;
  `hypergraph check --since main` 0 violations; PR #12 opened.

## Result

- **The arc closed agent-driven in 3 turns + 2 human legs.** Engine trace:
  +1729.95 total reward against −302.17 zero-torque, full 300-step
  horizon, arm 2.1° off vertical at t = 3 s and 5.7° at t = 6 s; the
  agent ran the ADR-092 bracing check unprompted (holding torque ±5 N·mm
  of 25, sign-changing) and verified against a randomisation-varied
  mechanism with both shoves fired.
- **Both traps dodged from one sentence each** — and the agent's
  collision fix (contact-group bitmasks) was better than ADR-170's
  box-collision swap. It also self-corrected a solver-flattened rest pose
  and 14× critical damping from in-engine evidence alone.
- **Two tool-surface gaps named** (the round's actionable output): the
  CLI agent has no shell — it cannot run the trainer and cannot read
  `training/SETUP.md`, so the command it handed back had guessed, wrong
  flags; and no `put_asset` — it cannot bring a policy home. Both
  refusals were clean, precise and resumable. Follow-up candidates:
  add `put_asset` to the CLI tool surface, and either a training
  dispatcher or the trainer's invocation shape in the agent's contract.
- Recorded in `docs/MUJOCO.md` §7b (commit 3dd84961). The in-app agent
  has a shell and does not share the first gap; that variant remains
  worth one interactive run.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: local-training-loop
- commit: 3dd849617b1127a5dcc78b19cd3c2d3a0f880b70

## State Impact

- target: late-pond-2851 — The agent-driven rehearsal closed the toy arc (+1729.95 vs -302.17, holds inverted) and named the two gaps between here and the North Star as one CLI prompt: the CLI agent has no shell and no put_asset. Those are the frontier's next moves.
