# orun13 P1: g4-peakf at 25 fails its keep rule; the hind foot is not reach-limited; g6-swank takes the slot

Verified against source: 2026-10-21. Frozen evidence (orun13, iteration 11).

## g4-peakf at 25 (`gallop.000025.cxpolicy`, sha256 `781e1722`)

g4-peakf is g4-peakc-25 (`c7e69d91`) warm on its own task (`b4680361`,
task sha256 `25b851d3`), at learning rate 3e-5 with 5 critic-only
iterations, 4096 envs, seed 0 (`g5-toe-25.md`). It ran at about 60 s an
iteration. It was judged at 25 as g4-peakc-25 was: `gallop_spec` on seeds
1001–1010, on the CPU (`orun11/judge.py`, evaluation `g4-peakf-25`), read
with `orun12/legs.py`, `orun13/spine_foot.py`, `orun13/p2_lag.py`,
`orun13/toeoff_term.py` and the new `orun13/hind_reach.py`.

| evaluation | pass | top 2 s m/s min / med / max | completes | upright | straight | hock_down LH / RH | at toe-off LH / RH | heel-down frames flat LH / RH | toes-up LH / RH | heel mm in stance LH / RH | no_tap | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g4-peakc-25 | 0/10 | 2.57 / 2.65 / 2.74 | 10/10 | 10/10 | 8/10 | 0.47 / 0.28 | 0.61 / 0.48 | 0.90 / 0.82 | 0.10 / 0.18 | 1 / 8 | 0/10 (1.54) | 464 / 103 | 1075 / 858 | 2.39 / 3.17 | 1.00, 0.160 | 1.91 (j_spine) | 0.00 | 3.8 |
| **g4-peakf-25** | 0/10 | 2.40 / **2.55** / 2.63 | **8/10** | **8/10** | 9/10 | 0.46 / **0.19** | 0.61 / **0.33** | 0.73 / 0.94 | **0.27** / 0.06 | 2 / 14 | 0/10 (1.56) | 430 / 86 | 1023 / 826 | 2.33 / 3.22 | 1.00, 0.160 | 1.94 (j_spine) | 0.00 | 4.0 |

P1 is 0/10. The worst-leg medians are `hock_down` 0.195 (bar 0.40) and
`hock_at_toeoff` 0.333 (bar 1.0). The per-seed heel shares are LH
0.38–0.53 and RH 0.18–0.26.

- **Footfalls (`p2_lag.py`, O3).** The fore lag is 0.250 of a cycle and
  the hind lag 0.022, so the hind pair lands together on 0.72 of strides.
  1/10 seeds are rotary. Flight is 0.160 s.
- **Spine (`spine_foot.py`, O4).** It moves 35.1° a stride over both
  joints and spends 0.00 of the time at a stop. The cable gap is at most
  0.64°.
- **Torque (O6).** `j_spine` runs at 1.94× rated RMS, with a peak margin
  of 0.00. The hock is at peak through the stance (below).
- **Loop gap (O9).** 4.0 mm, on the front rods: `j_frodbot_l` 4.02 and
  `j_frodbot_r` 3.77. The hind rods are at 1.1 / 2.3 mm. Q2 stays open.
- **Toe-offs (`toeoff_term.py`).** LH toe-offs go 0.61 through the heel,
  0.33 rolled and 0.05 taps. RH goes 0.36 / 0.09 / **0.56**: the RH taps
  have grown from g4-peakc-25's 0.37.

## Decision

Against the keep rule in `g5-toe-25.md`:

| part | needed | result | met? |
|---|---|---|---|
| toes-up, each leg | at most 0.10 | 0.27 / 0.06 | **no** (LH) |
| heels | at least 0.47 / 0.28 | 0.46 / 0.19 | **no** |
| `hock_at_toeoff` | at least 0.61 / 0.48 | 0.61 / 0.33 | **no** (RH) |
| speed | at least 2.65 m/s | 2.55 m/s | **no** |

**g4-peakf fails.** The fine-tune rate held the trainer's curve
(32.6 → 33.3 a step by 21), but the engine's judgement fell on every
part, and `completes` and `upright` slipped to 8/10. It is stopped once
g6-swank's build is accepted. That way the GPU is not idle through the
build (O8).

Following the critic, this ends the reward-shaping questions for P1 for a
screen. The next question is whether the leg can reach a flat foot.

## Can the hind leg reach a flat sole? (`hind_reach.py`)

Each hind leg's frames after the settle are classed by the engine's own
foot reading:
- **flat**: heel and paw down;
- **toes-up**: heel down, paw up (the O2 fault);
- **toe**: paw down, heel up.

For each class the probe gives the joint angles in the left leg's sign,
with the passive `j_ankle` read from the placements. It also gives the
margin to the nearer stop, the share of frames within 2° of a stop, the
hock's command minus its measured angle (positive means the command is
heel-up of the joint), and the hock drive's effort over its 22 N·m peak.

