# orun5 — closing report

Verified against source: 2026-10-07, at `f36f21b2` (the orun5 run branch).
Charter: `.ouroboros/goal.md`, "Sense the world, close the loop, judge the
motion". Every number below was measured on sb1x (linux-64, RTX 5090) on
scratch projects named `orun5-*`. The two reference projects were read and
never written. The owner ticks the criteria; this report ticks none of them.

## Where each criterion stands

| criterion | where the evidence stands | evidence | records |
|---|---|---|---|
| S1 a grounded position sensor | evidence recorded | ADR-588, ADR-589, ADR-590; `test_dynamics_position_tracker.py`; §1 | `peaceful-heron-7678`, `long-isle-5502`, `smooth-stream-7287` |
| M1 motion predicates | evidence recorded | ADR-587; §2; the circle probe on the rig's own physics | `dusty-meadow-8719`, `dusty-canyon-3027` |
| S2 a grounded load sensor | evidence recorded | ADR-591; `test_dynamics_load_sensor.py`; §3 | `tiny-lake-4065` |
| L1 a closed linkage, exported and driven | evidence recorded; the fit sweep **refuses** a loop, naming it, rather than solving it (the charter allows either) | ADR-593, ADR-594, ADR-595; `test_dynamics_linkages.py`; a live four-pin four-bar smoked and driven; §4 | `civic-sun-5811`, `spring-river-3041`, `young-aspen-5297` |
| R1 a goal held in a body's frame | evidence recorded | ADR-592; `test_dynamics_goal_frame.py`; first real run in P2; §5 | `long-cabin-6279` |
| P1 the ball-plate, as built | centring **passes 8/8**; circle on the charter's *otherwise* branch (predicate shown failing a rocking trace and passing a circling one; not trained to a pass) | §6 | `smooth-stream-7287`, `dusty-canyon-3027` |
| P2 the excavator's floor, measured | the floor **moved**, cause not separated | §7 | `hidden-sand-7542`, `misty-water-8806` |
| C1 this report | this file | §1–§10 | the record that adds this file |

The four capability figures below come from `capability_figures.py` in this
directory, which replays each test's own fixture through Cadex's real build,
MJCF export, observation path and evaluator, sweeping what the test checks
at a few points:

    pixi run python docs/probes/orun5/capability_figures.py docs/probes/orun5

## 1. S1 — a position tracker reads a free body (ADR-588 to ADR-590)

![S1](s1-position-tracker.png)

`position_tracker` is declared like a datasheet (range per axis, resolution,
rate, noise) on the component the real reader is fixed to: a touch panel on
a plate, a camera on a mast. Its channels are the tracked body's position
in that component's frame, and an `_in_range` flag.

- **Left:** the plate turns through ±160° at a 20° tilt while the ball stays
  still in the world. The panel's reading follows the ball's true position
  in the plate frame, worst error 0.24 mm against a 0.5 mm resolution.
- **Right:** past the 90 mm edge the reading drops to zeros and the flag to 0.
  It never holds a stale or clamped value, and a task terminates on the flag.
- **Noise and quantisation:** noise is added before rounding. The trainer's
  copy equals the engine's on 200 draws, and its spread is the declared σ
  within 6 %.
- **Training:** a task reading the tracker is grounded, so the "ungrounded"
  refusal does not fire. A tracker slower than the control loop is refused.
- **Velocity:** ADR-590 adds the velocity the panel's firmware would
  difference. Its noise is √2·σ/Δt, declared, not privileged.
- **Normaliser:** ADR-589 fixed the trainer's normaliser for noisy channels.
  It now floors their spread at the declaration.

## 2. M1 — predicates measure the motion (ADR-587)

![M1](m1-rock-vs-circle.png)

`assembly.success` takes `body=`, a centre held in a component's frame and an
axis. `CadexEvaluation` measures five metrics from the trace:

- `turns`: net signed turns, each frame's bearing change wrapped to half a turn;
- `laps`: `floor(|turns|)`;
- `final_distance_mm`, `mean_distance_mm` and `max_distance_mm`.

