---
node_id: 499efdc4-ec11-5d88-9c1e-9b347384ce38
slug: rustic-spire-7084
title: Delete Start after its verified disable; second engine whole-tree removal
created_at: '2026-09-07T01:35:20+00:00'
parents:
- southern-wood-6367
summary: ''
---
## What

Deleted Start after the separate verified disable commit 449b8e09 (ADR-220):
23 module files, four test files, three gates, option/report line, crowdin
row and two developer-config exclusions. ADR-221, FREECAD ledger, ROADMAP
checkbox and START-AUDIT verification document the boundary. All six
surviving inherited files retain current modification notices; the deleted
Start CMake file leaves the manifest.

## Why

One unit from short item 2, following southern-wood-6367, serving mission 3
and windy-pebble-4630, round-glacier-2865 and green-sea-3991. The re-audit
found no retained consumer. Start and Help count once each, after both
halves' gates; no wider Test, GSL, Assembly, Measure, core or Qt change.
The overseer asks for reconciliation at three tail nodes, but this work
iteration explicitly forbids reconciliation without exception. Leave it to
the separate maintainer; neither state nor plan nor .ouroboros is edited.

## Method

Repeated docs/START-AUDIT.md tracked consumer/symbol searches, including
shell separately. Regenerated both existing caches using pixi run cmake
--preset conda-macos-{release,debug} -U BUILD_START: removal of the option
replaces the disable's forced-OFF assertion. Confirmed absent option/rules/
install includes and retained FreeCADApp/Assembly/TestSources. Inventoried
all exact stale paths: none remained to quarantine. One build-release,
install-release and stage-engine. Installed FreeCADCmd script-file probe
with fresh user/system configs and explicit success marker. Full engine
suite except the committed-HEAD manifest test, four Cadex CTests, serial
inherited CTest, fresh-payload lifecycle/licensing tests. Reserved the HEAD
manifest check for after commit; working-tree manifest matches both imports.
Compared CTest JSON to disable (1533 unchanged), all failure labels against
the recorded baseline, and both fork metrics using manifest scopes/exclusions.
Ephemeral logs/JSON: /tmp/cadex-start-delete-*. No committed binary artifacts.

## Result

Both configurations, one release build (35 steps), install and stage pass.
No installed/staged Mod/Start or lib/Start.so; Test still installs. The 2.4 GB
stage retains documented external local library references, not a relocated
distribution. Start import/group absent; eleven retained imports succeed;
box volume 999.9999999999998 within 1e-9 of 1000, explicit pass marker.
Cadex CTests 4/4 passed in 24.61 s. Inherited CTest 162 failed of 1526 run
in 133.12 s: zero outside 164 baseline names, same two absent baseline names
(DlgVersionMigrator_Tests_run, SpreadsheetRenameProperty.renameProperty),
3 skipped, 7 disabled. Corrected an initial comparison parser to include
SEGFAULT as well as Failed labels. Discovery identical to disable at 1533.
Packaged lifecycle/licensing 25 passed, 1 deselected in 17.80 s; committed-
HEAD manifest check will run after this record's commit. Staging was serialized
before pytest, avoiding the previous unit's transient payload-isolation error.

FreeCAD M files/inserted/deleted 56/1637/1815; inherited remaining 3440
(9309 whole files deleted from import). Before delete 57/1639/1804 and
3467 remaining; run start 47/1804/1907 and 7277 remaining. This deletes
27 inherited files and one M entry but adds 11 to M deleted lines. Both M
line totals and inherited remaining are lower than run start, M file count
is higher. Blender unchanged 44/1046/129, inherited remaining 19052.
No credit for whole-file deletion as M-line reduction.

Next: separate GSL consumer re-audit and possible submodule/setup cleanup
(short item 3). The tail reaches three with this record; maintainer owns
reconciliation. Fresh-cache/from-scratch builds, other platforms and GUI
were not exercised. Final engine-suite result follows.

Engine suite: **2021 passed, 52 skipped, 1 deselected**, 256.74 s. Only the
committed-HEAD manifest test is deferred; no runtime test excluded. With
that post-commit check passing, Help and Start satisfy the two whole-tree
removal criterion, without closing standing inherited-tree reduction.
Dispatch closed: 1 unit — delete Start at its audited boundary with baseline-matched gates and both fork-delta measures.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 449b8e09aac39ed2593aceeab2b093012e12b558

## State Impact

- target: windy-pebble-4630 — Start deleted after verified disable: 27 files and audited consumers removed, macOS runtime gates pass with baseline-matched inherited failures; Help plus Start are two whole-tree removals, conditional only on the reserved post-commit HEAD manifest check.
- target: round-glacier-2865 — ADR-221 removes Start at the audited boundary; no Test, GSL, Assembly, Measure or retained Qt change. Next is the separate GSL consumer re-audit; standing reduction remains open.
- target: green-sea-3991 — FreeCAD M metric 56/1637/1815, inherited remaining 3440 versus run-start 47/1804/1907 and 7277. Both line totals and remaining count are lower; M file count is higher. Blender unchanged 44/1046/129 and 19052 remaining.
