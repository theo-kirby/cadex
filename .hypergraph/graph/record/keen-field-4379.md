---
node_id: e6e98025-a8a1-5aae-a9a0-6ec82eace29c
slug: keen-field-4379
title: Share explicit CPU selection across real CLI lifecycle tests
created_at: '2026-09-08T16:21:12+00:00'
parents:
- floral-arrow-7365
summary: ''
---
## What

Consolidated duplicate CPU backend pins into the explicitly requested `cpu_training` fixture for real CLI train, iterate, walk/recovery and local dispatcher stand-in tests. Successful training receipts now assert CPU. Condensed stale test descriptions, appended ADR-253 and ticked the ROADMAP item; the non-record diff removes 33 lines and adds 31.

## Why

This completes short unit 2 following floral-arrow-7365 and the overseer's direction. It maintains charter criterion “The walk exists and is tested headlessly” (crisp-reef-5607), including its review and two-mechanism mode checks. Assumption: only explicitly requesting tests should select CPU; production backend selection and fake GPU/refusal cases remain untouched. No new option, global autouse override, CUDA investigation or additional matrix is justified.

## Method

Moved the two independent walk environment pins into cli/tests/conftest.py. Real train and warm iterate request the same fixture; walk receipts cover baseline, iterate, recovery and both mechanisms in local/remote-flag modes. Existing trainer discovery and engine skip conditions remain intact. The dispatcher stand-ins train locally and never run SSH. Each existing real training invocation remains one iteration, four environments, with a 600-second timeout. Ran `env -u JAX_PLATFORMS pixi run python -m pytest cli/tests`, clearing any inherited backend override so fixture scope is exercised. Test output remains uncommitted at the temporary cadex-cpu15-tests.log; no generated policies, traces or review dumps are committed. No engine/payload/production code changes and no build required for this test-only consolidation.

## Result

CLI gate: **223 passed, no skips, 208.17 seconds**, exit 0, without an outer CPU override. Real CPU receipt assertions and fake GPU/refusal cases all passed. `git diff --check` passed. No new lifecycle gap was exposed; the criterion already has working evidence, and this unit removes environment-dependent test selection. The bounded CPU direction selected by dry-grove-2638 is exhausted: no further rehearsal or expanded matrix is selected. Next is a fresh planner choice within the charter; parked Later criteria remain parked. GUI execution, actual remote dispatch, gait improvement and swept-motion clearance remain outside this evidence. The unreconciled tail becomes three records including this unit; no actor reconciliation was performed. Hypergraph export/check is required before this unit's commit.

Dispatch closed: 1 unit — share explicit CPU selection and verify receipts in real CLI lifecycle tests.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 399fb09b0013c77ed3553c77f8e7f1c1dfa58b6f

## State Impact

- target: crisp-reef-5607 — Real train/iterate/walk tests explicitly request one CPU fixture and assert CPU receipts; CLI gate passes 223 tests without an outer backend override. The selected finite CPU verification direction is complete.
- target: witty-spark-2613 — Local dispatcher stand-ins for both mechanisms share the requested CPU fixture and assert actual receipt devices; fake GPU/refusal contracts remain green, with no real remote dispatch.
