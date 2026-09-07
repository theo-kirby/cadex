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

**One fully evidenced removal; the second awaits one recorded check.** Help is complete. Start's separate disable and deletion have baseline-matched runtime gates, but the deletion record reserves the post-commit HEAD manifest check. The Measure shim does not count as a tree removal [rec: silver-beacon-0723] [rec: steady-dew-8037] [rec: southern-wood-6367] [rec: rustic-spire-7084].

**First removal complete: `src/Mod/Help` (ADR-216 audit, ADR-217 disable, ADR-218 delete)** [rec: steady-dew-8037].

- *Audit (ADR-216, `docs/HELP-AUDIT.md`)*: 85 tracked files / 802,267 bytes, no App target, no `Init.py`, no Help-specific CTest consumer among 1,544 registrations, no tracked product importer; `BUILD_HELP` was ON in both caches independently of `BUILD_GUI=OFF` [rec: silver-beacon-0723].
- *Disable (ADR-217, `a04ca822`)*: landed without a record node and ahead of its gates; the follow-up ran them and rewrote the docs to say only what ran. Explicit `-DBUILD_HELP=ON` collapsed to OFF in both caches, release build exit 0, no `Mod/Help` in install or payload, engine suite 2,022 passed, Cadex ctests 4/4, inherited CTest zero names outside the baseline, packaged gate 26 passed [rec: zesty-otter-9342].
- *Delete (ADR-218, `b24761b4`)*: `src/Mod/Help` (85 files, 8,480 lines), the `if(BUILD_HELP)` gate, the forced-OFF cache entry, the report line, the Crowdin row in `src/Tools/updatecrowdin.py`, and the two developer-configuration path entries, with ledger row, ROADMAP tick, HELP-AUDIT §"Delete landed" and the manifest entry in the same commit. Gates run in the same unit: both caches with explicit ON then `cmake -U BUILD_HELP` (0 `Mod/Help` rules, no cache entry), release build 37 incremental steps, install and stage exit 0, installed `FreeCADCmd` probe from a script file (`import Help` fails, nine retained modules import, box volume 1000), engine suite 2,021 passed / 52 skipped pre-commit with only the HEAD-bound manifest test failing and passing after the commit, Cadex ctests 4/4, serial CTest 162 failed of 1,537 with 0 names outside the baseline, packaged gate 26 passed after the commit [rec: steady-dew-8037].
- *Not run for either half*: fresh-cache configure, from-scratch build, Linux/Windows. Static search cannot rule out external or dynamic imports [rec: silver-beacon-0723] [rec: steady-dew-8037].

**Start disable and deletion recorded (ADR-219/220/221).** The separate disable forced `BUILD_START=OFF` in both existing caches and explicit ON requests, retained all 27 sources, and removed installed/staged `Mod/Start` and `lib/Start.so`; stable-stage engine tests passed 2,022 / 52 skipped and packaged lifecycle/licensing passed 26 [rec: southern-wood-6367]. The subsequent deletion removed 23 module and four test files, three gates, the option/report line, Crowdin row and two developer-config exclusions. Both existing-cache configurations, release build, install and stage passed; Test still installs, eleven retained imports and the native box probe pass. Engine tests: 2,021 passed / 52 skipped / one committed-HEAD manifest test deselected; packaged lifecycle/licensing: 25 passed / that same check deselected. Cadex CTests: 4/4; inherited CTest: 162 failures of 1,526, no names outside the 164-name baseline, 3 skipped and 7 disabled. Registration count remains 1,533 after the disable removed exactly eleven passing Start tests. The post-commit HEAD manifest result is not supplied in this record [rec: rustic-spire-7084]. Fresh-cache/from-scratch builds, other platforms and GUI were not exercised; the local 2.4 GB stage retains external library references [rec: rustic-spire-7084].

Test is not audited or assumed removable; GSL is a separate follow-on [rec: rustic-spire-7084].

Reconcile judgement: keep the criterion **open solely for the reserved post-commit HEAD manifest evidence**. Help plus Start meet the two-tree scope, but the record makes completion conditional; do not infer that the reserved check passed [rec: rustic-spire-7084].

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

- southern-wood-6367 — ADR-220: verified Start disable, stable-stage gates and corrected inherited-file counts
- rustic-spire-7084 — ADR-221: Start deletion, baseline-matched runtime gates and updated metrics; post-commit HEAD manifest check reserved
