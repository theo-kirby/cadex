# orun19 report: leo v06 on sphere feet, speed first

Verified against source: 2026-10-24. **R1, the closing report**: written
in full after two X1 screens in a row (X1c, X1d) failed to raise the top
speed, per the charter's exhaustion policy. Every number cites the probe note in this folder
that holds it. Every judged run is the engine's evaluation on the 10 frozen
seeds (C2_SEEDS 1001–1010) at each held command, by orun18's
`speed_judge.py`, read by `b1_summary.py` and `s1_tables.py`. The model is
leo v06 throughout (tag `leo-v06`, revision `62e391eb`, model XML
`f9b8ab82`), frozen (O1); each screen changes the task only.

## Criteria

| criterion | state | best evidence so far |
|---|---|---|
| S1 | evidence complete | s1-v06 judged at 50 and 180 beside v05's b1-s2-180 (`s1-v06-50.md`, `s1-v06-180.md`) |
| S2 | **met** under the revised O3: s2a-hold-150 tracks six commands, 0.7, 1.5, 2.4, 3.5, 4.23 and 4.63 m/s, with 0/70 falls. The top is 4.57 m/s held (4.54 the slowest seed), Fr 5.38, judged at 4.23 and 4.63 in iteration 18. Above ~4.2 m/s commanded it holds ~4.55 m/s whatever the command, and 5.0 misses by one seed (4.49, 0.898) | `o3-reread.md`, `s2a-hold-150-top.md` |
| M1 | **judged** at 50 and 150 (4.63 / 5.0 / 5.33 m/s): `m1-cheetah-150` (`a1b5218a`) holds 4.25 / 4.37 / 4.36 m/s with 0/30 falls, so it holds the slowest stride's command and plateaus above it (top held 4.37 m/s, Fr 4.92; s2a-hold-150 4.53 and v05 B1 1.62 at 5.0); the clip's transverse order and ~2.5 Hz stride, hind feet 0 misses, fore feet double-tap (21–120 of ~210 strides missed); `j_spine` 1.48–1.53× rated, left elbow 1.32–1.35 against 0.81–0.86; at 50, 14/30 tip. Filmed beside its clip (`m1-cheetah-150-vs-clip.webm`) | `m1-cheetah-150.md`, `m1-retarget.md`, `f1-films.md` |
| M2 | **judged** at 50 and 150 (2.76 / 3.5 / 4.23 m/s, the bundle's span; M1's commands lie above it): `m2-dog-150` (`863845a8`) holds 3.67 / 4.36 / 4.83 m/s, over every command, and tracks 2.76 and 3.5 (top tracked 4.36 m/s, Fr 4.89); at 4.23 nine seeds hold 4.80–4.85 and seed 1007 tips at 0.42 s; the clip's rotary order and stride at 2.76–3.5, stride doubled (4.35 Hz) at 4.23; fore feet miss 62–84% of strides, hind 7–12%; worst `j_scap_r` 1.29–1.52×, `j_spine` 0.75–0.90×; hind loop 2.1 mm at 4.23. At 50 it ran as v05's c3-s1-50 (1.65–1.95 against 1.60–1.94 m/s), 6/30 tip. Dog against cheetah: the dog fits v06 better on held speed and torque, and the cheetah on following the clip | `m2-dog-150.md`, `m2-retarget.md` |
| L1 | **judged** at 250 (2.76 / 3.5 / 4.23 m/s, the bundle's span): `l1-dog-250` (`ec612b29`, warm from m2-dog-150 on M2's bundle `8e9e53fc`, 250 iterations in 4,904 s) holds 2.93 / 3.73 / 4.43 m/s with 0/30 falls, so it tracks all three (top tracked 4.43 m/s, Fr 5.05), and seed 1007 survives (pitch +15° against +23°). It is 0.4–0.7 m/s slower than m2-dog-150 on every command, nearer the clip: hind feet on every stride, the clip's 2.27 Hz stride kept at 4.23, the left fore still double-taps. Worst drive 0.94 / 1.05 / 1.22× rated (m2-dog-150 1.14–1.52), loops ≤ 1.6 mm. Below s2a-hold-150's 4.57 m/s on top tracked speed. Filmed beside m2-dog-150 and the clip | `l1-dog-250.md`, `l1-dog.md` |
| F1 | **all films made**: v06 standing, s1-v06-180 beside b1-s2-180, the M1 and M2 clips on v06, m1-cheetah-150 and m2-dog-150 beside their clips, s2a-hold-150 at its six tracked speeds, M1 and M2 beside s2a-hold-150 at 3.5, 4.23, 4.63 and 5.0 m/s, and L1 (l1-dog-250) beside m2-dog-150 and the clip at 2.76 and 4.23 m/s | `f1-films.md` |
| X1 | **top: `x1b-warm-150` (`10f197e1`), 5.72 m/s tracked at 6.0 (Fr 8.42), 5.84 m/s held at 6.5 on all ten seeds (Fr 8.78), 0/100 falls.** Four screens, each one change: X1a (ceiling 5000 → 6500, cold) ~4.1 m/s ceiling, no new top; **X1b** (`track_speed` one-sided, warm from s2a-hold-150) the new top; X1c (training ceiling 7500, warm from X1b) 5.61 m/s tracked at 6.0, 5.82 held at 8.0, no new top; X1d (torque, energy and action-rate weights to a quarter, warm from X1b) 3.95 m/s tracked at 4.23 (Fr 4.02) and 44/130 tips from 6.0 up, no new top. Two failed screens in a row: X1 ends here. Bound at the hind hips' 53 N·m limit (x1b-warm-150 at 6.0: both hips 1.74–1.75× rated, at the clamp on 7–9% of frames) | `x1a-cold.md`, `x1a-cold-150.md`, `x1b-warm.md`, `x1b-warm-150.md`, `x1c-ceil.md`, `x1c-ceil-150.md`, `x1d-reg.md`, `x1d-reg-150.md` |
| R1 | **written**: this file, closed after X1d | this file |

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

