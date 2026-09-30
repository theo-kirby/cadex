---
node_id: 82ce8a3e-58de-59da-9619-8c87a7f19678
slug: long-badger-5117
title: 'ot11 P3 rollout parity: trainer (MJX) and engine diverged through saturated servos; fixed in the trainer (ADR-465), walk rounds 1-3 flagged'
created_at: '2026-09-30T23:52:50+00:00'
parents:
- copper-sun-7929
summary: ''
---
## What

Ran the rollout-parity measurement the critic named, found that the trainer and the engine diverge, and fixed the drift in the trainer with a regression that fails first (ADR-465).

The evaluated r2 walk policy `1a0f0d28…` was driven with mean actions in the trainer's physics and in the engine's. The trainer's physics is MJX, with `cadex_train.py`'s step, observation and reward code. The engine's is `CadexDynamics.evaluate_episode` on stock MuJoCo. Both started from the same seeded reset, command and shoves, on CPU. The two disagree from the first 2 ms substep, before any contact. The cause is MJX 3.10's `deriv_smooth_vel`. Under `implicitfast` it always folds an affine actuator's `-kv` into the implicit step, and stock MuJoCo 3.10 leaves that term out for an actuator clamped at its `forcerange`. Every Cadex servo is exactly that actuator, and a 9 g one saturates most of the time. `cadex_train.match_engine_actuator_derivative` now applies the engine's rule inside MJX, and `train()` installs it before it builds a model. The measurement receipt is `docs/probes/ot11/retained/p3-quad-1-mjx-parity.json`, and the section is in `docs/probes/ot11/README.md`.

## Why

The critic asked for this unit because the evaluation outranks training, and it serves P3: "the trainer and the engine's rollout agree … and a test fails if they drift apart". The critic's rule was: if the two diverge, it is a P3 drift defect, so fix it with a test that fails first and flag every walk round on the drifted path. That is what was done. No GPU job was started; everything ran on CPU while `r3-nochatter` held the GPU. The agent's session (pid 735257) and its training job were not touched.

One deviation in scope. Evaluation seed 1101's episode, as the committed trace ran it, uses the success spec's own shove band (one shove, 3–7 s). This harness drew seed 1101 under the *training* task instead (two shoves, 2–5 s and 5.5–9 s, command 78.1 mm/s). Both sides of every comparison share the episode, so the parity verdict does not depend on which band. It does mean the engine totals here (−1.95/step on 1101) are not the committed evaluation's (−1.53/step).

## Method

- A throwaway harness in `/tmp/parity`, outside the repo, ran from `~/cadex-train-venv` with `JAX_PLATFORMS=cpu`. The engine side ran `CadexDynamics.evaluate_episode(seed=N)` with `policy_forward`, took the post-variation `qpos`/`qvel` at step 0, and redrew the shoves and command with the engine's own functions. The trainer side ran MJX float32. Rewards came from `cadex_train.globals_for` and `compile_expression`, and the step mirrors `step_env`: clamp, ctrl, 10 substeps, observe, goal appended. It ran in two modes: open-loop replay of the engine's actions, and closed-loop on MJX's own observations. The policy code was the same on both sides.
- Localisation, per substep, from the same state and the same ctrl:
  - float32 and float64 gave identical divergence.
  - Four model variants in memory: as built, Euler, no `forcelimited`, and kv = 0.
  - Read MJX's `derivative.py`.
  - Prototyped the clamped-actuator rule and checked it over the full 500-step episode.
- Test-first:
  - Wrote `cadex_tests/test_dynamics_mjx_forcelimit.py`: a contact-free, two-servo fixture with the kp, kv and stall torque from ot11-quad-1's model, run in float64.
  - On the old trainer, 3 of its 4 tests failed and the raw-disagreement test passed.
  - Implemented the rule, then cleared JAX's jit cache in the test: an `mjx.step` traced by an earlier test keeps its derivative. That cannot happen in `train()`, which installs the rule before any trace.
- Four seeds (1101–1104), before and after the fix.

## Result

- **The two diverged, and now agree.** Engine vs the trainer's rollout per seed, as reward per step and tray travel over 10 s:

  | seed | engine | trainer before | trainer after |
  |---|---|---|---|
  | 1101 | −1.95, −1271 mm | +2.80, +728 | −1.25, −1173 |
  | 1102 | −1.58, −1049 | +2.70, +882 | −1.82, −1379 |
  | 1103 | −1.75, −833 | +2.73, +921 | −1.18, −1185 |
  | 1104 | −1.57, −1101 | +2.82, +709 | −1.87, −57 |

  The train/evaluation gap flagged in `copper-sun-7929` is explained. The training reward (+2.48 sampled) was earned in MJX's physics, where this policy really does walk forwards.
