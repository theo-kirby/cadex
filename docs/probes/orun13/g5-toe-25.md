# orun13 P1: g5-toe at 25 puts the heels down by lifting the paws; stopped; g4-peakf takes the slot

Verified against source: 2026-10-21. Frozen evidence (orun13, iteration 10).

## g5-toe at 25 (`gallop.000025.cxpolicy`, sha256 `194fcf9f`)

g5-toe is g4-peak's task plus `toe_stance` at −10, 19 terms
(`g4-peakc-25.md`), on revision `019d8743`, trained cold for 50
iterations at 4096 envs with seed 0 and a 4,200 s budget.

- **Timing.** Iteration 2 came at 301 s and iteration 10 at 682 s. That
  is **about 48 s an iteration** after a ~110 s first iteration. 50
  iterations take about 2,500 s, so the 4,200 s budget does not bind.
- **How it was judged.** At 25, as g4-peak-25 was: `gallop_spec` on seeds
  1001–1010, on the CPU (`orun11/judge.py`, evaluation `g5-toe-25`),
  read with `orun12/legs.py`, `orun13/spine_foot.py`, `orun13/p2_lag.py`
  and `orun13/toeoff_term.py`.
- **The comparison.** g4-peak-25 is g5-toe's task without the term, at
  the same budget point.

| evaluation | pass | top 2 s m/s min / med / max | straight (°) | hock_down LH / RH | at toe-off LH / RH | heel-down frames flat LH / RH | toes-up LH / RH | heel mm in stance LH / RH | no_tap | every_stride | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g4-peak-25 | 0/10 | 0.81 / 0.94 / 1.16 | 7/10 (22.3) | 0.13 / 0.14 | 0.10 / 0.00 | 0.49 / 0.73 | 0.51 / 0.27 | 9 / 10 | 1/10 (1.93) | 9/10 | −168 / −198 | 203 / 199 | 2.89 / 4.28 | 0.69, 0.040 | 1.88 (j_tail1) | 0.00 | 2.1 |
| **g5-toe-25** | 0/10 | 0.59 / **0.81** / 1.06 | 6/10 (24.0) | **0.37 / 0.41** | **0.52 / 0.42** | 0.37 / 0.31 | **0.63 / 0.69** | 2 / 2 | 0/10 (1.59) | 10/10 | −216 / −227 | 143 / 140 | 2.67 / 3.67 | 0.21, 0.000 | 1.78 (j_spine) | 0.00 | 2.1 |

P1 is 0/10. The worst-leg medians are `hock_down` 0.349 (1/10 seeds
pass) and `hock_at_toeoff` 0.402 (bar 1.0).

- **Footfalls (`p2_lag.py`, O3).** The fore lag is 0.333 of a cycle, the
  hind lag 0.134. 3/10 seeds are rotary. There is no flight (0.000 s), and
  the stride is 140 mm: this is a shuffle, not a gallop.
- **Spine (`spine_foot.py`, O4).** It moves 24.2° a stride over both
  joints, j_spine runs from −26° to about +2°, it spends 0.10 of the time
  at a stop, and the cable gap is at most 0.33°.
- **Torque (O6).** `j_spine` runs at 1.78× rated RMS, with a peak margin
  of 0.00.
- **Loop gap (O9).** 2.1 mm.

### What the term did (`toeoff_term.py`)

| evaluation | leg | toe-stance share | of which landing / roll / tap | toe-offs through heel / rolled / tap |
|---|---|---|---|---|
| g4-peak-25 | LH | 0.75 | 0.01 / 0.72 / 0.20 | 0.22 / 0.56 / 0.21 |
| g4-peak-25 | RH | 0.83 | 0.08 / 0.46 / 0.46 | 0.02 / 0.46 / 0.53 |
| g5-toe-25 | LH | 0.39 | 0.00 / 0.65 / 0.01 | 0.62 / 0.37 / 0.01 |
| g5-toe-25 | RH | 0.32 | 0.12 / 0.71 / 0.10 | 0.47 / 0.44 / 0.09 |

**The term moved what it charges.** Toe-stance frames halved, and the
taps all but went. But the frames went to the risk named at launch: a
heel stance with the paw in the air. 0.63 / 0.69 of the heel-down frames
are toes-up, more than g4-peak-25's 0.51 / 0.27.

The term pays nothing for a heel-only frame and charges a toe-stance
frame. The peaked `heel_pitch` charges toes-up, but at 25 iterations it
does not outweigh that. A heel-only stance also passes `hock_at_toeoff`
trivially. So the rise in toe-off share is partly the defect O2 forbids,
not progress towards it.

## Decision

Against the keep rule in `g4-peakc-25.md`:

| part | needed | result | met? |
|---|---|---|---|
| `hock_at_toeoff` | above 0.10 / 0.00 | 0.52 / 0.42 | yes |
| toes-up, each leg | at most 0.10 | 0.63 / 0.69 | **no** |
| speed | at least 0.94 m/s | 0.81 m/s | **no** |

**g5-toe is stopped** (`request_stop`, 01:40, 32 iterations). After 25
the trainer's episode length fell from 3,277 to 445 steps. The term is
a dead end at −10. A heavier weight, the critic's first fallback, would
pay the heel-only stance even more, so it was not tried.

- **The build.** g5-toe was left running for four minutes while the
  project was rebuilt from `~/orun13-scripts/leo-flatpeak.py`, which
  is g4-peak's script, project git `dbf6de7`. The rebuild accepted
  `b4680361` again, the revision g4-peak and g4-peakc trained on. Then
  g5-toe was stopped.
- **A launch mistake, caught.** The first queue ran the build under
  `ulimit -v 16000000`, which a trainer started from the same queue would
  inherit. That queue was killed after the build and before any launch,
  and re-queued without the cap.

## Next screen: `g4-peakf` (launched 01:41)

This is the critic's second fallback. g4-peakc-25 (`c7e69d91`, the best
P1 checkpoint so far) is warm-started on its own task (`b4680361`, task
sha256 `25b851d3`) at learning rate **3e-5**, with 5 critic-only
iterations. It runs 50 iterations at 4096 envs, seed 0, budget 3,300 s.

The question is whether a fine-tune rate keeps g4-peakc-25's heels
(0.47 / 0.28) and toe-off (0.61 / 0.48) while its RH toes-up (0.18)
falls. At the default rate, the first actor update lost the policy
(31.2 → 22.8 a step) before it relearned it (`grand-heron-3034`).

**Judge at 25. Keep only if:**
- toes-up is at most 0.10 on each leg;
- heels are at least 0.47 / 0.28;
- `hock_at_toeoff` is at least 0.61 / 0.48;
- speed is at least 2.65 m/s.

**Its first ten iterations, timed.** Iteration 10 came at 671 s, and the
trainer then projected about 2,380 s more: some 3,050 s for 50, against
the 3,300 s budget. That margin is 8%, short of O8's 20%. The budget
was set before this timing, from g4-peak's ~54 s an iteration, and a
registered run's budget cannot be raised. If the run ends on its budget,
iteration 25 still decides it.

The fine-tune rate holds the policy through the first actor updates:
iterations 5–10 read 33.5 → 32.6 a step, against g4-peakc's
31.2 → 22.8 at the default rate.
