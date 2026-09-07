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

FreeCAD manifest-scoped M totals (files / inserted / deleted) are **56 / 1,637 / 1,815 after Start deletion**, versus 57 / 1,639 / 1,804 after its disable and 47 / 1,804 / 1,907 at nt2 run start. Inherited files remaining are **3,440**, versus 3,467 before deletion and **7,277 at run start**; the earlier 3,468 / 7,287 figures included added files and are superseded. Whole-file deletions do not count as M-line reduction. Blender remains 44 / 1,046 / 129 and 19,052 inherited files. FreeCAD's two line totals and inherited remaining count are lower than run start, but its modified-file count is higher [rec: southern-wood-6367] [rec: rustic-spire-7084].

The Start disable's packaged lifecycle/licensing suite passed all 26 tests. At deletion, the working-tree manifest matched both imports, but the committed-HEAD manifest check was reserved until after commit; this record supplies no subsequent result [rec: southern-wood-6367] [rec: rustic-spire-7084].

Reconcile judgement: retain **open**. The scoped line and whole-tree measures improved while modified-file count rose; the broad criterion is not established by those mixed measures, and the latest HEAD manifest evidence remains pending [rec: rustic-spire-7084].

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
