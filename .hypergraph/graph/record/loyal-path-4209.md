---
node_id: 0a97adf8-7bd8-568c-b7a6-f5cfda7d0ea6
slug: loyal-path-4209
title: 'F1 verified: the engine plays a policy under its recorded command filter (ADR-558), tipped 10/10 -> horizon 10/10'
created_at: '2026-10-06T08:55:35+00:00'
parents:
- civic-stream-8050
summary: ''
---
## What

F1 finished and measured: the engine plays a policy under the command filter its
`.cxpolicy` header records (ADR-558). This record also covers commit `8724d1f9`
("ouroboros #3: no record"), which landed the code without a record: the
`recorded_command_filter` reader and the trainer-order EMA-then-slew controller in
`CadexDynamics.rollout_policy`, the `command_filter` block in `evaluate_success`'s
report and every trace's `policy`, the same block in the checkpoint rollout's
trace (`cli/cadex_cli/checkpoint_runner.py`), the test
`src/Mod/cadex/cadex_tests/test_dynamics_policy_command_filter.py` (9 cases),
ADR-558, and the `docs/CLI.md` / `training/README.md` paragraphs. This iteration
added no code; it produced the evidence the critic asked for.

## Why

Charter F1 (`small-cedar-6887`), the highest-ranked open criterion, and the
critic's explicit instruction: record 8724d1f9 and finish F1 with evidence. The
critic asked for the record "parented to small-cedar-6887"; that slug is a state
node and a record's causal parent must be a record, so the record is parented to
this run's previous record (`civic-stream-8050`) and declares its impact on
`small-cedar-6887`. The critic also said "after that, start F2"; the dispatch
budget is one unit, so F2 was not started — it is the next unit.

## Method

- Confirmed the trainer side already exists: `training/cadex_train.py:2494`
  writes `training.action_filter_alpha` (and `:2499` `command_slew_deg`) into
  the header; the trainer's controller (`:1580-1613`) clamps, then EMA, then
  slew, first step of the episode unfiltered. The engine copy matches that order.
- Confirmed one path: `evaluate_success`, the checkpoint runner
  (`checkpoint_runner.py:91`) and the worker's viewport replay
  (`cadex_assembly_worker.py:4771`) all call `CadexDynamics.rollout_policy`,
  which is where the filter is applied, so what the viewport plays is what was
  evaluated.
- `pixi run build-engine` (exit 0); `pixi run test-engine`; the F1 test alone,
  then with the `CadexDynamics.py` half of 8724d1f9 reverse-applied (and restored).
- `pixi run stage-engine` (exit 0; payload `build/engine/cadex-engine-0.0.0-linux-x64`
  carries `recorded_command_filter`), then the packaged gate
  `CADEX_ENGINE_ROOT=<payload> pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`.
- CLI suite with `CUDA_VISIBLE_DEVICES=` (no training run was live).
- Before/after on a real filtered policy, from a scratch script under /tmp that
  only *reads* the reference project: `walk_r4_i200.cxpolicy` (header
  `action_filter_alpha` 0.5) on its own run's model and task (digests
  `b3cf0bc4…`, `dbc1a0b8…`, matching that evaluation's report), via
  `evaluate_success` once as shipped and once with the header's alpha set to
  1.0 (the pre-ADR-558 behaviour). Then the passing unfiltered policy
  `walk_r13_i140` (alpha 1.0) re-evaluated and compared to its recorded report.

## Result

- `test-engine`: **2594 passed, 58 skipped**. F1 test: **9 passed**; with the fix
  reverted: **9 failed** (KeyError on `command_filter`, unfiltered commands).
- Packaged lifecycle gate on the staged payload: **24 passed**.
- **Before/after, filtered policy (alpha 0.5), 10 frozen seeds:**

  | | before (played unfiltered) | after (played at its recorded 0.5) |
  |---|---|---|
  | terminations | tipped 10 | horizon 10 |
  | W1 survives | 0/10 | 10/10 |
  | duration s (min/med/max) | 1.42 / 2.86 / 5.98 | 10 / 10 / 10 |
  | W2 max tilt ° (min/med/max) | 47.4 / 49.3 / 52.0 | 2.3 / 3.1 / 4.1 |
  | W3 forward speed mm/s (med) | 73.6 (3/10 in band) | 115.9 (10/10 in band) |
  | W4 heading pass | 0/10 | 1/10 |
  | W5 lateral pass | 5/10 | 10/10 |
  | W6 steps | 0/10 | 0/10 |
  | verdict | fail | fail |

  The "before" column reproduces that policy's recorded evaluation exactly
  (tilt 47.418/49.307/51.979°, tipped 10), so the old engine was judging a
  different controller than the one trained. Played correctly it stands for the
  full horizon but still fails on heading and steps (a shuffle) — a real
  verdict now, not an artefact.
- **No filter recorded:** `walk_r13_i140` (alpha 1.0) re-evaluates **10/10**, and
  its summary metrics are **identical** to its recorded evaluation report: an
  unfiltered policy plays exactly as before. Headers without a `training` block
  load and play unfiltered (tested).
- CLI suite (GPU hidden): see the line below. A first `-x` run stopped at
  `test_review_overlay.py::test_designing_turns_idle_once_the_window_passes`
  after 885 passes; it passes on rerun (13/13 in that file). It compares a
  `since` minute prefix against a timestamp recomputed later and flakes across
  a minute boundary — pre-existing, untouched by F1, left alone per the
  question policy.
- CLI suite, full run with the GPU hidden: **1178 passed, 1 skipped** (996 s, exit 0).

Concerns for the next iteration: `docs/ROADMAP.md` was not touched (charter
forbids hand-editing it). The tail now holds 2 unreconciled records.
Next unit: F2 (`lucky-shade-9428`) — rebase `orun3-wip-adr558`; note ADR-558 is
now taken by F1, so F2's ADR is ADR-559.

Dispatch closed: 1 unit — F1 verified end to end: build, engine suite, packaged gate, CLI suite, and a measured before/after on a real alpha-0.5 policy (tipped 10/10 → horizon 10/10).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 8724d1f99525d13f2729150d6aa1acd8a4dec98b

## State Impact

- target: small-cedar-6887 — ADR-558 (commit 8724d1f9) landed and is measured: rollout_policy, checkpoint rollouts, worker replay and evaluate_success all play the header's action_filter_alpha/command_slew_deg in the trainer's order; an alpha-0.5 policy evaluated unfiltered tipped 10/10 (median tilt 49.3°), played at 0.5 survives the horizon 10/10 (median tilt 3.1°); an unfiltered passing policy re-evaluates 10/10 with identical metrics; test-engine 2594 passed, CLI 1178 passed, packaged gate 24 passed. Evidence complete pending the owner's tick.
