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

## c1-c10: the ladder's next rung (iteration 19)

c1-c9 extended c1-c8 at weight 8 and its closing speed stayed at 0.99–1.08
m/s. On `points`, c1-c8 @100 kept every drive within rated: the worst drive
per seed was at 0.82–0.94 of rated. So the waypoint pay, not the drives,
holds the cat back, and the next rung of the O8 ladder is weight 12.

**c1-c10**:
- the change: `waypoint_w` goes 8 → 12 and nothing else. Its bundle differs
  from c1-c8's in that one weight and no other field;
- the warm start: from c1-c8 @100 (ADR-753, critic warm-up 10);
- the budget: 100 iterations, 8,192 envs, checkpoints at 50 and 100;
- the revision: accepted `accf672b`, in scope `orun9-c1-c10`. The launcher
  and judge are `~/orun9-progress/c1c10/launch_c10.py` and `judge_c10.sh`.

`navcheck.py` on its bundle, with the target 5 m ahead in nav mode:

| v (mm/s) | 0 | 600 | 1500 | 2000 | 2500 |
|---|---|---|---|---|---|
| c1-c10 (waypoint ×12) | +9.41 | +12.16 | +16.20 | +18.30 | +20.20 |

Going at 2.5 m/s pays 2.15× standing at the target, against 1.9× at
weight 8. The gap from 0.6 to 2.5 m/s is +8.0 a step, against +5.0 at
weight 8. Standing with the target 5 m behind pays −2.59 a step. The stand
rows are unchanged.

The ladder rule stays: if points moves, the next rung is 16; if it does not,
the waypoint pay is not what holds points back.

## c1-c10 judged (iteration 20)

Each checkpoint was judged on all six specs over the 10 frozen seeds
(`judge_c10.sh`; summaries in `~/orun9-progress/c1c10/judge50.out` and
`judge100.out`). Pass counts, then each failing predicate's median:

| spec | c1-c9 @100 | c1-c10 @50 | c1-c10 @100 |
|---|---|---|---|
| run | 0/10; tracks_speed 937 mm/s | 0/10; tracks_speed 962, tail_clear 8/10 | 0/10; tracks_speed 975 |
| stand | 0/10; still 272 mm | 1/10; still 245 | 1/10; still 241 |
| shove | 10/10 | 10/10 | 9/10; one seed tips |
| turn2 | 9/10; tail_clear | 5/10; tail_clear 0.00083 | 3/10; tail_clear 0.00166 |
| reverse | 0/10; reverses 51.8° | 0/10; reverses 51.8°, tail_clear 4/10 | 0/10; reverses 44.6°, tail_clear 2/10 |
| points | 0/10; reaches 0, close 2870 mm | 0/10; reaches 0, close 3393, one seed tips | 0/10; reaches 0.5, close 3164, within_rated 6/10 (0.979) |

Points moved at weight 12, though not to a pass. `closing.py` gives:

- **Targets reached:** 6 over the 10 seeds at @100, five seeds reaching at
  least one. c1-c8 reached 0 and c1-c9 reached 1.
- **First leg:** the closing speed rose to 1.26 m/s, from 1.10 on c1-c8.
- **Overall:** the median closing speed held at 1.05 m/s, with closest
  approach per leg at a median of 1,971 mm, against 2,383 mm on c1-c8.

The drives now bind:

- **Rated torque:** `within_rated` on points fell from 10/10 (c1-c8, worst
  drive 0.82–0.94 of rated) to 6/10 (0.82–1.08).
- **Which drive:** per drive (`o8_rms.py`, `binding-points.txt`), the right
  wrist `j_wrist_r` is the worst drive on 8 of 10 seeds, at a median of
  0.979 of its 9 N·m rating, up from 0.845 on c1-c8.

The extra pay bought closing speed with wrist torque. It also cost turn2's
`tail_clear` (9/10 to 3/10) and one shove seed.

Under the ladder rule, the next rung is 16. A run at 16 should be expected
to cross rated on `j_wrist_r` on points. Judge it on `within_rated` before
reading `reaches`.

## c1-c11: the ladder's last rung (iteration 21)

**c1-c11**:
- the change: `waypoint_w` goes 12 → 16 and nothing else. The retained
  bundle differs from c1-c10's in `reward[3].weight` (12.0 → 16.0) and no
  other field;
