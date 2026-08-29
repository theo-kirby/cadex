---
node_id: c3195649-81d8-5ff8-91b3-8deefa0153f1
slug: staid-valley-0501
title: 'ADR-170: the balance-toy litmus closes the local CPU loop end to end'
created_at: '2026-08-29T13:00:17+00:00'
parents:
- dry-garden-5337
summary: ''
---
## What

Phase 4 of the local-training-loop round (commit bbb6fba2, ADR-170,
`docs/MUJOCO.md` §7b): the balance-toy litmus — the entire §7 arc run
locally on the M4 Mac Mini (16 GB, CPU-only) against a desk toy at
`~/cadex-balance`, from an agent-authored script through training,
verification, rollout, and the shell with the ADR-169 plot live.

## Why

The North Star prompt (quadruped, MG90s, 3D-printable, trained to walk
and wave, end to end by the agent) needs the loop rehearsable at toy
scale with live visibility before gait scale is worth attempting.

## Method

- Toy authored via one `./cadex -p` turn: puck ⌀80×12, post 15×15×120,
  arm 90×12×6 hinged at its end, MG90-class motor (200 N·mm), PLA 1240,
  tip-height reward + spin cost, StartKick + MidEpisodeShove. The turn
  hit the Claude session limit mid-flight but its rebuild had already
  been accepted.
- Two script fixes applied through cadexd's own `write_script` accept
  path (never hand-editing; backups taken): puck collision cylinder→box
  (MJX refuses cylinder↔box pairs), and the spin-out guard 3000→12000
  deg/s (one σ exploration action ≈ 3200 deg/s/step on this arm — the
  guard was ending episodes in 3.7 steps and had become the curriculum).
- Trained per SETUP.md §b: 300 it × 64 envs (61.6 s) + 500 warm-started
  (79.1 s), peak RSS 2.2 GB, `--progress` at the project root.
- Policy home: `put_asset` + `assembly.policy` + `assembly.rollout`,
  accepted; the engine verified (witness 3.0e-08) and published the
  trace.
- Measured recovery (32 seeded episodes) and a capability sweep over
  shove scale ×1..×300 with the engine's own `evaluate_episode`.
- Windowed probes against the built bundle: the Training editor
  screenshot shows the panel + the ADR-169 reward-curve plot drawing
  the real 500-point curve with the best marker; the viewport shows the
  toy with the 52-frame baked rollout (arm inverted mid-hold).

## Result

- Reward 0.77 → 1.85 against a ~2.16 inverted-hold ceiling; rollout
  215.0 vs 87.8 zero-torque over the full 100-step horizon.
- Recovery 32/32 at the declared band; sweep: 16/16 at ×1/×10/×30,
  9/16 at ×100 (15 N), 6/16 at ×300 — the declared band was toothless
  (§7 step 9's lesson, measured again).
- Findings recorded in §7b: reset_variation refuses grounded mechanisms
  (StartKick adaptation is the pattern); MJX cylinder↔box gap with no
  engine export-time warning yet; guard-vs-exploration sizing rule
  (σ·τ/I·Δt); ADR-093's warp stdout lines met again.
- `device: "cpu"` in the header recorded as a feature.
- **Still pending**: the North Star rehearsal as a single in-app chat
  prompt on a fresh project — blocked by the Claude session limit
  (resets 16:30 Europe/Madrid); to be attempted at close-out.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: local-training-loop
- commit: bbb6fba274d7ccb5c350e4dd64d46c3141f3f4d5

## State Impact

- target: late-pond-2851 — The whole training arc now runs locally on the M4 (agent-authored toy → CPU training → verified policy → rollout → live plot in the editor, MUJOCO.md 7b). The GPU-box blockage now gates only gait-scale runs, not the loop itself.
