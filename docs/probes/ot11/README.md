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
| W10 | on the floor, not in it | the lowest foot height of each foot over every frame | every foot: ≥ −0.05 hip heights |

W5, W6 and W7 are what the ot10 gait check could not see. A foot that
chatters in 40 ms hops takes swings but no steps (W5). A foot that lifts but
barely clears fails W6. A foot that is dragged fails W7 and W8.

### Decision: W10 was added after the freeze (ADR-454, 2026-09-30)

The contract was first frozen with W1–W9 (commit `ff066f1b`), and the known
negatives were measured after that commit. Measuring `w2-2` showed something
no predicate read: its feet go **up to 21.3 mm below the floor plane**, on
7.5 mm-radius feet. The likely cause is not yet measured: MuJoCo's contact
is soft, the feet weigh 1.5 g, and the servos are strong enough to drive
them in. The reader's foot heights equal MuJoCo's own geom positions to
0.0000 mm, so this is the rollout and not the reading.

A gait that paddles through the floor is not walking on it, so W10 was added
the same day, before any training. Its limit is **0.05 hip heights** (4.8 mm
on this quadruped). By estimate, a footfall at 0.3 m/s sinks about 2 mm
under MuJoCo's default contact, so the limit leaves room for a real landing
and none for a foot buried to its centre. Both known negatives were
re-measured under the changed contract. No other ot11 policy existed.
`w2-2` fails W3, W5, W7 and W9 under the contract as first frozen, and W10
as well under this one.

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

The rubric, the inputs, the judged seeds and the bar were frozen here before
the judge runner or the filmstrip renderer existed.

### What the judge is for, and what it does not see (ADR-463, 2026-09-30)

