# orun13 P1: g6-swank at 25 fails its keep rule; leo-v02.1 widens the hock 5° heel-side (O1)

Verified against source: 2026-10-21. Frozen evidence (orun13, iteration 12).

## g6-swank at 25 (`gallop.000025.cxpolicy`, sha256 `5efca7b1`)

g6-swank is g4-peak's task with each hind ankle's `track_pose` error gated
by `(1 − ref_down)`. The clip's ankle target is tracked in the hind swing
only, and `heel_pitch` alone sets the stance foot (`g4-peakf-25.md`). It
runs cold on `936e27e5` (project git `ca3729f`), 4096 envs, seed 0, at
about 67 s an iteration. It was judged at 25 the same way as the earlier
screens: `gallop_spec` on seeds 1001–1010, on the CPU (`orun11/judge.py`,
evaluation `g6-swank-25`). The evaluation was read with `orun12/legs.py`,
`orun13/spine_foot.py`, `orun13/p2_lag.py` and `orun13/hind_reach.py`.
Its baseline is g4-peak-25, the same task cold without the gate.

| evaluation | pass | top 2 s m/s min / med / max | completes | upright | straight | hock_down LH / RH | at toe-off LH / RH | heel-down frames flat LH / RH | toes-up LH / RH | heel mm in stance LH / RH | no_tap | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g4-peak-25 | 0/10 | 0.81 / 0.94 / 1.16 | 9/10 | 9/10 | 7/10 | 0.13 / 0.14 | 0.10 / 0.00 | 0.49 / 0.73 | 0.51 / 0.27 | 9 / 10 | 1/10 (1.93) | −168 / −198 | 203 / 199 | 2.89 / 4.28 | 0.69, 0.040 | 1.88 (j_tail1) | 0.00 | 2.1 |
| **g6-swank-25** | 0/10 | 1.03 / **1.16** / 1.23 | 10/10 | 10/10 | 7/10 | **0.11** / 0.17 | 0.06 / 0.06 | 0.79 / 0.90 | **0.21 / 0.10** | 10 / 10 | 0/10 (1.84) | −202 / −243 | 228 / 257 | 2.72 / 4.06 | 0.75, 0.045 | 1.71 (j_spine) | 0.00 | 2.5 |

- **P1** is 0/10. The worst-leg medians are `hock_down` 0.114 (bar 0.40)
  and `hock_at_toeoff` 0.049 (bar 1.0).
- **Footfalls (`p2_lag.py`).**
  - Fore lag is 0.353 of a cycle, and the fore pair lands together on 0.13
    of strides.
  - Hind lag is 0.161, together on 0.24.
  - 0/10 seeds are rotary.
  - Flight is 0.045 s.
- **Spine (`spine_foot.py`).** 31.1° a stride over both joints, 0.04 of
  the time at a stop. The cable gap is at most 0.46°.
- **Torque (O6).**

  | drive | RMS/rated | time at peak | peak margin |
  |---|---|---|---|
  | `j_spine` | 1.71 | 0.23 | 0.00 |
  | `j_hock_l` | 1.43 | 0.23 | 0.00 |
  | `j_hock_r` | 1.25 | 0.15 | 0.00 |

  g4-peakc-25's hocks were 1.15 / 1.04 at 0.18 / 0.14.
- **Loop gap (O9).** 2.5 mm.

### The hock in stance (`hind_reach.py`)

| leg | class | frames | hock (°) | margin to stop (°) | hock cmd − meas (°) | effort/peak med / p95 |
|---|---|---|---|---|---|---|
| LH | flat | 331 | −44.1 | 25.9 | **+15.5** (g4-peak-25 +5.7) | 0.96 / 1.00 |
| LH | toes-up | 86 | −38.9 | 31.1 | +5.1 | 0.07 / 0.28 |
| LH | toe | 2312 | −41.7 | 28.3 | **+17.4** (+13.7) | 0.78 / 1.00 |
| RH | flat | 421 | −50.3 | 19.7 | +13.5 (+20.4) | 0.87 / 1.00 |
| RH | toes-up | 51 | −39.5 | 30.5 | +4.3 | 0.11 / 0.47 |
| RH | toe | 2165 | −41.6 | 28.4 | +11.9 (+13.2) | 0.58 / 1.00 |

### Decision

Against the keep rule in `g4-peakf-25.md`:

| part | needed | result | met? |
|---|---|---|---|
| hock stance command offset falls | below +5.7 / +20.4 (flat) and +13.7 / +13.2 (toe) | +15.5 / +13.5 and +17.4 / +11.9 | **no** (LH rises in both) |
| toes-up | at most 0.51 / 0.27 | 0.21 / 0.10 | yes |
| heels | at least 0.13 / 0.14 | 0.11 / 0.17 | **no** (LH) |
| speed | at least 0.94 m/s | 1.16 m/s | yes |

