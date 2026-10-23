# orun13 P1/O1: g7c-hock75 fails its rule at 25 and is stopped; g8-gate gates heel_pitch on the paw's contact

Verified against source: 2026-10-21. Frozen evidence (orun13, iteration 14).

## g7c-hock75 at 25 (`gallop.000025.cxpolicy`)

g7c-hock75 is g7-hock75-50 continued on leo-v02.1 (`8eb6aed6`, hind hock
heel-side stop −75°): +50 iterations, 5 of them critic-only, 4096 envs. It
launched at 03:48:12, and checkpoint 25 was written at 04:13.

It was judged as before:
- `gallop_spec` on seeds 1001–1010, on the CPU (`orun11/judge.py`,
  evaluation `g7c-hock75-25`, 37 s);
- read with `orun12/legs.py`, `orun13/spine_foot.py` and
  `orun13/hind_reach.py`;
- the rod gaps come from the evaluation's `closure` block.

It is compared with g4-peakc-25: the same recipe on leo-v02, at the same
budget point.

| evaluation | pass | top 2 s m/s min / med / max | straight | hock_down (seeds, worst-leg median) | hock_down LH / RH | at toe-off LH / RH | flat / toes-up LH | flat / toes-up RH | no_tap | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g4-peakc-25 | 0/10 | 2.57 / 2.65 / 2.74 | 8/10 | 0/10, 0.285 | 0.47 / 0.28 | 0.61 / 0.48 | 0.90 / 0.10 | 0.82 / 0.18 | 0/10 (1.54) | 464 / 103 | 1075 / 858 | 2.39 / 3.17 | 0.160 | 1.91 (j_spine) | 0.00 | 3.8 |
| **g7c-hock75-25** | 0/10 | 2.55 / **2.63** / 2.75 | 10/10 | **7/10, 0.416** | 0.42 / 0.51 | 0.38 / 0.62 | 0.86 / 0.14 | 0.85 / 0.15 | 0/10 (2.01) | 484 / 36 | 1080 / 1055 | 2.56 / 2.44 | 0.200 | 2.04 (j_spine) | 0.00 | 4.4 |

- **P1 is 0/10.** `hock_down` passes on 7/10 seeds, the most yet.
  `hock_at_toeoff` passes on none (worst-leg median 0.383, bar 1.0).
- **The heel share has swapped sides.** At 50, g7-hock75 had LH 0.46 and
  RH 0.41; at 25 here, LH is 0.42 and RH 0.51. The same happens to
  toe-off: 0.36 / 0.67 at 50, 0.38 / 0.62 here.
- **Footfalls.** 49/49 strides are rotary, but 147 strides are tied
  within a frame, so the order is mostly unresolved.
- **Spine (`spine_foot.py`).** 54.6° a stride over both joints. It sits
  at a stop 0.00 of the time, and the cable gap is at most 0.30°.
- **Torque (O6).** The worst drive is `j_spine` at 2.04× rated, with a
  peak margin of 0.00.
- **Rod loops (O9), max (median), in mm.**
  - Front L: 4.36 (0.31).
  - Front R: 2.75 (0.36).
  - Hind L: 1.15 (0.13).
  - Hind R: 1.35 (0.23).

### The hock in stance (`hind_reach.py`)

| leg | class | frames | hock ° | margin to stop ° | at stop | hock cmd − meas ° | effort/peak med / p95 |
|---|---|---|---|---|---|---|---|
| LH | flat | 407 | −67.2 | 7.8 | 0.10 | +37.9 | 1.00 / 1.00 |
| LH | toes-up | 68 | −65.3 | 9.7 | 0.00 | +21.1 | 1.00 / 1.00 |
| LH | toe | 599 | −54.4 | 20.6 | 0.00 | +79.4 | 1.00 / 1.00 |
| RH | flat | 503 | −73.6 | 1.4 | **0.55** | +6.8 | 0.71 / 1.00 |
| RH | toes-up | 87 | −61.8 | 13.2 | 0.00 | −4.0 | 0.12 / 0.44 |
| RH | toe | 507 | −60.8 | 14.2 | 0.08 | +77.1 | 1.00 / 1.00 |

The RH flat foot now stands on the −75° stop on 0.55 of its frames. As at
50, the hock's command is heel-up of the measured angle, at peak, through
flat and toe stance (`hock-drive.md` reads its sign).

### Decision: against the rule written in `g7-hock75.md`

| part | needed | result | met? |
|---|---|---|---|
| heels | at least 0.47 / 0.28 | 0.42 / 0.51 | **no** (LH) |
| toe-off | at least 0.61 / 0.48 | 0.38 / 0.62 | **no** (LH) |
| toes-up per leg | at most 0.10 | 0.14 / 0.15 | **no** (both) |
| speed | at least 2.4 m/s | 2.63 m/s | yes |
| flat frames on the stop | below 0.29 / 0.29 | 0.10 / **0.55** | **no** (RH) |
| each hind rod | under 2 mm | 1.15 / 1.35 mm | yes |
| loop gap | at most 3.8 mm | **4.4 mm** (front L) | **no** |

