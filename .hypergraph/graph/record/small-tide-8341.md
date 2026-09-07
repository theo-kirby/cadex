---
node_id: 2f386b38-cb0a-5c24-9729-120d00fc3655
slug: small-tide-8341
title: Delete the disabled Measure GUI shim
created_at: '2026-09-07T00:03:04+00:00'
parents:
- placid-harvest-8845
summary: ''
---
## What

Delete only src/Mod/Measure/MassPropertiesGui.py after its separate disable
commit 68b4bbf4: one inherited file, 22 lines, 1,477 bytes. Update ADR-215,
FREECAD ledger, PHASE8-AUDIT verification and the bounded ROADMAP checkbox.
Measure App, the view-provider identity, four other Measure scripts and
required Assembly publishers remain unchanged.

## Why

Execute short item 2 and the overseer's explicit dispatch, following
placid-harvest-8845, serving mission 3 and round-glacier-2865. The prior disable
has a postcommit 26-test packaged pass. This unused shim only imports deleted
MeasureGui. Assumption: preserve the audited App identity rather than widening
the cleanup. No whole-tree removal or broad GUI-source closure follows.

## Method

Tracked consumer closure and generated debug/release consumer checks; one
release build after both configurations; full engine pytest; both cadex ctests;
serial full inherited CTest and before/after JSON discovery; compare failure
names against build/ctest_baseline_failures.txt and skips/disabled against the
prior disable log. Inspect Ninja dependencies. Install release, complete staging,
then run fresh packaged lifecycle/licensing and native installed Measure probe.
Detailed commands and results are in docs/PHASE8-AUDIT.md. Local logs and
inventories use /tmp/cadex-measure-delete-*; they are not committed.
Working-tree import-relative manifest equality checked for both forks. The
shim was never manifested, so no JSON or modification-notice edits are needed.
Precommit HEAD checks cannot see the deletion; rerun packaged checks after commit.

## Result

Both configurations and the single release build exit 0; Debug/OFF and
Release/OFF. Engine suite: 2022 passed, 52 skipped, 259.65 s. Cadex ctests:
2/2 pass, 16.78 s (digest 1.67 s; lifecycle 15.09 s). Inherited CTest: exit 8,
162 failures / 1537 enabled tests in 130.52 s, no new failure names against
164-failure baseline. DlgVersionMigrator_Tests_run and
SpreadsheetRenameProperty.renameProperty remain baseline-only and absent.
Identical 1544 registrations, commands and properties, no duplicates; three
skips/seven disabled unchanged. Zero deleted GUI compiler dependencies;
190 retained App/MetaTypes.h references.

Install and completed stage exit 0; fresh packaged lifecycle/licensing:
26 passed, 19.44 s. No stale shim/bytecode in release/install/stage; no quarantine
needed. Four Measure scripts/four required Assembly modules remain. Native
installed probe imports Measure/MassProperties, creates Measure::Result with
GuiUp false and prints MEASURE-APP-OK. Local 2.4 GB stage-only payload has expected
external rpath diagnostics and is not a relocated distribution.

Manifest-scoped FreeCAD M totals stay 56/1633 inserted/1796 deleted, against
nt2 start 7dd3d045 47/1804/1907; Blender stays 44/1046/129. Deleted file volume
is separate. Two engine-tree-removals and broad fork-delta gaps remain open,
as do other residual GUI-source obligations. No shell edits, GUI, remote work,
second build, state/charter/plan edits or reconciliation. Hypergraph export/check
must pass before commit; postcommit packaged comparison is the final check.
Next: three unreconciled records now trigger the separate maintainer and planner
passes before further work; this contributor must not reconcile.
Dispatch closed: 1 unit — delete the disabled Measure GUI shim.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 68b4bbf43fc3efabcbc2aaa4f8ecc707dc64fc29

## State Impact

- target: round-glacier-2865 — Deleted the separately disabled Measure GUI shim; Measure App identity and Assembly publishers preserved. Build, engine and fresh packaged gates pass; inherited failures unchanged. Broader GUI-source and whole-tree removal obligations remain open.
