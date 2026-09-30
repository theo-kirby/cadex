---
node_id: 36ce6b3d-4eb1-572d-9658-bc6fb02cc9c9
slug: silver-harvest-8970
title: 'ot11 P4 reach on ot11-heron-1: four motivated rounds, last passes 9 of 10 seeds; warm start unreachable through train_status'
created_at: '2026-09-30T20:26:43+00:00'
parents:
- even-otter-4624
summary: ''
---
## What

ot11 P4 on reach: the product agent ran the training loop on a copy of Heron,
`ot11-heron-1` (copied with `cp -a` from `ot8-heron-b`, which stays
read-only). One pre-registered session, four motivated rounds, four
evaluations against the frozen reach spec on twenty held-out targets drawn
before any training. The last round passes 9 of 10 seeds; seed 1106 misses
Q2 by 0.7 mm.

Landed:
- `docs/probes/ot11/prompts/reach.loop.prompt.txt`, which mirrors
  `balance.loop.prompt.txt` and hands over the frozen reach spec in xscript.
  `rounds.py` is unchanged: it has no reach-specific code path.
- `docs/probes/ot11/runner/goals.py`, a runner that names no behaviour. It
  draws a spec's per-seed goals the way an evaluation does (`evaluation_task`,
  one `random.Random(seed)` stream, the engine's `draw_episode_goals`).
- `retained/r2-heron-1-targets.json`: the twenty held-out targets.
  `retained/p4-heron-1-preregistration.json`: the session bounds. Both were
  committed (`02603727`) before the session started.
- `retained/p4-heron-1-registration.json` and `retained/p4-heron-1-rounds.json`
  (no paths, no transcript), two r4 filmstrip PNGs (62 KB and 120 KB), and a
  README section.
- Three tests in `cli/tests/test_ot11_rounds.py`:
  - the reach prompt carries the contract's numbers;
  - the targets receipt obeys the contract's draw rules and hashes the
    prompt's spec block;
  - `goals.py` names no behaviour.

## Why

The critic named this unit: R2 as P4's proving ground. The asks were to copy
Heron into `ot11-heron-1`, add a reach loop prompt that mirrors the balance
one with no reach code path in `rounds.py`, and pre-register round 1 with
its seed, budget and stop rule, keeping `--stop-on-collapse` on. This serves
P4, which still needed three motivated rounds, and R2.

**Deviation: I did not reconcile.** The critic asked me first to fold
`soft-otter-1938` and `even-otter-4624` into `staid-tooth-3475` and
`wild-harvest-4848`, then export and check. This dispatch forbids the
reconcile skill, `hypergraph update` and state-node edits in a work
iteration, with no exceptions. I left the fold for the next reconcile pass.
The tail is now three records, including this one, so a reconcile is due.

**Scope beyond "pre-register round 1".** The pre-registration covers the
whole session: four runs and four turns at most, as Robin's did. I let the
supervised session run to its stop rule inside this iteration. The
alternative was to stop after round 1, and that would have killed a
supervised product turn mid-loop.

## Method

1. Copied the project with `cp -a`, into `ot11-heron-1` and a scratch
   `ot11-heron-targets`. The scratch copy carries only the frozen spec and a
   goal-bearing task. It was used to export a bundle, and nothing trained on
   it.
2. Confirmed from the exported bundle that the arm length is 144.0 mm, the
   tip (the `c_forearm` frame) starts at (64, 0, 120) mm, and the model is
   `183fabff…`, which is ot8's accepted MJCF. The product's reach constants
   (0.05 arm lengths, 1.0 s final window) equal the contract's.
3. Drew the targets with `goals.py`. Every target is at least 29.4 mm up
   (limit 14.4 mm) and at least 37.9 mm from its segment's start (limit
   36 mm).
4. Wrote the prompt. It fixes the mechanism for the session, because a
   changed mechanism moves the held-out targets. The task must declare
   exactly one goal named "target" of kind point. How that goal is drawn in
   training is the agent's.
5. Committed the pre-registration, then launched `rounds.py` under `setsid`
   at 18:48:11Z.
6. After each run, checked:
   - the spec block is in the script byte for byte;
   - `--stop-on-collapse` is in the trainer command;
   - the model digest is unchanged;
   - the evaluation's drawn targets equal the receipt. They did, to within
     5.3e-05 mm, which is the receipt's rounding. No seed was void.