An episode that ends early measures none of them, and `check` fails it
(the ADR-586 rule).

The figure is the circle task's own spec (`laps ≥ 2`, mean distance 30–50 mm)
held against two 10 s scripted motions on the rebuilt rig's exported MJCF
(`circle_predicate.py`):

- **Rocking** ±25 mm across the circle's top reads −0.005 turns and 0 laps
  at a 45.7 mm mean radius. It fails on `laps` alone. The radius bound
  passes it, which is exactly how the reference project passed a rocking
  policy 8/8.
- **Circling** reads +3.005 turns and 3 laps at 42.8 mm, and passes.

## 3. S2 — a load sensor reads an actuator's effort (ADR-591)

![S2](s2-load-sensor.png)

`lib.servo(...).load_sensor(actuator)` grounds the actuator's applied force
or torque at the catalog's figures. The bus servos say they report load. A
PWM servo's load sensor is refused, with the reason that it reports nothing.

The figure is the load test's held arm under servos of rising stall torque:

- Below the 1816 N·mm gravity torque the reading sits on the stall line and
  the arm sags.
- Above it the reading is the gravity torque, and the sag is 0.

The test pins that the reading matches gravity within one resolution step,
and that a servo with half that stall reads exactly 908 N·mm while sagging
13.2°. **Not modelled** (named in `docs/MUJOCO.md`): the STS register reads
drive duty, which equals load only near stall.

## 4. L1 — a closed linkage, exported and driven (ADR-593 to ADR-595)

![L1](l1-four-bar.png)

A loop closure exports as an MJCF `equality/connect`, and an actuator on one
joint of the loop drives the chain. The figure is a Grashof crank-rocker
(200/80/220/120 mm) driven only by its crank, through 447° at the 0.5 ms step
the linkage tests use:

- the rocker against its circle-intersection angle: worst tip error
  0.0025 mm;
- closure residual 0.0012 mm, against the 0.01 mm MJCF pose contract
  (ADR-584).

The slider-crank test holds its 160 mm stroke within 0.01 mm of
`r cos θ + √(l² − r² sin² θ)`.

What else holds:

- **Refusals:** a loop whose closing axis would have to tilt
  (`overconstrained_loop`), and a drive on a loop with no freedom left
  (`actuator_locked_by_loop`).
- **One-freedom loops** (ADR-595): the native solver's redundancy on a
  four-pin four-bar is accepted when a screw-rank check proves the loop has
  one freedom. The same four-bar was built live through the real engine,
  smoked to a pass, and driven to the analytic rocker within 0.0032°.
- **Smoke** (ADR-594): `cadex smoke` measures every closure against the pose
  contract.
- **Fit sweep:** it refuses each joint of a loop, naming the loop. It does
  not solve it.

## 5. R1 — a goal held in a body's frame (ADR-592)

![R1](r1-goal-frame.png)

`goal(frame=component)` keeps the drawn target in that component's frame.
The policy reads it as the base sees it, and the reach metrics measure the
tip against where the target was at each frame. The figure is the
goal-frame test's base, which slides 400 mm and turns 90° in 2 s:

| goal | tip riding with the base | tip left where it started |
|---|---|---|
| held at (100, 0) in the base | 0.0 mm | 316.2 mm |
| fixed in the world | 316.2 mm | 0.0 mm |

A spec may not judge in the world a goal the task holds in a frame.

## 6. P1 — the ball-plate, rebuilt as built

On `orun5-ball-plate`, the ball is a free sphere rolling on the plate by
contact. A `position_tracker` touch panel on the plate reads it, with its
differenced velocity. There are no sliders, no hidden bead and no point goal.

![P1 hero](p1-centring-hero.png)

**Centring passes** (policy `9cb0a64c6ca1`, evaluation
`71e1646bdacd-9cb0a64c6ca1`), 8 of 8 seeds:

| predicate | bound | measured |
|---|---|---|
| `final_distance_mm` | ≤ 8 | 1.20–2.64 |
| `mean_distance_mm` | ≤ 15 | 3.11–6.41 |

