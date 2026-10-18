# orun10 S1: s1-g7 judged at every checkpoint (750 mm clip, duty 0.20, 3.0 Hz)

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 12).

s1-g7 is s1-g6's gallop task with the clip lengthened to the generator's
reach: 750 mm at duty 0.20 and 3.0 Hz, a 2.25 m/s clip (orun10-cat
`51fe9d25`). It trained cold, because the trainer refuses a warm start that
moves the reference. It ran 100 iterations, with a checkpoint every 25. Each
checkpoint was judged on its own bundle's `gallop_spec` (seeds 1001–1010)
through the engine's evaluation child, by `s3/judge_gallop.py`; the summary
comes from `s9/summ7.py`. The trainer's best is iteration 99, the same
file as the final.

| checkpoint | pass | 2 s top, m/s (min/median/max) | completes | upright (median °) | flight share (min) | flight / ms | engine stride, mm @ Hz | worst RMS/rated (drive) | peak ratio max |
|---|---|---|---|---|---|---|---|---|---|
| 25 | 0/10 | 1.104 (one seed measured) | 0 | 32.2 | — | — | — | 1.46–1.91 (j_spine) | 1.000 |
| 50 | 0/10 | 2.584 / 2.625 / 2.700 | 10 | 11.3 | 0.70 | 40 | 554 @ 4.55 | 1.58–1.68 (j_spine) | 1.000 |
| 75 | 0/10 | 3.676 / 3.699 / 3.714 | 10 | 9.4 | 0.90 | 60 | 609 @ 6.25 | 1.55–1.60 (j_elbow_l) | 1.000 |
| **final (99)** | 0/10 | **4.009 / 4.031 / 4.038** | 10 | 9.4 | 0.98 | 60 | 666 @ 6.25 | 1.59–1.65 (j_spine) | 1.000 |

At 25, six seeds tipped and four collapsed. From 50 on, every seed runs the
full horizon and no seed falls. The only predicate that fails is
`top_speed`, which needs 5000 mm/s.

**Against s1-g6 on the same schedule** (0.7 m clip, duty 0.25):

| checkpoint | s1-g6 top (median) | s1-g7 top (median) |
|---|---|---|
| 50 | 3.035 | 2.625 |
| 100 | 4.072 | 4.031 |

## Reading

- **The longer clip did not buy speed.** s1-g7 ends at 4.031 m/s, 0.04 below
  s1-g6 at 100 and 0.47 below the run's best, s1-g4's final at 4.498 m/s.
  Its curve was still climbing at 100: +0.33 m/s from 75 to 99.
- **The clock still follows the clip.** The engine counts two flights per
  clip cycle as two strides: about 666 mm at 6.25 Hz. That is one cycle of
  about 1.33 m at about 3.0 Hz (4.03 m/s ÷ 3.0 Hz = 1.34 m). s1-g6 at 100 ran
  one flight a stride of 1372 mm at 2.94 Hz. So s1-g7 sits at the same
  cycle length as s1-g6, split into two short flights of 60 ms where s1-g6
  had one of 80 ms. 5 m/s at 3.0 Hz still needs about 1.67 m a cycle.
- **What binds is unchanged.** Peak ratio is 1.000 on every judged seed,
  so some drive reaches peak each episode. `j_spine` carries the worst RMS
  over rated, at 1.6×.
- **The reference-clip lever is spent.** Clock (s1-g6, 3.0 Hz), clip weight
  (`reward-balance.md`) and clip length (this run) have all been screened,
  and the best stays at 4.50 m/s.
