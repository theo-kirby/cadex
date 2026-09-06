---
node_id: a63961e0-0391-55e2-ab72-0dc7c815b797
slug: placid-harvest-8845
title: Disable the audited Measure GUI shim install
created_at: '2026-09-06T23:53:02+00:00'
parents:
- solar-cove-9793
summary: ''
---
## What

Disable the audited Measure GUI shim's copy/install consumers by removing only
MassPropertiesGui.py from Measure_Scripts. Keep the source for the later delete
commit and retain all four other scripts, the Measure App class/view-provider
identity and required headless Assembly modules. Update ADR-215, FREECAD ledger,
PHASE8-AUDIT evidence and the bounded ROADMAP checkbox.

## Why

Follows solar-cove-9793's short bet and the residual audit, serving mission 3 and
round-glacier-2865. The shim imports the deleted MeasureGui and has no retained
Python importer. The shared list is the smallest reversible disable boundary.
The overseer requested reconciliation before work; the supplied STATE/PLAN
already carry the maintainer/planner result, and this dispatch expressly forbids
reconciliation. Assumption: execute the selected disable bet without editing
state, plan or charter. This is not a whole-tree removal or a broad GUI closure.

## Method

One inherited CMake-line removal; existing modification notice and manifest
membership already cover the file. Tracked consumer search; compare generated
debug/release build and install rules; compare serial CTest JSON inventories;
inspect compiler dependencies; run both configurations, one release build,
full engine pytest and serial inherited CTest. Quarantine stale shim copies,
install and finish stage before fresh packaged lifecycle/licensing tests.
Commands and measured evidence are in docs/PHASE8-AUDIT.md's final section.
Local logs and inventory/quarantine JSON use /tmp/cadex-measure-* and are not
committed. Baseline failure names are read from build/ctest_baseline_failures.txt
without rewriting it. Import-to-working-tree manifest equality verified for both
forks; import-to-HEAD checks cannot inspect an uncommitted CMake line, although
membership does not change. Rerun packaged comparison after commit.

## Result

Both configurations, one release build, install and completed stage exit 0.
Full engine suite: 2022 passed, 52 skipped, 273.31 s. CTest inventory/properties:
1544 identical registrations, no duplicates. Inherited run: 162 failures of
1537 enabled tests, exit 8, 140.29 s; no new names against the 164 baseline.
Baseline-only DlgVersionMigrator_Tests_run and SpreadsheetRenameProperty.renameProperty
remain absent; three skips/seven disabled unchanged. All four Cadex tests pass,
including rebuild digest (2.24 s) and lifecycle (15.71 s). Initial lowercase
-R cadex selected no tests; the subsequent full run is the evidence.
Fresh packaged lifecycle/licensing: 26 passed, 17.46 s. Three stale shim files
quarantined; no shim in generated consumers, installed directory or fresh stage.
Four Measure/four required Assembly scripts present; zero deleted GUI compiler
dependencies and 190 retained App/MetaTypes.h references. Installed native probe
imports Measure/MassProperties and creates Measure::Result headlessly. The staged
probe also completes but emits a startup No module named freecad diagnostic;
this is not a diagnostic-free standalone-launch claim. An earlier one-line
installed probe terminated; explicit script execution passes. No repair of
unrelated startup behavior attempted. Stage is local 2.4 GB with expected external
rpaths, not a relocated distribution.

No deleted source volume. FreeCAD manifest-scoped M totals versus nt2 7dd3d045:
56 files/1633 inserted/1796 deleted versus 47/1804/1907; Blender stays 44/1046/129.
Manifest membership and existing notices remain honest without a JSON edit.
Next: delete only the now-disabled shim in a separate verified unit; preserve
App identity and Assembly consumers. Broad GUI-source, two engine-tree removals
and fork-delta criteria remain open. No GUI, remote training, provisioning,
state-node or charter edits. Hypergraph export/check required before commit;
postcommit packaged recheck is the final validation, with no second build.
Dispatch closed: 1 unit — disable the audited Measure GUI shim install.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 74f26479893facf8301d9b042e4307922cc19d2c

## State Impact

- target: round-glacier-2865 — Measure GUI shim disabled in shared copy/install list with source retained; build, engine and fresh packaged gates pass, inherited failures unchanged. Separate source deletion is next; broader GUI-source obligations remain open.
