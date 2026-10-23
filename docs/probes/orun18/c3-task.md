# orun18 C3: leo's task on the dog's strides (the bundle, before training)

Verified against source: 2026-10-23. CPU work while b1-s2 trains (D1). Probe:
`c3_bundle.py`. No engine change: the bundle is B1's speed-only task with the
parts the engine writes for a speed-scheduled reference (ADR-703, ADR-706,
ADR-709, ADR-773), each built by the engine's own function
(`_tracking_records`, `_schedule_record`, `_reference_start_records`,
`compile_reward`) over `retarget.py`'s clips.

## Which strides: only the two gallops can be one schedule

A speed schedule blends two strides row for row at one phase. The engine
refuses a family whose footfall order crosses between neighbours
(`schedule_footfall_order`, in `_reference_schedule_records`), because a
blend of two strides is only a gait when the same foot lands in both.
`clip_carry.py` (C2) ran `_schedule_record` alone, which has no such check,
so C2's "the four clips pass the engine's readers over 1099–4233 mm/s" holds
for the tables, not for the order. `c3_bundle.py` applies the check and
refuses the four:

```
refused (schedule_footfall_order): pace11 -> trot23: LF before RF, then after;
pace11 -> trot23: LH before RF, then after; trot23 -> gallop34: RF before LF,
then after; trot23 -> gallop34: RF before LH, then after
```

Pace (lateral), trot (diagonal) and rotary gallop are three gaits, not one
gait at three speeds. The two gallops keep one order (LH 0.04/0.00, LF 0.19,
RF 0.38, RH 0.88) and are taken: **`cmd` is 3395–4233 mm/s**, not the
1099–4233 the critic named. Covering leo's slow end needs another route:
a slower gallop or canter stride from the dog (`D1_010_KAN01_003` runs down
to 2.7 m/s), or one task per gait.

## The bundle

`~/cadex-projects/leo/runs/c3-bundle/mocap_gallop-task.json` (sha256
`50759ea87797dd751b7bdc72874793861b304666c9c82fcdbdbb8d2b6b222414`), from
b1-s2's `speed-task.json` (`b51f1ff6…`) and the model XML it names
(`59bc5407…`, leo v05, unchanged). It holds the clips, so it is CC BY-NC
derived and stays out of the repository.

- **Strides:** gallop34 (3395 mm/s) and gallop42 (4233 mm/s), 26 samples
  each, periods 0.435 s, 0.046 turns per step.
- **Tracking:** 32 channels (clock, 22 joint refs, 4 lifts, 4 downs); table
  26 × 30; random start (ADR-709), 52 reset rows (both strides' samples).
- **Goal:** `cmd`, in the task and in its success spec, narrowed to
  3395–4233 mm/s; nominal 3395 (B1's 2850 clamped).
- **Reward (D6):** B1's ten rows unchanged (`alive`, `track_speed`,
  `near_peak`, `height_over_ground`, `posture`, `straight`, `tail`,
  `torque`, `energy`, `action_rate`) plus sgt-4's three tracking terms, the
  same text and weights: `track_pose` 1.5, `track_lift` 1.5,
  `track_contact` 10. No style term. Every row compiles against the bundle's
  channels and the tracking channels.

## Checked

- The engine reads it: at cmd 3395 / 3800 / 4233 the seeded start falls on
  stride 0 / 0 / 1 (rows 25, 25, 51), the blend weight is 0.00 / 0.48 / 1.00,
  and `judged_reference` at 4000 is gallop42. A reset at row 30 puts the
  trunk at the clip's height with a forward velocity of 3.90 m/s.
- The trainer reads it: `training/cadex_train.py` on the CPU (8 envs, GPU
  hidden, b1-s2 holding the 5090) compiled the task and ran iteration 0,
  reward 24.8 per step, episodes of 16 steps (a random policy starting at a
  gallop falls at once). It was stopped at the 580 s limit before
  iteration 1. That is a load check, not a screen.

## Not done here

C3's training waits for b1-s2's judgement at 180 (D1; the critic's order).
Its iteration time on the 5090 is still to be timed (D7).
