# orun10 J: the courses in the engine (ADR-772)

Verified against source: 2026-10-18. Frozen run evidence.

`~/cadex-projects/orun10-jump` is `orun10-cat` (`0f036864`'s cat, the same
script) with `course` defaulting to 8. Its accepted revision `b693771f` has a
`leap` task (the C1 actor with the height scan, 2.5 m/s held, 12 s) on the J1
course. A course changes the model (`4f622c8a`), so a leap policy trains on
its own bundle; the gallop project is untouched.

| course | what | platforms (near edge at x = 3 m; 1.2 m wide, 6 m since the J1 probe below) | spec |
|---|---|---|---|
| 8 | J1 | 300 mm, 1.5 m long, drop at 4.5 m | `j1_spec`: completed, no fall, `platforms_crossed ≥ 1`, 6 m made good |
| 9–13 | J2 ladder | the same at 200 / 400 / 600 / 800 / 1000 mm | `j2_spec_<h>`: as J1 |
| 14 | J3 | 300 / 600 / 400 / 200 mm, 1.2 m each, gaps 0.5 / 0.6 / 0.7 m | `j3_spec`: no fall, `platforms_crossed ≥ 3`, `gap_touches ≤ 0`, 10.5 m |

Built with the engine's builder (`courses.py` in the run's progress folder):
each J course draws flat to x = 3 m, the platform's top, then flat again; J3's
gaps read at 4.2, 5.9 and 7.7 m, 500/600/700 mm wide.

Leap metrics (ADR-772), stance against the course's ground:

- synthetic, two platforms and a 300 mm gap: cleared 1, touches 0; with a
  foot down in the gap, touches 1, cleared 0; take-off 3.0 m/s, rise 500 mm.
- physics, J1 model, cat dropped from its keyframe in stock MuJoCo: paws
  settle 0.13–0.24 mm into the ground under them, on the ground and on the
  300 mm top alike; `highest_platform_reached_mm` 0 and 300.

## J3 built (course 14)

`~/cadex-projects/orun10-j3` is `orun10-jump` with `course` set to 14
(`cadex params --set course=14`, 9 min 38 s; the tessellation is kept): accepted revision
`5da5d558`, a `leap` task whose spec is `j3_spec` (completes, no_fall,
three_platforms, no_gap_touch, lands_running), on a model of its own
(`cat_model` sha256 `2b9a2377`). Its terrain carries the four blocks at
x 3.0–4.2 / 4.7–5.9 / 6.5–7.7 / 8.4–9.6 m (300 / 600 / 400 / 200 mm), and
`platform_gaps` reads the three gaps at 4.2, 5.9 and 7.7 m, 500 / 600 /
700 mm wide.

Leap metrics on this model in stock MuJoCo (the cat dropped from its
keyframe, 1 s; `gap_check.py` in the run's progress folder):

| drop at (x, height above the ground) | paws over the ground under them | highest platform | gap touches |
|---|---|---|---|
| 1.0 m, 50 mm (run-up) | −0.13 to −0.25 mm | 0 | 0 |
| 3.6 m, 350 mm (300 top) | −0.13 to −0.25 mm | 300 | 0 |
| 5.3 m, 650 mm (600 top) | the same | 600 | 0 |
| 7.1 m, 450 mm (400 top) | the same | 400 | 0 |
| 9.0 m, 250 mm (200 top) | the same | 200 | 0 |
| 8.05 m, 50 mm (in the 700 mm gap) | fore paws −0.1 mm on the gap's floor, hind 13 mm above the gap's floor, so out of stance (what holds them up was not looked at) | 0 | 2, both in gap 3 |
| 4.45 m, 50 mm (in the 500 mm gap) | the body overlaps both walls and is thrown clear | 0 | 0 |

The cat does not fit in the 500 mm gap: dropped into it, it is thrown clear. The settled pose on the 300 mm top, carried rigidly
along +x over gap 1 onto the 600 mm top (a 450 mm arc), reads
`gaps_cleared` 1, `widest_gap_cleared_mm` 500, `gap_touches` 0,
`highest_platform_reached_mm` 600 and a rise of 610 mm. Its take-off speed reads
`None`, since the carry starts 0.07 s before the take-off, inside the 0.2 s window.

Not yet measured: a training iteration's cost on these courses (the 5090 is
running s1-g1), and any policy's leap.

## J1 probe: the run-up and the ledge face, zero-shot (orun10 iteration 8)

The leap task's actor reads the same 77 channels as orun9's C1 policies
(checked on c1-c8 to c1-c11b), so a C1 policy can warm-start a leap screen.
To see what the J1 spec meets in its first seconds before training on it,
c1-c11b's final policy (orun8-cat, read in place) was played on the J1
bundle through the engine's evaluation child. The copy played is re-headed
with the leap bundle's task and model digests, its weights unchanged, and is
declared nowhere (`judge_leap.py` in the run's progress folder). The trace
positions below are the chest frame's, which starts at x = 0.

**On the 1.2 m course** (revision `b693771f`, model `4f622c8a`): 0/10.
`up_across_down` 0/10 (`platforms_crossed` 0 on every seed), `lands_running`
3/10. Seven seeds stall with the chest at x 2.43–2.69 m, against the face.
Three (1003–1005) drift past y = 0.6 m by 2 s and run round the ledge: 18–20 m
made good with no platform reached. Since a detour pays the run reward, the
ledge has to span the path.

**The course is 6 m wide now** (`J_WIDTH_MM = 6000`, y ±3 m, every J course
8–14). orun10-jump accepted `b59eb2b1` (model `73548790`), fit passing. Re-run
of the same probe:

| | value |
|---|---|
| pass | 0/10 |
| `up_across_down` | 0/10, platforms crossed 0 everywhere; highest reached 0 |
| `lands_running` | 0/10, made good 2.46–2.68 m (median 2.60) |
| `completes` / `no_fall` | 9/10 / 10/10; seed 1005 tips at 9.0 s against the face |
| chest stalls at | x 2.43–2.80 m, 1.68–2.94 s |
| run-up speed, 0–0.2 s | 0.89–1.27 m/s (the trot reference's 1 m/s start) |
| run-up speed, 1.0–1.5 s | 1.22–1.64 m/s against the 2.5 m/s command |
| best 2 s mean | 1.17–1.24 m/s |
| worst drive | RMS 0.84–1.55× rated (median 1.24×), at peak (margin 0) on every seed |

What a J1 screen starts from: the setup is sound (no fall and no tip in the
first second on any seed; the cat leaves the keyframe at the reference's
1 m/s). But C1 meets the face at 1.2–1.6 m/s, not the commanded 2.5 m/s, and
shows no leap: it pushes into the wall. A leap screen warm from C1 has to buy
both the run-up speed and the leap. The J2 rungs and the J3 project
(`orun10-j3`, still 1.2 m wide at `5da5d558`) take the 6 m width on their next
build.
