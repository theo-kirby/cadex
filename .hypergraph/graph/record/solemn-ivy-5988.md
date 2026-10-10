---
node_id: 371a1857-4678-5289-a541-60e27591ae34
slug: solemn-ivy-5988
title: Docs staleness audit after ADR-480..627 (ADR-628)
created_at: '2026-10-10T11:13:45+00:00'
parents:
- warm-shore-1092
- small-brook-2395
summary: ''
---
## What
A docs staleness audit after ADR-480..627. Every live doc was checked against the source (code wins, AGENTS.md):
- AGENTS.md and README;
- every docs/*.md outside history/ and probes/;
- training/README.md, training/SETUP.md and analysis/README.md;
- the agent guidance and `cadex guidance`.

Seven finished one-off audits moved to docs/history/ (ADR-628). The full list of issues is in docs/DOCS-AUDIT.md.

## Why
The shell deletion, the read-only dashboard, the no-agent change, base+styles guidance and the creature fixes all landed quickly, and the docs had drifted.

## Method
- Seven parallel sub-auditors, each owning distinct files, and the lead.
- Checks: grepping and reading the code; `--help` for all 20 subcommands and the analysis scripts; `./cadex guidance`; `./cadex style --json`; dumping OP_ARG_SPECS; `pytest --collect-only`; reading the main checkout's staged payload.
- Pinned doc tests were run after each edit.
- Both full suites ran CPU-only in the worktree (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`), with no engine build.

## Result
- 141 issues found, 106 fixed (docs-only), 35 open, reduced to 11 owner decisions (DOCS-AUDIT.md §4).
- 14 code bugs or stale model-facing strings listed and not fixed (§3). The main ones:
  - build_engine_payload.sh's version sed never matches, so every payload is 0.0.0;
  - the test_panels kernel test does not skip without an engine, so test-engine fails on a bare checkout, a plausible cause of CI's red "Engine unit suite";
  - the project_docs scaffold says detached walk continuation is not automated;
  - analysis/search.py names `./cadex -p`;
  - the BUILD_GUI CMake error says "the application is the shell".
- Fixes of note:
  - guidance delivery: a brief, then `cadex guidance`, about 48k characters;
  - dashboard: three editors, and a default of 3D+Status;
  - ROADMAP: live-mode items marked removed (ADR-528), O2b closed, entries for ADR-541..627;
  - XSCRIPT: nonexistent error codes corrected;
  - SETUP: the walk's --detach/--complete.
- Tests:
  - test-engine: 2595 passed, 243 skipped, 1 failed (test_panels kernel test, environmental, also failing on the baseline);
  - cli/tests: 1148 passed, 112 skipped, 0 failed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: worktree-agent-a1e25ab3160ba0542
- commit: 3cbb24bd41ac6af03dc3cc59132c1a681b5ed75d

## State Impact

- target: early-arbor-7123 — the living docs re-verified against source at 3cbb24bd (2026-10-10): 106 fixes, seven finished audits moved to docs/history (ADR-628); open items and 11 owner decisions in docs/DOCS-AUDIT.md; known code-side drift: payload version 0.0.0, test_panels kernel test not skipping without an engine
