---
node_id: 23aecb2a-df9e-5dfc-946d-55f6e688258b
slug: first-mist-2505
title: 'ot11 P2: a success spec is declared in xscript beside the task, and the reward is refused as a predicate (ADR-456)'
created_at: '2026-09-30T08:54:56+00:00'
parents:
- ready-field-7940
summary: ''
---
## What

`assembly.success` — the success spec, declared in xscript beside the task
(ADR-456, commit `3ab0c538`). P2's first bullet: "The success spec is
declared in xscript alongside the task, and is documented in
`docs/XSCRIPT.md`."

- `assembly.success(predicates, seeds=..., feet=..., tip=..., tip_offset_mm=...,
  episode_seconds=..., reset_variation=..., disturbance=...)` is a new
  intermediate, passed to `assembly.task(..., success=spec)`.
- Predicates are `CadexEvaluation.check()`'s shape, `{id, metric, min, max}`.
- `CadexEvaluation.METRICS` is the closed vocabulary: 26 behaviour metrics,
  each with what measuring it needs (base, floor, feet, tip, shove, goal).
- `CadexDynamics._success_records` resolves the spec in the worker and writes
  the bundle's `success` block (`cadex-success-spec-v1`): predicates, seeds,
  feet, tip, its own episode schedule, its reset variation and disturbances
  resolved as the task's are, and a `scale` (mass, weight, COM height, hip
  height, arm length).
- `CadexDynamics.evaluation_task(bundle)` returns the bundle as an evaluation
  episode plays it: the task under the spec's horizon and conditions.
- `gait_metrics` reads a gait with no commanded speed (ratios are `None`).

## Why

Target: frontier node `damp-flame-5523` (P2), the unit the critic named.
P1's contract and ADR-455's metrics existed; nothing could declare a spec, so
no evaluation command could know a task's seeds, conditions or predicates.

**Deviation from the critic's message, stated.** The critic asked for a
reconcile first (fold `proud-lantern-5203` and `ready-field-7940`, advance the
high-water mark, regenerate views). The iteration prompt forbids the
reconcile skill, `hypergraph update`, state-node edits and STATE.md edits in a
work iteration "with no exceptions", so I did not reconcile and did the named
unit instead. The tail is now three records, which is the charter's reconcile
trigger.

The critic's unit also said "then the evaluation command and report". That is
a second unit (one unit per iteration) and is not started.

## Method

- Read the task surface end to end (`cadex_assembly_api.task`, the worker's
  `_execute_task_bundle`, `CadexDynamics.task_records`, ADR-134's identity
  fields) before choosing where the spec lives.
- Chose an argument to the task over a separate output. It costs no new
  publishable type, and the trainer's input then carries the evaluation
  seeds. The cost was identity, so `success` is in a new
  `TASK_JUDGEMENT_FIELDS` and outside `TASK_SEMANTIC_FIELDS`.
- Split the checks along the import boundary. `cadex_assembly_api` is in the
  service's closure and `CadexEvaluation` is not (ADR-455), so the API checks
  shape and the engine checks the vocabulary and the model. `CadexEvaluation.py`
  is now staged into the worker bundle.
- Goal metrics (`speed_ratio`, `lateral_ratio`, the four reach metrics) are
  refused, because a task states no goal until P3. No second way to state a
  goal was invented.
- Tests written in three layers: API shape (37), engine resolution against a
  floating two-footed fixture, a grounded arm and the M9 hopper (29), and a
  live `cadexd` (4). `test_evaluation_metrics` gained two.
- Rebuilt the engine, staged the payload, ran the packaged lifecycle gate.

## Result

True now:

- A script can declare a success spec, and the retained task bundle carries
  it resolved. Live through `cadexd`: component values become body names,
  the spec's 3 s horizon and its own shove sit beside the task's 1 s and its
  lighter one, and a seeded episode plays from `evaluation_task(bundle)`.
