# orun21 M0: where a design-to-policy iteration's time goes

Verified against source: 2026-10-28. Frozen run evidence; read it, never cite
it as current.

This is M0's first half: **the log pass** over the last three Ouroboros runs,
plus one timed measure the log pass pointed at (the closing view). The timed
fresh half (warm and cold builds of leon V and the biped, steps/s of each tier,
the suites) is not measured yet; the ranking below is provisional until it is.

## 1. The log pass

`m0_logs.py` (this directory) reads every role session's stream-json
transcript in a run's `.ouroboros/runs/<run>/transcripts/` and splits its wall
time into model time, foreground tool time by kind, and idle time spent waiting
for a background task of that kind to finish (a session that ends its turn and
is woken by a task notification). Kinds are regexes on the command text; a
`until … sleep` loop is counted as waiting on whatever it polls. "model" is an
upper bound: it is every gap between a tool result and the next assistant
event, so API latency and any idle gap with no finished task to blame land in
it.

    python3 docs/probes/orun21/m0_logs.py .ouroboros/runs/orun20 \
      ~/cadex-projects/leon-iv/.ouroboros/runs/l4r1 ~/cadex-projects/leon-v/.ouroboros/runs/l5r1

| run/role | sessions | wall h | model | build | train | judge | test | memory | other |
|---|---|---|---|---|---|---|---|---|---|
| orun20/actor | 7 | 4.85 | 0.99 (20%) | **2.97 (61%)** | 0.11 (2%) | 0.00 | 0.15 (3%) | 0.00 | 0.64 (13%) |
| orun20/critic | 6 | 0.01 | 0.01 | | | | | | |
| orun20/scribe | 6 | 0.34 | 0.10 (30%) | | | | | 0.24 (70%) | |
| l4r1/actor | 30 | 9.26 | 2.66 (29%) | 1.22 (13%) | **3.30 (36%)** | 1.40 (15%) | 0.23 (2%) | 0.00 | 0.52 (6%) |
| l4r1/critic | 29 | 0.09 | 0.08 | | | | | | |
| l4r1/scribe | 29 | 0.57 | 0.50 (88%) | | | | | 0.06 (11%) | |
| l5r1/actor | 22 | 8.01 | **2.37 (30%)** | **2.29 (29%)** | **2.23 (28%)** | 0.43 (5%) | 0.15 (2%) | 0.00 | 0.53 (7%) |
| l5r1/critic | 21 | 0.06 | 0.05 | | | | | | |
| l5r1/scribe | 21 | 0.42 | 0.36 (86%) | | | | | 0.06 (13%) | |
| **all three** | | **23.6** | **7.1 (30%)** | **6.5 (27%)** | **5.7 (24%)** | 1.8 (8%) | 0.5 (2%) | 0.4 (2%) | 1.7 (7%) |

orun20 was design only (leon I in four styles); l4r1 and l5r1 were design and
training (leon IV, leon V). Sessions include one retried actor attempt in l4r1.

Per iteration, from each run's `loop.log` (role end stamps):

| run | wall h | iterations | actor median (mean) | critic median | scribe median |
|---|---|---|---|---|---|
| orun20 | 5.29 | 6 | 46.3 min (48.4) | 0.2 min | 3.0 min |
| l4r1 | 10.43 | 29 | 18.1 min (18.9) | 0.3 min | 1.1 min |
| l5r1 | 8.59 | 21 | 11.6 min (22.3) | 0.2 min | 1.2 min |

What the logs say:

- **The actor is the iteration.** Critic and scribe together are 4–7% of a
  run's wall time. The scribe's largest share is model time; orun20's scribe
  spent 70% of its 0.34 h in `governor`/`ouroboros mem` calls (14 min over
  six folds and records), the edge-scaling cost noted when the graph moved to
  Flywheel. In l4r1 and l5r1 memory is 11–13% of the scribe, about 4 min a run.
- **Builds, training and the model are a third each** on the training runs.
  On the design-only run builds are 61%. Judging is 5–15%, tests 2–3%.
- **Waiting on usage cost nothing in these three runs.** No `rate_limit_event`
  was `rejected`; l5r1 ran 346 events at `allowed_warning`, none blocking, and
  no `loop.log` shows a usage wait or retry for capacity.
- **Model time is turn count.** l5r1's actor took 1,114 turns for 2.37 h of
  model time, 7.7 s a turn; l4r1 1,416 turns, 6.8 s; orun20 471 turns, 7.6 s.

### What an actor reads

