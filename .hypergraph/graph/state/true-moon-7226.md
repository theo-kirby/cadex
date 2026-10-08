---
node_id: 56353585-a006-5202-b993-eb6e613c3bb9
slug: true-moon-7226
title: P2. The excavator's precision floor, measured
created_at: '2026-10-07T17:58:13+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun5: **P2. The excavator's precision floor, measured.** The human owns the checkbox; roles report results and do not tick it [rec: honest-bay-2056].

Asked for: on a scratch copy, the policy reads each servo's S2 load channel and holds its goal in the track frame (R1); one reach run starts cold with the reference reward; the record reports whether the ~20 mm floor moved on the same frozen seeds — either outcome is a result. Optional, once L1 landed: the bucket driven through a four-bar [rec: honest-bay-2056].

**Measured, and the floor moved [rec: hidden-sand-7542] [rec: misty-water-8806].** On `~/cadex-projects/orun5-excavator` (a copy of the read-only `excavator-mini`, edited only through `write_script`), each STS3215 grounds a `load_sensor` read by the actor as `<joint>_load`, the goal is held in the track frame, and the reward, episode, spec and seeds are reach-05's (task `ea19ce4a…`). The cold run `reach-p2-cold` (1400 iterations, the reference chain's total; exit 0) was evaluated on frozen seeds 101–110 as `evaluations/0c0b7e5b05e5-5dc8fc5abd8a`: its best checkpoint (`5dc8fc5a…`) reaches a **median final error of 11.5 mm, 7/10 pass (≤ 15 mm)**, against reach-05's 23.6 mm, 2/10 [rec: misty-water-8806].

9 of 10 seeds improved (only 107 worse, 20.8 → 22.4 mm); 102, 103 and 107 still miss, so the spec still fails. Max tilt 0.06°, max drift 8.6 mm [rec: misty-water-8806].

- **Servo sag is ruled out as the floor by direct probe**: at reach-05's own final commands held still, load ≤ 0.19 of stall (boom), boom sag 0.54–0.94°, tip shift median 1.5 mm, max 4.3 mm [rec: hidden-sand-7542].
- **The reference floor was already in the policy's command**: rigid kinematics at reach-05's final command misses the track-frame goal by a median 19.7 mm (7.9–37.4); base drift in the reference is ≤ 7.5 mm, below its 11–39 mm errors [rec: hidden-sand-7542].
- **The move is not attributed.** The run changed the goal frame, the load channels and the schedule (uninterrupted 1400 iterations vs a 600+400+400 warm chain) at once; sag being ruled out leaves goal frame and schedule as the likely causes. The new error is measured against the track-frame goal, the reference's against a world-fixed one. The separating run (same schedule, world-fixed goal) was not done [rec: misty-water-8806].
- The optional bucket four-bar was not built [rec: pale-brook-6092].

Status `working`, not `done`: the measurement the criterion asks for is delivered, but the checkbox is the human's, and the attribution is open (judgement of this reconcile) [rec: misty-water-8806].

## Negative knowledge

- [scope: excavator-mini reach-05 on seeds 101–110 | confidence: high | evidence: hidden-sand-7542] Servo sag is not the ~20 mm precision floor: held at the policy's final commands, the tip moves ≤ 4.3 mm and load is ≤ 0.19 of stall. The policy already reads every joint's encoder, so a load channel adds force, not new pose information.

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-p2-excavator-s-precision-floor)
- hidden-sand-7542 — P2 measured: sag ruled out by probe, floor in the command, reach-p2-cold run on the copy with S2 + R1
- misty-water-8806 — P2 finished: reach-p2-cold 11.5 mm, 7/10 vs reach-05 23.6 mm, 2/10; cause not separated
- pale-brook-6092 — the optional bucket four-bar was not built (ledger W12)
