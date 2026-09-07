---
node_id: a69a85c0-299e-5024-beb4-a190f431f019
slug: steady-dew-8037
title: Delete the disabled Help module at its audited boundary
created_at: '2026-09-07T00:54:36+00:00'
parents:
- warm-anchor-2441
summary: ''
---
## What

Landed the delete half of the Help whole-tree removal as commit `b24761b4`
(ADR-218): `src/Mod/Help` (85 tracked files, 8,480 lines), the `if(BUILD_HELP)`
gate in `src/Mod/CMakeLists.txt`, the forced-OFF `BUILD_HELP` cache entry from
ADR-217 (now a two-line comment), the `value(BUILD_HELP)` report line, the Help
row in `src/Tools/updatecrowdin.py`, and the `src/Mod/Help` path entries in
`.pre-commit-config.yaml` and `contrib/.vscode/settings.json`. Ledger row,
ROADMAP tick, ADR-218, `docs/HELP-AUDIT.md` §"Delete landed" and the manifest
entry plus notice for `updatecrowdin.py` are in the same commit. The packaged
gate result lines land with this record commit because that test is bound to
committed HEAD.

## Why

Plan short item 1 (`young-crane-9546`), serving mission 3 and the frontier
nodes `windy-pebble-4630` (two engine-side removals), `round-glacier-2865`
(inherited-tree reduction) and `green-sea-3991` (fork delta). The overseer
asked for a reconcile first because the tail was at three; it was already
reconciled at `655a2b1c` and the tail was one node, so no reconcile was due and
none was run. Assumption written here: the other already-deleted trees still
listed in the two developer-config files and in `updatecrowdin.py` are left
alone, as the audit asked; widening to them is a separate unit.

## Method

Reaudited consumers with the audit's search basis (nothing live outside docs
and the graph). `git rm -r src/Mod/Help`, six targeted edits, manifest entry,
`tools/apply_modification_notices.py --write`. Then, in order, on macOS:
explicit `-DBUILD_HELP=ON` reconfigure over both existing caches; `cmake -U
BUILD_HELP` to drop the unread variable; `pixi run build-release` (37
incremental Ninja steps); `install-release`; `stage-engine`; installed
`FreeCADCmd` probe from a script file; `pixi run test-engine`; the four Cadex
ctests; serial inherited CTest diffed by failure name against
`build/ctest_baseline_failures.txt` (excluding Skipped/Disabled lines); the
packaged lifecycle/licensing gate before and after the commit. Manifest-scoped
M metrics recomputed with the PHASE8-AUDIT method. Logs under
`/tmp/cadex-help-delete-*.log`.

## Result

- Both caches: exit 0, 0 `Mod/Help` Ninja rules, no Help install include, no
  `BUILD_HELP` cache entry after `-U`; the final report no longer lists it.
- Build 37 steps, install and stage exit 0; installed `Mod/` keeps Start and
  Test, the payload prunes them as before; no `Mod/Help` anywhere.
- Probe: `import Help` / `import Help_rc` → `No module named`; Measure,
  Assembly, MassProperties, JointObject, UtilsAssembly, Part, PartDesign,
  Sketcher, Mesh, MeshPart, cadexd import; box volume 1000. The `-c` string
  form of the same probe crashed ("Application unexpectedly terminated");
  the script-file form is the one that works.
- Engine suite: 2,021 passed, 52 skipped, 1 failed pre-commit — the
  HEAD-bound manifest test, which passed after the commit.
- Cadex ctests 4/4. Serial CTest: 162 failed of 1,537 run (1,544 registered,
  3 skipped, 7 disabled, unchanged), 160 Failed + 2 SEGFAULT, **0 names
  outside the baseline**, the same 2 baseline names absent (ADR-214 binaries).
- Packaged gate after the commit: 26 passed in 13.6 s, manifest equal to HEAD.
- Manifest-scoped M metrics: FreeCAD 56/1,638/1,797 → **57/1,637/1,803**
  (updatecrowdin.py newly modified; deleted whole files are not M entries);
  Blender 44/1,046/129 unchanged. Fork-delta criterion not advanced by this
  measure.
- Not run: fresh-cache configure, from-scratch build, Linux/Windows.
- Help is now **one** complete engine-side whole-tree removal (ADR-216 audit,
  ADR-217 disable, ADR-218 delete). `windy-pebble-4630` needs one more.

Dispatch closed: 1 unit — Help deleted at the audited boundary with the full gate set green against the baseline; first engine-side whole-tree removal complete, Start audit is next.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: b24761b45ec02b6523acff34684d9512dd141d51

## State Impact

- target: windy-pebble-4630 — Help's delete commit b24761b4 (ADR-218) completes the first engine-side whole-tree removal under the two-commit protocol (audit ADR-216, disable ADR-217, delete ADR-218), with the full gate set run in the same unit: both caches with explicit ON, release build, install, stage, installed probe, engine suite 2,021 passed, Cadex ctests 4/4, serial CTest 0 names outside the baseline, packaged gate 26 passed; one removal remains, Start or Test must qualify through its own audit
- target: round-glacier-2865 — src/Mod/Help is deleted (85 files, BUILD_HELP option gone); the remaining unretained engine trees are Start and Test, both still built and installed and pruned only by the payload
- target: green-sea-3991 — manifest-scoped FreeCAD M metrics after the Help delete are 57 files / 1,637 inserted / 1,803 deleted (updatecrowdin.py newly modified with notice; deleted whole files are not M entries), against 56/1,638/1,797 at the disable and 47/1,804/1,907 at nt2 start; this criterion is not advanced by that measure
