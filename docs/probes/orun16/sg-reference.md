# orun16 SG: the speed schedule's strides, judged offline before a build; v05-s1x launched

Verified against source: 2026-10-22. Frozen evidence (orun16, iteration 3).
Short-term step 3, first half: the strides of leo's ADR-773 schedule,
generated with the engine's own generator on the v05 bundle's MJCF and
judged before anything is built or trained. Follows `sg-schedule.md` (what
a schedule can carry). Nothing in the project changed; the task is not
built yet.

## The GPU first: v05-s1x (single-speed P1 screen)

- v05-s1 continued on its own task and revision (`15d9feb4`), warm from
  v05-s1-50 (`41693803`), `--critic-warmup 5`, `--learning-rate 3e-5`,
  4,096 envs, seed 1, 50 iterations, `budget_s` 5,000 (76 s/it measured
  on v05-s1, + 20%, + compile), through `orun13/queue_run.py
  --expect-revision 15d9feb4` in its own `systemd-run --user --scope -p
  MemoryMax=30G`. **Launched 08:11:08** (`~/orun16-queue/v05-s1x.log`);
  the trainer logs `init-from gallop.cxpolicy sha256=41693803…`,
  iteration 0 at 08:16, reward per step 33.86 (v05-s1's 32.58 at 49).
- **Warranted** because v05-s1's curve was still climbing at 49 (+3.0 over
  its last 5 iterations) and its RH heel (0.35) and LH touch-down U
  (0.25) are the two numbers between it and P1.
- **The question:** does RH's heel stance share reach 0.4, and does LH's
  touch-down U (paw down toes-up of the floor, `paw_floor.py` split as in
  `v05-s1.md`) fall under 0.2?
- **Rules, written before judging** (at +25 and +50, `orun11/judge.py`,
  `paw_floor.py`, `pin_rate.py`, `p2_lag.py`, `legs.py`):
  - stop at +25 if either hind's U ≥ 0.3, speed < 2.2 m/s, or a pin's
    p95 ≥ 900 °/s;
  - keep at +50 if both hinds' U < 0.2 and `hock_down` passes on ≥ 8/10
    (each leg ≥ 0.4) at ≥ 2.3 m/s, pins < 900 p95: P1's foot. Otherwise
    the single-speed line stops here and the GPU goes to SG.

## The probe: `sg_clip.py`

```
R=~/cadex-projects/leo/runs/v05-s1/train
pixi run python docs/probes/orun16/sg_clip.py $R/gallop-task.json $R/cat_model-model.xml \
    docs/probes/orun16/sg-strides.json /tmp/sg/out
for k in 0 1 2 3; do python3 docs/probes/orun15/clip_read.py /tmp/sg/out/stride-$k.json; done
```