From the `usage` of each session's first and last assistant message (input +
cache creation + cache read), and the text of every tool result (chars/4):

| run | context at turn 1, median | at the last turn, median | text tool output per session | images read |
|---|---|---|---|---|
| orun20 | 56.7 k tokens | 136.7 k | 26 k tokens | 25 |
| l4r1 | 46.9 k | 121.3 k | 25 k | 30 |
| l5r1 | 47.5 k | 134.3 k | 28 k | 14 |

Of the ~47 k at turn 1, the files this repo controls are small, by chars/4:
`AGENTS.md` 3.5 k, `.ouroboros/goal.md` 4.7 k, the auto-memory index
`MEMORY.md` 2.1 k, and the orient block (frontier, architecture head, tail)
roughly 6–8 k. The rest is the harness's own system prompt and tool schemas.
Every turn re-reads the whole context from cache: l5r1's actor read 126.9 M
cached tokens over 1,114 turns, about 114 k a turn. A token cut at the top of
the prompt saves on every turn, but the context doubles within a session from
tool output and the actor's own work, so the prompt is not the main reader.

## 2. Timed: the closing view, alone

GO1-BASELINE.md found the end of a run 24 s slower than in orun18. ADR-835's
closing view is the suspect: after the last iteration the trainer JIT-compiles
and runs a `--view-seconds` (default 10 s, 500 steps) deterministic rollout of
the witness batch (`view_rollout`, `training/cadex_train.py:4343`, called from
`train` at :4550). Timed on its own with `m0_view_screen.sh`: run1's Go1
command at 100 iterations (8192 envs, unroll 20, 16.4 M steps), no
checkpoints, seed 1, `--view-seconds 10` against `0`, twice each, alternating,
alone on the 5090 under `systemd-run --user --scope -p MemoryMax=30G`.
Seconds from launch (`orun21-lab/go1/m0-view/v*/train.log`, each line
stamped by the script):

| run | first iteration | iteration 99 | policy written | end to end | last iteration → written |
|---|---|---|---|---|---|
| view 10, a | 52.4 | 72.7 | 123.4 | 123.9 | **50.7** |
| view 0, a | 51.2 | 71.4 | 97.4 | 97.9 | **26.0** |
| view 10, b | 52.6 | 72.8 | 124.1 | 124.6 | **51.3** |
| view 0, b | 52.6 | 72.8 | 98.8 | 99.3 | **26.0** |

- **The closing view costs 25.0–25.3 s**, a fixed cost whatever the run's
  length. It is the 24 s seen on run1. On a Playground-sized run (372 s) it
  is 7%; on this screen it is 20% of the wall time.
- **The rest of the end costs 26 s too**, with no view and no checkpoint:
  the final `snapshot` (the witness rollout's own compile, the policy pack)
  and the witness check before the policy is written. Not split further yet.
- **Training proper is 20 s of a 124 s screen (16%).** Compile before the
  first iteration is 51–53 s, the end 51 s. A screen of minutes is mostly
  fixed cost, and the fixed cost is the same on a 200-M-step run.
- The view was written (`v10-*/view/trace.json`) and the reward curves agree
  (0.0184 / 0.0185 / 0.0182 / 0.0183 per step at iteration 99), so the
  `--view-seconds 0` runs are the same training.

## 3. The sinks, provisionally ranked

By time saved per unit of work, from the log pass and §2 only; the timed half
re-ranks it.

| rank | sink | evidence | size | likely cut |
|---|---|---|---|---|
| 1 | trainer fixed cost per run: compile 52 s + end 51 s | §2 | ~100 s on every run; 83% of a screen | compile the view rollout with the witness rollout or reuse its trace; cache the JIT (`jax` persistent cache); time the end's 26 s |
| 2 | builds on the actor's critical path | §1: 27% of all actor time, 61% on design-only | 6.5 h of 23.6 | timed half measures warm vs cold; the training-model route (P1) keeps CAD builds out of training loops |
| 3 | training runs | §1: 24% | 5.7 h | fast training models (P1) and budgets; per-run fixed cost is rank 1 |
| 4 | model turns | §1: 30%, 7–8 s a turn | 7.1 h | fewer turns per unit: tools that answer in one call (judges, one-command routes) |
| 5 | judging | §1: 8% | 1.8 h | one generic judge (P1, G2) |
| 6 | memory writes | §1: 14 min of orun20's scribe | small | not ours to cut this run (Flywheel) |
| — | waiting on usage | §1: none | 0 | — |

Not taken on yet: which three S1 takes on is decided when the timed half is in.
