---
node_id: 06139779-aeb0-5970-b601-6289fb14ac84
slug: misty-timber-4175
title: 'ot11 P2: cadex evaluate holds a policy to its task''s success spec on every frozen seed; w2-2 and Robin fail on the contract''s conditions (ADR-457)'
created_at: '2026-09-30T09:42:27+00:00'
parents:
- first-mist-2505
summary: ''
---
## What

`cadex evaluate` — one command that holds the accepted policy against its task's success spec on the frozen seeds and writes a report into the project (ADR-457, commit `f3a43b90`). This is P2's second bullet, without the video, the filmstrip and the dashboard view.

- **Engine.** `CadexDynamics.evaluate_success(xml, task, container, components=...)` plays `rollout_policy` on `evaluation_task(task)` for each seed in the bundle's `success` block, at one frame per control step. New in `CadexEvaluation`: `measure` (one rollout as the one flat table a predicate may bound) and `summarise` (the seeds together, no verdict averaged).
- **CLI.** `cli/cadex_cli/evaluate.py` reads the retained accepted attempt as `cadex smoke` does and never rebuilds. `cli/cadex_cli/evaluate_runner.py` is the child, run by path under the engine's own interpreter.
- **Report.** `evaluations/<revision>-<policy>/evaluation.json` (`cadex-evaluation-v1`): per seed, pass or fail, every predicate row with its value and reason, the behaviour metrics, per-foot and per-shove detail, how the episode ended, the reward term by term and every drawn value; plus a summary with each predicate's tally, the termination causes and min/median/max of every metric and reward term. Each seed also leaves `seed-<n>-trace.json`, which the project's own `.gitignore` keeps out of its history. The `PROGRESS.md` row carries the verdict and the failing predicates.
- **Known negatives, now on the contract's conditions**, on two new copies: `ot11-w2-negative` and `ot11-robin-negative`.

## Why

Target: frontier node `damp-flame-5523` (P2). It is the unit the critic named, and I did what the message asked: one command, from the task bundle's `success` block, each frozen seed under the spec's reset variation and disturbances, the four report parts, no walking-specific branch, proved on `ot11-*` copies of w2-2 and Robin, with tests, both suites and the packaged gate.

**Not done here, as the critic scoped it: the filmstrip, the rollout video and the dashboard view of the report are the following unit.** The blind judge waits on the filmstrip.

## Method

- Chose `cadex smoke`'s shape over `cadex train`'s: read retained artifacts, run a child under the engine's interpreter, exit zero on a complete measurement. So the policy evaluated is the file the accepted revision verified (receipt → staged weights → sha256), and no rebuild runs.
- Kept every metric, the episode loop and the forward pass in the engine. The CLI child imports `CadexDynamics` from the module directory the resolved engine names.
- **Agreement gate.** Put the w2 task's own conditions where the spec's are and compared all ten seeds with the retained P1 receipts (`p1-w2-2-seeds.json`). First result: seeds 1103–1110 disagreed (worst relative difference 33). Cause: `apply_randomisation` multiplies its draws into the compiled model in place, and my first version played every seed on one compiled model, so each seed began with the previous seed's mass. Fixed by taking the model's bytes and compiling one per seed. Second result: **all ten reproduce to 2.0e-15**. The regression test fails on a shared model (checked by caching `load_model`).
- **A second defect found by a fixture.** The first live fixture went unstable (MuJoCo `BADQACC`), the state was reset, and the seed read as a calm block. `rollout_policy` now returns `solver_warnings`, read every control step, and a seed with any is `void` and has not passed.
- Copied the two read-only projects to `ot11-*` names (tracked files and the accepted attempt; not `runs/` or `review/`). Added the P1 contract's predicates, seeds and conditions to each copy's task as `assembly.success`, stored each original bundle and model as assets, and declared the policy with `trained_task=...`. The engine proved each rebuilt task the same task and verified the unchanged policy. I authored those specs; they are the actor's P1 contract on known negatives, not a spec an R criterion counts.
- Rebuilt the engine, staged the payload, ran the packaged gate, and ran the new CLI tests and Robin's evaluation through the payload.

## Result

True now:

- One command evaluates any accepted policy against its task's spec. It has no flag for a behaviour, and two tests strip docstrings and assert that neither `evaluate_success` nor the CLI modules contain a behaviour's name. Which metric families are read follows from the rig (floating base, named feet, a tip).
- **`w2-2` on the contract's conditions (`ot11-w2-negative`): 0 of 10 seeds pass.** W5's step share (0.00–0.12 against ≥ 0.70) and W7 (slip 0.53–0.76 against ≤ 0.15) fail on **all ten**, as do W6, W9 and W10. W2 fails on nine, `tipped` fires on two (1106 at 5.56 s, 1108 at 0.84 s). On three seeds it sits back at about 43° and travels under 5 mm/s; one of them, 1104, has the highest reward of the ten (867.0).
- **Robin on the contract's conditions (`ot11-robin-negative`): 0 of 10 seeds pass, with B1 and B5 measured.** B3 (9.2–18.7 COM heights), B4 (131°–168°) and B5 fail on all ten. `fallen` fires on six seeds, between 3.10 s and 9.08 s. Only two seeds recover from both shoves at all, in 6.39 s and 3.19 s at worst. ot9 never shoved it.
- No seed was void on either. Receipts without machine paths: `docs/probes/ot11/retained/p2-w2-2-evaluation.json` and `p2-robin-evaluation.json`, pinned by `cli/tests/test_ot11_contract.py`.
- A spec seed equal to the policy's training seed is refused by the evaluation (`evaluation_seed_is_the_training_seed`).
- Evaluating through the staged payload gives Robin's ten seed rows and summary identical to the dev tree's.

