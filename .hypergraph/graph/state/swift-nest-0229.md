---
node_id: 24999ced-c15e-59f7-88d3-3792e2cf3b41
slug: swift-nest-0229
title: D3. Autonomous runs are first-class in the dashboard (orun2)
created_at: '2026-10-03T10:54:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run orun2: **D3. Autonomous runs are first-class in the dashboard.** - The dashboard lists runs beside projects: - CLI agent turns; - Ouroboros runs (read-only from `.ouroboros/runs/<run>/` and the run branch). - Each run shows: - its iterations and critic verdicts; - the charter criteria; - the artifacts its records point to (renders, reports, probe pages). - orun1's review material (`docs/probes/orun1/`) renders in the dashboard from the repo alone. It replaces what `~/orun1-review/build.py` built by hand, which proves the per-run review pages are no longer needed. [rec: winter-stone-5109]

Declared target: `gap-d3-autonomous-runs-first-class`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun2 gap title carries the run. Flip to working only when the criterion has measured evidence; it stays open until then [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
