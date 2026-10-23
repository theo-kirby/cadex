# orun19 report: leo v06 on sphere feet, speed first

Verified against source: 2026-10-23. R1, kept current as criteria close;
not yet the closing report. Every number cites the probe note in this folder
that holds it. Every judged run is the engine's evaluation on the 10 frozen
seeds (C2_SEEDS 1001–1010) at each held command, by orun18's
`speed_judge.py`, read by `b1_summary.py` and `s1_tables.py`. The model is
leo v06 throughout (tag `leo-v06`, revision `62e391eb`, model XML
`f9b8ab82`), frozen (O1); each screen changes the task only.

## Criteria

| criterion | state | best evidence so far |
|---|---|---|
| S1 | evidence complete | s1-v06 judged at 50 and 180 beside v05's b1-s2-180 (`s1-v06-50.md`, `s1-v06-180.md`) |
| S2 | open: no v06 policy tracks at four commands | s2a-hold-150 tracks at 5000 only, s1-v06-180 at 700 (6/10) and 3500 (`s2a-hold-150.md`); S2b (O3 lever 2) training |
| M1 | retargeted and bundled, not trained | `m1-retarget.md` |
| M2 | retargeted and bundled, not trained | `m2-retarget.md` |
| L1 | not started (needs S2, M1 or M2 judged) | |
| F1 | first films made | `f1-films.md`: v06 standing, s1-v06-180 beside b1-s2-180, the M1 and M2 clips on v06 |
| R1 | this file | |

## S1: leo v06 on speed alone

