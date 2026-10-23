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
to 2.7 m/s), or one task per gait. The slower stride was found, and the
bundle C3 trains is the three-stride one: see "A slower gallop" below.

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

## A slower gallop: gallop27, and the bundle C3 trains

`stride_scan.py` lists every left-hind-to-left-hind stride over 1.8 m/s in
the dog's takes, with each foot's first touchdown phase. It is a finder:
`retarget.py` then measures the stride it takes. Among the takes, the
slowest gallops keeping the gallops' order (LH, LF, RF, RH) are:

| take, frames | dog m/s | LF / RF / RH phase | flight |
|---|---|---|---|
| `D1_010_KAN01_001`, 404–432 | 2.69 | 0.32 / 0.54 / 0.86 | 0.39 |
| `D1_010_KAN01_003`, 33–60 | 2.76 | 0.30 / 0.44 / 0.81 | 0.33 |

Nothing slower gallops in this order. `D1_010_KAN01_004` runs from 2.6 to
5.2 m/s, but its strides under 3.1 m/s show no fore touchdown at all.
`D1_047z_KAN01_002` gallops at 2.28–3.20 m/s in the other order (LH, RH,
RF, LF), which crosses the gallops'. So **2.76 m/s on leo is the dog's
floor** for one schedule. It is 4% above sgt-4-120's fast end (2.66 m/s at
2400 commanded), and nothing in this capture gallops at 2.4.

Both were retargeted on the shared 26-sample grid (`~/mocap/retargeted/`):

| stride | leo m/s, period, Fr | footfall LH LF RF RH | flight | fore miss max LF/RF (share > 5 mm) | raw slip max | seam max / step | violations, loops |
|---|---|---|---|---|---|---|---|
| gallop27 (001, 404–432) | 2.76, 0.478 s, 2.00 | 0.00 0.19 0.42 0.85 | 0.15 | 14 (0.12) / 38 (0.19) | 37 (RH) | 19° / 30° (`j_knee_l`) | 0, 0.000 mm |
| gallop28 (003, 33–60) | 2.80, 0.457 s, 2.06 | **0.96** 0.15 0.38 0.81 | 0.15 | 9 (0.08) / 50 (0.23) | 74 (RH) | 20° / 25° (`j_elbow_l`) | 0, 0.000 mm |

Hind misses are 0 in both. The spine takes −10…+9° of `j_spine`, unclipped.
gallop28's left hind lands at 0.96, just before the window's start, so its
order crosses gallop34's (`c3_bundle.py` refuses: "LF before LH, then
after"). gallop27 keeps the order, misses less on the right fore, and slips
half as much. **gallop27 is taken.**

`~/cadex-projects/leo/runs/c3-bundle27/mocap_gallop-task.json` (sha256
`cc8f312330ff79192a284d13b9e30bf32974bd3d4ea56633cd93905f6816900c`; model XML
`59bc5407…`, unchanged) is the same build as the two-stride bundle above,
with three strides:

- **Strides:** gallop27 (2756 mm/s, 0.478 s), gallop34 (3395), gallop42
  (4233); 78 reset rows.
- **Goal:** `cmd` 2756–4233 mm/s; nominal 2850 (B1's, now inside the span).
- **Reward:** unchanged from the two-stride bundle (13 rows, no style term).
- **The engine reads it:** at cmd 2756 / 3000 / 3395 / 3800 / 4233 the blend
  is stride 0 at 0.00 / 0.38, then stride 1 at 0.00 / 0.48 / 1.00. The
  seeded start (seed 0) is row 12 / 12 / 38 / 38 / 64, the nearest stride's
  own rows. `judged_reference` is gallop27 / gallop27 / gallop34 / gallop34 /
  gallop42.
- **The trainer has not yet run it.** On the CPU (8 envs, GPU hidden,
  b1-s2 holding the 5090), `training/cadex_train.py` hashed the bundle
  (`task_sha256` `cc8f3123…`, model `59bc5407…`) and was still compiling
  when its 1100 s limit stopped it, before iteration 0. The two-stride
  bundle's check reached iteration 0 inside 580 s. So this is not a load
  check: the first ten iterations timed on the 5090 (D7) are.

The clips' sha256: `gallop27.clip.json` `a88ad380…` (`D1_010_KAN01_001.bvh`
`61239cf0…`) and `gallop28.clip.json` `88d7d0c8…`. Reproduce with:

```
pixi run python docs/probes/orun18/stride_scan.py $X/D1_010_KAN01_00{1,2,3,4}.bvh $X/D1_047z_KAN01_002.bvh
pixi run python docs/probes/orun18/retarget.py $M $X/D1_010_KAN01_001.bvh 404 432 gallop27 ~/mocap/retargeted 26
pixi run python docs/probes/orun18/c3_bundle.py ~/cadex-projects/leo/runs/b1-s2/train/speed-task.json \
  ~/cadex-projects/leo/runs/c3-bundle27 mocap_gallop ~/mocap/retargeted/gallop{27,34,42}.clip.json
```

## The paw pins sit at their stop through the clip

`j_pawpin_l` / `j_pawpin_r` are at a stop on 0.69 / 0.61 of gallop27's
samples, 0.73 / 0.73 of gallop34's and 0.65 / 0.65 of gallop42's
(`joints_at_stop_share` in each `<label>.measure.json`). The pin's home, 0°,
is its upper stop (range −60…0°), so the clip asks for the pin at rest on
most of the stride, and `track_pose` pays for that. It is the spring's
resting pose, not a drive at its clamp, but a policy that tracks the clip is
paid to keep the paw pin shut: C3's judgement should read the pin's range
against B1's before crediting or blaming the paw.

## The film

`retarget_film.py` draws `retarget_sheet.py`'s picture moving: each of the
three strides three times at real time, then once at 1/4 speed, the window
following leo and the floor's ticks fixed so a held paw reads as still.
`~/mocap/films/c3-strides.webm` (9.4 s, 566 frames at 60 fps, every frame
decoded; sha256 `aae4b31ce7a8f4c67e4df1a3e8f8dc086d59bc9f2ff36ed5dc704763b106418e`)
is a drawing of CC BY-NC material, so it stays out of the repository (D5)
and goes on the run's page (F1's "the retargeted clip"):

```
pixi run python docs/probes/orun18/retarget_film.py $M ~/mocap/films/c3-strides.webm 26 3 4 \
  $X/D1_010_KAN01_001.bvh:404:432:gallop27 $X/D1_010_KAN01_003.bvh:86:112:gallop34 \
  $X/D1_010_KAN01_002.bvh:66:92:gallop42
```

## Not done here

C3 trains `c3-bundle27`. Its training waits for b1-s2's judgement at 180 (D1; the critic's order).
Its iteration time on the 5090 is still to be timed (D7).
