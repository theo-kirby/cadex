---
node_id: e24000ee-ec73-57be-a141-696a2185e4fe
slug: wild-beacon-4213
title: Verify the involute gear and rack slice on the fresh payload and close its record
created_at: '2026-09-07T05:43:27+00:00'
parents:
- placid-delta-6677
summary: ''
---
## What

Completed the verification of the involute spur gear and rack library slice (ADR-233) that landed in `0f0e3e17` without gates or a record. Ran the full engine suite, one `pixi run build-engine`, `pixi run stage-engine` to completion, and the fresh packaged lifecycle/library gate against the staged payload; replaced the ENGINE_RESULT / PACKAGED_RESULT placeholders in `docs/DECISIONS.md` (ADR-233) and `docs/L3-COVERAGE.md` with the real numbers and an explicit list of what was not verified. No code changed.

## Why

The critic rejected iteration 64: rank 1 of the short plan (`placid-delta-6677`, involute gearing toward `idle-tower-1624` and `brave-stone-9609`) had its code committed but its docs held placeholders instead of results, and no record node was minted. The overseer ordered a fix-forward commit and the missing record before rank 2 (rack and pinion) may start. Assumption: the commit `0f0e3e17` is not amended or reverted; this unit adds one new commit on top of it, per the run's fix-forward rule.

## Method

1. `pixi run python -m pytest src/Mod/cadex/cadex_tests` on the source tree before any build.
2. `pixi run build-engine` (one build), then `pixi run stage-engine` run to completion, sequentially, not overlapping.
3. `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_library.py`, after confirming the staged `cadex_library_api.py` carries `spur_gear`.
4. Wrote the results into ADR-233 and the L3-COVERAGE verification ledger, then minted this record and exported the graph before the single commit.

## Result

Full engine suite (pre-build): 2050 passed, 52 skipped, 260.41 s, exit 0. `build-engine` exit 0. `stage-engine` exit 0, 2.4 GB payload, only the pre-existing LC_RPATH warnings. Fresh packaged lifecycle/library gate: 107 passed, no skips, 25.79 s (was 90 at the joint delivery; the gear tests and the publication rows account for the growth). Not verified: `pixi run gate` (no `shell/` line changed) and ctest (no C++ changed). The involute gear and rack values are now standalone library values with real-kernel and packaged evidence; rack-and-pinion and planetary composition (mesh and clearance tests) remain the open half of the compound-mechanisms criterion. The unreconciled tail is now three nodes (the bet, this record, and 0f0e3e17's silent commit has none); a maintainer pass is due.

Dispatch closed: 1 unit — gear slice verified on the real kernel and the fresh payload, placeholders replaced, record minted.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 0f0e3e17f7fb752d2a2258333fdbc56654a3de1b

## State Impact

- target: idle-tower-1624 — Involute spur gear and rack exist as library values (ADR-233) with full-suite, real-kernel and fresh packaged evidence (2050/52, 107/0); rack-and-pinion and planetary composition with mesh and clearance tests remain open
- target: brave-stone-9609 — A gears family (lib.spur_gear, lib.rack over CadexCatalog.gear_spec, ISO 53/ISO 54) is verified on the staged payload; standalone values only, no strength or torque rating
