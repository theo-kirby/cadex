# orun10 S1: s1-g6, the 3.0 Hz clip, judged at 50 and 100

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 9).

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

The trainer's iteration 105 shows σ 0.50 → 0.60 and reward per step
15.5 → 13.3. Checkpoints 150 and 200 are judged when they land.

## The J1 screen, ready

`launch_j1s.py` (in the run's progress folder) registers **j1-s1** on
orun10-jump (`b59eb2b1`, the 6 m J1 course, 300 mm ledge). It warm-starts from
orun9's c1-c11b final policy at lr 3e-5, with a 10-iteration critic warm-up,
for 100 iterations and a checkpoint every 25. The step across tasks was
dry-run through the trainer's own `check_policy_fits` against the leap bundle
(`dry_check.py`). It passes, moving `label`, `model` (ground only, ADR-736),
`reward`, `success` and `terrain`. It launches when s1-g6 frees the GPU.