- the warm start: from c1-c10 @100 (ADR-753, critic warm-up 10);
- the budget: 100 iterations, 8,192 envs, checkpoints at 50 and 100;
- the revision: accepted `c0a39e63` (a 6 min 18 s rebuild). The script,
  launcher and waiter are in `~/orun9-progress/c1c11/`. b3-cat-ft held the
  machine's training slot, so a waiter ran as the transient user *service*
  `orun9-c1-c11`. It polled the slot every minute, and when b3-cat-ft
  ended at 18:50:25 it registered and launched `c1-c11`. The launcher
  returned, the service's main process exited, and systemd stopped the
  service and killed its control group. That took the detached supervisor's
  trainer with it, at 0.5 s (exit −15, 0 iterations). A waiter must
  launch through `systemd-run --scope` or run with `KillMode=process`.
  The waiter is deleted. The run went out again at once as **`c1-c11b`**
  (a run's name is used once), in scope `orun9-c1-c11b`, on the same
  bundle (`task_sha256` `c592c388…`).

`navcheck.py` on the retained bundle, with the target 5 m ahead in nav mode:

| v (mm/s) | 0 | 600 | 1500 | 2000 | 2500 |
|---|---|---|---|---|---|
| c1-c10 (waypoint ×12) | +9.41 | +12.16 | +16.20 | +18.30 | +20.20 |
| c1-c11 (waypoint ×16) | +11.41 | +15.12 | +20.60 | +23.50 | +26.20 |

Going at 2.5 m/s pays 2.30× standing at the target (2.15× at 12). The gap
from 0.6 to 2.5 m/s is +11.1 a step (+8.0 at 12). Standing with the target
5 m behind pays −4.59 a step. At 1.2× rated on every drive, the over-rated
price is −0.35 a step against +24.0 of waypoint pay. So nothing in the
reward stops the wrist going over rated while it closes.

**Judging order.** Read `within_rated` on points first, then turn2's
`tail_clear`, then `reaches`. If `j_wrist_r` crosses rated on points, it is
O8's binding drive for points, and the waypoint weight is not raised again.

## Where `j_wrist_r`'s points load goes (O8, iteration 22)

Before any further C reward change, I measured how `j_wrist_r` spends its RMS
on points. I used the judged traces of c1-c10 @100 and c1-c8 @100 on the 10
frozen seeds. The scripts are `~/orun9-progress/wrist/` (`wrist_legs.py`,
`wrist_dc.py`, `lr.py`). Each seed's whole-episode maximum is checked equal
to the engine's `effort_rms_rated_ratio_max`.

The spec's three legs are 4.0 s each on every seed: the target changes on
time, not on arrival. So a leg is a fixed window, and the drive's load can
be read per leg.

**By leg and phase** (RMS over rated, medians over the 30 legs):

| drive | c1-c8 whole leg | c1-c8 first 1 s / rest | c1-c10 whole leg | c1-c10 first 1 s / rest |
|---|---|---|---|---|
| `j_wrist_r` | 0.836 | 0.920 / 0.787 | 1.031 | 1.063 / 0.980 |
| `j_wrist_l` | 0.820 | 0.737 / 0.834 | 0.746 | 0.703 / 0.782 |
| `j_shoulder_r` | 0.846 | 0.847 / 0.871 | 0.873 | 0.849 / 0.892 |

- **Speed is not the cause.** Per-leg `j_wrist_r` RMS against the leg's
  mean planar speed: Pearson r = +0.00 at c1-c10 and +0.00 at c1-c8, over
  30 legs each. Legs at 133–216 mm/s carry 0.99–1.07 (seeds 1003, 1005,
  1008). Mean leg speed is 133–1,592 mm/s, with a median of about 0.6 m/s.
- **Turning into a new leg is not the cause either.** The first second of a
  leg runs only 0.08 above the rest at c1-c10 (1.063 against 0.980). The
  drive is over rated while it cruises.
- **It is static hold plus swing.** On points, c1-c10's `j_wrist_r` mean
  effort is −0.521 of rated and its swing (std) is 0.829. At c1-c8 they
  were −0.448 and 0.712. The waypoint rungs 8 → 12 raised both.

**Left against right**, whole episode (median RMS over rated, l/r):

| spec | scap | shoulder | elbow | wrist |
|---|---|---|---|---|
| c1-c10 run | 0.59/0.57 | 0.67/0.64 | 0.60/0.62 | 0.84/0.82 |
| c1-c10 turn2 | 0.59/0.59 | 0.60/0.59 | 0.66/0.75 | 0.66/0.65 |
| c1-c10 reverse | 0.60/0.58 | 0.60/0.60 | 0.63/0.77 | 0.62/0.63 |
| c1-c10 points | 0.69/0.52 | 0.65/0.86 | 0.66/0.50 | **0.73/0.98** |
| c1-c8 points | 0.59/0.48 | 0.66/0.84 | 0.63/0.45 | 0.84/0.84 |

The run spec commands up to 3 m/s, and its wrists are symmetric at
0.84/0.82. Points moves at about 0.6 m/s, and its right fore shoulder and
wrist carry 0.86 and 0.98, while the left elbow and scap take the
difference. At 12, the waypoint pay moved the right wrist from 0.84 to 0.98
and the left wrist from 0.84 to 0.73.

**Finding.** Points binds on a lopsided nav-mode gait, not on the
torque-speed trade. Raising the waypoint weight paid for closing speed with
this asymmetry. An effort price that is uniform across drives does not
target it: at 1.2× rated the price is −0.35 a step against +24.0 of
waypoint pay. Nav mode does read the trot reference: `track_reference`
(weight 1) is gated on in both modes. But it pays at most 4 a step,
against up to 24 for the waypoint at ×16, so nothing holds nav mode to the
symmetric gait. Under the owner's note to prefer more reference over
another penalty, the next C lever is the reference's weight in nav mode. A
left/right symmetry term is the alternative. Another waypoint or effort
weight is not the lever.
