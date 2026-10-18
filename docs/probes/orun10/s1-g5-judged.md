# orun10 S1: s1-g5 judged, and s1-g6 at 3.0 Hz

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 8).

s1-g5 extends s1-g4 (`s1-g4-judged.md`): warm from s1-g4's final policy
(4.498 m/s), the same gallop task (`c198a097`, clip at 2.4 Hz), learning rate
3e-5, a 10-iteration critic warm-up, 100 iterations, a checkpoint every 25.
The trainer's reward per step peaked at 17.02 at iteration 13 and ended at
16.94. Every checkpoint was judged on the bundle's own `gallop_spec`, seeds
1001–1010, with the engine's evaluation (`orun10-cat/evaluations/s1-g5-*`).

| checkpoint | pass | failing | top speed, median (min–max), m/s | worst drive's RMS over rated | peak margin |
|---|---|---|---|---|---|
| s1-g4 final (start) | 0/10 | top_speed | 4.486 (4.466–4.498) | 1.50× | 0 |
| best (it 13) | 0/10 | top_speed | 4.469 (4.464–4.476) | 1.50×, j_elbow_l | 0 |
| 25 | 0/10 | top_speed | 4.391 (4.368–4.399) | 1.49× | 0 |
| 50 | 0/10 | top_speed | 4.258 (4.241–4.270) | 1.47× | 0 |
| 75 | 0/10 | top_speed | 4.271 (4.255–4.287) | 1.46× | 0 |
| final (it 100) | 0/10 | top_speed; completes and upright 9/10 (seed 1006 tips, 32.1°) | 4.320 (3.430–4.334) | 1.64×, j_elbow_l on 9 seeds | 0 |

None of the checkpoints passes the start. Every one keeps a flight on every
stride (two 60 ms flights per cycle) and the 2.38 Hz clip clock: a cycle of
0.87–0.91 m per foot-strike pair at 4.77 strikes/s. Extending at the 2.4 Hz
clip is over: from 4.50 m/s the top speed only falls.

Next is **s1-g6**. orun10-cat was rebuilt with `gallop_hz=3.0` (revision
`6cd54655`; the gallop task's reference is now "rotary gallop 0.7 m, 3 Hz").
A warm start may not move a reference clock, so s1-g6 trains cold: 200
iterations, a checkpoint every 50, in scope `o10-s1-g6`. At 3.0 Hz, s1-g4's
1.86 m cycle would make 5.6 m/s.

s1-g6's first iterations match s1-g1's cold start: σ 46 at iteration 0, then
0.87; the loss is 3.9e10 at iteration 0 (s1-g1: 324) and 87 by iteration 2.
