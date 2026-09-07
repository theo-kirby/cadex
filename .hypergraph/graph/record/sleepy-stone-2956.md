---
node_id: 8b16003e-9338-54c5-a4ed-aab241a511aa
slug: sleepy-stone-2956
title: 'Audit Start as the second whole-tree candidate: qualifies for a separate disable'
created_at: '2026-09-07T01:06:51+00:00'
parents:
- steady-dew-8037
summary: ''
---
## What

Audited `src/Mod/Start` (with `tests/src/Mod/Start`) as the second engine-side
whole-tree removal candidate, documentation only, no build: commit `891168cc`
adds `docs/START-AUDIT.md`, ADR-219, the corrected `docs/FREECAD.md` ledger
rows and a `docs/ROADMAP.md` tick. **Verdict: Start qualifies for a separate
disable commit** at the same forced-OFF cache boundary Help used (ADR-217).
The audit names the exact disable, its verification list, and the later delete
boundary. Test is not audited and not assumed removable; Assembly, Measure,
the GSL submodule and retained QtCore are outside the boundary.

## Why

Plan short item 2 (`young-crane-9546`) and the overseer's message, serving
mission 3 and the frontier nodes `windy-pebble-4630` (two engine-side
removals), `round-glacier-2865` (inherited-tree reduction) and
`green-sea-3991` (fork delta). Assumption written here: the payload's
`lib/Start.so` and the GSL follow-on are recorded as findings, not fixed;
the overseer asked for an audit with no build, and widening to the payload
prune or `pixi.toml` would be a second unit.

## Method

Same shape as HELP-AUDIT.md. Tracked `git grep` over the Start token set
(`BUILD_START`, `Mod/Start`, `import Start`, `StartGlobal`, `StartMigrator`,
`Start.so`, `StartWorkbench`, …) outside docs, the graph and the tree itself,
then `shell/` separately; a symbol search for `Start::` and the six model
classes; a `Modules/Start` parameter-group search; source inspection of every
named file; `CheckInterModuleDependencies.cmake`; both `CMakeCache.txt`
files; both `build.ninja` files (211 and 199 Start-token lines) and the
generated install scripts; the existing Help-audit CTest discovery JSON
(1,544 registrations); the shared pixi install and the Help-delete staged
payload, labelled as existing-payload evidence; and the manifest metric plus
D/A/remaining counts against the import commit with the PHASE8-AUDIT method.
Gate for the docs zone: `pixi run test-engine`.

## Result

- Consumers: `BUILD_START` option ON (initializer:166), report line, one
  `src/Mod` gate and two `tests/` gates; the `Start.so` App target links only
  `FreeCADApp` and is linked only by `Start_tests_run`; no tracked source
  outside the two directories names a Start symbol; `Init.py` registers a
  `Start.py` module that does not exist and nothing reads; `InitGui.py` and
  `StartMigrator.py` are orphans since ADR-214; `Branding.cpp`'s
  `"StartWorkbench"` is a key-filter string, retained. `MainCmd`'s
  dependency is on Test (`TestSources`), not Start.
- CTest: 11 passing `FileUtilitiesTest` registrations leave with the disable
  (1,544 → 1,533); none is in the baseline, so it is the expected delta to
  compare by name, not a regression.
- Two doc claims were wrong and are corrected: the staged payload prunes
  `Mod/Start` but **carries `lib/Start.so` (266,296 bytes)** because the
  target installs to `lib/`; and Start is the **only** consumer of
  `src/3rdParty/GSL` (`pixi.toml:260` still checks it out), a separate
  follow-on after the delete.
- Stale to quarantine at the disable: shared-install `Mod/Start/{InitGui.py,
  StartMigrator.py,__pycache__}` from 2026-07-24 and `lib/Start.so`;
  `build/release/Mod/Start`, `tests/Start_tests_run` and its discovery files.
- Fork-delta counting, as the overseer asked: whole-tree deletions should be
  credited only against inherited files remaining (12,749 at import, 7,287
  at run start, 3,468 now), never against the manifest M metric, which is
  the surviving conflict surface and went 47 / 1,804 / 1,907 → 57 / 1,637 /
  1,803 (fewer lines, more files). Both numbers should be reported each time.
  Start's delete would take M to 56 files and remaining to 3,441. Proposal
  only; no criterion text or test changed.
- Gate: `pixi run test-engine` on the audit commit's tree: **2,022 passed,
  52 skipped in 252.2 s**, exit 0 (`/tmp/cadex-start-audit-gate.log`),
  manifest untouched. No build, configure, install, stage, CTest or packaged
  gate was run; the disable's gates are all future. macOS only.
- The unreconciled tail is now three nodes (`warm-anchor-2441`,
  `steady-dew-8037`, this one); a maintainer pass is due before the next
  work unit per the charter's reconcile rule.

Dispatch closed: 1 unit — Start audited and qualified for a separate forced-OFF disable (ADR-219, docs/START-AUDIT.md); payload still ships lib/Start.so; fork-delta counting convention recorded.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 891168cc665b26c87c29d4bba09540b9cfbfc985

## State Impact

- target: windy-pebble-4630 — Start is audited and qualifies for a separate forced-OFF disable (ADR-219, docs/START-AUDIT.md); the second engine-side removal now has a named disable boundary and gate list, Test remains unaudited
- target: round-glacier-2865 — Start audit landed documentation-only: Start.so is linked only by its own gtest, 11 passing FileUtilitiesTest registrations leave with the disable, the payload still ships lib/Start.so, and Start is the sole GSL-submodule consumer (follow-on)
- target: green-sea-3991 — Counting convention recorded: credit whole-tree deletions only against inherited files remaining (7,287 at run start → 3,468), never against the manifest M metric (47/1,804/1,907 → 57/1,637/1,803); both numbers to be reported each time
