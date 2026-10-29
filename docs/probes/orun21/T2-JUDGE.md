# T2: the first go-to-point judgement on held-out terrain

Verified against source: 2026-10-29 (this commit). Frozen run evidence; read it, never cite
it as current.

ADR-857's screen `go1-around/run1` (65.5 M env steps, warm from `go1-levels/run1`,
pool laid round the start) judged with G2's judge, unchanged, on held-out courses
(ADR-858).

## How

- **Courses.** `g2_judge.py POLICY TASK OUT --level L` plays held-out sequence
  `heldout:s` (8 points, 2–5 behind) on
  `CadexDynamics.terrain_evaluation_course(terrain, s, level=L)`, for s = 0–9. That is
  the pool's own draw with the key `eval:<s>:<n>`, so no seed plays a course the
  trainer drew. `--flat` plays an empty course: every slot parked, the plane at z = 0.
  The ten courses keep the same layout at every level. Only the magnitudes move
  (level l of 8 draws steps of 10 + 120·l/8 to 10 + 120·(l+1)/8 mm).
- **Player.** `cadex_goto.py play --course` stands the course in the model's slots.
  A check against the bundle's own compiled course 0 agreed to 5e-5 m on every terrain
  geom, and its ground agreed with `CadexDynamics.terrain_box_ground_mm` to 1e-13 mm
  at 2,000 points. A fall is the base under half its start height over the ground
  beneath it, or tipped past 60°.
- **Bar.** G2's own: reach 0.3 m, hold 0.15 m, no fall, straight-leg speed within 15%.
  No widening.

## Ten held-out seeds per row

`unreached` counts the points of 80 never reached. A `stall` is a straight leg read
at under 0.2 of its commanded speed.

| policy | ground | pass | reach | speed | falls | unreached /80 | stalls | total s |
|---|---|---|---|---|---|---|---|---|
| `go1-levels/run1` (parent) | flat | 2 | 10 | 2 | 0 | 0 | 0 | 960.4 |
| `go1-around/run1` it 200 | flat | **10** | 10 | 10 | 0 | 0 | 0 | 890.8 |
| | level 0 | 9 | 9 | 9 | 0 | 1 | 1 | 903.9 |
| | level 2 | 1 | 2 | 6 | 2 | 34 | 3 | 894.8 |
| | level 4 | 0 | 0 | 3 | 6 | 58 | 4 | 631.5 |
| | level 6 | 0 | 0 | 3 | 7 | 58 | 3 | 537.9 |
| `go1-around/run1` final (it 399) | flat | 3 | 8 | 3 | 0 | 8 | 2 | 947.3 |
| | level 0 | 4 | 7 | 4 | 0 | 10 | 2 | 953.0 |
| | level 2 | 0 | 1 | 2 | 2 | 42 | 6 | 913.1 |
| | level 4 | 1 | 1 | 5 | 3 | 54 | 5 | 806.6 |
| | level 6 | 0 | 0 | 3 | 4 | 59 | 6 | 737.6 |

Every hold that started stayed within 0.15 m. A short total time on terrain means the
episodes ended early, by falls.

## What it shows

- **Flat go-to-point survives terrain training at iteration 200 and regresses after it.**
  Checkpoint 200 passes flat ground 10/10, every leg within 0.86–0.97 of its
  speed. That beats both the parent (2/10, the share-0.5 slow walk, `kind-ridge-3238`)
  and G2's cold share-0.5 run (3/10). The final policy stalls. On flat seed 6 it
  stands still for 70 s at (−3.78, −7.08) with a 1.2 m/s forward command: four feet
  on the plane, no other contact, the actor holding a static pose. Training on past
  iteration 200 bought level, not skill.
- **Every terrain failure is at an edge.** At every failed seed on levels 2 and 4,
  for both checkpoints, the ground within 0.5 m of where the base stopped or fell has
  42–92 mm of relief. Those are the step and platform faces of the level's band
  (40–55 mm at level 2, 70–85 mm at level 4). The same layout stops the robot at
  the same spot on both levels: seed 2 at (2.33, −2.57) and (2.34, −2.60).
- **The curriculum's level is not a skill reading.** Training reported a batch mean
  level of 3.17, yet at level 2 the robot misses 34 of 80 held-out points.
  Promotion counts points reached without a fall, and an episode can earn it on the
  points it reaches before an edge.
- **What is binding, as a hypothesis.** The actor is blind. The bundle carries no
  height scan at all, so the policy reads only proprioception and the command. Facing a 40 mm face it cannot see, it does not lift its feet higher; it
  stops. The next step gives the actor a height scan (`role="policy"`, ADR-748),
  or a swing-height term the face rewards. It does not train longer at this
  setting.

T2 is not met: no level ≥ 2 passes a seed in more than one of ten.
