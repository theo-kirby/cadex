---
run: orun18
machine: sb1x
started: 2026-10-23T05:04:59
ended: 2026-10-23T16:24:17+00:00
hours: 7.2
state: killed
iterations: 14
commits: 23
criteria_ticked: ?
criteria_closed: 0
criteria_total: 11
criteria_unknown: 11
criteria_source: run-local memory snapshot
merged: 44ec3656ddf6ac8cd75554fef08cf222d3053ab2
branch: ouroboros/orun18
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun18

14 iterations in 7.2h on `sb1x`, killed (-). Branch `ouroboros/orun18`, merged as `44ec3656`.

## The numbers

| | |
|---|---|
| iterations | 14 (changed 14, recorded 0) |
| commits | 23 — 31 files changed, 4607 insertions(+), 10 deletions(-) |
| criteria | **this run completed ?**; 0 of 11 verified met; 11 unknown (run-local memory snapshot) |
| reverts | 0 |
| verdicts | continue 14 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 6% -> 11% (+5 this run); claude five_hour 18% -> 6% (-12 this run) |

## What landed

- orun18 F1 side_film.py: the stopped iteration 15's side-on film script (owner stopped the run mid-film; committed as left)
- orun18 C4 film: retarget_film.py reads AcinoSet fte.pickle takes (through acino_retarget.cheetah_stride; FTE skeleton gains a drawing tree, cheetah59 clip/measure byte-identical ef691788); ~/mocap/films/c4-cheetah-strides.webm (cheetah52/59/61, 3x real time + 1/4 speed, 8.4 s, 506 frames decoded, 24902f6f) outside the repo; dog path unchanged
- orun18 C4 retarget: AcinoSet's three slowest steady strides (cetane 146-188, 104-144; zorro 30-71; order LH RF LF RH) retargeted to leo v05 by retarget.py's own solve (acino_retarget.py; retarget() now takes a stride from any capture, dog gallop27 byte-identical a88ad380); leo 4.63/5.20/5.33 m/s (upper bounds), flight 0.46, paw = wrist/hock (a planted-pivot paw fit is ill-posed); 0 limit violations, loops <=0.011 mm, no miss in stance, right hind misses 36-61 mm in early swing (j_hip_r at stop 0.35-0.42); paw pin at stop L 0.65-0.73 / R 0.35-0.54; c4-bundle (e6a04ce8, cmd 4629-5328) built by c3_bundle.py in ~/mocap/acinoset, untrained
- orun18 C3 judged at 50: c3-s1 (0b13282b) rotary on 39/39 standing seeds, flight 0.08-0.12 s, 2.3 Hz stride, but settles at 1.60/1.94/1.81/1.83 m/s at 2756/3395/3800/4233 commanded (top 2 s is the reset); 1 fall (2756, tipped 0.44 s); worst drive j_wrist_r 1.51-1.57x rated, peak margin 0; left hind long stride, right short; loops 3.5-4.1 mm; paw pin at its stop 0.72-0.78 (B1 0.82-0.86, sgt-4-120 0.00); speed_judge.py --task, pin_stop.py
- orun18 C4 CPU: AcinoSet fetched (90 fte.pickle, sha256 in ~/mocap/acinoset/SHA256SUMS) and read by acino_strides.py; 30 steady strides 5.20-14.17 m/s, rotary (LH LF RF RH) from ~9 m/s, transverse below; the slowest four 5.20-6.08 m/s reach leo's range (4.7-5.9 m/s at equal Froude, upper bound); 12 Hz low-pass removes <=5.5 mm (0.11 of accel power) without changing strides, 8 Hz cuts motion; SOURCES.md cat line corrected with the actual search, AcinoSet cited
- orun18 C3 launched and B2 read: c3-s1 (leo 2ba9b8bf, c3-bundle27 cc8f3123 swapped in for speed by queue_bundle.py) trains cold, seed 0, 4096 envs, 150 it, 68.9 s/it after a 240 s compile; b2-ceiling.md: B1's 2.59 m/s is Fr 1.73 (hip 0.396 m, froude.py) vs sgt-4-120 1.82, orun7 f1-g2 4.55, orun10 s1-g4 5.18 (same 31 kg, 53 N·m drives), Go1 0.80 in range / 2.11 at 2.5; fores bind, then the stride; not a ceiling (reward rising at 179)
- orun18 B1 judged at 180: b1-s2 (8adbb84f, 12,873 s) 0/50 falls; settles 1.84/2.59/1.85/1.80/1.62 m/s at 700/1500/2400/3500/5000 (trot at 1.5, half-bound above, command not tracked); fores bind (worst 1.44-1.82x rated, peak margin 0), heel/U 0.00, loops 1.7-2.3 mm; b1_summary.py adds last-2 s speed and left/right RMS
- orun18 F1 retargeted clip: retarget_film.py films gallop27/34/42 (capture against leo, 3 loops real time + 1/4 speed) to ~/mocap/films/c3-strides.webm (9.4 s, 566 frames decoded, sha256 aae4b31c…, CC BY-NC so outside the repo); c3-task.md notes the paw pins sit at their stop on 0.61-0.73 of the C3 strides' samples
- orun18 C3 slow end: stride_scan.py finds the dog's slowest same-order gallop, gallop27 (D1_010_KAN01_001 404-432, 2.76 m/s on leo, 0 violations, fore miss <=38 mm); bundle c3-bundle27 carries gallop27/34/42, cmd 2756-4233, engine readers pass; gallop28 refused on footfall order; nothing slower gallops in this capture
- orun18 C3 bundle: c3_bundle.py writes the dog's gallop strides into a copy of B1's speed task by the engine's own builders (cmd 3395-4233; the four-stride family is refused on footfall order); c2-retarget.png removed (CC BY-NC, D5), stills in ~/mocap/stills
- orun18 C2: AI4Animation dog retargeted to leo v05 (pace 1.1, trot 2.3, gallop 3.4/4.2 m/s); 0 limit violations, loops closed, hind follows, fore misses up to 46 mm at 3.4 and 75 mm at 4.2; clips pass the engine's tracking and schedule readers; B1 task reads cmd, track_speed is a one-sided ramp
- orun18 B1: b1-s2 judged at 50 — 0/50 falls, ~1.4 m/s at every command (command not yet learned), nose-down on the fores; speed_judge.py fills footfall by the engine's function
- orun18 B1: b1-s1 stopped (regularisers paid a fall at exploration noise, priced by noise_terms.py); b1-s2 re-weighted and training cold
- orun18 B1: leo v05 speed-only task (no clip, no style terms) launched cold as b1-s1; C1 licence read: AI4Animation dog, CC BY-NC 4.0
- orun18 A2: Go1 joystick through cadex_train in 351 s tracks within 6% of Playground's; A3 cleared
- orun18 A1: Playground Go1 joystick (flat) trained from its published config and judged by D3

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

Stopped by the owner at 7.2 h to start orun19 on sphere feet. The trainer is not the problem: A3 cleared (Go1, our trainer within 6% of Playground). Leo with speed alone trots at 2.59 m/s without falling (B1), and imitating the dog clip gives a rotary gallop that settles at 1.6-1.9 m/s whatever it is commanded (C3). Every leo policy ran on its toes with the paw pin shut. The cause is geometry, not the spring: the hind pad touches 15 mm behind the pin, so stance load locks the pin on its stop at any spring rate (governor tall-bay-3130). The owner chose sphere feet over a paw redesign.