**S2 is met under the owner's revised O3** (over the command is never a
miss; `o3-reread.md`, re-read from the evaluations, nothing re-run). The
second table is the old reading (within ±10%), kept as judged.

| screen | what changed from its parent | judged | tracks up to (revised O3) | held there, median m/s (Fr) |
|---|---|---|---|---|
| s1-v06 | (S1, the base) | 180 | 3.5 (4 commands) | 3.77 (3.66) |
| s2a-hold | lever 1, sampling: command held per episode (resample 3 s → 12 s) | 50, 150 | **4.63 (6 commands) at 150**, 3.5 before 4.23 and 4.63 were judged; 5.0 misses by one seed (0.898) | **4.57 (5.38)**; 4.08 (4.29) at 3.5 |
| s2b-tent | lever 2, shape: `track_speed`'s tent symmetric (overshoot slope −0.5 → −1 /cmd) | 50, 150 | 3.5 (4 commands) at 150; rejected, slower at the top (4.01 at 5.0) | 3.82 (3.76) |

Old reading, last 2 s, median m/s (seeds within ±10%):

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 | falls |
|---|---|---|---|---|---|---|
| s2a-hold-50 (`80f97755`) | 1.80 (0) | 1.95 (0) | 1.63 (1) | 2.23 (0) | 1.05 (0) | 0/50 |
| s2b-tent-50 (`43cbe2ef`) | 1.27 (0) | 1.43 (6) | 1.49 (0) | 1.23 (0) | 1.16 (0) | 0/50 |
| s2b-tent-150 (`f971c970`) | 0.97 (0) | 1.89 (0) | 3.09 (0) | 3.82 (6) | 4.01 (0) | 0/50 |
| **s2a-hold-150** (`efe7f96b`) | **0.86** (0) | **1.80** (0) | **2.95** (0) | **4.08** (0) | **4.53** (9) | 0/50 |
| s1-v06-180 | 0.75 (6) | 2.17 (0) | 3.07 (0) | 3.77 (10) | 4.24 (0) | 0/50 |

- **Lever 1 (s2a-hold)** made speed a tight, monotone function of the
  command (±2–3% seed to seed) and opened a flightless walk-to-trot at
  700–2400 below a bound at 3500–5000, but it runs **+17–23% over every
  command it can reach**, so it tracks only at 5000, where the body tops out.
  The uniform overshoot is what the asymmetric tent predicts (reward falls
  half as fast over the command as under it); S2b tests that reading.
- **Lever 2 (s2b-tent) at 50** (`s2b-tent-50.md`) runs ~1.2–1.5 m/s at
  every command, 0.4–0.5 m/s under s2a-hold-50's plateau: the symmetric tent
  cut the slow end's overshoot (700: 1.80 → 1.27) by lowering the whole
  plateau, not by separating speeds. 0/50 falls, veers above ~3 m/s, toe
  stance; worst RMS 1.49–1.59× (`j_spine`, then `j_shoulder_l`), loops
  1.3–1.5 mm.