All 8 seeds ran the full 300 steps, through the start kick and the
mid-episode shove. `p1-centring-seed-9001.png` is seed 9001's filmstrip.

The training curve (seed 12, 700 iterations, 256 envs, 326 s) peaked at
1.13 reward per step at iteration 535. Without a velocity input it
plateaued at 0.62, and with a privileged true velocity it reached 1.33.

**The circle task is on the charter's *otherwise* branch.** Its spec bounds
`laps ≥ 2` and mean distance 30–50 mm (§2). Five policies were trained:

- every one circulates, 3–11 laps on every seed that ran to the horizon, so
  none rocks;
- none passes, because each holds a circle tighter than the bound: mean
  radius 16–29 mm against a floor of 30;
- the closest, circle-5, reads 28.1–29.2 mm with 6 of 8 seeds completed.

The pushrod tilt (optional, needs L1) was not built.

## 7. P2 — the excavator's precision floor, measured

On `orun5-excavator`, the policy reads each bus servo's S2 load channel and
holds its goal in the track frame (R1). One run, `reach-p2-cold`, started
cold with the reference project's reward: 1400 iterations, 256 envs, seed 2.
It was evaluated on the same frozen seeds 101–110 and the same spec.

| policy | final error per seed (mm) | median | pass (≤ 15 mm) |
|---|---|---|---|
| reach-p2-cold (best) | 3.4, 17.2, 21.4, 2.5, 10.6, 5.2, 22.4, 12.5, 6.0, 12.4 | **11.5** | **7/10** |
| reach-05 (reference) | 11.0, 32.6, 25.1, 25.4, 26.7, 13.7, 20.8, 22.1, 39.3, 18.7 | 23.6 | 2/10 |

**The floor moved.** The median error halved, and 9 of 10 seeds improved.
Seeds 102, 103 and 107 still miss, so the spec still fails. Max tilt was
0.06°, and max drift 8.6 mm.

**Servo sag is ruled out directly.** At reach-05's own final commands, held
still:

- load is at most 0.19 of stall;
- the tip shifts 1.5 mm at the median and 4.3 mm at most.

Under rigid kinematics, reach-05's commands already miss the goal by a
median 19.7 mm. The reference floor was in the command, not the servo.

**Attribution caveat: one run cannot say what moved the floor.** It changed
three things at once:

- the goal frame;
- the load channels;
- an uninterrupted 1400-iteration schedule, where the reference ran a
  600 + 400 + 400 warm chain.

There is also a measurement caveat. The new error is measured against the
goal in the track frame, the reference's against a goal fixed in the world.
Drift is at most 8.6 mm, and the reference errors reproduce in the track
frame. Separating the causes needs the same schedule with a world-fixed
goal; that run was not done. The bucket four-bar (optional) was not built,
so the bucket is still driven servo-direct.

## 8. The base guidance added (ADR-596)

Three domain-neutral rules, each with its reason; no rule names a project:

- **Choose a sensor a real part could be.**
  - A free object's position comes from a `position_tracker` on the
    component the real reader is fixed to, terminated on its `_in_range`
    flag.
  - An effort comes from `load_sensor`, and only on an actuator that
    reports it.
  - A target relative to a moving base is held in that base's frame.
  - A channel no part could measure is declared privileged, with the part
    that would ground it recorded.
- **Close a linkage where the built machine would have one.**
  - Close a chain when the actuator should stay on the frame, when the
    output needs a ratio or path one pivot cannot give, or when two outputs
    move together.
  - Stay serial for independent wide-range axes, or for a chain near a dead
    point.
  - A loop is proved by smoke, never by the fit sweep.
- **State the motion as a predicate, not as where it ends.** Bound `turns`
  or `laps` for a motion that goes round, and the distance metrics for how
  far a body stays from a point, with no goal declared for it.

`cli/tests/test_agent_guidance.py` pins each rule.

## 9. The workaround ledger and the ADRs

