# orun9 B1: the cold quadruped, set up by the recipe

Verified against source: 2026-10-17. Frozen evidence (orun9, iteration 6).

B1's proof is a cold walk on one quadruped and one biped that are not the
cat, each reaching a walk spec on 10 seeds within 300 iterations, following
`training/RECIPE.md` with no step invented on the spot. This is the
quadruped's setup, before any GPU run.

## The robot

`~/cadex-projects/orun9-quad`, a copy of `quad-qdd` (9.27 kg, twelve
CubeMars AK80-9: 9 N·m rated, 22 N·m peak; hip height 306 mm). Revision
`f08798cc`, project commit `af93615`; fit, mounting and the 12-joint sweep
pass. Bundle `b1_walk`, sha256 `b980d268`.

**Set aside on purpose:** the stand and walk tasks of 2026-10-04/05
(`stand-r*`, `walk-r1`–`r24`) and their policies (`stand_r3_i600`,
`walk_r13_i700`). Those tasks described a trot by hand-written terms
(`trot`, `sync`, `tuck`, `step_<leg>`) on torque drives with a gravity
feed-forward, which is what recipe 1.1 says not to do; the drives are now
position servos, so none of those policies fits the model. The
`policy_on`, `walk_on` and old reward parameters are gone with them.

## The task, step by step

| recipe step | what `b1_walk` does |
|---|---|
| 0.1 drives against the gait | `cadex_proxy.py`, as built, on the bundle's reference (below): holds |
| 0.2 rating declared | every drive carries `rated_torque_nmm` 9000; the spec judges `within_rated` |
| 0.3 stiff stops | no light passive joint: nothing to stiffen |
| 1.1 track a reference | `assembly.gait(feet, gait="trot", speed_mm_s=250)`; pose, foot lift and contact tracked (weights 3, 1.5, 1) |
| 1.2 stride in reach | no override: dynamic similarity gives 220 mm at 1.13 Hz, and the generator built it |
| 1.3 start inside it | `reference_start="random"` |
| 1.4 cadence | one speed, so the fixed clock (the step applies to more than one speed) |
| 1.5 speed as a share | `exp(-|v-V|/(V/2)) + min(v, V)/V`, weight 4 |
| 1.6 positive per step | `alive` 2 |
| 1.7 stand in the same task | not asked: the walk spec has no stand |
| 1.8 effort per drive | each drive's squared excess over rated, weight 2, no speed gate (no sprint) |
| 1.9 height over ground | flat floor, no course: `com_z` |
| 1.10 cheap course | flat floor |
| 2.1 engine's predicates | the robot's own walk spec (walk-r13's, 10 frozen seeds 9101–9110), unchanged but for `W8-within_rated` |
| 3.1 trainer | Brax PPO, 8192 environments, unroll 20 |
| 3.3–3.5 warm start | cold, so none |
| 4.1 budget | 300 iterations, checkpoints at 50, 100, …, each judged |

The drives are position servos about the build stance (zero command
holds it) with the cat's AK80-9 gains (1050 N·mm/deg, 26 N·mm·s/deg),
clamped at peak. The recipe does not name the drive kind; every run it
cites used position drives (the cat, Go1), so this follows them rather than
the quad's old torque drives. If the proof shows the kind matters, that is a
step the recipe gains.

The walk spec at 250 mm/s: survives 10 s, tilt ≤ 25°, mean forward speed
175–325 mm/s, heading ≤ 30°, lateral ±50 mm/s, ≥ 4 steps per foot, step
clearance ≥ 0.02 hip heights, worst drive's RMS ≤ rated; resets tilted up to
5° and dropped 20–30 mm, two shoves at 0.1–0.25 of the capture-point margin.

## Measured before training

**Drives against the gait** (`cadex_proxy.py`, as built, 10 seeds):

| support | completes | worst RMS / rated | at peak | holds |
|---|---|---|---|---|
| full (base carried) | 10/10 | 0.25 (`j_knee_fl`) | 0 | yes |
| attitude (legs carry the weight) | 10/10 | 0.34 (`j_knee_fl`) | 0 | yes |
| inverse (the clip exactly) | 1/1 | 0.58 (`j_knee_rl`) | 0 | yes |

**Standing against moving** (orun8's `points` lesson), from the bundle's
tracking table: a robot standing still at the build stance earns
track_pose 0.885, track_lift 0.878 and track_contact 0.455 of 1 over a
stride, so 6.97 a step from the positive terms against 15.50 for tracking
the reference at 250 mm/s. Moving pays 2.2× standing.

**A note on the gait:** the reference trot's Froude number is 0.021, below
the natural trot range (0.3–3) the generator reports; a 250 mm/s trot is
slow for 306 mm legs. It is the robot's spec speed and the recipe's proven
gait, so it stays; whether a `walk` footfall trains faster at this Froude
number is not tested.

## b1-q1: the cold run, and its judged checkpoints

`b1-q1`: cold, 300 iterations, 8192 environments, unroll 20, seed 0,
checkpoints every 50 (scope `orun9-b1-q1`, registered on the dashboard).
**4.5 s an iteration** on the 5090 with the compile included (1,346 s wall
for 300), against the cat's 14–19 s. Reward per step: −6.3 at iteration 0,
positive from 6, 10.8 at 50, 13.9 at 150, 14.0 at 299 (the hand estimate
for tracking the reference is 15.5).

Judged on the walk spec with the engine's evaluation, 10 frozen seeds
(`~/orun9-progress/b1q/judge_q.py`, `judge2.py` with the model output and
bundle name as parameters):

| it | passed | failing predicates (pass count, median) | speed mm/s (med) | worst drive / rated (med) |
|---|---|---|---|---|
| 50 | **0/10** | W3-speed 0/10 (43), W6-steps 0/10 (0), W7-clearance 2/10 | 43 | 0.61 |
| 100 | **0/10** | W1-survives 2/10 (8 tipped), W2-tilt 2/10 (48°), W3-speed 6/10, W5-lateral 0/10 (−131), W6-steps 6/10 | 177 | 0.66 |
| 150 | **10/10** | — | 260 | 0.47 |
| 200 | **10/10** | — | 255 | 0.48 |
| 250 | **10/10** | — | 257 | 0.47 |
| 300 | **10/10** | — | 238 | 0.54 |

**The quadruped half of B1's proof passes:** a cold walk on a robot that is
not the cat reaches its walk spec on 10/10 seeds by iteration 150 of the
300 allowed, and holds it to 300, following the recipe with no step
invented. At 150: heading ≤ 1.5°, lateral −20 mm/s, 10 steps a foot,
clearance 0.029 hip heights, worst drive 0.47 of rated. By 250 the lateral
drift is gone (+2 mm/s) and clearance has risen to 0.071; at 300 the speed
slips to 238 mm/s and lateral to +29 mm/s, still inside the spec.

So the cold quadruped needs at most 150 iterations to the walk spec; B3's
bar ("half the iterations a cold run needs") is **≤ 75** on this robot.
The biped half (`orun9-biped`) is still to run.