The clip's own targets over its heel-down samples are:

| leg | clip hip / knee / ankle (°) |
|---|---|
| LH | −7.2 / +20.8 / −33.5 |
| RH | −5.3 / −6.6 / −52.9 |

| evaluation | leg | class | frames | hip / knee / hock / ankle (°) | margin hip / knee / hock (°) | at a stop hip / knee / hock | hock cmd − meas (°) | hock effort/peak med / p95 | tilt mm |
|---|---|---|---|---|---|---|---|---|---|
| g4-peak-25 | LH | flat | 341 | −11.8 / −36.4 / −35.7 / −35.8 | 31.5 / 23.6 / 34.3 | 0 / 0 / 0 | +5.7 | 0.42 / 1.00 | −0.5 |
| g4-peak-25 | LH | toes-up | 384 | −14.4 / −23.0 / −30.7 / −30.7 | 30.6 / 37.0 / 39.3 | 0 / 0 / 0 | +2.7 | 0.08 / 0.27 | +10.3 |
| g4-peak-25 | LH | toe | 2157 | +5.7 / −34.3 / −41.6 / −41.7 | 32.2 / 25.7 / 28.4 | 0 / 0 / 0 | +13.7 | 0.67 / 1.00 | −10.9 |
| g4-peak-25 | RH | flat | 295 | −9.1 / −29.5 / −39.7 / −39.7 | 35.5 / 30.5 / 30.3 | 0 / 0 / 0 | +20.4 | 1.00 / 1.00 | −0.6 |
| g4-peak-25 | RH | toes-up | 120 | −11.8 / −22.5 / −36.7 / −36.6 | 33.2 / 37.5 / 33.3 | 0 / 0 / 0 | +9.6 | 0.11 / 0.28 | +9.4 |
| g4-peak-25 | RH | toe | 2096 | −3.4 / −25.5 / −33.1 / −33.2 | 38.4 / 34.2 / 36.9 | 0 / 0 / 0 | +13.2 | 0.74 / 1.00 | −12.7 |
| g4-peakc-25 | LH | flat | 455 | +3.4 / −21.0 / −59.5 / −59.5 | 34.4 / 34.3 / 10.5 | 0 / 0 / 0.29 | +14.8 | 1.00 / 1.00 | −0.2 |
| g4-peakc-25 | LH | toes-up | 52 | −1.9 / −2.7 / −41.1 / −41.1 | 36.3 / 38.6 / 28.9 | 0 / 0 / 0 | −4.2 | 0.16 / 0.64 | +4.0 |
| g4-peakc-25 | LH | toe | 509 | +21.9 / +10.7 / −48.2 / −48.2 | 18.1 / 37.9 / 21.8 | 0 / 0 / 0.06 | +67.4 | 1.00 / 1.00 | −15.6 |
| g4-peakc-25 | RH | flat | 208 | +15.6 / −16.9 / −63.8 / −64.2 | 24.4 / 36.4 / 6.2 | 0 / 0 / 0.29 | +15.8 | 1.00 / 1.00 | −0.4 |
| g4-peakc-25 | RH | toes-up | 42 | +13.1 / +4.3 / −48.3 / −48.2 | 26.8 / 40.0 / 21.7 | 0 / 0 / 0.02 | +1.4 | 0.25 / 1.00 | +7.6 |
| g4-peakc-25 | RH | toe | 536 | +20.1 / +2.4 / −47.6 / −47.6 | 19.9 / 36.9 / 22.4 | 0 / 0 / 0.16 | +47.9 | 1.00 / 1.00 | −17.0 |
| g4-peakf-25 | LH | flat | 402 | +6.6 / −23.7 / −66.1 / −66.0 | 32.9 / 33.4 / 3.9 | 0 / 0 / 0.41 | +18.4 | 1.00 / 1.00 | −0.3 |
| g4-peakf-25 | LH | toes-up | 160 | −14.4 / −39.2 / −51.9 / −51.9 | 30.0 / 20.8 / 18.1 | 0 / 0 / 0.01 | −6.9 | 0.15 / 0.70 | +10.4 |
| g4-peakf-25 | LH | toe | 474 | +25.0 / +12.3 / −53.2 / −53.2 | 15.0 / 37.3 / 16.8 | 0.03 / 0 / 0.07 | +71.9 | 1.00 / 1.00 | −15.7 |
| g4-peakf-25 | RH | flat | 154 | +14.6 / −36.4 / −69.7 / −70.6 | 25.4 / 23.1 / 0.3 | 0 / 0.02 / 0.56 | +12.2 | 1.00 / 1.00 | −0.5 |
| g4-peakf-25 | RH | toes-up | 12 | +17.1 / −18.5 / −69.2 / −69.8 | 22.9 / 39.6 / 0.8 | 0 / 0 / 0.58 | +18.7 | 1.00 / 1.00 | +3.7 |
| g4-peakf-25 | RH | toe | 588 | +18.9 / −1.5 / −47.7 / −47.9 | 21.1 / 28.0 / 22.3 | 0 / 0 / 0.27 | +43.3 | 1.00 / 1.00 | −23.1 |

