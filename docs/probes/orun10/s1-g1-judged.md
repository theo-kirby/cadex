# orun10 S1: s1-g1 judged, checkpoint by checkpoint, and the next screen

Verified against source: 2026-10-17. Frozen evidence (orun10, iteration 5).

## What was judged

s1-g1 is the cold gallop sprint task (`gallop-task.md`), trained for 300
iterations. Seven policies were judged on its own `gallop_spec` over seeds
1001–1010, with the engine's evaluation on the CPU: the checkpoints at
50–250, the final policy (it 300), and `gallop.best`. The trainer moved its
best twice while the run went on, so `gallop.best` was judged as two files:
the copy at it 243, taken mid-run, and the final one at it 280. The judge is
`~/orun10-progress/s3/judge_gallop.py` (outside the repo). It is
`s1/judge_sprint.py` with the trained bundle's `success` (`gallop_spec`)
played unchanged, since that task has no goals. Each run writes
`orun10-cat/evaluations/s1-g1-<checkpoint>/evaluation.json`.

## Results (10 seeds each)

| checkpoint | pass | failing predicate (median) | top 2 s speed, m/s: min / median / max | flight strides | cycle: length × freq | flight per cycle | worst RMS / rated | peak ratio |
|---|---|---|---|---|---|---|---|---|
| 50 | 0/10 | top_speed (2051) | 2.022 / 2.051 / 2.099 | 0.74 | — | 30 ms | 1.27 (j_spine) | 1.000 |
| 100 | 0/10 | top_speed (3566) | 3.558 / 3.566 / 3.584 | 0.93 | 1.48 m × 2.38 Hz | 80 ms | 1.32 (j_elbow_l) | 1.000 |
| 150 | 0/10 | completes 0/10, upright 0/10 (33.8°), top_speed (2578) | 2.247 / 2.578 / 2.711 | 1.00 | — | — | 1.78 (j_spine) | 1.000 |
| 200 | 0/10 | top_speed (3795) | 3.785 / 3.795 / 3.818 | 1.00 | 1.58 m × 2.38 Hz | 100 ms | 1.36 (j_elbow_l) | 1.000 |
| 243 (best, mid-run) | 0/10 | completes 9/10, upright 9/10, top_speed (2462) | 2.368 / 2.462 / 2.552 | 0.85 | — | — | 1.50 (j_elbow_l) | 1.000 |
| 250 | 0/10 | top_speed (3306) | 3.255 / 3.306 / 3.374 | 0.97 | 1.35 m × 2.38 Hz | 100 ms | 1.43 (j_elbow_l) | 1.000 |
| 280 (final best) | 0/10 | top_speed (4248) | 4.232 / **4.248** / **4.258** | 1.00 | **1.77 m × 2.38 Hz** | 100 ms | 1.44 (j_scap_l) | 1.000 |
| 300 (final) | 0/10 | top_speed (3835) | 3.828 / 3.835 / 3.843 | 1.00 | 1.60 m × 2.38 Hz | 100 ms | 1.41 (j_elbow_l) | 1.000 |

No seed fell on any checkpoint. At it 280, `straight` has a median of
0.8° and `upright` 6.4°. A peak ratio of 1.000 means the worst drive is at
its clamp: its peak margin is 0. On it 280, the drives at peak on all 10
seeds include both shoulders and wrists, the left elbow, and the left hip,
knee and hock.

**S1 so far:** the best is 4.258 m/s on one seed, with a median of
4.248 m/s, at it 280. That is 0/10 against 5 m/s. It is the fastest gallop on
this cat. orun9's c1-c6 ran 2.74 m/s, and orun7's f1-g2 reached 4.25 m/s
on its earlier model.

## The stride: the left fore lands twice a cycle

The engine's stride clock is the left fore's touchdown (ADR-771). The
policy's left fore lands twice in each cycle, so a `stride` in
`evaluation.json` is half a cycle. Strides alternate between the orders
fl → fr and fl → hl → hr. The fl-clock medians are 0.90 m at 4.55 Hz for
it 280, and 0.72 m at 5.0 Hz for it 200. Taking the strides two at a time
gives the cycle (`~/orun10-progress/s3/cycles.py`). The table's cycle
columns are those pairs. The pairing is approximate on it 280, which has 65
four-foot fl → hl → hr → fr strides. As a check, its pairs give
1.771 m × 2.38 Hz = 4.22 m/s, against a mean speed of 4.15 m/s.

- **Every checkpoint's cycle is the reference's 2.38 Hz** (0.420 s). The
  policy holds the clip's 2.4 Hz clock. All of its gain from 3.5 to 4.25 m/s
  is **cycle length**: 1.48 m, then 1.58 m, then 1.77 m. That is orun7
  f1-g2's 1.77 m × 2.38 Hz exactly.
- There are two flights a cycle, 40–60 ms each, about 100 ms in all, as the
  clip has (0.35–0.5 and 0.85–1.0).
- **What binds (O8).** At a clock locked to 2.38 Hz, 5 m/s needs a 2.10 m
  cycle, 19% longer than the best yet. Every checkpoint is at a peak clamp,
  at the fore wrists and elbows and the hocks, as `o8-peak-phase.md` found
  for orun7's gallop. So a longer cycle at this clock asks more of drives
  that are already at peak. The other lever is a faster clip clock. The clip
  is a task key, so that would be a cold run.
- The trainer's best is not the fastest, and the reward is noisy: it 150
  and it 243 lost the line or tipped. Judging every checkpoint is what found
  it 280.

## The next screen: s1-g3

The track_speed cap of 5.5 m/s does not bind at 4.25 m/s, so raising the
"commanded" speed alone would change nothing below 5.5. Instead, the
project script (`orun10-cat` revision `490e682f`, project commit `b0fffd3`)
adds a parameter, `sprint_speed_w`. The screen raises the pay's ceiling to
`sprint_speed` = 7000 mm/s and its weight from 9 to 14. Pay per m/s rises
by 22% (14/7 against 9/5.5), and nothing caps it below 7 m/s. This is a
reward-only change. No new term was added, so no per-step evaluation was
run before training.

- s1-g2 was launched warm from it 200 before it 280 had been judged. It was
  stopped before its first iteration and never trained.
- **s1-g3** is warm from s1-g1's `gallop.best` (it 280), with
  `--critic-warmup 10`, 100 iterations and a checkpoint every 25. It was
  registered through `cadex_cli.loop` with `retain_training_view`, and runs in
  its own `systemd-run --user --scope -p MemoryMax=30G`.
- Its checkpoints are judged on `gallop_spec` by a later iteration. That
  spec is unchanged; only the reward moved.

## s1-g3 wiped; s1-g4 is the same screen at 3e-5

s1-g3 ran at the trainer's default learning rate, 3e-4. Through its ten
critic-only iterations it held reward/step at 16.4, and its episodes ran
the full horizon. Its first actor update (iteration 11) wiped the policy,
just as orun7–9 warned a warm start would be:

- reward/step fell from 16.44 to 8.8–13.0;
- σ rose from 0.416 to 0.52;
- mean episode length fell to 30–450 steps.

It was stopped at iteration 18. It wrote no checkpoint, so there is
nothing of it to judge.

**s1-g4** is s1-g3 unchanged except for `learning_rate` 3e-5. It runs
warm from s1-g1 it 280, on the same task (revision `490e682f`), for 100
iterations, with a checkpoint every 25. At iterations 11–15 reward/step
climbs 16.44 → 16.49, σ stays at 0.417–0.418 and episodes still run long.
The warm start survives. Its checkpoints are judged on `gallop_spec` by a
later iteration.
