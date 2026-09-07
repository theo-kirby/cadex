---
node_id: 36e843ef-738a-5e57-9278-f61a51f98e90
slug: zesty-otter-9342
title: Run and record the Help disable gates
created_at: '2026-09-07T00:34:50+00:00'
parents:
- silver-beacon-0723
summary: ''
---
## What

Ran the gates that the Help disable (`a04ca822`, ADR-217 in `504b46bc`) had claimed but never executed, and rewrote ADR-217's evidence paragraph, the ROADMAP line and a new `docs/HELP-AUDIT.md` §"Disable landed" so the three say only what actually ran. No build rule or source changed in this unit.

## Why

The overseer's message: three iterations without a record node, and the ADR cited a HELP-AUDIT section that did not exist. Targets: `windy-pebble-4630` (two Phase 13b engine-side removals) and `round-glacier-2865` (inherited-tree reduction). Plan item short-2 required this verification before any delete commit. Assumption written here rather than asked: the stale Help copies, install and bytecode the audit listed were already absent when this unit began, so no quarantine was performed and the doc says which unrecorded unit did it is unknown.

## Method

Explicit `-DBUILD_HELP=ON` reconfigure over the existing Release and Debug caches; `pixi run build-release`; `install-release`; `stage-engine`; an installed `FreeCADCmd` import probe; `pixi run test-engine`; `ctest -R '^Cadex'`; serial `ctest -j 1` diffed by name against `build/ctest_baseline_failures.txt`; the packaged lifecycle/licensing gate with `CADEX_ENGINE_ROOT` at the fresh payload; manifest-scoped M metrics recomputed with the PHASE8-AUDIT recipe. Then edited the three docs and re-ran the licensing test.

## Result

Both caches OFF under explicit ON, 0 `Mod/Help` Ninja rules, no install include, report OFF. Release build exit 0 (690 steps). No `Mod/Help` in the shared install or the payload. Probe: `import Help` fails, all nine retained modules import. Engine suite 2,022 passed / 52 skipped. Cadex ctests 4/4. Inherited CTest 162 failed of 1,537 run, zero failures outside the baseline by name; two baseline names are ADR-214 deleted binaries. Packaged gate 26 passed. FreeCAD M metrics 56 / 1,638 / 1,797 (nt2 start 47 / 1,804 / 1,907), Blender unchanged 44 / 1,046 / 129. Not run: fresh-cache configure, non-macOS. Tail is 3 nodes with this one; a maintainer pass is due. The Help delete commit is now unblocked as a separate unit.

Dispatch closed: 1 unit — Help disable gates run and recorded; ADR-217, ROADMAP and HELP-AUDIT now state only what ran.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 504b46bc870aaa8686f0819e00aa8e42f9cab2c9

## State Impact

- target: windy-pebble-4630 — Help's disable commit (ADR-217) is now gate-verified: explicit-ON caches collapse to OFF, release build/install/stage carry no Mod/Help, engine suite 2022 passed, inherited CTest at baseline, packaged gate 26 passed; the separate delete commit is unblocked and no removal is complete until it lands
- target: round-glacier-2865 — the Help whole-tree disable has real evidence in docs/HELP-AUDIT.md §Disable landed; two prior units landed code and ADR without records or gates, and the docs now say so; quarantine state of stale Help artifacts was found already absent
