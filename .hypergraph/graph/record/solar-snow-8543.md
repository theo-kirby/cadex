---
node_id: 274117e0-28d4-5ef1-8f77-51dd1f523ac5
slug: solar-snow-8543
title: Failed project-document updates preserve earlier history
created_at: '2026-09-08T21:10:45+00:00'
parents:
- honest-banner-0821
summary: ''
---
## What

Fix project-document updates that truncate existing history when a write fails.

## Why

Bounded bet, recorded before implementation: write updated documents to a sibling temporary file and replace only after successful writing, preserving prior history on failure. The overseer directs one file-lifecycle repair after the seed experiment; no supplied capacity signal reopens the live provider iterate. This serves mission 1 and the project-as-codebase portion of the lifecycle criterion (calm-peak-5247). Test progress, decisions and domain-note updates with an injected partial-write failure. No new seeds, provider probes or parked work.

## Method

Replaced the in-place writes in append_progress_row, record_decisions and record_notes with one sibling-temporary-file helper. It resolves document symlinks, writes complete text, copies existing file permissions, then uses os.replace; ordinary exception cleanup removes the scratch file. First-visit scaffolding and engine state are unchanged. Updated docs/CLI.md and the project ARCHITECTURE scaffold together, logged ADR-264, and ticked the ROADMAP maintenance item.

Before implementation, ran `pixi run python -m pytest cli/tests/test_project_docs.py -k failed_document_write -q`: all three partial-write cases failed because original document bytes were truncated (local output /tmp/cadex-iteration35-red.log). After implementation, those three passed. Extended to six cases covering both partial writes and refused replacement, preserving prior bytes, permissions, file inventory and successful retry. A manual temporary-project check confirmed a PROGRESS.md symlink remains a symlink and its target retains prior history after append.

Required gate: `pixi run python -m pytest cli/tests`, local output /tmp/cadex-iteration35-cli.log. No engine, protocol, payload or shell changes and no full build needed for this CLI-only Python repair. An initial editing command used unavailable unqualified python and changed nothing; reran with python3.

## Result

Full CLI gate: 251 passed in 228.40 s, no skips. All six failure-injection cases pass. git diff --check passes. Hypergraph export/check passed with zero violations/warnings before minting and will be repeated after recording.

This repairs a concrete file-lifecycle defect in durable project history and maintains the charter's project-as-codebase and headless lifecycle evidence (calm-peak-5247, chilly-union-8972). Nothing further is required from this repair before the existing working lifecycle criterion can be ticked; this is not evidence that a live provider understands project history. No engine/payload/shell gate was needed or run. No generated output or machine paths enter the product commit.

Limits: replacement is per file, not a multi-document transaction, concurrency solution or power-loss guarantee. An uncatchable process termination can leave a hidden sibling scratch file. Existing history remains intact on the tested write/replacement failures; first-visit scaffolding is unchanged.

Next: the selected seed direction remains spent. Attempt the planned history-aware live iterate only when supplied capacity signals reopen it; otherwise select another concrete maintenance defect under the overseer's direction, without probes, hold records or parked criteria. This node makes three unreconciled record nodes; no reconcile or state edits performed.

Dispatch closed: 1 unit — preserve project document history when an update fails, with regression and full CLI gate.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 86d9739a5261b15334a31355f13f1b7f38eb0f2b

## State Impact

- target: chilly-union-8972 — Progress, decisions and domain-note updates replace complete files; six failure/retry regressions and the 251-test CLI gate pass.
- target: calm-peak-5247 — Durable project-as-codebase history survives partial-write and replacement errors; per-file protection only, no live-provider understanding claim.
