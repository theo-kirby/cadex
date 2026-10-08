---
node_id: 0387d990-5105-5389-aaf2-b9f9cfabbdc1
slug: tidy-badger-2182
title: 'P1 circle-10: ADR-598 phase goal kind built; a phase-led reward passes 6/8 seeds, 2 lost to the start kick'
created_at: '2026-10-08T04:04:19+00:00'
parents:
- damp-orchard-1989
summary: ''
---
## What

Built the `phase` goal kind (ADR-598, REPORT defect 12). It is a clock:
`assembly.goal(name, kind="phase", period_seconds=T)`. The start phase is
drawn over one turn per segment, by the value draw that is already stated
(`low` 0, `high` 2π). The angle then turns `radians_per_step` = 2π·dt/T
every control step and reads as `name_sin` and `name_cos`. It is carried
through:

- `_GOAL_KINDS` in the API, plus its `period_seconds` argument and its
  refusals;
- the worker's `_goal_input`;
- `GOAL_KINDS`, `_goal_records`, `goal_schedule` and `goal_values`, plus
  `GOAL_PHASE_ALGORITHM`, which is appended only where a phase is stated so
  no earlier digest moves;
- the trainer's `goals_at`, through a new `phase_channels`. The draw code
  (`draw_goals`, `draw_episode_goals`) is unchanged by construction;
- the reference runner's `goals_at`;
- `describe_api` notes, `docs/XSCRIPT.md`, `docs/MUJOCO.md` and ADR-598.

Then trained P1 circle-10 on `orun5-ball-plate`. It is a new task,
`task_circle_phase`, whose reward follows the clock's point on the 40 mm
circle. It ran on the GPU and was evaluated on frozen seeds 9101–9108.

Commit `3ffabb2b`.

## Why

The critic named this unit: the phase goal from defect 12, with the
channel set, ADR-598, a pin test, a unit test that the channels advance,
the docs, both suites with the GPU hidden, then circle-10 on the GPU and
evaluated on the frozen seeds. It is the open half of P1, the run's
headline criterion.

**One deviation.** The critic asked for circle-10 to start **warm from
circle-9**. That cannot be done. A phase goal adds two policy inputs, and
ADR-161 refuses a warm start whose observation channels change (`goal` is
not a curriculum key). A recurrent or memoryless policy also cannot track a
clock it is not shown. So circle-10 trained **cold**: 1500 iterations
instead of 1000, to cover the cold start.

## Method

**Engine, API and trainer.** A phase reuses the value draw (`low` 0,
`high` 2π), so both copies of the draw and their stream lengths are
untouched. `goal_values` computes `start + radians_per_step·(step −
segment start)`. The trainer's `goals_at` turns the pooled start by the
same rule on device. A task may state more than one phase.

**Tests:**
- `test_dynamics_goal_model.py`:
  - the bundle row and the appended algorithm;
  - the channels a policy sees and a reward names follow sin/cos of the
    clock, come round after 40 steps and restart at the 1.0 s resample,
    and an unseeded episode starts at 0;
  - a malformed period and a clashing `elbow_sin` channel are refused;
  - the stock-MuJoCo reference runner reproduces a phase episode as text,
    parametrized beside the old case;
  - the `GOAL_KINDS` pin.
- `test_dynamics_goal_trainer.py`:
  - `goal_segment` + `phase_channels` (numpy) equal `goal_values` at every
    step and 40 past the horizon, through a resample;
  - the `goals_at` source pin;
  - a venv-gated real-trainer reward-curve test for a `lead_sin` reward.
    The venv has no pytest, so it was **run by hand**: bundle and expected
    curve from pixi, the trainer in `~/cadex-train-venv`, compared in pixi.
    Max difference **8.7e-8**, and the observations ended `lead_sin`,
    `lead_cos`.
- `test_dynamics_goal_api.py`: arguments and refusals, and the kinds named
  in `describe_api`.

**`describe_api` budget.** The assembly page came to 21,612 characters
against `API_VIEW_CHAR_BUDGET` 21,500. I trimmed wording in the notes
(disturbance azimuth, collision-only export, "RL task", termination,
sustained push) without dropping a fact, which brought it back under.

**circle-10:**
- `goals=[lead]` with a period of 3.5 s (2.86 turns per 10 s episode).
- Reward:
  - alive +1.0;
  - `exp(-gap²/800)` to the clock's point, +1.5;
  - bearing-lag cosine, +0.3;
  - off radius `tanh(|r−40|/25)`, −0.8;
  - tilt.