`LESSONS.md` lists every workaround in the two reference projects (W1–W12),
its evidence and what replaced it:

- **Nine replaced:** W1, W2, W3, W4, W5, W6, W8, W9 and W11, each by this
  run's or orun4's ADRs.
- **One kept as legitimate:** W10, privileged channels used in reward
  terms only.
- **Two still open:**
  - W7, the warm-start rule (§10);
  - W12, the bucket four-bar, which was not built.

ADRs added by this run:

| ADR | decision |
|---|---|
| 587 | motion predicates: `turns`, `laps` and distance of a body about a centre |
| 588 | `position_tracker`, a grounded sensor for a free body's position |
| 589 | the normaliser follows a tracker's noisy readings and floors its channels |
| 590 | a tracker reports the velocity its firmware differences |
| 591 | `load_sensor`, the effort an actuator applies, as a bus servo reports it |
| 592 | a reach goal can be held in a body's frame |
| 593 | a closed linkage is driven from its crank; a loop the export would misstate is refused |
| 594 | `cadex smoke` measures every loop closure; a four-bar built live with rod ends |
| 595 | a redundant loop of one freedom is accepted; the driven gap sits beside its contract |
| 596 | base guidance: choose a real sensor, close a linkage, state a motion as a predicate |

## 10. Remaining defects

1. **W7, the warm-start rule, is undecided.** A warm start is refused across
   tasks whose success specs differ, even when observations and actions
   match. The reference circle task trained cold for that reason. The
   charter asks for an ADR either way, and none was written this run.
2. **The trainer's checkpoint stall was not re-measured this run.** orun4
   fixed it (ADR-576: 42.5–45.4 s down to 1.9 s per checkpoint on a
   4096-env biped). In P2's run, 1400 iterations took 3903 s and the
   25-iteration checkpoints landed evenly, 69–72 s apart. The progress file
   keeps no per-iteration times, so a residual stall cannot be separated
   from that spacing.
3. **"Not found" before a project's first script was not re-measured this
   run.** orun4's ADR-575 made a project readable from its agent's first
   tool call. Neither orun5 project exercised a fresh, script-less project.
4. **A failed `cadex script --set` silently reverts the project's
   `script.py`** to the accepted revision. During P1's circle work this
   discarded an edit twice, because a stale policy declaration failed its
   digest check. It is working as designed (only an accepted script
   persists), but nothing tells the agent its edit is gone. It cost one
   training run.
5. **`cadex smoke` misjudges a rig with a free payload.**
   - `support` treats a free ball in a grounded assembly as a robot base
     that needs a floor.
   - The `components` check counts the ball's 7.5 µm contact penetration
     against a 1e-6 mm³ overlap threshold.
6. **P1's evaluation is noise-free.** Engine evaluations draw no tracker
   noise (ADR-588), so centring was judged on clean readings, while
   training saw 70.7 mm/s of velocity noise.
7. **A driven loop at the default 2 ms step sits 0.02–0.70 mm open**, above
   the 0.01 mm pose contract. `assembly.dynamics` reports the residual, but
   smoke holds the loop still, so an agent who keeps the default step is
   not warned.
8. **A loop of two or more freedoms is still refused as redundant**, for
   example a planar five-bar. The fit sweep refuses a loop rather than
   solving it.
9. **A reward against a world `component_position` beside a goal held in a
   frame compares across frames.** This is documented, not detected.
10. **xscript has no `math`** (no sin, cos or atan2). A linkage script
    computes angles with `** 0.5` or a series.
11. **P1's circle task is not trained to a pass** (§6). P2's spec still
    fails on 3 of 10 seeds, and its improvement is not attributed (§7).

## Done claim

S1, M1, S2, L1, R1, P1, P2 and this report have evidence recorded. P1's
circle half and P2's attribution are on the terms stated above. The owner's
boxes are not ticked.

The unreconciled tail is `dusty-canyon-3027` and this report's record. A
work iteration may not reconcile, so the next reconcile pass folds both
before the critic judges this claim.