**g6-swank fails.** Freeing the stance ankle from the clip flattened the
sole: toes-up halves on both legs, and heel-down frames are 0.79 / 0.90
flat. But it does not take the hock off peak. The LH stance command
moved further heel-up, and the LH heel share fell. The clip's stance
ankle target was not what drove the hock heel-up.

That is the seventh P1 screen on the policy side:
- g2-heel5;
- g3-flat;
- g4-peak and g4-peakc;
- g4-peakf;
- g5-toe;
- g6-swank.

As the critic directed, the clip and reward shaping for P1 stops here, and
the O1 model change is made. g6-swank ran on to 50 (03:01) so the GPU was
busy through the builds (O8).

### g6-swank at 50 (`gallop.cxpolicy`, sha256 `877d4b1e`), against g4-peak-50

| evaluation | pass | top 2 s m/s med | hock_down LH / RH | at toe-off LH / RH | toes-up LH / RH | overreach | flight s | worst RMS/rated | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|
| g4-peak-50 | 0/10 | 2.43 | 0.44 / 0.22 | 0.43 / 0.21 | 0.09 / 0.06 | 10/10 | 0.160 | 1.80 (j_spine) | 3.8 |
| g6-swank-50 | 0/10 | 2.35 | 0.42 / 0.29 | 0.09 / 0.16 | 0.17 / 0.11 | 0/10 | 0.120 | 1.94 (j_spine) | 4.8 |

- **No better than g4-peak-50.** RH heels rise by 0.07, but toe-off,
  toes-up, overreach, speed and the loop gap are all worse. The swing-only
  ankle gate is a dead end.
- **More O1 evidence (`hind_reach.py`).** At 2.35 m/s the stop binds
  again:
  - RH's flat frames stand at −66.5°, 0.42 of them within 2° of the −70°
    stop. LH's stand at −63.5°, 0.24 of them.
  - RH's **toe-stance** frames sit at −64.8°, also 0.42 within 2° of the
    stop. The hock is at its heel-side stop with the heel still up, so for
    those frames the leg cannot reach a flat sole at all.
  - The hock's effort is at peak in flat and toe stance (p95 1.00).

## O1 model change: leo-v02.1, the hock's heel-side stop from −70° to −75°

Written for −80° before the first build; −80° failed clearance and −75° was built instead (below).

**The measurement** (`g4-peakf-25.md` and above):
1. **At speed, the flat foot is on the stop.**
   - At 2.55–2.65 m/s (g4-peakc-25, g4-peakf-25) the flat foot stands at
     hock −60 to −70°.
   - 0.29–0.56 of its flat frames are within 2° of the −70° stop. On
     g4-peakf-25, RH's flat median is −69.7°.
   - At ~1 m/s (g4-peak-25, g6-swank-25) it stands at −36 to −50°, with
     20–34° of margin.
   - So the hock a flat sole needs grows with speed, and at the speed P1
     must hold, the stop sets it. A posture that needs more than −70° for
     a flat sole cannot have one: the heel stays up.
2. **The stop is also the edge of the command box.**
   - The hock's box is its travel, −70..+40 (`FULL_TRAVEL`, `widen`=1).
   - The trainer centres each action on its box, here −15°
     (`training/cadex_train.py`: `output_bias` is (high + low)/2).
   - The fast flat seat sits at 0.82–1.00 of the heel-side half-range.
     The command cannot go past the stop, so near the seat the drive can
     hold at most a few degrees heel-down.
3. **The hock is at peak through the stance.**
   - In flat and toe stance its effort is at peak (p95 1.00).
   - The hocks are at peak 0.14–0.23 of the time, at 1.04–1.43× rated RMS.
   - Peak margin is 0.00 on every checkpoint.

**The change.** In `~/orun13-scripts/leo-hock80.py`, the rigid foot's
hock and ankle stops go from −70..+40 to **−80..+40** (mirrored on the
right). That is one literal: the script is at its 64-parameter cap.
- The command box follows the travel, so its centre moves from −15° to
  −20°.
- The fast flat seat (−60 to −70°) gets 10–20° of margin, and sits at
  0.67–0.83 of the heel-side half-range.
- Nothing else changes. The task is g4-peak's (`leo-flatpeak.py`: the
  flat-peaked `heel_pitch`, 18 terms), so the screen isolates the model.
  Thigh, shin, foot, drive and rod geometry are untouched.

**Expected effect.**
- At the fast posture the foot can lie flat without resting on the stop.
  So `hock_down` should rise on the warm-speed gait.
- RH's flat frames should leave the stop (g4-peakf-25: 0.56 of them
  within 2°).

