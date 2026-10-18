# orun10 S1: s1-g4 judged, checkpoint by checkpoint, and s1-g5

Verified against source: 2026-10-17. Frozen evidence (orun10, iteration 7).

## What was judged

s1-g4 is s1-g1's `gallop.best` (it 280, 4.258 m/s) warm-started on the
gallop task with a reward-only change: speed paid to 7 m/s at weight 14
(`s1-g1-judged.md`). It ran at learning rate 3e-5 for 100 iterations, with
a 10-iteration critic warm-up and a checkpoint every 25. Its trainer reward
per step rose from 16.44 to 17.23, and σ fell from 0.416 to 0.402.

The trainer wrote checkpoints at 25, 50 and 75, `gallop.best` (it 99) and
the final policy (it 100). It wrote no `.000100` file: the final policy is
the it-100 checkpoint. All five were judged on the trained bundle's own
`gallop_spec` over seeds 1001–1010, with the engine's evaluation on the CPU
(`~/orun10-progress/s3/judge_gallop.py`). Each run writes
`orun10-cat/evaluations/s1-g4-<checkpoint>/evaluation.json`. Cycles are the
fl-clock strides paired two at a time (`~/orun10-progress/s3/cycles.py`).

## Results (10 seeds each)

| checkpoint | pass | failing predicate (median) | top 2 s speed, m/s: min / median / max | flight strides | cycle: length × freq | flight per cycle | worst RMS / rated | peak ratio |
|---|---|---|---|---|---|---|---|---|
| s1-g1 it 280 (start) | 0/10 | top_speed (4248) | 4.232 / 4.248 / 4.258 | 1.00 | 1.77 m × 2.38 Hz | 100 ms | 1.44 (j_scap_l) | 1.000 |
| 25 | 0/10 | top_speed (4341) | 4.334 / 4.341 / 4.355 | 1.00 | 1.80 m × 2.38 Hz | 120 ms | 1.45 (j_elbow_l) | 1.000 |
| 50 | 0/10 | top_speed (4263) | 4.246 / 4.263 / 4.286 | 1.00 | 1.77 m × 2.38 Hz | 120 ms | 1.41 (j_elbow_l) | 1.000 |
| 75 | 0/10 | top_speed (4363) | 4.354 / 4.363 / 4.366 | 1.00 | 1.82 m × 2.38 Hz | 120 ms | 1.45 (j_elbow_l) | 1.000 |
| 99 (best) | 0/10 | top_speed (4486) | 4.466 / 4.486 / 4.498 | 1.00 | 1.86 m × 2.38 Hz | 120 ms | 1.49 (j_elbow_l) | 1.000 |
| 100 (final) | 0/10 | top_speed (4486) | 4.466 / **4.486** / **4.498** | 1.00 | **1.86 m × 2.38 Hz** | 120 ms | 1.49 (j_elbow_l) | 1.000 |

Worst RMS / rated is the median over seeds of each seed's worst drive. No seed fell on any checkpoint, and every one fails only `top_speed`. On
the final policy, `upright` has a median of 6.4° and `straight` 2.8°. The
best (it 99) and final (it 100) files differ (`ef7843c9…` against
`a84f7551…`), but they judge identically on every seed, to the millimetre
per second.

A peak ratio of 1.000 means the worst drive is at its clamp, so its peak
margin is 0. On the final policy, the drives at peak on all 10 seeds are the
left scapula, shoulder, elbow, wrist, knee and hock, and the right elbow and
wrist. The worst drive's RMS over rated is the left elbow's, 1.47–1.50×.

**S1 so far:** the best is 4.498 m/s on one seed, with a median of
4.486 m/s, on s1-g4's final policy. That is 0/10 against 5 m/s, and
+0.24 m/s over s1-g1's best.

## What it shows (O8)

- **The clock is still 2.38 Hz on every checkpoint.** The gain is cycle
  length alone, 1.77 → 1.86 m. Flight per cycle grew from 100 to 120 ms:
  two flights of 60 ms. The footfall orders are unchanged, fl → fr and
  fl → hl → hr.
- **The speed did not plateau.** The top speed climbed 4.36 → 4.49 m/s over
  the last 25 iterations, and the trainer's reward was still rising at
  it 100. O7 says extend while the curve climbs, so the next run is a warm
  extension, not the cold faster-clip run. At 2.38 Hz, 5 m/s needs a 2.10 m
  cycle, 13% longer than 1.86 m. More of the same drives are at peak, and
  rated RMS rose with the speed (medians 1.45 → 1.49×).
- **The faster clip is ready.** The orun10-cat script now has a
  `gallop_hz` parameter (revision `b7181a04`, project commit `6aecd68`).
  It sets the reference clip's clock, and the clip's speed is 0.7 m ×
  `gallop_hz`. At its default of 2.4 the gallop task is byte-identical to
  s1-g4's (task `c198a097…`, checked at s1-g5's registration). The
  generator reaches the 0.7 m clip at duty 0.25 and swing 60 mm at 2.4,
  2.8, 3.0 and 3.2 Hz alike (`~/orun10-progress/s5/reach_hz.py`). A
  40 mm swing is refused at every one of those clocks, as it was at
  2.4 Hz. Moving `gallop_hz` is a task-key change, so it means a cold run.
  A rebuild at 3.0 Hz was started and stopped before it was accepted, since
  the 2.4 Hz curve was still climbing. The accepted revision stays at 2.4.

## s1-g5

s1-g5 is warm from s1-g4's final policy (it 100), on the same task, with no
task change. It runs at learning rate 3e-5, with a 10-iteration critic
warm-up, for 100 iterations, with a checkpoint every 25. It was registered
through `cadex_cli.loop` with `retain_training_view`, and runs in its own
`systemd-run --user --scope -p MemoryMax=30G`. Through iteration 13 the
warm start holds: reward/step is 16.95 → 17.02 and σ is 0.397–0.399. A
later iteration judges its checkpoints on `gallop_spec`. If the top speed
stalls below 5 m/s with the clock at 2.38 Hz, the next run is the cold one
at `gallop_hz` 3.0.
