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

## Two-mechanism complete-review comparison (2026-09-08)

Both fresh projects used the unchanged public script/walk entry point, one CPU
training iteration, four environments, training seed 0, rollout seed 3 and
50 rollout steps (one second, 50 Hz). Neither needed mechanism-specific
runner changes. The reviewing agent copied the example sensor notes and
committed this comparison after the automatic walk commit.

| Measurement | Hinged arm | Linear carriage |
|---|---:|---:|
| Training reward/step | -0.3801981508731842 | -82.31990814208984 |
| Rollout total reward | -27.109384220927513 | -24159.19535630446 |
| Rollout reward/step | -0.5421876844185503 | -483.1839071260892 |
| Policy witness maximum error | 1.3841167412209642e-09 | 5.41889473917867e-09 |
| Training compute (s) | 1.1770828749868087 | 1.0579057919676416 |
| Shared display acquisition (s) | 0.7093497079913504 | 0.6857212079921737 |
| Four-view rendering (s) | 0.5243987909634598 | 0.6373496250016615 |
| Section contour generation (s) | 7.558299694210291e-05 | 7.579103112220764e-05 |
| walk_seconds (s) | 16.351018832996488 | 16.048740583006293 |
| External whole command (s) | 16.61 | 16.39 |
| Sampled process-tree peak RSS (bytes) | 1059241984 | 987168768 |
| Components / catalogued | 2 / 0 | 2 / 0 |
| Checked / offending / unknown pairs | 1 / 1 / 0 | 1 / 0 / 0 |
| Initial pair distance (mm) | 0 | 34 |
| Initial common volume (mm³) | 0 | 0 |
| Section areas (mm²) | base 360; swing 640 | base 360; slide 400 |

Acquisition is shared by render and section and counted once. Rendering is
CPU rasterization into SVG; contour timing excludes serialization/writes.
walk_seconds excludes the final project commit; the external monitor includes
startup, that commit and process exit. RSS was sampled every 0.2 s with
2.9 GB / 850 s cutoffs and a 600 s trainer timeout. Both runs overlapped their
CLI gate, so timings are observations, not a speed benchmark.

The lift objective is -(com_z - 60 mm)^2 weighted by 1e-4 in both models;
the control cost uses abs(effort) weighted by -1e-6, but effort is N·mm for
the arm and N for the carriage. Different dynamics and effort units prevent
ranking these as policy improvements. The carriage falls under gravity with
this toy policy; the common metric shape proves review/comparison plumbing,
not useful control. Training-batch mean and rollout mean are distinct.

All four named views and the XZ section at Y=3.125 mm were visually inspected.
Carriage front/right show the cube above the plate, top shows its footprint,
and iso shows both volumes. The section contains two closed contours spanning
X=0..60/Z=0..6 and X=12..32/Z=40..60 mm. Neither example has a cavity.
Inventory truthfully has catalog fields but no catalogued synthetic parts.
The arm's base–swing contact remains offending at the 0.1 mm / 1e-6 mm³
thresholds; the carriage's base–slide pair is clear at 34 mm. These findings
are initial-pose only, not swept clearance; sections are tessellation cuts.
Rollout-leg, accepted project, render and section revision/digest agree;
clearance and inventory identify that revision. Policy hash, task hash,
reward and step count agree with trace metadata.

Next: combined evidence is ready for maintainer assessment of the headless
review criterion. GUI remains documented-only; remote remains scripted-only,
with local CPU stand-in parity already recorded in copper-timber-8947.
