# orun19 L1: the long run, l1-dog (launch), and seed 1007's tip at reset

Verified against source: 2026-10-23. Charter L1, first part: the launch.
Not judged yet. When the run ends it is judged at 2.76, 3.5 and 4.23 m/s
beside m2-dog-150, with the same tables (`s1_tables.py`, `ref_tables.py`,
orun18's `b1_summary.py`).

## Why m2-dog

S2, M1 and M2 are all judged. On a command it tracks (O3), m2-dog-150
(`863845a8`) is the faster policy: 4.36 m/s held at 3.5 against s2a-hold-150's
4.08. The owner ranks faster higher, so the critic picked it for L1
(iteration 16). The cost: it cannot be commanded below the bundle's 2.76 m/s,
and it lost one seed (1007) at reset at 4.23 (below).

## The launch

O5's long run is a warm start from a screen on the same task.
`queue_warm.py` (this folder) is orun18's `queue_bundle.py` with one setting
added, `init_from`. No `init_from_parent_task` is passed, because the task has
not changed. The trainer checks that the policy fits the bundle's model and
channels.

```
systemd-run --user --scope -p MemoryMax=30G env PYTHONPATH=cli pixi run python \
    docs/probes/orun19/queue_warm.py ~/orun19-queue/m2-dog-150.cxpolicy \
    ~/cadex-projects/leo l1-dog ~/mocap/ai4animation/m2-bundle/mocap_gallop-task.json 6200 250 \
    "orun19 L1: m2-dog-150 (863845a8) read best (4.36 m/s tracked at 3.5); warm-started on the same dog bundle for 250 more iterations to see what length buys" \
    --base-task speed --seed 1 --envs 4096
```

- **The run:** `l1-dog` was launched at 20:23:32 on leo revision `4ff224d2`.
  Its task is `mocap_gallop` `8e9e53fc`, M2's own bundle (sha256 checked), in
  place of `speed` `c5e8223c`, on model `f9b8ab82`.
- **Settings:** a warm start from `863845a8` (150 iterations, σ 0.580).
  - The actor's normaliser carries the source's 12.3 M samples.
  - Seed 1, not M2's 0. The new seed gives fresh rollouts, and it is not an
    evaluation seed.
  - 4096 envs, 250 iterations, a checkpoint every 25.
  - Budget 6,200 s.
- **Timing (O5):**
  - Compile: iteration 0 came at 20:27:40, about 250 s after launch.
  - Iterations 0–10 took ≤ 184 s, ~18.4 s an iteration, with the M2 film
    rendering on the CPU beside the trainer.
  - Iterations 10–36 ran ~22 s an iteration while the film was still
    rendering. It finished at 20:34.
  - At 18.4–22 s an iteration, 250 iterations take 4,600–5,500 s. The 6,200 s
    budget was set at launch from M2's 20.6 s (3,091 s for 150), and the
    supervisor reads it only then. That makes it +13% to +35% over the
    measured range. If it binds, the run ends `budget_exhausted` on its last
    25-iteration checkpoint.
- **First iterations:**
  - Reward per step is 29.8 at iteration 0, against the source's 30.1 at its
    end. It dipped to 28.8 by iteration 10 and was back to 29.8 at 36.
  - The value loss starts at 2,850 and falls to 190 by iteration 36. The
    critic is relearned from scratch, as in any warm start.
  - σ rose from 0.580 to 0.587.

## Seed 1007: the reset draw, not the pose alone

At 4.23 m/s m2-dog-150 lost seed 1007 at 0.42 s, and v05's c3-s1-50 lost the
same seed at 0.44 s on 2756. `reset_draws.py` (this folder, standard library)
reads what each seed drew at reset from `evaluation.json`, and the chest's
start pose and early pitch from each trace.

`python3 docs/probes/orun19/reset_draws.py ~/cadex-projects/leo/evaluations/m2-dog-150-{3500,4230}`:

| seed | mass factor | kick m/s | kick rad/s | start pitch ° (3.5 / 4.23) | pitch max ° in 0.42 s (3.5 / 4.23) | max tilt ° (3.5 / 4.23) |
|---|---|---|---|---|---|---|
| 1001 | 1.059 | 0.061 | 0.209 | +1.3 / +2.8 | +2.5 / +10.7 | 10.8 / 11.7 |
| 1004 | 0.984 | 0.127 | 0.173 | +2.7 / −1.3 | +2.7 / +1.8 | 10.6 / 12.4 |
| 1009 | 0.936 | 0.122 | **0.238** | −9.5 / −7.8 | +3.4 / +4.1 | 11.0 / 10.9 |
| 1010 | 1.034 | 0.109 | 0.111 | **+6.8 / +5.9** | +12.5 / +7.7 | 12.7 / 11.8 |
| **1007** | **1.071** | **0.146** | 0.196 | +4.8 / **+6.1** | +12.0 / **+22.9** | 13.9 / **34.4 (0.42 s)** |

The other five seeds sit inside these ranges.

- **The start pose is the reference at a start phase the seed draws.** It is
  the same on v05 and v06, and it changes with the command, because the
  stride blends with speed. So frame 0 differs from seed to seed:
  - the chest pitch spans −9.5° to +9.9° across seeds and commands;
  - 1007 starts nose-up at +4.8° to +6.1°.
- **The pose alone does not tip it.** Seed 1010 starts as far up or further
  (+5.9° to +9.9°) and survives at every command, on both policies.
- **The draw is the outlier.** 1007 is the heaviest of the ten seeds (mass
  ×1.071) and has the largest linear kick (0.146 m/s), with an angular kick
  near the top (0.196 rad/s; 1009 is highest at 0.238 and starts nose-down).
- **The tip grows with the command.** On m2-dog-150, 1007 already pitches
  the most at 3.5 (+12.0° in 0.42 s, 13.9° max, the highest of the ten).
  At 4.23 the pitch reaches +22.9° and the chest rolls +24° before the 30°
  tilt limit stops it.
- **v05 lost it too, but at its slowest command.** On c3-s1-50 at 2756,
  seed 1007 draws the same mass, kick and start pose (+6.0°), pitches +25.1°
  and stops at 0.44 s, at 35.5°. It survives 3395, 3800 and 4233. So on v05
  the command is not what makes the draw fatal.

So the cause is a draw at the edge of the training distribution: the
heaviest mass, the strongest push and a nose-up start, together. Two
different policies fail to catch it in their first stride, each at one
command: m2-dog-150 at its fastest and c3-s1-50 at its slowest. The start pose alone is not the cause. This is read from the
recorded draws and traces. No counterfactual rollout was run, such as 1007's
start phase with another seed's mass and kick, so the share each part takes
is not measured. L1's judgement at 4.23 shows whether the extra iterations
catch it.