**g7c-hock75 fails five of seven parts.** It was stopped at 04:14
(`loop.request_stop`), and leo-v02.1 stays rejected (no `revision
restore 18`).

The wider stop has had two screens now. Each moved the heel share
between the legs without lifting both, and each put one flat foot on the
new stop. The hock's travel is closed as a lever for this run.

## The hock drive: written up, not built

The O1 write-up the critic asked for is in `hock-drive.md`. The drive is
at peak pushing the heel **up**, and the weight on the foot keeps it
down. More torque would therefore be expected to make `hock_at_toeoff`
worse, and a reducing ratio would trade push-off for it. Neither is
built.

## g8-gate (launched 04:15:34): heel_pitch paid wherever a hind paw stands

### Why this lever

The question was where `heel_pitch` pays. It pays a flat sole only while
the clip has that hind paw in stance (`ref_lh_down`): 5 of the clip's 21
samples, about 100 ms. `stance_gate.py` (new) fits each seed's clip clock
from the paws' measured contact (match 0.81–0.93), then counts the frames
outside that window.

| evaluation | leg | stance frames med (clip) | on-ground in clip / outside | toe frames in clip / outside | toe-offs | last 40 ms wholly outside clip stance |
|---|---|---|---|---|---|---|
| g4-peak-50 | LH | 6 (5) | 0.73 / 0.27 | 0.88 / 0.12 | 212 | 0.00 |
| g4-peak-50 | RH | 4 (5) | 0.60 / 0.40 | 0.50 / 0.50 | 356 | **0.46** |
| g4-peakc-25 | LH | 5 (5) | 0.81 / 0.19 | 0.92 / 0.08 | 212 | 0.00 |
| g4-peakc-25 | RH | 3 (5) | 0.62 / 0.38 | 0.49 / 0.51 | 279 | 0.35 |
| g7-hock75-50 | LH | 5 (5) | 0.81 / 0.19 | 0.95 / 0.05 | 213 | 0.00 |
| g7-hock75-50 | RH | 4 (5) | 0.77 / 0.23 | 0.61 / 0.39 | 219 | 0.10 |
| g7c-hock75-25 | LH | 5 (5) | 0.85 / 0.15 | 0.95 / 0.05 | 212 | 0.00 |
| g7c-hock75-25 | RH | 5 (5) | 0.76 / 0.24 | 0.49 / 0.51 | 216 | 0.03 |

- **RH's off-clock stance is unpaid.** On g4-peak-50, half of RH's
  toe-stance frames lie outside the clip's stance. For 0.46 of its
  toe-offs, the whole `hock_at_toeoff` window lies outside it, where a flat
  foot earns nothing. These are the taps that `toeoff_term.py` found.
- **LH's roll is inside the clip's stance.** 0.88 of LH's toe frames fall
  there, and none of its toe-off windows lie wholly outside. The peaked
  `heel_pitch` already charges it, so the gate change does not touch it.

### The change

On leo-v02 (revision `86c15551`, project git `7dab0f5`,
`~/orun13-scripts/leo-gate.py`), `heel_pitch`'s gate changes from
`ref_down` to the clip's stance *or* the paw's own contact:

    ref_lh_down + chl_down - ref_lh_down * chl_down     (and RH)

Its weight (10) and its peaked pitch kernel are g4-peak's. No term is
added; it is still 18 terms.

The bundle's model XML is byte-identical to g4-peak's, so no clearance
pair can change. The clip is identical too, and `heel_pitch` is the only
reward that differs.

It runs cold, because the task digest differs: 50 iterations, 4096 envs,
seed 0, budget 4,000 s. It is queued through `queue_run.py --after
g7c-hock75 --build`, in its own 30G scope.
Iteration 10 came at 04:28:00, 746 s after launch, the same as
g7-hock75's. At about 54 s an iteration, 50 should finish near 2,700 s,
inside the budget.

**Judge at 25 against g4-peak-25, and at 50 against g4-peak-50.** Keep
it only if, at 50:
- RH's toe-offs whose window is wholly outside the clip's stance fall
  below g4-peak-50's 0.46 (`stance_gate.py`);
- `hock_at_toeoff` rises on RH above 0.21, and LH holds at 0.43 or more;
- toes-up stays at or below 0.10 on each leg;
- the speed is at least 2.2 m/s.

At 25, stop it if `hock_at_toeoff` and the speed both fall below
g4-peak-25's (0.10 / 0.00, 0.94 m/s).

**Risk.** The new pay is earned by standing, so the policy may lengthen
its stance off the clip's schedule (`track_contact` prices that at 4),
or stand flat and slow. The speed part of the rule catches that.
