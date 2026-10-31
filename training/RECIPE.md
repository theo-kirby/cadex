# The recipe: from a spec to a judged go-to-point policy

Verified against source: 2026-10-29. Provenance: `[Cadex-new]`. Rewritten
in orun21 (K1, ADR-864) as the route a new robot follows. It was orun8's
cold-start draft (`wild-forest-4815`). Part I is orun21's: the route
(§R), the task (§G), terrain (§T), the defaults (§D) and the budgets (§B).
Part II (§0–§6) is the earlier, gait-tracking evidence from orun8 to l3r1,
kept under its old numbers because records cite them.

Each step names the ADR, run or probe that is its evidence. Records are
`[rec: slug]` (read them with `governor snapshot`), and the probes are
`docs/probes/orun21/*.md`. A step with no run behind it says so. *Limits*,
at the end, lists what this recipe is known to miss. The biped was taken
from its CAD through §R and §G by this file alone (ADR-865); the places
it was wrong or silent are fixed in §G.1, §G.2, §G.4 and §G.7, and the biped
did not pass G3's bar (*Limits*).

**The route in one screen.**

| step | command | evidence |
|---|---|---|
| spec | write `cadex-concept-v1` JSON | ADR-843, ADR-844 |
| concept | `cadex_concept.py SPEC --out concept.xml` | ADR-842 |
| task | `cadex_joystick.py TASK.json --out DIR` | ADR-862 |
| train | `cadex_train.py ... --goto walk:...,run:... --goto-share 0.2` | ADR-840, G2-GOTO.md |
| judge go-to-point | `docs/probes/orun21/g2_judge.py POLICY TASK OUT` (`--other-model` on the export) | ADR-839, ADR-858, ADR-865 |
| or race gates | `cadex_train.py ... --gates`; `cadex_goto.py race POLICY --task EXPORT-TASK --other-model` | ADR-955–957 |
| freeze, CAD | the project's script, with `assembly.task` | ADR-846, ADR-847 |
| export | `cadex export --out DIR` (copies the accepted attempt) | ADR-848 |
| compare | `cadex_cad_vs_concept.py concept.xml EXPORT.xml` | ADR-843 |
| cut | `cadex_training_model.py cut --project DIR --out cut.xml` | ADR-841 |
| relay | `cadex_relay.py EXPORT-TASK.json cut.xml --out DIR` | ADR-845, ADR-863 |
| confirm | the same training on the cut, `--cad-model EXPORT.xml` | ADR-846 |
| judge | `cadex evaluate --weights ... --task ... --out ...` on the export | ADR-846 |
| terrain | a leveled `around` pool, `--terrain-curriculum`, then a scan | ADR-856–861 |

The trainer, `cadex_concept.py`, `cadex_relay.py`, `cadex_joystick.py`,
`cadex_goto.py` and `g2_judge.py` run from `~/cadex-train-venv`
(`training/SETUP.md`). `cadex export`, `cadex evaluate` and the cut's
`--project` read the project through the engine.

# Part I: the route (orun21)

## R. The route: spec to judged policy (ADR-846)

Two models are written: the concept, from a spec, and the CAD, from its
script. The training model is cut from the CAD's export and never written
by hand, and the export is the judge. Once the CAD exists, its export's task
bundle is the only task, and the concept and the cut train on it re-laid by
name. Every step is one command, generic over robots (ADR-841–846). Each
line names the run that showed it.

1. **Spec.** Write a `cadex-concept-v1` spec (`examples/concept/`). Name the
   leg roots and driven joints as the CAD will name them, so the later
   comparison matches row by row (ADR-843). Flat feet are capsule `soles`
   (ADR-844). Give the trunk the mass the CAD will have, not the mass of
   the motors alone: leon V's E2 concept was 7.1% light and its policy
   failed the export 0/10 on drive ratings (ADR-847). The same concept with
   its chest raised to the CAD's 33.31 kg passed it 10/10 (ITERATION.md §9,
   `wise-moon-5991`; that run controlled at 40 Hz through the pre-ADR-863
   relay).
2. **Concept training.** `cadex_concept.py SPEC --out concept.xml` takes
   0.1 s. Sweep with `--set`, then train each variant briefly. A concept
   trains faster than any CAD-derived model: leon V's concept runs 525 k env
   steps/s, its cut 303 k and its export 9.4 k (ADR-842). Train it on §G's
   task. Before any CAD exists, Cadex has no command that writes a concept
   its first task bundle (see *Limits*).
3. **Frozen numbers.** Freeze the spec that passes. Its geometry and masses
   are what the CAD is built to.
4. **CAD.** Build the robot in its project and declare its task with
   `assembly.task` and a success spec, so the export carries the task bundle
   that every later tier trains on and is judged by. A gait reference the
   legs cannot reach refuses at accept, naming the leg and the stop. On
   leon V a 680 mm trot stride and then the 731 mm dynamic-similarity
   default were both out of the re-legged fore leg's reach, and 520 mm was
   accepted (ADR-847). `cadex export --out DIR` then copies the accepted
   attempt in seconds (leon V 1.1–1.2 s, against 1,844 s when it rebuilt,
   ADR-848), so the build is paid once, at accept. On leon V that accept is
   the CAD route's cost: 1,421 s for an edit that reaches the frames, 70%
   of a 34-minute CAD iteration (ITERATION.md §9).
5. **Compare.** `cadex_cad_vs_concept.py concept.xml EXPORT.xml`. Geometry
   should agree (leon V: hip heights, reach and foot x within 0.7 mm). The
   flagged rows say what the CAD moved, usually mass (leon V +7.1% against
   E2; the biped 4 of 45 rows, ADR-843/844). If the mass moved, carry it
   back into the spec (step 1) before believing a concept policy.
