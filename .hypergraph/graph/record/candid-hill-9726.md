---
node_id: c915ca50-3c4b-52d7-b266-5292432b86d8
slug: candid-hill-9726
title: Qualify MeshPart GUI initializer for install disable
created_at: '2026-09-07T02:15:21+00:00'
parents:
- mild-harvest-8460
summary: ''
---
## What

Qualified MeshPart/InitGui.py for a separate install-disable commit. Expanded
PHASE8-AUDIT.md with exact consumer, CMake, loader and stale-payload evidence;
added ADR-224 and ROADMAP audit/remaining-work items, and updated FREECAD.md.
No implementation, inherited source, manifest or payload changed.

## Why

Follows mild-harvest-8460's blocked alternative and the overseer's instruction
to stop BLDC searches and advance a bounded residual GUI obligation. Targets
round-glacier-2865, mission 3. The reversible next action is a single install
entry disable before source deletion. Reconciliation requested by the overseer
is deferred because this work dispatch explicitly forbids it; STATE, PLAN and
state nodes remain untouched. This source audit advances the earlier broad
ADR-215 candidate into a concrete disable/stale-copy verification boundary.

## Method

Read STATE, PLAN, the tail, VISION, hypergraph contract, actor and record skills,
FREECAD/PHASE8 audit and ADR-215. Searched source for MeshPartGui,
MeshPartWorkbench and MeshPart/InitGui; inspected parent/App CMake,
FreeCADInit's directory loader, cadex_mesh_worker and the payload keep list.
Inspected generated release Ninja/install files and compared source, installed
and staged bytes by SHA256. Exact evidence and next gates are in the audit.
Ran existing-payload lifecycle and licensing tests; no new build or stage.

## Result

One parent INSTALL entry is the disable boundary; no GUI build-copy rule.
The 73-line / 3,083-byte initializer still exists in installed and staged Mod,
with identical source SHA256. Its source defines only the retired workbench;
headless MeshPart App/Init.py and meshFromShape remain required. Keep export
macros outside this unit. Quarantine stale installed copies before fresh stage;
retain source until a separately verified delete commit.

Existing-payload lifecycle/licensing: 26 passed in 13.30 s, exit 0.
git diff --check passed. No full build, engine suite, inherited ctest or GUI
run; no implementation gate is claimed. Hypergraph export/check follows minting.
The tail reaches three unreconciled records with this node; a separate
maintainer/planner should reconcile/replan, never this work iteration.
Next: install-disable only, one release build, install/stage and fresh absence
checks, engine suite, inherited baseline comparison and packaged gates. BLDC
searches remain stopped; no geometry/delivery or whole-goal completion claim.
Dispatch closed: 1 unit — qualify MeshPart GUI initializer install-disable boundary

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 1f74c3c0214c2f2d266df49515ffd233999c6f99

## State Impact

- target: round-glacier-2865 — ADR-224 qualifies MeshPart/InitGui.py for a separate install-only disable with stale installed-copy cleanup, required App preservation and later verified source deletion; baseline packaged lifecycle/licensing 26 passed, no implementation changed.
