# hex3 — gaps observed

Third unassisted attempt, on `main` @ `908af995`: ADR-406 (`look`, design
language), ADR-407 (electronics), ADR-408 (grounded sensors) and ADR-409
(gait review, servo dynamics, walking-task overlay). The prompt, flags and
`CADEX_EFFORT=medium` were identical to hex2's. Launched 2026-09-26 09:50.
Observe only.

## Log
- **09:52–10:08: the same API refusals as hex2.** A wrong horn style name,
  then `edit_script` with no script yet. After that the agent wrote two
  small probe scripts to read the MG90S, board and battery specs. hex2
  never looked up the electronics; this was ADR-407 working.
- **10:08–10:33: assembly-shape rules learned by failing, again.** "exactly
  one assembly and one solver_diagnostics output", then "every joint
  exactly once", each needing a full resend. After that came one MJCF
  stability refusal (fixed with `solver_step_s=0.001`) and one
  reset-variation refusal (fixed by raising the drop band).
- **10:33: first full design accepted**, 41 min in against hex2's 76. It
  has the deck, brackets, 12 × MG90S, the ESP32, PCA9685, BNO085,
  D36V50F6 and the 2S LiPo.
- **10:33–10:51: fit-driven refinement by `edit_script`.** Servo flange
  seat +1.2 mm, horn height, then the last 0.13 mm³ pinch. Four accepted
  revisions in 18 min, with no full resends.
- **`look` failed on every call** (6 attempts): "render: triangle budget
  exceeded". The filleted brackets put the model at 589,268 triangles
  against ADR-406's 400,000 cap, so the agent never saw its design, and
  the design-language rules had nothing to act on. The model is still a
  flat deck of plates with bare boards; see
  [`shots/hex3-look_iso.png`](shots/hex3-look_iso.png), drawn after the
  ADR-410 fix, all parts in the printed colour.
- **10:53: training started.** The task was what ADR-409's overlay asked
  for:
  - rewards: upright, closeness to a 55 mm/s target, a yaw-rate cost and a
    lateral cost;
  - terminations: upright below 0.7 and a CoM-height collapse;
  - `servo.joint_dynamics` on all 12 joints;
  - policy inputs: joint encoders and the IMU only.
- **11:05: episodes collapsing.** The mean episode fell from 28 to 3 of
  200 steps by iteration 77 while reward/step rose from −8.9 to −0.8.
  Every surviving step paid about −9: `-abs(comv_x/55 - 1)` is −1 at rest,
  and the yaw and lateral costs were charged per deg/s and per mm/s. So
  tripping a termination was the optimum, and the overlay's own example
  (`-abs(comv_x / 60 - 1)`) invited it.
- **Training ran on for 7.2 h** to iteration 2000 at 2.0 steps per
  episode. Nothing stopped it.
- **Rollout: the policy slumps.** The body drops 20.5 mm in one step, trips
  the CoM-height termination at step 1, and never tips (max 9.3°). The
  ADR-409 gait check, run on the artifacts, says "terminated at step 1;
  training episodes ended early: 2 of 200". walked = false, correctly.
- **The walk failed in review anyway**, on the same render refusal, so
  `review.json` and its gait verdict were never written. This is hex2's
  failure mode again.

## Fixed by ADR-410
- `render` and `look` cluster vertices instead of refusing: 589,268
  triangles become 106,326, and the four views take 3.6 s. The pixel
  budget scales with image area.
- A render refusal in the walk's review is recorded, and the rest of the
  review stands.
- The overlay requires an alive bonus and costs sized so that standing
  still nets positive, and its forward example is now a cost with a
  negative weight.
- The trainer detects a collapse (50 iterations under 5% of the horizon
  and half the early length) and warns. `--stop-on-collapse` stops it, and
  `cadex walk` always passes it.