g3-flat-50 and g5-toe-25 read the same way: in toes-up frames the hock
keeps 22–38° of margin, the command is within 3° of the joint, and the
effort is 0.07–0.16 of peak.

**The toes-up foot is not a reach limit.** In the toes-up frames that
matter, the hock has 18–29° of margin, its command sits within 7° of the
joint, and its effort is 0.15–0.25 of peak. No hip or knee is near a
stop. The policy puts the foot there, and could put it flat. (RH's 12
toes-up frames on g4-peakf-25 are on the hock stop, but they are 0.06
of its heel-down frames.)

**What the probe does show, in every stance class, is this:**
1. **The hock is driven heel-up at peak.** In flat and toe stance its
   effort is at 1.00 of peak (median and p95). The command is heel-up of
   the joint by 12–18° in flat stance and by 43–72° in toe stance.
2. **On the two faster checkpoints, the flat foot sits on the hock's −70°
   stop.** g4-peakc-25 and g4-peakf-25 (2.55–2.65 m/s) stand flat at hock
   −60 to −70°, with 0.29–0.56 of flat frames within 2° of the stop.
   The slow cold g4-peak-25 (0.94 m/s, its hip 20° further back) stands
   flat at −36 to −40°, with 30° of margin. So the hock a flat sole
   needs depends on the posture, and the faster posture pushes it to
   the stop.
3. **So the heel is down where the load beats the hock drive.** At the
   stop the drive can only push heel-up. The command range ends at the
   stop, and the trainer centres each action on its range: the hock's
   is −15° (`training/cadex_train.py`, output bias), so the flat seat sits
   at the bottom edge of the action space.
4. **The clip's stance ankle target is heel-up of flat.** On LH it asks
   for −33.5°, 26–33° heel-up of the flat foot. g4-peakf-25's LH toes-up
   frames sit at −52°, at a knee of −39°. `track_pose` pulls the stance
   hock that way.

The pull in item 4 is small. `track_pose` is exp(−Σ deg²/17,100) at
weight 1.5, so a 26° ankle error costs 4% of the exponent. But it is the
one term that asks for the heel-up hock in stance.

**O1.** Items 1–3 are O1's examples: a drive at peak, and a joint stop
the policy sits on. They are recorded as evidence. No model change is
made yet, because O1 says to change the policy first, and the policy-side
lever (item 4) is untested. If the clip-side screen does not take the
hock off peak in stance, the next lever is the model: centre or widen
the hock's command range on the heel side, so the flat seat is not the
edge of the action space. That change would need a clearance check of
the metatarsus against the shin past −70°.

## Next screen: `g6-swank` (queued 02:10)

g6-swank is g4-peak's task (`~/orun13-scripts/leo-flatpeak.py`) with one
change. In `track_pose`, each hind ankle's error is multiplied by
`(1 − ref_{lh,rh}_down)`, so the clip's ankle target is tracked only in
the clip's hind swing, and `heel_pitch` alone sets the stance foot. The
script is `~/orun13-scripts/leo-swingankle.py`. It changes the task
digest, so the run is cold: 50 iterations, 4096 envs, seed 0, budget
3,000 s (g5-toe's ~48 s an iteration cold, plus 20%). It is queued with
`queue_run.py --after g4-peakf --build`.

**Judge at 25 against g4-peak-25** (the same task cold, without the
change). Keep only if:
- the hock's stance command offset (`hind_reach.py`) falls from
  g4-peak-25's, which is +5.7 / +20.4° flat and +13.7 / +13.2° toe
  (LH / RH);
- toes-up is no higher than 0.51 / 0.27;
- heels are at least 0.13 / 0.14;
- speed is at least 0.94 m/s.

At 50, compare against g4-peak-50: toes-up 0.09 / 0.06, heels
0.44 / 0.22, 2.43 m/s.

**Launched.** The build was accepted as `936e27e5` (project git `ca3729f`)
in 4 minutes. g4-peakf was stopped at 02:15 (`request_stop`, about 30
iterations), and g6-swank launched at 02:15:23. Its bundle has 18 terms.
Only the two hind-ankle errors in `track_pose` are gated, and the model
is byte-identical to g4-peakf's.

**Its first ten iterations, timed.** Iteration 10 came at 676 s, and the
trainer projected about 2,400 s more: some 3,070 s for 50, against the
3,000 s budget. A registered run's budget cannot be raised, so it may
end on its budget at about 48. Iteration 25, which decides the screen,
comes at about 1,600 s.
