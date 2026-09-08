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
| 2026-09-08T00:31:22Z | script | de0dae7f | 8b676fdc | script --set script.py |  |
| 2026-09-08T00:31:42Z | train | de0dae7f | 8b676fdc | train 1 it × 4 envs → job.cxpolicy (stored) | reward/step -0.3802, 1.2 s, sha256 3c12fa09 |
| 2026-09-08T00:31:45Z | script | e65b7f71 | 8b676fdc | script --set script.py |  |
| 2026-09-08T00:31:46Z | params | 61cf8114 | 66320986 | params policy_on=1 | total_reward -27.1 |
| 2026-09-08T00:31:48Z | walk | 61cf8114 | 66320986 | walk 1 it × 4 envs → <project>/runs/baseline | clearance offending 1; unknown 0; pairs checked 1 (initial solved pose; 0.1 mm / 1e-06 mm³) |
| 2026-09-08T00:32:16Z | inventory | — | — | inventory → docs/inventory.md |  |
| 2026-09-08T00:32:16Z | clearance | — | — | clearance → docs/clearance.md |  |
| 2026-09-08T00:32:18Z | render | 61cf8114 | 66320986 | render → review/render/ (front, top, right, iso) |  |
| 2026-09-08T00:32:19Z | section | 61cf8114 | 66320986 | section → review/section/ (XZ, 3.125 mm) |  |

## Cold revisit — 2026-09-08

Fresh local CPU walk: one iteration, four environments, seed 0; training reward/step -0.3801981508731842, witness error 1.3841167412209642e-09. Rollout seed 3, 50 steps, total reward -27.109384220927513, mean -0.5421876844185503. Whole command 16.80 s, sampled process-tree peak RSS 1,056,636,928 bytes. Toy compatibility evidence, not useful control.

Fresh-process script, asset, inventory, clearance, render and XZ section (Y=3.125 mm) all exited 0. Accepted revision/digest and policy identity preserved. Four SVGs and section SVG equal committed baseline bytes; geometry summaries equal apart from command paths, wrapper fields and timings. Inventory and clearance byte-identical: two synthetic components, zero catalogued; base–swing 0 mm distance / 0 mm³ common volume, one offending pair, zero unknowns. Section areas 360 and 640 mm². Initial pose only. Restore restages attempts; review commands append progress rows. No recovery or cache deletion was needed.
