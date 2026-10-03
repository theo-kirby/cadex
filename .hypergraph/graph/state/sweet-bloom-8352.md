---
node_id: c1d1836d-c602-5b62-a354-210d90caf84a
slug: sweet-bloom-8352
title: D1. One command from a clone to a running dashboard (orun2)
created_at: '2026-10-03T10:54:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run orun2: **D1. One command from a clone to a running dashboard.** - On a fresh clone on linux (sb1x), a documented, short command sequence builds the engine and serves the dashboard over a projects directory: - for example `pixi run setup-engine && pixi run app`; - `./cadex` with no project should open or serve the dashboard. - No step needs git-lfs, Xcode or `shell/lib`. - **Measured before and after:** - tracked files; - working-tree size; - Python and JS LOC by tree; - the number of setup steps; - wall time from clone to the dashboard's first page; - installed footprint. [rec: winter-stone-5109]

**Before numbers measured** (`docs/probes/orun2/D1-BEFORE.md`, at `a375745c`; `measure_d1.sh` is ready to re-run for the after): 25,633 tracked files, 19,446 (75.9%) under `shell/`; 6,716 LFS objects, all under `shell/`, declaring 824 MB (pointers only on sb1x); Python LOC 873,875 total — `shell/` 549,304, `mesh_agent` 29,629, `src/Mod/cadex` 139,983, `cli/` 46,392; JS 2,531; C/C++ 3.59M in `shell/`, 761k in `src/`. Setup is 4 steps either way: the app route is macOS-only and needs git-lfs and Xcode; the linux engine-plus-review route is undocumented as a sequence and serves one project, read-only. Clone → first dashboard page on sb1x took **114 s** (clone 6 s, warm `pixi install` 1 s — cold download not measured, `setup-engine` 1 s, `build-engine` 105 s with ccache off). Footprint: `.pixi` 5.65 GB, `build/release` 226 MB, staged payload 3.26 GB, no linux app bundle. Reconcile judgement: stays `open` — only the before half exists and no one-command path has been built [rec: old-arrow-4088].

Declared target: `gap-d1-one-command-from-clone`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun2 gap title carries the run. Flip to working only when the criterion has measured evidence; it stays open until then [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- old-arrow-4088 — D1 before numbers measured; measure_d1.sh ready for the after run