- **Localisation:**
  - First-substep `qvel` divergence was 6.9 rad/s with no contact, the same in float64.
  - After 5 control steps the tray was at −229 mm/s in C and +172 mm/s in MJX.
  - Euler, no force limit, and kv = 0 each brought the two to 2e-6.
  - With the rule, the open-loop replay agrees to 1e-6 for 10 control steps, then drifts only as float32 contact does: −1251 vs −1298 mm after 10 s, where raw MJX gave −226.
- **Regression:** `test_dynamics_mjx_forcelimit` measured raw MJX at 10.2 rad/s and the trainer with the rule at 6.2e-15. An unlimited servo gave 1e-14 either way. Its source-level test (the rule is installed before `mjx.put_model`) runs under pixi too.
- **Flagged (critic's rule):**
  - Walk rounds 1 and 2, and `r3-nochatter`, trained on physics the engine does not run. `r3-nochatter` started at 19:01Z on the old trainer file and is still training.
  - Their evaluations stand, because `cadex evaluate` runs the engine and was never on the drifted path. They are not evidence about their reward designs.
  - Every earlier ot11 run trained the same way. R2's and R3's confirmation passes stand as the engine measured them.
  - The next round the agent registers uses the fixed trainer automatically, and a policy's `trainer_sha256` tells the runs apart.
- **Gates:**
  - Trainer-facing suites from the training venv (`JAX_PLATFORMS=cpu`, through a scratch `/tmp` venv layered over `~/cadex-train-venv` with pytest added, as `vast-moss-6116` did): 145 passed. The files: forcelimit, policy_trainer, mjx_agreement, goal_trainer, action_filter, command_slew, mjx_geom_pairs, purity_guardrails, units.
  - `pixi run test-engine`: 2506 passed, 60 skipped, 2 failed. The failures:
    - `test_every_deferred_import_is_one_the_requirements_install`: a race, since the run started before `mujoco.mjx._src` joined the allowed list. It passes on rerun.
    - `test_every_source_file_declares_the_right_license`, on `cli/tests/test_ot11_rounds.py`, which was committed in `0ffc6569` with no SPDX header. This predates this unit. The header was added, and the licensing file passes on rerun.
  - `pixi run python -m pytest cli/tests`: 1256 passed, 1 skipped.
  - `test_dynamics_policy_live` and `test_dynamics_policy_measured` from the venv: 27 passed. The live one trains a tiny task on CPU with the rule installed.
  - The final full `pixi run test-engine`: **2508 passed, 60 skipped, 0 failed**.
  - No engine, protocol, payload or shell file changed, so no packaged gate was run.
- **New dependency:** none in the repo. pytest went into a scratch venv under `/tmp` only.
- The unfolded tail is now three records, which reaches the reconcile threshold. Reconcile is forbidden in a work iteration, so it was not run.

Dispatch closed: 1 unit — rollout parity measured: the trainer (MJX) and the engine diverged through saturated servos (+2.8 vs −1.9 per step on the r2 policy), fixed in the trainer with a failing-first test (ADR-465), and walk rounds 1–3 flagged as trained on the drifted physics

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 7635ac8d5e4e8f10d148ff658e2f260bb65634d3

## State Impact

- target: late-pond-2851 — the trainer now integrates a force-limited servo as stock MuJoCo does (ADR-465, commit b81dd2e1): MJX 3.10 kept a clamped actuator's -kv in the implicitfast step, so every run before it trained a different machine; on r2's walk policy MJX gave +2.70..+2.82/step forwards vs the engine's -1.57..-1.95 backwards (seeds 1101-1104), and after the fix MJX gives -1.18..-1.87; test_dynamics_mjx_forcelimit pins raw divergence (10.2 rad/s) and the match (6.2e-15)
- target: smooth-fountain-9832 — the walk train/evaluation gap is explained: rounds 1, 2 and r3-nochatter trained on MJX physics that disagreed with the engine through saturated servos (ADR-465); their engine evaluations stand but are not evidence about their reward designs; the next round trains on the fixed trainer (receipt retained/p3-quad-1-mjx-parity.json)
- target: salty-isle-4063 — MJX and stock MuJoCo now agree for Cadex's force-limited PD servos under implicitfast only because the trainer installs match_engine_actuator_derivative; test_dynamics_mjx_agreement never saturated and missed it
