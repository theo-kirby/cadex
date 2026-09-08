# cadex-nt3-i18-arm — Progress

One row per run the `cadex` CLI accepted, newest last. Written by the
CLI from what actually happened; read by the agent on every visit. A
number a previous row also carried shows its change against that row,
as `total_reward 127.8 (Δ -1602.1 vs 2996fb73 at 1729.9)`: the delta,
the digest of the run compared against, and that run's value. Each row
is one commit in the project's own repository (`git log` is this table).

For lifecycle comparisons, record iterations, environment count and seeds.
`total_reward` sums rewards over the verified rollout's `step_count`;
divide by that count for rollout reward per step. The trainer's
`reward/step` is its final training-batch mean, a different measurement.
Compare objectives only when reward expressions, weights, units and
episode lengths match; a larger reward after changing them is not progress.

| When (UTC) | Run | Revision | Digest | What | Numbers |
|---|---|---|---|---|---|
| 2026-09-08T00:13:50Z | script | de0dae7f | 8b676fdc | script --set script.py |  |
| 2026-09-08T00:14:10Z | train | de0dae7f | 8b676fdc | train 1 it × 4 envs → job.cxpolicy (stored) | reward/step -0.3802, 1.2 s, sha256 1a8df33f |
| 2026-09-08T00:14:12Z | script | 8dadb374 | 8b676fdc | script --set script.py |  |
| 2026-09-08T00:14:13Z | params | c84dfda0 | 7ad3cf79 | params policy_on=1 | total_reward -27.1 |
| 2026-09-08T00:14:15Z | walk | c84dfda0 | 7ad3cf79 | walk 1 it × 4 envs → <project>/runs/baseline | clearance offending 1; unknown 0; pairs checked 1 (initial solved pose; 0.1 mm / 1e-06 mm³) |

## Fresh complete-review rehearsal (2026-09-08)

One CPU iteration, four environments, training seed 0; rollout seed 3,
50 steps. Training reward/step -0.3801981508731842; rollout total reward
-27.109384220927513, mean -0.5421876844185503 per step; witness error
1.3841167412209642e-09. These are toy task measurements, not learned robotics.

Shared display acquisition 0.7093497079913504 s (count once); four-view
rasterization 0.5243987909634598 s; section contours 0.00007558299694210291 s.
Contour time excludes serialization/writes; walk_seconds 16.351018832996488 s
ends before final project commit. External whole-command time 16.61 s includes
that commit and process startup/exit; sampled process-tree peak RSS
1,059,241,984 bytes, sampled every 0.2 s under 2.9 GB/850 s cutoffs.

Four named previews and XZ at Y=3.125 mm inspected. Section areas: base
360 mm², swing 640 mm². Inventory: two synthetic components, zero catalogued.
Clearance: base–swing 0 mm distance, 0 mm³ common volume; one offending pair,
zero unknowns, one checked, at 0.1 mm / 1e-6 mm³ thresholds. Initial pose only.
Rollout, render and section revision/digest match; clearance revision agrees.
Next: compare with a fresh carriage run using identical measurement boundaries.
