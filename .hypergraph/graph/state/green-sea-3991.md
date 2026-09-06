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

**nt2 baseline measured, no reduction:** the audit uses explicit run-start commit `7dd3d0458c61d300100177955267eca074d6865b` and audited HEAD `d031bde0`. Both have identical inherited manifests and modified-file numstat: FreeCAD 47 M files, 1,804 inserted / 1,907 deleted lines; Blender 44 M files, 1,046 inserted / 129 deleted lines, including one premodified entry. Reconcile judgement: retain `open`; this is the scoped manifest/M-file metric documented in `docs/PHASE8-AUDIT.md`, and it supplies no evidence of reduction [rec: wise-isle-1725].

## Negative knowledge

None yet.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- wise-isle-1725 — nt2 run-start and audited HEAD manifest/M-file comparison is unchanged; criterion remains open
