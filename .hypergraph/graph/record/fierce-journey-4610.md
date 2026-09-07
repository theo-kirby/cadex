---
node_id: 870d31d6-bdf5-5fe3-8fdf-9f6379a8a1da
slug: fierce-journey-4610
title: Disable MeshPart GUI initializer installation with fresh payload verification
created_at: '2026-09-07T02:25:53+00:00'
parents:
- sharp-oak-9030
summary: ''
---
## What

Disabled only MeshPart/InitGui.py installation. Retained its 73-line source,
App, Init.py, meshFromShape and export macros. Quarantined stale installed and
staged copies; completed release build, install, stage and required gates.
Updated ADR-224, FREECAD, PHASE8-AUDIT and split the ROADMAP disable/delete
checkbox so only the verified disable is checked.

## Why

One unit from short plan young-crane-9546, following sharp-oak-9030, serving
mission 3 and round-glacier-2865. The existing plan already incorporates the
MeshPart audit and stopped BLDC searches. The overseer's request to reconcile
is superseded here by the dispatch's explicit prohibition on contributor
reconciliation; no STATE, PLAN, charter or state nodes were edited. Choose the
reversible install-disable before a separate source deletion.

## Method

Read actor and record skills, STATE/PLAN, hypergraph contract, VISION and
ADR-224 audit. Removed one parent INSTALL entry. Quarantined two stale copies
under /tmp/cadex-meshpart-disable-quarantine; inspected release/debug Mod,
installed environment and stage for initializer and bytecode. Ran exactly one
pixi run build-release, then install-release and completed stage-engine.
Ran full engine pytest, serial pixi run test-release with failure-name baseline
comparison, fresh packaged lifecycle/licensing and an installed engine script
which tessellates a box using MeshPart. Logs: /tmp/cadex-meshpart-disable-*.log.
Verified working-tree manifest equality with its ours exclusions and existing
CMake notice. Hypergraph export/check and committed-HEAD manifest gate follow.

## Result

Build/install/stage exit 0; Release/OFF. Generated MeshPart install no longer
names InitGui.py. No stale initializer/bytecode in inspected locations; source
retained. Release, installed environment and fresh 2.4 GB stage retain Init.py
and MeshPart.so; debug has no built App. Stage-only is local, not relocated,
with expected external rpath diagnostics. Script probe prints
MESHPART-APP-OK facets=12 with GuiUp=false. The initial -c probe printed
Application unexpectedly terminated despite exit 0; explicit script passes,
as in the earlier Measure launcher limitation. Incorrect initial ad-hoc checks
omitted manifest ours exclusions and assumed libraries lived under Mod in the
install; corrected checks follow actual manifest and lib paths, and pass.

Full engine: 2023 passed, 52 skipped in 265.63 s, exit 0. Fresh packaged
lifecycle/licensing: 26 passed in 18.07 s, exit 0. Serial CTest: 162 failures
of 1526 enabled tests in 141.81 s, exit 8; no new failures against baseline
164, whose two absent names remain DlgVersionMigrator_Tests_run and
SpreadsheetRenameProperty.renameProperty. Three skipped/seven disabled
unchanged. All four Cadex tests pass (2.02/15.33/0.75/0.19 s). Discovery is
1533 names, eleven fewer than prior Measure evidence: precisely the Start
FileUtilitiesTest.humanReadableSize tests deleted by 14d47c31; no new names.
This is stale discovery cleanup, not a MeshPart test regression.

Manifest equality: 56 FreeCAD/44 Blender. FreeCAD scoped M totals go from
1637 inserted/1815 deleted to 1637/1816; Blender remains 1046/129. No broad
fork-delta, whole-tree or no-GUI-source closure. git diff --check passes.
Next: separate verified initializer source deletion, preserving App and export
macros. Keep BLDC qualification stopped. No shell changes, GUI or second build.
Dispatch closed: 1 unit — disable MeshPart GUI initializer installation with fresh payload evidence

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 666fad07d8169aafc79c1addb879d236da3b7ae6

## State Impact

- target: round-glacier-2865 — MeshPart InitGui install-only disable verified by one release build, completed install/stage, 2023 engine tests, 26 packaged tests and 162 unchanged baseline CTest failures; source retained for separate deletion.
