---
node_id: 773e7144-483a-5311-8e87-997bb1854c74
slug: civic-sand-2641
title: Phase 8 `src/Gui` delete commit landed
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion: **Phase 8 `src/Gui` delete commit landed** under the two-commit protocol, with the DECISIONS entry and the gate green after it. [rec: empty-wolf-3962]

Declared target: `gap-phase-8-src-gui-delete`. This node tracks the criterion as a gap; it becomes working only with evidence that the criterion is met. Truncated impact wording is resolved from the full charter in the same record [rec: empty-wolf-3962].

**Audit and prerequisites complete; directory deletion remains open (ADR-213).** The audited coherent boundary is thirteen trees, 3,731 tracked files / 137,324,776 bytes; `src/Gui` alone is 1,960 files / 65,331,470 bytes. Residual registrations, identity tests, Doxygen paths, Main GUI-only targets and InventorBuilder still require the audit's explicit delete/install/stage treatment [rec: wise-isle-1725].

The metatype contract now lives in `App/MetaTypes.h`, with the old Gui header forwarding and all twelve Material sources plus six retained tests migrated. Release dependencies contain zero audited GUI paths; release build and all 35 Material tests pass [rec: sharp-pond-0087]. All nine public presets now select `BUILD_GUI=OFF`; the shared initializer defaults OFF and rejects truthy requests. Debug/release configure and release build pass; real GUI-on requests and a stale ON cache fail as intended. QtCore, QtConcurrent, LinguistTools and GUI sources remain [rec: fair-cabin-5280].

Verification: the disable record reports 2021 engine tests passed / 52 skipped, then 6/6 focused tests after the final rpm preset correction; the full suite and build were not repeated after that correction. Linux/Windows/rpm toolchains were not configured. Both cadex ctests pass with their installed-engine preference; inherited ctest has 162 baseline failures / 1537 enabled tests, unchanged inventory, skips and disabled cases, and all 35 Material tests passing. No fresh staging or packaged gate was run for these prerequisites. Reconcile judgement: this establishes prerequisites only; retain the separate deletion criterion and its packaging gates as open [rec: fair-cabin-5280].

## Negative knowledge

- [scope: audited Phase 8 deletion boundary at d031bde0 | confidence: high | evidence: wise-isle-1725] Historical blocker, resolved by sharp-pond-0087 and fair-cabin-5280; at the audit, BUILD_GUI=OFF alone did not establish deletion readiness: twelve headless Material sources and six retained tests include Gui/MetaTypes.h; release Ninja records the header as an active valid dependency. Debug configure then succeeded with BUILD_GUI=ON.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- wise-isle-1725 — ADR-213: dependency audit and exact deletion boundary/gates; active metatype and debug GUI prerequisites keep criterion open
- sharp-pond-0087 — preserved metatypes and migrated retained includes; release dependency/build/Material evidence
- fair-cabin-5280 — completed GUI disable, verified rejection and baseline gates; deletion and packaged verification remain open