The predicates and the judge each have a job. The owner set them out in the
charter on 2026-09-30, after the judge was measured on both known negatives
([below](#the-judges-scores-on-both-negatives-adr-460)):

- **Where a predicate measures a property, the predicate is authoritative
  for it.** That covers slip, stepping, foot clearance, drift, heading and
  reach error.
- **The judge's job is what no predicate measures**: whether the behaviour
  reads as the intended one at all, and gross failures such as falling,
  flailing or the wrong motion.
- **The judge's bar still applies** to every judged seed of R1, R2 and R3.
  It is the bar as frozen.
- **Where the judge contradicts a measured predicate, the predicate wins**,
  and the disagreement is recorded.

**Known limit: the judge's manner score (V2) is not a reading of stepping
or of foot slip.** W5 and W7 are.

- *Measured.* On `w2-2` seeds 1101 and 1110, **all eighteen calls scored
  manner 2**, "real steps": the six calls the contract judges with
  (ADR-460) and the twelve of the floor-marks probe (ADR-461). On those
  seeds the foot that stepped least made 8.5 % and 3.6 % of its path in
  steps (W5, limit 70 %), and the foot that slid most slid for 60 % and
  81 % of its path (W7, limit 15 %).
- *Why.* Twelve still frames 0.04 s apart, in a window that follows the
  base, show legs in different positions. They do not show that a foot on
  the floor is moving across it, or how short and how brief each lift is.
  W5 and W7 are totals over the whole episode, which twelve frames do not
  hold.
- *What follows.* A shuffle that stays upright can meet the judge's bar. It
  cannot pass the contract: W5 and W7 are read on all ten seeds, and a
  behaviour is met only when the predicates pass **and** the bar is met.
- *Status.* This is a recorded limit. It does not block P1, and it calls
  for no further judge probe.

**Nothing frozen changed, so nothing is re-evaluated.** No seed, condition,
predicate, threshold, rubric line, judge input, judge instruction or bar
moved. Every earlier reading and score stands as measured. The limit and
the jobs are in `contract.json` as `judge_scope`, beside the frozen `judge`
block and not in it, and the decision is its second `decisions` entry.

### The procedure (ADR-460)

[`runner/judge.py`](runner/judge.py) is the judge. It was pinned before any
ot11 policy was judged, and it adds to the frozen items above without
changing one. Changing it later is a recorded decision that re-judges every
earlier ot11 policy.

```bash
pixi run python docs/probes/ot11/runner/judge.py walk \
  --evaluation PROJECT/evaluations/<revision>-<policy> --seed 1101 \
  --label NAME --out retained/judge-NAME-seed-1101.json
```

- **Each call is a fresh Claude Code process** in a new, empty directory
  outside the repository: `--model claude-opus-5-5`, no fallback model,
  effort `high`, one tool (`Read`), no MCP servers, no skills, no user
  settings, hooks, memory or `CLAUDE.md`, and no session kept.
- **Its system prompt** is five sentences of instructions followed by the
  rubric block, byte for byte. The instructions say what a sheet is (twelve
  frames, read left to right, each carrying its time) and what to reply
  with (one JSON object of four scores, each with a one-sentence reason).
  They name no behaviour. Their SHA-256 is pinned in `contract.json`
  (`judge_procedure`) and in `cli/tests/test_ot11_judge.py`.
- **Its one message** is the behaviour's intent paragraph and the paths of
  the seed's two sheets, copied into the one directory it can read as
  `overview.png` and `detail.png`. The seed number and `--label` go into
  the receipt and never to the judge.
- **The sheets are the evaluation's.** They are read through
  `evaluation.json`. A sheet whose digest is not the one the report
  recorded is refused, and so is a seed the contract does not judge.
- **What is not a score.** A reply without four integer scores is retried
  once. A second failure, a refusal, an error from the harness, or an
  answer from any model but `claude-opus-5-5` writes no score: the attempts
  are kept as `<out>.failed.json` and the runner exits 2.
- **The receipt** (`ot11-judge-v1`) carries every call's scores, reasons
  and reply, the medians, the total, whether the bar is met, the digests of
  the rubric, the instructions, the intent and both sheets, and the policy,
  task and model the evaluation measured.

## Reading a trace against the contract

The reading is the product's (ADR-455). `src/Mod/cadex/CadexEvaluation.py`
turns a trace into behaviour metrics — gait, reach and posture — and holds
predicates against them; `CadexDynamics.evaluation_rig` reads the model.
[`runner/measure.py`](runner/measure.py) is the contract's binding and
nothing else: which product metric each frozen predicate bounds, and the
numbers the definitions above fix. It changes nothing: no rebuild, no
rollout, no training.

| predicates | product metrics |
|---|---|
| W2, W3, W4 | `max_tilt_deg`, `speed_ratio`, `lateral_ratio` and `max_heading_deg` |
| W5, W6, W7 | `steps_min` and `step_share_min`, `step_clearance_hip_heights_min`, `slip_share_max` |
| W8, W9, W10 | `duty_factor_min` and `duty_factor_max`, `step_count_ratio`, `foot_lowest_hip_heights_min` |
| Q2, Q3, Q4 | `final_error_arm_lengths_max`, `time_to_target_s_max`, `overshoot_ratio_max` |
| B2, B3, B4, B5 | `max_tilt_deg`, `max_drift_com_heights`, `max_heading_deg`, `recovery_s_max` |

W1, Q1 and B1 are read from the episode. "Every foot", "both segments" and
"every shove" are the worst one. A metric that could not be measured fails.

`src/Mod/cadex/cadex_tests/test_evaluation_metrics.py` pins every metric on
a motion that passes it and one that fails it, and
`cli/tests/test_ot11_measure.py` pins every frozen predicate the same way: a
trot with real steps passes all ten walk predicates and a chattering shuffle
fails W5, W6, W7 and W9 while passing W1, W2 and W3; a direct reach passes
Q1–Q4 and a swing past the target fails Q4 alone. **The `w2-2` shuffle is a
failing fixture**: the base and feet of its stored rollout
(`cadex_tests/fixtures/ot10_w2_2_feet.json`) fail W3, W5, W7, W9 and W10 in
both suites.

**The product's evaluation command is `cadex evaluate`** (ADR-457,
`docs/CLI.md`). A task declares its spec with `assembly.success`, and the
command rolls the accepted policy on the spec's seeds under the spec's
conditions and writes `evaluation.json` into the project: pass or fail per
seed and per predicate, the behaviour metrics, the reward by term, how each
episode ended and every value each seed drew. It takes no behaviour's name.
The reader below remains for a trace that predates a spec.

```bash
pixi run python docs/probes/ot11/runner/measure.py walk \
  --model model-model.xml --foot c_foot_fl --foot c_foot_fr \
  --foot c_foot_rl --foot c_foot_rr --command-mm-s 80 --off-contract TRACE.json
pixi run python docs/probes/ot11/runner/measure.py balance \
  --model robin_model-model.xml --off-contract TRACE.json [TRACE.json ...]
pixi run python docs/probes/ot11/runner/measure.py reach \
  --model arm-model.xml --tip c_hand:0,0,40 \
  --target 0:4:120,0,180 --target 4:8:60,90,140 TRACE.json
```

A task can now state a goal (P3, ADR-462): `assembly.goal` declares a
commanded speed or a reach target, each seed draws it after its shoves,
and `cadex evaluate` reads `speed_ratio`, `lateral_ratio` and the reach
metrics against what the episode drew. Nothing is given on a command line
there. This reader still takes the commanded speed and the reach targets
as arguments, because the traces it exists for predate a goal.

`--off-contract` is for a trace that predates the contract and ran under its
own task's conditions. Its predicates are reported, a predicate whose
condition the trace did not apply reads *not measured*, and the trace can
fail but can never pass.

## The known negatives

Measured on 2026-09-30, before any ot11 training run. Both projects are
read-only and nothing was written to either. Both readings are
**off-contract**: the policies predate the contract, so they ran under their
own tasks' conditions, not the ones above. They can fail and cannot pass.
The video judge was run afterwards, on the contract's conditions
([below](#the-judges-scores-on-both-negatives-adr-460)).

### ot10's `w2-2` shuffle fails the walk spec, on stepping and slip

Policy `7a4e8c23…`, model `49d11013…`, task `b0913fa0…`, on
`ot10-quadruped-3-w2`. Hip height 96.7 mm, so a step must land 14.5 mm from
where it lifted, a step must clear 7.7 mm and a foot may sink 4.8 mm. The
commanded speed is taken as 80 mm/s, which is what its task's reward asked
for. Receipt: [`retained/p1-w2-2.json`](retained/p1-w2-2.json), from the
project's own stored rollout (no seed).

| predicate | front left | front right | rear left | rear right | limit | verdict |
|---|---|---|---|---|---|---|
| W5 steps | 18 | 21 | 5 | 7 | ≥ 4 | pass |
| W5 share of path made in steps | 0.36 | 0.38 | 0.14 | 0.14 | ≥ 0.70 | **fail** |
| W6 step clearance, mm | 19.0 | 19.5 | 10.4 | 9.7 | ≥ 7.7 | pass |
| W7 stance slip share | 0.32 | 0.33 | 0.67 | 0.57 | ≤ 0.15 | **fail** |
| W8 duty factor | 0.52 | 0.51 | 0.73 | 0.69 | 0.40–0.85 | pass |
| W10 lowest foot height, mm | −17.6 | −21.3 | −8.4 | −8.9 | ≥ −4.8 | **fail** |

- **W5 fails.** The feet leave the floor 60, 66, 48 and 61 times in 10 s,
  and only 18, 21, 5 and 7 of those are steps. The typical swing is airborne
  for 0.08 s at the front and **0.04 s at the rear**, and the typical rear
  swing peaks at **2.7 mm**. That is chatter. Steps carry 14–38 % of each
  foot's travel.
- **W7 fails.** A third of each front foot's travel, and 57–67 % of each
  rear foot's, is made with the foot on the floor. The rear feet are
  dragged.
- **W9 fails.** The front feet take 4.2 times the steps the rear feet take
  (limit 1.5).
- **W3 fails.** It runs at 152.6 mm/s, 1.91 times the 80 mm/s its reward
  asked for (limit 0.75 to 1.25).
- **W10 fails**, as the decision above describes.
- **W1, W2, W4, W6 and W8 pass**: it completes, tilts 15.9° at most, turns
  30.5° at most, and the few steps it does take clear the floor. The old
  gait check read only what these read, which is why it said `walked = true`.

So the shuffle fails for the reason the owner gave: it does not step, and it
slides. It does not fail by accident on staying up or on heading.

**On the ten contract seeds**, under the w2 task's own reset variation, mass
randomisation and 0.3–1.5 N shove, it fails on **all ten**
([`retained/p1-w2-2-seeds.json`](retained/p1-w2-2-seeds.json)). W5, W7, W9
and W10 fail on every seed. It also tips on two seeds (1106 at 6.46 s, 1108
at 0.84 s) and passes 30° of tilt on five more. ot10 reviewed one rollout
with no seed, so none of that was seen. These episodes were rolled by the
engine's `CadexDynamics.rollout_policy` from the run's stored bundle; the
same call with no seed reproduces the project's stored trace pose for pose.

### ot9's Robin fails the balance spec: it wanders and it turns

Policy `ef71f370…`, model `933b1ac6…`, task `1f8c1040…`, on `ot9-robin`:
the ten stored ot9 evaluation traces (ot9's seeds 0–9, 8.0 s, reset
variation only, no shove). COM height 52.4 mm, so it may move 104.8 mm.
Receipt: [`retained/p1-robin.json`](retained/p1-robin.json).

| predicate | measured, over the ten seeds | limit | verdict |
|---|---|---|---|
| B2 upright | 2.78° to 5.35° | ≤ 30° | pass on all ten |
| B3 stays in place | 829.4 mm to 850.8 mm (15.8 to 16.2 COM heights) | ≤ 104.8 mm (2.0) | **fail on all ten** |
| B4 keeps heading | 130.9° to 131.6° at most; 86.3° to 87.5° at the end | ≤ 20° | **fail on all ten** |
| B1 completes | ran its own task's 8.0 s, by truncation | 10.0 s | not measured |
| B5 recovers | no shove was applied | ≤ 2.0 s | not measured |

Robin is upright on every seed and fails on every seed. It drives away at
109–113 mm/s, twice the 52.4 mm/s that counts as rest, so it would not
satisfy B5's rest either. ot9's bar passed it 10 of 10; this spec says it
wanders.

### On the contract's conditions, through the product (ADR-457, ADR-458)

Measured on 2026-09-30 with `cadex evaluate`, before any ot11 training run.
Each read-only project was copied to a new `ot11-*` project, and the copy's
task was given the contract's predicates, seeds and conditions as an
`assembly.success` spec. The policy is unchanged: the engine verified it
against the bundle it was trained on (`assembly.policy(trained_task=...)`)
and proved the rebuilt task the same task. No seed was void.

These are the first readings under the contract's own shoves and horizon, so
B1 and B5 are now measured.

- **Both specs state `randomisation=[]`** (ADR-458). The contract lists a
  reset variation and shoves and no randomisation, so the mechanism is
  judged as built. The w2 task varies the tray's mass by 0.85 to 1.15 to
  train, and the first product reading (ADR-457) kept that draw, because a
  spec could not yet switch it off. That reading is superseded by the table
  below and is kept in the copy's `PROGRESS.md`. The mass draw came first in
  each seed's stream, so removing it also changed which start and which
  shove each seed draws: these are different episodes from the first
  reading's, and every drawn value is in the receipt. Robin's task never
  randomised, and its ten rows are number for number the first reading's.
- **W3 and the lateral half of W4 are not stated**, because a task cannot
  state a commanded speed until P3. The walk spec on the copy is W1, W2,
  W4's heading, and W5 to W10.

**ot10's `w2-2`, on `ot11-w2-negative`: 0 of 10 seeds pass.** Receipt:
[`retained/p2-w2-2-evaluation.json`](retained/p2-w2-2-evaluation.json).

| predicate | bound | seeds passing | measured, over the seeds |
|---|---|---|---|
| W1 completes | ran to 10.0 s | 8 | `tipped` fired on 1107 (6.26 s) and 1110 (6.32 s) |
| W2 upright | ≤ 30° | 2 | 13.9° to 46.3° |
| W4 heading | ≤ 45° | 9 | 19.1° to 59.3° |
| W5 steps by the foot that took fewest | ≥ 4 | **0** | 0 to 3 |
| W5 share of path made in steps | ≥ 0.70 | **0** | 0.00 to 0.08 |
| W6 step clearance, hip heights | ≥ 0.08 | 6 | 0.045 to 0.126 on the nine seeds where every foot stepped |
| W7 stance slip share | ≤ 0.15 | **0** | 0.49 to 0.81 |
| W8 duty factor | 0.40 to 0.85 | 9 low, 9 high | 0.12 to 0.96; seed 1108 fails both ends |
| W9 every leg works | ≤ 1.5 | **0** | 3.7 to 11 on the nine seeds where every foot stepped |
| W10 lowest foot height, hip heights | ≥ −0.05 | **0** | −0.26 to −0.14 |

It fails W5 and W7 on every seed, which is the reason the owner gave: the
foot that stepped least took at most three steps in ten seconds and made at
most 8 % of its path in steps, and the foot that slid most slid for 49 % to
81 % of its path. W9 and W10 also fail on all ten. W6 passes on six: the few
steps it does take mostly clear the floor, as the off-contract reading
found. It is also far less steady than its one unseeded rollout showed. It
passes 30° of tilt on eight seeds and tips over on two. On the seed
the reward paid most, 1109 (836.0), the foot that stepped least took one
step and made 2.7 % of its path in steps.

**ot9's Robin, on `ot11-robin-negative`: 0 of 10 seeds pass.** Receipt:
[`retained/p2-robin-evaluation.json`](retained/p2-robin-evaluation.json).

| predicate | bound | seeds passing | measured, over the seeds |
|---|---|---|---|
| B1 completes | ran to 10.0 s | 4 | `fallen` fired on six seeds, between 3.10 s and 9.08 s |
| B2 upright | ≤ 30° | 4 | 3.5° to 64.2° |
| B3 stays in place | ≤ 2.0 COM heights | **0** | 9.2 to 18.7 (480 mm to 982 mm) |
| B4 keeps heading | ≤ 20° | **0** | 131° to 168° |
| B5 recovers from every shove | ≤ 2.0 s | **0** | both shoves recovered from on two seeds, in 3.19 s and 6.39 s at worst; on the other eight, never |

Robin wanders and turns on every seed, as the off-contract reading said.
Under shoves of 0.10 to 0.25 × its weight it also **falls on six seeds of
ten**. ot9 never shoved it.

### The filmstrips of both negatives (ADR-459)

`cadex evaluate` now draws the filmstrip this contract describes, from the
traces an evaluation keeps (`docs/CLI.md`, *The film*). Both negatives were
filmed with `--film-only` from the traces of the two evaluations above, with
no new rollout, on the three judged seeds. The sheets below are the second
draw: the detail now follows the base (ADR-460), and the overview sheets
came out byte for byte as they were.

```
cadex evaluate --project ot11-w2-negative    --film-only --film 1101,1105,1110 \
               --detail-start 5.0 --detail-step 0.04
cadex evaluate --project ot11-robin-negative --film-only --film 1101,1105,1110
```

The walk's detail window (every 0.04 s from 5.0 s) is the two flags. The
balance's (every 0.2 s from the first shove's onset) is the command's
default: the detail starts at the seed's first drawn disturbance. Each film
block is in its receipt under `film`, with every sheet's sha256 and frame
times. Drawing is repeatable: the six sheets of each project came out byte
for byte the same on two separate draws. The encoded video did not (same
size, different digest), so a video's sha256 identifies a file, not a
rollout.

| | `w2-2` | Robin |
|---|---|---|
| sheets, three seeds | 62.6 s | 54.0 s |
| video, seed 1101 | 101 frames, 179.0 s, 386 KB | 92 frames (it fell at 9.08 s), 154.4 s, 231 KB |
| sheet size, 1036×776 | 149 KB to 239 KB | 107 KB to 183 KB |
| detail window | 5.00 s to 5.44 s on all three | 1101 from 2.22 s, 1105 from 2.40 s, 1110 from 2.06 s |
| detail follows | the base, `c_tray` | the base, `comp_chassis` |
| solids drawn | 78,303 triangles, in the design's materials, floor slab left out | 62,948 triangles, in the design's materials |

Robin's seed 1110 fell at 4.26 s, before the last of twelve moments from its
2.88 s shove. The window slides back so its last frame is the fall; the
block records both the requested start and the one shown.

Seed 1101 of each, as committed (the other two seeds' sheets and both videos
stay in the projects):

| | overview | detail |
|---|---|---|
| `w2-2` | [`film-w2-2-seed-1101-overview.png`](film-w2-2-seed-1101-overview.png) | [`film-w2-2-seed-1101-detail.png`](film-w2-2-seed-1101-detail.png) |
| Robin | [`film-robin-seed-1101-overview.png`](film-robin-seed-1101-overview.png) | [`film-robin-seed-1101-detail.png`](film-robin-seed-1101-detail.png) |

**The detail is side-on, following the base** (ADR-460). The first draw
followed the centre of the whole design, which is not what the frozen text
says. The product was changed, not the contract: the window is now centred
on the base the evaluation measured (`rig.base`, the mechanism's single
free-joint body) in every frame, and side-on is measured on that body, from
where it started to where it was farthest away. On the quadruped the window
grew from 141 mm to 161 mm of half-width on seed 1101, because it must hold
the legs on both sides of the base. On Robin it changed by under 1 mm.
`cli/tests/test_film.py` holds it on a design whose base walks away from a
part left behind.

**A frame of an episode with a target shows it as a marker** (ADR-463).
This was the one place where the product's filmstrip was not yet the frozen
text. Since P3 (ADR-462) an evaluation's trace carries the target in every
frame (`goal`, named by `goal_channels`). The film now draws a ring centred
on the target in force at each frame's own time, in both sheets and in the
video (`docs/CLI.md`, *The film*). The ring is drawn over the solids and is
hollow, so a tip that arrives neither hides it nor is hidden by it. The
product was changed, not the contract, and it landed before any reach film
was drawn or judged.

It does not apply to these two: neither task states a target. Seed 1101 of
`ot11-w2-negative` was drawn from its stored trace by the film before and
after the change, and both sheets came out byte for byte the same.

### The judge's scores on both negatives (ADR-460)

Judged on 2026-09-30, before any ot11 training run, from the sheets above:
three calls a seed, eighteen calls in all. Every call returned a score. None
was refused, retried or answered by another model. Receipts:
`retained/judge-w2-2-seed-*.json` and `retained/judge-robin-seed-*.json`.

| policy | seed | V1 task | V2 manner | V3 control | V4 consistency | total | bar (≥ 9, none under 2) |
|---|---|---|---|---|---|---|---|
| `w2-2` | 1101 | 1 | 2 | 0 | 1 | 4 | **not met** |
| `w2-2` | 1105 | 1 | 1 | 0 | 1 | 3 | **not met** |
| `w2-2` | 1110 | 1 | 2 | 0 | 1 | 4 | **not met** |
| Robin | 1101 | 0 | 1 | 0 | 1 | 2 | **not met** |
| Robin | 1105 | 1 | 1 | 2 | 1 | 5 | **not met** |
| Robin | 1110 | 0 | 1 | 0 | 1 | 2 | **not met** |

Each cell is the median of three calls. The three calls agreed on every
trait of every seed but one (Robin 1105, V2: 1, 2, 1).

**Neither negative meets the bar on any judged seed**, so the judge and the
predicates agree on both verdicts. Where they differ is recorded here.

- **Robin: the judge says what the numbers say.** On all three seeds it
  reports a quarter turn in the first second and a steady drift away, which
  is B4 and B3. It reports the falls on 1101 (9.08 s) and 1110 (4.26 s),
  which are B1 and B2. On 1105, the seed that stays upright (4.2° of tilt at
  most), it scores control 2 and still fails the task.
- **`w2-2`: the judge sees a fall on two seeds where no termination
  fired.** On 1101 and 1105 it reports the robot down and still from about
  8 s and 6.4 s. The traces agree: the base goes to 42° of tilt and its
  position does not change again. The w2 task's own `tipped` termination
  did not fire, so W1 passes on both seeds. **W2 fails on both** (43.6° and
  43.7° against 30°), so the contract does read the fall. It is the task's
  termination that missed it.
- **`w2-2`: the judge does not see the shuffle.** This is a disagreement on
  one trait, and the predicates are the ones to trust. On 1101 and 1110
  every call scored manner 2, "real steps" seen in the detail frames. The
  same seeds measure 3 and 1 steps by the foot that stepped least, 8.5 %
  and 3.6 % of its path made in steps (W5, limit 70 %), and 60 % and 81 %
  of a foot's path made sliding (W7, limit 15 %). Twelve frames 0.04 s
  apart show legs in different positions. They cannot show that a foot on
  the floor is moving across it, least of all in a window that follows the
  base. The rear feet's typical swing lasts 0.04 s (measured off-contract
  above), which is the gap between two detail frames.
- **So `w2-2` fails the judge for falling, not for shuffling.** The
  judge's bar is a second reading that catches what a person would see in
  twenty-four frames. It is not a reading of stepping or slip. A policy
  that shuffled without falling could score manner 2 here. That is why a
  behaviour is met only when the predicates pass **and** the bar is met,
  and why this finding changes no frozen item: the rubric, the filmstrip
  and the bar stand as frozen.

### A probe: floor marks in the detail sheet, measured and not adopted (ADR-461)

Measured on 2026-09-30, before any ot11 training run. The finding above
leaves a judge that scores a shuffle's manner as "real steps". This probe
asked whether the detail sheet can be made to show slip, so that the judge's
manner score (V2) reads it. **It cannot, by this means: every call still
scored manner 2.** No frozen item, and nothing in the product, was changed.

**The rule, written before the first call.**

The rule was fixed in the actor's working notes before the first call. It
was not committed beforehand: it first reached the repository in the same
commit as the results. From ADR-462 on, a probe's or a run's rule is
committed before its first call.

- **One change to the film.** The floor of each detail frame keeps a light
  mark wherever a drawn solid has touched it since the episode began:
  within 1.0 mm of the floor plane, or under it, on a 2 mm grid. The marks
  are fixed to the floor while the window follows the base, so a part set
  down and lifted leaves separate prints and a part dragged leaves a
  streak. The overview, the frame times, the view and the window are
  untouched. A floor-fixed window was the other candidate and was not
  drawn: between two frames 0.04 s apart a sliding foot moves about 5
  pixels, in separate tiles, where a mark shows the whole slide inside one
  frame.
- **Two arms, in order.** *A*: the marked sheet, the judge procedure
  untouched. *B*, only if A does not move the score: the same sheet, and
  one sentence added to the judge's instructions saying what a mark is:

  > In the detail sheet the floor keeps a light mark wherever a part of the
  robot has touched it since the episode began; the marks are fixed to the
  floor, so a part set down and lifted leaves a separate print and a part
  dragged across the floor leaves a streak or a smear.

- **Which seeds.** `w2-2` seeds 1101 and 1110, the two whose manner scored
  2. Three calls a seed, as the contract judges.
- **What would adopt it.** A manner median under 2 on both seeds. Then the
  change is a recorded contract decision and all six judged seeds of both
  negatives are judged again. Otherwise nothing frozen changes, the film
  stays as it is, and there is no third arm.

**Measured.** `ot11-w2-negative` was filmed again from its stored traces, no
new rollout, with the change applied. Both overview sheets came out byte for
byte as before. By 5.0 s the floor carried 8,074 marked cells on seed 1101
and 5,686 on seed 1110. Twelve calls, 109 s of model time, $0.48 at list
price. Every call scored; none was refused, retried or answered by another
model.

| arm | seed | V1 task | V2 manner | V3 control | V4 consistency | total |
|---|---|---|---|---|---|---|
| as judged (above) | 1101 | 1 | 2 | 0 | 1 | 4 |
| A: marks | 1101 | 1 | 2 | 0 | 1 | 4 |
| B: marks and the sentence | 1101 | 1 | 2 | 0 | 1 | 4 |
| as judged (above) | 1110 | 1 | 2 | 0 | 1 | 4 |
| A: marks | 1110 | 1 | 2 | 0 | 1 | 4 |
| B: marks and the sentence | 1110 | 1 | 2 | 0 | 1 | 4 |

Each cell is the median of three calls. All twelve calls scored manner 2.
Eleven of the twelve scored 1, 2, 0, 1; one call of arm A on seed 1110
scored 2, 2, 1, 2.

- **Arm A: the judge did not mention the marks.** Its reasons are the ones
  it gave before ("real steps with feet lifting and swinging forward"). On
  1110 two of three calls said the feet shuffle in places and still scored
  2, exactly as two of three had before the marks.
- **Arm B: the judge read the marks, and read them as prints.** All six
  calls called the prints "mostly separate": "clumped and smeared in
  places" on 1101, "elongated into short streaks that suggest some foot
  sliding" on 1110. That is rubric level 2 in its own words: the manner
  dominates and a shortcut shows in places.
- **The reading is a fair one of what was drawn.** `w2-2` does not drag a
  planted foot in one long line. Each foot leaves the floor four to seven
  times a second (37 to 52 times on seed 1101, 24 to 42 on seed 1110, for
  a median 0.04 s to 0.07 s each) and slides between lift-offs, so the
  floor shows a run of short dashes, not a streak. The marks say "lifts
  often, slides a little each time". What makes it a shuffle is how short
  and how brief each lift is, and how much of the path the slides add up
  to. Those are W5 (3 and 1 steps by the foot that stepped least) and W7
  (60 % and 81 % of a foot's path made sliding). Both are totals over the
  whole episode, which twelve frames do not hold.

**So nothing is adopted.** The film draws no marks, the judge's instructions
are the pinned ones, and the probe entered no decision in the contract's
`decisions` list. (The limit it measured was recorded there afterwards, as
a known limit, by ADR-463.) The judge's manner score is not a reading of stepping or slip and is
not to be treated as one: **W5 and W7 are**, and the pass rule requires the
predicates and the bar together. A shuffle that stays upright can still meet
the judge's bar. It cannot pass the contract.

**What this does not show.** No policy that really steps has been filmed,
so the judge's manner score has been seen on a shuffle and never on a walk.
The first ot11 policy that passes W5 and W7 is the first chance to see
whether the judge tells the two apart at all.

Receipts: `retained/probe-marks-a-w2-2-seed-*.json` and
`retained/probe-marks-b-w2-2-seed-*.json`, as the runner wrote them.
[`probe-marks-w2-2-seed-1101-detail.png`](probe-marks-w2-2-seed-1101-detail.png)
is the marked sheet of seed 1101. `retained/probe-marks.patch` is the change
to `cli/cadex_cli/film.py` and the sentence in `runner/judge.py`, against
commit `81873196`; it was reverted before this was committed. Afterwards the
project's film was drawn again by the unchanged product.

## The loop, run by the product agent (P4, ADR-464)

These are **training rounds, not confirmation evaluations**. None of them
counts for R1–R3. Each R criterion is judged only on a later
pre-registered confirmation evaluation, which is also where the blind
judge scores the film.

### How long one tool call may block

`runner/block_probe.py` gives one `claude -p` call, with the flags
`cadex -p` uses and `claude-opus-5-5`, a single standard-library MCP tool
that sleeps for the time it is asked. A **900 s** call blocked for 900.1 s
and returned its answer with no error. That is `train_status`'s longest
`wait_s`. The 5 s control call returned in 5.1 s. Claude Code was 2.1.285.
Receipts: `retained/p4-block-probe-900s.json` and
`retained/p4-block-probe-5s.json`.

In the real turn below, the longest blocking calls were `train_status` at
618.6 s and `evaluate` at 189.8 s. Neither returned an error.

### Balance, on `ot11-robin-1`: one round, and it passed

`ot11-robin-1` is a copy of `ot9-robin`. `ot9-robin` itself was not
touched, and its baseline policy `ef71f370…` stays in the copy's store,
undeclared.

`runner/rounds.py` drives the product agent through `cadex -p`. It runs
the frozen first prompt, `prompts/balance.loop.prompt.txt`, and then
continues with `prompts/continue.loop.prompt.txt` while the project's loop
ledger shows neither a pass nor four evaluated runs. Registration:
`retained/p4-robin-1-registration.json`. The prompt hands over the frozen
balance spec in xscript. The agent wrote it into the script byte for byte;
this was checked by a diff after the turn. The task, the reward, the
observations, the terminations, the training conditions and the settings
are all the agent's.

| run | settings | budget | ended | GPU wall time | evaluated policy | verdict |
|---|---|---|---|---|---|---|
| `bal-1` | 650 it × 1024 envs, seed 7 | 900 s | `budget_exhausted` at iteration 400 | 900.6 s | iteration-400 checkpoint `8919a22d…` | **pass, 10 of 10 seeds** |

- **The run's reason** cited the baseline's measurements: B3 drift of
  about 16 COM heights against 2.0, B4 heading of about 131° against 20°,
  and B5 never coming to rest.
- **What the agent changed.**
  - The policy now reads only declared sensors: an IMU on the board and an
    encoder on each wheel.
  - The chassis pose, COM and torques are privileged.
  - The reward pays for holding position, heading and low speed. It
    trains under shoves of 0.08–0.30 × weight, wider than the spec's.
  - Terminations are looser than the spec's limits.
- **The evaluation.** `evaluations/cbf14e3c6865-8919a22dae1f/` in the
  project. Worst seed on each predicate:

  | predicate | worst seed | limit |
  |---|---|---|
  | B1 | all ten ran 10.0 s, by truncation | the full 10.0 s |
  | B2 | 11.5° | 30° |
  | B3 | 0.92 COM heights (48 mm) | 2.0 |
  | B4 | 0.97° | 20° |
  | B5 | 0.42 s | 2.0 s |

  No seed was void.
- **The turn.** One turn of 24.5 minutes, with 28 tool calls. It cost
  $2.80 as the harness reported it.
- **The film.** Seed 1101:
  [overview](p4-robin-1-bal-1-seed-1101-overview.png) and
  [detail](p4-robin-1-bal-1-seed-1101-detail.png).

Receipt: `retained/p4-robin-1-rounds.json`. It holds the ledger, the run's
registration and ending, the per-seed rows and the tool timings. It does
not include the transcript.

**What this round does not show.**

- **No revision.** The first evaluation passed, so the stop rule ended the
  session and nothing was revised. P4's requirement of three motivated
  rounds is **not met on balance**.
- **The ledger's `trained_by_run` is empty for this evaluation.** It
  matches a run's *final* policy only, and a budget-exhausted run has
  none. The agent evaluated a checkpoint, so the ledger cannot link the
  evaluation to `bal-1`. This receipt makes the link by digest instead.
  *Fixed afterwards (ADR-464 follow-up):* `loop.runs_that_trained` now
  names `bal-1` for `8919a22d…`. The row above stays as written.
- **Robin's model has not been confirmed.** The policy reads an IMU the
  mechanism declares on its board component, but no IMU part is modelled.
  The agent said so itself. R3 needs a confirmation evaluation and the
  judge's bar.
  *Measured afterwards:* the trainer (MJX) and the rollout (MuJoCo)
  read the same numbers on every channel to float32 rounding over 200
  states (`runner/obs_parity.py`, `retained/r3-robin-1-obs-parity.json`).
  The gyro channel reads in the world frame, not the board's. The sensor
  parts stay declared rather than modelled (ADR-408); only the product
  agent may change the mechanism.

### Reach, on `ot11-heron-1`: four rounds, and 9 of 10 seeds at the last

`ot11-heron-1` is a copy of `ot8-heron-b`, the arm ot8 accepted (G2).
`ot8-heron-b` itself was not touched. The accepted script had a reach task
with one fixed target and no goal, and no policy had been trained on it.

**The held-out targets were drawn before any training.** The contract says
the twenty reach targets are fixed points computed from the accepted
model before its first training run. `runner/goals.py` draws them the way
an evaluation does: the spec's conditions, one `random.Random(seed)`
stream, and the engine's own `draw_episode_goals`. It drew them from a
scratch copy carrying only the frozen spec block. The receipt is
`retained/r2-heron-1-targets.json`: model `183fabff…`, arm length 144.0 mm,
the tip starting at (64, 0, 120) mm, and every target at least 29.4 mm
above the bench (limit 14.4 mm) and at least 37.9 mm from where its
segment starts (limit 36 mm). Each of the four evaluations below held
these twenty targets to within 5.3 × 10⁻⁵ mm, which is the receipt's
rounding. No seed was void.

**Pre-registered first.** `retained/p4-heron-1-preregistration.json` was
committed (`02603727`) before the session started. It fixes the prompts,
the targets, four runs and four turns at most, 900 s at most per run, and
`--stop-on-collapse`. The driver is `runner/rounds.py`, unchanged; only
the prompt, `prompts/reach.loop.prompt.txt`, names the behaviour. The
prompt hands over the frozen reach spec in xscript, and the agent wrote
it into the script byte for byte (checked after each run). The prompt
fixes the mechanism for the session, because a changed mechanism would
move the targets. The model digest stayed `183fabff…` through all four
runs. Registration: `retained/p4-heron-1-registration.json`.

| run | seed | settings | budget | ended | evaluated policy | seeds passed | Q2 worst final error (≤ 0.05 arm lengths) |
|---|---|---|---|---|---|---|---|
| `reach-r1` | 7 | 700 it × 1024 envs | 880 s | budget, iteration 685 | `c5a01908…` | 0 of 10 | 0.43–1.28 |
| `reach-r2` | 11 | 800 it × 1024 envs | 890 s | budget, iteration 649 | `e1b0277d…` | 1 of 10 | 0.04–0.26 |
| `reach-r3` | 23 | 800 it × 1024 envs, entropy 0 | 890 s | budget, iteration 649 | `2036f471…` | 0 of 10 | 0.07–0.31 |
| `reach-r4` | 31 | 800 it × 1024 envs, entropy 0, joint rates privileged | 895 s | budget, iteration 474 | `3270ce26…` (checkpoint 475) | **9 of 10** | 0.008–0.055 |

GPU wall time: 880.5 + 890.5 + 890.5 + 895.5 = **3,557 s**. No run
finished its iterations, and none collapsed.

**Each revision cited the previous evaluation, and the next evaluation
shows whether it helped.** The quotes are the runs' registered reasons,
shortened.

- **r1.** A random-target task was designed with the goal redrawn every
  2 s. The policy reads the joint encoders and the goal; the tip's
  position and velocity and the forces are privileged. Result: Q2 and
  Q3 failed on 10 of 10 seeds and Q4 on 7. Some segments were reached,
  some moved away, and some never moved (seed 1101, segment B: closest
  119.8 mm, which was also its final error).
- **r2** cited "Q2 on 10/10 seeds (… median 0.82, min 0.43, limit
  0.05)". Its diagnosis was that an `exp(−d/40)` reward is flat at
  60–180 mm, so the arm held one pose. It added a linear distance cost.
  **It helped**: worst Q2 fell to 0.04–0.26, one seed passed, and Q4
  failed on one seed instead of seven.
- **r3** cited "Q2 on 9/10 seeds (… median 0.099, max 0.26 on 1106)".
  Its diagnosis was that a distance-gated speed cost paid the tip to
  stand off the target. It made the cost ungated and saturating.
  **It did not help**: 0 of 10 passed, and Q2 rose to 0.07–0.31.
- **r4** cited "Q2 on 10/10 seeds (… median 0.139, max 0.307 on 1106)"
  and "settle_cost sat at its 0.3/step ceiling". Its diagnosis was
  chatter: actuator force was about 3× the gravity hold. It made the
  speed cost linear, raised the force cost ×10 and moved the joint rates
  to privileged. **It helped**: 9 of 10 seeds passed.

This is P4's requirement of three or more motivated rounds, met on
reach. The owner ticks P4; this page does not.

**r4's evaluation.** `evaluations/6418a337500a-3270ce260233/` in the
project. Q1 passed on all ten seeds, and every episode ran 8.0 s. The
nine passing seeds have a worst final error of 1.2–5.0 mm, reach the
target in 0.08–0.24 s, and overshoot at most 0.13 (limit 0.20). **Seed
1106 fails Q2 and Q3.** Its segment B target sits low beside the
pedestal with the elbow folded back. The tip settles 7.92 mm from it,
against the 7.2 mm limit, and never gets closer. 1106 was the worst seed
in r2, r3 and r4. Film of seed 1106:
[overview](p4-heron-1-reach-r4-seed-1106-overview.png) and
[detail](p4-heron-1-reach-r4-seed-1106-detail.png).

**The turn.** One turn of 74.5 minutes, with 50 tool calls. It cost
$3.20 as the harness reported it. The longest blocking calls were
`train_status` at 892.8 s and `evaluate` at 111.3 s. Receipt:
`retained/p4-heron-1-rounds.json`. It holds the ledger, every run's
registration and ending, every evaluation's per-seed rows and segments,
and the target check. It does not include the transcript.

**What this session does not show.**

- **R2 is not met.** These are training rounds, and the last one fails a
  seed. R2 is judged on a later pre-registered confirmation evaluation.
- **Warm start is not reachable through the tools.** For r3 the agent
  tried to warm-start from r2. It guessed five paths for
  `init_from_parent_task`, and `train_start` refused each one. The file
  exists, as `runs/reach-r2/train/heron_reach_task-task.json`, but
  neither `train_status` (`loop.run_view`) nor the refusal names it. The
  agent trained r3 from scratch and said so in its reason. Its closing
  report names the same gap as the blocker for its next step.
- **The film may not show chatter.** The agent's diagnosis for r3 was
  50 Hz chatter, which the 0.2 s filmstrip frames cannot resolve. It
  read it from the force and speed reward terms instead.

### Reach round 5: a warm start, and 10 of 10 seeds

*The warm-start gap is fixed:* `train_status` now names each run's task
bundle (DECISIONS, the amendment "a run names its task bundle").
**Pre-registered first.** `retained/p4-heron-1-r5-preregistration.json`
was committed (`c758ffeb`) before the session. It fixes the prompt,
`prompts/reach.r5.loop.prompt.txt`, the same model, spec digest and held-out
targets, one run of at most 900 s, and two turns. The prompt names seed
1106's Q2 miss and says warm start now works. How the task changes is left
to the agent. `runner/rounds.py` was unchanged (`a6a2a5b1…`) and ran under
`setsid` from 20:36:18Z.

| run | seed | settings | budget | ended | evaluated policy | seeds passed | Q2 worst final error |
|---|---|---|---|---|---|---|---|
| `reach-r5` | 41 | 800 it × 1024 envs, entropy 0, warm start from `reach-r4` checkpoint 475 | 890 s | budget, iteration 422 | `6bb5a403…` (checkpoint 400) | **10 of 10** | 0.014–0.032 |

GPU wall time: 890.5 s, which brings the reach total to **4,447 s**. The run
did not collapse, and `--stop-on-collapse` was in its command. `train_start`
took the warm start at the first call, with no refusals. The earlier session
had seven.

**The revision cited the measurement.** The registered reason, shortened:
"reach-r4 ckpt 475 failed Q2 on seed 1106 (… 0.0550, limit 0.05; 7.92 mm
vs 7.2 mm) … the tip holding still about 8 mm above and short of a
reachable low target … the reward pulled only about 0.12/mm/step". The
change touched the reward only. The coarse reach length went from 20 to
10 mm and the fine reach weight from 2 to 3. The run was declared with
`init_from_task_change`, and observations, actions, goals and terminations
were unchanged. **It helped.**

