---
node_id: dc377513-6b13-5651-bbe1-335a91efc854
slug: frosty-willow-1202
title: Dated history moves out of ROADMAP, CLI and MUJOCO (ADR-629)
created_at: '2026-10-10T12:24:38+00:00'
parents:
- solemn-ivy-5988
summary: ''
---
## What
Moved dated history out of the three largest live docs into docs/history/ (ADR-629), as the owner approved for DOCS-AUDIT.md §4 item 5:
- docs/ROADMAP.md → docs/history/ROADMAP-RUNS.md: the Phase 0–14 dependency diagram and its prose, every finished ([x]) or struck item of "Later — identified, not scheduled", and the body of the ot5 "Live headless project review (ADR-284)" section.
- docs/CLI.md → docs/history/CLI-EVIDENCE.md: the ot4 carriage/quill/crank/mix/cart walk rehearsals, the Wren/Lark/Reed copy proofs, the dashboard browser and restart proofs, and the page prose that duplicated docs/DASHBOARD.md (layout, the "What the page shows" list, page-only behaviour).
- docs/MUJOCO.md → docs/history/MUJOCO-SLICES.md: §4's M0–M9 slices.

## Why
Most of these docs' length was dated run logs, which hid what is true now. The audit raised it, and the owner approved the move.

## Method
- A one-off script cut each block by exact text markers, asserting each marker occurs once, and wrote the history files verbatim with HISTORICAL banners. Relative links were rewritten to resolve from docs/history/, and a link check found no broken links in the six files.
- Every heading a test or doc relies on was kept: both ROADMAP section headings, the `## Phase N` lines, MUJOCO §4 (code cites "docs/MUJOCO.md M2"), and §7c (code cites its rows), each with a one-line pointer.
- CLI.md keeps the command reference, the HTTP API table and "What the browser keeps." (test_http_api parses them), the server routes, the MJX geom-pair rule, the Status/poll paragraph, and a new short summary of where each view's model comes from.
- ADR-629 added; DOCS-AUDIT.md items marked RESOLVED.
- Tests run CPU-only (CUDA_VISIBLE_DEVICES=, JAX_PLATFORMS=cpu).

## Result
- Line counts: ROADMAP 3,014 → 2,248; CLI 3,651 → 3,159; MUJOCO 3,420 → 1,796. New history files: ROADMAP-RUNS 788, CLI-EVIDENCE 555, MUJOCO-SLICES 1,634 lines.
- `pixi run test-engine`: 2,595 passed, 243 skipped, 1 failed. The failure is the known environmental test_panels kernel test (no engine build in the worktree), identical to the ADR-628 audit baseline.
- `pytest cli/tests`: 1,144 passed, 112 skipped, 4 failed. The 4 failures were headless-browser tests that ran alongside the engine suite. Rerun alone, they passed both here and on an untouched main worktree (16 passed, 1 skipped); test_dashboard_prefix behaved the same way.
- The doc-pinning tests all pass: test_project_docs, test_http_api, test_evaluate's report-block test, test_review_design, test_dashboard_read_only and test_licensing_compliance (178 passed, 3 skipped).
- MUJOCO.md keeps its 2026-10-09 date: only §4 was touched, not the remainder.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: worktree-agent-a414735df70fb864e
- commit: 5e372f2f1ae8c69a308f09bb3e15b42c298fb4dd

## State Impact

- target: early-arbor-7123 — ROADMAP, CLI and MUJOCO carry only current and planned content; their run logs, dated evidence, duplicated dashboard prose and M0–M9 slices are in docs/history/{ROADMAP-RUNS,CLI-EVIDENCE,MUJOCO-SLICES}.md (ADR-629, commit 5e372f2f); DOCS-AUDIT §4 item 5 resolved
