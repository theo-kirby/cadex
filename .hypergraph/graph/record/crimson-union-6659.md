---
node_id: 6b080652-57e9-5a11-b126-b1489d6f1f46
slug: crimson-union-6659
title: 'orun2 S1: Claude Code is the only harness — Codex and pi retired (ADR-497, iteration 6 catch-up record)'
created_at: '2026-10-03T12:43:21+00:00'
parents:
- clear-heron-4371
summary: ''
---
## What

The record iteration 6 never wrote, for commit `96a67c9e` ("ouroboros #6: no record"), which landed ADR-497: **Claude Code is the only harness; the Codex and pi backends are retired** (orun2 S1, charter A4).

The commit:
- `AGENTS.md` and `docs/VISION.md` say Claude Code is the only harness. They no longer offer Codex or pi as a preference.
- `docs/IDEAS.md` no longer counts a pi extension as a live transport.
- `docs/SHELL-PARITY.md`: the `backend.py` (Codex/pi half), `harness.py` and `pi_tools.js` rows and the sandboxing note move to *dropped*, citing ADR-497.
- Deletes `package/rattler-build/scripts/validate_cadex_macos_runtime.py` (150 lines). Nothing called it, and it imported `CadexProvider` and `CadexCodex`, which ADR-021 deleted.
- `cli/tests/test_project_docs.py` gains `test_claude_code_is_the_only_harness`. It fails if any `cli/cadex_cli` module names `codex`, `pi_tools`, `PiBackend` or `registerTool`, or if AGENTS.md and VISION do not state the one harness.

## Why

The critic's message for iteration 7 asked for this first: iteration 6 committed with no record, and unrecorded work is invisible. This node records that work and cites the suite results I ran against that exact commit. Iteration 6 left no receipts of its own.

## Method

- Checked out `96a67c9e` in a separate git worktree, with `build/` symlinked to the main checkout's engine build. Iteration 6 changed no engine code.
- Ran both suites there with the pixi environment:
  - `python -m pytest src/Mod/cadex/cadex_tests`;
  - `CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu python -m pytest cli/tests`, with the GPU hidden.
- Re-read ADR-497 against the diff.

## Result

At `96a67c9e`:
- engine suite: **2582 passed, 56 skipped**, exit 0 (5:57);
- CLI suite, GPU hidden: **1292 passed, 1 skipped**, exit 0 (19:43).

ADR-497 holds, as the critic also found: no CLI module names a second harness, and the deleted validator had no callers.

Not done here, and still open: the Codex and pi code under `shell/` went with the delete commit (ADR-498, the next record). `docs/ROADMAP.md` Phase 6 still lists the three harnesses. That is R1's to mark historical, because a work unit does not hand-edit ROADMAP.

Dispatch closed: 1 unit — catch-up record for iteration 6's ADR-497 (Claude Code is the only harness), with suite results measured at its commit

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 96a67c9e2b5e7f97e1430b64e25c0e9a858bd579

## State Impact

- target: sunny-clover-3750 — ADR-497 (commit 96a67c9e): Claude Code is the only harness; AGENTS.md and VISION say so, the dead macOS runtime validator (imported ADR-021-deleted CadexProvider/CadexCodex, no callers) is deleted, and test_claude_code_is_the_only_harness pins that no cli/cadex_cli module names codex, pi_tools, PiBackend or registerTool. Measured at 96a67c9e: engine suite 2582 passed / 56 skipped; CLI suite (GPU hidden) 1292 passed / 1 skipped.
