# orun13 P1: g4-peakc at 25 lifts both heels, fails its keep rule on RH toes-up; g5-toe takes the slot

Verified against source: 2026-10-21. Frozen evidence (orun13, iteration 9).

## g4-peakc at 25 (`gallop.000025.cxpolicy`, sha256 `c7e69d91`)

g4-peakc is g4-peak-50 warm (`g4-peak-50.md`): the same task and revision
`b4680361`, +50 iterations with 5 critic-only, 4096 envs, the default
learning rate. It was judged at 25 as g4-peak-50 was: `gallop_spec`,
seeds 1001–1010, on the CPU (`orun11/judge.py`, evaluation
`g4-peakc-25`; `orun12/legs.py`, `orun13/spine_foot.py`,
`orun13/p2_lag.py`, and the new `orun13/toeoff_term.py`).

| evaluation | pass | top 2 s m/s min / med / max | straight (°) | hock_down LH / RH | at toe-off LH / RH | heel-down frames flat LH / RH | toes-up LH / RH | heel mm in stance LH / RH | no_tap | every_stride | overreach | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g4-peak-50 | 0/10 | 2.40 / 2.43 / 2.49 | 10/10 (19.8) | 0.44 / 0.22 | 0.43 / 0.21 | 0.91 / 0.94 | 0.09 / 0.06 | 2 / 14 | 0/10 (1.68) | 10/10 | 10/10 (141) | 416 / 141 | 978 / 868 | 2.33 / 4.00 | 1.00, 0.160 | 1.80 (j_spine) | 0.00 | 3.8 |
| **g4-peakc-25** | 0/10 | 2.57 / **2.65** / 2.74 | **8/10** (13.6) | **0.47 / 0.28** | **0.61 / 0.48** | 0.90 / 0.82 | 0.10 / **0.18** | 1 / 8 | 0/10 (1.54) | 10/10 | 10/10 (103) | 464 / 103 | 1075 / 858 | 2.39 / **3.17** | 1.00, 0.160 | 1.91 (j_spine) | 0.00 | 3.8 |

P1 is still 0/10: worst-leg medians `hock_down` 0.285 (bar 0.40),
`hock_at_toeoff` 0.482 (bar 1.0). Seed 1001: 2.73 m/s, `hock_down`
0.297, `hock_at_toeoff` 0.464, `no_tap` 1.54.

- **Footfalls (`p2_lag.py`, O3).** Fore lag 0.192 of a cycle (about
  73 ms at 2.63 strides/s), hind 0.031 (about 12 ms, together 0.69);
  0/10 seeds rotary.
- **Spine (`spine_foot.py`, O4).** 32.2° a stride (both joints), 0.00 at a
  stop, j_spine −18.7..−24.0° to +7.5..+13.2°, cable gap at most 0.47°.
- **Torque (O6).** `j_spine` 1.91× rated RMS, peak margin 0.00.
- **Q2 (O9).** The loop gap is 3.8 mm, as on g4-peak-50. That is over
  O9's 2 mm, so this policy fails Q2, as g3-flat-50 (4.5 mm) and
  g4-peak-50 do. It stays an open Q2 item.
- **The curve.** At the first actor update (iteration 6) the trainer's
  reward fell from 31.2 to 22.8 a step, and the episode length from
  2,341 to 267. It was back at 33.4 by 24. g2-heel5c did the same
  (31.3 → 24.4 → 33.3). A default-rate continuation loses the policy
  before it relearns it, which is the fine-tune lesson of
  `grand-heron-3034`.

### Where the toe-off fails (`toeoff_term.py`)

A toe-off passes `hock_at_toeoff` if the heel is down within 1 mm in the
stance's last 40 ms: the lift frame and the two before it. Each toe-off
is either through the heel, rolled off the toes after a heel-down
stance, or a tap that never laid the heel. A toe-stance frame has the
paw down and the heel up.

