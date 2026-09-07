---
node_id: 6a68450d-50fe-5c87-935b-72165483505f
slug: windy-pebble-4630
title: Two Phase 13b engine-side removals landed
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

**Two Phase 13b engine-side whole-tree removals are complete:** Help and Start each have separate disable/delete commits, ADRs and recorded verification. This satisfies the charter criterion declared as `gap-two-phase-13b-engine-side` [rec: empty-wolf-3962] [rec: late-pond-3758].

**Help (ADR-216/217/218):** audited at 85 tracked files, disabled separately, then deleted with its build/configuration references. Disable verification was supplied by a corrective follow-up after the commit [rec: silver-beacon-0723] [rec: zesty-otter-9342]. Delete configure/build/install/stage, retained-module/native-box probes and four Cadex CTests passed; inherited CTest had no failure names outside baseline. The committed-HEAD manifest check and 26 packaged tests passed after commit [rec: steady-dew-8037].

**Start (ADR-219/220/221):** separately disabled with 2,022 engine tests / 52 skips and 26 packaged tests passing, then deleted (23 module and four test files plus build/configuration references) [rec: southern-wood-6367] [rec: rustic-spire-7084]. Delete configure/build/install/stage, retained imports/native box and four Cadex CTests passed; inherited CTest had no new failure names. The delete suites reserved only committed-HEAD manifest verification: 2,021 engine tests / 52 skips and 25 packaged tests passed with that check deselected [rec: rustic-spire-7084]. The later committed-tree licensing run passed 10 tests / one payload-only skip, including `test_the_manifest_matches_git_reality`, resolving the last condition [rec: late-pond-3758].

Reconcile judgement: move to **working** because the explicitly reserved evidence now exists. GSL is subsequent dependency cleanup, not a third module; the Measure shim does not count as a whole tree. This closes neither standing inherited reduction nor the broad fork-delta criterion [rec: late-pond-3758] [rec: silver-beacon-0723]. Fresh-cache/from-scratch builds and Linux/Windows remain unverified; local stage gates establish local behavior, not a relocated distribution [rec: steady-dew-8037] [rec: rustic-spire-7084].

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
- late-pond-3758 — reserved Start manifest check passed; Help plus Start satisfy the two-tree criterion
