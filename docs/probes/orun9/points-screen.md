# orun9 C1/C2: what binds stand and points, and the waypoint-weight screen (c1-c8)

Verified against source: 2026-10-17. Frozen run evidence: read it, never
cite it as current.

Before another cat screen, the critic asked for one aimed at stand drift and
points, with standing against moving measured per step on the bundle first.
The scripts and their output are in `~/orun9-progress/c1c8/` (outside the
repo): `standsplit.py`, `navcheck.py`, and the launch and judge scripts.

## Stand: the opening brake takes most of the budget

The stand spec commands zero (cmd −400, nav −1) for 10 s and allows
200 mm of drift. Its seeds are seeded episodes, so under ADR-709 they
start **mid-stride, at the 1 m/s trot reference's speed**: "drift" counts a
stop from 1 m/s as well as the stand after it. With the base holding the
solved keyframe and the policy off (stock MuJoCo, actuators at the keyframe
angles), the chest moves 8 mm in 2.6 s, so the model does not slide.

`standsplit.py` splits every judged stand evaluation into the chest's
displacement over 0–0.6 s (the brake) and from 1 s to 10 s (the creep),
medians over the 10 seeds:

| checkpoint | still (median) | 0–0.6 s | 1–10 s |
|---|---|---|---|
| c1-t7 @50 / @100 / @150 | 185 / 178 / 172 mm | 153 / 137 / 159 | 69 / 97 / 72 |
| c1-t6 @150 | 173 | 153 | 110 |
| c1-t8 @150 | 291 | 190 | 153 |
| c1-c6 @100 | 389 | 204 | 212 |
| c1-c7 @50 / @100 | 453 / 449 | 244 / 245 | 257 / 223 |

On every one of 26 judged stand evaluations the brake alone is 137–245 mm
of the 200 mm budget. Starting at 1 m/s, stopping in 0.6 s over about
200 mm is an average deceleration near 2.5 m/s². A stop inside about
120 mm, which would leave 80 mm for the stand, needs about 4 m/s².

The reward already prices the brake hard. Per step, from the speed,
stand, effort and yaw terms of c1-c7's bundle (`navcheck.py`):

| forward speed in stand mode | 0 | 100 | 300 | 600 | 1000 mm/s |
|---|---|---|---|---|---|
| reward per step | +12.81 | +8.91 | +4.92 | +1.07 | −3.00 |

A stronger stand weight is therefore not the obvious lever. A half-second
brake already costs about 250 of an episode's return. What limits the
stand is the stop from the spec's reference start, together with the creep
after it, which has grown since c1-t7 (72 mm then, 223–257 mm on c1-c7). No
change to the stand is screened here.

## Points: the cat is slow, not unable

`points` sets three world targets 4 s apart. Over the 10 seeds the legs are
3.0–8.1 m, so they need 0.76–2.02 m/s on average, a turn included. The cat
has run 2.2–2.4 m/s on `run`. On c1-c7 @50 it closed on its targets at
about 0.6 m/s: on seed 1002, with the first target 23° off its nose and
5.2 m away, it was still 2.9 m short when the target moved on.

Per step in nav mode, with the target 5 m dead ahead, cmd 1500 as in the
spec, and the drives at k × rated (the k values are assumptions, stepped
with speed):

| v (mm/s) | 0 | 600 | 1500 | 2000 | 2500 |
|---|---|---|---|---|---|
| c1-c7 (waypoint ×4) | +5.41 | +6.24 | +7.40 | +7.90 | +8.20 |
| c1-c8 (waypoint ×8) | +7.41 | +9.20 | +11.80 | +13.10 | +14.20 |

Going at 2.5 m/s pays 1.5× standing at the target on c1-c7. That is
orun8's `points` lesson half-learned: moving now pays more than standing,
but not by much. Weight 8 makes it 1.9×, with the gap from 0.6 to 2.5 m/s
at +5.0 a step instead of +2.0. Standing with the target 5 m behind pays
+1.41 on c1-c7 and −0.59 on c1-c8.

## The screen

**c1-c8**:
- the change: the `waypoint` term's weight goes 4 → 8 (script parameter
  `waypoint_w`), and nothing else;
- the warm start: from c1-c7 @50, the checkpoint with turn2 at 10/10
  (ADR-753, critic warm-up 10);
- the budget: 100 iterations, 8,192 envs, checkpoints at 50 and 100.

It is the first rung of a weight ladder (O8). If points moves, the next rung
is 12; if it does not, the waypoint pay is not what limits points either.

c1-c8 trains from the accepted revision `8342d6d1`, in scope
`orun9-c1-c8`. Its bundle differs from c1-c7's only in that one weight,
checked field by field, and `navcheck.py` on it gives the c1-c8 row above.
Iteration 0 logged +4.28 reward per step.