- **Lever 2 at 150, rejected** (`s2b-tent-150.md`): as tight and monotone
  as s2a-hold-150 but **further over** the command at 700–2400 (+26–39%
  against +20–23%) under a tent that pays twice as hard for overshoot; 6/50
  seeds within 10% (3500 only) against s2a-hold-150's 9/50; top end 4.01
  m/s against 4.53; right hind knee/hip 1.16–1.78× rated, hind rod loops
  2.2–2.3 mm at 3500–5000 (over O6's 2 mm). The tent's shape is not what
  holds the slow end over its command. Lever 3 (one regulariser weight)
  goes on s2a-hold's task, queued behind M1.
- **Why s2a-hold runs ~1.2× over** (`s2-speed-signal.md`, no training): the
  speed `track_speed` reads (`comv_x`, the root's `subtreelinvel`) is right
  in MJX and equals the judge's base-point speed to 0.02% on the judged
  traces. Its within-stride swing is 0.3–2.6% of the command, too small to
  move the tent's peak. The trainer's own deterministic witness overshoots
  the same way (1.18–1.22 at 100 and 150). In the trainer's environment the
  same actor **with its training noise** (σ 0.52) runs at **1.03×** the
  command (median, 64 envs; 1.00–1.15 at 1.2–3.4 m/s) against **1.21×**
  deterministic. The policy is calibrated for its noisy self, and the
  engine plays the mean. The slow end keeps a floor (×1 still 1.13–1.27 at
  700–1150), and the full noise stalls the gait above ~3.4 m/s. So no
  regulariser weight closes it (they cost 0.5–1.5 a step and pull toward
  slower); what would is a smaller σ late (a long warm start as σ falls, or
  the entropy cost) or a task that pays the played speed.
- O6 at 150 (s2a-hold): worst RMS 1.03× rated at 700 rising to 1.43× (`j_elbow_l`) at
  5000; peak margin 0.00; the fores lean left (shoulder 1.4–2.1× the
  right's), the hinds lean right at the knee (1.2–2.4×). No NaN; loops
  1.0–1.5 mm. The heel pad never touches.
- **Top tracked speed (revised O3): 4.57 m/s held on a 4.63 m/s command,
  Fr 5.38** (s2a-hold-150, every seed 4.54–4.59, `s2a-hold-150-top.md`;
  4.08 m/s, Fr 4.29, on 3.5 in `o3-reread.md`), against
  v05's B1, which tracks 0.7 and 1.5 only and holds 2.59 m/s at most (Fr
  1.73), and Go1's tracked 1.53 m/s (Fr 0.80; held 2.48, Fr 2.11, past its
  range, `../orun18/b2-ceiling.md`). That is S2's top. X1 has since raised
  v06's: x1b-warm-150 tracks to 6.0 m/s, holding 5.72 (Fr 8.42), and holds
  5.84 m/s at 6.5 on all ten seeds (Fr 8.78) (`x1b-warm-150.md`).

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
asks. Neither clip asks for the heel pad. Trained, the cheetah's policy keeps its clip's
order and stride and holds 4.25–4.37 m/s (`m1-cheetah-150.md`). The dog's
runs 1.1–1.3× over its strides, 3.67–4.83 m/s, keeps the clip's order and
stride to 3.5 m/s and drops the stride at 4.23, with its fore feet off the
clip on most strides (`m2-dog-150.md`). v05's c3-s1-50 held 1.60–1.94 m/s at
the same commands (1 fall in 40, `../orun18/c3-s1-50.md`).

| | M1 cheetah-150 | M2 dog-150 | v05 c3-s1-50 |
|---|---|---|---|
| held m/s at the bundle's commands | 4.25 / 4.37 / 4.36 (4.63–5.33) | 3.67 / 4.36 / 4.83 (2.76–4.23) | 1.60 / 1.94 / 1.83 (2.76–4.23) |
| commands tracked; falls | 1; 0/30 | 2; 1/30 (at reset) | 0; 1/40 |
| fore / hind strides missed | 10–58% / 0% | 62–84% / 7–12% (to 3.5) | – |
| worst RMS / rated | 1.53 (`j_spine`) | 1.52 (`j_scap_r`, 4.23); 1.14–1.29 below | 1.57 (`j_wrist_r`) |

## X1: top speed

Each screen is one change from its parent, judged at 50 and 150 on the 10
frozen seeds per command, by `o3_reread.py`'s O3 (at least 0.9 × the
command on every seed, no fall or tip, at every judged command up to the
top). Fr uses v06's hip height, 0.396 m.