- **The reward cannot judge itself.** A predicate naming the task's reward,
  `total_reward`/`return`, or a reward term's label is refused as
  `success_reads_the_reward`; an observation channel or any other non-metric
  as `unknown_success_metric`, with the vocabulary listed. Both refusals fail
  the script in a live engine. An expression as a metric is refused by the
  API.
- A metric that cannot be measured is refused at declaration:
  `success_metric_needs_{feet,tip,shove,goal,base,floor}`.
- A task with no spec writes byte for byte the bundle it did. Two bundles
  that differ only in their spec have one semantic digest and no
  `task_differences`, so a revised spec can be held against an earlier policy
  through `assembly.policy(trained_task=...)`.
- No protocol change: `OP_ARG_SPECS`, `docs/INTEGRATION.md` and the shell
  client are unmoved.

Evidence, at commit `3ab0c538`:

- `pixi run test-engine`: 2414 passed, 53 skipped, 0 failed (329 s). The
  skips are the standing MJX-gated and platform ones; the new live tests ran.
- `pixi run python -m pytest cli/tests`: 1125 passed, 1 skipped (828 s).
- Packaged gate after `build-engine` and `stage-engine`:
  `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest
  test_cadexd_lifecycle.py test_success_spec_live.py`: 27 passed.

Concerns and assumptions for the next iteration:

- **The assembly page of the CLI's API view is at its ceiling: 21,478 of
  21,500 characters** (ADR-360). A first attempt also described the spec in
  the assembly domain's notes and failed
  `test_every_page_of_the_live_contract_fits_one_tool_result` at 23,344; the
  notes paragraph was removed. So the product agent sees `success`'s
  signature and one sentence, and the vocabulary is in the export's full
  documentation and in the refusals. **P3's goal surface will not fit on that
  page** until the notes are trimmed or the section is paged. That is a
  decision for whoever adds it.
- `speed_ratio`, `lateral_ratio` and the reach metrics are refused until a
  task can state a goal (P3). Reach cannot be specified through the product
  until then; walk can, using `mean_forward_speed_mm_s` in mm/s.
- The trainer was not changed and was not run. It reads a bundle by key, so a
  `success` block should pass through, but that is unverified. It does not
  yet refuse a `--seed` that is one of `success.seeds`, and
  `CURRICULUM_TASK_KEYS` does not list `success`, so a warm start across a
  spec revision is a whole-file digest mismatch there.
- The rest thresholds, stance height and step definition are the engine's
  constants; a spec cannot override them. The P1 contract uses the same
  values.
- Seeds: the API accepts 1 to 64. The P1 contract's ten is the authority for
  R1–R3, not this limit.
- P2 remains open: the evaluation command, the report, the filmstrip and the
  dashboard are not built.
- The unreconciled tail is three records after this one. A reconcile is due
  by the charter's rule, and the critic has asked for it.

No new dependency.

Dispatch closed: 1 unit — assembly.success declares a task's success spec in xscript, resolved into the bundle, with the reward refused as a predicate (ADR-456)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 3ab0c53881e401589e2e05b7ea0835e30d10b24b

## State Impact

- target: damp-flame-5523 — The success spec is declared in xscript: assembly.success(predicates, seeds, feet, tip, episode_seconds, reset_variation, disturbance) goes to assembly.task(success=...) and lands resolved in the task bundle's success block (cadex-success-spec-v1), documented in docs/XSCRIPT.md (ADR-456, commit 3ab0c538). A predicate names one of 26 behaviour metrics in CadexEvaluation.METRICS; the task's reward, a reward term or a channel is refused, and an unmeasurable metric is refused at declaration. Goal metrics (speed_ratio, lateral_ratio, reach) are refused until P3. The spec is outside the task's identity. Still open under P2: the evaluation command, the report, the filmstrip, the dashboard. The CLI's assembly API page is at 21,478 of 21,500 characters, so the next assembly export needs the notes trimmed or the page split.