**Risks, checked after the build.**
1. **Clearance of the metatarsus and heel against the shin past −70°.**
   - In the −70..+40 sweep, shin/metatarsus is at a 0.5 mm minimum and
     shin/heel at 2.8 mm.
   - The rebuild's `cadex clearance` and `--sweep` are compared pair by
     pair with `orun13/clearance_diff.py`.
   - Baseline on `936e27e5`: 16 static pairs fail and 8 swept pairs fail
     (by the CLI's 1e-6 mm³ common-volume default).
   - A new failing pair rejects the change.
2. **Transmission.** The crank sits at 100° + hock off the rod
   (`script.py`, `LINK_V` comment). At −80° it is 20° off, against 30° at
   −70°, so the rod's force at the stop is 1.46× for the same torque. The
   hind loop gap is re-measured on the screen (O9: ≤ 2 mm; g4-peak-25
   was 2.1 mm).
3. **Toes-up past flat.** The stop no longer catches a foot pressed past
   flat at the fast posture. Toes-up share is judged per leg.

**The builds.**

1. **−80° (`leo-hock80.py`, revision `02236c8f`, project git `f5abe3a`):
   rejected.**
   - The sweep adds two failing pairs: `c_meta_hl / c_shin_l` and
     `c_meta_hr / c_shin_r`, 3.4 mm³ each, first contact at the −80°
     sample.
   - `clearance_diff.py` puts the swept failing pairs at 8 before and 10
     after.
   - It was never tagged or trained. Its queued screen was stopped before
     it launched.
2. **−75° (`leo-hock75.py`, revision `8eb6aed6`, project git `54fbf22`,
   tagged `leo-v02.1`): clean.**
   - No new failing pair. Static failing pairs are 16 before and after;
     swept failing pairs are 8 before and after.
   - Over −75..+40 the shin/metatarsus minimum is still 0.5 mm, and
     shin/heel drops from 2.8 to 1.7 mm.
   - The build's own verdicts match leo-v02's baseline: fit fails 16
     static pairs, the sweep fails 12 pairs (all front leg against the
     chest), mounting passes, and the panels report 0 failing.
   - The command box is −75..+40, centred on −17.5°. The fast flat seat
     (−60 to −70°) now has 5–15° of margin and sits at 0.74–0.91 of the
     heel-side half-range (57.5°). The crank is 25° off the rod at the stop.

**The screen.** The digest changes, so the trainer refuses a warm start,
and the screen is cold:
- g4-peak's task on leo-v02.1, 50 iterations, 4096 envs, seed 0;
- budget 4,000 s: g6-swank's 67 s an iteration, plus 20%;
- run `g7-hock75`, queued at 02:55 with `queue_run.py --expect-revision
  8eb6aed6`, so it launches when g6-swank's budget frees the slot.

It is the same task, cold, that g4-peak ran on leo-v02. So its
before/after pairs are:
- g4-peak-25 at 25: 0.94 m/s, heels 0.13 / 0.14, toes-up 0.51 / 0.27;
- g4-peak-50 at 50: 2.43 m/s, heels 0.44 / 0.22, toes-up 0.09 / 0.06,
  hock_at_toeoff 0 / 0;
- g4-peakc-25, the critic's reference: heels 0.47 / 0.28, toe-off
  0.61 / 0.48, 2.65 m/s, flat frames on the stop 0.29 / 0.29.

**Keep leo-v02.1 only if, at 50 against g4-peak-50:**
- heels rise on both legs;
- the share of flat frames within 2° of the hock's heel-side stop falls from g4-peak-50's 0.29 / 0.08 (`hind_reach.py`; there the LH flat foot stands at −62.5°);
- toes-up is at most 0.10 per leg;
- speed is at least 2.2 m/s (g4-peak-50 less 10%);
- the loop gap is no worse than g4-peak-50's 3.8 mm (front rods), and each hind rod's gap stays under 2 mm.

At 25 it is screened against g4-peak-25 for direction only. If heels and
speed both fall there, it stops early (O8).

**Launched.** g7-hock75 launched at 03:01:57, when g6-swank's run freed
the slot.
- Its bundle carries the hock box −75..+40 (RH mirrored).
- Against g4-peak's bundle, the model differs only in four joint ranges:
  `j_hock_*` and `j_ankle_*`, −1.22173 → −1.309 rad. The rewards are
  identical. The clip's joint angles are unchanged; only its recorded
  `joint_limits_rad` differ.
- Iteration 10 came at 746 s, against g6-swank's 676 s. g6-swank finished
  50 in 2,794 s, so g7 should finish 50 at about 3,100–3,700 s, inside its
  4,000 s budget. Iteration 25 is due at about 03:30.