| screen | the one change, from | top tracked m/s at command (Fr) | fastest held, no tip | falls / tips | verdict |
|---|---|---|---|---|---|
| s2a-hold-150 (`efe7f96b`) | (S2's top) | 4.57 at 4.63 (5.38) | 4.57 at 4.63 | 0/70 | the start |
| x1a-cold-150 | training ceiling 5000 → 6500, cold | 4.12 at 4.23 (4.37) | ~4.1 | 0/100 | no new top |
| **x1b-warm-150** (`10f197e1`) | `track_speed` pays in full at and above the command, warm from s2a-hold-150 | **5.72 at 6.0 (8.42)** | **5.84 at 6.5 (8.78)** | 0/100 | **new top** |
| x1c-ceil-150 (`56182229`) | training ceiling 5000 → 7500, warm from x1b-warm-150 (ADR-791) | 5.61 at 6.0 (8.10) | 5.82 at 8.0 (8.72) | 0/130 | no new top (1) |
| x1d-reg-150 (`a57ca0d2`) | torque, energy and action-rate weights to a quarter, warm from x1b-warm-150 | 3.95 at 4.23 (4.02) | 4.09 at 5.0 (4.31) | 44/130 tips, 6.0–8.0 | no new top (2) |

- **The top is x1b-warm-150**: 5.72 m/s tracked at 6.0 (Fr 8.42) and 5.84
  m/s held at 6.5 on all ten seeds (Fr 8.78), against v05's B1 2.59 m/s
  held (Fr 1.73; it tracks only 0.7 and 1.5) and Go1's 1.53 m/s tracked
  (Fr 0.80; 2.48 held, Fr 2.11, `../orun18/b2-ceiling.md`). It is faster
  than the best on any cat before this run (4.64 m/s, orun10, per the
  charter). Its gait from 3.5 up: 6.25 Hz,
  flight every stride, steps 616 → 931 mm (`x1b-warm-150.md`).
- **X1c**: asked for up to 7.5 m/s in training, the policy holds ~5.8 m/s
  whatever it is commanded to 8.0, in a diagonal trot that loads the hips
  less (`x1c-ceil-150.md`). The command is not what holds it back.
- **X1d**: with torque and energy priced at a quarter, the hips did not
  work harder. The policy's σ rose 0.41 → 0.49 and its reward per step fell
  22.9 → 20.5. Its hips ran at 0.8–1.2× rated, and it slowed to a 5.56 Hz
  stride that tips from 6.0 m/s up. At 50 it was nearer the top (5.31 m/s
  tracked, Fr 7.26) (`x1d-reg-150.md`). The regularisers are not what keeps
  the top policy's hips in check.
- O6 at the top (x1b-warm-150 at 6.0): worst RMS 1.74–1.75× rated at the
  hips (`j_spine_yaw` 1.70×); both hips peak at their 53 N·m limit, at the
  clamp on 7–9% of frames; peak margin 0.00; left and right hips within 1%;
  loops within 2 mm; no NaN; the heel pad never touches.

## What v06's body allowed against v05

On the same speed-only task and budget, v06 against v05:

- it reaches 4.24 m/s held against 2.59 (S1), s2a-hold-150 tracks to
  4.63 m/s commanded, holding 4.57 m/s on all ten seeds, and X1b's
  x1b-warm-150 tracks to 6.0, holding 5.72 m/s (Fr 8.42), and holds 5.84
  m/s at 6.5 (Fr 8.78): 2.2× v05's held speed, Fr 8.78 against 1.73;
- its speed follows the command instead of plateauing;
- it runs more upright (tilt 9–13° against 12–28°);
- at S's speeds its fore drives stay within 1.35× rated (s2a-hold-150),
  against v05's shoulder and scapula at 1.4–1.8×; at X1's top the
  scapulae reach 1.35–1.46× (`x1b-warm-150.md`);
- it trains ~3.7× faster per iteration (the reason is not measured).

What binds it now:

- **At the top, the hind hips' peak torque.** x1b-warm-150 holds 5.7–5.8
  m/s at a fixed 6.25 Hz stride by lengthening its step to ~930 mm. Both
  hips run at 1.74–1.75× their 18 N·m rated and touch their 53 N·m limit,
  at the clamp on 7–9% of frames at 6.0 (`x1b-warm-150.md`,
  `x1d-reg-150.md`). The hips are already the catalog's heaviest QDD
  (CubeMars AK10-9 V3.0, ADR-713). Neither more command (X1c) nor cheaper
  torque (X1d) moved the top. Next after the hips, `j_spine_yaw` (9 N·m
  rated) runs at 1.70×.
- **The stride, not the frequency**: every fast v06 policy holds a fixed
  stride frequency (6.25 Hz at the top) and gains speed only by step
  length. So the step's reach, set by the hip's swing and the leg's
  length, is the second limit. That is a reading from the gait tables,
  not a measured counterfactual.
- **Tracking, not reach**, at S's speeds: the speed range covers the
  commands; the error is a proportional overshoot (s2a-hold) or a gap
  between gaits (s1-v06). The trainer's noisy policy runs at ~1.03× the
  command where the engine's deterministic one runs at ~1.21×
  (`s2-speed-signal.md`).
- **The right hind and the left fore**: drives over rated and lopsided left
  to right on every judged v06 policy below the top (the shoulders 1.3–2.1×,
  the hind knees 1.2–2.4×); at x1b's top the hips are even.
- **The heel pad is never used**: every v06 policy and both clips run on
  the balls; the pad rides 123–139 mm up in stance.
- **On the cheetah's strides, the clip's stride frequency and the spine**:
  m1-cheetah-150 keeps ~2.5 Hz whatever it is commanded, so its speed
  plateaus at 4.37 m/s, and its spine runs at 1.5× rated.
- **On the dog's strides, the fore girdle and the fore feet**: m2-dog-150
  reaches 4.83 m/s, with the right scapula at 1.52× rated, and the fore balls
  touch twice a stride on both motions. v06's straight forearm does not
  follow either clip's fore swing (`m1-retarget.md`, `m2-retarget.md`).

## Not tested

- What holds the slow end (700–1150 mm/s) over its command once the noise
  gap is accounted for.
- A smaller σ late in training (a long warm start, or the entropy cost),
  which `s2-speed-signal.md` predicts would close the overshoot and X1d's
  rising σ suggests may matter at the top.
- A command draw weighted toward the top, as an X1 lever.
- AMP (O4) is not started; tracking the clips was not too rigid for the
  speeds they cover.
- A counterfactual for seed 1007 (its start phase with another seed's mass and kick), which would measure each part's share (`l1-dog.md`).
- L1 judged above 4.23 m/s: its bundle's command range stops there (`l1-dog-250.md`).
- Why v06 trains faster per iteration than v05.
- x1b-warm-150 above 6.5 m/s commanded: its speed spec stops there, so the judge refuses higher (x1c-ceil-150, judged to 8.0, holds 5.82 m/s there).
- Any v06 policy on the heel pad: none uses it, and no task asked for it (O2).

## Recommendation for the next run

- **Train from x1b-warm-150** (`10f197e1`), on its task (`x1b-warm`'s
  bundle `f070a89b`), for anything that needs speed. It tracks 0.7–6.0 m/s
  with 0/100 falls.
- **Model (needs the owner; O1 froze it here):** the next speed is at the
  hind hips. The evidence asks for more hip torque at the top of the stroke
  than the AK10-9's 53 N·m. Options: a reduction stage on the hip (the
  hip's speed is not what binds; its torque is), or moving hip load onto a
  second drive. `j_spine_yaw` (9 N·m rated, 1.70× at the top) is the next
  drive to bind, so it should be sized up with the hips. Lighter hind
  segments would cut the swing torque the hips pay at 6.25 Hz. Each of
  these is a recommendation from the torque tables, not a tested change.
- **Feet:** v06's heel pad is never loaded by a speed policy and either
  clip. If a plantigrade stance is still wanted, the task has to ask for
  it, or the pad has to sit where a ball stance reaches it. Otherwise it
  can go.
- **Fore leg:** v06's straight forearm does not follow either clip's late
  fore swing (fore misses 10–84% of strides). A motion run on v06 should
  retarget with a fore target the forearm can reach, or bring a carpus
  back.
- **Training:** before another X1 lever, screen σ: a late low-noise warm
  start from x1b-warm-150 on its own task. It is the one lever the
  evidence points at that X1 did not test.
- **Docs:** fold this run into `training/RECIPE.md` (sphere feet, speed
  first, a one-sided `track_speed`, warm starts across a goal's range by
  ADR-791). That work is not done here.
