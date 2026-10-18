# orun10 J1: j1-c3 judged, and the floor that never fires

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 18).

j1-c3 is the leap task with its collapse termination moved to a world
floor, `com_z < 250 mm` (orun10-jump `c65cf762`, `j1-c2-task.md`). It is
warm-started from j1-c1's best policy (iteration 138), at lr 3e-5, with a
critic warm-up of 10, for 100 iterations at 8192 envs, with a checkpoint
every 25. It trained for 3003 s.

Each checkpoint is judged on the bundle's own `j1_spec`, seeds 1001–1010,
on the J1 course: a 300 mm ledge at x = 3 m, 1.5 m long, then a drop. The
judge is the engine's evaluation (`orun10-jump/evaluations/j1-c3-*`), run
by `s8/judge_j1.py` and summarised by `s8/summ_j1.py`. The return comes
from `s13/hold_check.py`, the chest path from `s13/wall_check.py`, and
`com_z` from `s14/com_check.py`. All of these scripts are in
`~/orun10-progress`, and the outputs are in `s15/`.

| checkpoint | pass | completes | no_fall | up_across_down | lands_running (median made good) | chest x at the end, median | chest's highest rise, median | return per step, median | worst RMS / rated (range; drive) | peak margin |
|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 0/10 | 10/10 | 0/10 | 0/10 | 0/10 (2.98 m) | 2.984 m | +21 mm | 9.58 | 0.79–0.85 (j_hock_r) | 0 |
| 50 | 0/10 | 10/10 | 0/10 | 0/10 | 0/10 (2.98 m) | 2.984 m | +17 mm | 9.66 | 0.74–0.80 (j_scap_l) | 0 |
| 75 | 0/10 | 10/10 | 0/10 | 0/10 | 0/10 (2.98 m) | 2.984 m | +19 mm | 9.77 | 0.71–0.78 (j_scap_l) | 0 |
| final (100) | 0/10 | 10/10 | 0/10 | 0/10 | 0/10 (2.99 m) | 2.990 m | +12 mm | 9.72 | 0.69–0.78 (j_scap_l) | 0 |
| best (2) | 0/10 | 10/10 | 0/10 | 0/10 | 0/10 (2.99 m) | 2.988 m | +20 mm | 9.64 | 0.74–0.82 (j_scap_l) | 0 |

- The failing predicates are `no_fall`, `up_across_down` and
  `lands_running`. `no_fall` has a median of 1 fall. The highest platform
  reached is 0 on all 50 episodes.
- No seed leaves the ground, so no take-off speed or leap peak is measured.
- The peak ratio is 1.000 at every checkpoint, so some drive reaches its
  peak in every episode (margin 0).
- Every episode runs the full horizon: 50 of 50.
- The trainer's reward per step goes from 8.38 at iteration 15 to 8.82 at
  99, and σ narrows from 0.383 to 0.347. Its "best" (16.77) falls at
  iteration 2, inside the 10-iteration critic warm-up, and judges like the
  others.

## The cat still parks at the face

- The new termination is never what ends an episode: on all 50 judged
  episodes `com_z < 250` never fires.
- The lowest `com_z` on any episode is 314.6–323.9 mm, at least 65 mm above
  the floor.
- The chest still ends 10–20 mm short of the face, 20 mm below its start
  height, and rises at most +12 to +21 mm (median by checkpoint). A clean
  crossing needs about +230 mm.
- What changed from j1-c1: in 9 of the 50 episodes the chest frame nudges
  past x = 3000 at steps 81–92 and then settles back. Those are 1 at 25,
  2 at 75, 5 at the final and 1 at the best. Under j1-c1's `scan_4`
  termination, each of these would have ended the episode. Now they
  survive, but the cat does not climb.

So the wall is gone and the behaviour stayed. The hold pays 9.6–9.8 a step
and is a local optimum. A warm start from the parked policy at lr 3e-5
moves it only within that optimum, and σ shrinks while it does.

## What follows

- **Lowering the floor is not a lever.** It never comes within 65 mm of
  firing. The charter's note that a fine-tune needs about 3e-5 still
  holds: 3e-4 lost the warm start in j1-c2.
- **The parked policy is the wrong start.** The next J1 screen should
  train the `c65cf762` bundle (floor termination) **cold**, at the default
  lr. Then a first update cannot wipe a warm start, and exploration does
  not begin from a converged hold.
- Before that, check the bundle's first second on the course. Look at
  whether the run-up from x = 0 at the 2.5 m/s goal reaches the face with
  the speed a 300 mm leap needs.
