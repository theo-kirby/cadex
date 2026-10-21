# orun13 P1: g3-flat at 50 is kept, g2-heel5c is stopped at 25, and a heel_pitch peaked on the flat sole is next

Verified against source: 2026-10-20. Frozen evidence (orun13, iteration 6).

## g3-flat at 50 (`gallop.cxpolicy`, sha256 `28e10c6c`)

g3-flat (`g3-flat-25.md`) ran to 50 iterations, cold, 4096 envs, seed 0,
on revision `a280b070`, from 22:37 to 23:24. The trainer read 32.24
reward/step at iteration 49, still rising about 0.5 an iteration. It was
judged as `g2-heel5-50.md` was, on the bundle's `gallop_spec`, seeds
1001–1010, on the CPU (`orun11/judge.py`, `orun12/legs.py`,
`orun13/p2_lag.py`, `orun13/spine_foot.py`, `orun13/heel_band.py`,
`orun12/trace_check.py`; the trace check is in
`~/orun13-logs/trace-g3-flat-50.txt`). The comparison is g2-heel5 at 50:
same task except for `hind_flat`, same model XML.

| evaluation | pass | top 2 s m/s min / med / max | straight (°) | hock_down LH / RH | at toe-off LH / RH | heel-down frames flat LH / RH | heel mm in stance LH / RH | no_tap | every_stride | overreach | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g2-heel5-50 | 0/10 | 2.50 / 2.58 / 2.73 | 10/10 (15.3) | 0.23 / 0.11 | 0.19 / 0.14 | 0.45 / 0.36 | 8 / 12 | 0/10 (1.59) | 10/10 | 3/10 (−229) | 63 / −204 | 961 / 752 | 2.78 / 3.61 | 1.00, 0.150 | 1.89 (j_spine) | 0.00 | 3.9 |
| **g3-flat-50** | 0/10 | **2.75 / 2.80 / 2.88** | 10/10 (15.8) | **0.39** / 0.11 | **0.50 / 0.24** | **0.68** / 0.13 | **2** / 12 | 0/10 (1.21) | 10/10 | **10/10 (516)** | 572 / 516 | 1130 / 1121 | 2.89 / 2.67 | 1.00, 0.220 | 1.82 (j_spine) | 0.00 | 4.5 |

- **Faster, longer, more even.** 2.80 m/s at the median against 2.58.
  The stride is 1130 / 1121 mm, against 961 / 752, and heel5c-s1's
  1168. The left and right strides are now within 1%, and the touchdown
  rates within 8%. `overreach` passes 10/10, against 3/10: the hind paws
  land 516–572 mm ahead of the fore paws' mean. The flight is 0.22 s a
  stride (heel5c-s1: 0.26). `completes` and `upright` pass 10/10.
- **The left heel came down; the right did not.** The engine has the LH
  heel down for 0.39 of stance (from 0.23) and at 0.50 of toe-offs (from
  0.19). The RH is unchanged at 0.11 and 0.24. In stance the LH heel sits
  2 mm up at the median and the RH heel 12 mm up. P1 is 0/10: `hock_down`
  worst-leg median 0.114, `hock_at_toeoff` 0.245.
- **The RH foot is toes-up when its heel is down.** When the RH heel is
  down, the sole is flat in only 0.13 of frames (LH 0.68). The other 0.87
  are toes-up, the orun12 fault. The engine does not count those frames as
  stance at all, because the toes are off the floor.
- **`no_tap` 1.21**, from 1.59: the fore paws step 1.21 times a hind
  stride. The bar is 1.10.
- **Footfalls (`p2_lag.py`, O3).** At 2.38 strides/s (420 ms a cycle),
  the fore lag is 0.049 of a cycle (about 21 ms) and the hind lag 0.172
  (about 72 ms). The hind pair now passes O3's 40 ms; the fore pair does
  not, and lands together 0.57 of the time. No seed reads rotary: 122 of
  208 strides are tied.
- **Torque (O6).** The worst drive is `j_spine` at 1.82 × rated RMS, with
  peak margin 0.00.

**Decision: g3-flat is kept.** At 25 the rule was set (`g3-flat-25.md`):
keep it only if it beats g2-heel5-50 on the flat share and the heel share
at a speed within reach of it. It does on the left leg (flat 0.45 → 0.68,
heel 0.23 → 0.39) and holds on the right (heel 0.11 → 0.11), at a higher
speed (2.58 → 2.80). The right foot's flat share fell (0.36 → 0.13), so
the keep is made on the left leg, the speed, the overreach and the
stride. The two-sided `hind_flat` stays in the task the next screen
builds on.

## Spine (`spine_foot.py`, O4)

