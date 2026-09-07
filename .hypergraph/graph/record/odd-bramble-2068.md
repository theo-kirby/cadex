---
node_id: 43027bc9-cc5b-57f4-82fa-97165b601381
slug: odd-bramble-2068
title: Disable Material GUI registrations with fresh payload verification
created_at: '2026-09-07T02:56:31+00:00'
parents:
- light-arbor-2584
summary: ''
---
## What

Disabled only InitGui.py, MaterialEditor.py and TestMaterialsGui.py in
MaterialScripts_Files, retaining all three sources unchanged. Updated ADR-225,
FREECAD, PHASE8-AUDIT and the disable ROADMAP checkbox.

## Why

Iteration 45 advances mission 3, frontier round-glacier-2865, following the
explicit safe subset in light-arbor-2584 and the overseer's disable instruction.
Preserving sources, App/tests/resources, TestMaterialDocument, retained Qt and
Assembly consumers is the reversible audited choice. No human input is needed.
The instruction to reconcile at three records conflicts with this dispatch's
explicit prohibition; leave reconciliation to the separate maintainer.

## Method

Quarantined nine stale release/install/stage copies outside active roots.
Regenerated debug without building; ran one full release build, install, and
completed stage before any payload reader. Checked generated copy/install rules,
all four active paths, retained source equality, resources and Materials.so.
Ran full engine pytest, serial inherited CTest with failure-name comparison,
fresh packaged lifecycle/licensing and installed TestMaterialsApp startup probe.
PHASE8-AUDIT.md records commands, local logs, exact scope and limitations.
Checked working-tree manifest equality and existing notice; repeat licensing
against committed HEAD as the final post-commit check. Use hypergraph export
and check before committing this single record with the implementation.

## Result

Configure/build/install/stage pass. Three scripts and bytecode absent in all
active roots, sources retained; debug configured only. Stage-only payload is
2.4 GB with expected external rpath diagnostics, not a relocatable release.
Engine: 2,023 passed, 52 skipped in 261.29 s. Packaged: 26 passed in 17.03 s.
Installed App: 15 tests, zero errors/failures/skips in 0.188 s, GuiUp false,
App suite registered and GUI suite absent; no FreeCADGui import. All 35 Material
C++ tests and four Cadex ctests pass. CTest exits 8 with 162 failures / 1,526
enabled tests in 128.24 s; none new against the 164-name baseline, three skipped
and seven disabled unchanged. Baseline-only names remain DlgVersionMigrator_Tests_run
and SpreadsheetRenameProperty.renameProperty. Initial ad-hoc manifest comparison
wrongly excluded a premodified entry and initial CTest regex included skipped/
disabled summaries; correcting those checks to the actual contracts passes,
without any code, baseline or manifest change.
Manifest remains 56 FreeCAD / 44 Blender; surviving-file M totals 1,637 added /
1,819 deleted and 1,046 / 129 respectively. Risk is unsupported external GUI
imports; broad GUI-source and fork-delta claims remain open. No GUI launch,
shell change, training, source deletion or second build. Next: maintainer has
three unreconciled records; deletion needs a later verified unit and replan.
Dispatch closed: 1 unit — Material GUI copy/install registrations disabled and verified.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: c1b629e4d2ea0c1834107ac029faf3e941fff204

## State Impact

- target: round-glacier-2865 — ADR-225 disables exactly three Material GUI copy/install entries with sources and protected consumers retained; one build/install/stage, engine 2023 passed/52 skipped, packaged 26 passed, Material App 15 and C++ 35 passed; CTest 162 baseline failures with no additions. Source deletion awaits separate unit and replan; broader GUI and fork-delta obligations remain open.
