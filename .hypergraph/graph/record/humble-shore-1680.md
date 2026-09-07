---
node_id: 786668f4-5a7a-54a1-b40a-5d98a7814b73
slug: humble-shore-1680
title: Audit residual GUI installs and preserve headless Assembly consumers
created_at: '2026-09-06T23:41:35+00:00'
parents:
- terse-ridge-1619
summary: ''
---
## What

Audited residual GUI sources and unconditional install lists after the thirteen-directory deletion. Updated PHASE8-AUDIT.md, FREECAD ledger, ADR-215 and only ROADMAP's bounded residual-audit checkbox. No source, build rule, manifest or runtime change.

## Why

Mission 3, civic-sand-2641 and round-glacier-2865; follows terse-ridge-1619 and the overseer's explicit short-item-2 dispatch. Preserve headless Assembly publication and choose the smallest reversible next boundary rather than interpreting a GUI filename as dead code. Assumption: the existing product contract, not arbitrary third-party FreeCAD workbench imports, bounds this audit. Broad no-GUI-source and fork-delta claims remain open.

## Method

Read actor/record skills, STATE, PLAN, graph protocol, VISION and deletion evidence. Trace CMake script/target/copy/install consumers, FreeCADInit startup contract, worker/publisher imports, generated release install lists and current payload presence at deletion HEAD 9f7c3268. Tracked searches for MassPropertiesGui, MaterialEditor, TestMaterialsGui, Help imports, retired resource template and CADEX_GUI_LAUNCHER establish the named consumers. PHASE8-AUDIT.md records source paths and reproducible probes. Run the existing packaged baseline with CADEX_ENGINE_ROOT pointing to the preceding deletion's stage: pixi run python -m pytest -q src/Mod/cadex/cadex_tests/test_licensing_compliance.py src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py. Log is local /tmp/cadex-residual-gates.log; durable result below and in the audit. Run git diff --check and hypergraph export/check before committing.

## Result

26 packaged lifecycle/licensing tests passed in 14.43 s, including the committed-HEAD manifest comparison deferred by the deletion record. Required Assembly CommandCreateView/JointObject/Preferences/UtilsAssembly remain used by headless publication/solving. Material GUI scripts, MeshPart InitGui and Measure MassPropertiesGui still exist in the stage with active generated install rules. Help/Start/Test are absent from the payload but retain build/install consumers. Main retains an unused GUI resource template and four inactive GUI-launcher branches inside the still-required Windows CLI launcher. Other Part/PartDesign mixed helpers and resources remain separate audit/removal obligations.

Next: separately disable MassPropertiesGui.py in Measure_Scripts (one shared target/copy/install list), verify the prescribed build/install/stage gates with stale-file cleanup, then delete the shim in a later verified commit. Its sole executable statement imports deleted MeasureGui; its only retained code reference is the Measure App view-provider-name string, preserved by this narrow sequence. Do not delete the Measure App class or rewrite Assembly publication. Other GUI clusters need their own disposition. No build, configure, installation/staging, full engine suite, inherited ctest, shell edit, GUI launch or training in this docs-only unit. Static searches do not prove absence of arbitrary dynamic/external imports; Windows behavior is unexercised. The gate rerun reuses the preceding staged payload and is not a new build claim.

The run-start manifest metrics are unchanged; broad fork-delta and no-GUI-source exit remain open. This adds the third unreconciled record after the checkpoint; a separate maintainer should reconcile, never this work dispatch. No STATE, PLAN, state-node or .ouroboros edits.

Dispatch closed: 1 unit — audit residual GUI consumers and size the separate Measure shim disable/delete sequence.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 9f7c32685dbc3d364661a0dd0cd3a398e69fe648

## State Impact

- target: civic-sand-2641 — Post-deletion packaged lifecycle/licensing now passes 26 tests including committed-HEAD manifest equality; directory evidence confirmed, broader no-GUI-source exit remains open.
- target: round-glacier-2865 — Residual install audit identifies required Assembly proxies and installed GUI scripts; smallest separate disable/delete boundary is Measure/MassPropertiesGui.py, preserving the App view-provider identity. ADR-215 records exact consumers and limits.
- target: green-sea-3991 — Documentation-only audit leaves manifest metrics unchanged; broader fork-delta reduction remains open.