| | j_spine min / max | range per stride (sum of both joints) | at a stop | cable gap max | peak flexion / extension, phase of the LH stride |
|---|---|---|---|---|---|
| g2-heel5-50 | −18.4 to −22.7 / +15.5 to +21.0 | 36.6° | 0.00 | 0.72° | 0.64–0.84 / 0.33–0.37 |
| **g3-flat-50** | −18.3 to −20.8 / +6.6 to +10.3 | **37.7°** | **0.00** | 0.56° | 0.39–0.90 / 0.41–0.45 |

The spine flexes and extends 37.7° a stride and reaches no stop. It now
flexes further than it extends (−20 / +9). The cable holds `j_spine2`
within 0.56° of `j_spine` (O9: 1°).

## Real meshes and loops (`trace_check.py`, O9)

- **The hind-paw/elbow clash is gone.** Five pairs that are apart in the
  build pose go deeper than 5 mm, all on seed 1005 and all within 5.6 mm:
  chest frame × left forearm or wrist drive, the right fore paw and its
  rod × the jaw. At g2-heel5-50 there were 18, with hind paws up to
  27.4 mm into the fore elbow drives. The longer stride lands the hind paws
  ahead of the fore paws, not into them.
- **Front rod loops open to 3.37 / 4.46 mm** (`j_frodbot_l` / `_r`; medians
  0.12 / 0.15). The hind rods hold at 1.10 / 1.59 mm. This stays a Q2
  candidate.

## g2-heel5c at 25 (`gallop.000025.cxpolicy`, sha256 `ab4e72c3`): stopped (O8)

g2-heel5c warm-starts g2-heel5's final policy (`a3d6bfb1`) on its own
bundle (`e46d3273`). It ran 5 critic-only iterations, then the default
learning rate, with 4096 envs, launched 23:24. It asked whether leo's heel
returns as the gait settles. Judged the same way:

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH | at toe-off LH / RH | heel mm in stance LH / RH | heel-down frames flat LH / RH | no_tap | every_stride | overreach | stride mm LH / RH | touchdown Hz LH / RH | flight share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g2-heel5-50 (its start) | 0/10 | 2.50 / 2.58 / 2.73 | 0.23 / 0.11 | 0.19 / 0.14 | 8 / 12 | 0.45 / 0.36 | 0/10 (1.59) | 10/10 | 3/10 | 961 / 752 | 2.78 / 3.61 | 1.00, 0.150 | 1.89 (j_spine) | 0.00 | 3.9 |
| **g2-heel5c-25** | 0/10 | **2.92 / 3.03 / 3.08** | **0.10 / 0.05** | 0.16 / 0.07 | 13 / 19 | 0.12 / 0.15 | **8/10 (1.07)** | 10/10 | **7/10 (491)** | 1231 / 1218 | 2.33 / 2.56 | 1.00, 0.260 | 1.77 (j_spine) | 0.00 | 4.6 |

- **The fastest gait on leo yet**, at 3.03 m/s. heel5c-s1 on v07 did
  2.91. `no_tap` passes 8/10, `overreach` 7/10 and `straight` 10/10. The
  strides are 1231 / 1218 mm, and the flight 0.26 s a stride.
- **It is on its toes.** The heels are down 0.10 / 0.05 of stance,
  against 0.23 / 0.11 at its start. In stance they sit 13 / 19 mm up.
  When a heel is down the foot is toes-up 0.88 / 0.85 of the time. On the
  ground the feet are on their toes 0.50 / 0.72 of frames, at +16.6° /
  +18.8° (`heel_band.py`). The current `heel_pitch` band still pays those
  frames 0.85 / 0.75, and the peaked band would pay them 0.26 / 0.24.
- **Footfalls.** The fore lag is 0.095 of a cycle (about 40 ms), but the
  hinds land together 0.88 of the time (lag 0.000): a half-bound behind.
  No seed reads rotary.
- **Spine:** 28.6° a stride, never at a stop, cable gap ≤ 0.76°.

The heel share fell on both legs by the first judged checkpoint, so the
screen's measure is moving the wrong way. It was stopped at 23:51, at iteration 25
(`loop.request_stop`), 25 iterations early, and recorded as a dead end
for P1. As the gait settles on heel5's task, the heel does not return:
it leaves. Its 25 checkpoint stays as the speed and P2 reference for a
heel-up gait on leo.

Neither g3-flat (0.39 / 0.11) nor g2-heel5c (0.10 / 0.05) lifts both
heels above about 0.35, so the critic's condition for the next screen
holds.

## Where the feet sit in heel_pitch's band (`heel_band.py`)

