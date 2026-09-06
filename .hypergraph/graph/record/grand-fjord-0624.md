---
node_id: 9cff4f2e-6936-5ee0-8cbf-e7029cb00c71
slug: grand-fjord-0624
title: 'Correct ADR-201: the shell retry can silently overwrite CLI work; refresh before GUI edits'
created_at: '2026-09-06T20:11:03+00:00'
parents:
- red-comet-9710
summary: ''
---
## What

Correct ADR-201 and the GUI-attached walk guidance in docs/CLI.md sections 2 and 5: the shell's automatic stale-revision retry retains the original mutation and can silently overwrite a CLI-accepted script or parameter values. Require Rebuild Model or reopening after a CLI acceptance and before resuming GUI edits. Align the project ARCHITECTURE.md scaffold, its wording test, MUJOCO section 7c row 11 and ROADMAP. This is a correction to red-comet-9710, whose immutable body and impacts are superseded by the impacts below.

## Why

Iteration 6, one unit targeting witty-spark-2613 (mission 2), as the overseer required after the critic rejected the overlap guarantee. Assumption: finish the correction already drafted in the working tree on arrival; keep runtime changes for their own shell-gated unit. The one-unit dispatch takes precedence over starting L2 boards in the same iteration.

## Method

Read STATE.md, PLAN.md, the previous record and the actor and record skills. Inspected Lifecycle.poll and _start in shell/scripts/startup/mesh_agent/cadex_backend.py: on the first stale refusal with a changed revision, poll adopts the reported revision and calls _start; _start copies the unchanged self._args. Inspected begin_write_script, begin_set_params and begin_rebuild_model, including the latter's refresh of source, specs and values. Preserved and reviewed the six-file draft already present, refining it to distinguish source replacement from parameter replacement and to qualify the overwrite on retry success. Kept the per-command CLI lock scope and the absence of a shell lock. No runtime code copied or changed. Ran the full CLI suite and reran the scaffold suite after wording edits.

## Result

pixi run python -m pytest cli/tests: 137 passed in 115.29 s, no skips. The final scaffold wording was also verified by pixi run python -m pytest cli/tests/test_project_docs.py: 15 passed in 2.64 s. git diff --check passed. No engine, protocol, payload or shell runtime change, so no build or shell gate required. No GUI launched or remote training dispatched.

The mode is documented with a sequential-use limitation, not verified safe for concurrent edits. The automatic retry's handling of foreign revisions is a candidate runtime leg on witty-spark-2613 beside the previously recorded shared-lock leg. This supersedes red-comet-9710's implication that a refused overlap protects accepted work and its claim of only one remaining runtime leg. Next: L2 boards, short unit 2; the runtime candidates remain separate work. The unreconciled tail reaches three records with this correction; a maintainer pass is due, and was not attempted here.

Dispatch closed: 1 unit — correct the GUI overlap guarantee and require refresh before GUI editing resumes; CLI suite 137 passed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: d6cd646a325bf8c25a389c7e7e93ecb8b3740f13

## State Impact

- target: witty-spark-2613 — Supersedes red-comet-9710 overlap impacts: the automatic stale-revision retry retains original mutation arguments and can silently overwrite a CLI-accepted script or parameter values. GUI mode is documented only with sequential ownership and Rebuild Model or reopening before resuming GUI edits. Candidate runtime leg: handle foreign revisions without blindly retrying, alongside the shared-lock leg; neither implemented or GUI-exercised.
- target: calm-peak-5247 — The project ARCHITECTURE.md scaffold requires Rebuild Model or reopen before the next GUI edit and explains the silent overwrite risk; the wording test pins agreement with docs/CLI.md.
- target: chilly-union-8972 — CLI lock-scope documentation retained; sections 2 and 5 correct the overlap guarantee. CLI suite 137 passed without skips; final scaffold wording suite 15 passed.
