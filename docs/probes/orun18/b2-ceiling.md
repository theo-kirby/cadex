# orun18 B2: leo's speed-only top speed, read against the other runners

Verified against source: 2026-10-23. Reads B1's end judgement
(`b1-s2-180.md`, policy `8adbb84f`) beside sgt-4-120, the cats of orun7 and
orun10, and A's Go1. Hip heights are measured by `froude.py` on each
model's first keyframe: the hind hip-pitch joint's anchor above the lowest
point of its leg's collision geoms.

```
F=docs/probes/orun18/froude.py
CUDA_VISIBLE_DEVICES= pixi run python $F ~/cadex-projects/leo/runs/b1-s2/train/cat_model-model.xml j_hip_l,j_hip_r 2.59 2.66 2.71
CUDA_VISIBLE_DEVICES= pixi run python $F ~/cadex-projects/orun10-cat/runs/s1-g4/train/cat_model-model.xml j_hip_l,j_hip_r 4.498
CUDA_VISIBLE_DEVICES= pixi run python $F ~/cadex-projects/orun7-cat/runs/f1-g2/train/cat_model-model.xml j_hip_l,j_hip_r 4.17
CUDA_VISIBLE_DEVICES= pixi run python $F ~/menagerie/mujoco_menagerie/unitree_go1/go1.xml RL_thigh_joint,RR_thigh_joint 1.526 2.482
```

## The bodies

| robot (model) | mass kg | actuators / joints | hind hip height m | shoulder, hip, knee peak N·m |
|---|---|---|---|---|
| leo v05 (`59bc5407`) | 31.5 | 26 / 48 | **0.396** | 53 (AK10-9) |
| orun10-cat (s1-g4's model) | 31.6 | 28 / 34 | 0.395 | 53 |
| orun7-cat (f1-g2's model) | 31.1 | 27 / 28 | 0.390 | 53 |
| Unitree Go1 (Menagerie) | 12.7 | 12 / 13 | 0.297 | 23.7 (thigh), 35.55 (calf) |

`retarget.py` puts leo's hip height at 0.387 m, to the paw's foot point
rather than to the lowest collision point. Below, Froude numbers use 0.396
for every cat, so the cats compare on one rule.

## Top speeds as Froude numbers (Fr = v² / g·h)

| run | what it is | speed m/s | Fr |
|---|---|---|---|
| **B1, b1-s2 at 180** | speed only, cold, 180 it; trot held over the last 2 s at command 1500 (min seed 2.53) | **2.59** | **1.73** |
| B1, best 2 s window on any seed | 2400 command, before the switch to the half-bound | 2.71 | 1.89 |
| sgt-4-120 (orun17) | 18 terms with a reference schedule, at 2400 commanded | 2.66 | 1.82 |
| orun7 f1-g2 | a gallop task with its clip, owner-accepted F1 | 4.15–4.17 | 4.55 |
| orun10 s1-g4 | gallop task with its clip, speed paid to 7 m/s, warm from s1-g1's 280 it; median / max of 10 seeds | 4.486 / 4.498 | 5.18 / 5.22 |
| Go1 A1, top of Playground's range | judged at 1.5 m/s commanded | 1.526 | 0.80 |
| Go1 A1, past the range | judged at 2.5 m/s commanded, 0/10 falls | 2.482 | 2.11 |

The charter cites 4.64 m/s for orun10. The highest orun10 speed in
`docs/probes/orun10/` is s1-g4's 4.498 m/s on one seed, so this table uses
it; 4.64 m/s would be Fr 5.54.

## Read

- **2.59 m/s is not leo's ceiling, and B1 does not show one.** Reward per
  step was still rising at 179 (11.68 at 150, 12.41 at 179, ~0.9 per 25
  iterations), and every command above 1.5 m/s first reaches ~2.6 m/s for
  1–2 s before the policy changes gait and settles slower. What B1 shows is
  how fast 180 cold iterations of speed alone make it, not how fast the
  body goes.
- **The same mass, height and drives have gone 1.6–1.7× faster.** orun7's
  and orun10's cats weigh 31 kg, stand 0.39–0.40 m at the hip and carry the
  same 53 N·m drives; they galloped at 4.2–4.5 m/s (Fr 4.5–5.2). Those runs
  differ from B1 in three ways that B1 cannot separate: they followed a
  gallop clip, they trained longer (s1-g4 is ~380 iterations from cold),
  and their body has 14–20 fewer joints (no push-rod loops, no sprung paw
  pin). So a ceiling set by the drives alone is ruled out as an explanation
  for 2.59 m/s; the gait search and the extra joints are not.
- **Against the Go1, leo is not slow for its size.** Leo's 2.59 m/s is
  Fr 1.73. The Go1 at the top of Playground's trained range runs Fr 0.80,
  and Fr 2.11 when commanded past it. Playground's recipe asks for a slow
  trot; leo's speed-only task asks for 5 m/s and gets about the Go1's
  out-of-range Froude number in a trot.
- **What binds now is a drive, then the stride, not the foot.**
  - *A drive.* The fore scapula and shoulder run 1.2–1.8× their rated RMS
    at every command, at their peak (margin 0.00); the shoulder and elbow
    are at their clamp on 0.05–0.17 of frames. The hind hip and hock stay
    at 0.2–0.85 of rated, the knee about 1.0. The fores carry the run.
  - *The stride.* Above 1.5 m/s commanded the policy leaves the 5 Hz trot
    for a ~3.2 Hz half-bound that settles at 1.6–1.9 m/s, slower the
    higher the command. The faster gait exists in the policy for 1–2 s and
    is given up: a gait the reward has not yet paid it to keep.
  - *Not the foot.* The hind paw is digitigrade throughout (heel 0.00,
    U 0.00, heel 70–74 mm up), pins are calm (p95 ≤ 180 °/s), and nothing
    in the hind leg is near its limit.
- **It does not settle the owner's question alone.** B1 says the style
  terms are not what holds sgt-4-120 to 2.66 m/s: speed alone reaches the
  same speed, with no heel. Whether more iterations, a clip, or fewer
  joints buy the orun10 cats' 4.5 m/s on leo is what C3 (the dog's gallop
  as the clip) and a longer B1 test.

## Not done here

No longer B1 run was trained. A warm continuation of b1-s2 on the same task
(the long-term rung) would show whether the half-bound gives way to a held
faster gait; this report does not predict it.
