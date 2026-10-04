---
node_id: c1d1836d-c602-5b62-a354-210d90caf84a
slug: sweet-bloom-8352
title: D1. One command from a clone to a running dashboard (orun2)
created_at: '2026-10-03T10:54:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Open charter criterion for run orun2: **D1. One command from a clone to a running dashboard.** - On a fresh clone on linux (sb1x), a documented, short command sequence builds the engine and serves the dashboard over a projects directory: - for example `pixi run setup-engine && pixi run app`; - `./cadex` with no project should open or serve the dashboard. - No step needs git-lfs, Xcode or `shell/lib`. - **Measured before and after:** - tracked files; - working-tree size; - Python and JS LOC by tree; - the number of setup steps; - wall time from clone to the dashboard's first page; - installed footprint. [rec: winter-stone-5109]

**The one-command path exists.** `pixi run setup-engine && pixi run build-engine && pixi run app` — or a bare `./cadex` — serves the dashboard over `~/cadex-projects` on 127.0.0.1, an index at `/` and each project at `/p/<name>/` (ADR-502, commit a9df266e; `cli/tests/test_app.py`, including a Chromium walk) [rec: mild-grove-9448].

**Before numbers measured** (`docs/probes/orun2/D1-BEFORE.md`, at `a375745c`; `measure_d1.sh` is ready to re-run for the after): 25,633 tracked files, 19,446 (75.9%) under `shell/`; 6,716 LFS objects, all under `shell/`, declaring 824 MB; Python LOC 873,875 total — `shell/` 549,304, `mesh_agent` 29,629, `src/Mod/cadex` 139,983, `cli/` 46,392; JS 2,531. Setup was 4 steps; the linux route was undocumented and served one project read-only. Clone → first dashboard page on sb1x took **114 s** (`build-engine` 105 s with ccache off). Footprint: `.pixi` 5.65 GB, `build/release` 226 MB, staged payload 3.26 GB [rec: old-arrow-4088].

**Remaining:** the measured after numbers (`measure_d1.sh`) and a wall-clock fresh-clone run on sb1x [rec: mild-grove-9448].

Declared target: `gap-d1-one-command-from-clone`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: every orun2 gap title carries the run. Flipped to `working` this pass — the path is built and tested, but the criterion's measured after half is still missing, so it is not `done` [rec: winter-stone-5109] [rec: mild-grove-9448].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- old-arrow-4088 — D1 before numbers measured; measure_d1.sh ready for the after run
- mild-grove-9448 — bare ./cadex and pixi run app serve the dashboard over a projects dir (ADR-502)
