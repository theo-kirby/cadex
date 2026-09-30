---
node_id: 6831d169-0bf9-551b-b4ae-5a5a896b3c4f
slug: lively-ledge-7354
title: 'ot11 R1 started: ot11-quad-1 copied, full walk spec with speed goal pre-registered, walk round 1 r1-clearance registered and training'
created_at: '2026-09-30T21:36:06+00:00'
parents:
- tender-quartz-6082
summary: ''
---
## What

R1 is started. ot10's accepted quadruped is copied into `ot11-quad-1` (`cp -a` of `ot10-quadruped-3-w2`, accepted revision `84ff4c98…`). The frozen walk spec is written as a thirteen-predicate xscript block with a commanded-speed goal, `retained/walk-spec-block.txt` (sha256 `487416af…`). A walk loop session was pre-registered and committed before any GPU time (`626141c8`): `retained/p4-quad-1-preregistration.json` and `prompts/walk.loop.prompt.txt` (`13386046…`). The session was then launched under `setsid`, and it outlives this iteration.

The product agent then authored the task and pre-registered **walk round 1** through `train_start`, and it is training:
- run `r1-clearance`: seed 7, 1000 it × 2048 envs, checkpoints every 100, budget 2350 s, `--stop-on-collapse`, registered at 21:35:25Z.

## Why

**I did not do the reconcile the critic asked for first.** This iteration's dispatch forbids the hypergraph-reconcile skill, `hypergraph update` and edits under `.hypergraph/graph/state/` or to STATE.md in a work iteration, "no exceptions". I took that as the harder rule and did the critic's second instruction instead: start R1, have the product agent author a walk task that samples a commanded velocity (P3) and trains against the frozen walk spec, and pre-register round 1 before GPU time. With this record there are **three unreconciled records** (cold-summit-2811, tender-quartz-6082 and this one), which is the pressure line. **The next iteration should be the housekeeping reconcile**: fold these three, move R2 (sunny-garden-4245) to "measured bar reached, owner tick pending", and advance the high-water mark. The walk session will still be running then, and a reconcile does not touch it.

R1 is the hardest open criterion. The question policy ranks the behaviours after the loop and the evaluation, and both of those are working. R2 and R3 each have a passing confirmation.

## Method

- **The spec block.** It is the P1 contract's walk section, stated in the metric vocabulary:
  - the goal: `assembly.goal("command", kind="speed", between=[0.6·HIP_MM, 1.0·HIP_MM])`, held, with HIP_MM = 96.7006 from the P1 receipt;
  - W3 as `speed_ratio` in [0.75, 1.25], and W4 as `lateral_ratio` ≤ 0.25 plus `max_heading_deg` ≤ 45;
  - W1, W2 and W5–W10 as on `ot11-w2-negative`;
  - the contract's conditions: 10.0 s; tilt 0–3° with lift [SPEC_LIFT, SPEC_LIFT + 5] mm; one shove of 0.05–0.20 × weight for 0.15 s, starting between 3 s and 7 s; `randomisation=[]`.
  - SPEC_LIFT is computed from a fixed 3°, not from the task's editable `reset_tilt`. The feet are named through `result["c_foot_*"]`, because the accepted script has no `foot_c` dict.
- **Checked before the session.** The block was built on a scratch copy (in /tmp, now discarded) with `cadex script --set`, with the ot10 policy declaration off. It was accepted, and the exported bundle carried `goal` (speed, 58.02036–96.7006 mm/s, `resample_steps` 0) and all thirteen predicates.
  - A first attempt at this check was invalid. `cadex params` rewrites `script.py` from the accepted revision, so my edit was lost and the spec never reached the build. I found that out and redid the check.
- **The prompt.** It has the same shape as reach's:
  - the frozen block, verbatim;
  - the mechanism fixed for the session, because HIP_MM, WEIGHT_N and SPEC_LIFT are this model's;
  - what `w2-2` measured under this spec (0 of 10 seeds; W5, W7, W9 and W10 fail on every seed), and that its policy cannot be declared on a task with a goal;
  - a budget of at most 2400 s per run. ot10's runs on this mechanism took 1,866 s and 1,945 s for 1000 × 2048.
  - It says nothing about how to reward a gait.
- **The driver.** `runner/rounds.py` is unchanged (`a6a2a5b1…`): 4 runs and 4 turns at most, on claude-opus-5-5 with no fallback. The output goes to `~/cadex-projects/ot11-notes/quad-1/` (registration at 21:27:25Z), and the log to `quad-1.log`.
- **Checked after round 1 registered.**
  - The spec block appears verbatim in the accepted script (revision `db1cfc96…`).
  - `r1-clearance`'s MJCF differs from `w2-2`'s only in its sensor block: the agent added `subtreecom` and `subtreelinvel` for the four feet. Bodies, joints and actuators are unchanged.
  - The registration has `has_success_spec: true`, task sha `9aa69b30…` and model `ade106a6…`.
- **The agent's round-1 design, in its own registered reason:**
  - the task reads the commanded speed;
  - it charges foot-height error × foot speed, so a foot travels only while lifted about 14 mm;
  - it charges feet sinking into the floor, and diagonal feet out of sync.
  - It first hit the engine's limit of 16 reward terms (it wrote 19) and an "expression is too complex" refusal, and it restructured to 15 terms on its own.
- **Tests.** `pytest cli/tests -k "ot11 or film or evaluate or loop"`: 217 passed. `test_ot11_contract.py`: 15 passed. No product code changed.

## Result

**What is true now:**
- `ot11-quad-1` exists at the accepted design, and its task states the full frozen walk spec with a commanded-speed goal.
- The walk loop session is pre-registered and running.
- Walk round 1 (`r1-clearance`) is registered with settings, seed, budget and stop rule, and is training on the GPU.
- Nothing has been evaluated yet, so R1 has no measured result.

**For the next iterations:**
- **Do not start another GPU job** while `rounds.py --project ot11-quad-1` is alive (`pgrep -f "rounds.py --project ot11-quad-1"`). The session can run up to 4 × 2400 s plus evaluations, about 3 hours.
- **Reconcile is due now**, at three unreconciled records.
- When the session ends, read `ot11-notes/quad-1/rounds.json` (`rounds.py --summarise` works mid-session).
- After each evaluation, compare the script's spec block with `retained/walk-spec-block.txt`. A difference voids that evaluation.
- Then publish every run and evaluation in the README, as for reach.
- **Assumption:** fixing the mechanism for this session is reversible. A later session may open it with the constants recomputed, recorded as its own decision.
- No new dependency.

Dispatch closed: 1 unit — R1 started: ot10's quadruped copied to ot11-quad-1, the full 13-predicate walk spec with a speed goal pre-registered with a walk loop session (626141c8), and the agent's round 1 r1-clearance registered and training; reconcile deferred to the next iteration because this dispatch forbids it

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 626141c817869feb7fc8a84642e8ac5bfab18645

## State Impact

- target: smooth-fountain-9832 — R1 started on ot11-quad-1 (cp -a of ot10-quadruped-3-w2 at 84ff4c98): the frozen walk spec as a 13-predicate xscript block with a speed goal in [0.6,1.0] hip heights/s (retained/walk-spec-block.txt, 487416af) and a 4-run walk loop session pre-registered (626141c8, <=2400 s per run, stop-on-collapse); the agent's round 1 r1-clearance (seed 7, 1000x2048, 2350 s) is registered and training; no walk evaluation yet
