# orun13 P1: g8-gate is stopped at 25; LH's roll is the policy's, against the clip; g9-roll charges it

Verified against source: 2026-10-21. Frozen evidence (orun13, iteration 15).

## 1. g8-gate at 25 (`gallop.000025.cxpolicy`)

g8-gate is g4-peak's task, with `heel_pitch` gated on the clip's stance
*or* the paw's own contact (`g7c-hock75.md`). It runs on leo-v02
(`86c15551`), cold, at 4096 envs. Checkpoint 25 was written at 04:41.

It was judged as before:
- `gallop_spec` on seeds 1001–1010, on the CPU (`orun11/judge.py`,
  evaluation `g8-gate-25`, 33 s);
- read with `orun12/legs.py`, `orun13/spine_foot.py`,
  `orun13/stance_gate.py`, `orun13/hind_reach.py` and
  `orun13/lh_roll.py`.

It is compared with g4-peak-25: the same task, ungated, at the same
budget point.

| evaluation | pass | top 2 s m/s min / med / max | hock_down (worst-leg median) | hock_down LH / RH | at toe-off LH / RH | flat / toes-up LH | flat / toes-up RH | heel mm in stance LH / RH | no_tap | every_stride | stride mm LH / RH | touchdown Hz LH / RH | flight stride share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g4-peak-25 | 0/10 | 0.81 / 0.94 / 1.16 | 0/10 (0.102) | 0.13 / 0.14 | 0.10 / 0.00 | 0.49 / 0.51 | 0.73 / 0.27 | 9 / 10 | 1/10 (1.93) | 9/10 | 203 / 199 | 2.89 / 4.28 | 0.69, 0.040 | 1.88 (j_tail1) | 0.00 | 2.1 |
| **g8-gate-25** | 0/10 | 0.43 / **0.66** / 0.85 | 0/10 (0.043) | **0.04** / 0.19 | **0.00** / 0.13 | 0.97 / 0.03 | 0.92 / 0.08 | 10 / 5 | 0/10 (4.05) | 7/10 | 303 / 278 | 2.33 / 3.44 | **0.03**, 0.000 | 2.26 (j_tail1) | 0.00 | 2.3 |

Seed 1001 at its source (`evaluation.json`): it fails `top_speed` (640
mm/s), `hock_down` (0.039), `hock_at_toeoff` (0.0), `no_tap` (7.12) and
`overreach` (−238 mm).

- **P1 is 0/10.** The LH heel share falls from 0.13 to 0.04, and LH
  toe-off from 0.10 to 0.00. RH rises a little: heels 0.14 → 0.19, toe-off
  0.00 → 0.13.
- **The foot stands on its toes, crouched.** Toe stance is 3,591 LH frames
  and 2,809 RH, with the hock at −39.0° and −27.5°. A flat sole needs it
  in the −60s. Where the heel is down, the sole is flat (toes-up
  0.03 / 0.08).
- **No flight.** The flight stride share falls from 0.69 to 0.03; flight
  time is 0.000 s.
- **Spine (`spine_foot.py`).** 28.3° a stride over both joints, and it
  sits **at its flexion stop 0.29** of the time (j_spine down to −27°).
  g4-peak-25 sat there 0.00. The cable gap is at most 0.25°.
- **Torque (O6).** The worst drive is `j_tail1` at 2.26× rated, with a
  peak margin of 0.00.
- **Rod loops (O9), max (median), in mm.**
  - Front L: 2.25 (0.07).
  - Front R: 1.63 (0.10).
  - Hind L: 0.80 (0.07).
  - Hind R: 1.12 (0.07).

### The gate's own measure moved the wrong way (`stance_gate.py`)

| evaluation | leg | stance frames med (clip) | on-ground in clip / outside | toe-offs | window wholly outside clip stance | fit match |
|---|---|---|---|---|---|---|
| g4-peak-25 | LH | 12 (5) | 0.33 / 0.67 | 254 | 0.92 | 0.54 |
| g4-peak-25 | RH | 7 (5) | 0.38 / 0.62 | 342 | 0.63 | 0.63 |
| g8-gate-25 | LH | 17 (5) | 0.28 / 0.72 | 208 | 0.92 | 0.40 |
| g8-gate-25 | RH | 11 (5) | 0.30 / 0.70 | 296 | **0.72** | 0.45 |

