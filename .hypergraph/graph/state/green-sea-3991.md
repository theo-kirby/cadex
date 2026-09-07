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

FreeCAD manifest-scoped M totals (files / inserted / deleted) are now **56 / 1,634 / 1,819**, versus **56 / 1,637 / 1,819** before the Preferences guard removal and **47 / 1,804 / 1,907** at nt2 start `7dd3d045`. Inherited files remaining stay **3,434**, versus **7,277** at run start. Blender remains **44 / 1,046 / 129** and **19,052** inherited files. The finite audit qualified only the redundant JointObject Preferences guard; its removal saves three inserted lines (JointObject **42 / 5 → 39 / 5**) and removes no inherited file. Manifest membership and notices remain accurate [rec: proud-branch-1079] [rec: proud-moon-9023].

Reconcile judgement: retain **open**. FreeCAD's line totals and inherited remaining count are below run start, but its modified-file count is higher. The bounded surviving-diff saving establishes neither the broad fork-delta criterion nor the broader GUI-source exit; whole-file deletions and M-line savings remain separate measures [rec: proud-branch-1079] [rec: proud-moon-9023].

The completed implementation passed both source and staged GUI-denied import/solver-dispatch probes, release build/install/stage, **2,023 source tests / 52 skips**, and **26 fresh packaged lifecycle/licensing tests**, including a jointed assembly. Inherited CTest exited 8 with **162 failures / 1,526 run**, zero new names against the 164-name baseline. Local stage evidence does not prove a relocatable release, Windows or GUI behavior; these fresh gates supersede the audit's existing-payload-only result [rec: proud-moon-9023].

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

- proud-branch-1079 — ADR-227: finite audit of 56 surviving FreeCAD modifications and GUI-denied qualification of the Preferences guard
- proud-moon-9023 — ADR-227: exact guard removal, three inserted lines saved, fresh source/build/stage/packaged verification and unchanged inherited failure baseline
