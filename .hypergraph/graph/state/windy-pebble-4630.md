---
node_id: 6a68450d-50fe-5c87-935b-72165483505f
slug: windy-pebble-4630
title: Two Phase 13b engine-side removals landed
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion: **Two Phase 13b engine-side removals landed** under the two-commit protocol, DECISIONS entries included. [rec: empty-wolf-3962]

Declared target: `gap-two-phase-13b-engine-side`. This node tracks the criterion as a gap; it becomes working only with evidence that the criterion is met. Truncated impact wording is resolved from the full charter in the same record [rec: empty-wolf-3962].

**Score: one of two.** The Measure GUI shim sequence (ADR-215) was one file and does not count [rec: silver-beacon-0723]. Help is the first complete engine-side whole-tree removal; Start is audited and qualified as the second candidate, with its disable and delete still owed [rec: steady-dew-8037] [rec: sleepy-stone-2956].

**First removal complete: `src/Mod/Help` (ADR-216 audit, ADR-217 disable, ADR-218 delete)** [rec: steady-dew-8037].

- *Audit (ADR-216, `docs/HELP-AUDIT.md`)*: 85 tracked files / 802,267 bytes, no App target, no `Init.py`, no Help-specific CTest consumer among 1,544 registrations, no tracked product importer; `BUILD_HELP` was ON in both caches independently of `BUILD_GUI=OFF` [rec: silver-beacon-0723].
- *Disable (ADR-217, `a04ca822`)*: landed without a record node and ahead of its gates; the follow-up ran them and rewrote the docs to say only what ran. Explicit `-DBUILD_HELP=ON` collapsed to OFF in both caches, release build exit 0, no `Mod/Help` in install or payload, engine suite 2,022 passed, Cadex ctests 4/4, inherited CTest zero names outside the baseline, packaged gate 26 passed [rec: zesty-otter-9342].
- *Delete (ADR-218, `b24761b4`)*: `src/Mod/Help` (85 files, 8,480 lines), the `if(BUILD_HELP)` gate, the forced-OFF cache entry, the report line, the Crowdin row in `src/Tools/updatecrowdin.py`, and the two developer-configuration path entries, with ledger row, ROADMAP tick, HELP-AUDIT §"Delete landed" and the manifest entry in the same commit. Gates run in the same unit: both caches with explicit ON then `cmake -U BUILD_HELP` (0 `Mod/Help` rules, no cache entry), release build 37 incremental steps, install and stage exit 0, installed `FreeCADCmd` probe from a script file (`import Help` fails, nine retained modules import, box volume 1000), engine suite 2,021 passed / 52 skipped pre-commit with only the HEAD-bound manifest test failing and passing after the commit, Cadex ctests 4/4, serial CTest 162 failed of 1,537 with 0 names outside the baseline, packaged gate 26 passed after the commit [rec: steady-dew-8037].
- *Not run for either half*: fresh-cache configure, from-scratch build, Linux/Windows. Static search cannot rule out external or dynamic imports [rec: silver-beacon-0723] [rec: steady-dew-8037].

**Second candidate: `src/Mod/Start`, audited and qualified for a separate disable (ADR-219, `docs/START-AUDIT.md`, `891168cc`, documentation only, no build)** [rec: sleepy-stone-2956].

- Consumers: `BUILD_START` option ON, a report line, one `src/Mod` gate and two `tests/` gates. The `Start.so` App target links only `FreeCADApp` and is linked only by its own gtest `Start_tests_run`. No tracked source outside the two directories names a Start symbol. `Init.py` registers a `Start.py` module that does not exist; `InitGui.py` and `StartMigrator.py` are orphans since ADR-214. `MainCmd` depends on Test, not Start [rec: sleepy-stone-2956].
- Expected CTest delta at the disable: 11 passing `FileUtilitiesTest` registrations leave (1,544 → 1,533), none in the baseline, so compare by name [rec: sleepy-stone-2956].
- Two corrected doc claims: the staged payload prunes `Mod/Start` but still carries `lib/Start.so` (266,296 bytes); Start is the only consumer of `src/3rdParty/GSL`, which `pixi.toml` still checks out, a separate follow-on after the delete [rec: sleepy-stone-2956].
- Gate for the docs zone: engine suite 2,022 passed / 52 skipped. No build, configure, install, stage, CTest or packaged gate ran; the disable's gates are all future [rec: sleepy-stone-2956].

**Test is not audited and not assumed removable** — it carries headless testing obligations (`MainCmd` depends on `TestSources`) [rec: silver-beacon-0723] [rec: sleepy-stone-2956].

Reconcile judgement: the criterion stays open. One removal is complete and the second has a named disable boundary and gate list; it becomes working only when Start's disable and delete both land with their gates [rec: steady-dew-8037] [rec: sleepy-stone-2956].

## Negative knowledge

- [scope: counting removals toward this criterion | confidence: high | evidence: silver-beacon-0723] Two shim commits are not two tree removals. The Measure sequence was one file; only a whole-tree disable plus delete pair counts.
- [scope: Help disable at a04ca822 | confidence: high | evidence: zesty-otter-9342] A removal commit can land with an ADR that cites evidence and a doc section that did not exist. Run the gates before the ADR claims them; the docs now state only what ran.
- [scope: installed FreeCADCmd probes | confidence: medium | evidence: steady-dew-8037] The `-c` string form of the import probe crashed ("Application unexpectedly terminated"); the script-file form is the one that works.
- [scope: payload evidence for a whole-tree audit | confidence: high | evidence: sleepy-stone-2956] "Pruned from the payload" was wrong for Start: the `Mod/` directory is pruned but the App target installs to `lib/`, so `lib/Start.so` ships. Check `lib/` as well as `Mod/` before claiming a tree is absent from a payload.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- silver-beacon-0723 — ADR-216: Help audited and qualified for a separate whole-tree disable; Start/Test unqualified; Measure shim is not a tree removal
- zesty-otter-9342 — ADR-217 gate-verified after the fact: Help disable evidence, delete commit unblocked, docs corrected to what ran
- steady-dew-8037 — ADR-218: Help deleted at the audited boundary with the full gate set green against the baseline; first whole-tree removal complete
- sleepy-stone-2956 — ADR-219: Start audited and qualified for a separate forced-OFF disable; payload still ships lib/Start.so; Test unaudited
