---
run: orun6
machine: sb1x
started: 2026-10-14T15:40:31
ended: 2026-10-15T07:32:25+00:00
hours: 11.6
state: killed
iterations: 25
commits: 25
criteria_ticked: 0
criteria_closed: 0
criteria_total: 9
merged: 5951235e79cea5b54f1deaf19c73f6f6d5b08110
branch: ouroboros/orun6
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun6

25 iterations in 11.6h on `sb1x`, killed (-). Branch `ouroboros/orun6`, merged as `5951235e`.

## The numbers

| | |
|---|---|
| iterations | 25 (changed 22, recorded 18) |
| commits | 25 — 70 files changed, 32928 insertions(+), 178 deletions(-) |
| criteria | **this run ticked 0**; 0 of 9 checked at the tip |
| reverts | 0 |
| verdicts | continue 25 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5 |
| usage | claude seven_day 22% -> 29% (+7 this run); claude five_hour 25% -> 9% (-16 this run) |

## What landed

- D1: the proxy screens a clip by inverse dynamics, and held replays leave the path free (ADR-711)
- D1: a drive proxy loop screens drives and masses on the exported model (ADR-710)
- G2: an episode can start at a random phase of its gait reference (ADR-709)
- G2: a drive's continuous rating and smoothness against the reference clip (ADR-707, ADR-708)
- G2: a task tracks its gait reference through channels on a gait clock (ADR-706)
- G2: a success spec can judge a gait against the task's own reference (ADR-705)
- G2: a success spec can bound drive smoothness, clamp load and cost of transport (ADR-704)
- G1: a task carries a gait reference, and the dashboard plays it (ADR-703)
- G1: a procedural gait reference generator, CadexGait (ADR-702)
- B1: the trainer can floor each step's reward (ADR-700); a task may observe 128 sensor channels (ADR-701)
- T1: a task observes a joint's acceleration; every standard regulariser is a reward term (ADR-699)
- T1: a task observes foot contact (ADR-698)
- T1: a task observes its own commands (ADR-696); reward expressions may be 512 nodes (ADR-697)
- training: compile the model once; host memory no longer scales with --envs (ADR-695)
- dynamics: a rollout trace records joint state and delivered drive effort (ADR-694)

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

**Stopped by the owner at iteration 26 (11.6 h of a 48 h ceiling)** to replace the PPO core with Brax's. The operator committed the interrupted unit, ADR-711 (its 23 tests pass).

**The headline is B1: Cadex's trainer is the bottleneck, not the physics and not the reward.**
- Playground's Go1 joystick recipe trains a 933 mm/s diagonal trot in 378 s and 206 M steps on the 5090. It runs on the same MuJoCo/MJX physics.
- `training/cadex_train.py`, on the same Go1, Playground's full expressible reward and the same budget, learns to stand: −2…4 mm/s.
- The ablations ruled out:
  - the observation frame (body-frame inputs);
  - the stateless and stateful reward terms;
  - reward clipping (ADR-700's floor);
  - host memory (ADR-695).
- What is left is the PPO core: minibatching, value bootstrap at truncation, and action squashing, then observation noise and command resampling.
- Every cat tracking run (track-s1, track-s2) fell on 10/10 seeds within about 2.6 s. That cannot be read as the cat's fault until the trainer learns Go1.
- Lesson: **benchmark the trainer before tuning anything that runs on it.** Twelve panel-cat runs and two orun6 runs were spent on a learner that cannot learn a known-easy task.

**Smoothness bar.** The owner's "half r5's RMS" was unreachable: the known-good Go1 is no smoother by raw RMS (318 °/s and 10,040 °/s², against r5's 320 and 7,983). It was replaced mid-run by two bounds: within 1.5× of the reference clip's own RMS, and a high-frequency share at most half r5's 6.4 % (ADR-708). Raw RMS grows with stride and speed, and jitter does not.

**The cat is under-driven (D1, ADR-710, ADR-711):**
- Even the r5 trot runs 9 of 19 drives above their rated RMS torque.
- The fore girdle as built reaches 1.7× rated, with 28 % of the time at peak.
- AK10-9 drives at the scapula, shoulder and elbow are the only screened family that holds a supported trot.
- A wrist drive moved inboard cuts swing load by 30–40 %.
- A 15 % lighter cat barely helps.
- **New finding (ADR-711):** the exported position servo (kp ≈ 60 N·m/rad) misses the clip by 16° RMS against a ±12° scapula stride. Freed replays brake and reverse. The servo gains, not only torque, limit tracking. Revisit kp/kd against the AK drives' MIT-mode range.

**What worked:**
- the H1 progress page (`~/orun6-progress/build.py`);
- CadexGait (8 gaits, IK inside the joint limits) and the clip playback on the dashboard;
- the T1 channels;
- the G2 predicates;
- a critic that kept naming the overdue criterion.

**What did not:**
- The trainer OOM at `--envs 8192` (one host MjModel per env) killed the whole loop. ADR-695 fixed it, and long training now runs in its own `systemd-run` scope.
- The critic accepted parking B1 for 10 iterations while G1, G2 and D1 built on an unproven learner. A blocker on the learning path should outrank the features that depend on it.

**Next:** swap the PPO core for Brax PPO, operator-planned 2026-10-15. Then re-run B1 (Go1 must trot), then P1 with the AK10-9 fore girdle, a stiffer servo, and tracking.
