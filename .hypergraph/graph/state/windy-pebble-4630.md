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

**What has landed does not yet count.** The Measure GUI shim disable/delete sequence (ADR-215) removed one file under the protocol; it is a shim removal, not a whole-tree removal, and does not satisfy this criterion [rec: silver-beacon-0723].

**First whole-tree candidate: `src/Mod/Help`, audited and disabled; delete still owed** [rec: silver-beacon-0723] [rec: zesty-otter-9342].

- *Audit (ADR-216, `docs/HELP-AUDIT.md`)*: Help qualifies for a separate disable. 85 tracked files / 802,267 bytes, no App target, no `Init.py`, no Help-specific CTest consumer among 1,544 registrations, no tracked product importer. `BUILD_HELP` was ON in both caches independently of `BUILD_GUI=OFF`; four sources copied/installed it unconditionally. Its later deletion must also drop the Help row from the Crowdin translation updater and clean two developer-configuration references [rec: silver-beacon-0723].
- *Disable (ADR-217, `a04ca822`)*: landed with no record node and with gates it claimed but had not run; the follow-up unit ran them and rewrote ADR-217, the ROADMAP line and HELP-AUDIT §"Disable landed" to say only what ran [rec: zesty-otter-9342].
- *Disable evidence*: explicit `-DBUILD_HELP=ON` reconfigure over both caches collapses to OFF; 0 `Mod/Help` Ninja rules, no install include; release build exit 0 (690 steps); no `Mod/Help` in the shared install or the staged payload; installed `FreeCADCmd` fails `import Help` while all nine retained modules import; engine suite 2,022 passed / 52 skipped; Cadex ctests 4/4; inherited CTest 162 failed of 1,537 with zero names outside the baseline; packaged lifecycle/licensing gate 26 passed [rec: zesty-otter-9342].
- *Not run*: fresh-cache configure and non-macOS platforms. Static search cannot rule out external or dynamic imports [rec: silver-beacon-0723] [rec: zesty-otter-9342].

The Help delete commit is unblocked as a separate unit. No engine-side whole-tree removal is complete until it lands, and a second candidate is still unqualified: Start has an App target and Test is a MainCmd dependency [rec: silver-beacon-0723] [rec: zesty-otter-9342].

## Negative knowledge

- [scope: counting removals toward this criterion | confidence: high | evidence: silver-beacon-0723] Two shim commits are not two tree removals. The Measure sequence was one file; only a whole-tree disable plus delete pair counts.
- [scope: Help disable at a04ca822 | confidence: high | evidence: zesty-otter-9342] A removal commit can land with an ADR that cites evidence and a doc section that did not exist. Run the gates before the ADR claims them; the docs now state only what ran.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- silver-beacon-0723 — ADR-216: Help audited and qualified for a separate whole-tree disable; Start/Test unqualified; Measure shim is not a tree removal
- zesty-otter-9342 — ADR-217 gate-verified after the fact: Help disable evidence, delete commit unblocked, docs corrected to what ran
