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

FreeCAD manifest-scoped M totals (files / inserted / deleted) are **56 / 1,637 / 1,815 at Start deletion**, versus 57 / 1,639 / 1,804 after its disable and 47 / 1,804 / 1,907 at nt2 run start. Inherited files remaining at Start deletion were **3,440**, versus 3,467 before deletion and **7,277 at run start**; the earlier 3,468 / 7,287 figures included added files and are superseded. Whole-file deletions do not count as M-line reduction. Blender remains 44 / 1,046 / 129 and 19,052 inherited files. FreeCAD's two line totals and inherited remaining count are lower than run start, but its modified-file count is higher [rec: southern-wood-6367] [rec: rustic-spire-7084].

MeshPart's separately verified initializer deletion removes one unmodified inherited file, **73 lines / 3,083 bytes**. The current manifest remains **56 FreeCAD / 44 Blender**, with surviving-file M totals **1,637 inserted / 1,816 deleted** and **1,046 / 129** respectively; deleting the initializer itself leaves those totals unchanged. Fresh packaged lifecycle/licensing passed 26 tests, and the working-tree manifest matched both imports [rec: light-peak-0510].

Reconcile judgement: retain **open**. The whole-file deletion is recorded independently of M-line savings; mixed scoped measures do not establish the broad criterion. This unit closes neither a whole-tree removal nor the broader GUI-source exit [rec: light-peak-0510].

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
- sleepy-stone-2956 — ADR-219: the two-number counting convention; remaining-file counts superseded by southern-wood-6367

- southern-wood-6367 — ADR-220: verified Start disable, stable-stage gates and corrected inherited-file counts
- rustic-spire-7084 — ADR-221: Start deletion, baseline-matched runtime gates and updated metrics; post-commit HEAD manifest check reserved

- light-peak-0510 — MeshPart whole-file deletion and fresh packaged verification; current manifest/M totals and broad criterion retained open
