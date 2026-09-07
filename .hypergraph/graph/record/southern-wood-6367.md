---
node_id: 6e880b9a-1b5d-5160-9493-113a89f7d3ec
slug: southern-wood-6367
title: Disable Start at the audited boundary, retaining all sources
created_at: '2026-09-07T01:25:30+00:00'
parents:
- still-quill-0059
summary: ''
---
## What

Disabled Start at the ADR-219 boundary: `BUILD_START` is forced OFF even over
existing caches or explicit ON requests. All 27 module/test sources, all
three gates and the report line remain. ADR-220, the inherited-tree ledger,
the narrow ROADMAP checkbox and START-AUDIT verification are updated.

## Why

One unit from short item 1, serving mission 3 and windy-pebble-4630,
round-glacier-2865 and green-sea-3991. The audited reversible choice removes
the unused shipped Start extension before a later source delete. Test and
GSL remain untouched. The overseer's reconcile request is stale: STATE
already incorporates Help deletion and the Start audit; only its subsequent
bet was unreconciled on arrival. More importantly, this dispatch explicitly
forbids contributor reconciliation without exception, so none was run.

## Method

Followed docs/START-AUDIT.md's six verification steps on macOS arm64.
Configured both existing caches with `pixi run cmake --preset
conda-macos-{release,debug} -DBUILD_START=ON`. Checked cache/report OFF,
no Start Ninja/install rules, and retained FreeCADApp/Assembly/TestSources.
Inventoried and quarantined the exact stale installed and generated Start
paths. One release build, install-release, stage-engine; checked absence of
both Mod/Start and lib/Start.so in install/stage and retention of installed
Test. Probed installed FreeCADCmd with a script file and fresh user/system
parameter paths. Ran full engine pytest, four Cadex CTests, serial inherited
CTest and fresh-payload lifecycle/licensing pytest. Compared CTest JSON
registrations and failure names, and recomputed both manifest-scoped fork
metrics against the existing imports. Detailed commands/results are in
START-AUDIT.md; ephemeral logs/JSON use /tmp/cadex-start-* and quarantine
/tmp/cadex-start-disable-quarantine, not committed artifacts.

## Result

Both configurations, the sole release build, install and stage passed.
Start import fails and no Start parameter group exists; eleven retained
modules import; box volume is 999.9999999999998 (tolerance 1e-9). Initial
probe mistakes were corrected: retained target is TestSources, not
TestScripts, and volume requires floating-point tolerance. FreeCADCmd's zero
exit alone is insufficient because script exceptions can still return zero;
the corrected script prints an explicit pass marker.

Cadex CTests: 4/4 passed, 20.48 s. Inherited CTest: 162 failed of 1,526 run,
134.02 s; zero names outside the 164-name baseline; the same two absent
baseline names as Help deletion, 3 skipped and 7 disabled. Registrations
1,544 -> 1,533: exactly eleven passing FileUtilitiesTest cases removed, no
other removal and no addition. Fresh packaged lifecycle/licensing suite:
26 passed, 19.16 s; manifest path set unchanged.

The first full engine suite overlapped staging and caught temporary bin/ccx
before pruning: 1 failed, 2,021 passed, 52 skipped, 269.46 s. This is a
verification-order error, not a pre-existing baseline failure. The affected
test passed alone after staging in 1.26 s; the full stable-stage rerun is
reported below. Future iterations must serialize staging before suites that
inspect the payload.

FreeCAD M files / inserted / deleted: 57 / 1,639 / 1,804 versus run-start
47 / 1,804 / 1,907; inherited remaining 3,467 versus 7,277. Corrects the
audit's 3,468/7,287 figures, which included 1/10 added files. Blender remains
44 / 1,046 / 129, inherited remaining 19,052. No source files are removed
in this unit, and no whole-tree-removal credit is claimed.

Next: the separate Start delete after this disable commit and its gates;
repeat the audited consumer check and verification. Keep Test and GSL out
of that deletion. Fresh-cache configure, from-scratch build, other platforms
and GUI were not run. State/plan projections and .ouroboros were untouched.

Full stable-stage engine rerun: **2,022 passed, 52 skipped**, 249.42 s.
Dispatch closed: 1 unit — disable Start with all sources retained and the audited gates verified.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: b3c74f8732242c2355dea7bc989d558eeb1db7f4

## State Impact

- target: windy-pebble-4630 — Start disable verified; all 27 sources retained, separate delete next. Help remains the only completed whole-tree removal.
- target: round-glacier-2865 — ADR-220 forces Start OFF in both existing caches and explicit ON requests; no Start module or library installs or stages; macOS gates pass with inherited failures matching baseline.
- target: green-sea-3991 — After Start disable FreeCAD M metric is 57/1639/1804, inherited remaining 3467. Correct audit remaining counts to 7277 at run start and 3467 now by excluding added files; Blender remains 44/1046/129 and 19052 inherited files.
