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

Declared target: `gap-d1-one-command-from-clone`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun2 gap title carries the run. Flip to working only when the criterion has measured evidence; it stays open until then [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
