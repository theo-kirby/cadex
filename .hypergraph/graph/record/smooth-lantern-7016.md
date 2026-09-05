---
node_id: 37637c0e-da5f-50fc-a0b5-ed9720a220d0
slug: smooth-lantern-7016
title: Snapshot accumulated product work and demo projects for publication
created_at: '2026-09-05T09:08:00+00:00'
parents:
- curious-sail-8332
- twilight-lake-8164
summary: ''
---
## What

Snapshot the accumulated ADR-174 through ADR-183 work and the local demo projects for the owner-requested commit and push of everything currently present.

## Why

The owner explicitly requested committing and pushing the complete current working tree after the project status review.

## Method

Staged all current tracked and untracked files, including demo history, drawings, retained geometry and training outputs. Converted machine-specific repository prefixes in three demo receipts/logs to relative paths per AGENTS.md. Credential-pattern scan found no matches. Source diff whitespace check passed; generated BREP whitespace was preserved to retain artifact bytes. Existing feature records retain their individual state impacts.

## Result

- `pixi run build-release`: passed after allowing compiler cache access outside the sandbox.
- `pixi run gate`: passed outside the sandbox, packaged gate reports ok true. Initial sandbox run rejected its model and failed hydration.
- Staged-payload `test_cadexd_lifecycle.py`: 14 passed outside the sandbox.
- Full engine and CLI suites outside the sandbox: 2028 passed, 47 skipped, 2 failed in 282.28 seconds. Failures are licensing source headers and the manifest comparing committed HEAD to the staged rna_userdef.cc change; the latter must be rechecked after commit.
- Initial sandbox full-suite run: 1870 passed, 54 skipped, 120 failed, 33 errors, including blocked local sockets and engine subprocesses; superseded by the unrestricted run above.

This is an authorized snapshot, not a claim that every suite is green. State reconciliation remains pending; no state nodes were edited.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

none: Publication snapshot; feature impacts remain on their existing records, with no new product behavior.
