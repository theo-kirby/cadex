---
node_id: e34cd938-1d2d-50c7-bcb5-fe411731c309
slug: wise-tooth-2750
title: cadex export hands over the training bundle and the rollout trace (ADR-189)
created_at: '2026-09-06T01:23:33+00:00'
parents:
- sweet-light-3396
summary: ''
---
## What

`cadex export` now hands over every staged output, not only the BREP ones:
the training task JSON, the MJCF model XML, the policy receipt, the rollout
trace and a mesh's `.ply` are copied into `--out` beside the STEP and STL,
under the filenames the engine staged them with, and named in the `--json`
envelope's `files` under their suffix. Only an output with nothing staged
(an assembly component, a solve diagnostic) is skipped, now as
`no staged artifact`. ADR-189; `docs/CLI.md` §3, `docs/MUJOCO.md` §7c rows
3 and 7 and frontier item 1, and `training/README.md` updated in the same
commit (`7319fed6`).

## Why

Overseer direction for iteration 22 of `ouroboros/nt1`: of the three gaps
the lifecycle audit (`sweet-light-3396`) named, take export first — it is
the smallest and it unblocks `put_asset` next. Targets the lifecycle
frontier (`robot-lifecycle-walk`, declared NEW by the audit) and the CLI
node (`chilly-union-8972`), which the audit marked as writing only BREP
outputs. One assumption taken without a human: the copies keep the
*staged* basename rather than the output's name, because the task bundle
references its model by that name and `training/cadex_train.py`'s
`load_bundle` resolves the model beside the task by it — kept, the export
directory is a bundle the trainer accepts unchanged; renamed, the trainer
would have needed a change. That was found by running the trainer against
a first version that renamed, and the first version was replaced before
the commit.

## Method

- `cli/cadex_cli/export.py`: `ExportedOutput` gains a non-serialised
  `copy` plan; `export_plan` turns every non-BREP output with an
  `artifact_path` into a copy under `Path(source).name`; `export_outputs`
  copies before the engine subprocess, a missing source is an
  `ExportError` naming the output, and a model with no BREP never runs the
  engine at all.
- `cli/tests/test_export.py`: the plan test distinguishes copy from skip;
  a no-engine test copies the four dynamics kinds under their staged
  names with a bogus engine binary, proving it is never run; a missing
  staged copy is an error; the real-engine mixed-model test asserts the
  `.ply` is the staged bytes. `pixi run python -m pytest cli/tests`:
  **85 passed** (13 in the export module), the engine-needing half
  included, against the built dev-tree engine.
- On a scratch copy of the §7b rehearsal project (`~/cadex-balance-ns`
  copied to `/tmp`, never built in place): `./cadex export --json` in
  **2.0 s** wrote `arm`/`stand` STEP+STL and `balance_task-task.json`,
  `model-model.xml`, `policy-policy.json`, `assembly-simulation-trace.json`;
  five outputs skipped as `no staged artifact`. The trace's `policy` block
  carries `total_reward` 1729.95 and the five `reward_totals`.
- The trainer from the repo's untracked `.venv`, pointed at the exported
  folder alone: `--iterations 2 --envs 8`, **exit 0**, task digest
  `602d62c1…` (the audit's), model digest matched, 16 s wall, well inside
  the 15 min / 3 GB bound. Local CPU only; nothing dispatched.
- `training/README.md` said a flat copy of the two files does not work;
  `load_bundle`'s basename fallback says it does. Code wins; the doc is
  fixed and re-dated.
- No engine, shell or protocol change, so no engine suite, gate or
  packaged lifecycle gate was run for this unit.

## Result

§7c rows 3 and 7 move from "a person, or a guess" to "the agent, or a
pipeline": the `--out` directory is the training bundle and the rollout
review, with no staging path read by anyone. Frontier item 1 of the audit
is closed; item 2 (`put_asset` in the CLI tool surface plus a no-model
`cadex asset`) is next, then the `cadex train` dispatcher. One oddity
grew: every `cadex export` leaves a fresh complete attempt directory for
the same accepted revision (three now on the audit's copy); harmless,
noted in §7c, still not chased. The unreconciled tail is now three nodes.

Dispatch closed: 1 unit — cadex export copies every staged non-BREP output under its staged name (ADR-189); the exported folder is a trainer-accepted bundle; §7c rows 3 and 7 closed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: 7319fed614cb08d2c9d5fa4a150b446c346dbfc1

## State Impact

- target: NEW robot-lifecycle-walk — leg 3 (bundle out) and leg 7 (review for a pipeline) closed on 2026-09-06: cadex export copies the task JSON, model XML, policy receipt and rollout trace into --out under their staged names and names them in the --json envelope; the exported folder is a bundle training/cadex_train.py accepts unchanged (2 it × 8 envs, exit 0, digest 602d62c1). Frontier item 1 of §7c done; item 2 (put_asset in the CLI plus a no-model cadex asset) is next. Every export leaves a fresh attempt directory for the same revision: noted, not chased
- target: chilly-union-8972 — cadex export now converts BREP outputs and copies every other staged artifact (mesh .ply, MJCF .xml, task/receipt/trace .json) into --out under its staged filename, naming each in the envelope's files under its suffix; only outputs with nothing staged are skipped (ADR-189, docs/CLI.md §3). The INSPECTION_FAILED validator crash is unchanged
