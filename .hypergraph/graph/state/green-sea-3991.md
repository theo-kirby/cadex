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

**Scoped line reduction measured; broad criterion remains open.** Import-relative, manifest-scoped M-file totals against nt2 run-start `7dd3d045` [rec: terse-ridge-1619] [rec: silver-beacon-0723] [rec: zesty-otter-9342]:

- FreeCAD: 47 files, 1,804 / 1,907 at nt2 start; 56 files, 1,633 / 1,796 after the Measure delete; 56 files, 1,638 / 1,797 after the Help disable [rec: terse-ridge-1619] [rec: silver-beacon-0723] [rec: zesty-otter-9342].
- Blender: 44 files, 1,046 / 129 at nt2 start, unchanged since [rec: silver-beacon-0723] [rec: zesty-otter-9342].

The Help disable commit adds five inserted and one deleted line to the FreeCAD modified-file totals; the Help audit itself changed nothing [rec: silver-beacon-0723] [rec: zesty-otter-9342]. Whole deleted upstream volume (3,734 files / 137,376,129 bytes at ADR-214, the Measure shim, and any future Help delete) is reported separately from modified-file delta [rec: terse-ridge-1619] [rec: silver-beacon-0723].

**The manifest is honest at HEAD.** The packaged lifecycle/licensing gate, including committed-HEAD manifest equality, passed 26 tests against the existing payload after the audit and 26 tests against a freshly staged payload after the Help disable [rec: silver-beacon-0723] [rec: zesty-otter-9342].

Reconcile judgement: fewer changed lines alongside more modified FreeCAD files establishes only the stated scoped reduction. Every record folded here declares the broad criterion open; retain it as open [rec: terse-ridge-1619] [rec: humble-shore-1680] [rec: silver-beacon-0723].

## Negative knowledge

None yet.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- wise-isle-1725 — nt2 run-start and audited HEAD manifest/M-file comparison is unchanged; criterion remains open
- terse-ridge-1619 — ADR-214: verified directory deletion, fresh install/stage and scoped delta measurements
- humble-shore-1680 — ADR-215: 26 packaged tests resolve HEAD verification; residual consumers and narrow Measure boundary
- silver-beacon-0723 — ADR-216: audit leaves totals at 56/1633/1796 and 44/1046/129; existing-payload manifest gate 26 passed
- zesty-otter-9342 — ADR-217 gates: totals 56/1638/1797 after the Help disable; fresh-payload manifest gate 26 passed
