---
node_id: dfbdfb50-e25f-5fac-9b90-61a276efe60f
slug: green-sea-3991
title: The fork's delta against upstream is smaller than at the start of this run
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: superseded
## Current

Open charter criterion: **The fork's delta against upstream is smaller than at the start of this run**, measured by the delta manifest AGENTS.md names, and the manifest is honest about every inherited file touched. [rec: empty-wolf-3962]

Declared target: `gap-fork-s-delta-against-upstream`. This node tracks the criterion as a gap; it becomes working only with evidence that the criterion is met. Truncated impact wording is resolved from the full charter in the same record [rec: empty-wolf-3962].

FreeCAD manifest-scoped M totals (files / inserted / deleted) are now **56 / 1,635 / 1,881**, versus **47 / 1,804 / 1,907** at nt2 start `7dd3d045`. The translation-updater disable moved them from 56 / 1,634 / 1,820 to 56 / 1,635 / 1,832, and the helper deletion removed 49 inherited lines to reach 1,881; both are updater-only edits to `src/Tools/updatecrowdin.py`, with zero whole-file saving and manifest membership and the modification notice unchanged [rec: green-stone-3882] [rec: autumn-arrow-3125]. Inherited files remaining are **3,433**, down from **7,277** at run start; the Tk runner deletion saved **399 lines / 15,021 bytes** as a whole file [rec: silver-lodge-1952]. Blender remains **44 / 1,046 / 129** and **19,052** inherited files [rec: silver-lodge-1952] [rec: autumn-arrow-3125].

Reconcile judgement: retain **open**. Both FreeCAD line totals and the inherited remaining count are below run start, but the modified-file count (56 versus 47) is higher, and deleting lines inside an already-modified inherited file raises the deleted-line total while the file count stays put. The Tk runner and translation-writer removals each close only their own boundary; broader Test removal remains unqualified, and the broad criterion is not established. Whole-file deletions and M-line savings remain separate measures [rec: silver-lodge-1952] [rec: autumn-arrow-3125].

The earlier Preferences guard removal passed both source and staged GUI-denied import/solver-dispatch probes, release build/install/stage, **2,023 source tests / 52 skips**, and **26 fresh packaged lifecycle/licensing tests**, including a jointed assembly. Inherited CTest exited 8 with **162 failures / 1,526 run**, zero new names against the 164-name baseline. Local stage evidence does not prove a relocatable release, Windows or GUI behavior; these fresh gates supersede the audit's existing-payload-only result [rec: proud-moon-9023].

The Test runner deletion passed release build/install/stage, **2,023 engine tests / 52 skips**, **26 fresh packaged lifecycle/licensing tests**, **12 GUI-denied UnitTests** and **4/4 Cadex CTests**. Inherited CTest exited 8 with **162 failures / 1,526 run**, unchanged from the disable and with no new names against baseline; all 1,533 registrations and disabled/skipped names were unchanged. These gates cover the local stage, not a portable release or GUI, shell, Windows or remote execution [rec: silver-lodge-1952].

The translation-updater pair (ADR-232) is now implemented, not documentation only. Each unit passed one release build, full engine **2,034 passed / 52 skipped**, inherited CTest exit 8 with **162 failures / 1,526 enabled** and zero new names against the 164-name baseline, eleven isolated updater tests, combined updater/licensing **21 passed / 1 packaged-license skip**, byte-identical App/Base TS files (78), a generated QRC referencing 76 QMs, and an installed headless Qt translation probe. No install/stage, fresh packaged lifecycle or shell gate ran, because the updater has no build/install rule and the payload was untouched; no live network workflow is claimed. Reconcile judgement: retain **open**; the pair reduces inherited lines but does not meet the criterion as measured [rec: green-stone-3882] [rec: autumn-arrow-3125].

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
- silver-lodge-1952 — ADR-230: one inherited file / 399 lines / 15,021 bytes removed, current M and remaining-file counts, fresh gates and criterion kept open

- eager-garden-8009 — updater audit qualifies a bounded future writer removal without changing inherited source or manifest
- cold-clover-8123 — documentation-only disposition claims no fork-delta saving and requires a later implementation bet
- green-stone-3882 — ADR-232 disable: updater-only edit moves FreeCAD M totals to 56/1,635/1,832; fresh build/engine/CTest gates, no whole-file saving
- autumn-arrow-3125 — ADR-232 delete: 49 inherited lines removed, totals 56/1,635/1,881; same gates green, Blender unchanged, criterion kept open


## Superseded

Parked by the operator before nt3 (2026-09-07). The criterion moved to `## Later criteria` in the charter, where it seeds no gap. It is not abandoned: the human promotes it back into `## Done criteria` when the nt3 frontier — the lifecycle walk and the headless review calls — lands or blocks. No evidence about the criterion itself changed.
