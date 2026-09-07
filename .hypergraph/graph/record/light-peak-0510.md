---
node_id: e995d17c-7f58-545d-a979-9d9ae9c1b168
slug: light-peak-0510
title: Delete disabled MeshPart GUI initializer with fresh payload verification
created_at: '2026-09-07T02:37:05+00:00'
parents:
- fierce-journey-4610
summary: ''
---
## What

Deleted only MeshPart/InitGui.py after the separate install-disable commit
01e85a4e and its recorded fresh-payload evidence. Preserved App, Init.py,
meshFromShape and export macros; updated ADR-224, FREECAD, PHASE8-AUDIT and
ROADMAP's separate source-delete checkbox.

## Why

One unit from short plan young-crane-9546, serving mission 3 and frontier
round-glacier-2865, causally following fierce-journey-4610. The overseer
explicitly advanced the source deletion after the disable evidence. Its
reconcile request conflicts with this dispatch's explicit contributor ban;
leave reconciliation to the maintainer, without touching STATE, PLAN,
charter or state nodes. Unsupported external GUI users are the bounded
compatibility risk; Cadex's headless MeshPart contract is preserved.

## Method

Read actor/record skills, STATE, hypergraph contract, VISION and ADR-224's
verified disable. Delete the 73-line / 3,083-byte initializer, search source,
tests and package consumers, inspect generated install and active debug,
release, installed and fresh staged locations for source/bytecode absence.
One pixi run build-release, then install-release and completed stage-engine.
Run full engine pytest, serial inherited CTest against failure-name baseline,
fresh packaged lifecycle/licensing and an installed MeshPart box-tessellation
script. Verify working-tree manifest equality with ours exclusions; run the
committed-HEAD manifest gate after the single commit. Local logs are
/tmp/cadex-meshpart-delete-*.log; durable commands/results are in PHASE8-AUDIT.

## Result

Release/OFF build, install and completed stage exit 0. Generated install has
no initializer; debug/release Mod, install and fresh stage have no initializer
or bytecode. Debug has no built App; release/install/stage retain Init.py and
MeshPart.so. Installed script prints MESHPART-APP-OK facets=12 with GuiUp=false.
Stage is local-only 2.4 GB with expected external rpath diagnostics, not a
relocated distribution. Fresh packaged gates: 26 passed in 18.15 s, exit 0.

CTest: 162 failures / 1526 enabled tests in 142.70 s, exit 8; no new failures
against baseline 164, with DlgVersionMigrator_Tests_run and
SpreadsheetRenameProperty.renameProperty still absent. All four Cadex tests
pass (2.41/15.60/0.72/0.19 s); three skips/seven disabled unchanged. The initial
comparison mistakenly included those ten skipped/disabled entries as failures;
filtering actual Failed/SEGFAULT statuses corrects it, without a rerun.

Initial engine run: 2022 passed, 52 skipped, one failed in 267.49 s. It
inappropriately overlapped staging: the analysis guard saw bin/ccx during the
copy before staging pruned it. Completed staging has no ccx; repeated full
engine pytest only after staging finished. Future units must serialize
staging before engine tests because those tests inspect build/engine.

Full engine rerun after staging: 2023 passed, 52 skipped in 251.30 s, exit 0.
git diff --check passes. Hypergraph export/check precede the commit.

Manifest equality remains 56 FreeCAD / 44 Blender; surviving-file scoped M
totals are unchanged at 1637 inserted/1816 deleted and 1046/129 respectively.
This is one whole-file deletion of 73 lines, not M-line savings, a whole-tree
removal or closure of broad GUI-source/fork-delta criteria. Existing notices
are preserved. No shell changes, GUI launch or second full build.

Next: maintainer reconciliation is due with three pending records; contributor
reconciliation is forbidden. Then replan the residual GUI obligations (Material
registrations, mixed helpers/resources and inactive Main branches); preserve
required Assembly proxies, and keep BLDC qualification stopped.
Dispatch closed: 1 unit — delete the disabled MeshPart GUI initializer with fresh payload verification

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 01e85a4ed2300378615e1f785939dbda93e38b94

## State Impact

- target: round-glacier-2865 — MeshPart InitGui source deleted separately after verified disable; App, initializer and export macros retained. One release build, install/stage, 2023 engine passes, 26 packaged passes, 162 baseline CTest failures with no additions. Serialize staging before payload-reading engine tests. Broader GUI obligations remain open.
- target: green-sea-3991 — MeshPart deletion removes one unmodified inherited file, 73 lines and 3083 bytes; manifest remains 56 FreeCAD/44 Blender and surviving-file M totals remain 1637/1816 and 1046/129. Whole-file deletion is not M-line savings; broad criterion remains open.
