# orun10 J: the courses in the engine (ADR-772)

Verified against source: 2026-10-18. Frozen run evidence.

`~/cadex-projects/orun10-jump` is `orun10-cat` (`0f036864`'s cat, the same
script) with `course` defaulting to 8. Its accepted revision `b693771f` has a
`leap` task (the C1 actor with the height scan, 2.5 m/s held, 12 s) on the J1
course. A course changes the model (`4f622c8a`), so a leap policy trains on
its own bundle; the gallop project is untouched.

| course | what | platforms (near edge at x = 3 m, 1.2 m wide) | spec |
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

Not yet measured: a training iteration's cost on these courses (the 5090 is
running s1-g1), and any policy's leap.
