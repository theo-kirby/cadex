---
node_id: bb5ca3df-8911-5fd5-83bc-babb451b7c7b
slug: fond-mesa-1562
title: 'Fresh-toy lifecycle audit: 117 tests pass; the general entry point remains open'
created_at: '2026-09-06T19:16:19+00:00'
parents:
- empty-wolf-3962
summary: ''
---
## What

Audited the committed lifecycle sequence on a fresh, repository-defined toy through the existing real-engine CLI integration suite. Updated docs/MUJOCO.md §7c, the ADR-192 evidence and ROADMAP to distinguish proven individual legs from the charter's still-open general entry point. No runtime code changed.

## Why

Iteration 1 follows operator directive empty-wolf-3962 and targets calm-peak-5247, the charter's highest-priority remaining lifecycle work. The reconciled node calls all leg owners working, but the current charter asks for one documented entry point and a second mechanism. docs/CLI.md still requires a caller to edit the policy filename and digest. Assumption: preserve pre-existing uncommitted cli/cadex_cli/__main__.py, report.py and walk.py rather than adopting an unfinished implementation as evidence. PLAN.md is absent; choose the short-term audit directly from the charter. The fixed-toy test is the smallest reproducible experiment available without an agent call that could spend money.

## Method

- Read STATE.md, the hypergraph contract, VISION, the lifecycle state and rehearsal record, both unreconciled reduction records and the operator directive; inspected CLI/training docs and the real-trainer tests.
- Extracted only committed cli/ from `git archive HEAD cli` at 7dd3d045 into a temporary root outside the worktree. Linked src, training, .pixi, .venv and build to the existing local installation. This excludes the pre-existing CLI edits without resetting or committing them.
- Ran the pixi environment's Python with `-m pytest <isolated>/cli/tests -ra --basetemp <isolated>/test-projects`, JAX_PLATFORMS=cpu and OMP_NUM_THREADS=1. An external watchdog sampled aggregate process-group RSS every 0.5 seconds and would terminate at 3,000,000,000 bytes or 850 seconds. No limit was hit.
- Inspected the real iterate test's two exported traces, progress JSONs, project PROGRESS.md and git history. It starts from the in-repo plate-and-arm xscript fixture, not a pre-existing home-directory project. The test invokes CLI main for every leg, supplies the digest edit itself, and checks rejection of a changed task while the old policy remains enabled.

## Result

117 passed, no skips, pytest time 85.76 s; watchdog elapsed 86.26 s, sampled aggregate peak RSS 1,047,805,952 bytes. Both iterate trainers report device cpu, one iteration and four environments: 1.2823 s / reward per step -0.3801982 and 1.2424 s / -0.6151326. Full 50-step rollouts score -27.1093842 and -55.3480045. Project PROGRESS.md records -55.3 (delta -28.2 vs the previous -27.1), and the project has eight commits. Reward weight doubled, so the score delta is not an improvement comparison under equal conditions. Temporary policies and traces are not added to this repository.

The existing CLI sequence, real policy verification and warm retraining hold. This does NOT prove a generic product walk: the test helper supplies design and the digest edit; its bundles and exported traces are siblings of the temporary project; no domain documents are authored by the test. No model turn, GUI, remote dispatch, build or packaged lifecycle gate ran. The gate result applies to the committed CLI, not the pre-existing uncommitted walk edits. Documentation-only changes introduce no runtime risk; no project scaffold behavior changed. ROADMAP now explicitly keeps the single-entry-point item open; no charter checkbox was changed.

Next: finish and test a bounded, documented lifecycle entry point with a repo-owned mechanism, automatic policy declaration, project-local review artifacts and domain docs; then reuse it on a second mechanism. Preserve/review the pre-existing walk edits before relying on them. The tail was already three records on arrival and now grows to four; a separate maintainer owns reconciliation. Export/check and diff whitespace verification are required before the single documentation-and-record commit.

Dispatch closed: 1 unit — committed lifecycle legs reverified on a fresh toy; general entry-point gap recorded without adopting unfinished code.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 7dd3d0458c61d300100177955267eca074d6865b

## State Impact

- target: calm-peak-5247 — Committed CLI reverified: 117 tests pass, fresh toy trains and warm-retrains on CPU, both 50-step rollouts and eight project commits recorded. General single-entry-point walk remains open: fixed test supplies design and policy digest edit, outputs are not all project-local, and domain docs are not exercised. No GUI or remote run; pre-existing uncommitted walk code excluded.
