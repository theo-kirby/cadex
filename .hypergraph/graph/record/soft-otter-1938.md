---
node_id: 30e4b513-2cc3-59ac-968a-50bfd47c6aa3
slug: soft-otter-1938
title: 'ot11 R3 trust: trainer (MJX) and rollout (MuJoCo) observe Robin''s policy channels identically; the loop ledger links an evaluated checkpoint to its run'
created_at: '2026-09-30T18:16:17+00:00'
parents:
- southern-quartz-3293
summary: ''
---
## What

The two evaluation-trust items the critic named for R3, both on
`ot11-robin-1`'s policy `8919a22d…` (run `bal-1`).

- **Measured what the trainer and the rollout observe.** New
  `docs/probes/ot11/runner/obs_parity.py`, run from the training venv
  (mujoco 3.10.0, jax on GPU). It drives the run's own model
  (`runs/bal-1/train/robin_model-model.xml`, the bundle's digest) in MuJoCo
  from a random push with random in-range commands. At each of 200 sampled
  states it hands the same state to `mjx.forward` and compares every task
  channel, scaled into its declared unit. Receipt:
  `docs/probes/ot11/retained/r3-robin-1-obs-parity.json` (no paths).
- **Fixed the ledger defect.** `cli/cadex_cli/loop.py` gains
  `run_checkpoints` (the checkpoint files on disk, each with its own
  digest; the progress's iteration and reward are kept only where the
  digests match) and `runs_that_trained` (final policy ∪ every digest the
  progress ever named ∪ every file on disk). `bridge.py`'s `evaluate` uses
  it for `trained_by_run`, and `run_view` (what `train_status` shows) lists
  checkpoints through it.
- **Regression test**:
  `cli/tests/test_loop.py::test_a_checkpoint_the_progress_never_listed_is_still_the_runs`.
  It failed on the old code (run with `loop.py` and `bridge.py` stashed:
  1 failed) and passes on the new code.
- **Docs**: an ADR-464 follow-up in `docs/DECISIONS.md`, the Limits
  paragraph in `docs/CLI.md`, and two notes in `docs/probes/ot11/README.md`.

## Why

This is the critic's named next unit, evaluation trust first. It serves
`staid-tooth-3475` (R3), since the policy's inputs must be trusted before a
confirmation, and `wild-harvest-4848` (P4), since the ledger is what the
loop's rounds are read back from.

**What the critic asked that I did not do this iteration.** The blind judge
on the policy's judged seeds, and R3's confirmation pre-registration. The
critic ordered them "after that", so they are the next units, not this one.

## Method

1. Read the task bundle and the compiled MJCF. The policy reads `rot` and
   `gyro` (`framequat` and `frameangvel` on `comp_board`) and the wheel
   `jointpos`/`jointvel`. Chassis pose, COM and torques are
   `role: privileged` and read by neither the actor in the trainer
   (`actor_channels`) nor the engine's policy (`policy_channels`; the
   engine refuses a policy whose header's channel list differs).
2. Confirmed both evaluators compute an observation the same way:
   `sensordata[adr:adr+dim] * scale`, read after the physics steps of a
   control step (`cadex_train.py` `observe` after `mjx.step`;
   `CadexDynamics.py` `observation_values` after `mj_step`). The only
   remaining difference is the library, so I measured it.
3. For the ledger: found that the evaluated checkpoint is **not** in
   `progress.json` at all. The progress stops at iteration 398 and lists
   `000350` last, but `balance_task.000400.cxpolicy` (sha `8919a22d…`) is on
   disk. So matching the progress's digests alone, which the last record
   proposed, would not have fixed it. The files on disk had to be the
   authority. I also found that `train_status` showed the stale `best`
   digests that the progress listed for a file since rewritten.
4. Checked the fix read-only on the real project:
   `runs_that_trained(ot11-robin-1, 8919a22d…)` returns `['bal-1']`, and
   the view lists `000400` at iteration 399 with its real digest.

## Result

**True now.**
- **The trainer and the rollout observe the same numbers.** Over 200
  states, the worst MJX-vs-MuJoCo difference per policy channel is:
  - `rot`: 1.3e-7 (quat)
  - `gyro`: 0.0003 deg/s, on readings up to 826 deg/s
  - wheel positions: 1.7e-6 deg
  - wheel velocities: 1.4e-5 deg/s

  The privileged channels are the same order. This is float32 rounding;
  there is no disagreement, so there is nothing to fix and no fix test.
- **The sensors are declared, not modelled, and that stays.** The IMU is a
  sensor declaration on the Pi board component, which is rigidly fixed to
  the chassis. The encoders are declarations on the wheel joints. ADR-408
  grounds a channel by declaration. Only the product agent may change a
  mechanism. **Assumption, recorded:** R3's "accepted design" does not
  require the IMU or encoder parts to be modelled.
- **Sim-to-real fact (long-term rung, not an evaluation defect).**
  `component_angular_velocity` compiles to `frameangvel`, which reads in
  the **world** frame. At 108.6° tilt the error against the world frame is
  0; against the board frame it is 0.10 rad/s. A real gyro reads in its
  own frame. Both evaluators read the same thing, so no evaluation
  changes.
- **The ledger links an evaluated checkpoint to its run.** This includes a
  checkpoint written after the trainer's last progress rewrite. The
  historical `bal-1` row in `ot11-robin-1/loop-ledger.jsonl` still says
  `trained_by_run: []`. It is append-only and was not rewritten. The same
  code now names `bal-1` for that digest.
- **Suites.** `pixi run python -m pytest cli/tests`: 1252 passed, 1 skipped (1251 before; +1 regression test). The doc-reading subset was re-run after the doc edits: 550 passed, 1 skipped. No
  engine, protocol, payload or trainer file changed, so `test-engine` and
  the packaged gate were not due and were not run.
- No new dependency. The probe runs from the existing training venv. Only
  standard-library imports were added to `loop.py` (`glob`).

**Next, in the critic's order:**
1. The frozen blind judge (`runner/judge.py`) on `8919a22d`'s judged seeds
   (1101, 1105, 1110).
2. Pre-register R3's confirmation evaluation.
3. Then reach as P4's three-round proving ground.

Dispatch closed: 1 unit — measured that the trainer (MJX) and the rollout (MuJoCo) observe Robin's policy channels identically to float32 rounding (the gyro reads world frame), and fixed the loop ledger so an evaluated checkpoint missing from progress.json is linked to its run, with a regression test that fails on the old code.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 4b4b03e8ff828841213c288d65b03be2df396e89

## State Impact

- target: staid-tooth-3475 — Evaluation trust for policy 8919a22d settled (commit 4b4b03e8): over 200 states MJX and MuJoCo sensordata agree to float32 rounding on every policy channel (worst gyro 0.0003 deg/s of 826), so trainer and rollout observe the same inputs; the IMU and encoders stay declared rather than modelled (ADR-408; assumption: R3 does not require those parts modelled); the gyro channel reads world frame, a sim-to-real fact for the long-term rung. Next: frozen blind judge on seeds 1101/1105/1110, then pre-register R3's confirmation.
- target: wild-harvest-4848 — Ledger defect fixed (commit 4b4b03e8): trained_by_run now names a run for its final policy, any digest its progress named, or any checkpoint file on disk; bal-1's evaluated 000400 checkpoint had been written after the last progress.json rewrite. train_status lists checkpoints from the files with their own digests. Regression test fails on the old code; cli/tests 1252 passed, 1 skipped.
