---
node_id: 1f67058f-9a60-5950-ac96-18a588d289cf
slug: sharp-pond-0087
title: Preserve Material metatypes outside the Phase 8 deletion boundary
created_at: '2026-09-06T23:11:40+00:00'
parents:
- silver-sage-7486
summary: ''
---
## What

Preserve the headless Qt metatype contract in src/App/MetaTypes.h before Phase 8 deletion. The old Gui header forwards; twelve Material source files and six retained tests include App directly. One conservative prerequisite, no directories deleted.

## Why

Follow short-plan bet silver-sage-7486 and audit wise-isle-1725, serving mission 3 and civic-sand-2641 / round-glacier-2865. Material actively required a header inside the deletion boundary. The reversible move preserves every declaration and upstream attribution. The overseer asked for reconciliation, but this dispatch explicitly forbids it; the supplied/current tail has only the planner bet unreconciled, so use that plan and leave reconciliation to the maintainer. No human answer assumed.

## Method

Copied the original licensed header to App, verified its body below pragma once byte-identical, made Gui forward, migrated exactly 18 retained includes. Added per-file notices and manifested all 19 inherited modifications; the moved App header is a FreeCAD-derived addition. Working-tree manifest equality is 66 files (51 src, 15 build/tests). Updated ADR-213, FREECAD ledger, PHASE8-AUDIT and the narrow ROADMAP prerequisite checkbox. No CMake/install/protocol/payload changes.

Ran pixi run configure, configure-release, build-release (one build), python -m pytest src/Mod/cadex/cadex_tests, ctest --test-dir build/release -R '^(TestMaterial|TestModelProperties)' --output-on-failure, ctest --test-dir build/release -R '^(CadexProjectRebuildDigest|CadexdLifecycle)$' --output-on-failure, and pixi run test-release. Inspected pixi run ninja -C build/release -t deps; compared failure names to build/ctest_baseline_failures.txt without overwriting it. Logs are local /tmp/cadex-metatypes-*.log, not committed artifacts; durable counts and interpretation are in docs/PHASE8-AUDIT.md.

## Result

Both configurations and release build exit 0; debug remains GUI ON and release OFF. Narrow Material tests 30/30 pass (7.22 s); full ctest confirms all 35 Material registrations pass. Both cadex ctests pass (17.09 s), with their known installed-engine preference. Full ctest exits 8: 162 failures among 1537 enabled tests (127.69 s), all in the 164-name failure baseline. Baseline-only DlgVersionMigrator_Tests_run and SpreadsheetRenameProperty.renameProperty are absent from the current inventory, not removed by this unit.

Current skipped: BackupPolicyTest.StandardWithZeroFilesDeletesExisting, BackupPolicyTest.TimestampWithZeroFilesDeletesExisting, SchemaTest.imperial_building_special_function_length. Current disabled: BackupPolicyTest.TimestampWithInvalidFormatStringThrows, BackupPolicyTest.TimestampWithAbsurdlyLongFormatStringThrows, DocumentObserverTest.hasSubObject, DocumentObserverTest.hasSubElement, DocumentObserverTest.normalize, DocumentObserverTest.normalized, ExpressionParserTest.expressionsParseAsPyObjectWrapper. No baseline skip/disabled snapshot exists in the failure-only file, so no historical change claim.

Full engine suite precommit: 2015 passed, 52 skipped, 1 failed in 316.58 s. Sole failure is the HEAD-based manifest equality, expected until the source edits are committed; equivalent working-tree equality passes. Rerun the licensing suite after the single commit. Release dependencies now show zero audited GUI paths and 190 App/MetaTypes.h occurrences. No install/payload changes, so no fresh staging or packaged gate; no shell gate required. Hypergraph export/check passed before recording and will run again before commit.

Next: complete debug/explicit-GUI-request disable as its own unit, then gated directory deletion. Phase 8 and fork-delta reduction remain open. No state nodes or .ouroboros files edited.

Dispatch closed: 1 unit — preserve Material's headless metatype contract outside the GUI deletion boundary.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: fe8153d4f7c8c3e77a50284aba8ae1d5c8399042

## State Impact

- target: civic-sand-2641 — Metatype prerequisite landed: retained App header, 18 migrated includes, release build and all 35 Material tests pass; debug disable and deletion remain open.
- target: round-glacier-2865 — Headless release dependencies no longer reference the audited GUI trees; full ctest has 162 baseline failures and no new failures. Nineteen inherited edits manifested; no fork-delta reduction claimed.
