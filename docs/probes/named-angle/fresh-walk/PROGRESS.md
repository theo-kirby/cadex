# hinged-arm — Progress

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
| 2026-09-07T23:42:48Z | script | de0dae7f | 8b676fdc | script --set script.py |  |
| 2026-09-07T23:43:07Z | train | de0dae7f | 8b676fdc | train 1 it × 4 envs → job.cxpolicy (stored) | reward/step -0.3802, 1.2 s, sha256 d3f5f777 |
| 2026-09-07T23:43:09Z | script | 9c476301 | 8b676fdc | script --set script.py |  |
| 2026-09-07T23:43:11Z | params | 6ebea031 | 0c74e228 | params policy_on=1 | total_reward -27.1 |
| 2026-09-07T23:43:12Z | walk | 6ebea031 | 0c74e228 | walk 1 it × 4 envs → PROJECT/runs/baseline | clearance offending 1; unknown 0; pairs checked 1 (initial solved pose; 0.1 mm / 1e-06 mm³) |