- Terminations, randomisation, kick and `circle_success` are as before.
- Accepted with `cadex script --set`, registered and launched with
  `cadex_cli.loop`: 1500 it × 256 envs, seed 16, a checkpoint every 250,
  from a shell with `CUDA_VISIBLE_DEVICES` unset. Device `gpu`.
- Stored as `circle-10.best.cxpolicy` (bf6dab62…) and `circle-10.cxpolicy`
  (6b815c46…), declared as `policy_circle_phase` and
  `policy_circle_phase_final`, then `cadex evaluate --film none` on each.

## Result

**The phase goal kind exists and is pinned across the engine, the trainer
and the reference runner.**

Gates:
- `pixi run test-engine`: **2681 passed, 61 skipped**.
- `pytest cli/tests` with the GPU hidden: **1225 passed, 1 skipped**, run
  after `build-engine`.
- Not run: the staged payload gate. `OP_ARG_SPECS` and the protocol are
  unchanged.

circle-10 trained on the GPU: exit 0 in 695.6 s. Reward per step 0.72 at
iteration 0, best 2.42 at iteration 640, final 1.78.

Evaluation on frozen seeds 9101–9108:

| policy | evaluation | seeds passing | on the seeds that completed |
|---|---|---|---|
| best | `35c62c0b23ab-bf6dab62633e` | **5/8** | 2–3 laps (turns +2.27 to +3.28), mean radius 34.2–35.6 mm |
| final | `35c62c0b23ab-6b815c4671e7` | **6/8** | 2–3 laps (turns +2.34 to +3.32), mean radius 33.4–35.3 mm |

- **Every seed that runs to the horizon passes every predicate.** No
  earlier circle policy passed a single seed. circle-9 was at 20.6–24.0 mm.
- **Every failure is the same:** "ball reached the rim" at 0.30–0.36 s,
  from the start kick (up to 0.6 N for 40 ms). Seeds 9101 and 9102 fail
  for both policies, and 9103 for the best.
- circle-9 survived the same kicks on 8/8. So the phase-led policy reaches
  for the circle along with the kick instead of first catching the ball.

**The circle task is still not trained to a spec pass**, which needs all 8
seeds. The radius and circulation gaps are closed. The open gap is the
first 0.3 s.

Suggested next attempts, smallest first:
- **(a)** warm circle-10 into the same task with a revised reward: an
  early-episode `exp(-r²/…)` catch term, or a lower near-point weight while
  `r` is over 50. That is a reward-only curriculum step (ADR-597), so warm
  start is allowed.
- **(b)** train longer from circle-10's final policy.

Do not loosen the kick or the spec.

State of the scratch project:
- the accepted script adds `task_circle_phase`, `policy_circle_phase`
  (best) and `policy_circle_phase_final`;
- circle-9's declarations are unchanged;
- the policies are in `assets/`;
- no policy, trace or checkpoint is committed.

Other notes:
- The `describe_api` assembly page sits close to its budget again (under
  21,500 after the trim). The next note added there will need trimming.
- No new dependency.
- The tail is one record (this one).

Dispatch closed: 1 unit — ADR-598 `phase` goal kind built and pinned (engine, trainer, reference runner; trainer curve agrees to 8.7e-8); circle-10 led by it passes 6/8 frozen seeds at 33–36 mm and 2–3 laps, failing 2 to the start kick, so the circle task is still not a spec pass

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 3ffabb2b481dcdbcc47cdb58ef42530e5460091a

## State Impact

- target: salty-isle-4063 — ADR-598 (commit 3ffabb2b): goal kind 'phase' (period_seconds) is a clock read as name_sin/name_cos from the step counter; carried through _GOAL_KINDS, GOAL_KINDS/goal_values/goal_schedule, GOAL_PHASE_ALGORITHM (appended only where stated), the trainer's goals_at via phase_channels, and the reference runner; real trainer reward curve agrees with the engine to 8.7e-8
- target: peaceful-orchard-2220 — circle-10 (task_circle_phase, cold, GPU 696 s, reward follows the phase goal's point on the 40 mm circle): best 5/8, final 6/8 frozen seeds pass every predicate at 33-36 mm and 2-3 laps; remaining failures are the start kick throwing the ball to the rim within 0.36 s; still not a spec pass
- target: grand-otter-5246 — REPORT section 6 circle-10 paragraph and table, status row, defect 11 updated, defect 12 marked resolved by ADR-598, done-claim tail; LESSONS W5 updated
