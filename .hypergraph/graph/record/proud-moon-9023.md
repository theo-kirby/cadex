---
node_id: 1fe0f14b-4e53-5d95-8b78-4cd9b9690c94
slug: proud-moon-9023
title: Remove redundant Preferences guard with fresh headless verification
created_at: '2026-09-07T03:44:08+00:00'
parents:
- proud-branch-1079
summary: ''
---
## What

Removed exactly JointObject.py's redundant Preferences ImportError wrapper,
replacing four lines with import Preferences. Qt/Coin guards, explanation,
Preferences.py and all other inherited code are unchanged. Updated ADR-227,
FREECAD, SURVIVING-DIFF-AUDIT and the ROADMAP implementation checkbox.

## Why

Follows proud-branch-1079 and the overseer's exact-boundary dispatch, serving
mission 3 and round-glacier-2865 / green-sea-3991. Preferences is required by
solveIfAllowed; None was no functioning fallback. A damaged installation now
fails at import rather than during solver dispatch. No supported functionality
is removed or retired functionality restored. The contributor prohibition on
reconciliation takes precedence over the overseer's reconcile request; leave
the third unreconciled record for the separate maintainer.

## Method

Repeated the audited GUI-denied import/dispatch probe on tracked source and
staged Assembly modules under pixi run FreeCADCmd, preserving the user's prior
SolveInJointCreation preference in finally. Both import Preferences, bind
coin=None, record [False, True] when enabled and no further call when disabled.
One pixi run build-engine completed release build and install, followed by
completed pixi run stage-engine. cmp confirms the source and staged file match.
Ran full source pytest, full inherited CTest and fresh staged lifecycle/licensing
pytest including test_cadexd_solves_a_jointed_assembly. Compared CTest failure
names including SEGFAULT entries, excluding skipped/disabled lists, against
build/ctest_baseline_failures.txt. Measured manifest-scoped import-to-worktree
numstat and tracked-path intersections against nt2 start 7dd3d045 and parent
HEAD. No manifest membership or notice changes required. No installed commit
hook; no formatter-policy exception or unrelated formatting change introduced.
Logs are /tmp/cadex-51-{probe,staged-probe,build,stage,engine,packaged,ctest}.log
and /tmp/cadex-51-ctest-comparison.txt. The committed-HEAD licensing equality
check follows the single commit because its test intentionally ignores worktree.

## Result

Both GUI-denied probes exit 0. Build/install and local stage exit 0. Full engine:
2023 passed, 52 skipped in 272.43 s. Fresh packaged lifecycle/licensing:
26 passed in 18.67 s. Inherited CTest: exit 8, 162 failures of 1526 run in
148.93 s; zero new names versus 164 baseline failures. Already-retired
DlgVersionMigrator_Tests_run and SpreadsheetRenameProperty.renameProperty are
absent, not newly fixed. Local staging reports external library paths as expected;
no relocatable release, Windows or GUI validation is claimed. Fresh staged
results above supersede the previous audit's existing-payload-only evidence.

Actual FreeCAD M files/inserted/deleted: 56/1634/1819 versus parent
56/1637/1819 and start 47/1804/1907; inherited remaining stays 3434 versus
start 7277. JointObject alone is 39/5 versus 42/5. Blender remains
44/1046/129 and 19052 inherited remaining at all three revisions. Three inserted
lines removed, no inherited file removed; broader fork-delta and GUI-source
claims remain open. git diff --check passed. No state, plan or ouroboros files
edited. Tail becomes three records: maintainer reconciliation and subsequent
planner dispatch are next; do not widen this completed boundary or repeat the
audit without new evidence.

Dispatch closed: 1 unit — remove only the qualified Preferences guard with fresh headless verification and three-line surviving-diff savings.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 20ede95deec0418ed6182c662cef093a47661367

## State Impact

- target: round-glacier-2865 — ADR-227 Preferences guard removal implemented; GUI-denied probes, release build/install/stage, 2023 source tests and 26 fresh packaged tests pass; inherited CTest has zero new failures.
- target: green-sea-3991 — Actual FreeCAD surviving M totals fall to 56/1634/1819; inherited remaining stays 3434, Blender unchanged; manifest and notices remain accurate and broad reduction claim stays open.
