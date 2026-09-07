---
node_id: f5c026e9-5dd0-5cb0-b2c7-db2decd4c38e
slug: light-arbor-2584
title: Audit Material GUI registrations and preserve headless consumers
created_at: '2026-09-07T02:44:53+00:00'
parents:
- shady-ivy-2659
summary: ''
---
## What

Audited Material's GUI script registrations; documented the exact three-entry
copy/install disable boundary in PHASE8-AUDIT.md, ADR-225, FREECAD and ROADMAP.
No source, CMake, payload or state node changed.

## Why

Mission 3 and open frontier round-glacier-2865, following shady-ivy-2659's short
bet after MeshPart deletion. The stale overseer reconciliation request conflicts
with this dispatch's explicit prohibition; the reversible choice is the already
planned contributor audit, leaving reconciliation to the maintainer. No human
input or new motor search is needed.

## Method

Traced repository consumers, headless loader and registered test discovery,
Material scripts and App dependencies, shared copy/install macros, generated
debug/release rules, and source equality in active build/install/stage roots.
Inspected TestMaterialDocument separately rather than treating its filename as
proof. Ran existing-payload lifecycle/licensing and an installed FreeCADCmd
script asserting headless startup and running TestMaterialsApp. Exact commands,
retained boundary, stale-copy procedure and subsequent disable gates are in
PHASE8-AUDIT.md. Documentation whitespace and hypergraph checks are final gates.

## Result

Qualify only InitGui.py, MaterialEditor.py and TestMaterialsGui.py entries in
MaterialScripts_Files for the next separate disable. Nine active copies match
source; no debug copies or matching bytecode existed at inventory. Preserve
TestMaterialDocument and all App/tests/resources, importFCMat, materialtools,
retained Qt and Assembly proxies. Existing packaged gates: 26 passed in 14.45 s;
installed App suite: 15 passed in 0.180 s with no errors/failures/skips and GUI
false. No full build, full engine suite, inherited CTest or fresh stage was run:
this is audit evidence only. Next is conditional disable with stale-copy cleanup,
one build and serial install/stage/gates; deletion requires a later verified unit.
Broader GUI-source and fork-delta claims remain open. BLDC searches stay stopped.
Dispatch closed: 1 unit — Material GUI registration boundary audited.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 847c03b9482e5dc7a3103adb949eb48d4c6e6f89

## State Impact

- target: round-glacier-2865 — ADR-225 qualifies exactly three MaterialScripts_Files entries for later copy/install disable; preserve App/tests/resources and TestMaterialDocument. Existing payload 26 tests and installed App 15 tests pass; no disable or deletion yet, broader GUI obligations remain open.