| seed | r4 final error mm | r5 final error mm | r4 → r5 time to target s | r4 → r5 overshoot |
|---|---|---|---|---|
| 1101 | 1.36 | 4.54 | 0.24 → 0.22 | 0.008 → 0.053 |
| 1102 | 3.16 | 3.67 | 0.22 → 0.22 | 0.017 → 0.021 |
| 1103 | 2.21 | 4.52 | 0.20 → 0.20 | 0.015 → 0.053 |
| 1104 | 1.09 | 3.92 | 0.24 → 0.22 | 0.070 → 0.044 |
| 1105 | 4.55 | 1.99 | 0.12 → 0.12 | 0.116 → 0.153 |
| **1106** | **7.92** | **3.33** | never → 0.46 | 0.052 → 0.142 |
| 1107 | 3.32 | 4.03 | 0.08 → 0.08 | 0.131 → 0.140 |
| 1108 | 1.25 | 3.04 | 0.08 → 0.10 | 0.019 → 0.123 |
| 1109 | 4.98 | 4.23 | 0.12 → 0.12 | 0.010 → 0.054 |
| 1110 | 4.56 | 4.46 | 0.12 → 0.12 | 0.049 → 0.110 |

The limits are 7.2 mm (0.05 arm lengths), 2.0 s and 0.20. **Seed 1106
passes**, and none of r4's nine passing seeds failed. The cost is
precision on the easy seeds: the median error rose from 3.24 to 3.98 mm,
and the median overshoot from 0.034 to 0.082. The worst overshoot is
0.153, on seed 1105. Two cost terms more than doubled at unchanged weights:
`control_cost` went from −26.1 to −68.3 and `settle_cost` from −21.1 to
−55.3, both medians. The arm pushes harder to hold. (The agent's closing
report calls the second one the "tip-speed cost". The report's own
`tip_speed_cost` term reads 0 in both evaluations.)