6. **Cut, passing fidelity.** `cadex_training_model.py cut --project DIR
   --out cut.xml` takes under 1 s. It keeps floor-only contacts and fused
   static bodies, except those holding the feet (ADR-951), and picks the fastest solver setting that keeps the
   root's path within 5 mm of the export and stands (ADR-841). No one
   setting suits every robot: the fastest passes on leon V and blows up on
   the biped's stiff servos (`sandy-acorn-7218`), which is why the cut
   searches. A chain whose drives only hold it (leon VI's tail) can be
   welded at its build pose with `--weld` (ADR-959) when the bench needs it;
   the export's judge still plays the chain. If no setting passes, the cut refuses. Then train on the
   export instead, and say so.
7. **Relay.** `cadex_relay.py EXPORT-TASK.json cut.xml --out DIR` re-lays
   the export's task by name, so the policy reads the export's channels
   (ADR-845). Relay onto the concept too, to screen the frozen spec on the
   CAD's own task. **The control interval stays the task's, and the
   substeps follow the target model's own timestep** (ADR-863): 8 substeps
   on leon V's 2.5 ms concept for 20 ms control. An interval that is not a
   whole number of the model's steps refuses. Before ADR-863 every relayed
   concept controlled at 25 ms (40 Hz) while its task said 20 ms.
8. **Confirming retrain** on the cut: `cadex_train.py DIR/outputs/TASK.json
   --cad-model EXPORT.xml`, at the concept's budget. The biped took 100
   iterations in 106 s, against ~249 s on the export (ADR-845). leon V's
   trot took 300 iterations in 316 s (ADR-847). Judge the checkpoints, not
   only the last. leon V's cut run passed at 200 and at its best (218) and
   failed at 299, where the run had begun to come apart (episode length
   5,285 → 92 steps at 267).
9. **Judged on the export.** `cadex evaluate --project DIR --task TASK
   --weights RUN/policy.cxpolicy --out JUDGED` runs the engine's success
   spec on its frozen seeds, as for a declared policy (ADR-846). The biped:
   cut-trained 10/10 (as the export-trained runs), concept-trained 7/10,
   every failure step clearance 0.019 against 0.020 hip heights. leon V's
   trot: cut-trained 10/10, concept-trained 0/10, every seed over its
   drives' rating (1.21–1.34×), the concept being 7.1% lighter than the CAD
   (ADR-847). A pass is then declared with `cadex train --put` and
   `assembly.policy`, as any policy is.

Skip the concept only when the CAD already exists and no geometry is in
question. Never skip the cut for a large robot: leon V's export trains at
1/32 of its cut's rate. On a small one the cut still halves the run.

**What an iteration costs** (leon V, ITERATION.md §9, 49.2 M-step training):
a concept iteration, spec change to judged policy, is 327 s without the
film; a CAD iteration is 2,031 s, of which the accept is 1,421 s. Screen
design on the concept; go to the CAD when the numbers are frozen.

## G. The task: go-to-point (ADR-839, ADR-840, ADR-862)

One policy, many skills. A point lights on the floor and the robot walks
or runs to it, turning when the point is behind or to the side, holds there,
then goes on to the next. A new point appears on arrival or when the hold
ends, not on a clock. This replaces separate stand, sprint and turn tasks.

1. **A velocity policy under a scripted layer** (ADR-839, from
   RESEARCH.md §1.2 and §4). The policy is Playground's omnidirectional
   joystick: forward and lateral speed and yaw rate. `cadex_goto`'s layer
   turns each point into those commands from the base's pose. A point
   behind is a turn on the spot, and a hold is a zero command with
   corrections. A turn on the spot starts past 60° off and goes on until the
   point is within 30°, so a robot whose step-off yaws it back is not
   caught at one edge (ADR-865: the biped chattered at a single 60° edge
   and turned for 200 s). The other route, end-to-end position targets (Rudin et al.
   2022), is the charter's E1 and has no run.
2. **Write the task onto the robot's model.** `cadex_joystick.py TASK.json
   --out DIR` writes G2's task onto any `cadex-training-task-v1` bundle: an
   export's, or a relay's onto a concept or a cut (ADR-862). It reads the
   root, drives, joint ranges, keyframe, feet and floor from the model, and
   the substeps from its timestep. Its actions are the source bundle's: a
   drive the source leaves out (leon VI's tail) is held at its keyframe
   command, which must be 0 (ADR-958). It writes Playground's terms (§D) with
   the Go1's speeds (±1.5, ±0.8 m/s, ±1.2 rad/s; `--speeds` changes them).
   On the Go1 it writes orun18's bundle back again, up to channel names.
   The task names nothing robot-specific beyond the model. Slower
   `--speeds` scale the tracking widths and the reset kick with them, and
   the trunk payload is capped at ±20% of the trunk's mass (ADR-865). Before
   that, the biped's 0.2 m/s commands paid 0.85 of the tracking reward for
   standing, and its policy stood; a 0.5 m/s reset kick tipped it over
   (episodes 334 of 1000 steps); and its 0.26 kg pelvis drew a negative
   mass. A CAD task with no goal (the biped's fixed-speed walk) is a valid
   source.
3. **Train with the layer on a fifth of the episodes.** Add `--goto
   walk:0.4-0.7,run:1.0-1.5 --goto-share 0.2` to the run (ADR-840). Each
   such episode plays one of 1,024 seeded `train` sequences, turned to a
   uniform heading about the start. On the Go1 at share 0.2 (`g2-goto-s20`,
   206.4 M env steps, 332.9 s): **10/10 held-out sequences** (8 points,
   3–5 behind), every point reached within 0.255 m, every hold within
   0.100 m, no fall, straight legs at 0.873–0.987 of the command
   (G2-GOTO.md). Share 0.5 passes 3/10 on slow walk legs (0.767). Share 0
   passes the Go1 10/10 with the faster walk (0.924) but failed leon V's
   concept 0/10 against share 0.2's 4/10 (ADR-863). Keep 0.2.
4. **Judge on held-out sequences, every checkpoint.**
   `docs/probes/orun21/g2_judge.py POLICY TASK OUT` plays `heldout:0`–`9`
   through `cadex_goto.py play` and writes `OUT/summary.json` with the bar
   per seed: every point reached within 0.3 m, every hold within 0.15 m, no
   fall (base centre of mass under half its start height, or tipped past
   60°; ADR-862), and straight-leg speed within 15% of the command. The
   sequence generator is one seeded source for training and judging, and
   the `heldout` split never trains. Reach and hold are close to guaranteed
   by the layer's arrival rule, so the speed column and `leg_s` (time per
   point) are what tell policies apart. leon V's best pass (4/10) was
   iteration 900, not its best-reward 1113 (2/10) or its last (2/10)
   (G3-GOTO.md). **On the export:** a policy trained on the cut is judged
   on `cadex_joystick.py`'s task written onto the export's bundle, with
   `--other-model`: the channels match by name, and `goto.json` records
   both models' digests (ADR-865). `cadex evaluate` (§R step 9) judges the
   engine's own success spec, which for a CAD task is its gait, not
   go-to-point. The play now runs to a bound of each leg and a half turn
   at half their speed: the old bound (each leg at its full speed, plus
   10 s) cut every biped sequence off unfinished (ADR-865).
5. **The judge has a picture.** The player writes a `view/` the dashboard
   plays with the points drawn: the current point lit, the next ones dim,
   each coloured by its band, and a hold as a filling ring
   (G1-TARGETS.md, ADR-839).
6. **Change only the speed bands for a new robot.** G3 put leon V's concept
   at 33.3 kg through §G with the Go1's bands and command unchanged
   (206.4 M steps, 602 s): all 80 held-out points reached, every hold kept,
   0 falls, 4/10 passes at iteration 900. Every miss was a walk leg at
   0.80–0.85 of a 0.5 m/s command (*Limits*).
7. **A slower robot scales the Go1's speeds by one ratio.** Take the
   robot's top speed from its CAD task (the success spec's speed bound) and
   scale the Go1's `--speeds 1.5,0.8,1.2` and bands
   `walk:0.4-0.7,run:1.0-1.5` by the ratio to 1.5 m/s. The orun9 biped's
   `W3-speed` tops at 240 mm/s, a ratio of 0.16: `--speeds
   0.24,0.128,0.192` and `--goto walk:0.064-0.112,run:0.16-0.24`, given to
   both the trainer and `g2_judge.py --bands`. The biped
   (G3-GOTO.md, `orun21-lab/g3/biped`) went export → cut → relay →
   `cadex_joystick.py` → G2's command on the cut (206.4 M steps, 478.6 s).
   At iteration 1200 it reached all 80 held-out points, held every hold
   within 0.100 m and did not fall, on the cut and on the export, but passed
   0/10 on the cut and 2/10 on the export: each seed's slowest leg was at
   0.80–0.86 of its command, leon V's signature. A 300-iteration screen
   (49.2 M) walked, and did not turn in place, so a robot with no hip yaw
   (the biped's legs are roll, pitch and knee) needs the full budget to
   learn a stepping turn.

8. **Or race gates, end to end (ADR-955).** `--gates` in place of
   `--goto`: every episode is a gate course; the policy sees the next two
   gates in its heading frame and no commanded speed, and is paid for speed
   made good toward the lit gate under a ceiling that rises as the
   population reaches it, for each gate, and a little less for time. The
   joystick task's tracking terms are dropped; its regularisers stay. Judge
   with `cadex_goto.py race` on the export (`--rated-nm` for the drives' RMS
   ratio). `--gait-reference gallop --reference-fade N` adds a clock-free
   guide that fades (ADR-957). **No run behind it yet:** a 30-iteration
   smoke on leon VI's cut (2.46 M steps) reached 0.19 m/s made good and no
   gate on the export (ADR-955).

## T. Terrain (ADR-852–861)

One engine source: the course is placed by `CadexDynamics` and the trainer
builds none (ADR-852; `training/test_terrain_pool.py` holds the parity).
A pool is declared on the model's terrain (`api.mjcf(terrain=...)`, or a
bundle's `terrain.pool`). Its kinds are steps, slopes, bumps, platforms,
rock and tile patches, walls and mazes, and heightfields from a grid or a
mesh (ADR-853–855, `docs/MUJOCO.md` *The floor and terrain*).

1. **Start from G2's command.** The chain in step 6 began cold on a
   leveled pool with G2's command and the curriculum added, and every later
   step was a warm start. Judge flat ground at every step (step 8).
2. **A leveled pool laid round the start.** Set `random.levels` (8 here) so
   level l draws each height from its band of the range, as Isaac Lab
   scales a tile by its row (ADR-856). Set `random.around: true` so the
   points, which lie on every side, meet relief: on the +x-only pool 80% of
   first points lay off the course, and on the round pool none did, with
   66% of first legs crossing relief (ADR-857).
3. **The curriculum on points reached.** `--terrain-curriculum` (with
   `--goto`) starts every environment at level 0. An episode on the layer
   that reaches `--terrain-promote` points (default 1) without falling goes
   up, and one that falls or reaches none goes down. This is legged_gym's
   game rule with points in place of distance (ADR-856). Levels are not
   kept in a checkpoint, so every warm start climbs again from level 0.
   The batch's level is not a skill reading. Judge on held-out courses.
4. **Collide the course with the feet only** (ADR-739). It costs: the
   Go1's 29-slot pool trained 4.2× slower than the plane (1,361 s against
   325 s for 206.4 M steps), and the 41-slot round pool about 1.5× more per
   iteration again (ADR-856, ADR-857). On a heightfield, only spheres and
   capsules may touch it; a box or mesh on one is refused (ADR-854).
5. **Give the actor a height scan by warm start.** A blind actor stops at
   step faces it cannot see (T2-JUDGE.md). Add a `height_scan` with
   `role: policy` and warm start across `--init-from-task-change`: the new
   inputs start at zero weight, so the actor starts as its source (ADR-859).
   Held-out level 2 went 1/10 → 6/10, and flat stayed 10/10. Iteration 100
   was no better than blind. The gain showed between 100 and 200.
6. **The chain that passed** (Go1, T2-SCAN.md, T2-MAZE.md):
   `go1-levels/run1` (cold, 206.4 M, share 0.5, curriculum, 1,361 s) →
   `go1-around/run1` (warm, round pool, 65.5 M, 667 s; iteration 200) →
   `go1-scan/run1` (warm, + scan, 49.2 M, 512 s) → `run2` (warm, 73.7 M,
   741 s; iteration 300) → `run3` (warm, + the `feet` block, 41.0 M,
   430 s, ADR-861). `run3` holds G2's bar unwidened on flat ground (10/10),
   on held-out level 0 (10/10) and through maze levels 0–2 (10/10 each);
   level 2 passes 9/10 and level 4 1/10. The terrain runs used share 0.5,
   because the curriculum moves only episodes on the layer; share 0.2 on
   terrain has not been tried.
7. **Steer through walls with the route, not the policy.**
   `cadex_goto.maze_route` places points through a maze's cell centres, and
   `g2_judge.py --level L --maze` plays them and fails any step with a body
   in a wall (ADR-860). A policy that never trained on walls passed 29 of
   30 maze seeds. Holding the robot at each turn's cell centre took wall
   hits from 4/10 seeds to 0/10.
8. **Judge by level.** `g2_judge.py POLICY TASK OUT --level L` plays
   held-out courses from the engine's evaluation stream, which the trainer
   never draws, and `--flat` plays the empty course (ADR-858). Report flat
   ground with every terrain row: training on terrain can cost flat speed
   (`go1-scan/run2`'s final checkpoint fell from 10/10 to 6/10 on flat).

9. **A gate race over relief** (ADR-962). `--race-terrain u1` with `--gates`
   lays K train-split fields of race terrain round the start (the trainer's
   own heightfields, paws only), each episode on a level uniform in 0..top,
   the top raised on few falls. Judge it with `cadex_goto.py race --terrain`
   on held-out courses and on flat ground. It costs about 0.5 s per field per
   8192-env iteration (4.1× flat at K = 4 on leon VI's cut).
   `--relief-fields graded` (ADR-963) lays every field at the race's full
   amplitude, its hills' grade climbing the race's range field by field.
   `--relief-fields graded-rough` (ADR-964) keeps a rough-only field below
   the graded hills, so rough ground without hills is never missing.
   `race --terrain b1` (ADR-965) judges boxes and steps to 60 mm across
   every leg on that relief, `boxes` the same boxes on the plane.
   `--race-terrain b1` (ADR-966) trains over them: each field scatters
   0.2 boxes and steps per m², about one every 3 m of a run.
   `--race-scan default` (ADR-967) lets the actor see them: the base's
   height over the ground on 18 points up to 0.8 m ahead, warmed in at zero
   weight from a blind racer.
   `--gate-backward 1` (ADR-968) makes the racer lead with its fore end:
   a body that runs hind end first carries its scan, its fore shoulders
   and its stance load the wrong way round.

## D. Defaults (from R1, RESEARCH.md §3 and §5)

What `cadex_joystick.py` writes and §G's command sets. Each is
Playground's Go1 joystick unless the row says otherwise. On it the Go1
tracks 0.94–0.97 of Playground's own speeds with no falls (GO1-BASELINE.md).

| | default | RESEARCH.md row |
|---|---|---|
| actor | root body-frame velocity, gyro, gravity; each driven joint's position and velocity; the last action; the command. No history | C-6, C-8, C-9 |
| action | home + 0.5·a rad, clipped to the joint's range, on position drives | C-10 |
| control | 50 Hz; substeps from the model's timestep | ADR-862, ADR-863 |
| reward | Playground's terms and weights, times the control interval, `--reward-floor 0` | C-11 |
| termination | upside down only | C-12 |
| reset | yaw uniform; go-to-point sequences turned to the start's heading | C-13 |
| randomisation | floor friction 0.4–1.0; joint frictionloss and armature; every body's mass ±10%; ±1 kg on the root, at most ±20% of it (ADR-865); drawn once per environment | C-14, C-15 |
| commands | ±1.5, ±0.8 m/s, ±1.2 rad/s, held 250 steps; go-to-point layer on 0.2 of episodes | C-1–C-4, ADR-840 |
| PPO | 8192 envs, unroll 20, 4 epochs × 32 minibatches, 512-256-128, γ 0.97, lr 3e-4, entropy 0.01, clip 0.3, grad norm 1.0 | C-17, C-18 |
| budget | 1,260 iterations = 206.4 M env steps (Playground's 200 M) | C-19 |
| terrain | feet-only contact; leveled round pool; curriculum on points; height scan added by warm start | C-21–C-25 |

`cadex_train.py`'s own `--envs` default is still 256, a smoke test. State
every §D flag on the command line, as `docs/probes/orun21/G2-GOTO.md`'s
launch does.

## B. Budgets

State budgets in env steps and wall time, not iterations.

1. **A full go-to-point run is Playground's: 206.4 M env steps.** On the
   5090 that is 333 s on the Go1, against Playground's 385 s for 200 M on
   the same card. It is 602 s on leon V's concept and 664 s for the same
   run at share 0, and 479 s on the biped's cut (G3-GOTO.md). A
   300-iteration screen (49.2 M, 226 s on leon V, 186 s on the biped) is
   too short to judge go-to-point: leon V's reached 2 of 10 sequences and
   stood still at 1.5 m/s, and the biped's walked but could not turn in
   place.
2. **A route screen is 49.2 M** (8192 × 300 × 20): enough to compare a
   concept against its cut on a declared gait (§R step 8, ITERATION.md §9).
3. **Terrain steps are warm extensions of 40–75 M** (§T.6), each judged on
   held-out levels before the next.
4. **Extend by warm start only while the judged numbers climb**, and change
   the approach, not the steps, when they do not: `go1-scan/run2`'s 73.7 M
   more at the high levels turned stops into falls and left level 4 at
   1/10 (T2-SCAN.md).
5. **Keep the first checkpoint that passes, and judge every one** (§4.4,
   §R.8, §G.4).

# Part II: reference gaits, speed and many speeds (orun8 to l3r1)

These sections come from runs that tracked a reference gait or a speed
command on the engine's own tasks, before go-to-point. They hold for a task
that is judged on a gait (a stride, a footfall order, a stand spec) rather
than on points, and they are cited by number from earlier records.

## 0. Before training: can the machine do it?

1. **Measure the drives against the gait before writing a reward.** The
   panel cat's gallop failed on torque, not on the reward: about 3× less
   torque per unit of mass times leg length than a Mini Cheetah class robot,
   with heavy distal legs [rec: calm-lake-6662]. The drive proxy screens
   drives and masses against a reference clip by inverse dynamics, with no
   rebuild (ADR-710, ADR-711).
2. **Declare every drive's continuous rating** (`rated_torque_nmm`,
   ADR-707), so a spec can judge RMS over rated and a reward can price it.
   Without it a policy runs its drives at 1.7–1.9× rated and passes
   [rec: cold-meadow-3037] [rec: bright-spring-0370].
3. **Make every stop as stiff as its hardware.** A light passive joint's
   default MuJoCo limit is a soft spring: the cat's 144 g paw pin folded
   25–72° past its stop under stance load (ADR-724) [rec: humble-harvest-1485].
   A 0.004 s stop on that pin was the suspect when r1-t5 went NaN at
   iteration 2 [rec: sunny-coast-7833]; under ADR-735's guard the same model
   trains cold and finite (c1-t1, 300 iterations) [rec: wild-vale-0638].

## 1. The task

1. **Track a reference gait; do not describe one.** A reward that describes
   a gait buys its cheapest exploit: the panel cat went lunge, skate, dive,
   wheelbarrow, nose-dive [rec: calm-lake-6662]; a hexapod paid only for
   forward speed flipped forward [rec: polished-path-3774]. Generate the
   stride on the robot's own legs with `assembly.gait` (ADR-702, ADR-703)
   and pay pose, foot height and contact against it on the gait clock
   (ADR-706). On the Brax learner the cat then tracks the reference trot
   10/10 with no falls, joint RMS 2.6°, footfall phase error 0.017
   [rec: bright-spring-0370].
2. **Keep the stride inside the legs' reach.** The generator refuses an
   unreachable stride with the leg, phase and joints at a stop; on the cat
   the joint ranges cap a stride near 0.6 m where dynamic similarity asks
   0.69–0.88 m [rec: early-lake-4580] [rec: fast-sky-9811]. Pass
   `stride_length_mm` inside the reach rather than widening the clip.
3. **Start every episode inside the reference** (`reference_start="random"`,
   ADR-709). From a standstill the tracking reward asks for full speed at
   step 0 and the policy lunges and falls [rec: civic-otter-7503]. On the old
   learner a random start alone still fell [rec: frosty-canyon-1593]; with
   the Brax learner it is part of the 10/10 above [rec: bright-spring-0370].
4. **Let the clock follow the command** (`reference_cadence="speed"`,
   ADR-752) when the task asks more than one speed. On a fixed 1.72 Hz clock
   the cat ran 1.0–1.3 m/s whatever it was told [rec: wise-spark-1215]; on
   the cadenced clock it ran 2.4 m/s at a 3 m/s command with no reward
   change [rec: keen-harbor-0874]. Where the stride's length and footfall
   should change with speed too, a speed schedule (`reference=[slow, ...,
   fast]`, ADR-773) blends strides at the command instead, and
   `reference_switches` (ADR-822) switches between gait families (a trot
   and a gallop) at a stated speed where a blend cannot join them. l3r1
   trained leon III on such a schedule (section 6); a schedule's own gain
   over the cadenced clock has not been isolated.
5. **Pay speed as a share of the command made good, linear up to the
   command.** A kernel round the command alone is flat far from it: at a
   3 m/s command the cat stopped (0.06 m/s); with
   `min(v, cmd) / max(cmd, 250)` added it ran 1.6 m/s and climbing
   [rec: rich-bay-6759] [rec: staid-shade-4488]. The same defect, and the
   same fix, held for a waypoint goal: a kernel at the wanted speed paid
   standing over running up to 2.1 m/s [rec: golden-heron-9117]; the share
   turned the cat to its points and moved it [rec: eager-haven-6416].
6. **Keep the per-step reward positive while the robot is up.** A task
   whose surviving step is net negative teaches the policy to end its
   episodes: hex3's mean episode went 28 → 3 of 200 steps
   [rec: late-sky-2627]. An `alive` term and costs scaled under it do this.
7. **Train standing in the same task as moving, gated by the command.**
   This is what the cat has, not a stand-first stage. With standing a fifth
   of the command draws and its own still-body pay, a cold run halved stand
   drift (median 210 mm, was 410–610) [rec: wise-spark-1215]. Half of the
   drift left is braking from the trot sample an episode starts at, so price
   the plan speed linearly at a stand: its integral is the distance drifted
   [rec: zesty-cliff-9219]. No run has tried a separate stand-first stage
   (see *What is not proven*).
8. **Price effort per drive when the spec judges the worst drive.** A mean
   over 21 drives charges one drive 1/21 of its excess; the cat stood on its
   right hock at 1.22–1.73× rated while the left sat at 0.45–0.91×
   [rec: eager-haven-6416]. Gate the price off with the speed asked if a
   sprint may exceed rated. c1-t8 was that change's run: the per-drive
   price put every drive at a stand at or under 0.63× rated, but stand drift
   rose to 291 mm against the 200 mm bar, and on the run it slowed to
   1.9 m/s with its worst drive a quarter under rated, speed it did not
   need to give up (`docs/probes/orun9/o8-torque.md`).
9. **Measure height and collapse over the ground** (`scan_4`, the centre
   channel of the height scan, ADR-715), never over z = 0, once there is a
   course: the cat's `collapsed` termination and height term read
   `scan_4` so the same terms hold on any course [rec: wild-vale-0638]
   (ADR-745). A policy that must step onto things reads the scan itself
   (`role="policy"`, ADR-748), which is a new actor input and so a cold
   start.
10. **Keep a course cheap.** Collide the course with the feet only
    (`collides_with`, ADR-739); each box slot costs about 2.5 s an iteration
    on 8192 environments, so ≤ 11 slots keeps a course within 3× flat
    (ADR-747) [rec: lone-ridge-2680].

## 2. The spec

1. **Judge on 10 frozen seeds with the engine's predicates**, never the
   trainer's numbers. Script the command sequence the spec asks
   (`sequence=`); before ADR-750 a scripted sequence never reached the
   engine and a verdict built on it measured nothing [rec: loud-ridge-1660].
2. **Judge standing on a spec of its own.** A speed predicate refuses a
   range that includes zero (`success_command_spans_zero`), so standing is
   `max_drift_mm` with no speed predicate [rec: wild-vale-0638].
3. **Know what a metric excludes.** `yaw_rate_error_rms_deg_s` read
   1–8 °/s while the heading drifted 100–428° over 12 s, because the
   drift fell in the windows it skips [rec: tall-ash-7464].

## 3. The trainer

1. **Brax PPO** (ADR-712): the old learner left Go1 at 3 mm/s; Brax trots it
   at 977 mm/s and trains the cat's run cold 10/10 [rec: cold-meadow-3037].
   The cat's settings: 8192 environments, unroll 20, defaults otherwise;
   14.1 s an iteration on flat on the 5090 [rec: wild-vale-0638].
2. **A non-finite environment ends as a fall** (ADR-735), so one blown-up
   environment no longer kills the run [rec: sunny-coast-7833].
3. **Warm the critic up on every warm start** (`--critic-warmup 10`,
   ADR-740). A warm start carries no critic; without the warm-up episodes
   fell 504 → 62 steps in two iterations [rec: old-mist-8631]. With it the
   cat's warm starts held their episodes [rec: wise-spark-1215]
   [rec: keen-harbor-0874].
4. **A warm start keeps the source's normaliser count** (ADR-753, automatic).
   The old reset ended 7,695 episodes in c1-t7's first 14 iterations; the
   fix, 1,012 [rec: bright-thistle-0405].
5. **A warm start needs the same observations, actions and reference**; a
   reward, goal or spec change is a declared curriculum step
   (`--init-from-task-change`). A new actor input or action needs the
   task's `body=` block (ADR-755): `--init-from-base` then maps the old
   policy onto the new layout, a new input starting as a zero first-layer
   row with fresh statistics while the shared inputs keep theirs (ADR-760),
   and a new action as a zero output at its box centre. Without a `body=`
   block it is still a cold start. The remap is shown across robots (orun9
   `b3-base1` onto v0); a same-robot input change through it has not been
   run.
6. **A fine-tune from a base model (`--init-from-base`, ADR-755) trains at
   `--learning-rate 3e-5`, a tenth of the default.** At 3e-4 the first actor
   update after the warm-up threw a base at sigma 0.14 out to 0.47, and the
   fine-tune then followed a cold curve (orun9 `b3-ft150`: 6/10 at 25, 0/10
   at 50 and 75). At 3e-5 sigma held and it walked 9/10 at 50 and 75
   (`b3-ftlr`, `docs/probes/orun9/b3-family.md`). Shown on one quadruped
   pair, base and v0; not yet on a cat-sized extrapolation or a biped.
   The same holds for the cat's warm start onto a changed termination
   (orun10 `j1-c2`): at 3e-4, σ went from 0.38 to 0.64 and the reward per
   step from 8.31 to 3.27 on the first update. At 3e-5 (`j1-c3`) σ held
   (`docs/probes/orun10/j1-c2-task.md`).

## 4. Budgets

For a reference-gait task at 8192 environments. Go-to-point and terrain
budgets are §B's.

1. **Screen at 100–150 iterations; a full run is 200–300.** orun7's r1-t3
   had 85% of its reward-per-step gain by iteration 200 and 7% more by 475
   [rec: calm-moon-2039]. c1-t4b sat flat from iteration 80 of 150
   [rec: zesty-cliff-9219].
2. **Extend by warm start only while the judged numbers still climb.** Read
   checkpoints 50/100/150 on the spec: c1-t3's run speed at a 3 m/s command
   went 1.07 → 1.30 → 1.58 m/s and earned its extension
   [rec: staid-shade-4488].
3. **A speed curriculum at a fixed tempo does not buy speed** (f1-s1, a dead
   end slower than its source) [rec: warm-hill-9213]; change the reference's
   tempo (step 1.4) instead.
4. **Keep the first checkpoint that passes, and judge every one.** The
   cold biped b1-b1 passed its walk spec 10/10 at iteration 100. Its reward
   per step went on climbing to 264, and by 200 it had traded the stride for
   a shuffle that fails step clearance; at 300 it fell. The reward curve
   alone would have kept the worst file (orun9 iteration 10,
   `docs/probes/orun9/b1-biped.md`).

## 5. Speed alone, then top speed (orun19, leo v06)

orun19 trained leo v06 (30.7 kg, 24 drives, sphere feet) on a speed task
with no reference and no style terms: a speed command, `track_speed`,
upright and alive, torque, energy and action-rate costs, terminations.
Every number below is the engine's evaluation on 10 frozen seeds, last 2 s
along the heading (`docs/probes/orun19/REPORT.md`). Shown on one robot.

1. **Give the feet a round contact before tuning the reward.** On v05's
   paw pin every policy ran on its toes with the pin shut, and the same
   speed task held 1.6–2.6 m/s whatever it was asked (orun18 `b1-s2-180`).
   On v06's balls the unchanged task's speed rose with the command, a
   0.75 m/s walk to a 4.24 m/s gallop, 0/50 falls (`s1-v06-180.md`). The
   rest of the change is one run's body against another's, not isolated.
   v06's heel pad was never loaded by any policy or clip (O2 did not ask):
   a contact a stance does not reach is not a foot.
2. **Speed first, with no reference, when speed is what is judged.** Speed
   alone reached 4.57 m/s held (`s2a-hold-150`, below); the cheetah clip's
   policy held 4.25–4.37 m/s, plateauing at the clip's ~2.5 Hz stride
   (`m1-cheetah-150.md`), and the dog's tracked to 4.36 m/s at 150 and to
   4.43 after 250 more iterations, nearer the clip and slower
   (`m2-dog-150.md`, `l1-dog-250.md`) [rec: bright-quill-0475]. A clip
   buys its order and stride where the body can follow it (the hind legs;
   v06's straight fore leg missed 10–84% of the clips' fore strides) and
   caps speed at the clip's tempo. This refines step 1.1 for a speed
   criterion; it does not overturn it for a gait criterion.
3. **Hold the command for the episode.** Resampling every 3 s left a gap
   between a walk and a ~2.1 m/s gallop; holding one command per episode
   (resample 12 s) made held speed a monotone function of the command,
   ±2–3% seed to seed, tracking to 4.63 m/s (`s2a-hold-150.md`,
   `s2a-hold-150-top.md`). Making `track_speed`'s tent symmetric instead
   lowered every speed and was rejected (`s2b-tent-150.md`).
4. **Expect the engine's deterministic policy to run faster than the
   trainer's noisy one.** s2a-hold's ~1.2× overshoot is not the speed
   signal: with its training noise (σ 0.52) the same actor runs 1.03× the
   command, deterministic 1.21× (`s2-speed-signal.md`). No regulariser
   weight closes that gap; a lower σ late might (not tested).
5. **For top speed, pay `track_speed` in full at and above the command**
   (one-sided: linear `v / cmd` below, the full weight above), warm from the
   best speed policy. That one change took the top from 4.57 to 5.72 m/s
   tracked at a 6.0 command it never trained on (Fr 8.42), 5.84 held at
   6.5, 0/100 falls (`x1b-warm-150.md`) [rec: twilight-river-5248]. A cold
   run with only the ceiling raised (5000 → 6500) stopped near 4.1 m/s
   (`x1a-cold-150.md`) [rec: green-bay-4654].
6. **A warm start may widen a goal's draw range** (`goal.range`, ADR-791;
   a banded goal's `bands` too, ADR-871) [rec: crisp-spark-8057]; the rest of a goal is still refused. On leo it
   bought nothing: asked for up to 7.5 m/s, x1b's policy held ~5.8 m/s
   whatever it was commanded to 8.0 (`x1c-ceil-150.md`)
   [rec: civic-grove-0040]. Raise the ceiling only below what the body
   reaches.
7. **At the top, read the drive clamp before another reward lever.**
   x1b-warm-150's hind hips run 1.74–1.75× rated and touch their 53 N·m
   limit on 7–9% of frames at 6.0, at a fixed 6.25 Hz stride (it gains
   speed by step length). Quartering the torque, energy and action-rate
   weights did not load the hips harder; σ rose 0.41 → 0.49 and the policy
   slowed to 3.95 m/s tracked and tipped from 6.0 up (`x1d-reg-150.md`)
   [rec: keen-dawn-4639]. When the worst drive sits at its peak, the next
   speed is a model change (step 0.1), not a weight.

## 6. Many speeds in one policy (l3r1, leon III)

l3r1 (2026-10-24/25, owner-stopped at 27.4 h) asked one policy to stand and
to run 0.5–4.5 m/s. What it established, each as an engine or trainer
feature with its probe in `docs/probes/l3r1/`:

1. **A trot and a gallop cannot be one blended schedule.** Their footfall
   orders differ at every phase origin; switch families at a stated speed
   instead (`reference_switches`, ADR-822).
2. **The fast end needs its share of training.** The fast end strode at a
   gallop's frequency only when 0.89–1.00 of episodes were commanded in the
   gallops' band, and scuttled at 4–6.5 Hz at 0.44. Weight the draw by
   bands rather than narrowing the range (`api.goal(bands=...)`, ADR-824).
3. **A stand did not train inside the gallop's bundle.** Every lever that
   gave the stand share cost the fast end; a stand trained alone passed.
   The trainer can now distil band teachers into one student
   (`--teacher`, ADR-825); the run stopped before a distilled student was
   judged, so this step does not claim it. A stand is evaluated at a
   command of 0, where the speed ratios read `None` (ADR-823).

## Where it has been shown

- **The Go1** (Playground's Go1 through Cadex, orun18; the fixed reference).
  §G: 10/10 held-out go-to-point sequences at 206.4 M env steps in 333 s
  (G2-GOTO.md). §T: flat, held-out level 0 and maze levels 0–2 each 10/10
  on one policy, level 2 9/10, level 4 1/10 (T2-SCAN.md, T2-MAZE.md).
- **leon V's concept** at the CAD's mass (33.3 kg, 14 position drives,
  sphere paws). §R: concept-trained 10/10 on the export's trot (40 Hz
  control, pre-ADR-863), cut-trained 10/10 (ADR-847). §G with only the
  model changed: 4/10, every point reached and held, 0 falls, slow walk
  legs (G3-GOTO.md).
- **The quadruped.** orun9's `b1-q1` followed §0.1–§4.1 cold on
  `orun9-quad` (9.27 kg, twelve AK80-9 position servos, a 250 mm/s trot
  generated on its legs): the walk spec passed 10/10 at iterations 150,
  200, 250 and 300, 0/10 at 50 and 100, at 4.5 s an iteration
  (`docs/probes/orun9/b1-quad.md`).
- **The biped.** orun9's `b1-b1` followed the same steps cold on
  `orun9-biped` (the servo biped, STS3215 position servos, a 160 mm/s
  two-foot walk from ADR-754's generator, §1.1 by ADR-756/757): the walk
  spec passed 10/10 at iteration 100, then failed step clearance from 150
  on (§4.4). Through §R steps 5–9 (ADR-844, ADR-845): cut-trained 10/10,
  concept-trained 7/10 on the export. The biped has not been through §G.

## Limits

What this recipe is known to miss, and what no run has shown yet.

**Open misses.**
- **The slow walk, on both robots after the Go1.** The biped passes 0/10 on
  its cut and 2/10 on its export, with every point reached and every hold
  kept; each seed fails on one leg at 0.80–0.86 of its command (G3-GOTO.md).
  The biped weighs 0.65 kg, a twentieth of the Go1, so the effort scale
  below cannot be all of it. Read step by step (G3-GOTO.md, "Step back"),
  the miss is the policy's, not the layer's or the judge's: a bare
  constant command misses the same way, the deficit is nearly absolute
  (biped 0.011–0.023 m/s, leon V 0.021–0.082, Go1 0.023–0.052), and every leg
  under 0.85 is in the bottom sixth of its walk band. The tracking kernel's
  absolute width (√σ = 0.5 m/s, biped 0.08) pays 0.985 at the judge's 15%
  tolerance at the band floor, so the reward hardly resists the miss there.
  σ/4 (0.0625) on leon V's concept confirmed it, and showed why it cannot
  simply be narrowed (G3-GOTO.md, "σ/4"): every walk leg read 0.96–0.99
  (bottom-third deficit 0.007–0.025 m/s), but above 1.1 m/s the policy stood
  still, since a narrow kernel pays nearly nothing on the way to a run speed.
  1/10, and nine seeds never reached their first run point. The writer keeps
  0.25. The next test is a kernel shaped like the judge's tolerance: a wide
  plus a narrow kernel, or a width proportional to the command.
- **A slow-turning robot's run legs are not read for speed.** The judge
  reads a leg's speed only on its straight (bearing within 10°). At the
  biped's 0.192 rad/s yaw limit, the layer alternates a turn in place (to
  30°) and a diagonal walk that drifts back to 60°. 32 of the biped's 37 run
  legs are never straight, so its speed result rests on its walk legs alone
  (G3-GOTO.md, "Step back"). This is stated here, not fixed: a judge that
  read a run leg's speed off the straight would be judging a different bar.
- **leon V's slow walk.** On §G leon V's concept passes 4/10 (3/10 under
  the 30° turn exit of ADR-865), and every
  failure is a walk leg at 0.80–0.85 of a 0.5 m/s command (constant
  0.5 m/s gives 0.433). Share 0 did not lift it (0/10, ADR-863). The
  effort-scale hypothesis is not needed (σ/4 lifted every walk leg to ≥ 0.96
  with the effort terms unchanged, above); the earlier hypothesis was the effort scale: Playground's torque and energy
  weights are in absolute N·m, and leon V weighs 2.6× the Go1, against a
  tracking kernel that pays 0.96 for a 0.1 m/s miss (`kind-ridge-3238`).
  A heavier robot than the Go1 may need mass-normalised effort terms;
  no run has tried them.
- **The go-to-point layer costs slow walking** on the Go1 too, in
  proportion to its share: 0.470, 0.458, 0.443 m/s at a 0.5 m/s command for
  share 0, 0.2, 0.5 (`kind-ridge-3238`). 0.2 is the share that passes.
- **The Go1's level 4** (70–90 mm faces) passes 1/10. More exposure
  (73.7 M more steps) moved reach, not passes, and the `feet` block's swing
  terms did not move it either: 1/10 against a control's 3/10
  (`cool-valley-2757`, ADR-861). The next lever is unknown; neither
  exposure nor swing terms are it.
- **The go-to-point judge is a probe script.** `g2_judge.py` lives in
  `docs/probes/orun21/`, which no test reads. `cadex_goto.py play` is the
  tool it drives.
- **Terrain on a robot other than the Go1.** The Go1's terrain bundles
  were written by probe scripts (`t1_levels.py`, `t2_around.py`,
  `t2_scan.py`) onto its joystick bundle. No robot has carried a leveled
  pool and a policy scan from its own script through `cadex_joystick.py`.

**Not proven.**
- **The route from an empty project** (`modest-field-9752`). The biped and
  leon V each went concept → CAD task → cut → relay → retrain →
  `cadex evaluate` (ADR-845, ADR-847), but both CADs existed before their
  task was declared. No robot has yet been taken through §R steps 1–9 in
  order.
- **A concept's task before any CAD** (`tiny-pine-0692`). `cadex_joystick.py`
  needs a bundle to write onto, and Cadex has no command that makes a
  concept's first bundle with no CAD project. Every concept run so far
  relayed a CAD export's task or used a robot's own script.
- **§G on leon V's cut.** Not run. The biped's cut has been (G3-GOTO.md).
- **Length-scaled terms.** The writer's foot swing height (0.1 m, the Go1's)
  and the sequences' 2–5 m spacing are absolute. On the biped, whose hips
  stand 0.23 m high, the swing target is near half a leg and a leg takes
  30–60 s; neither has been scaled or tested.
- **The biped skipped the concept.** Its CAD existed and no geometry was in
  question (§R), so its route began at the export; its concept spec
  (`examples/concept/orun9-biped.json`) has not trained on §G.
- **The biped's servo armature.** Its export carries armature 0 on every
  driven joint (`green-wren-7528`), so the rotor inertia does not reach the
  cut either.
- **End-to-end position targets** (E1) against §G's layer: not run.
- **Inverted knees: shown on one quadruped.** The generator's IK pulls
  toward the home pose, so a leg keeps the knee direction its build pose
  has. orun9's `b3-v1cold` built quad-qdd's legs with all four knees ahead
  of the hip–foot line (`orun9-qfam` v1, thigh 185, shank 225 mm,
  ADR-758). Following the same steps cold, it passed the walk spec 10/10
  at iterations 150 and 200 (4/10 at 50, 8/10 at 100), as b1-q1 did with
  the knees behind. `b3-v7cold` (v7, 180/180 mm, the front knee behind
  and the hind knee ahead) also passed 10/10 at 150 and 200, after standing
  still at 100 (`docs/probes/orun9/b3-family.md`). No biped has tried it.
- **Uneven legs** (short forelegs). The gait generator scales the stride
  from one hip height, the mean of the four legs', and gives every leg the
  same stride length, so a short leg is asked the long leg's stride; no run
  has tried legs of different length.
- **A stand-first stage.** Only stand-and-move in one task (§1.7, and §G's
  holds) has a run behind it.
- **Torque drives.** Every run that followed the recipe used position
  drives about the build stance; no torque-drive robot has.
