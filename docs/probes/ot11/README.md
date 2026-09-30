# ot11 — the evaluation contract

Verified against source: 2026-09-30. [Cadex-new]

**This is P1**: the frozen success spec, evaluation seeds, conditions, pass
rule and blind video judge that every ot11 policy is measured against. It was
written before any ot11 training run. The machine-readable copy is
[`contract.json`](contract.json), and `cli/tests/test_ot11_contract.py` holds
this page and that file equal.

ot10's quadruped passed the gait check and shuffled. ot9's Robin passed its
bar and wandered off. In both, the reward and the check said yes and the
owner's eye said no. This contract says what *yes* means for three
behaviours — **walk**, **reach** and **balance** — in numbers read from a
rollout trace, and it is measured on those two known failures
([below](#the-known-negatives)) before anything new is trained.

**Changing a frozen item is a recorded decision.** A changed seed, condition
range, predicate, threshold, rubric line, judge input or bar gets an ADR
entry, moves the test on purpose, and re-evaluates every earlier ot11 policy
under the changed contract.

## What is frozen, and who owns it

- This contract is the **evaluation authority**. It is the actor's.
- The product agent authors the task, the reward and the success spec it
  trains against. That spec may be stricter than this contract or shaped
  differently. It is never the authority for R1–R3.
- **The reward never judges itself.** No predicate below reads the task's
  reward, a reward term or the trainer's progress. Every predicate is
  computed from the rollout trace's component poses, its episode block and
  the accepted model.
- Thresholds are written in the mechanism's own scale (hip height, arm
  length, COM height, weight), so the same contract holds for ot10's
  quadruped, for Robin, for Heron, or for a mechanism the agent designs.

## The evaluation seeds

**1101, 1102, 1103, 1104, 1105, 1106, 1107, 1108, 1109, 1110.**

Each is the engine's rollout seed. `random.Random(seed)` draws every
condition below, in the order the engine's `EPISODE_VARIATION_ALGORITHM`
states (`src/Mod/cadex/CadexDynamics.py`). The evaluation report echoes
every drawn value. A change to the draw algorithm is a change to this
contract.

**Evaluation seeds are never training seeds.** A trainer `--seed` may never
be one of these ten values. The trainer draws its resets, pushes and goals
from its own on-device stream, so no evaluation episode is a training
episode.

## The pass rule

**Every seed must pass every predicate.** No behaviour is granted a per-seed
rate. One failed seed fails the policy. Results are never averaged across
seeds, and all ten are reported, including the ones that pass.

A behaviour is **met** only when its pre-registered confirmation evaluation
passes every predicate on all ten seeds **and** every judged seed meets the
[judge's bar](#the-blind-video-judge). When the predicates and the judge
disagree, both are recorded, and the disagreement is diagnosed before
anything is trained again.

A trace is **void**, and is not a result, when:

- its model digest is not the digest of the model read;
- it carries no policy digest;
- its drawn conditions are not the ones this contract states for that seed;
- its frames are not one per control step, or the rate is under 50 Hz.

## Definitions

All are read from the trace (`cadex-assembly-simulation-trace-v1`, one
`solver_output` frame per control step) and the accepted model.

| term | meaning |
|---|---|
| base | the mechanism's single free-joint body |
| tilt | the angle between the base's local +Z and its local +Z in the model's `solved` keyframe |
| heading | the yaw about world Z of the rotation from the solved attitude to the current one, read on the world +X axis, relative to the first timed frame |
| forward | world +X of the solved pose, carried with the base and flattened to the floor plane |
| base point | the base body's own centre of mass |
| speed | the plan displacement of the base point over the preceding 0.20 s, divided by 0.20 s |
| foot height | the lowest point of the foot body's collision geoms above the floor plane |
| foot point | the centre of the foot body's first collision geom |
| stance | a frame whose foot height is at most **1.0 mm** |
| swing | a run of consecutive non-stance frames with a stance frame on both sides. Its path runs from the stance frame before it to the stance frame after it. |
| step | a swing that is airborne for at least **0.10 s** and lands at least **0.15 hip heights**, in plan, from where it lifted |
| stance slip | between two consecutive stance frames, the plan travel of the point of the foot that was lowest in the first. A round foot that rolls is not charged. |
| hip height | the height above the floor, in the solved keyframe, of the anchor of the first joint between the base and each foot, averaged over the feet |
| arm length | the sum of the straight distances, in the solved keyframe, from the first actuated joint's anchor through each later joint anchor to the tip point |
| COM height | the height of the whole mechanism's centre of mass above the floor in the solved keyframe |
| weight | the mechanism's total mass times 9.81 m/s² |

## Walk

**Intent.** A four-legged robot walks forward across a flat floor at a
steady commanded speed. It walks with real steps: each foot lifts clear of
the floor, swings forward, lands and carries weight in turn, and the feet on
the ground do not slide. The body stays level, keeps its heading and keeps
walking after a sideways shove.

**Conditions**, drawn per seed over a **10.0 s** episode:

- reset variation: base tilt in [0°, 3°]; lift in [0, 5] mm above the lift
  at which that tilt clears the floor;
- goal: a forward speed in **[0.6, 1.0] hip heights per second**, in the
  base's heading frame, held for the episode; no lateral speed and no yaw
  rate;
- disturbance: one horizontal shove on the base, at any azimuth, of
  **[0.05, 0.20] × weight** for 0.15 s, starting between 3.0 s and 7.0 s.

**Predicates.** W3, W4 and W8 are read after a 1.0 s settle.

| id | name | measured | passes when |
|---|---|---|---|
| W1 | completes | how the episode ended | it runs the full 10.0 s and ends by truncation; no termination fires |
| W2 | upright | the largest tilt over every frame | ≤ 30° |
| W3 | tracks speed | mean forward speed, as a ratio of the commanded speed | 0.75 to 1.25 |
| W4 | goes straight | mean lateral speed, as a ratio of the commanded speed; the largest heading over every frame | ≤ 0.25 and ≤ 45° |
| W5 | steps | steps taken by each foot; the share of each foot's plan path made during steps | every foot: ≥ 4 steps and ≥ 0.70 |
| W6 | foot clearance | the median peak foot height over each foot's steps | every foot: ≥ 0.08 hip heights |
| W7 | foot slip | each foot's stance slip, as a share of its plan path | every foot: ≤ 0.15 |
| W8 | duty factor | the share of frames in which each foot is in stance | every foot: 0.40 to 0.85 |
| W9 | every leg works | the largest per-foot step count divided by the smallest | ≤ 1.5 |

W5, W6 and W7 are what the ot10 gait check could not see. A foot that
chatters in 40 ms hops takes swings but no steps (W5). A foot that lifts but
barely clears fails W6. A foot that is dragged fails W7 and W8.

## Reach

**Intent.** A robot arm fixed to a bench moves its tip to a target marker
placed at random in its workspace, stops there and holds still. Halfway
through, the marker jumps to a second place and the arm moves to it. Each
move is direct and settles without swinging past the marker.

**Conditions**, drawn per seed over an **8.0 s** episode:

- reset variation: none. The base is grounded, and the engine's reset
  variation moves only a floating base. The variation is the targets.
- goal: a tip target position. **Target A** holds from 0.0 s and **target B**
  from 4.0 s.
- Each target is the tip position, by forward kinematics on the accepted
  model, of a joint configuration with every actuated joint drawn uniformly
  in the **central 80 %** of its joint range. A draw is taken again (up to
  100 times) if the tip is under 0.10 arm lengths above the floor, if the
  model is in contact at that configuration, or if the target is under
  **0.25 arm lengths** from where the tip starts that segment (the solved
  pose for A, target A for B).
- disturbance: none.

**Held-out targets.** The twenty targets are fixed points, computed from the
accepted model before its first training run. No training configuration may
list them. Training samples its own targets from the trainer's stream.

**Predicates.** Each of Q2–Q4 must hold on both segments.

| id | name | measured | passes when |
|---|---|---|---|
| Q1 | completes | how the episode ended | it runs the full 8.0 s and ends by truncation; no termination fires |
| Q2 | final error | the largest tip-to-target distance over the last 1.0 s of the segment | ≤ 0.05 arm lengths |
| Q3 | time to target | the time from the segment's start until the tip is within 0.05 arm lengths of the target and stays there to the segment's end | ≤ 2.0 s |
| Q4 | overshoot | the furthest the tip travels past the target along the line from its segment-start position to the target, as a ratio of that line's length | ≤ 0.20 |

## Balance

**Intent.** A two-wheeled robot balances upright on the spot. It stays where
it started and keeps facing the same way; it does not roll away or turn.
When it is shoved it catches itself, comes back to rest and stays upright.

**Conditions**, drawn per seed over a **10.0 s** episode:

- reset variation: base tilt in [0°, 3°]; lift in [0, 5] mm above the lift
  at which that tilt clears the floor;
- goal: none. The robot holds the position and heading of the first timed
  frame.
- disturbance: **two** horizontal shoves on the base, each at any azimuth,
  of **[0.10, 0.25] × weight** for 0.10 s. The first starts between 2.0 s
  and 3.0 s, the second between 5.5 s and 6.5 s.

**Predicates.**

| id | name | measured | passes when |
|---|---|---|---|
| B1 | completes | how the episode ended | it runs the full 10.0 s and ends by truncation; no termination fires |
| B2 | upright | the largest tilt over every frame | ≤ 30° |
| B3 | stays in place | the largest plan distance of the base point from its position in the first timed frame | ≤ 2.0 COM heights |
| B4 | keeps heading | the largest heading over every frame | ≤ 20° |
| B5 | recovers | for each shove, the time from its end to the first frame that starts 1.0 s of rest. Rest is tilt ≤ 10° and speed ≤ 1.0 COM heights per second. | every shove: ≤ 2.0 s |

B3, B4 and B5's rest are what the ot9 bar did not measure. A balancer that
stays upright while driving away fails B3 and never comes to rest.

## The blind video judge

The numbers can be met by a motion no person would call walking. The judge is
the second reading, and it is blind.

- **Who.** A fresh `claude-opus-5-5` call, with no fallback model. A refusal
  or a harness failure is not a score.
- **What it sees.** The frozen rubric below, the behaviour's one-paragraph
  intent as written above, and the filmstrip frames of one seed. **Nothing
  else**: no reward, no metric, no seed number, no project, no report, no
  prompt, and no other seed's frames.
- **Which seeds.** **1101, 1105 and 1110**, fixed here. Each is judged in its
  own calls.
- **How many calls.** Three per seed. Each trait scores the median of the
  three.
- **The filmstrip.** Every frame stands on the dark prototype floor
  (ADR-444) and carries its time in seconds. A reach frame shows the target
  as a marker.
  - *Overview*: 12 frames, evenly spaced from 0.0 s to the episode's end, in
    a fixed three-quarter view that frames the whole path.
  - *Detail*: 12 frames, side-on, following the base. Walk: every 0.04 s
    from 5.0 s. Reach: every 0.2 s from the 4.0 s target switch. Balance:
    every 0.2 s from the first shove's onset.

The rubric block between the markers is given to the judge byte for byte.
Its SHA-256 is pinned in `contract.json`.

<!-- rubric:start -->
Score the motion shown in the filmstrip on four traits, 0 to 3 each. Judge
only what the frames show. The intent paragraph says what the robot was
asked to do. The overview frames span the whole episode; the detail frames
are consecutive moments a fraction of a second apart.

V1 Task. Does the robot do what the intent paragraph asks?
  0 - It does not: it falls, stays put when asked to move, moves away when
      asked to stay, or ends far from where it was asked to be.
  1 - It does part of it, or does it only for part of the episode.
  2 - It does it, with a visible shortfall in how far, how close or how long.
  3 - It plainly does it, from the first frame to the last.

V2 Manner. Does it do the task in the manner the intent paragraph describes,
and not by a shortcut that reaches the same end (sliding, dragging,
vibrating, hopping in place, flailing, drifting)?
  0 - The manner described is absent: the result is reached entirely by a
      shortcut.
  1 - The manner described appears now and then; the shortcut dominates.
  2 - The manner described dominates; a shortcut shows in places.
  3 - The manner described throughout, as a person would expect to see it.

V3 Control. Is the motion stable and deliberate?
  0 - It falls, tumbles, or a part passes through the floor.
  1 - It stays up but lurches, swings wildly or is visibly close to falling.
  2 - It is stable, with some wobble or an awkward posture.
  3 - It is steady and composed throughout, including after any disturbance.

V4 Consistency. Does the same quality hold across the whole filmstrip?
  0 - The motion is erratic: no two stretches look alike.
  1 - It starts one way and degrades, or works only in stretches.
  2 - It is mostly regular, with a few irregular moments.
  3 - It is regular and repeated (or, for holding still, unchanging) from
      start to end.
<!-- rubric:end -->

**The judge's bar.** On **each** judged seed: a total of **at least 9 of 12**,
and **no trait below 2**.

The judge runner and the filmstrip renderer are later units. The rubric, the
inputs, the judged seeds and the bar are frozen here, before either exists.

## Reading a trace against the contract

[`runner/measure.py`](runner/measure.py) reads the walk and balance
predicates from a trace and the model it ran. It changes nothing: no
rebuild, no rollout, no training. `cli/tests/test_ot11_measure.py` pins every
walk and balance predicate on a synthetic trace that passes it and one that
fails it for the stated reason — a trot with real steps passes all nine walk
predicates, and a chattering shuffle fails W5, W6, W7 and W9 while passing
W1, W2 and W3. The product's own evaluation command is P2's, and it takes
over from this reader.

```bash
pixi run python docs/probes/ot11/runner/measure.py walk \
  --model model-model.xml --foot c_foot_fl --foot c_foot_fr \
  --foot c_foot_rl --foot c_foot_rr --command-mm-s 80 --off-contract TRACE.json
pixi run python docs/probes/ot11/runner/measure.py balance \
  --model robin_model-model.xml --off-contract TRACE.json [TRACE.json ...]
```

`--off-contract` is for a trace that predates the contract and ran under its
own task's conditions. Its predicates are reported, a predicate whose
condition the trace did not apply reads *not measured*, and the trace can
fail but can never pass.

## The known negatives

KNOWN_NEGATIVES_SECTION
