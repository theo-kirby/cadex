---
node_id: 7a78f8e7-71f5-5fed-9f3e-82a49b469099
slug: even-clover-8953
title: 'orun2 R1: docs/DASHBOARD.md replaces REVIEW-DESIGN.md as the UI spec (ADR-501)'
created_at: '2026-10-03T15:47:51+00:00'
parents:
- careful-rain-8917
summary: ''
---
## What

`docs/REVIEW-DESIGN.md` is moved with `git mv` to `docs/DASHBOARD.md` and becomes the dashboard's UI spec (ADR-501, commit `f132d3e9`). It has a new preamble: the dashboard is the second of the three parts (ADR-500) and the only UI; it restates charter A2 (standard-library server, vanilla JS, no build step) and A3 (the project directory is the truth; writes only through the CLI's paths). §1 Purpose now says what is true today: the server answers `GET`/`HEAD` only, and D2's steering controls are still to come. §2–§17 are unchanged: hierarchy, the 12/14/17/22 px type scale, the dark palette tied to the viewport's scene background, and the dark prototype floor of §10 and §16. Every live pointer now names `DASHBOARD.md`: AGENTS.md's doc row (still 215 lines), README (both links), VISION, CLI.md, the static files' comments, `video.py` and four tests. New test `test_dashboard_md_replaces_review_design_as_the_ui_spec` in `cli/tests/test_project_docs.py`.

## Why

The critic named this unit: create DASHBOARD.md, carry over palette, type scale and dark floor, re-point README, AGENTS.md and the tests, add an ADR and run both suites. It also fixes the inconsistency the critic flagged: ARCHITECTURE linked a missing DASHBOARD.md and README's DASHBOARD link pointed at REVIEW-DESIGN.md. Before this unit, the retroactive record `careful-rain-8917` was written for iteration 11, as the critic asked first.

**Deviation:** the critic asked to move REVIEW-DESIGN.md to `docs/history/`. Every rule in it is live, so it was renamed rather than copied: a copy in history would be a stale second version of the current spec, and `git log --follow` reaches the old name. ADR-501 records this. BLENDER.md, BLENDER-TREE.md and BLENDER-RECIPES.md were already in `docs/history/`; the new test pins that.

## Method

`git mv`, a scripted preamble rewrite, then `sed` over the live references. The new test first caught AGENTS.md's row still naming the old file; reworded. `docs/review-design/` (the ot6 evidence images) keeps its name because §7 and §8 and `test_review_design.py` cite it.

## Result

What is true now: `docs/DASHBOARD.md` is the UI spec, no `docs/REVIEW-DESIGN.md` exists, and no live doc or `cli/` file names it (test-pinned). Gates: `pixi run test-engine` gave 2582 passed, 56 skipped. `pytest cli/tests` with the GPU hidden gave 1296 passed, 1 skipped. Only comments changed in `cli/cadex_cli`, so no engine, protocol or payload change was made and no packaged gate was needed.

What R1 still needs: pruning the stale frontier. That is ot7 F4–F7 and F10 (`polished-forest-0215`, `stormy-aspen-5433`, `narrow-dune-9454`, `rapid-grove-9687`, `first-snow-5587`), ot10 A5 and A7 (`loyal-fountain-8709`, `rough-vale-0587`), orun1 C1 (`gentle-bramble-6120`), and the shell-era planner bets (the short plan `young-crane-9546` still names a "shell client"). Each needs a record whose impact supersedes it. The unreconciled tail is now two records (this one and `careful-rain-8917`).

Dispatch closed: 1 unit — docs/DASHBOARD.md replaces REVIEW-DESIGN.md as the UI spec (ADR-501), live pointers re-pointed and test-pinned

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: f132d3e92db4f448ddddfaafedc701b01db06b19

## State Impact

- target: eager-sea-3906 — docs/DASHBOARD.md is the UI spec (git mv of REVIEW-DESIGN.md, ADR-501, commit f132d3e9) keeping hierarchy, type scale, dark palette and dark floor; all live pointers re-pointed; pinned by test_dashboard_md_replaces_review_design_as_the_ui_spec; BLENDER docs confirmed under docs/history. Open: frontier pruning (ot7 F4-F7, F10; ot10 A5, A7; orun1 C1; shell-era bets)
