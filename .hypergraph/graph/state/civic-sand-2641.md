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

**Dependency audit complete, deletion still open (ADR-213):** `docs/PHASE8-AUDIT.md` identifies historical disable commit `d2c8bcc5` and the remaining metatype/debug-disable prerequisites. Preserve the App/QtCore metatype contract before completing disable and performing the separate directory deletion. The coherent boundary is thirteen trees, 3,731 tracked files / 137,324,776 bytes; `src/Gui` alone is 1,960 files / 65,331,470 bytes. Residual registrations, identity tests, Doxygen paths, Main GUI-only targets and InventorBuilder need explicit treatment. Audit verification was debug configure, 26 packaged lifecycle/licensing tests and two cadex ctests; full build, staging and full inherited ctest comparison remain later deletion gates [rec: wise-isle-1725].

## Negative knowledge

- [scope: audited Phase 8 deletion boundary at d031bde0 | confidence: high | evidence: wise-isle-1725] BUILD_GUI=OFF alone does not establish deletion readiness: twelve headless Material sources and six retained tests include Gui/MetaTypes.h; release Ninja records the header as an active valid dependency. Debug configure still succeeds with BUILD_GUI=ON.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- wise-isle-1725 — ADR-213: dependency audit and exact deletion boundary/gates; active metatype and debug GUI prerequisites keep criterion open
