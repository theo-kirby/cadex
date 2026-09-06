---
node_id: 64b8ee1b-6967-5560-b7dc-9bbdba7c09b0
slug: terse-ridge-1619
title: Delete the audited Phase 8 GUI directory boundary
created_at: '2026-09-06T23:36:52+00:00'
parents:
- deep-ash-7027
summary: ''
---
## What

Delete the verified Phase 8 directory boundary in a separate unit after ADR-213's prerequisites: thirteen GUI directories, MainGui.cpp, FreeCADGuiPy.cpp and the orphan InventorBuilder test. Remove their retired build/test/doc registrations, including Main GUI targets and GUI-only script/resource registrations in the eleven retained workbench parents. Preserve App/MetaTypes.h, Qt components, all headless App trees, command-line launchers and mixed Assembly native publication modules. Update ADR-214, ROADMAP's narrow directory checkboxes, FREECAD ledger, architecture/agent orientation and the inherited manifest together.

## Why

Mission 3; targets civic-sand-2641, round-glacier-2865 and green-sea-3991. Follows deep-ash-7027's selected deletion bet after verified metatype and configuration prerequisites. The overseer's request to reconcile is already reflected in the current checkpoint/plan and conflicts with this dispatch's explicit prohibition on reconciliation; no state, plan or .ouroboros file is edited. The reversible scope choice is the audited boundary, leaving residual GUI-lineage sources and broader fork-delta claims open for the next dependency audit.

## Method

Read STATE.md, PLAN.md, the graph protocol, VISION and PHASE8-AUDIT; use ouroboros-actor and hypergraph-record. Measure tracked working-file bytes before deletion and manifest-scoped import deltas separately. Configure debug/release, perform one release build, run the full engine suite, both cadex ctests and inherited ctest with baseline-name/inventory/skip comparison. Quarantine stale generated/installed GUI artifacts, install without another build, then freshly stage and exercise the packaged lifecycle/licensing suites. Inspect retained files and release Ninja dependencies. Working-tree manifest equality and modification notices are checked before committing; repeat the HEAD-based licensing gate after the commit. Local evidence logs are /tmp/cadex-delete-*.log; durable numbers and limits live in docs/PHASE8-AUDIT.md.

## Result

Removed 3,734 files / 137,376,129 bytes total: directories 3,731 / 137,324,213; the three additional sources 51,916 bytes. Manifest matches the working tree at 56 FreeCAD files (40 src, 16 build/tests) and 44 Blender files. Relative to nt2 start 7dd3d045, FreeCAD M-file inserted/deleted lines fall from 1804/1907 to 1633/1795, while M count rises from 47 to 56; Blender stays 1046/129 and 44. Removed upstream volume is separate; no broad fork-delta closure claimed.

Debug/release configure and the single release build exit 0. Full engine suite: 2021 passed, 52 skipped, one expected precommit manifest-vs-HEAD failure in 263.29 s; the equivalent working-tree equality passes. Both cadex ctests pass in 16.74 s. Concurrent CTest discovery initially corrupted generated test metadata; regenerated all twelve discovery files serially and obtained the exact pre-deletion 1544-test inventory/properties. Inherited ctest then gives 162 failures / 1537 enabled tests, all baseline names; final serial confirmation is 123.54 s, exit 8. Same three skips, seven disabled cases and baseline-only absent DlgVersionMigrator_Tests_run / SpreadsheetRenameProperty.renameProperty. All 35 Material registrations pass. An initial summary miscounted the ten non-runs as failures; corrected extraction reads only the failure section. No baseline overwritten.

Quarantined 38 stale local paths (13 debug GUI directories, two generated resources, 22 GUI libraries/bindings and the old GUI executable). Fresh install and stage both exit 0. Payload is the documented local 2.4 GB stage-only build with external rpath warnings, not a relocated release. Retained Assembly publication modules are present; inspected GUI binary/deleted-source patterns find no stale matches in build/install/payload. Ninja has zero deleted GUI paths and 190 retained App/MetaTypes.h occurrences. No GUI launch, shell edit, remote dispatch or second build.

Next: audit remaining GUI-lineage sources and unconditional Python install lists, including Main's retired resource template/shared launcher branch and mixed Assembly publication. The thirteen-directory deletion does not prove the broader no-GUI-source exit. Keep that and the broad fork-delta frontier open. No reconciliation in this work iteration.

Fresh packaged lifecycle/licensing before commit: 25 passed and the sole expected manifest-vs-HEAD failure, 19.78 s. All lifecycle/payload-license cases pass; postcommit repeat is required to establish the HEAD comparison. Hypergraph export/check and the notice/working-tree equality checks pass before landing. Two records will be unreconciled after this contribution, not a reconciliation dispatch.

Dispatch closed: 1 unit — delete and verify the audited Phase 8 GUI directory boundary; retain the residual-source audit next.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 9d100a8ed49e87ed4d37e1cc687b5af4bc6a2e56

## State Impact

- target: civic-sand-2641 — Audited thirteen GUI directories and retired Main GUI/InventorBuilder sources deleted after separate disable prerequisites; release build, unchanged inherited baseline and fresh packaged lifecycle checks verified. Broader GUI-lineage exit remains open; postcommit HEAD manifest check required.
- target: round-glacier-2865 — Phase 8 directory deletion removes 3734 files and 137376129 bytes; retained App metatypes, Qt and headless Assembly publication. Next is residual GUI-source/install dependency audit, not speculative removal.
- target: green-sea-3991 — Manifest-scoped FreeCAD M line totals decrease from 1804/1907 to 1633/1795, while modified files increase 47 to 56; Blender unchanged. Deleted volume reported separately; broad fork-delta claim remains open.