orun18's B1 task (`b1-s2`'s ten reward rows and weights) rebuilt on v06's
drives (`s1-task.md`): 20 actions, 42 actor channels, commands 700–5000
mm/s resampled every 3 s. Cold, seed 0, 4096 envs, 180 iterations in
3,717 s (~18.7 s an iteration against b1-s2's 68.7 s on the same GPU).

Last 2 s along the start heading, median of 10 seeds, m/s; in brackets the
seeds within 10% of the command (O3):

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 | falls |
|---|---|---|---|---|---|---|
| s1-v06-50 (`a3296704`) | 1.62 (0) | 1.70 (0) | 1.76 (0) | 1.82 (0) | 1.04 (0) | 0/50 |
| **s1-v06-180** (`bd32a42c`) | **0.75** (6) | **2.17** (0) | **3.07** (0) | **3.77** (10) | **4.24** (0) | 0/50 |
| v05 b1-s2-180 (`8adbb84f`) | 1.84 | 2.59 | 1.85 | 1.80 | 1.62 | 0/50 |

- **Speed follows the command on v06**, monotone from a 0.75 m/s walk to
  a 4.24 m/s gallop; v05's B1 peaked at 2.59 m/s at 1500 and fell back to
  1.6–1.9 above it. At 50 v06 ran 1.6–1.8 m/s whatever it was asked and
  veered off the line above ~2 m/s; by 180 the veer is gone (median max
  heading 1.6–4.3°).
- **It does not track**: 1.45× over at 1500, 1.28× at 2400, 0.85× at 5000.
  Between the 0.75 walk and a ~2.1 m/s slowest gallop no gait is used.
- **Top held speed 4.24 m/s, Fr 4.63** (hip height 0.396 m, `froude.py`),
  against v05's B1 2.59 m/s (Fr 1.73).
- **Footfall and flight.** A walk at 700 (duty 0.65, no flight); from 1500
  a flight on every stride (100–180 ms) at 4.2–4.6 Hz; from 2400 a
  transverse sequence (LH → RH, LF → RF), the fore lag shrinking with
  speed.
- **The heel pad never touches** at any command (rides 132–139 mm up in
  ball stance): a toe stance, as on every v05 policy.
- **O6.** Within rated at 700 (worst 0.97, `j_knee_r`); from 1500 the
  right hind binds, knee 1.24–1.29× and hip 1.55× (3500) and 1.68× (5000).
  Peak margin 0.00 everywhere (`j_tail2`, unrated, at its clamp on
  0.11–0.35 of frames). The right hip and knee carry 1.2–1.5× the left's.
  No NaN; hind rod loops 1.0–1.7 mm (within 2 mm).

## S2: making it track (O3's levers, one at a time)

| screen | what changed from its parent | judged | tracked commands (O3) | top tracked m/s (Fr) |
|---|---|---|---|---|
| s1-v06 | (S1, the base) | 180 | 700 (6/10), 3500 (10/10); not a tracking prefix | 3.77 (3.66) |
| s2a-hold | lever 1, sampling: command held per episode (resample 3 s → 12 s) | 50, 150 | 5000 only (9/10) | 4.53 (5.28) |
| s2b-tent | lever 2, shape: `track_speed`'s tent symmetric (overshoot slope −0.5 → −1 /cmd) | training | | |

Last 2 s, median m/s (seeds within 10%):

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 | falls |
|---|---|---|---|---|---|---|
| s2a-hold-50 (`80f97755`) | 1.80 (0) | 1.95 (0) | 1.63 (1) | 2.23 (0) | 1.05 (0) | 0/50 |
| **s2a-hold-150** (`efe7f96b`) | **0.86** (0) | **1.80** (0) | **2.95** (0) | **4.08** (0) | **4.53** (9) | 0/50 |
| s1-v06-180 | 0.75 (6) | 2.17 (0) | 3.07 (0) | 3.77 (10) | 4.24 (0) | 0/50 |

- **Lever 1 (s2a-hold)** made speed a tight, monotone function of the
  command (±2–3% seed to seed) and opened a flightless walk-to-trot at
  700–2400 below a bound at 3500–5000, but it runs **+17–23% over every
  command it can reach**, so it tracks only at 5000, where the body tops out.
  The uniform overshoot is what the asymmetric tent predicts (reward falls
  half as fast over the command as under it); S2b tests that reading.
- O6 at 150: worst RMS 1.03× rated at 700 rising to 1.43× (`j_elbow_l`) at
  5000; peak margin 0.00; the fores lean left (shoulder 1.4–2.1× the
  right's), the hinds lean right at the knee (1.2–2.4×). No NaN; loops
  1.0–1.5 mm. The heel pad never touches.
- **Top tracked speed so far: 4.53 m/s, Fr 5.28** (s2a-hold-150 at 5000,
  9/10), against v05's B1 2.59 m/s (Fr 1.73, held, not tracked) and Go1's
  tracked 1.53 m/s (Fr 0.80; held 2.48, Fr 2.11, past its range,
  `../orun18/b2-ceiling.md`). S2 needs four commands from 700 up, so this is
  not S2's number yet.

## M1 and M2: the motion, retargeted

Both retarget onto v06 with the solve unchanged (O4): the ball as each
foot, no wrist, the spine and the tail mapped, the head measured and held.
No joint leaves its range and the hind loops stay closed on every clip.

| | M1 cheetah (cheetah52/59/61) | M2 dog (gallop27/34/42, carpus target) |
|---|---|---|
| leo speed of the strides | 4.63–5.33 m/s | 2.76–4.23 m/s |
| footfall order | LH, RF, LF, RH (transverse) | LH, LF, RF, RH (rotary) |
| stance miss max | 6.2 mm | 14 mm |
| fore swing miss max LF / RF | 39–96 / ≤ 18 mm | 75–108 / 81–173 mm |
| hind swing miss max LH / RH | 15–46 / 49–77 mm | 0–33 / 0–7 mm |
| heel pad touch share | 0.0 | 0.0 |
| bundle (outside the repo) | `c3c099af`, 13 rows, cmd 4629–5328 | `8e9e53fc`, 13 rows, cmd 2756–4233 |

On the retarget alone the dog fits v06's hind legs and the cheetah its fore
legs; v06's fore leg reaches less far forward in late swing than the dog
asks. Neither clip asks for the heel pad. Neither bundle is trained yet;
the comparison M2 asks for is on trained policies, against v05's
c3-s1-50 (1.60–1.94 m/s last 2 s at 2756–4233 commanded, 1 fall in 40,
`../orun18/c3-s1-50.md`).

## What v06's body allowed against v05, so far

On the same speed-only task and budget, v06 against v05:

- it reaches 4.24 m/s held against 2.59, and 4.53 m/s on a held command;
- its speed follows the command instead of plateauing;
- it runs more upright (tilt 9–13° against 12–28°);
- its fore drives stay within 1.35× rated, against v05's shoulder and
  scapula at 1.4–1.8×;
- it trains ~3.7× faster per iteration (the reason is not measured).

What binds now, on the evidence so far:

- **Tracking, not reach**: the speed range covers the commands; the
  error is a proportional overshoot (s2a-hold) or a gap between gaits
  (s1-v06).
- **The right hind and the left fore**: drives over rated and lopsided left
  to right on every judged v06 policy.
- **The heel pad is never used**: every v06 policy and both clips run on
  the balls.

## Not tested yet

- O3's third lever (the regularisers' weights), and S2b's result.
- Any trained M1 or M2 policy; AMP (O4) is not started.
- The long run (L1) and its films.
- Why v06 trains faster per iteration than v05.
