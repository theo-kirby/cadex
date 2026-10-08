---
node_id: 02b7277c-d6e9-5524-9aa3-172ec54e5e37
slug: dusty-canyon-3027
title: 'P1 circle evidence: laps bound fails a rocking ball and passes a circling one on the free-ball rig'
created_at: '2026-10-08T02:22:14+00:00'
parents:
- pale-brook-6092
summary: ''
---
## What

Produced P1's circle evidence on the rebuilt free-ball rig (`orun5-ball-plate`). The scratch project now has a circle task, `task_circle`. It rolls the ball anticlockwise round a 40 mm circle, and its spec bounds `completed ≥ 1`, `mean_distance_mm` in [30, 50] and **`laps ≥ 2`** (ADR-587), with no point goal. A probe, `docs/probes/orun5/circle_predicate.py`, drives the exported MJCF with a scripted tracker in two motions: rocking across the circle's top, and going round it. It holds each 10 s trace against the task bundle's own predicates using Cadex's `CadexEvaluation.motion_metrics` and `check`. The plot is `docs/probes/orun5/m1-rock-vs-circle.png` (41 KB). I also trained five circle policies and evaluated each with `cadex evaluate`.

## Why

The critic asked me to check that P1's circle evidence (a rocking trace fails, a circling trace passes) was actually recorded before writing C1, and to produce it if not. It was not recorded. `dusty-meadow-8719` showed it only on synthetic unit-test traces, and `smooth-stream-7287` listed the circle task as not rebuilt. So this unit produced that evidence, and C1 is the next unit. I did not write the report in this iteration because of the one-unit rule.

## Method

- **Circle task.** The reward follows the reference project's signed-progress design, with two changes: progress is capped at V = 60 mm/s by writing min(vt, V) with `abs`, and it is weighted by `exp(-(r-40)²/200)`, so it pays only near the circle. The tangential speed comes from the privileged world velocity. Terminations are the rim and "panel lost the ball". A second task, `task_circle_unsigned`, has the same spec and drops the signed progress term (the reward shape the reference said paid for rocking).
- **Training runs** (5090, 256 envs; evaluated with `cadex evaluate` on the 8 frozen seeds 9101–9108, noise-free):

  | Run | Training | Laps | Mean radius | Notes |
  |---|---|---|---|---|
  | circle-1 | uncapped reward, cold, 700 it | 10–11 | 26–28 mm | turns +10.8 |
  | circle-2 | capped, warm from circle-1, 700 it | 5–6 | 16–20 mm | |
  | circle-4 | radius-gated progress, cold, 1000 it | 4–5 | 19.5–24.5 mm | |
  | circle-5 | warm from circle-4, 1000 it, best 1.42 reward/step | 3–4 | 28.1–29.2 mm | 6 of 8 seeds completed |
  | unsigned-1 | cold, 1000 it | 4 | 19–21 mm | turns +4.1 to +4.7 |

  circle-3 was wasted: a failed `script --set` (a stale policy declaration) left the old reward accepted, so it trained the circle-2 reward cold. I did not evaluate it.
- **Probe.** The plate's component frame is the world at the solved keyframe, so its pose is the body's motion since then. The ball's body frame is its centre. The tracker is a PD law on the ball's true plate-frame position (3 rad/s, damping 0.7) plus the target's acceleration, giving tilt = a/(5/7·g), clamped to ±8°. It is a scripted controller, not a policy.

## Result

**On the rig's own physics, the circle spec's laps bound fails a rocking ball and passes a circling one** (probe run on `runs/circle-5`'s exported model and bundle):
- **Rock** (±25 mm across the circle's top at 0.4 Hz, a bearing swing of about ±35°): completed 1, turns **−0.005**, laps **0**, mean distance **45.7 mm**. Verdict **fail**, by `went_round` only ("laps is 0, under 2"). It *passes* the radius bound, which is exactly the circle-6 failure in the reference project that M1 replaces.
- **Circle** (40 mm at 0.3 Hz): completed 1, turns **+3.005**, laps **3**, mean distance **42.8 mm** (max 43.3). Verdict **pass** on all three predicates.

**No trained circle policy passes the spec yet.** Every one circulates (laps 3–11 on every seed), so none rocks, and the laps predicate passes all of them. All fail `on_circle`: their mean radius is 16–29 mm against a floor of 30, because each holds a circle tighter than 40 mm. Two seeds of circle-5 also ended early. The charter allows this "otherwise" branch for the circle half of P1. Training to a pass remains open: circle-5 is closest, and a warm continuation or a stronger radius term is the next step if time allows.

**Gates.** No engine or CLI code changed. The commit adds a probe script, a PNG and a ledger row. `test_licensing_compliance.py` passes (11 passed, 1 skipped). Neither the probe nor the plot names a reference project.

**Concerns:**
- **The project's script reverts on a failed set.** A failed `cadex script --set` that points at the project's own `script.py` restores it to the accepted revision. Twice that silently discarded my edit, because the stale `policy_circle` declaration failed the digest check. This is working as designed (only an accepted script persists), but it cost one training run. The lesson for an agent: drop a policy whose task digest changes in the same set, and pass `--replace`.
- **Scratch files.** The scratch policies are in the project's `runs/` and `assets/`. None is committed.
- **Tail.** One unreconciled record (this one).

**Next:** C1. Write `docs/probes/orun5/REPORT.md` and use `m1-rock-vs-circle.png` as M1's figure.

Dispatch closed: 1 unit — P1 circle evidence: on the free-ball rig a rocking ball (turns −0.005, mean r 45.7 mm) fails laps ≥ 2 and a circling one (turns +3.005) passes; five trained policies all circulate but none holds the 30–50 mm radius yet

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 401ba5bd6ee2ff1917e9f0cd829f3b2af05754b0

## State Impact

- target: peaceful-orchard-2220 — P1 circle half evidenced (commit 401ba5bd): task_circle on the free-ball rig bounds laps>=2 with no point goal; on the rig's own MJCF a scripted rocking ball (turns -0.005, mean r 45.7 mm) fails only went_round and a circling one (turns +3.005, mean r 42.8 mm) passes; five trained circle policies all circulate (3-11 laps) but none holds the 30-50 mm mean radius (best circle-5: 28.1-29.2 mm, 6/8 completed), so the circle task is not trained to a pass
