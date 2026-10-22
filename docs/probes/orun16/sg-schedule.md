# orun16 SG: what one ADR-773 speed schedule can carry on leo

Verified against source: 2026-10-22. Frozen evidence (orun16, iteration 2).
Short-term step 2: a reading, on the CPU, of the speed-scheduled gait
reference (ADR-773, `docs/DECISIONS.md`), against leo's gallop task as
v05-s1 trains it (`runs/v05-s1/train/gallop-task.json`, revision
`15d9feb4`). No code changed, nothing built. What it does not settle is
listed at the end, for step 3.

## What the schedule is (read in the source)

- `assembly.task(reference=[g0, ..., gK-1])`: 2 to 8 `assembly.gait`
  values, slowest first, speeds strictly rising
  (`MAXIMUM_REFERENCE_SCHEDULE = 8`, `cadex_assembly_api.py:1343`,
  `:5726-5807`). The api checks only that each names the same `feet` and
  the same `spine` as `g0`; everything else in `gait(...)` is per stride.
- The worker generates every stride on one phase grid, at the largest
  sample count any of them takes at 50 Hz (`CadexDynamics.py:12724`,
  `_reference_schedule_records`), and refuses:
  - `schedule_joints_differ`: a stride posing other joints than stride 0;
  - `schedule_footfall_order`: a pair of feet landing in the other order
    from one stride to the next (they may meet, not cross);
  - `schedule_with_cadence`: `reference_cadence` other than `"fixed"`;
  - a stride the legs cannot reach, named by index, label and speed.
- It needs exactly one `goal(kind="speed")` whose `between` lies inside
  the strides' speeds (no extrapolation). The policy observes the goal
  (one actor input), and rewards read it by name (`cmd`, as leo's C1
  task does: `script.py:2383`).
- Each step the command picks the bracketing strides and blends every
  `q_*_ref`, `ref_<foot>_lift` and `ref_<foot>_down` channel linearly at
  the phase, a down flag thresholded at one half after the blend; the
  clock turns at the blended frequency, summed, so the phase never jumps.
- A random start begins on the stride nearest the opening command.
  `judged_reference` judges an evaluation against the stride nearest the
  settled command. The drive proxy (ADR-710) replays only the slowest.
- A warm start onto a schedule is refused (`reference` and `tracking`
  move), so the SG policy trains cold, as O2a says.

## What one reference can schedule

Every one of these is an argument of `assembly.gait` and so may differ
from stride to stride:

| lever | `gait(...)` argument | per stride? | constraint |
|---|---|---|---|
| heel hold | `heels`, `heel_from` (0–0.99) | yes | `flat_feet` needs `heels` (`CadexGait.py:737`), so a stride with no heels cannot lay the paw by `"sole"`; keeping `heels` on every stride and scheduling `heel_from` keeps the joints and the sole rule alike |
| body drop | `body_drop_mm`, `body_pitch_deg` | yes | whole stride, blended through the joints (ADR-773: the blend's height is what the blended joints give) |
| stance shift | `stance_shift_mm` | yes | orun15 (`ss-sole`): the generator refused under 120 mm on the plantigrade clip at 0.7 m |
| pair lag | `offsets` (`LH` 0, `RH` 1 − hind lag, `RF` 0.5, `LF` 0.5 − fore lag) | yes | the order must not cross between strides: the lags may shrink towards 0, never past it |
| duty | `duty` | yes | the plantigrade clip at 0.7 m reaches only 0.2 (`script.py:2740`) |
| stride, rate | `stride_length_mm`, `speed_mm_s` | yes | the clock is the blended frequency; `speed_mm_s` must rise |
| swing, spine | `swing_height_mm`, `spine_amplitude_deg` | yes | the spine joint itself must be the same |

So **yes: one reference can carry heel hold, body drop, stance shift and
pair lag as functions of speed**, each linear between the strides, in up
to 8 strides.

**The lag in milliseconds** is `share × 1000 / f`. O3's 40 ms needs a
share ≥ 0.04 f: at 2.4 Hz ≥ 0.096, so the fast end's 0.1–0.15 holds only
at 2.5 Hz or below (0.1) or 3.75 Hz (0.15). At 50 Hz a lag is whole
20 ms samples; today's clip lands each pair 3 samples (60 ms) apart.

## What a speed command adds to the task

- **One actor input**, the goal `cmd` (92 observation channels today, 50
  of them the actor's; cap 128), hence a cold start.
- **A goal**, `assembly.goal("cmd", kind="speed", between=[v0, v1],
  resample_seconds=..., ramp_seconds=...)`, inside the strides' speeds.
- **The speed reward changes meaning.** `track_speed` (w20) now pays
  forward speed linearly up to `sprint_speed`; a commanded task pays
  tracking, `exp(-abs(comv_x - cmd) / (0.2 * cmd))` (ADR-773), or the
  policy runs its top speed at every command.
- **The clip's speed should be the speed run.** hk12-s1's clip asks
  1.68 m/s (0.7 m at 2.4 Hz) and the policy ran 2.40 with a 991 mm
  stride, longer than the clip's: the speed term outpaid the clip. On a
  schedule each stride's `speed_mm_s` is the command that selects it, so
  a stride must be the gait at that speed.
- **Terms that are not tables are not scheduled.** `heel_pitch` (w10,
  peaked at +6° on the metatarsus in the clip's hind stance),
  `plantigrade` (w10, the heel on the floor in stance) and `hind_flat`
  (w6) pay a heel down at every speed, so a slow stride's heels-up
  reference would be fought by them. They must be gated by the command,
  e.g. weighted by `min(1, max(0, (cmd − v0) / (v1 − v0)))` written in
  the expression (a literal; the script is at 64 parameters). `paw_flat`
  (the paw's floor pitch within 15°) holds at both ends: digitigrade is
  still the paw flat on pad and toes, heel up (O2a).
  `hind_lag` (w10) is `abs(ref_lh_down − ref_rh_down) · (1 −
  abs((chl_down − chr_down) − (ref_lh_down − ref_rh_down)))`: it reads
  the reference's flags, so it follows the blended lag as it is.
  `fore_sync` (w2) is `1 − abs(cfl_down − cfr_down)`: it pays the fore
  paws down together at every speed, against the slow end's wide fore
  lag; it is to be cut or gated by the command too.
- **Judging at a speed** needs no retraining: the success spec is outside
  the task's semantic digest (`script.py` comment at the `run_policy`
  declaration), so `gallop_spec` with `goals=[goal("cmd", kind="speed",
  ..., sequence=[v])]` per judged speed judges one policy at each
  (ADR-750 carries a spec's goal sequence to the engine).
- **Terms:** 21 today, cap 32; replacing `track_speed` and gating the
  heel terms and `fore_sync` adds none.
- **The charter's "paw_fold is not in the task" does not match the
  bundle:** hk12-s1's and v05-s1's `gallop-task.json` both carry
  `paw_fold` at w −10 (21 terms). v05-s1 is hk12-s1's task, as B1 asks;
  the SG task inherits the term unless step 3 cuts it.

## Not settled, for step 3 (judge the reference first)

1. Whether a slow stride with `heels` kept and a late `heel_from`
   (towards 0.99) stands the paw on pad and toes with the heel up under
   `flat_feet="sole"` / `trail_feet`, or a heel-less stride is needed
   (and then whether `j_pawpin_*` stays in the posed joints:
   `schedule_joints_differ`). Read with `orun15/clip_read.py`.
2. Which slow strides the generator reaches: shorter strides, larger
   duty, and the slow end's 0.25–0.5 lag (at 0.7 m it refused every
   right-trailing hind lag and reached the RH-lead order at 0.1–0.15:
   `orun13/clip_lag.md`).
3. The fast end's top speed: around 2.4 m/s (hk12-s1-50's 2.40) with
   lag ≥ 0.1 and heel held from ~0.2 (the clip's 0.8 of stance).
