---
node_id: 90535efa-954b-511e-afd6-02b6d86f1b7a
slug: nimble-meadow-6874
title: 'ADR-408: policies read only sensor-grounded channels; asymmetric actor-critic; training refuses ungrounded inputs'
created_at: '2026-09-26T13:28:05+00:00'
parents:
- polished-path-3774
summary: ''
---
## What
ADR-408: a trained policy reads only what an onboard sensor measures. Commit `c11ed048`.

## Why
hex2's policy read joint angles and rates its stock MG90S servos cannot report and a
centre-of-mass position and velocity nothing on the robot measures
(polished-path-3774). The owner chose: refuse rather than warn; allow a declared
potentiometer tap as a joint encoder; enforce at training, not at build, so no
existing project stops building.

## Method
- `api.sensor(target, kind, name=)`: `imu` on a component (grounds its
  `component_orientation`, `component_angular_velocity`), `joint_encoder` on a joint
  (its `position`, `velocity`). Registered as an assembly intermediate, never published.
- `api.observation(..., role="policy"|"privileged", sensor=)`; the API refuses a
  sensor passed to a kind it does not measure or a target it is not mounted on. The
  worker and `CadexDynamics.observation_records` carry `role`, `grounded_sensor`,
  `grounded_kind` into task rows **only when not the default**, so legacy tasks export
  byte-identical and their policies keep verifying.
- `CadexDynamics.policy_channels` (non-privileged, in order) is what policy headers
  are verified against; `ungrounded_policy_channels` names the rest.
- Trainer: asymmetric actor-critic. Actor input is `jnp.take(normalised, actor_idx)`;
  critic and normaliser see all channels; header `observations`, network input width,
  normaliser and witness are the actor's slice; `--init-from` scatters the stored
  normaliser back into the full one.
- `cadex train`/`walk` refuse ungrounded policy channels (listing them and both
  remedies) unless `--allow-ungrounded`, which adds an envelope note. Overlay "GROUND
  WHAT THE POLICY READS". Both `examples/lifecycle` scripts and the CLI training
  fixture now declare an encoder and mark CoM/effort privileged.

## Result
- A real CPU training run on the fixture produced a policy whose header reads
  `["angle"]` only (network input 1, normaliser length 1) out of five task channels,
  stored and verified by the engine.
- A legacy fixture builds, is refused by `cadex train` naming `angle`, `com_x`,
  `effort`, and trains with `--allow-ungrounded`.
- Engine suite 2205 passed / 54 skipped; CLI suite 952 passed / 1 skipped. After the
  merge (`dbb082d0`): `pixi run build-engine`, `stage-engine`, and the packaged gate
  `test_cadexd_lifecycle.py` against the staged payload, 23 passed.
- Not built: IMU linear acceleration (`accelerometer` still deferred, needs a site),
  and the policy reading its own last command.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: dbb082d04496b8a8944973d67295ddc5802091f7

## State Impact

- target: salty-isle-4063 — Observations carry a role (policy/privileged) and policy channels name an api.sensor (imu on a component, joint_encoder on a joint) that measures them (ADR-408, commit c11ed048). Policies are verified against CadexDynamics.policy_channels; tasks written before ADR-408 export byte-identical so their policies still verify. Packaged gate after the merge: 23 passed.
- target: late-pond-2851 — The trainer is an asymmetric actor-critic (actor reads policy channels, critic and normaliser read all); cadex train and cadex walk refuse ungrounded policy inputs unless --allow-ungrounded (ADR-408). A real CPU run produced a policy reading 1 grounded channel of 5 and the engine verified it.
