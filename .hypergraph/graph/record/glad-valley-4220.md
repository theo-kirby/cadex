---
node_id: b9788920-2937-5c9e-b95d-e11a268cb366
slug: glad-valley-4220
title: 'P1 circle-11: state-gated catch warm from circle-10 passes 7/8; 9102 lost to the kick, circle iteration stops'
created_at: '2026-10-08T04:15:47+00:00'
parents:
- tidy-badger-2182
summary: ''
---
## What

First, the critic's fix-first: why `hypergraph check` showed 274 violations.
Then P1 circle-11. It is a reward-only curriculum step (ADR-597), warm from
circle-10's final policy, into a new task `task_circle_catch` on
`orun5-ball-plate`. It was trained on the GPU and evaluated on frozen seeds
9101–9108. REPORT §6, the status row, defect 11 and LESSONS W5 are updated
(commit `0d3dd298`).

## Why

The critic asked for two things.

**Get check back to exit 0.** Nothing in the graph regressed. The
violation count depends on whether `--config` is passed:

| command | result |
|---|---|
| `hypergraph check --record .hypergraph/cache/record.json --state .hypergraph/cache/state.json` | 274 violations |
| the same with `--config .hypergraph/config.yml` | **0 violations**, 6 warnings, exit 0 |

The second is the documented invocation (`.hypergraph/AGENTS.md`). Without
the config, the checker has no epoch marker, so the 14 pre-epoch legacy
nodes are not exempted, and it has no `plan` view. The CLI is at 0.0.13,
the same as `hypergraph_version` in the config, so `hypergraph upgrade` was
not needed. No fix was applied because there is nothing to fix. The next
critic should run check with `--config`.

**circle-11.** The critic's next unit: warm from circle-10 with an early
catch term, on frozen seeds 9101–9108, with the kick and the spec
unchanged. If it reached 8/8, render the hero. If not, record the numbers
and stop iterating on the circle task.

**One deviation.** The critic suggested `exp(-r²/σ²)` weighted over the
first ~0.5 s. A reward expression cannot name episode time: reward names
are the declared channels only, and only control formulas see `time`. So I
took the critic's alternative, gating on state: lower the near-point
weight beyond a radius. I added a state-gated catch to it.

## Method

**Task.** `task_circle_catch` is identical to `task_circle_phase` (same
model, the phase goal `lead`, terminations, randomisation, kick and
`circle_success`), except for the reward:

- `over = max(r − 48, 0)`, written with `abs`;
- `far = tanh(over / 4)`;
- the near-point term is multiplied by `(1 − far)`;
- a new catch term, `−far · tanh(v_r / 100)` at +1.0, where
  `v_r = (b_x·bv_x + b_y·bv_y) / (r + 5)` and `bv` is the privileged
  speed the reward already reads.

The other terms are unchanged.

**Training.** Accepted with `cadex script --set`. Then
`cadex_cli.loop.register` and `launch`:

- warm from `assets/circle-10.cxpolicy`, with the parent task
  `runs/circle-10/train/task_circle_phase-task.json`;
- 800 iterations × 256 envs, seed 17, a checkpoint every 200, budget
  900 s;
- `CUDA_VISIBLE_DEVICES` unset.

The trainer logged `init-from circle-10.cxpolicy` and "curriculum: the task
changed in ['label', 'reward']".

**Evaluation.** The policies were stored as `circle-11.best.cxpolicy`
(33b73809…) and `circle-11.cxpolicy` (a6d3d7e8…), declared as
`policy_circle_catch` and `policy_circle_catch_final`, and evaluated with
`cadex evaluate --film none`.

## Result

**circle-11 trained.** It ran on the GPU and exited 0 in 382 s. Reward per
step was 0.84 at iteration 0, best 2.54 at iteration 523, and ended at
2.51. The warm start was accepted as a reward-only change.

**Evaluation on frozen seeds 9101–9108:**

| policy | evaluation | seeds passing | on the passing seeds |
|---|---|---|---|
| best | `8cfdf569c42b-33b73809c148` | **7/8** | 2–3 laps (turns +2.38 to +3.39), mean radius 33.8–35.7 mm |
| final | `8cfdf569c42b-a6d3d7e85fe2` | **7/8** | 2–3 laps (turns +2.36 to +3.39), mean radius 33.8–35.6 mm |

- **Seed 9101 now stays on**; circle-10 lost it.
- **Seed 9102 still fails**: "ball reached the rim" at 0.30 s (best) and
  0.28 s (final).
- In 9102's trace, the kick drives the ball out at about 250 mm/s. It has
  slowed to about 140 mm/s when the panel reads it past 62.5 mm. The
  policy brakes, but within the ±10° command range it does not stop in
  time.

**The circle task is not a spec pass**, so no hero was rendered. As the
critic directed, **iteration on the circle task stops here at 7/8**, with
the kick and the spec unchanged. P1's circle half stands on the charter's
*otherwise* branch: the predicate fails a rocking trace and passes a
circling one, and 7 of 8 seeds pass every predicate.

**Gates.**
- The repo change is docs only (REPORT, LESSONS). No test pins them, and
  no code changed, so the suites were not rerun.
- On the scratch project, the accepted script adds `task_circle_catch`,
  `policy_circle_catch` and `policy_circle_catch_final`. Nothing is
  committed from it: no policy, trace or checkpoint.

**Other notes.**
- No new dependency.
- The tail is now two records: circle-10's and this one.

Dispatch closed: 1 unit — check's 274 violations come from running it without `--config` (0 violations with it, nothing to fix); circle-11 (warm, state-gated catch) passes 7/8 frozen seeds, 9102 still lost to the start kick at 0.28 s, so circle iteration stops and P1's circle half stays on the otherwise branch

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 0d3dd29817499bae10c6d61588e878a5a63364db

## State Impact

- target: peaceful-orchard-2220 — circle-11 (task_circle_catch, warm from circle-10 by ADR-597, reward-only: near-point gated off beyond 48 mm plus a radial catch term; GPU 382 s): best and final each pass 7/8 frozen seeds (2-3 laps, 33.8-35.7 mm); seed 9102 still reaches the rim at 0.28-0.30 s; not a spec pass, and circle iteration stops per the critic
- target: grand-otter-5246 — REPORT section 6 circle-11 paragraph and table, status row and defect 11 updated to 7/8; LESSONS W5 updated (commit 0d3dd298)