| evaluation | leg | toe-stance share of on-ground frames | of which landing / roll / tap | toe-offs | through heel / rolled / tap | median roll frames |
|---|---|---|---|---|---|---|
| g4-peak-50 | LH | 0.52 | 0.03 / 0.91 / 0.03 | 217 | 0.47 / 0.52 / 0.02 | 3 |
| g4-peak-50 | RH | 0.78 | 0.04 / 0.63 / 0.34 | 356 | 0.21 / 0.35 / 0.44 | 3 |
| g4-peakc-25 | LH | 0.50 | 0.03 / 0.91 / 0.06 | 215 | 0.58 / 0.37 / 0.05 | 3 |
| g4-peakc-25 | RH | 0.68 | 0.03 / 0.56 / 0.41 | 279 | 0.58 / 0.06 / 0.37 | 3 |
| g3-flat-50 | LH | 0.51 | 0.04 / 0.87 / 0.05 | 244 | 0.54 / 0.43 / 0.03 | 3 |
| g3-flat-50 | RH | 0.51 | 0.00 / 0.85 / 0.15 | 347 | 0.67 / 0.22 / 0.11 | 3 |

- **The LH fails by rolling.** It rolls onto its toes for a median of 3
  frames before the lift, one frame more than the 40 ms window allows.
- **The RH fails by tapping.** On g4-peakc-25, 0.37 of its toe-offs
  are taps with no heel, and only 0.06 are rolls.
- **Landing is not the problem.** Toes-first frames before the heel
  comes down are 0–6% of the toe-stance frames. A charge on toe-stance
  frames therefore lands almost entirely on the roll and the taps, the
  two things `hock_at_toeoff` fails on.

## Decision

Against the keep rule in `g4-peak-50.md`:

| part | needed | result | met? |
|---|---|---|---|
| toes-up, each leg | at or below 0.10 | 0.10 / 0.18 | no: RH 0.18 |
| heel shares | at least 0.44 / 0.22 | 0.47 / 0.28 | yes |
| RH tap or speed | RH rate towards LH's, or speed towards 2.80 | 3.17 Hz (from 4.00); 2.65 m/s (from 2.43) | yes |

**g4-peakc is stopped at 26 iterations** (`request_stop`, 01:07). The
heels did not fall: this is the run's best P1 checkpoint yet, with
heels 0.47 / 0.28 and toe-off 0.61 / 0.48. But the RH toes-up foot that
g4-peak removed is coming back (0.06 → 0.18), the rule was written to
catch exactly that, and its slot buys the toe-off lever this table
points to. `straight` also slipped from 10/10 to 8/10. The checkpoint
stays on disk as the comparison for the next screen.

## Next screen: `g5-toe` (launched 01:08)

g5-toe is g4-peak's task (revision `019d8743`, project git `0ab2087`,
`~/orun13-scripts/leo-toe.py`) with one added term, 19 in all:

    toe_stance = (chl_down * (1 - khl_down) + chr_down * (1 - khr_down)) / 2,  weight -10

It runs cold, because the task digest differs and the trainer refuses to
warm-start across one. It is a 50-iteration screen at 4096 envs, seed 0,
budget 4,200 s, so it compares directly with g4-peak-50. The model XML
is byte-identical to g4-peak's, so no clearance pair changes.

**Scored per step before the launch (O7).** On g4-peak-50's traces the
term reads 0.167 a step. That is −1.67 at weight −10, about the size of
`heel_pitch`'s pay and 5% of the trainer's 31 a step. Removing one roll
frame a stance would recover about a third of it.

On the clip's kinematic replay the term reads 0.008. A kinematic pose
seldom presses the floor, though, and the bundle's own `plantigrade`
reads 0 there too. So that number bounds the term's cost to perfect
tracking but does not measure it.

**Judge at 25. Keep only if:**
- `hock_at_toeoff` rises above g4-peak-25's 0.10 / 0.00 (the same
  budget point) and heads towards g4-peakc-25's 0.61 / 0.48;
- toes-up stays at or below 0.10 on each leg;
- speed is at least g4-peak-25's 0.94 m/s.

**Risks.** The policy could avoid the charge by lifting the foot early,
which shortens stance and costs speed. It could also stand on its heel
with the toes up, which the peaked `heel_pitch` already charges.
