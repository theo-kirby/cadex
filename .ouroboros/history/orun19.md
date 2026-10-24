---
run: orun19
machine: sb1x
started: 2026-10-23T13:50:55
ended: 2026-10-24T07:08:40+00:00
hours: 13.3
state: stopped
iterations: 28
commits: 40
criteria_ticked: 8
criteria_closed: 8
criteria_total: 8
criteria_unknown: 0
criteria_source: run-local memory snapshot
merged: d2b161ca1b2a680ac2ae4790bf1c9141d7c4a4d9
branch: ouroboros/orun19
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun19

28 iterations in 13.3h on `sb1x`, stopped (critic accepted done 2x in a row). Branch `ouroboros/orun19`, merged as `d2b161ca`.

## The numbers

| | |
|---|---|
| iterations | 28 (changed 27, recorded 0) |
| commits | 40 — 46 files changed, 5298 insertions(+), 16 deletions(-) |
| criteria | **this run completed 8**; 8 of 8 verified met; 0 unknown (run-local memory snapshot) |
| reverts | 0 |
| verdicts | continue 25, done_accepted 2, done_rejected 1 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 12% -> 18% (+6 this run); claude five_hour 15% -> 2% (-13 this run) |

## What landed

- orun19 R1: fold the run into training/RECIPE.md §5 (sphere feet, speed first, held command, noise gap, one-sided track_speed, ADR-791 warm start across goal.range, hip clamp before another weight); REPORT's Docs line updated; leo DECISIONS ADR-002 (26bf35d)
- orun19 X1d: x1d-reg judged at 50 and 150 (a57ca0d2) to 8.0 m/s — tracks 0.7-4.23 only, top 3.95 m/s (Fr 4.02), 44/130 tips from 6.0 up; no new top over x1b-warm-150's 5.72 (Fr 8.42), second failed X1 screen in a row; R1 written in full (X1 table, hip peak torque binds, next-run recommendation)
- orun19 X1d: x1d-reg launched warm from x1b-warm-150 (10f197e1) on leo 0f11e624 — torque, energy and action_rate weights to a quarter (O3's third lever), judged range to 8000; bundle 3ced6ed6 differs from x1b's in the three weights and spec only; ~18.2 s/it
- orun19 X1c: x1c-ceil judged at 50 and 150 (56182229) to 8.0 m/s — tracks 0.7-6.0 with 0/130 falls, top 5.61 m/s at 6.0 (Fr 8.10), 5.82 held at 8.0 (Fr 8.72); no new top over x1b-warm-150's 5.72 (Fr 8.42), first failed X1 screen in a row; a 6.25 Hz flying trot, hips 1.42-1.62x rated at 6.0
- orun19 X1c: ADR-791 lets a warm start cross a goal's draw range (goal.range); x1c-ceil launched warm from x1b-warm-150 (10f197e1) on leo 9763fa37 with the training goal's ceiling 5000 -> 7500 mm/s and the judged range to 8000; bundle ab9e023e differs from x1b's in the goal range and spec only; ~17.7 s/it
- orun19 X1b: x1b-warm judged at 50 and 150 (10f197e1) to 6.5 m/s — tracks 0.7-6.0 with 0/100 falls, top tracked 5.72 m/s at 6.0 (Fr 8.42), 5.84 m/s held at 6.5 (Fr 8.78); new X1 top over s2a-hold-150's 4.57; one 6.25 Hz gait, hind hips 1.74-1.85x rated
- orun19 X1b: x1b-warm launched warm from s2a-hold-150 (efe7f96b) on leo 6f4bbe78 — track_speed one-sided (0.75 -> 0.5, full pay at and above the command), judged range to 6500; bundle f070a89b differs from s2a-hold's in the reward and spec only; ~17.9 s/it
- orun19 X1a: x1a-cold judged at 50 and 150 (3eb2927f) to 6.5 m/s — tracks 0.7-4.23 with 0/100 falls, top 4.12 m/s Fr 4.37, ~4.1 m/s ceiling below s2a-hold-150's 4.57; hind hips 1.41-1.49x rated; first X1 screen without a new top
- orun19 L1: l1-dog-250 (ec612b29) judged at 2.76/3.5/4.23 — holds 2.93/3.73/4.43 m/s, tracks all three with 0/30 falls (top 4.43, Fr 5.05), seed 1007 survives; 0.4-0.7 m/s slower than m2-dog-150, nearer the clip, worst drive 0.94-1.22x; filmed beside M2 and the clip (4ef0aca7), F1 complete; X1a (ceiling 5000 -> 6500) training cold as x1a-cold after a refused warm start
- orun19 F1: s2a-hold-150 filmed at its six tracked speeds (bb22f155) and M1/M2 beside it at 3.5/4.23/4.63/5.0 (14dd6ece); s2a-hold-150 judged at 4.23 and 4.63 m/s tracks both (4.55/4.57, 0/20 falls), top tracked now 4.57 m/s Fr 5.38
- orun19 L1: l1-dog launched warm from m2-dog-150 (863845a8) on 8e9e53fc, seed 1, 250 it, budget 6,200 s, ~18-22 s/it (queue_warm.py); M2 filmed beside its clip (6e92a939); seed 1007's reset tip is the draw (mass x1.071, kick 0.146 m/s, +6 deg start) not the start pose alone (reset_draws.py)
- orun19 M2: m2-dog judged at 50 and 150 (2760/3500/4230 mm/s) — 863845a8 holds 3.67/4.36/4.83 m/s, over every command, tracks 2.76 and 3.5 (top tracked 4.36 m/s Fr 4.89; s2a-hold-150 4.08), 4.23 lost seed 1007 at reset (0.42 s); the clip's rotary order and stride to 3.5, stride doubled at 4.23; fore 62–84% strides missed, hind 7–12%; j_scap_r 1.52x, spine 0.75–0.90x; at 50 = v05 c3-s1-50. M1 filmed beside its clip (clip_side_film.py, 97d59ade)
- orun19 M1: m1-cheetah judged at 50 and 150 (4630/5000/5328 mm/s) — a1b5218a holds 4.25/4.37/4.36 m/s with 0/30 falls, tracks 4.63 only (revised O3), top held 4.37 m/s Fr 4.92 (s2a-hold-150 4.53, v05 B1 1.62 at 5.0); clip's transverse order and ~2.5 Hz stride, hind 0 misses, fore double-tap; j_spine 1.53x rated; at 50 14/30 tip; ref_tables.py reads the engine's reference footfall
- orun19 S2: re-read under the revised O3 (over the command is never a miss) — s2a-hold-150 tracks 0.7/1.5/2.4/3.5 m/s, 0/50 falls, slowest seed 1.14x at 3.5, held 4.08 m/s Fr 4.29 (v05 B1 tracks 0.7/1.5, 2.59 Fr 1.73; Go1 1.53 Fr 0.80); 5.0 misses by one seed (4.49); S2 met; M2 (m2-dog, 8e9e53fc) launched cold 19:19:50
- orun19 S2: why s2a-hold runs ~1.2x its command — comv_x is right (MJX = MuJoCo = finite-difference COM; COM = judge's base point to 0.02%, swing 0.3-2.6%), the trainer's own witness overshoots 1.18-1.22, and with its training noise the same actor runs 1.03x (deterministic 1.21x): calibrated for its noisy self; regulariser weights predicted not to close it; M1 trained 150/150 (a1b5218a), not judged
- orun19 S2: s2b-tent judged at 150 — lever 2 rejected: +26–39% over at 700–2400 (s2a-hold-150 +20–23%), 6/50 within 10% (3500 only), 4.01 m/s at 5000, 0/50 falls, right hind over rated, rod loops 2.2–2.3 mm at the top; M1 (m1-cheetah, c3c099af) launched cold at 17:04, 370 s at iteration 10
- orun19 S2: s2b-tent judged at 50 — 1.2–1.5 m/s whatever the command (6/10 at 1500 is the plateau crossing it), 0.4–0.5 m/s under s2a-hold-50, 0/50 falls, veers above ~3 m/s, heel pad never down; verdict waits for 150; M1 launch command ready
- orun19 R1: REPORT.md skeleton, kept current — S1 (s1-v06-50/180) and S2a (s2a-hold-50/150) numbers beside v05 b1-s2-180, S2 screen ladder with s2b-tent training, M1/M2 retarget fit (untrained), F1 so far, what v06 allowed and what binds, not tested yet
- orun19 S2: s2a-hold judged at 150 — speed follows the command within ±2% seed to seed but ~1.2x over it (0.86/1.80/2.95/4.08/4.53 m/s at 700-5000), tracked at 5000 only (9/10), 0/50 falls, Fr 5.28 top; S2b (track_speed's tent made symmetric) launched cold
- orun19 F1: first films outside the repo — v06 standing (turn), s1-v06-180 beside v05 b1-s2-180 at 0.7/3.5 m/s, M1 cheetah and M2 dog clips on v06 (clip sha256 checked against the bundles'); stand_film.py, retarget_film.py
- orun19 S2: s2a-hold judged at 50 — 1.7-2.3 m/s whatever the command (1/50 seeds within 10%), veers and slows above ~2 m/s, 0/50 falls, heel pad never down; same plateau as s1-v06-50, verdict waits for 150
- orun19 M2: the dog's gallop27/34/42 retargeted to leo v06 (carpus target: stance miss <=14 mm, fore swing miss 75-173 mm, hind <=33, heel pad never down); M2 bundle built from s1-v06's leo_v06 speed task (13 rows, cmd 2756-4233), untrained
- orun19 S1: s1-v06 judged at 180 — speed follows the command (0.75/2.17/3.07/3.77/4.24 m/s at 700–5000), tracked at 700 (6/10) and 3500 only, 0/50 falls, top 4.24 m/s Fr 4.63 vs v05 B1 2.59 Fr 1.73; S2a (command held per episode) launched cold
- orun19 M1: cheetah tail mapped to j_tail1/j_tail2 (head measured, held in the speed task); M1 bundle built on v06 (13 rows, 30 tracking channels, cmd 4629-5328), untrained
- orun19 S1: s1-v06 judged at 50: 1.6-1.8 m/s settled at 700-3500, veers and slows at 5000, 0 falls/50, heel pad never down; s1_tables.py for v06
- ... and 2 more

## Decisions the critic made

- #26 done_rejected: The X1d numbers match their source and R1 is written correctly after two failed X1 screens, but the RECIPE.md rung that R1 itself names as undone is still open on the horizon ladder.

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

Closed itself at 13.3 h of 72, 8 of 8 criteria, no reverts. Sphere feet were the fix: on the same speed-only task leo v06 held 4.24 m/s against v05's 2.59, and the top policy (x1b-warm-150) tracks 0.7–6.0 m/s and holds 5.72 m/s (Fr 8.42) with 0/100 falls. Two things the numbers do not say. The owner's mid-run edit made tracking one-sided (overshoot is never a miss): that alone closed S2, because a symmetric ±10% band had been failing a policy that ran ~1.2× its command, an overshoot traced to the deterministic-vs-noisy gap, not to the reward. And the top-speed criterion (X1) with a "two failed screens ends it" rule gave the run a useful end instead of idling; the one-sided `track_speed` was the lever that moved, while a higher command ceiling and cheaper torque did not. The limit is now the hind hips at their 53 N·m peak, a model change for the owner; the heel pads and the straight forearm were never used or could not follow a clip, so the next model should revisit both.