**The checks held.** The evaluation's spec hashes to the registered
`61b25b02…`, and the model is `183fabff…`. The twenty drawn targets equal
the receipt to within 4.9 × 10⁻⁵ mm, and no seed was void. The declared
policy's digest is that of `runs/reach-r5/train/heron_reach_task.000400.cxpolicy`.
The film of seed 1106 is the
[overview](p4-heron-1-reach-r5-seed-1106-overview.png) and the
[detail](p4-heron-1-reach-r5-seed-1106-detail.png).

**The turn.** One turn of 22.4 minutes. The harness reported 17 turns and
$1.27. There were 16 tool calls, and none errored. `evaluate` was called
twice: once to re-read r4 on seed 1106 before the change, and once on r5.
The receipt is `retained/p4-heron-1-r5-rounds.json`. The ledger now holds
five runs and six evaluations; r4 appears twice.

**This is still a loop round and not R2.** Its pre-registration says R2 is
judged on a separately pre-registered confirmation evaluation, registered
only because this round passed on all ten seeds. The judge has not seen
reach yet.

## R3's confirmation evaluation: balance on `ot11-robin-1`

This is the evaluation R3 is judged on. It is not a loop round.

**Pre-registered first.** `retained/r3-confirm-1-registration.json` was
committed (`c2dd99bb`) before the evaluation ran. It fixes:

- the policy, `8919a22d…` (`bal-1`'s iteration-400 checkpoint, as the
  product agent declared it);
- the accepted revision, the task and the model digests;
- the spec's digest, which must be the spec `bal-1`'s round held;
- the ten frozen seeds, the conditions, B1–B5 and the pass rule;
- the judge's runner digest, the judged seeds, three calls a seed and the
  bar;
- the two commands, and that it is run once.

**The spec: pass, 10 of 10 seeds.** No seed was void, and no solver
warning was raised. Every episode ran the full 10.0 s and ended by
truncation. The spec hashed to the registered digest. Every seed's
metrics equal those of `bal-1`'s round evaluation exactly: the engine's
rollout is deterministic for a seed. Receipt:
`retained/r3-confirm-1-evaluation.json` (no paths).

| seed | B2 tilt (≤ 30°) | B3 drift, COM heights (≤ 2.0) | B4 heading (≤ 20°) | B5 worst recovery (≤ 2.0 s) | shoves, × weight |
|---|---|---|---|---|---|
| 1101 | 9.1° | 0.72 (38 mm) | 0.63° | 0.26 s | 0.21, 0.12 |
| 1102 | 8.3° | 0.83 (43 mm) | 0.97° | 0.42 s | 0.14, 0.19 |
| 1103 | 7.0° | 0.55 (29 mm) | 0.66° | 0.22 s | 0.16, 0.15 |
| 1104 | 8.6° | 0.66 (34 mm) | 0.74° | 0.27 s | 0.15, 0.15 |
| 1105 | 9.9° | 0.66 (35 mm) | 0.85° | 0.29 s | 0.20, 0.22 |
| 1106 | 8.3° | 0.67 (35 mm) | 0.91° | 0.40 s | 0.24, 0.18 |
| 1107 | 9.2° | 0.41 (21 mm) | 0.87° | 0.33 s | 0.24, 0.16 |
| 1108 | 11.2° | 0.92 (48 mm) | 0.95° | 0.34 s | 0.14, 0.24 |
| 1109 | 8.5° | 0.71 (37 mm) | 0.65° | 0.25 s | 0.11, 0.11 |
| 1110 | 11.5° | 0.58 (30 mm) | 0.84° | 0.36 s | 0.16, 0.19 |

