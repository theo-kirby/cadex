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

**Two numbers, reported together every time** [rec: sleepy-stone-2956]:

- **Manifest-scoped M metric** (files / lines inserted / lines deleted, import-relative, against nt2 run-start `7dd3d045`) — the surviving conflict surface. FreeCAD: 47 / 1,804 / 1,907 at nt2 start; 56 / 1,633 / 1,796 after the Measure delete; 56 / 1,638 / 1,797 after the Help disable; **57 / 1,637 / 1,803 after the Help delete** (`updatecrowdin.py` newly modified with notice; deleted whole files are not M entries). Blender: 44 / 1,046 / 129 at nt2 start, unchanged since [rec: terse-ridge-1619] [rec: silver-beacon-0723] [rec: zesty-otter-9342] [rec: steady-dew-8037].
- **Inherited files remaining**: 12,749 at import, 7,287 at nt2 run start, **3,468 after the Help delete**. Whole-tree deletions are credited here only, never against M. A Start delete would take M to 56 files and remaining to 3,441 [rec: sleepy-stone-2956].

The counting convention is a recorded proposal: no criterion text or test changed [rec: sleepy-stone-2956]. Whole deleted upstream volume (3,734 files / 137,376,129 bytes at ADR-214, the Measure shim, Help's 85 files) is separate from the modified-file delta [rec: terse-ridge-1619] [rec: silver-beacon-0723] [rec: steady-dew-8037].

**The manifest is honest at HEAD.** The packaged lifecycle/licensing gate, including committed-HEAD manifest equality, passed 26 tests after the Help audit, after the Help disable and after the Help delete commit [rec: silver-beacon-0723] [rec: zesty-otter-9342] [rec: steady-dew-8037]. The Start audit touched no manifest entry; engine suite 2,022 passed / 52 skipped on its tree [rec: sleepy-stone-2956].

Reconcile judgement: fewer changed lines beside more modified FreeCAD files establishes only the scoped reduction, and the Help delete record itself says the criterion is not advanced by that measure. Every record folded here declares the broad criterion open; retain it as open [rec: terse-ridge-1619] [rec: humble-shore-1680] [rec: silver-beacon-0723] [rec: steady-dew-8037] [rec: sleepy-stone-2956].

## Negative knowledge

- [scope: crediting a whole-tree deletion against the fork delta | confidence: medium | evidence: sleepy-stone-2956] The manifest M metric cannot show a tree deletion: deleted whole files are not M entries, and the file count rose 47 → 57 while whole trees left. Credit deletions against inherited files remaining and report both numbers; a proposal, not yet criterion text.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- wise-isle-1725 — nt2 run-start and audited HEAD manifest/M-file comparison is unchanged; criterion remains open
- terse-ridge-1619 — ADR-214: verified directory deletion, fresh install/stage and scoped delta measurements
- humble-shore-1680 — ADR-215: 26 packaged tests resolve HEAD verification; residual consumers and narrow Measure boundary
- silver-beacon-0723 — ADR-216: audit leaves totals at 56/1633/1796 and 44/1046/129; existing-payload manifest gate 26 passed
- zesty-otter-9342 — ADR-217 gates: totals 56/1638/1797 after the Help disable; fresh-payload manifest gate 26 passed
- steady-dew-8037 — ADR-218: totals 57/1637/1803 after the Help delete; packaged gate 26 passed after the commit; criterion not advanced by that measure
- sleepy-stone-2956 — ADR-219: the two-number counting convention; inherited files remaining 12,749 → 7,287 → 3,468
