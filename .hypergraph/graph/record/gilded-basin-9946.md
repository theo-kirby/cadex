---
node_id: ade31bc4-b8f6-5f00-8a84-5651ca468c5b
slug: gilded-basin-9946
title: 'Three modes share whole-walk artifacts: offline parity audit'
created_at: '2026-09-07T22:12:57+00:00'
parents:
- lawful-ivy-4474
summary: ''
---
## What

Audited the charter criterion **Three modes, one shape** and supplied its missing whole-walk remote stand-in artifact-parity test. No runtime orchestration changed. Added a shared mode-artifact table in docs/CLI.md, linked it from the ARCHITECTURE.md project scaffold, pinned the link and paths in test_project_docs.py, and recorded the audit in ADR-200 and a checked ROADMAP item.

## Why

Targets witty-spark-2613, the remaining mission-2 frontier node and short-plan rank 1. The prior test exercised train --remote --put and another checked flag forwarding, but neither took the stand-in policy through real witness verification, rollout and committed review. That was the one missing evidence unit in restless-star-0524's audit.

Assumption: the overseer's request for a separate maintainer pass does not override this dispatch's explicit prohibition on reconciliation. No maintainer action or replan is performed here. One unit means inventory wiring is left for the next actor, even though the overseer also names that later step.

## Method

Read docs/CLI.md's walk and GUI sections, ADR-200/201 and ADR-204's correction, the training setup, test_walk.py, test_train.py and the project scaffold tests. Verify the GUI documentation against cadex_backend.project_root, Lifecycle's stale-revision rule, begin_rebuild_model and on_file_changed, and backend.py's built-in-tool restriction; no shell code copied or changed.

New test runs two independent toy projects through the public walk entry point: one local, one --remote --allow-cpu. Each uses one PPO iteration, four environments, seed 0, CPU JAX and a 600-second train timeout. Child CLI processes receive a test-only REMOTE_SCRIPT replacement. That executable accepts the real remote_train.sh argv contract, calls the real local venv trainer and adds the dispatch trailer. It never calls remote_train.sh or ssh. All other legs use the real engine: export, asset storage, script declaration, witness verification, rollout and review.

Assertions compare complete relative output file sets, trace path and training metric keys; verify policy bytes and digest against the asset store and rollout; check committed project docs, review, task and script; require clean project git status and numeric PROGRESS rows with the remote marker only on the remote train. Existing test_train.py continues to pin argv against the real dispatcher usage and its failure receipts. GUI concurrency and remote transport are not exercised.

## Result

`JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests/test_walk.py -k cpu_dispatcher -q`: **1 passed, 16 deselected in 31.76 s**. Full zone gate `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests -q`: **148 passed in 161.61 s**, no skips or failures; built engine and real training venv available. `git diff --check` passed. No build, engine suite, payload gate or GUI gate needed or run: only CLI tests, scaffold text and docs changed.

The first targeted pair completed in 31.76 s total. During the full suite a process-tree guard sampled RSS every 0.2 s, with 2.9 GB and 850-second cutoffs; it was attached after suite start, so its measurement covers only the observed interval, including the final parity test.

**Criterion verdict: witty-spark-2613 can be ticked against its exact wording.** Headless exercised: the two clean prompt walks in [rec: placid-sky-7374] and the current real-engine suite. GUI attached documented, not exercised: docs/CLI.md and ADR-201 as corrected by ADR-204. Remote handoff scripted/documented, not executed: ADR-200 and the offline stand-in tests. Shared steps/artifacts: the public walk, the shared table and scaffold, and now whole-walk path and committed-review parity. Nothing remains missing for this criterion under the charter's stated limits; this does not establish remote transport reliability or concurrent GUI mutation safety.

Next: wire inventory into the walk review, with scaffold/docs and real-walk evidence, as short rank 2 prescribes. Headless-review criterion damp-moon-9297 remains open. The tail reaches three unreconciled records (restless-star-0524, lawful-ivy-4474, this audit); a separate maintainer pass is due. No state or charter files were edited.

Dispatch closed: 1 unit — audit Three modes, one shape and prove whole-walk artifact parity with a local CPU stand-in dispatcher.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 0e9fe84d51321fc3fd66d3add8adad2936ec85e4

## State Impact

- target: witty-spark-2613 — MET against the exact charter wording: headless prompt walks exercised; GUI attachment documented and unexercised; remote handoff scripted/documented and never dispatched. New real-engine local versus remote-flag CPU stand-in walks prove identical output paths, verified stored policy, committed review and comparable PROGRESS rows. Shared artifact table pinned to scaffold. CLI gate 148 passed, no skips; no remaining gap for this criterion under the stated limits.