**The judge: the bar is met on every judged seed.** Three calls a seed,
nine in all. Every call returned a score from `claude-opus-5-5`. None was
refused or retried. Receipts: `retained/judge-r3-confirm-1-seed-*.json`.

| seed | calls (V1 V2 V3 V4) | medians | total | bar (≥ 9, none under 2) |
|---|---|---|---|---|
| 1101 | 3333, 3333, 3333 | 3 3 3 3 | 12 | **met** |
| 1105 | 3332, 3323, 3333 | 3 3 3 3 | 12 | **met** |
| 1110 | 3333, 2332, 2333 | 2 3 3 3 | 11 | **met** |

**The spec and the judge agree.** Both say pass, so there is no
disagreement to diagnose. On 1110, two calls scored V1 (task) 2. They saw
the robot "moving left after the shove and later drifting a little to the
right of its start". The trace agrees: the base wandered 30 mm (0.58 COM
heights), inside B3's limit of 2.0. The predicate is authoritative for
drift (ADR-463), so this is a reading of the same fact, not a
contradiction. One call on 1105 said no shove was clearly visible in its
frames. It still scored control 3.

**R3's measured bar is reached** by this confirmation: every seed passes
B1–B5, and every judged seed meets the judge's bar. The owner ticks R3;
this page does not.

