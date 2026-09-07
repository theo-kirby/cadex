---
node_id: 1f0ab01c-28df-5cb1-a3fc-cf624d276971
slug: chilly-summit-3112
title: Delete the disabled Main GUI resource template
created_at: '2026-09-07T03:27:53+00:00'
parents:
- icy-tree-0009
summary: ''
---
## What

Deleted only src/Main/freecad.rc.cmake: 47 lines / 1,641 bytes. Updated
ADR-226, PHASE8-AUDIT, FREECAD and a template-only ROADMAP checkbox; left the
four inactive shared launcher arms explicitly deferred. No other source changed.

## Why

Iteration 49 serves mission 3 and frontier round-glacier-2865, following
icy-tree-0009 and the amber-tower-7307 template-only bet, as the overseer
requested. The prior consumer-disable commit is an ancestor and no new
consumer exists. The reversible boundary preserves the entire shared launcher
and active command-line resources; broader GUI-source and fork-delta claims
remain open. No human decision or Windows behavior assumption was needed.

## Method

Confirmed ancestor 9f7c3268 removed template configuration and the GUI targets;
searched tracked non-documentation consumers. Quarantined only the two audited
retired debug Main autogen metadata directories. Regenerated debug, ran one
release build, installed, then completed staging before payload readers.
Verified active rules and outputs lack retired resources and protected Main
files are byte-identical to preceding HEAD. Reused retained Material App/C++
probes and resource equality checks; ran full engine pytest, serial inherited
CTest with baseline failure-name comparison and fresh packaged lifecycle/licensing.
PHASE8-AUDIT records commands, local logs, metrics and limitations. The ad-hoc
metric checker initially used filesystem exists, undercounting dangling Blender
symlinks; corrected it to tracked paths minus pending deletions, without any
source change. Export/check the graph and repeat licensing on committed HEAD.

## Result

Debug configure, one release build, install and local 2.4 GB stage all exit 0.
Full engine pytest: 2,023 passed, 52 skipped in 264.42 s.
Packaged lifecycle/licensing: 26 passed in 22.28 s. Pre-deletion committed-HEAD
licensing: 10 passed/1 payload-variable skip in 0.23 s. Material App: 15 passed,
no errors/failures/skips in 0.202 s; GuiUp false, GUI suite absent, no FreeCADGui.
All 35 Material C++ and four Cadex ctests pass. CTest exits 8 with 162 failures
of 1,526 enabled tests in 141.51 s, three skipped/seven disabled: zero additions
to the 164-name baseline; baseline-only DlgVersionMigrator_Tests_run and
SpreadsheetRenameProperty.renameProperty. Manifest membership/notices and
surviving M totals unchanged: FreeCAD 56/1,637/1,819, Blender 44/1,046/129.
Inherited remaining: FreeCAD 3,435 to 3,434; Blender 19,052. Whole-file deletion
is not surviving-file delta savings. Debug configure only, static Windows
configuration checks only; stage has external rpath diagnostics and is not
relocatable-distribution proof. External custom GUI builds remain the risk.
Next: this record makes three unreconciled nodes; separate maintainer then
planner dispatches are due before further work. No reconciliation/state edits
in this contributor dispatch. Shared launcher arms require a separate bet and
Windows validation path; broader GUI-source/fork-delta obligations stay open.
Dispatch closed: 1 unit — retired Main GUI resource template deleted and verified.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 14f4fbf2c28fc3d1be9e80f8897758fcc0b0101b

## State Impact

- target: round-glacier-2865 — ADR-226 deletes only the disabled Main freecad.rc.cmake; shared launcher/resources unchanged. Build/install/stage pass; engine 2023 passed/52 skipped; packaged 26 passed; retained Material App 15 and C++ 35 passed; CTest 162 baseline failures with no additions. Broader GUI-source and fork-delta claims remain open; three-node tail requires separate maintainer/planner dispatches.
