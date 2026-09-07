---
node_id: 5673ac0e-cb6c-5d86-9c4d-ec61cf1ac761
slug: proud-branch-1079
title: Audit surviving FreeCAD differences and qualify Preferences guard removal
created_at: '2026-09-07T03:37:26+00:00'
parents:
- easy-sea-7738
summary: ''
---
## What

Audited the finite 56 surviving FreeCAD manifest modifications and qualified
one exact next-unit boundary: replace JointObject.py's four-line Preferences
ImportError guard with the unconditional import. Documentation only in this
unit; no implementation or inherited file edits. Added ADR-227, the complete
SURVIVING-DIFF-AUDIT inventory, FREECAD pointer and ROADMAP audit checkbox.

## Why

Follows easy-sea-7738, short rank 1, serving mission 3 and green-sea-3991 /
round-glacier-2865. The overseer's older request for reconciliation is already
superseded by the visible maintainer checkpoint and planner dispatch; this
actor is explicitly forbidden to reconcile. Chose the bounded import guard
because Preferences imports safely without GUI and every solver use requires
it: assigning None provides no functioning fallback. Earlier import failure
in a damaged installation is the only proposed error-path change.

## Method

Read STATE, PLAN, graph protocol and vision. Compared each manifest M path
against its recorded import and measured both forks at 7dd3d045 and HEAD
870150b8; intersected git ls-tree paths for inherited-remaining counts,
including tracked symlinks. Inspected all 56 diffs and traced Assembly_Scripts,
Preferences module imports, JointObject.solveIfAllowed and both worker imports.
Git warned that exhaustive rename detection was skipped; used the established
manifest M convention rather than claiming a rename audit.

Ran pixi run FreeCADCmd /tmp/cadex-50-probe.py: current and proposed source
loaded in isolated namespaces with GUI Python imports explicitly denied.
Preferences imported, coin was None, GuiUp was false, and solver dispatch
recorded [False, True] when enabled and no new call when disabled. Restored
the preference in finally. Probe exit 0, AUDIT50 PASS. Candidate existed only
in memory and /tmp. git diff --no-index against import-era JointObject measured
39 inserted / 5 deleted versus current 42 / 5. An AST comparison independently
showed TestPartApp formatting plus exactly three retired import/test removals;
no whole-file or formatter change was selected.

Existing CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run
python -m pytest -q src/Mod/cadex/cadex_tests/test_licensing_compliance.py
src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py passed. Logs:
/tmp/cadex-50-probe.log and /tmp/cadex-50-packaged.log. Audit document carries
exact source substitution, probe procedure and implementation gate requirements.

## Result

26 existing-payload tests passed in 14.19 s; import/dispatch probe passed;
git diff --check passed. No full build, install/stage, full engine pytest,
full inherited CTest or GUI execution; existing payload is baseline evidence,
not proof of an installed implementation.

FreeCAD start: 47/1804/1907 M files/inserted/deleted, 7277 inherited remaining.
HEAD: 56/1637/1819 and 3434. Proposed: 56/1634/1819 and 3434. Blender start,
HEAD and proposed: 44/1046/129 and 19052. Actual audit change in all measures:
zero. Broader GUI-source and fork-delta claims stay open. No state or plan
nodes edited; tail before this record was one unreconciled record.

Next unit may remove exactly this guard, preserving Qt/Coin guards and
Preferences.py, and run the documented source, build/install/stage, baseline-
compared CTest, real assembly and fresh packaged gates. No widening or new
formatter policy; stop with a blocker if mandatory formatting expands scope.
Windows launcher arms remain deferred. This audit neither repeats completed
Material/Main deletions nor resumes motors.

Dispatch closed: 1 unit — qualify the redundant Preferences import guard with finite diff audit and headless probe.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 870150b8c8325f29e94ee7922c2b150981aad25c

## State Impact

- target: green-sea-3991 — Audit confirms 56/1637/1819 surviving FreeCAD M totals and 3434 inherited files; only qualified reduction removes three inserted Preferences guard lines; broad claim stays open.
- target: round-glacier-2865 — ADR-227 inventories all 56 surviving M files and qualifies only JointObject Preferences guard, with GUI-denied import and solver-dispatch evidence; no implementation yet.