**What this confirmation does not show.** The sensors the policy reads
(an IMU on the board, an encoder on each wheel) are declared on the
mechanism, not modelled as parts (ADR-408). The gyro channel reads in the
world frame (`runner/obs_parity.py`). Both are sim-to-real questions for
the long-term rung, and neither changes this evaluation.

## R2's confirmation evaluation: reach on `ot11-heron-1`

This is the evaluation R2 is judged on. It is not a loop round.

**Pre-registered first.** `retained/r2-confirm-1-registration.json` was
committed (`e80fd938`) before the evaluation ran. It fixes:

- the policy, `6bb5a403…` (`reach-r5`'s iteration-400 checkpoint, which the
  product agent declared as `reach_r5.cxpolicy`), and the accepted revision
  `13f9c63c…`;
- the task, model and spec digests (`61b25b02…`, the spec the rounds held);
- the held-out target receipt `retained/r2-heron-1-targets.json`
  (`8bb702af…`), which was drawn before any training on this model;
- the ten frozen seeds 1101–1110, Q1–Q4 and the pass rule;
- the judge's runner digest, the judged seeds 1101, 1105 and 1110, three
  calls a seed and the bar;
- the two commands, and that it is run once.

**The spec: pass, 10 of 10 seeds.** No seed was void, and no solver
warning was raised. Every episode ran the full 8.0 s at 50 Hz and ended by
truncation. The spec hashed to the registered digest, and the policy, task
and model hashed to theirs. The twenty drawn targets equal the receipt to
within 4.9 × 10⁻⁵ mm. None of these targets was in a training configuration.
Every seed's metrics equal those of `reach-r5`'s round evaluation exactly.
Receipt: `retained/r2-confirm-1-evaluation.json` (no paths).

| seed | Q2 worst final error (≤ 0.05 arm lengths = 7.2 mm) | Q3 worst time to target (≤ 2.0 s) | Q4 worst overshoot (≤ 0.20) |
|---|---|---|---|
| 1101 | 0.032 (4.54 mm) | 0.22 s | 0.053 |
| 1102 | 0.026 (3.67 mm) | 0.22 s | 0.021 |
| 1103 | 0.031 (4.52 mm) | 0.20 s | 0.053 |
| 1104 | 0.027 (3.92 mm) | 0.22 s | 0.044 |
| 1105 | 0.014 (1.99 mm) | 0.12 s | 0.153 |
| 1106 | 0.023 (3.33 mm) | 0.46 s | 0.142 |
| 1107 | 0.028 (4.03 mm) | 0.08 s | 0.140 |
| 1108 | 0.021 (3.04 mm) | 0.10 s | 0.123 |
| 1109 | 0.029 (4.23 mm) | 0.12 s | 0.054 |
| 1110 | 0.031 (4.46 mm) | 0.12 s | 0.110 |

**The judge: the bar is met on every judged seed.** There were three calls
a seed, nine in all. Every call returned a score from `claude-opus-5-5`,
and none was refused or retried. Receipts:
`retained/judge-r2-confirm-1-seed-*.json`.

| seed | calls (V1 V2 V3 V4) | medians | total | bar (≥ 9, none under 2) |
|---|---|---|---|---|
| 1101 | 3333, 3333, 3333 | 3 3 3 3 | 12 | **met** |
| 1105 | 3333, 3223, 3333 | 3 3 3 3 | 12 | **met** |
| 1110 | 3333, 3333, 3333 | 3 3 3 3 | 12 | **met** |

**The spec and the judge agree.** Both say pass, so there is no
contradiction to diagnose. Two readings are worth recording:

- *Overshoot.* No call saw the tip swing past a marker. Seed 1105 carries
  the worst overshoot, 0.153, which is inside Q4's 0.20. One call said the
  gap between frames "could hide a brief overshoot". Q4 is authoritative
  for overshoot (ADR-463).
- *Twitching in the hold, a defect no predicate measures.* One call on
  1105 scored manner and control 2 because the tip "keeps drifting slightly
  in and out of the marker ring". The trace confirms this. Over target B's
  hold (4.6–8.0 s), the tip's frame-to-frame motion on 1105 has 3 steps
  over 1 mm, 11 mm of path in all, and its error ranges 0.53–2.78 mm.
  **Seed 1110 is worse, and all three calls scored it 3:** 16 of 170
  steps are over 1 mm, the largest is 4.8 mm in one 20 ms step, the path
  totals 78 mm, and the error ranges 0.37–3.06 mm. Six of the ten seeds
  twitch in at least one hold (over 30 mm of path in a hold). Seed 1102
  holds dead still in both. Q2 bounds the error, and every excursion stays
  inside its 7.2 mm, so the verdict stands. Still, no predicate reads hold
  steadiness, and twelve frames 0.2 s apart mostly miss it. Round 4 saw the
  same chatter (the agent read it from the force and speed terms). It is
  listed under the remaining defects for REPORT.md. Measuring it would
  change the frozen contract, which is a recorded decision that
  re-evaluates every earlier policy, and this page does not take that
  decision.

**R2's measured bar is reached** by this confirmation: every seed passes
Q1–Q4 on targets the policy never trained on, and every judged seed meets
the judge's bar. The owner ticks R2; this page does not.

## Walk, on `ot11-quad-1`: the loop session, pre-registered

`ot11-quad-1` is a copy (`cp -a`) of `ot10-quadruped-3-w2`, the copy of
ot10's accepted quadruped on which `w2-1` and `w2-2` were trained. The
original stays read-only. The copy is at accepted revision `84ff4c98…`,
model `d67ac96c…`, hip height 96.7006 mm.

**The spec the agent is handed is the whole walk contract.** Now that a
task can state a speed goal (P3), W3 and W4's lateral half are stated too,
so the block has all thirteen predicates. The commanded speed is a
`speed` goal drawn in [0.6, 1.0] hip heights per second (58.02–96.70 mm/s)
and held for the episode. The block is
[`retained/walk-spec-block.txt`](retained/walk-spec-block.txt). It was
built on a scratch copy before the session and accepted, and the bundle
carried the goal and all thirteen predicates. The reset lift is written as
the lift that clears a 3° tilt, not read from the task's `reset_tilt`
parameter, so the agent cannot move it by editing the task.

**Pre-registered first.** `retained/p4-quad-1-preregistration.json` fixes
the driver (`runner/rounds.py`, unchanged, `a6a2a5b1…`), the prompt
([`prompts/walk.loop.prompt.txt`](prompts/walk.loop.prompt.txt)), the
spec block digest, four runs and four turns at most, **2400 s at most per
run**, and `--stop-on-collapse`. The per-run budget is larger than reach's
900 s because ot10's two runs on this mechanism took 1,866 s and 1,945 s
for 1,000 iterations × 2,048 environments. Each run's settings, seed and
reason are registered by `train_start` before it launches. The mechanism
is fixed for the session, because the spec's constants are this model's.
The prompt tells the agent what `w2-2` measured under this spec, and that
its policy cannot be declared on a task with a goal. It does not tell the
agent how to reward a gait.

### Walk round 1: `r1-clearance` collapsed, and its best checkpoint walks backwards

The session started under `setsid` at 21:27Z and was still alive when this
round was read. The agent registered `r1-clearance` before launch: seed 7,
1,000 iterations × 2,048 envs, a 2,350 s budget, `--stop-on-collapse`.

| run | seed | settings | budget | ended | evaluated policy | seeds passed |
|---|---|---|---|---|---|---|
| `r1-clearance` | 7 | 1000 it × 2048 envs | 2,350 s | **collapsed** at iteration 568, 1,542 s | `8db0cb61…` (`best`, iteration 273) | **0 of 10** |

