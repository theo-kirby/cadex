---
node_id: df7b000c-1eb2-5e49-850b-c3d4d6841ac8
slug: chilly-hill-6548
title: 'W7: a curriculum step may revise the success spec (ADR-597)'
created_at: '2026-10-08T02:42:41+00:00'
parents:
- still-arrow-7544
summary: ''
---
## What

Decided the orun5 long-term rung W7, the warm-start rule across success specs that differ. Decision (ADR-597, commit `ed8b287e`): `success` joins the trainer's `CURRICULUM_TASK_KEYS`. A declared curriculum step (`--init-from-task-change` + `--init-from-parent-task`) may now revise the success spec.

## Why

The critic asked for a reconcile pass first: fold `dusty-canyon-3027` and `still-arrow-7544`, then export and check. **This iteration did not do that.** The dispatch contract forbids reconciling in a work iteration, with no exceptions: no hypergraph-reconcile skill, no `hypergraph update`, no state-node edits. So the reconcile is left to the separate reconcile pass, and C1's "reconcile, then claim done" is still waiting on it. The unit taken instead is the one the critic named to follow the reconcile: W7, with an ADR either way and REPORT §10 item 1 updated to match. It is the highest open item on the ladder, and the ledger and report both listed it as open.

## Method

- Read `check_policy_fits` and `check_curriculum_change` in `training/cadex_train.py`, the ADR-161 rationale, and ADR-456's note that recorded the gap.
- Grepped the trainer for every read of `success`. There is exactly one: `check_training_seed`, the evaluation-seed refusal. It reads the child bundle, so a revised seed list is still enforced.
- Read the evidence: ball-plate ADR-007, where the circle policy trained cold because a curriculum step may not move `success`.
- Applied ADR-161's own test: does the change alter what the network reads or emits? The spec does neither.
- Added `success` to the set, with its reason in the set's comment.
- Added two tests in `training/test_curriculum_warm_start.py`:
  - a revised spec (a `laps` predicate added) is admitted as a declared step and returns `["success"]`;
  - the same revision without the flag is still a digest refusal.
- Extended the set-membership pin: `success` in, `goal` out.
- Proved the tests: with `success` removed from the set, 2 tests fail; restored, 18 pass.
- Updated the docs:
  - the base guidance's warm-start rule (`cli/cadex_cli/guidance.py`) now lists the success spec;
  - the `training/README.md` flag row, with its verified date;
  - ADR-597 in `docs/DECISIONS.md`;
  - the ledger's W7 row, now replaced;
  - `docs/probes/orun5/REPORT.md`: §9 (ten replaced, one open, the ADR row) and §10 item 1.

## Result

- W7 is decided: a curriculum step may revise the success spec. Every other warm-start check is unchanged: the model digest, the observation order, the action table, the network shape, the parent-bundle tie and the formatting refusal. `goal`, `observations` and `actions` still may not move.
- Gates, all green:
  - `pixi run python -m pytest cli/tests` with the GPU hidden: 1225 passed, 1 skipped, 476.6 s;
  - `pixi run test-engine`: 2673 passed, 60 skipped, 349.2 s;
  - `training/test_curriculum_warm_start.py`: 18 passed.
- Not shown yet: no training run has used the new rule. The report says so in §10 item 1.
- The tail is now three unreconciled records (`dusty-canyon-3027`, `still-arrow-7544`, this one), which meets the charter's reconcile trigger. The reconcile pass should fold them. After that, C1's done claim can be restated.
- No new dependency. No engine, protocol or tool-surface change.

Dispatch closed: 1 unit — W7 decided: success joins CURRICULUM_TASK_KEYS (ADR-597), tested, report and ledger updated; reconcile deferred to the reconcile role per dispatch rules

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: ed8b287ef1cc4b790e2ff6203c2af6385df23639

## State Impact

- target: late-pond-2851 — ADR-597 (commit ed8b287e): success joins CURRICULUM_TASK_KEYS, so a declared --init-from-task-change may revise the success spec; every other warm-start check unchanged; test-pinned in training/test_curriculum_warm_start.py
- target: grand-otter-5246 — REPORT §9 and §10 item 1 and ledger W7 updated: W7 replaced by ADR-597, only W12 open; reconcile still pending before the done claim is restated
