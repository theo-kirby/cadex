# orun10 S1: s1-g6, the 3.0 Hz clip, judged at every checkpoint

Verified against source: 2026-10-18. Frozen evidence (orun10, iterations 9 and 10).

s1-g6 trains the gallop task cold with its reference clip at 3.0 Hz
(orun10-cat `6cd54655`, `gallop_hz=3.0`; `s1-g5-judged.md`): 200 iterations,
a checkpoint every 50. Each checkpoint is judged as it lands, on the bundle's
own `gallop_spec`, seeds 1001–1010, with the engine's evaluation
(`orun10-cat/evaluations/s1-g6-*`, `judge_gallop.py`). The clock is each
foot's touchdown rate from the engine's strides, t ≥ 1 s (`rates.py`); the
cycle is the 2 s top speed over that clock.

| checkpoint | pass | failing (median) | top 2 s speed, m/s: min / median / max | strikes/s fl / fr / hl / hr | cycle | flight | footfall order | worst RMS / rated | peak margin |
|---|---|---|---|---|---|---|---|---|---|
| s1-g1 at 50 (2.4 Hz, for scale) | 0/10 | top_speed (2051) | 2.022 / 2.051 / 2.099 | — | — | 30 ms | — | 1.27 (j_spine) | 0 |
| s1-g1 at 100 | 0/10 | top_speed (3566) | 3.558 / 3.566 / 3.584 | — | 1.48 m × 2.38 Hz | 80 ms | — | 1.32 (j_elbow_l) | 0 |
| s1-g4 final (best so far, 2.4 Hz) | 0/10 | top_speed (4486) | 4.466 / 4.486 / 4.498 | 4.81 / 2.40 / 2.40 / 2.40 | 1.86 m × 2.38 Hz | 2 × 60 ms | fl→fr and fl→hl→hr alternating | 1.50 (j_elbow_l) | 0 |
| **s1-g6 at 50** | 0/10 | top_speed (3035) | 2.988 / 3.035 / 3.053 | 3.11 / 3.06 / 3.00 / 3.00 | 0.99 m × 3.0 Hz | 70 ms per stride, 98% of strides | fl→hr→hl→fr (148 of 266) | 1.91 (j_spine, every seed) | 0 |
| **s1-g6 at 100** (= best at 100) | 0/10 | top_speed (4072) | 4.068 / 4.072 / 4.077 | 3.00 / 3.00 / 3.00 / 3.00 | 1.36 m × 3.0 Hz | 80 ms, every stride | fl→hl→hr→fr (261 of 261) | 1.88 (j_spine, every seed) | 0 |
| **s1-g6 at 150** | 0/10 | top_speed (3761) | 3.707 / 3.761 / 3.780 | 3.00 / 3.00 / 3.00 / 3.00 | 1.25 m × 3.0 Hz | 120 ms, every stride | fl→hr→hl→fr (259 of 261) | 1.50–1.55 (j_spine, every seed) | 0 |
| **s1-g6 best at 142** | 0/10 | completes (0), upright (33.3°), top_speed (3545) | 3.466 / 3.545 / 3.586 | 3.00 / 3.00 / 2.98 / 3.00 | 1.18 m × 3.0 Hz | 100 ms, 91% of strides | fl→hr→hl→fr (68), fl→hr→fr→hl (42) | 1.34–1.39 (j_elbow_r, every seed) | 0 |
| **s1-g6 best at 193** | 0/10 | top_speed (3003) | 2.985 / 3.003 / 3.014 | 3.00 / 3.00 / 3.00 / 3.00 | 1.00 m × 3.0 Hz | 120 ms, every stride | fl→hr→hl→fr (201 of 261) | 1.47–1.50 (j_hock_l 7, j_spine 3) | 0 |
| **s1-g6 final (200)** | 0/10 | top_speed (3425) | 3.412 / 3.425 / 3.436 | 3.00 / 3.00 / 3.00 / 3.00 | 1.14 m × 3.0 Hz | 120 ms, every stride | fl→hr→hl→fr (222 of 260) | 1.38–1.43 (j_spine 8, j_scap_r 2) | 0 |

completes, no_fall, upright and straight pass 10/10 at both. At 100 the
engine's own stride reads 1.372 m at 2.94 Hz, with duty factor ≤ 0.29.

What it shows:

- **The 3.0 Hz clock holds.** Every foot strikes 3.00 times a second at
  checkpoint 100. On the 2.4 Hz clip, fr, hl and hr struck 2.40/s and fl
  twice a cycle. The fl double strike is gone at 3 Hz: one fl touchdown per
  cycle, in a single rotary order, fl→hl→hr→fr.
- **It climbs faster than the 2.4 Hz run did.** It is at 4.07 m/s at
  iteration 100, against s1-g1's 3.57. Its cycle is 1.36 m, against s1-g1's
  1.48 m at 100. At 3.0 Hz, 5 m/s needs a 1.67 m cycle. s1-g4 reached 1.86 m
  at 2.4 Hz.
