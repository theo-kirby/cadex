---
node_id: c8263c6f-b32b-51f0-9d7f-1675e675da21
slug: silver-beacon-0723
title: Audit Help for a separate whole-tree disable
created_at: '2026-09-07T00:11:57+00:00'
parents:
- quiet-canyon-3950
summary: ''
---
## What

Audit src/Mod/Help as the next whole-tree Phase 13b candidate. Add
HELP-AUDIT.md with exact tracked and generated consumers, existing cache and
installed-file inventory, separate disable/delete boundaries and future gates.
Record ADR-216, update the FREECAD ledger and tick only the bounded ROADMAP
audit item. No runtime, source, CMake, manifest or payload changes.

## Why

Iteration 27 executes short item 1 following quiet-canyon-3950, serving mission
3 and windy-pebble-4630/round-glacier-2865. Help qualifies for separate disable:
no tracked product importer or required native App target. Assumption: Cadex's
product contract bounds removal, not arbitrary third-party FreeCAD imports;
Help.show's unused console API is retired along with its GUI plumbing. The
work-iteration prohibition on reconciliation takes precedence over the stale
overseer request; the preceding maintainer/planner commits already exist.
Do not redispatch Measure or infer that two shim commits are two tree removals.

## Method

Read actor and record skills, STATE/PLAN, graph contract, VISION and preceding
Measure evidence. Search tracked BUILD_HELP, Help import/resource/path and
packaging consumers; read Help scripts/CMake, module startup, copy macro,
translation updater, presets and package allowlist. Inspect Debug/Release
cache, Ninja and install rules, copied/installed/staged files. Count tracked
Help files and bytes. Run release CTest JSON discovery and existing-payload
lifecycle/licensing gate, recalculate import-relative manifest-scoped numstat
at nt2 start and HEAD. Commands, durable results and limits are in
HELP-AUDIT.md; local logs are /tmp/cadex-help-audit-gates.log and
/tmp/cadex-help-audit-ctest.json. Run git diff --check and hypergraph
export/check before commit.

## Result

Help qualifies, still enabled today: both caches have BUILD_HELP ON and
BUILD_GUI OFF; four sources copy/install unconditionally. The shared install
also carries stale Help_rc.py and two bytecode files. There are 85 tracked
files / 802,267 bytes, no App target, no Init.py and no Help-specific CTest
consumer among 1,544 registrations. The Crowdin updater is an external source
resource writer and must lose its Help row at later deletion; two developer
configuration references also need cleanup. Retained Qt, required Assembly
publishers, Measure App and attribution stay untouched.

26 existing-payload lifecycle/licensing tests passed in 14.48 s, including the
preceding deletion's committed-HEAD manifest equality. CTest discovery exits
0; no full engine suite, inherited test execution, build, configure,
install/stage or GUI in this documentation-only audit. This is existing-payload
evidence, not verification of a disable that has not happened. Static search
cannot rule out external/dynamic imports; Windows/Linux are unexercised.

FreeCAD modified-file metrics remain 56 files / 1,633 inserted / 1,796 deleted,
versus nt2 start 7dd3d045 at 47 / 1,804 / 1,907. Blender stays 44 / 1,046 / 129.
Whole deleted source volume is separate. Broad fork delta, residual GUI-source
closure and two whole-tree removals remain open. Start/Test are not qualified.

Next: separate disable commit normalizing BUILD_HELP OFF with CACHE BOOL FORCE,
retaining source/parent gate/report; verify stale and explicit ON requests,
quarantine stale copies/resources/bytecode, run one release build and the
specified full engine/CTest/install/stage/packaged gates before promotion to a
later deletion. No plan/state/charter edits or reconciliation in this unit.
Dispatch closed: 1 unit — qualify Help for a separately verified whole-tree disable.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 0e1497b1edf029ad6fb75f298fcdbff168c23f6d

## State Impact

- target: round-glacier-2865 — Help qualifies for a separate durable disable; audit identifies ON caches, four install/copy sources, stale resource/bytecode and the external translation writer. Preserve required App/Assembly and Qt; no code removed.
- target: windy-pebble-4630 — First whole-tree candidate Help audited and qualified, still enabled; separate disable and later delete gates remain. Start/Test unqualified; Measure shim sequence is not two tree removals.
- target: green-sea-3991 — Existing-payload committed manifest gate passes 26 tests; import-relative totals remain FreeCAD 56/1633/1796 and Blender 44/1046/129. Broad fork-delta reduction stays open.
