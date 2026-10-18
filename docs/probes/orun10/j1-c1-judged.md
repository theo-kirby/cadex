# orun10 J1: j1-c1 judged, and the termination wall at the ledge face

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 16).

j1-c1 is the leap task trained cold on its own straight J goals
(orun10-jump `07e833fb`, `j1-c1-task.md`): 150 iterations, 8192 envs, a
checkpoint every 25. Each checkpoint is judged on the bundle's own `j1_spec`,
seeds 1001–1010, on the 6 m wide J1 course: a 300 mm ledge at x = 3 m,
1.5 m long, then a drop. The judge is the engine's evaluation
(`orun10-jump/evaluations/j1-c1-*`), run by `s8/judge_j1.py` and summarised
by `s8/summ_j1.py`. The return per step comes from `s13/hold_check.py` and
the wall from `s13/wall_check.py` (both in `~/orun10-progress`).

| checkpoint | pass | completes | no_fall | up_across_down (median) | lands_running (6 m; median made good) | highest platform | chest x at the end, median | return per step, median | worst RMS / rated (range; drive) | peak margin |
|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 0/10 | 10/10 | 10/10 | 0/10 (0) | 0/10 (2.74 m) | 0 on all 10 | 2.74 m | 7.89 | 0.72–0.97 (j_spine) | 0 |
| 50 | 0/10 | 10/10 | 0/10 | 0/10 (0) | 0/10 (2.85 m) | 0 on all 10 | 2.85 m | 7.87 | 0.95–1.40 (j_scap_r) | 0 |
| 75 | 0/10 | 6/10 | 0/10 | 0/10 (0) | 0/10 (2.98 m) | 0 on all 10 | 2.98 m | 9.21 | 0.91–1.30 (j_scap_r) | 0 |
| 100 | 0/10 | 8/10 | 0/10 | 0/10 (0) | 0/10 (2.99 m) | 0 on all 10 | 2.99 m | 9.29 | 0.89–1.56 (j_scap_l) | 0 |
| 125 | 0/10 | 10/10 | 0/10 | 0/10 (0) | 0/10 (2.97 m) | 0 on all 10 | 2.97 m | 9.59 | 0.69–0.77 (j_scap_l, j_hock_r) | 0 |
| final (150) | 0/10 | 10/10 | 0/10 | 0/10 (0) | 0/10 (2.98 m) | 0 on all 10 | 2.98 m | 9.59 | 0.70–0.78 (j_scap_l) | 0 |
| best (138) | 0/10 | 9/10 | 0/10 | 0/10 (0) | 0/10 (2.99 m) | 0 on all 10 | 2.99 m | 9.64 | 0.74–1.17 (j_scap_l) | 0 |

No seed leaves the ground at the face, so no take-off speed or leap peak is
measured. Peak ratio is 1.000 on every checkpoint: some drive reaches its
peak in every episode (margin 0). The trainer's reward per step climbs with
the judged hold: 6.6 at iteration 57, 9.39 at 79, and a best of 10.16 at
iteration 138.

## The cat parks against the face

From 75 on, the chest moves up to the ledge face at x = 3.00 m and stops
there:

- In every horizon episode from 75 to the final, the chest frame ends
  8–53 mm short of the face, 20 mm below its start height. Its highest
  point is +2 to +43 mm.
- Every early end is a `collapsed` termination, 77–90 steps in, at chest x
  3000.2–3002.8 mm: 4 at 75, 2 at 100, 1 at the best and none at 125 or
  the final.
- By 125 the policy has learned to stay behind the face: all 10 seeds run
  the full horizon there.

## Why: the `collapsed` termination is a wall at x = 3000

The leap task ends an episode on `scan_4 < scan_stand − 70 = −95.2 mm`.
`scan_4` is the chest frame's height over the ground directly under it. The
cat starts standing at `scan_stand` = −25.2 mm, with the chest frame at
x = 0. Once the chest frame passes over the face, the ground under it is
300 mm higher. So the episode ends unless the chest frame is already
**230 mm above its standing height** as it crosses x = 3000.

`wall_check.py` rebuilds `scan_4` from each judged chest path:

- Every early end falls on the first frame that crosses the wall: steps 89,
  81, 90 and 84 at 75, 90 and 81 at 100, and 77 at the best.
- `scan_4` there is −332 to −344 mm.
- The chest is 7–19 mm *below* its start height at that frame.

The engine's termination step and the rebuilt wall agree on all seven.

`no_fall` fails for the same reason, judged from the base's centre of mass:

- The engine counts a fall when that centre comes down to
  `FALL_HEIGHT_SHARE` = 0.5 of its first height over the ground under it.
- From 75 to the final, the lowest share is 0.21–0.23 on every seed.
- That fits a centre about 380 mm up when standing (300 / (1 − 0.21)),
  with the cat parked so that the centre sits over the ledge with no rise.
- So the spec needs the centre about 110 mm higher than standing as it
  crosses the face. The training wall asks for more: the chest frame
  230 mm higher.

## Holding beats crossing

The hold earns 9.21–9.64 a step (the median judged return at 75, 100,
125, the final and the best). The leap estimate (`j1-c1-task.md`) is 13.94. So the reward
itself does not prefer the hold over a completed leap. Every partial
attempt is a different matter:

- A cat that walks its forepaws up and then brings its chest over the face
  crosses the wall with its chest well under +230 mm.
- That episode ends there, and loses the 4.0-a-step `alive` term and every
  other term for the rest of the 12 s.
- A cat whose chest stays low over the platform for one step would also pay
  `height_over_ground` of about 3.1 a step (|scan_4 + 25.2| / 100). The leap
  estimate left that out.

So the only crossing that is not cut off is a full leap, with the chest
already 230 mm up at the face. Nothing between the hold and that leap pays.
The policy learns the best hold it can reach: parked at the face, as close
as the wall allows.

This is j1-s2's stall at the face in a new shape. In j1-s2 the chest stopped
at 2.40–2.83 m. j1-c1, trained on the straight 2.5 m/s goals, comes up to
the wall itself.

## What follows

- More reward weight cannot fix this, because the reward already pays the
  leap. The termination is what binds.
- The next J1 task should not end an episode for crossing the face with the
  chest low. For example, it could judge collapse by the chest's height
  over the *lowest* ground under its scan rows, or by a world-height floor.
  The flat turning task in `orun10-jump/script.py` (line 2145) already uses
  a floor: `com_z` below 250 mm.
- Before training, check per step on the judged episodes that a climb is
  no longer cut off.
- `j1_spec` (`no_fall`) is the bar and stays as it is: the change is to the
  training termination, not to the spec.