- **The spine binds now, not the elbow.** j_spine is the worst drive over
  rated on every seed at both checkpoints (1.84–1.94×; on the 2.4 Hz clip it
  was j_elbow_l at about 1.5×). Every drive stays at or under peak, but eight
  drives touch peak on every seed: both elbows and wrists, j_hock_l,
  j_shoulder_r, j_knee_r and j_spine.

## After 100: three collapses, and the speed falls

The run has no checkpoint at 200: the trainer's final policy is iteration
200. Seeds 1001–1010 as above (`s1-g6-000150`, `-best142`, `-best193`,
`-final`).

- **It collapsed three times.** At iterations 105, 145 and about 195 σ
  jumped (0.50 → 0.60 at 105), the loss spiked to 100–240, and reward per
  step dropped by 2–4. It recovered each time. The trainer's best is
  iteration 193 (16.89 per step); the final is 13.37.
- **The speed peaked at 100.** It fell to 3.76 m/s at 150 and 3.43 at 200.
  The trainer's best-reward snapshots are slower still: 3.00 m/s at 193,
  and 3.55 at 142, which tips on all 10 seeds (median 4.84 s, 33° tilt).
  The trainer's reward is not a pass: its best is this run's slowest
  policy. Nothing past 100 beats s1-g4's 4.498 m/s, so no warm extension
  was launched (O7).
- **The clock holds at 3.00/s, so cycle length is everything.** Every
  foot strikes 3.00/s at every checkpoint after 50. The cycle shrinks
  1.36 → 1.25 → 1.14 m, against the 1.67 m that 5 m/s needs at 3 Hz. The
  pass-time flight grows 80 → 120 ms; it buys no length.
- **j_spine's RMS over rated falls with the speed:** 1.88 at 100, 1.50–1.55
  at 150, 1.38–1.43 at 200. Every drive stays at or under peak (the model
  clamps at peak: margin 0). 11–14 drives touch peak on all 10 seeds at
  each checkpoint. Every checkpoint has both elbows and wrists, j_scap_l,
  j_knee_r and the tail's j_tail2–4 among them, and j_spine on 8–10
  seeds.
- **The reward pays the clip, not the speed.** At the engine's judged
  episodes, `track_speed` peaks at 100 (3887) and falls to 2901 at 193.
  The clip-tracking terms (`track_pose` 551 → 574) hold or rise. The clip
  is a 2.1 m/s gait (0.7 m × 3.0 Hz), so after 100 the policy trades
  speed for tracking a slower clip.

## The clip's stride, at the generator's reach

`reach_len.py` (in the run's progress folder) asks the engine's own gait
generator (`CadexGait.generate`, on s1-g6's model, 3.0 Hz, rotary gallop)
how long a clip stride fits:

| duty | 700 mm | 750 mm | 800 mm | 850–900 mm |
|---|---|---|---|---|
| 0.25, swing 60 mm | fits | refused: RF misses by 3.6 mm (j_shoulder_r, j_wrist_r at a stop) | refused (8.7 mm) | refused |
| 0.20, swing 60 mm | fits | **fits** | refused: RF misses by 4.2 mm (same stops) | refused |
| swing 80 mm, either duty | refused: LH misses by 11–15 mm (j_hip_l, j_knee_l, j_pawpin_l) | refused | refused | refused |

So the clip can grow only 7%, to 750 mm at duty 0.20 (a 2.25 m/s clip).
The right fore's shoulder and wrist stops bound it. orun10-cat now
declares `gallop_len` and `gallop_duty`. Its defaults (700 mm, 0.25)
reproduce the old clip, and the accepted revision `51fe9d25` sets them to
750 mm and 0.20 at `gallop_hz=3.0`. `launch_g7.py` is written:
**s1-g7**, a cold 100-iteration screen, a checkpoint every 25, to be
compared with s1-g6 at 100. It launches when j1-s1 frees the GPU.

## j1-s1 launched

The GPU went to J1 when s1-g6 ended. j1-s1 runs on orun10-jump at about
27 s an iteration, against s1-g6's 14.4 s on flat ground, so its 100
iterations take about 45 min.

## The J1 screen, ready

`launch_j1s.py` (in the run's progress folder) registers **j1-s1** on
orun10-jump (`b59eb2b1`, the 6 m J1 course, 300 mm ledge). It warm-starts from
orun9's c1-c11b final policy at lr 3e-5, with a 10-iteration critic warm-up,
for 100 iterations and a checkpoint every 25. The step across tasks was
dry-run through the trainer's own `check_policy_fits` against the leap bundle
(`dry_check.py`). It passes, moving `label`, `model` (ground only, ADR-736),
`reward`, `success` and `terrain`. It launches when s1-g6 frees the GPU.