GPU wall time: 1,542 s. Episodes ran about 490 of 500 steps early in the
run, began shortening near iteration 250 and averaged 23 steps at the stop.
The reward per step was negative throughout, from −7.0 to −0.8: the alive
bonus of 2.0 did not cover the costs, so ending an episode paid.

**The evaluation is valid.** The script's spec block equals
`retained/walk-spec-block.txt`. Revision `8498db6e…` differs from the
registered `db1cfc96…` only in the declared policy digest. The model is
`ade106a6…`. The report is
`evaluations/8498db6e1ff5-8db0cb619fc4/evaluation.json`, and the receipt
with every seed's predicates, feet and reward terms is
[`retained/p4-quad-1-r1-evaluation.json`](retained/p4-quad-1-r1-evaluation.json).

| predicate | seeds failing | range |
|---|---|---|
| W3 tracks speed | 10 | speed ratio −1.46 to −0.05; every seed with a value moves **backwards** (1102 tips at step 38 with none) |
| W5-share steps | 10 | 0.00–0.19 of the path made in steps (≥ 0.70) |
| W6 clearance | 10 | 0.04–0.07 hip heights where measured (≥ 0.08) |
| W7 slip | 10 | 0.48–0.90 (≤ 0.15) |
| W10 in the floor | 10 | −0.11 to −0.19 hip heights (≥ −0.05) |
| W4-heading | 8 | up to 173° on seed 1103 |
| W9 every leg | 8 | ratio up to 9.5; on seed 1105 the rear feet take 2 and 3 steps and the front feet 19 and 13 |
| W4-lateral | 5 | up to 1.07 |
| W5-steps | 5 | 0–3 steps on the weakest foot |
| W1, W2 | 4 | seeds 1102, 1106, 1107, 1110 **tip** (38–315 steps, 37–39°) |
| W8 duty factor | 3 low, 2 high | seeds 1102 and 1110, which tip early, and 1105's low of 0.26 |

On the six seeds that complete the episode, the body's largest heading is 56–173°
and backs away at 27–85 mm/s against a commanded 61–93 mm/s. The front
feet do most of the stepping. Tilt is 17–21°, under W2's 30° but well
off level. On seed 1101 the four foot-clearance terms together cost 1,364
and the speed error 954, against an alive total of 1,000. The film of seed
1101 is the [overview](p4-quad-1-walk-r1-seed-1101-overview.png) and the
[detail](p4-quad-1-walk-r1-seed-1101-detail.png). The body swings
side-on to the camera and back, and the legs splay under a level trunk.

**This fails for the right reasons.** It is not a shuffle that the spec
misses. W3 catches the direction, W7 and W10 the drag through the floor,
and W5-share and W9 the rear legs that barely step.

**Round 2 cites round 1.** The agent registered `r2-bounded` at 22:11Z:
seed 11, 800 it × 2048 envs, 2,380 s, `--stop-on-collapse`. Its reason
quotes this evaluation's W3, W7, W10 and W6 ranges and the collapse. The
change touches the reward only, and the spec block is still equal to the
retained one. Every cost now goes through `tanh`, so each is bounded. The
alive bonus rises to 3, and the speed Gaussian widens from 0.25 to 0.4 of
the command. The sink threshold goes from 1.5 to 2.0 mm, and the sink
cost becomes quadratic at weight −2. The heading weight falls from −2.0 to
−1.5, and the yaw-rate weight rises from −0.3 to −0.5.

### Walk round 2: `r2-bounded` no longer collapses, and still walks backwards

| run | seed | settings | budget | ended | evaluated policy | seeds passed |
|---|---|---|---|---|---|---|
| `r2-bounded` | 11 | 800 it × 2048 envs | 2,380 s | **finished**, all 800 iterations, 2,251 s | `1a0f0d28…` (final, iteration 799) | **0 of 10** |

GPU wall time: 2,251 s. **The bounded costs fixed the collapse.** Episodes
ran full length at the end (the trainer's mean was 506 steps), and training reward per step
climbed from −1.5 to +2.48. **They did not fix the backwards motion.** In
the engine the final policy backs away on every seed, at 114–144 mm/s against
a commanded 61–93 mm/s (W3 −2.06 to −1.22). It is already backing away at
119–132 mm/s over the first three seconds, before any seed's shove (3.4–4.6 s), so the
disturbance is not the cause.

**The evaluation is valid.** The script's spec block equals
`retained/walk-spec-block.txt` at the evaluated revision `80ba9fb9…`. It
still does at round 3's revision `27da0754…`. The model is `ade106a6…`, and
the task is `ffbe1d43…`, the one trained. The report is
`evaluations/80ba9fb9905e-1a0f0d28a2aa/evaluation.json`, and the receipt is
[`retained/p4-quad-1-r2-evaluation.json`](retained/p4-quad-1-r2-evaluation.json).

| predicate | seeds failing | range |
|---|---|---|
| W1, W2 | **0** | every seed completes 500 steps; tilt 15.8–30.0° (seed 1107 at 29.998°) |
| W3 tracks speed | 10 | speed ratio −2.06 to −1.22, **backwards** |
| W5-steps, W5-share | 10 | the rear feet take **0 steps** on nine seeds and 2 on 1107; share ≤ 0.02 |
| W6, W9 | 10 | not measured on nine seeds (no rear step to measure); 1107 has W6 0.08 and W9 10.5 |
| W7 slip | 10 | 0.56–0.63, all on the rear feet (front feet 0.05–0.21) |
| W8-low duty factor | 10 | 0.16–0.26: the front feet are in the air most of the time |
| W10 in the floor | 10 | −0.13 to −0.11 hip heights |
| W4-heading | 5 | 47–82° on 1102, 1106, 1107, 1108, 1110 |
| W4-lateral | 1 | 0.29 on 1109 |

The gait is the same on every seed. The front feet step 8–29 times, with duty factors of
0.16–0.47. The rear feet drag on the ground (duty 0.75–0.83, slip 0.51–0.63), about 10 mm
into the floor. Round 1's legs were more even. This round turned that into a
front-pulled, rear-dragged slide. The film of seed 1101 is the
[overview](p4-quad-1-walk-r2-seed-1101-overview.png) and the
[detail](p4-quad-1-walk-r2-seed-1101-detail.png). The robot slides steadily
across the mat, with the shins splayed back and the feet low under a
near-level trunk.

The reward terms say where the bounded costs sit. `speed_error` costs
0.92–0.99 per step of its 1.0 cap, so backing away at twice the command
costs almost what standing still would (tanh 0.76). `clearance_rl`/`_rr`
cost 0.42–0.43 of 0.5, and `sink` costs 0.82–0.90 of 2.0. `speed_track`
earns 0.00–0.02 of 2.0.

**Training and evaluation disagree, in both rounds.** The evaluated
policy's training reward was +2.48 per step. On the evaluation seeds it
scored −1.69 to −1.21. Round 1 shows the same gap: −1.39 at its best
checkpoint in training, −7.51 to −4.34 on evaluation. Both rounds move
backwards in the engine, although the reward pays forward speed. The part of
the ~4 per step gap that sampled vs mean actions or the reset draws would
explain is not measured. Nor is whether the trainer's rollout of this policy
also goes backwards. The observation-parity probe (R3) compares sensor
values at forced states, not a policy rollout. This page does not claim a
cause. The next measurement is that rollout: the trainer's own
environment, driving the evaluated policy with mean actions, from an
evaluation seed's reset and command, compared step by step with the
engine's trace. Until it is run, a walk round's evaluation is published but
the train/evaluate agreement for walk is an open question.

**Round 3 cites round 2.** The agent registered `r3-nochatter` at 23:01Z:
seed 23, 800 it × 2048 envs, 2,380 s, `--stop-on-collapse`. Its reason
quotes W3 −1.22 to −2.06 at 114–144 mm/s, W7 0.56–0.63, W5-steps 0–2 and
W10 −0.11 to −0.13. It also reads the knee joint-speed term as about
360°/s RMS of knee chatter (−0.10 per step at weight −0.03 over four knees
is 364°/s), and names the training/evaluation gap itself. It charges
bounded hip and knee chatter and landing speed, and strengthens the
per-foot clearance, slip and trot-sync terms. The spec block is still
equal to the retained one.
