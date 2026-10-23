# orun13 P1/O1: g7-hock75 lifts both heels but fails its keep rule at 50; leo-v02.1 is not kept

Verified against source: 2026-10-21. Frozen evidence (orun13, iteration 13).

g7-hock75 is g4-peak's task (`leo-flatpeak.py`, 18 terms) run cold on
leo-v02.1 (revision `8eb6aed6`, project git `54fbf22`). The only change
from leo-v02 is the hind hock's heel-side stop, moved from −70° to −75°
(`g6-swank-25.md`). The screen used 4096 envs and seed 0.
- It launched at 03:01:57.
- Iteration 10 came at 746 s and iteration 25 at about 1,550 s. It finished
  50 at 2,689 s (about 54 s an iteration), inside its 4,000 s budget.

It was judged as the earlier screens were:
- `gallop_spec` on seeds 1001–1010, on the CPU (`orun11/judge.py`;
  evaluations `g7-hock75-25` and `g7-hock75-50`);
- read with `orun12/legs.py`, `orun13/spine_foot.py`, `orun13/p2_lag.py`
  and `orun13/hind_reach.py`;
- the rod gaps per leg come from each evaluation's `closure` block.

## At 25 (`gallop.000025.cxpolicy`): direction only, against g4-peak-25

| evaluation | pass | top 2 s m/s min / med / max | completes | straight | hock_down LH / RH | at toe-off LH / RH | flat / toes-up LH | flat / toes-up RH | flight s | worst RMS/rated | peak margin | front rod gap max L / R mm | hind rod gap max L / R mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g4-peak-25 | 0/10 | 0.81 / 0.94 / 1.16 | 9/10 | 7/10 | 0.13 / 0.14 | 0.10 / 0.00 | 0.49 / 0.51 | 0.73 / 0.27 | 0.040 | 1.88 (j_tail1) | 0.00 | 1.94 / 2.10 | 0.92 / 1.16 |
| g7-hock75-25 | 0/10 | 0.61 / 0.95 / 1.42 | 6/10 | 0/10 | **0.26 / 0.17** | 0.13 / 0.04 | 0.75 / 0.25 | 0.93 / 0.07 | 0.000 | 2.18 (j_tail1) | 0.00 | 2.47 / 1.70 | 0.87 / 1.75 |

The heels rose on both legs, and the speed held (0.95 against 0.94 m/s).
The stop rule was "stop if heels and speed both fall", so the run went on
to 50. It completes only 6/10 seeds and runs straight on none. The spine
sits at a stop 0.23 of the time.

## At 50 (`gallop.cxpolicy`, sha256 `3ad0315a`), against g4-peak-50 (`02f16f15`)

| evaluation | pass | top 2 s m/s min / med / max | straight | hock_down (seeds, worst-leg median) | hock_down LH / RH | at toe-off LH / RH | flat / toes-up LH | flat / toes-up RH | heel mm in stance LH / RH | no_tap | overreach (seeds, mm LH / RH) | stride mm LH / RH | touchdown Hz LH / RH | flight s | worst RMS/rated | peak margin |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g4-peak-50 | 0/10 | 2.40 / 2.43 / 2.49 | 10/10 | 0/10, 0.218 | 0.44 / 0.22 | 0.43 / 0.21 | 0.91 / 0.09 | 0.94 / 0.06 | 2 / 14 | 0/10 (1.68) | 10/10, 416 / 141 | 978 / 868 | 2.33 / 4.00 | 0.160 | 1.80 (j_spine) | 0.00 |
| **g7-hock75-50** | 0/10 | 2.51 / **2.60** / 2.67 | 10/10 | **6/10, 0.406** | **0.46 / 0.41** | 0.36 / **0.67** | 0.93 / 0.07 | 0.79 / **0.21** | 2 / 3 | 0/10 (2.01) | 7/10, 396 / 7 | 1045 / 1035 | 2.44 / 2.44 | 0.180 | 2.07 (j_spine) | 0.00 |

- **P1 is 0/10.** `hock_down` passes on 6/10 seeds, the first time on
  leo; the worst-leg median is 0.406 against a bar of 0.40.
  `hock_at_toeoff` passes on no seed (worst-leg median 0.362, bar 1.0).
- **Left and right (O5).**
  - The heel shares are 0.46 / 0.41 (13% apart; g4-peak-50 was 51%).
  - Stride is 1,045 / 1,035 mm and touchdown rate 2.44 / 2.44 Hz, the
    most even pair yet.
  - RH's sole folds toes-up on 0.21 of its heel-down frames.
- **Footfalls (`p2_lag.py`, O3).**
  - Fore lag is 0.048 of a cycle (together 0.62); hind lag is 0.000
    (together 0.76).
  - 0/10 seeds are rotary. It is a bound with flight (0.180 s), not a
    rotary gallop.
- **Spine (`spine_foot.py`, O4).**
  - 65.2° a stride over both joints: g4-peakc-25 had 32.2°.
  - It sits at a stop 0.01 of the time.
  - The cable gap is at most 0.39°.
- **Torque (O6).**

  | drive | RMS/rated g4-peak-50 → g7-hock75-50 | share at the clamp |
  |---|---|---|
  | `j_spine` | 1.80 → 2.07 | 0.27 → 0.53 |
  | `j_hock_l` | 1.24 → 1.26 | 0.20 → 0.25 |
  | `j_hock_r` | 1.17 → 1.04 | 0.20 → 0.14 |

  The peak margin is 0.00 (every drive stays at or under peak).
