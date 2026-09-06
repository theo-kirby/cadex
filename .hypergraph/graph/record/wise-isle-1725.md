---
node_id: 64b5ccb5-b5d4-5408-9389-6a8b7c59236f
slug: wise-isle-1725
title: Audit Phase 8 deletion boundary and headless metatype dependency
created_at: '2026-09-06T22:57:35+00:00'
parents:
- steady-rain-3009
summary: ''
artifacts:
- docs/PHASE8-AUDIT.md
---
## What

Iteration 20 completed one Phase 8 dependency/deletion-readiness audit at d031bde033aca73242fa7a668f657fa15b16935f. Added docs/PHASE8-AUDIT.md, ADR-213, corrected FREECAD's stale count, and ticked only ROADMAP's dependency-audit checkbox. No source deletion, runtime changes or edits to state/plan/charter.

## Why

Follows steady-rain-3009 and short item 2, serving mission 3 and civic-sand-2641, round-glacier-2865 and green-sea-3991. The smallest reversible action is an evidence-backed boundary before deleting conservative inherited code. Assume nt2's explicit start commit 7dd3d0458c61d300100177955267eca074d6865b is this run's baseline (not nt1). The overseer's reconcile request conflicts with the explicit contributor prohibition; this unit records only, leaving the third unreconciled node for the maintainer.

## Method

Read STATE, PLAN, hypergraph contract, VISION, FREECAD and Phase 8/ADR-022/197; traced actual disable commit d2c8bcc5abc962a7ecef32a99552fffdfaa49c84, CMake parent registrations, script installation, retained native includes and exploded publication. Enumerated tracked GUI paths and byte sizes, compared both revisions' inherited manifest and git numstat within manifest scopes excluding ours. Queried existing release Ninja dependency database without building. Ran debug configure, existing packaged lifecycle/licensing and the two cadex ctests. Reproduction commands, exact file lists, baseline metric definition and later full-build/ctest/package gates are in the audit artifact.

## Result

Deletion is not ready: 12 headless Material source files and 6 retained tests include Gui/MetaTypes.h; it is the only GUI-tree header in the existing release Ninja dependency database, and MaterialValue.cpp.o marks it VALID. Preserve the App/QtCore metatype contract before deletion; complete debug disable (configure currently succeeds with BUILD_GUI=ON), then delete the coherent directory boundary and residual registrations in a separate unit. Thirteen directory trees total 3,731 tracked files / 137,324,776 bytes; src/Gui alone is 1,960 / 65,331,470. Keep Assembly CommandCreateView/JointObject/Preferences/UtilsAssembly; the publisher still creates native ExplodedView/ExplodedViewStep from the unconditionally installed module, while the worker's import is already gone. Identity test source-presence checks, Doxygen paths, Main GUI-only targets and InventorBuilder require explicit treatment; mixed GUI-lineage Python outside the directories is not blanket-removable.

nt2 start and audited HEAD: identical manifests, FreeCAD 47 M files with 1,804 inserted / 1,907 deleted lines; Blender 44 M files with 1,046 / 129 (one entry marked premodified, already counted). No measured fork-delta reduction. Full L3 and Phase 8 deletion remain open.

Validation: pixi run configure exit 0 (17.8 s configure + 0.8 s generate); CADEX_ENGINE_ROOT pointing to existing build/engine/cadex-engine-0.0.0-macos-arm64, pixi run python -m pytest -q test_licensing_compliance.py test_cadexd_lifecycle.py: 26 passed in 16.22 s. pixi run ctest --test-dir build/release -R '^(CadexProjectRebuildDigest|CadexdLifecycle)$' --output-on-failure: 2/2 passed (2.19 s / 14.93 s, 21.85 s total). Those ctests prefer .pixi's binary; the packaged run supplies the separate GUI-less evidence. No full build, staging, full engine suite or full inherited ctest baseline comparison performed for this docs-only unit. No GUI, training or remote activity. git diff --check passes. Export/check will gate the record before commit. The unreconciled tail reaches three with this node; maintainer reconciliation is next outside this contributor dispatch, while the next implementation candidate is the retained metatype contract.

Dispatch closed: 1 unit — audited Phase 8 deletion prerequisites and unchanged run-start inherited delta.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: d031bde033aca73242fa7a668f657fa15b16935f

## State Impact

- target: civic-sand-2641 — Dependency audit complete; deletion remains open on active Material Gui/MetaTypes.h dependency and debug GUI disable, with coherent boundary and exact gates documented in docs/PHASE8-AUDIT.md.
- target: round-glacier-2865 — Phase 8 historical disable identified as d2c8bcc5; retain mixed headless Assembly publisher modules and move metatype contract before separate disable/delete units.
- target: green-sea-3991 — nt2 baseline 7dd3d045 and d031bde0 have identical inherited manifests and M-file numstat: 47 FreeCAD and 44 Blender files; no reduction measured, criterion remains open.
