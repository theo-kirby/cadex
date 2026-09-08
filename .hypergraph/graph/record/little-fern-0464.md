---
node_id: ad62f79d-2edb-5127-ac52-ce22ba13d057
slug: little-fern-0464
title: Git ownership guidance distinguishes project-root and nested repositories
created_at: '2026-09-08T08:19:20+00:00'
parents:
- fresh-flint-1505
summary: ''
---
## What

Corrected the qualified Git ownership distinction in docs/CLI.md, the project_docs module guidance and DECISIONS/PROGRESS scaffolds, and the lifecycle example guide. Updated the existing ADR-194 with a dated correction and clarified its already-checked ROADMAP item. No Git implementation changed.

## Why

Follows the demonstrated mismatch in [rec: fresh-flint-1505] and executes the conditional second short-plan unit. Serves missions 1 and 2, preserving charter criteria **Project as codebase** and **The walk exists and is tested headlessly**: an agent must know whether accepted project work is committed and whether generated artifacts have ignore protection. Existing project-root repositories and projects nested beneath another root have different legitimate ownership contracts. No new criterion is ticked or reopened. The explicit work-iteration prohibition on reconciliation overrides the overseer's request to reconcile at three records; the maintainer owns that next pass.

## Method

Read STATE, Hypergraph instructions and record skill, VISION, the previous three-case qualification, project_docs scaffolds and tests, ensure_project_repo and commit_project, CLI history guidance, lifecycle example guide, ADR-194 and ROADMAP. Correct prose only: default ignore rules are created during initialization only when absent; existing repositories retain their ignore configuration; project-root repositories attempt to commit all working changes, including unrelated edits and the working versions of staged files; nested roots without their own .git get documents/rows but no automatic commit and leave the parent index untouched. Progress rows alone are not proof of a commit; command notes report committed <sha> on success. Missing Git and commit failure do not invalidate acceptance.

Run the required complete CLI gate, `pixi run python -m pytest cli/tests`, with stdout/stderr captured outside the repository, then `git diff --check`. No new tests mirror the wording; existing scaffold, Git and acceptance coverage runs in the full gate. No repeat of the three-root qualification, provider call, stage refresh, durable-project edit, GUI or remote dispatch. The full CLI suite exercises its existing local toy training/walk integration tests; no separate training experiment or lifecycle rehearsal was launched.

## Result

Full CLI suite: **206 passed, no skips, in 224.33 s**, exit 0. Diff whitespace check passed. Only the five scoped documentation/scaffold files changed before recording. Git routines, user ignore files and index behavior are unchanged. Existing project documents remain user-owned and are not migrated or overwritten by this template correction. The prior qualification's fresh-root-with-existing-ignore and commit-failure limits remain runtime limits; those explanatory statements were checked against code, not newly exercised as an experiment.

The precise mismatch handed off by fresh-flint-1505 is corrected. No additional missing lifecycle leg was demonstrated, and this unit supplies no new evidence for ticking the charter's other criteria. The previously established completion evidence stands. Next: return the finite Git ownership direction for replanning; do not repeat qualification or broaden into Git behavior changes. This record brings the unreconciled tail to three; a separate maintainer pass is due. Hypergraph export/check is the final recording gate; no state nodes, STATE.md, plan or .ouroboros files are edited.

Dispatch closed: 1 unit — Git ownership documentation and project scaffolds corrected; full CLI gate passed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: a7be71f3af74534bb90477d96cf0201757e511b9

## State Impact

- target: chilly-union-8972 — Qualified Git ownership mismatch corrected in CLI guidance and scaffolds; existing ignore configuration and nested parent index behavior unchanged; 206 CLI tests passed
- target: calm-peak-5247 — Lifecycle guide and project-doc scaffold now qualify automatic history by repository ownership; finite correction complete with no new lifecycle gap
