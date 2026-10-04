---
node_id: 730f8bd5-1eca-56ba-8e84-4d4e73c21489
slug: mellow-pine-4848
title: 'orun2 S1: no live doc names the deleted shell, test-pinned (ADR-499, iteration 8 catch-up record)'
created_at: '2026-10-03T13:19:30+00:00'
parents:
- calm-quartz-1493
summary: ''
---
## What

Catch-up record for orun2 iteration 8 (commit `4266f639`, "ouroboros #8: no record"), written by iteration 9 because iteration 8 did not mint one. Iteration 8 swept every live Markdown doc of the deleted shell's paths and pinned the result with a test (ADR-499).

## Why

The critic for iteration 8 accepted the sweep and asked that it be recorded with ADR, test name and State Impact so S1's last requirement — "no live doc refers to `shell/`, `mesh_agent`, a `.blend` or `CADEX_BLENDER_EXECUTABLE`" — has a causally parented record.

## Method

Iteration 8 rewrote `SECURITY.md`, `PRIVACY_POLICY.md`, `docs/ARCHITECTURE.md` (§1, §2, §5, §6), `docs/cadex-release-packaging.md` (retitled "The Engine Payload") and made one-line fixes in AGENTS.md, VISION, ORGANIC, IDEAS, FREECAD, CLI, PROVENANCE, MUJOCO, INTEGRATION, `training/README.md`, `analysis/README.md` and three removal audits; `docs/ASSEMBLY-VISIBILITY-AUDIT.md` moved to `docs/history/`. It added `cli/tests/test_project_docs.py::test_no_live_doc_names_the_deleted_shell`, which lists tracked `*.md` via `git ls-files` and fails on any match of `shell/`, `mesh_agent`, `.blend` or `CADEX_BLENDER_EXECUTABLE` outside a declared history set (DECISIONS.md, `docs/history/`, `docs/probes/`, SHELL-PARITY.md, ROADMAP.md, STATE.md, `.hypergraph/`, `.ouroboros/`). Against the previous tree the test names 19 files. The critic independently grepped every tracked `.md` and confirmed only history-set files still match.

## Result

True now: S1's live-doc requirement is met and test-pinned (ADR-499). With ADR-495 (disable), ADR-496 (`mesh.blender` retired), ADR-497 (Codex/pi retired) and ADR-498 (delete + no GPL code), every S1 bullet has evidence; S1 can be reported to the owner, who ticks it.

Concerns: `docs/ROADMAP.md` keeps 48 shell mentions as phase history because the charter both forbids hand-editing it and asks R1 to rewrite it — an assumption recorded in ADR-499 for R1 to resolve. VISION's interface section and AGENTS.md's "Where this is going" still describe a Rust shell; R1 owns that prose.

Dispatch closed: 1 unit — catch-up record for iteration 8's live-doc sweep (ADR-499), closing S1's last requirement

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 4266f6397ff7e7fa5855e1cd3378f446045598b1

## State Impact

- target: sunny-clover-3750 — every S1 requirement now has evidence: the live-doc sweep is done and pinned by test_no_live_doc_names_the_deleted_shell (ADR-499, commit 4266f639); ready for the owner to tick
- target: shy-crane-2573 — no live doc names shell/, mesh_agent, a .blend or CADEX_BLENDER_EXECUTABLE (ADR-499); only the history set does
