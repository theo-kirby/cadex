---
node_id: d95e13e5-77a0-547c-b463-10c4f4c52511
slug: fair-cabin-5280
title: Complete Phase 8 headless configuration and reject GUI-on requests
created_at: '2026-09-06T23:19:40+00:00'
parents:
- sharp-pond-0087
summary: ''
---
## What

Complete the separate Phase 8 GUI-disable prerequisite. All nine public presets select BUILD_GUI=OFF; the shared initializer defaults OFF and rejects truthy requests before GUI dependencies or targets. GUI sources remain for the delete unit.

## Why

Follow sharp-pond-0087 and the short-plan disable bet, serving mission 3 and civic-sand-2641 / round-glacier-2865. Historical disable d2c8bcc5 covered release/package only. The reversible completion preserves source, QtCore, QtConcurrent and LinguistTools while eliminating ordinary debug's remaining GUI path. A common preset resets stale debug caches; explicit overrides and non-preset ON caches fail with remediation. No human decision assumed. Reconciliation is explicitly forbidden in this contributor dispatch despite the overseer's generic threshold request; leave it to the separate maintainer.

## Method

Changed the already-manifested/noticed InitializeFreeCADBuildOptions.cmake, common preset, and standalone rpm preset (the latter does not inherit common and previously selected TRUE). Added CMake execution regressions for unset/OFF/ON/TRUE/1 and a resolver regression covering all nine public presets. Updated AGENTS build instructions, ADR-213, FREECAD ledger, PHASE8-AUDIT evidence and the narrow ROADMAP disable checkbox. Manifest membership remains exactly 66 FreeCAD / 44 Blender; equivalent import-to-working-tree equality passes. No release install/payload/protocol rule changed.

Ran pixi run configure, configure-release, build-release (one build), python -m pytest src/Mod/cadex/cadex_tests, both cadex ctests, and test-release. Explicit GUI-on debug/release configurations used separate temporary build directories; reused debug's ON cache without a preset to prove rejection. Inspected debug Ninja targets, release Ninja dependencies and retained Qt cache entries. Compared full ctest failure names against build/ctest_baseline_failures.txt, and inventory/skips/disabled cases against the previous prerequisite log. Local logs are /tmp/cadex-disable-*.log, not committed artifacts; durable evidence is in docs/PHASE8-AUDIT.md.

## Result

Debug/release configure and one release build exit 0; caches are Debug/OFF and Release/OFF. Both real GUI-on requests and the stale ON cache fail as intended, exit 1 at the shared guard. Debug has no FreeCADGui library or GUI test targets; release has zero audited GUI source dependencies. All retained Qt components remain configured. The old initializer accepts ON (exit 0), establishing the rejection regression fails on old behavior.

Full engine suite: 2021 passed, 52 skipped, 261.86 s, exit 0. A final preset audit caught the independent rpm TRUE override; after correcting it and adding the sixth test, the focused suite passed 6/6 in 0.11 s. The full suite had included the five execution cases. No second build: the final preset change affects only unexercised rpm configuration. Linux/Windows/rpm toolchains were not configured.

Both cadex ctests pass, 22.18 s, with their known installed-engine preference. Full inherited ctest exits 8: 162 failures / 1537 enabled tests, 128.98 s. All failure names are in the 164-name baseline, identical to the previous prerequisite's 162 failures. Baseline-only DlgVersionMigrator_Tests_run and SpreadsheetRenameProperty.renameProperty remain absent. Inventory unchanged; all 35 Material registrations pass. Three skipped and seven disabled cases are unchanged by name from sharp-pond-0087. No baseline overwritten. No install/staging/fresh packaged gate because release install/payload contracts did not change; no shell gate or GUI launch.

Next: the metatype and disable prerequisites now have successful evidence for the separate gated directory deletion; retain mixed Assembly publisher modules and verify the audit's entire delete/install/stage sequence. Phase 8 deletion and fork-delta reduction remain open. The unreconciled tail reaches three records including this one; the separate maintainer should reconcile, never this work actor. Hypergraph export/check and diff checks run before the single commit. No state or .ouroboros files edited.

Dispatch closed: 1 unit — disable the inherited GUI across presets and reject GUI-on configuration requests.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: f02a7b0a4ba9736fb21b60cec61b07983738da1a

## State Impact

- target: civic-sand-2641 — GUI-disable prerequisite complete: presets headless, explicit and cached ON rejected; release build and audit gates verified. Separate directory deletion remains open.
- target: round-glacier-2865 — Complete disable after metatype preservation; 162 baseline inherited failures with unchanged inventory/skips/disabled cases, engine suite green. Qt components and GUI source retained; manifest remains 66 FreeCAD files.
