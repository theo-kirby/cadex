---
node_id: 773e7144-483a-5311-8e87-997bb1854c74
slug: civic-sand-2641
title: Phase 8 `src/Gui` delete commit landed
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

**The Phase 8 `src/Gui` directory-delete criterion is met (ADR-214).** After separate metatype and disable prerequisites, thirteen GUI directories and three retired Main/InventorBuilder sources were deleted: 3,734 files / 137,376,129 bytes. App metatypes, Qt components and headless Assembly publication remain [rec: terse-ridge-1619].

Debug/release configuration and one release build pass. The engine suite reports 2,021 passed / 52 skipped plus the expected precommit manifest-vs-HEAD failure; working-tree manifest equality passes. Both cadex ctests pass. After serial discovery repair, inherited ctest retains the exact 1,544-test inventory and 162 baseline failures / 1,537 enabled cases, unchanged skips and disabled cases; all 35 Material tests pass [rec: terse-ridge-1619].

Stale local GUI artifacts were quarantined before fresh install and staging. The follow-up packaged lifecycle/licensing run passes all 26 tests, including the committed-HEAD manifest equality deferred at deletion. It reuses that stage; it is not another build. The payload is a local 2.4 GB stage-only build with external rpath warnings, not a relocated release [rec: terse-ridge-1619] [rec: humble-shore-1680].

Reconcile judgement: mark this narrow directory criterion working because deletion and the deferred packaged check are now evidenced. The broader no-GUI-source exit remains open under inherited-tree reduction: residual installed GUI scripts and required mixed Assembly modules remain. Neither this status nor static consumer searches establish arbitrary external-import safety or Windows behavior [rec: humble-shore-1680].

## Negative knowledge

- [scope: audited Phase 8 deletion boundary at d031bde0 | confidence: high | evidence: wise-isle-1725] Historical blocker, resolved by sharp-pond-0087 and fair-cabin-5280; at the audit, BUILD_GUI=OFF alone did not establish deletion readiness: twelve headless Material sources and six retained tests include Gui/MetaTypes.h; release Ninja records the header as an active valid dependency. Debug configure then succeeded with BUILD_GUI=ON.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- wise-isle-1725 — ADR-213: dependency audit and exact deletion boundary/gates; active metatype and debug GUI prerequisites keep criterion open
- sharp-pond-0087 — preserved metatypes and migrated retained includes; release dependency/build/Material evidence
- fair-cabin-5280 — completed GUI disable, verified rejection and baseline gates; deletion and packaged verification remain open

- terse-ridge-1619 — ADR-214: verified directory deletion, fresh install/stage and scoped delta measurements
- humble-shore-1680 — ADR-215: 26 packaged tests resolve HEAD verification; residual consumers and narrow Measure boundary
