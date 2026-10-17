# The cold-start recipe for a legged policy

Verified against source: 2026-10-17. Provenance: `[Cadex-new]`. orun8's B1
draft (`wild-forest-4815`), half proven: a cold quadruped that is not the cat
followed it to its walk spec on 10/10 seeds by iteration 150 (orun9 `b1-q1`,
`docs/probes/orun9/b1-quad.md`); the biped has not run (see *What is not
proven*).

This is the order of work that has made a cold legged policy train quickly
in Cadex, written from the runs that showed it. Each step names the record
(`[rec: slug]`, read with `governor snapshot`) or ADR that is its evidence.
A step with no run behind it says so. It lives in `training/` because most of
it is how a task is written for this trainer; the task language it uses is
the engine's (`docs/MUJOCO.md`, `docs/XSCRIPT.md`).

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
   change [rec: keen-harbor-0874].
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
   sprint may exceed rated. (c1-t8 is that change's run; its result is not in
   yet.)
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
   (`--init-from-task-change`). A new actor input means a cold start.

## 4. Budgets

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

## What is not proven

These are the parts of B1's criterion no run has shown yet. The recipe's
proof (a cold walk on one new quadruped and one biped, 10 seeds, ≤ 300
iterations) is what settles them.

- **A biped's reference has not trained.** Since ADR-754 `CadexGait` builds
  a two-foot `walk` or `run` (`assembly.gait([foot_l, foot_r], ...)`), and
  it builds into `orun8-biped`'s task bundle; no biped has trained on one
  yet. The two engine refusals that blocked step 1.1 on a biped are fixed:
  a reward may name `ref_l_lift` and `ref_l_down` (ADR-756), and a foot
  `contact` channel on flat capsule feet passes the export check (ADR-757).
  The servo biped's task by the recipe builds
  (`docs/probes/orun9/b1-biped.md`).
- **Inverted knees.** The generator's IK pulls toward the home pose, so a
  leg keeps the knee direction its build pose has; no run has tried a
  backward-bending knee.
- **Uneven legs** (short forelegs). The generator scales the stride from
  one hip height, the mean of the four legs', and gives every leg the same
  stride length, so a short leg is asked the long leg's stride; no run has
  tried legs of different length.
- **A stand-first stage.** Only stand-and-move in one task (step 1.7) has a
  run behind it.
- **A robot but the cat: the quadruped is proven, the biped is not.**
  orun9's `b1-q1` followed steps 0.1–4.1 cold on `orun9-quad` (9.27 kg,
  twelve AK80-9 position servos, a 250 mm/s trot generated on its legs): the
  walk spec passed 10/10 at iterations 150, 200, 250 and 300, 0/10 at 50
  and 100, at 4.5 s an iteration (`docs/probes/orun9/b1-quad.md`). Every
  run here used position drives about the build stance; no torque-drive
  robot has followed the recipe.