- **Rod loops (O9), max over the window (median).**

  | rod | g4-peak-50 | g7-hock75-50 |
  |---|---|---|
  | front L `j_frodbot_l` | 3.11 (0.17) | **4.59** (0.31) |
  | front R `j_frodbot_r` | 3.84 (0.19) | 3.30 (0.34) |
  | hind L `j_rodbot_l` | 1.22 (0.16) | 1.50 (0.12) |
  | hind R `j_rodbot_r` | 1.22 (0.16) | 1.48 (0.17) |

  The crank works 5° nearer the rod at the new stop (`g6-swank-25.md`,
  risk 2). The hind rod gaps rose about 0.3 mm but stay under 2 mm.

### The hock in stance (`hind_reach.py`)

| leg | class | g4-peak-50 frames, hock °, margin °, at stop | g7-hock75-50 frames, hock °, margin °, at stop | g7 hock cmd − meas ° | g7 effort/peak med / p95 |
|---|---|---|---|---|---|
| LH | flat | 518, −62.5, 7.5, 0.29 | 522, −66.0, 9.0, **0.22** | +33.3 | 1.00 / 1.00 |
| LH | toe | 621, −55.8, 14.2, 0.11 | 578, −54.7, 20.3, 0.01 | +79.4 | 1.00 / 1.00 |
| RH | flat | 235, −55.8, 14.2, 0.08 | 320, −69.1, 5.9, **0.30** | +13.0 | 0.88 / 1.00 |
| RH | toe | 883, −50.8, 19.2, 0.10 | 484, −55.3, 19.7, 0.02 | +53.1 | 1.00 / 1.00 |

With 5° more travel, both flat feet stand further heel-down: LH by 3.5°,
RH by 13.3°. RH now stands 5.9° from the new stop, with 0.30 of its flat
frames on it.
- **The stop still binds.** Given room, the flat foot takes it and lands
  on the new stop.
- **But the stop does not bind alone.** In flat and toe stance the hock
  drive is at peak (median effort 1.00 on three of the four rows). Its
  command asks 13–79° more hock than the joint holds. The drive cannot hold
  the commanded heel-down hock under stance load.

### Decision: against the keep rule written in `g6-swank-25.md`

| part | needed | result | met? |
|---|---|---|---|
| heels rise on both legs | above 0.44 / 0.22 | 0.46 / 0.41 | yes |
| flat frames on the hock's heel-side stop fall | below 0.29 / 0.08 | 0.22 / **0.30** | **no** (RH) |
| toes-up per leg | at most 0.10 | 0.07 / **0.21** | **no** (RH) |
| speed | at least 2.2 m/s | 2.60 m/s | yes |
| loop gap no worse | at most 3.8 mm | **4.6 mm** (front L) | **no** |
| each hind rod | under 2 mm | 1.50 / 1.48 mm | yes |

**leo-v02.1 fails its keep rule on three parts and is not kept.** The
project's accepted revision is restored to `b4680361`: leo-v02 with
g4-peak's task, ordinal 15 in the stored trail, the revision g4-peak and
g4-peakc trained on.
- The `leo-v02.1` tag stays in the project's git as a record.
- `leo-v02` is untouched.

What the screen does show, for the record and for R1:
- **The stop binds, but only together with the hock drive's peak.** The
  wider stop raised `hock_down` to 6/10 seeds (RH 0.22 → 0.41) at a higher
  speed (2.43 → 2.60 m/s).
- **The cost.** The RH foot rode onto the new stop, and 0.21 of its
  heel-down frames folded toes-up.
- So the hock stop was **not "not binding"**. A wider stop is not enough
  on its own, because the hock drive is at peak through the stance.
- **The next model lever is the hock drive's torque, or its ratio through
  the push-rod.** The stop alone is not it. Any such change needs its own
  O1 write-up.
- One cold seed per model: g4-peak's left/right split was shown to be the
  policy's handedness (`scarlet-hill-3979`). So the per-leg parts of this
  rule (RH stop share, RH toes-up) carry seed-to-seed noise that a single
  cold screen does not settle.

## g7c-hock75: the warm follow-on on v02.1, already running

Queued at 03:21 (before the write-up, O8) and launched at 03:48:12 when
g7's slot freed, on `8eb6aed6`:
- g7-hock75-50 warm on its own task, +50 iterations;
- 5 of them critic-only, at the default learning rate;
- 4096 envs, budget 4,500 s.

It is g4-peakc's recipe on v02.1, so its 25 pairs with g4-peakc-25 (2.65
m/s, where 0.29 / 0.29 of the flat frames sat on the old stop). That is the
speed at which the stop should matter most.

It trains on its own bundle, so restoring the project revision does not
touch it. It runs to 25 so the GPU stays busy while the next screen on
leo-v02 is chosen.

**Rule for g7c at 25, written before it is judged.** v02.1 is restored
(`cadex revision restore 18`) only if, against g4-peakc-25, all of these
hold:
- heels at least 0.47 / 0.28;
- toe-off at least 0.61 / 0.48;
- toes-up at most 0.10 per leg;
- speed at least 2.4 m/s;
- flat frames on the stop below 0.29 / 0.29;
- each hind rod under 2 mm;
- the loop gap at most 3.8 mm.

Otherwise g7c is stopped at 25, and leo-v02.1 stays rejected.
