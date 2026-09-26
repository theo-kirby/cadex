---
node_id: 3c5d9606-023c-5fc3-b064-b6f5aa80e502
slug: fond-light-6196
title: 'ADR-409: judge a walk on whether the robot walked'
created_at: '2026-09-26T14:03:15+00:00'
parents:
- nimble-meadow-6874
- polished-path-3774
summary: ''
---
## What
ADR-409, commit dc3210b4. `cadex walk`'s review gains a `gait` block, the library gains `servo.joint_dynamics`, and the overlay gains "A WALKING TASK PAYS FOR WALKING, NOT FOR DISTANCE".

## Why
hex2's task paid for forward CoM speed with only a height termination. The policy tumbled, and the walk reported the run as a verified total reward of 3,492. The data that showed the failure (body pose in the trace, `episode_steps_curve` in progress.json) was already written and never read (polished-path-3774).

## Method
- `walk.gait_from_trace`: the base is the MJCF body with a free joint; if there are several, it is the one the task observes the orientation of. Tilt is the angle of the starting up axis; heading is the unwrapped forward axis projected on XY. Findings: tipped ≥45°, turned ≥90°, a rollout termination, final mean training episode <90% of max_steps (capped at the horizon, because an iteration in which no episode ended reports the whole unroll).
- The block is wired into review.json, the walk's notes, report.py, and run.json's rollout.gait plus the dashboard row.
- `servo.joint_dynamics(joint, voltage=None)`: damping = stall N·mm / (60 / s_per_60) °/s, at a voltage rated for both torque and speed.

## Result
- On hex2's real artifacts, the gait block reports: tipped at t=0.88 s (max 127.5°), heading −521° (extent −647°), training episodes 217/500, walked=false.
- MuJoCo check: MG90S damping 0.294 N·mm·s/deg; a flat-out joint settles at 600°/s ±2%. hex2's hand-picked damping was 1.0.
- Tests: engine 2207 passed; CLI 957 passed, 1 skipped.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: hex/task-quality
- commit: dc3210b4fcbfb3e752f13ce88d0e290a77e70cbc

## State Impact

- target: shady-rose-6292 — close the 'task pays for tumbling' and 'reward-up/survival-flat unsurfaced' gaps: gait review block, servo.joint_dynamics, walking-task overlay; speed stays reported-not-judged and no rollout video yet