7. Round 1 showed a large gap between training reward and the spec. I checked
   whether reward and spec measure different tips. They measure the same
   one: seed 1101's segment A reached 6.9 mm, and its segment B never moved.
   The policy was poor; the evaluation was sound.

## Result

**True now.**
- `ot11-heron-1` holds four rounds by `claude-opus-5-5`. It was one turn of
  74.5 min with 50 tool calls, costing $3.20. The longest blocks were
  `train_status` at 892.8 s and `evaluate` at 111.3 s.

  | run | seed | budget | iterations | policy | passed | worst Q2 |
  |---|---|---|---|---|---|---|
  | r1 | 7 | 880 s | 685 | c5a01908 | 0/10 | 0.43–1.28 |
  | r2 | 11 | 890 s | 649 | e1b0277d | 1/10 | 0.04–0.26 |
  | r3 | 23 | 890 s | 649 | 2036f471 | 0/10 | 0.07–0.31 |
  | r4 | 31 | 895 s | 474 | 3270ce26 | 9/10 | 0.008–0.055 |

  Q2's limit is 0.05 arm lengths. All four runs ended on their wall-clock
  budget, and none collapsed. GPU wall time was 3,557 s.
- **P4's three motivated rounds are met on reach.** r2, r3 and r4 each cite
  the failing predicate, its value and the limit from the previous
  evaluation. The next evaluation shows whether each change helped: r2
  helped, r3 did not, and r4 helped. The owner ticks P4.
- **R2 is not met.** r4 fails seed 1106. Its segment B target sits low
  beside the pedestal with the elbow folded; the tip settles 7.92 mm from it
  against the 7.2 mm limit. 1106 was the worst seed in r2, r3 and r4. A
  confirmation evaluation needs a policy that passes, then its own
  pre-registration.
- Suites: `pixi run python -m pytest cli/tests`: 1255 passed, 1 skipped (18 min). No engine,
  protocol, payload or trainer file changed, so `test-engine` and the
  packaged gate were not due.

**Concern: a loop defect, and the next unit.** Warm start is not reachable
through the tools. `train_start` needs `init_from_parent_task`, the path of
the parent run's task bundle. `loop.run_view`, which is what `train_status`
returns, never names it, and neither does the refusal. The agent guessed
five paths, and all five were refused. The real file is
`runs/<run>/train/<task>-task.json`, and the registration's `bundle` key
already holds it. The agent trained r3 from scratch because of this, and
its closing report names the gap as the blocker for its next step. The fix
is to report the bundle path in `run_view` (and in the refusal), with a
regression test that fails before the fix. A second session on the same
prompt may follow only after that product change, recorded.

**Other notes.**
- The agent diagnosed 50 Hz chatter from the reward terms. The 0.2 s film
  frames cannot show it.
- The scratch project `ot11-heron-targets` is left in the projects directory
  and counts for nothing.
- The unreconciled tail is 3 records, so a reconcile is due.

Dispatch closed: 1 unit — reach loop on ot11-heron-1: prompt and held-out targets pre-registered (02603727), four motivated rounds by the product agent, last round 9 of 10 seeds (1106 misses Q2 by 0.7 mm); P4's three rounds met on reach, R2 open; warm start unreachable through train_status is the next unit.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 0c07267de87eff6875a794bfc83d595ac54a6651

## State Impact

- target: wild-harvest-4848 — P4's three motivated rounds are met on reach: on ot11-heron-1 the product agent ran four pre-registered rounds (r2-r4 each citing the prior evaluation's failing predicate, value and limit); r2 helped (0->1/10), r3 did not (1->0/10), r4 helped (0->9/10). Loop defect: train_status (loop.run_view) never names a run's task bundle, so warm start (init_from_parent_task) is unreachable; the agent guessed five paths
- target: sunny-garden-4245 — Reach loop exists on ot11-heron-1 (copy of ot8-heron-b): frozen reach spec handed over byte for byte, twenty held-out targets drawn before training (retained/r2-heron-1-targets.json, model 183fabff) and held by all four evaluations; best policy 3270ce26 passes 9 of 10 seeds, seed 1106 fails Q2 at 0.055 vs 0.05 arm lengths. No confirmation evaluation yet; R2 open
