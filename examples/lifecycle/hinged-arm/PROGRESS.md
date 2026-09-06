# hinged-arm — Progress

One row per run the `cadex` CLI accepted, newest last. Written by the
CLI from what actually happened; read by the agent on every visit. A
number a previous row also carried shows its change against that row,
as `total_reward 127.8 (Δ -1602.1 vs 2996fb73 at 1729.9)`: the delta,
the digest of the run compared against, and that run's value. The rows below
are CLI receipts; this example is versioned by the parent repository, as
explained in the comparison below.

| When (UTC) | Run | Revision | Digest | What | Numbers |
|---|---|---|---|---|---|
| 2026-09-06T20:35:25Z | script | fbf64f89 | 8b676fdc | script --set script.py |  |
| 2026-09-06T20:35:36Z | train | fbf64f89 | 8b676fdc | train 1 it × 4 envs → job.cxpolicy (stored) | reward/step -0.3802, 1.3 s, sha256 c67bbe80 |
| 2026-09-06T20:35:38Z | script | dc0ab988 | 8b676fdc | script --set script.py |  |
| 2026-09-06T20:35:40Z | params | 60690883 | 39d0b57e | params policy_on=1 | total_reward -27.1 |

## Baseline comparison — 2026-09-06

Both runs use the unchanged `cadex walk`: local CPU, 1 PPO iteration × 4
environments, training seed 0, verified rollout seed 3, 1 s at 50 Hz (50
steps), lift weight 1e-4 and control-cost weight -1e-6. All train, declare
and rollout legs exited 0, and both traces reached the 50-step horizon
without early termination. This proves pipeline coverage, not learned control.

`total_reward` is the sum of the verified trace's after-step rewards;
rollout reward/step divides it by its `policy.step_count` (50).
Trainer reward/step is the receipt's final training-batch mean, with
exploratory actions across four environments; it is not the verified
rollout mean. Walk wall time includes all child commands. RSS is the sum
over the walk process tree, sampled every 0.2 s; a watchdog stopped at
2.9 GB or 850 s, and the trainer also had `--timeout 600`. Neither guard
fired. Sampling is an observed peak, not an exact allocator high-water mark.

| Mechanism | Rollout total_reward | Rollout reward/step | Trainer reward/step | Walk wall seconds | Peak process-tree RSS bytes |
|---|---:|---:|---:|---:|---:|
| hinged-arm | -27.1093842209 | -0.542187684419 | -0.380198150873 | 15.22 | 986218496 |
| linear-carriage | -24159.1953563 | -483.183907126 | -82.3199081421 | 13.52 | 979582976 |

The height term is identical: `-1e-4*(com_z-60)^2`, with `com_z` in mm.
The effort term is `-1e-6*abs(effort)`, but effort is N·mm on the arm and
N on the carriage. Thus total-reward columns have comparable definitions,
but their objectives are not physically equivalent and do not rank designs.
The carriage is an unconstrained ideal vertical guide with no stops or
contact; a nearly untrained policy lets it fall far below its target
(final component-origin z = -4699.378313 mm at 1 s).
No reward weight was tuned to improve the reported score.

Source recipes are reset to `policy_on=0` with a placeholder digest for
fresh training. Policies, accepted caches, checkpoints and traces remain
local and untracked. These projects belong to the parent Cadex repository;
its one experiment commit carries source, documents and numbers, rather
than a nested repository or a commit per CLI row. See `../README.md`.

Verified policy sha256: `c67bbe80598f2df1605b44f40105a9c5b29fc46625a179bcd8f37fed2bd48812`.
Task sha256: `c4315071d146843471098bb1386a3d8c5740b9bae8cf0a36685aa6c4869b2920`.
Witness error: `1.38411674122e-09`.