Evidence, at commit `f3a43b90`:

```
pixi run test-engine
  2434 passed, 53 skipped in 331.95s (0:05:31)
pixi run python -m pytest cli/tests -q
  1147 passed, 1 skipped in 842.76s (0:14:02)
CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest \
    cadex_tests/test_cadexd_lifecycle.py cadex_tests/test_success_spec_live.py
  27 passed in 21.97s                      (after build-engine and stage-engine)
CADEX_ENGINE_ROOT=<the same payload> pytest cli/tests/test_evaluate.py cli/tests/test_smoke.py
  48 passed in 20.28s
```

- The 53 and 1 skips are the standing ones (MJX-gated, platform); I did not inspect them individually. The new tests ran: 16 in `test_evaluate_success_model.py`, 5 added to `test_evaluation_metrics.py`, 21 in `cli/tests/test_evaluate.py`, 1 added to `test_ot11_contract.py`.
- After the full CLI run I made one more edit: `failing_predicates` leads with void seeds, and one assertion was added. `test_evaluate.py`, `test_ot11_contract.py`, `test_smoke.py` and `test_commands.py` were re-run after it: 84 passed. The full CLI suite was not re-run on that last edit.
- The payload's `CadexDynamics.py` and `CadexEvaluation.py` are byte-identical to the source at the commit.

Concerns and assumptions for the next iteration:

- **The spec cannot switch off a task's randomisation.** The w2 task randomises the tray's mass by 0.85–1.15, and an evaluation episode keeps it. The P1 contract lists no mass randomisation, and those draws come first in the seed's stream, so the w2-2 numbers are the contract's reset, shove and horizon on a drawn mass. The P1 contract says a trace whose drawn conditions are not the contract's is void. Either `assembly.success` gains a `randomisation=` condition or the contract says mass randomisation is allowed; that is a decision for P1's owner (the actor) and it will matter for R1.
- **W3, W4's lateral half and Q1–Q4 are still not statable** in a spec: they need a goal (P3). The w2 copy's spec is W1, W2, W4's heading and W5–W10.
- **`apply_randomisation` is unchanged.** Any caller that plays two seeded episodes on one compiled model still compounds the draws. `evaluate_success` and the worker each compile per episode. I did not audit the trainer's reference runner or live mode for this.
- The reset lift in each copy's spec is the task's own clearing lift plus the contract's 0–5 mm (w2: `RESET_LIFT`; Robin: 3 mm). The engine's clearance check accepted both. The contract says "above the lift at which that tilt clears", and I did not search for a smaller clearing lift.
- A rollout is bounded by `MAXIMUM_TRACE_POSES` (100,000). Ten seconds at 50 Hz with 62 components is 31,000. A long horizon on a large assembly would be refused by `rollout_policy`; the evaluation does not yet trim the trace to the bodies it reads.
- The first evaluation on `ot11-w2-negative` ran before the per-seed fix and left a wrong row in that copy's `PROGRESS.md` (W1 9 of 10, W6 3 of 10). The report file was overwritten by the corrected run; the two later rows are the right ones.
- Each evaluation leaves about 6 MB of trace per seed in the project (ignored by its git). Nothing prunes them.
- The trainer still does not refuse a `--seed` that is an evaluation seed; only the evaluation refuses.
- The agent does not yet have this as a tool, and nothing in its guidance mentions it. That is P4.
- The unreconciled tail is one record after this one.

No new dependency. No protocol change.

Next unit, as the critic ordered: the filmstrip and the rollout video on the dark floor from the per-seed traces this command now leaves, and the review dashboard's view of `evaluation.json`. Then the blind judge on the two known negatives.

Dispatch closed: 1 unit — `cadex evaluate` holds the accepted policy to its task's success spec on every frozen seed and writes the report; w2-2 and Robin both fail on the contract's conditions (ADR-457)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: f3a43b90be6665eb090abec40ab7069e8de7900e

## State Impact

- target: damp-flame-5523 — still open. One command now evaluates an accepted policy against its task's success spec: cadex evaluate reads the retained accepted attempt, rolls the policy on each frozen seed under the spec's conditions through CadexDynamics.evaluate_success, and writes evaluations/<revision>-<policy>/evaluation.json (cadex-evaluation-v1) with pass or fail per seed and per predicate, the behaviour metrics, the reward term by term, termination causes, every drawn value and one trace per seed (ADR-457, commit f3a43b90). It names no behaviour; a model is compiled per seed because randomisation is written into the compiled model; a seed with a solver warning is void; a spec seed equal to the training seed is refused. Missing under P2: the rollout video and filmstrip on the dark floor, and the review dashboard's view of the report. The spec cannot switch off a task's randomisation.
- target: rough-shore-6557 — no status change. Both known negatives are now measured on the contract's seeds, shoves and horizon through the product, on ot11-w2-negative and ot11-robin-negative: w2-2 passes 0 of 10 seeds and fails W5's step share and W7 on all ten; Robin passes 0 of 10, fails B3, B4 and B5 on all ten and falls on six, with B1 and B5 measured for the first time (receipts docs/probes/ot11/retained/p2-*.json). W3 and W4's lateral half are not statable until P3. The w2 task's mass randomisation is kept in an evaluation episode, which the contract does not list. The judge has still not run.
