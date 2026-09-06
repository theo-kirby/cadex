---
node_id: dfbdfb50-e25f-5fac-9b90-61a276efe60f
slug: green-sea-3991
title: The fork's delta against upstream is smaller than at the start of this run
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion: **The fork's delta against upstream is smaller than at the start of this run**, measured by the delta manifest AGENTS.md names, and the manifest is honest about every inherited file touched. [rec: empty-wolf-3962]

Declared target: `gap-fork-s-delta-against-upstream`. This node tracks the criterion as a gap; it becomes working only with evidence that the criterion is met. Truncated impact wording is resolved from the full charter in the same record [rec: empty-wolf-3962].

**Scoped line reduction measured; broad criterion remains open.** Against nt2 run-start `7dd3d045`, the post-deletion FreeCAD manifest/M-file comparison changes from 47 files and 1,804 inserted / 1,907 deleted lines to 56 files and 1,633 inserted / 1,795 deleted lines. Blender stays 44 files and 1,046 inserted / 129 deleted lines. The 3,734 removed files / 137,376,129 bytes are reported separately from modified-file delta [rec: terse-ridge-1619].

The documentation-only residual audit leaves those metrics unchanged and confirms committed-HEAD manifest equality in the 26-test packaged lifecycle/licensing pass. Reconcile judgement: fewer changed lines alongside more modified FreeCAD files establishes only the stated scoped reduction; retain the broader criterion as open, as both records declare [rec: terse-ridge-1619] [rec: humble-shore-1680].

## Negative knowledge

None yet.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- wise-isle-1725 — nt2 run-start and audited HEAD manifest/M-file comparison is unchanged; criterion remains open

- terse-ridge-1619 — ADR-214: verified directory deletion, fresh install/stage and scoped delta measurements
- humble-shore-1680 — ADR-215: 26 packaged tests resolve HEAD verification; residual consumers and narrow Measure boundary
