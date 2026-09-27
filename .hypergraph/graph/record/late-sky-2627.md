---
node_id: 74f6a27d-671f-5bcc-ae73-d947d0899d09
slug: late-sky-2627
title: 'hex3: designed a complete grounded hexapod in 41 min, trained a policy that ends its own episodes'
created_at: '2026-09-27T14:28:03+00:00'
parents:
- fond-light-6196
summary: ''
---
## What
hex3: the third unassisted hexapod walk, on `main` @ 908af995 (ADR-406 to 409), with hex2's prompt and flags and `CADEX_EFFORT=medium`. Gap log: `docs/probes/hex/hex3-GAPS.md`.

## Why
To measure whether ADR-406 to 409 moved one prompt closer to a walking robot, against hex2 (polished-path-3774).

## Method
Observe only. `cadex walk --iterations 2000 --envs 2048`, launched 2026-09-26 09:50, with the dashboard on :8768. After it ended, the ADR-409 gait check was run by hand on the artifacts, and the model's triangles were measured with the render caps lifted.

## Result
- **Design, 41 min to the first accepted design (hex2: 76).** It included the ESP32, PCA9685, BNO085, D36V50F6 and 2S LiPo, plus `servo.joint_dynamics` on 12 joints, joint encoders and the IMU as the only policy inputs, and the CoM channels privileged. The same refusals as hex2 appeared (horn style, the assembly-shape rules); the fit-driven refinements were done with `edit_script` (4 revisions in 18 min).
- **`look` was refused on all 6 calls:** 589,268 triangles against the 400k cap, so the design was never seen and is still a flat deck of plates.
- **Training:** the task paid about −9 per surviving step, because `-abs(comv_x/55-1)` is −1 at rest and the yaw and lateral costs were charged per deg/s and per mm/s. The mean episode went 28 → 3 of 200 by iteration 77 and 2.0 by iteration 2000, over 7.2 h wall.
- **Rollout:** the body slumps 20.5 mm and trips the CoM termination at step 1 (tilt ≤9.3°).
- **Gait check (by hand):** walked=false; findings: terminated at step 1, training episodes 2 of 200.
- **The walk died in review** on the same render refusal, so `review.json` was never written.

The design phase improved, but the task-writing guidance in ADR-409 caused a new failure mode, early-termination hacking.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: hex/after-hex3
- commit: 54b1219f8b33defe2b6d72cf3a722b4f70413267

## State Impact

- target: shady-rose-6292 — hex3 measured: design phase 41 min with electronics and grounded sensors; new failure mode early-termination hacking from net-negative per-step reward; look and review refused at 589k triangles; 7.2 h trained after collapse