RH's toe-offs outside the clip's stance rose from 0.63 to 0.72. The
stance has stretched to 17 and 11 frames against the clip's 5. This is
the risk `g7c-hock75.md` named: paid to stand, the policy stands off the
clip's schedule, flat-footed or on its toes, and slowly.

### Decision: stopped at 25 under O8

The rule written at launch was to stop if `hock_at_toeoff` and speed
**both** fell below g4-peak-25's (0.10 / 0.00, 0.94 m/s):
- speed: 0.66 m/s, below;
- `hock_at_toeoff`: LH 0.00, below 0.10; RH 0.13, above 0.00. The
  worst-leg median is 0 on both.

Read per leg, the rule is split. **It is stopped anyway, under O8** ("a
screen that clearly is not moving its measure by its first judged
checkpoint"). The measure it was built to move, RH's toe-offs outside
the clip's stance, worsened (0.63 → 0.72). Speed fell 30%, flight
vanished, and LH lost its heel. This deviates from the letter of the
rule, for the reasons above.

It was stopped at 04:44 (`loop.request_stop`, state `stopped`). The gate
is a dead end. Paying a flat foot off the clip's clock buys standing,
not a heel at toe-off.

## 2. LH's roll against the clip (`lh_roll.py`, new)

The critic asked for this before LH's 3-frame roll is changed. Each hind
toe-off is aligned on its lift frame (the last frame with the paw down).
The clip is read around its last heel-down sample.

### The clip does not roll

| leg | sample (vs last heel-down) | paw down | heel down | heel mm | paw mm | hip / knee / ankle ° (left sign) |
|---|---|---|---|---|---|---|
| LH | 3 (−1) | 1 | 1 | 0.0 | 0.0 | −5.3 / +21.5 / −36.0 |
| LH | 4 (0) | 1 | 1 | 0.0 | 0.0 | −0.2 / +23.4 / −41.0 |
| LH | 5 (+1) | 0 | 0 | 20.9 | 0.9 | −9.6 / −2.1 / −42.3 |
| LH | 6 (+2) | 0 | 0 | 41.9 | 4.4 | −15.7 / −19.7 / −38.7 |
| RH | 0 (−1) | 1 | 1 | 0.0 | 0.0 | −3.3 / −4.4 / −54.6 |
| RH | 1 (0) | 1 | 1 | 0.0 | 0.0 | +1.7 / +2.1 / −56.6 |
| RH | 2 (+1) | 0 | 0 | 20.7 | 1.2 | −5.4 / −12.1 / −51.7 |

- **Heel and paw lift together.** At the sample after the last heel-down
  one, the heel is 21 mm up and the paw 0.9 / 1.2 mm up. The roll is at
  most one sample at the engine's 1 mm, inside the 40 ms that
  `hock_at_toeoff` allows.
- **The lift is the knee's, not the hock's.** The knee folds 25° in one
  sample (+23.4 → −2.1 on LH). The hock reference holds or keeps turning
  heel-down (−41.0 → −42.3).

### The policy rolls with its hock

| evaluation | leg | toe-offs | taps | roll frames 0 / 1 / 2 / ≥3 | median |
|---|---|---|---|---|---|
| g4-peak-50 | LH | 213 | 0.02 | 0.00 / 0.02 / 0.45 / 0.50 | 3 |
| g4-peak-50 | RH | 353 | 0.44 | 0.00 / 0.03 / 0.18 / 0.35 | 3 |
| g4-peakc-25 | LH | 213 | 0.05 | 0.00 / 0.18 / 0.39 / 0.37 | 2 |
| g4-peakc-25 | RH | 278 | 0.37 | 0.01 / 0.22 / 0.33 / 0.06 | 2 |

g4-peak-50, LH, frames before the lift:

| frame | heel mm | paw mm | hock ° | hock cmd − meas ° | effort / peak |
|---|---|---|---|---|---|
| −3 | 0.0 | −0.3 | −65.2 | +17.8 | 1.00 |
| −2 | 1.2 | −0.3 | −65.1 | +48.7 | 1.00 |
| −1 | 10.7 | −0.3 | −59.9 | +74.0 | 1.00 |
| 0 (lift) | 34.1 | 0.1 | −49.5 | +74.0 | 1.00 |

- **Half of LH's stances roll for three frames or more** (0.50). Those
  fail `hock_at_toeoff`; the 0.47 that roll for two or fewer pass.
- **The policy pushes off with the hock.** Over its last two frames the
  hock turns 15.6° heel-up (−65.1 → −49.5), with the drive at peak and the
  command 74° beyond it. The clip's hock does not turn there. RH does the
  same (−58.6 → −41.4, at peak).
- **So the roll is the policy's, against the clip.** No clip change is
  needed: the clip already lifts heel and paw within a sample. The lever
  is to make the push-off through the hock in toe stance cost something.

### The candidate term, scored per step (O7)

`roll_brake` charges the hock's heel-up speed while the paw is down and
the heel is up. It uses the left sign, and `dq_*` is in deg/s
(`control_deg_per_s`):

    (chl_down * (1 - khl_down) * (dq_hock_l + |dq_hock_l|) / 2 / 500
     + chr_down * (1 - khr_down) * (-dq_hock_r + |dq_hock_r|) / 2 / 500) / 2

| evaluation | leg | mean per on-ground frame | on roll frames (n) | on other toe frames (n) |
|---|---|---|---|---|
| g4-peak-50 | LH | 0.285 | 0.62 (533) | 0.11 (88) |
| g4-peak-50 | RH | 0.340 | 0.49 (772) | 0.08 (111) |
| g8-gate-25 | LH | 0.044 | 0.09 (627) | 0.04 (2964) |
| g8-gate-25 | RH | 0.034 | 0.05 (843) | 0.04 (1966) |

- It charges the roll **5–6× more than any other toe frame**.
- It pays nothing on a heel-down or flat frame, so unlike g5-toe's
  `toe_stance` (a dead end) it gives no gradient towards a heel-only,
  toes-up stance.
- On the clip it is 0 on every sample, so perfect tracking costs
  nothing.

## 3. g9-roll (queued 04:44:37)

The task is g4-peak's (`leo-flatpeak.py`, the kept task on leo-v02),
plus `roll_brake` at weight −4. That makes 19 terms. The weight is a
literal, because leo is at the 64-parameter cap. The script is
`~/orun13-scripts/leo-roll.py`, and only the reward differs, so the
model XML and the clearance stay leo-v02's.

The run is cold, because the task digest differs: 50 iterations, 4096
envs, seed 0, budget 4,000 s. It goes through `queue_run.py --after
g8-gate --build`, in its own 30G scope (`orun13-q-g9-roll`).

- The build took 3.7 minutes (a reward-only change) and was accepted as
  revision `4f9f48f9` (project git `963c8e4`).
- It launched at 04:48:21.
- Checked in the bundle: the model XML is byte-identical to g4-peak's,
  and so is the clip. `roll_brake` is the only term added or changed.
- Iteration 10 came at 05:00:58, 757 s after launch. At about 55 s an
  iteration, 50 should finish near 2,960 s, inside the budget.

**Judge at 25 against g4-peak-25, and at 50 against g4-peak-50.**

At 25, stop it if LH's roll of three frames or more is no lower than
g4-peakc-25's 0.37 **and** the speed is below 0.94 m/s.

Keep it at 50 only if all four hold:
- LH's roll of three frames or more falls below g4-peak-50's 0.50;
- `hock_at_toeoff` rises on LH above 0.43, and holds on RH at 0.21 or
  more;
- toes-up is at most 0.10 on each leg;
- the speed is at least 2.2 m/s.

**Risk.** The push-off is a speed source. With the hock charged, the
policy may lift by the knee as the clip does, or it may slow down. The
speed part of the rule catches the second.
