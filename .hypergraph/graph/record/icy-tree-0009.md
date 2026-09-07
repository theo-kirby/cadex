---
node_id: a7c15d1b-932a-5ddb-a8e7-65817e3acfa5
slug: icy-tree-0009
title: Delete three disabled Material GUI scripts with retained App verification
created_at: '2026-09-07T03:19:37+00:00'
parents:
- amber-tower-7307
summary: ''
---
## What

Deleted exactly Material/InitGui.py, MaterialEditor.py and TestMaterialsGui.py
following their separate copy/install disable. Updated ADR-225, PHASE8-AUDIT,
FREECAD and the corresponding ROADMAP checkbox. Removed 1,093 lines / 43,917
bytes; retained all protected Material App/tests/resources, TestMaterialDocument,
Qt and Assembly code.

## Why

Iteration 48 serves mission 3 and frontier round-glacier-2865, following the
explicit amber-tower-7307 deletion bet. The overseer's separate maintainer and
planner passes already landed (3a474e7d/bcac7e7a, 8d524a90); the plan explicitly
clears that prerequisite. Repeating the ordering handoff would ignore current
evidence. The bounded, previously disabled subset needs no human decision;
broad GUI-source and fork-delta obligations remain open.

## Method

Confirmed disable d7e2b59c and committed-HEAD licensing (10 passed, one skipped
without the payload variable). Repeated consumer, bytecode and generated-rule
searches; no stale copies required cleanup. Regenerated debug only, ran one
release build, install and completed stage before all payload readers. Verified
retained source equality, Materials.so and card/model resources. Ran full engine
pytest, fresh packaged lifecycle/licensing, installed Material App startup probe,
and serial inherited CTest with failure-name comparison to baseline. Audit's
Material deletion section records exact commands, metrics, logs and limits.
The ad-hoc CTest checker initially assumed dashboard XML existed; switched to
the actual per-test log to count retained C++ tests, without modifying or
rerunning tests. Export/check the graph and verify committed-HEAD licensing
again after the single commit.

## Result

Configure/build/install/stage exited 0. Active debug/release/install/stage paths
and generated rules lack the three scripts and bytecode; protected components
remain. Engine: 2,023 passed, 52 skipped in 258.78 s. Packaged: 26 passed in
18.07 s. Material App: 15 passed, no errors/failures/skips in 0.176 s; GuiUp
false, no FreeCADGui import. All 35 Material C++ and four Cadex ctests pass.
CTest exits 8: 162 failures / 1,526 enabled tests in 128.19 s, no additions to
the 164-name baseline, three skipped/seven disabled. Baseline-only names remain
DlgVersionMigrator_Tests_run and SpreadsheetRenameProperty.renameProperty.
Manifest equality/notices remain 56 FreeCAD / 44 Blender; surviving M totals
1,637 added / 1,819 deleted and 1,046 / 129. FreeCAD inherited files remaining
fall 3,438 to 3,435; Blender stays 19,052. These three whole-file deletions do
not count as surviving-file M savings or close broader GUI/fork-delta claims.
Debug was configured only; the 2.4 GB local stage has expected external rpath
diagnostics, not relocatable-distribution or Windows proof. External unsupported
GUI imports remain the compatibility risk. No shell change, GUI launch,
training, second build, state edit or reconciliation. Next: the plan's separate
Main freecad.rc.cmake-only deletion; preserve the shared launcher verbatim.
Dispatch closed: 1 unit — three disabled Material GUI sources deleted and verified.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 8d524a904968ddb9aa154f3006eecfee34239191

## State Impact

- target: round-glacier-2865 — ADR-225 source deletion removes exactly three disabled Material GUI scripts; protected App/tests/resources retained; build/install/stage pass, engine 2023 passed/52 skipped, packaged 26 passed, Material App 15 and C++ 35 passed, CTest 162 baseline failures with no additions. Broader GUI-source and fork-delta obligations remain open.