`heel_pitch` pays the metatarsus's world pitch `m` in the clip's hind
stance: in full at `m` ≤ 10°, nothing at 45°. leo's sole is flat at
+4.5° (`hind_flat_target.py`). In the judged traces, one degree of pitch
about the toes lifts the heel 1.26–1.35 mm (a straight-line fit of sole
tilt on `m`, correlation −0.98 to −1.00). The engine counts a heel as
down within 1 mm (`STANCE_MM`), so a heel down with the toes needs `m`
within about 0.8° of flat. The band pays in full up to 5.5° off flat,
with the heel about 7 mm up.

On the ground, each hind foot is flat (heel and toes down), toes-up (heel
only) or on its toes (toes only):

| evaluation | leg | flat / toes-up / toe share | median `m` flat / toes-up / toe (°) | pay: now / flat-only / peak | toes-up share of `now` pay |
|---|---|---|---|---|---|
| g2-heel5-50 | LH | 0.18 / 0.23 / 0.58 | 4.5 / −7.8 / 14.4 | 0.84 / 0.73 / 0.40 | 0.28 |
| | RH | 0.10 / 0.17 / 0.73 | 4.5 / −2.9 / 15.2 | 0.80 / 0.76 / 0.37 | 0.21 |
| g3-flat-25 | LH | 0.23 / 0.04 / 0.73 | 4.5 / 0.9 / 8.5 | 0.96 / 0.96 / 0.60 | 0.04 |
| | RH | 0.11 / 0.07 / 0.82 | 4.5 / −3.9 / 10.6 | 0.94 / 0.92 / 0.45 | 0.07 |
| g3-flat-50 | LH | 0.33 / 0.16 / 0.51 | 4.5 / 1.4 / 11.1 | 0.90 / 0.89 / 0.62 | 0.18 |
| | RH | 0.07 / 0.42 / 0.51 | 4.5 / −7.9 / 14.6 | 0.88 / 0.66 / 0.31 | 0.48 |

- The commonest posture is a toe stance: half the on-ground frames or
  more on every leg and policy, at +8.5° to +15° (the heel 6–15 mm up).
  The current band pays it 0.80–0.96 a frame.
- Closing only the toes-up side (`flat-only`: full −1° to +10°, nothing
  at −15°) changes little. It cuts the pay by at most 0.22 (g3-flat-50
  RH), and leaves the toe stance paid in full.
- A band **peaked on the flat sole** separates them: `0.3 exp(−((m −
  4.5)/20)²) + 0.7 exp(−((m − 4.5)/3)²)` pays 1 when flat, 0.93 at 1°
  off, 0.41 at +8.5° and 0.30 at +10°. On these traces it pays 0.31–0.62
  where the current band pays 0.80–0.96. The broad term keeps a slope
  from a toe stance at +15° to +30°. It costs fewer expression nodes than
  the clamp it replaces: `m` appears twice a leg instead of four times.

The critic asked for a band that pays only the flat sole if neither screen
lifts both heels above about 0.35. The measurement says the band must close
the heel-up side as well, since that side is where the pay goes. The
peaked band does both.

**Scored per step on the bundle first (O7, `reward_terms.py`):**

| bundle | `heel_pitch` hold / keyframe / clip | `hind_flat` hold / clip | total hold / clip |
|---|---|---|---|
| g3-flat (≤ 10° band) | 1.345 / 0.000 / 2.179 | 0.257 / 1.059 | 3.305 / 33.435 |
| g3-flat + peaked band | 0.384 / 0.000 / 1.718 | 0.257 / 1.059 | 2.344 / 32.974 |

Standing still in the dropped pose now earns `heel_pitch` 0.38 a step,
not 1.35. Perfect clip tracking earns 1.72, not 2.18. The clip does not
hold the sole exactly flat in its hind stance.

## Queued: g4-peak

g4-peak is g3-flat's task with `heel_pitch` peaked on the flat sole, and
nothing else changed (`~/orun13-scripts/leo-flatpeak.py`, project git
`leo-flatpeak.py`, revision `b4680361`). It is cold, 50 iterations, 4096
envs, seed 0, budget_s 4000. It launched at 23:52, when g2-heel5c was stopped. Its bundle's
`heel_pitch` expression is byte-identical to the one scored above, and its
model XML is byte-identical to g3-flat's.

It is judged at 25 against g3-flat at 25 and 50, on:
- the heel share and toe-off share per leg;
- the on-ground share flat, toes-up and on the toes (`heel_band.py`);
- speed.

It is kept only if both heels rise without speed falling below g3-flat's
at the same checkpoint. A first build of the same change on g2-heel5's
task (`leo-peak.py`, revision `db32673e`) was superseded before it ran,
once g3-flat was kept.