It regenerates the bundle's own clip first and checks it equal (qpos
exactly: **True**), then generates each stride with the bundle's settings
(`flat_feet="sole"`, `trail_feet`, heels, swing 40 mm, spine 7°) and the
stride's own speed, length, lags and `heel_from`; then, as the worker's
`_reference_schedule_records` does, regenerates every stride on the
largest sample count any takes (the slowest's), and checks the footfall
order never crosses from one stride to the next. Per hind leg over the
clip's stance it reads the heel's held share and the median height of
heel, pad and toe bulbs above the floor (the paw's lowest point at home,
which the generator takes as the ground). `clip_read.py` on each written
stride agrees on period, lags and heel samples.

## The schedule (`sg-strides.json`), on one grid of 25 samples

| stride | m at Hz = m/s | hind / fore lag (ms) | `heel_from` | heel held LH / RH | heel mm in stance, median LH / RH | pad, toe mm | pin toes-up ° LH / RH | IK miss mm |
|---|---|---|---|---|---|---|---|---|
| sg0 | 0.5 × 2.0 = **1.00** | 0.30 / 0.30 (150) | 0.99 | **0.00 / 0.00** | **35.9 / 54.2** | pad 20.9 / 29.3, toe 0 | 0..0.2 / 0 | 0.18 / 0.12 |
| sg1 | 0.6 × 2.3 = 1.38 | 0.25 / 0.25 (109) | 0.7 | 0.20 / 0.20 | 13.4 / 20.3 | 0, 0 | 0.7..25.2 / 0..35.3 | 0.76 / 0.01 |
| sg2 | 0.7 × 2.7 = 1.89 | 0.20 / 0.20 (74) | 0.45 | 0.40 / 0.40 | 7.8 / 11.8 | 0, 0 | 1.6..20.7 / 0..28.7 | 0.01 / 0.23 |
| sg3 | 0.8 × 3.0 = **2.40** | 0.15 / 0.15 (**50**) | 0.2 | **0.80 / 0.80** | 0.0 / 0.0 | 0, 0 | 2.6..3.8 / 0..3.8 | 0.18 / 0.19 |

Against short-term step 3's bar:

- **Slow end: heels up, lag 0.25–0.5.** sg0 holds no heel (36 / 54 mm up
  in stance), lag 0.30 of the stride, 150 ms. ✓
- **Fast end: heel 0.4+, lag ≥ 40 ms.** sg3 holds the heel on 0.80 of
  stance (the clip share orun12 needed to get 0.4 in the engine), lag 0.15
  of the stride, 50 ms. ✓
- **In between:** the clip's heel share rises 0 → 0.2 → 0.4 → 0.8 and the
  heel height falls 36 → 13 → 8 → 0 mm (LH; RH 54 → 20 → 12 → 0), per leg;
  the lag falls 0.30 → 0.25 → 0.20 → 0.15. The order (RH, LH, LF, RF,
  rotary, RH lead) never crosses: LF moves 0.20 → 0.35 of the stride, RH
  0.70 → 0.85, LH 0, RF 0.5. ✓
- Stride and rate both rise with speed (0.5 → 0.8 m, 2.0 → 3.0 Hz); every
  stride's `speed_mm_s` is the gait at that speed, as `sg-schedule.md`
  asks of a commanded task. The top stride, 2.40 m/s, is v05-s1-50's run
  speed (2.39), by a stride the generator reaches (the policy ran 0.97 m
  at 2.38 Hz; the generator refuses past ~0.8 m at duty 0.2).

## What the generator does that step 3's build must know

1. **A paw is laid flat only where its heel has a row.** `_leg_rows` adds
   the `flat_feet` pitch row only with a heel row (`CadexGait.py:459`). A
   stride with no held sample is solved once, with no heel rows, so sg0's
   paw stands on its **toe bulbs, pad 21–29 mm up, pin at its stop**: heels
   up, but not O2a's "on toe bulbs and pad, pin toes-up". Any stride with
   one held sample is solved twice, and the second pass eases the heel
   from touchdown to its hold (`_eased_heels`), with a heel row on every
   stance sample: sg1/sg2's paws are flat on pad and toes with the heel
   13–20 mm up and the pin 20–38° toes-up — the digitigrade O2a describes,
   but at a held share of 0.2, over SG's slowest-speed bar of 0.1.
   - Why sg0 is still the slow stride: the pin is not tracked
     (`track_pose`'s tags carry no `pawpin`), and `track_lift` reads the
     paw body's origin, so the paw's rotation on the pin changes no
     reward; under load the pad (behind the pin) lays the paw flat, and
     `paw_flat` (w10) pays it. The hind joints' references are what heels
     up needs, and sg0's have the heel highest.
   - If a judged SG policy's slow end stands on its toe tips (`T` frames
     in `paw_floor.py`), the lever is a generator option holding the heel
     at a height above the floor with the paw flat (ADR from ADR-786), not
     a reward.
2. **The heel share is quantised at 0.2.** Duty 0.2 on 25 samples is 5
   stance samples, so the clip's held share takes only 0, 0.2, 0.4, 0.6,
   0.8. The schedule blends joint references, not heel flags (no reward
   reads a reference heel flag: `plantigrade`, `heel_pitch`, `hind_flat`
   and `paw_flat` read `ref_*_down`, the paw's contact), so the engine's
   share can fall between them.
3. **RH's phase is fractional on the grid.** RH's offset (0.70–0.85 of 25
   samples) does not land on a sample, so a `heel_from` near a boundary
   holds a different count per leg: at sg0's speed `heel_from` 0.85 holds
   0 samples on LH and 1 on RH. Every stride above holds the same count on
   both. RH's heel also stands higher where it is free (54 vs 36 mm in
   sg0, as in the bundle's clip, 34.6 vs 23.5 mm max).
4. **Reach.** At duty 0.2 and swing 40 mm: 0.6 m at 2.4 Hz is refused at
   hind lag 0.24–0.25 (LH misses its swing target by 1.4 mm with
   `j_hip_l` and `j_pawpin_l` at a stop) and reached at 0.26 or at 2.3 Hz;
   0.5 m at 2.0 Hz with duty 0.3 is refused (2.9 mm, hip and knee stops);
   0.75–0.8 m at 3.0–3.2 Hz and 0.7 m at 3.4 Hz are reached. A lag of 0.12
   at 3.2–3.4 Hz is 35–38 ms, under O3's 40: the fast end keeps 0.15.

## What the SG task adds, for the build (step 3's second half)

From `sg-schedule.md`, made concrete for these strides:

- `reference=[sg0, sg1, sg2, sg3]` (each `assembly.gait` as `gallop_ref`,
  with the stride's `speed_mm_s`, `stride_length_mm`, `offsets`,
  `heel_from`); `body_drop_mm`, `stance_shift_mm` and swing as hk12-s1's
  on every stride (sg0–sg3 above are judged with them);
- `assembly.goal("cmd", kind="speed", between=[1000, 2400], ...)`, the
  actor's one new input (cold start);
- `track_speed` → tracking, `exp(-abs(comv_x - cmd) / (0.2 * cmd))`;
- `heel_pitch`, `plantigrade`, `hind_flat` weighted by the command's share
  of the range, `min(1, max(0, (cmd - 1000) / 1400))`, as literals (the
  script is at 64 parameters); `fore_sync` gated the same way or cut
  (it pays the fore pair together, against the slow end's 150 ms lag);
  `hind_lag` reads the blended reference flags and needs nothing;
- `paw_fold` (w −10) is in hk12-s1's and v05-s1's bundles against the
  charter's "not in the task": the SG task inherits it, and it stays
  unless a judged screen cuts it (noted in `REPORT.md` for the owner).
