---
node_id: 2598c564-79de-58ec-a543-99a9d951424d
slug: humble-tide-6752
title: Qualify Test's standalone Tk runner removal boundary
created_at: '2026-09-07T04:11:10+00:00'
parents:
- hidden-ridge-7342
summary: ''
---
## What

Audited the inherited Test harness and qualified only its standalone
unittestgui.py Tk runner for separate copy/install-disable and source-delete
commits. Added TEST-TK-AUDIT.md, ADR-230 and an audit-only checked ROADMAP item;
updated the FreeCAD ledger. No inherited source, runtime or manifest change.

## Why

The overseer stops the exhausted two-servo bet: no proof, delivery, third
candidate or recipe refactor. Choose the highest-priority actionable standing
frontier, mission 3 / round-glacier-2865: a finite dependency audit of Test,
which earlier reduction records explicitly left unaudited. The reversible
choice is to qualify one unused GUI runner and retain the live MainCmd to
TestSources dependency. This follows hidden-ridge-7342's stop, not a new servo
search. Maintainer and planner own reconciliation and replanning; this actor
neither invokes those roles nor edits their files.

## Method

Read STATE, PLAN, VISION, actor/record contracts and the stopped qualification.
Trace Test CMake copy/install lists, Init.py registration, TestApp and
App/FreeCADTest.py execution; distinguish TestGui/InitGui and their Qt consumers
from the independent Tk runner. Tracked-tree case-insensitive search finds
only the unittestgui.py CMake row. Inspect generated debug/release install
rules, release copy rules, source/release/install hashes and four Mod/Test
roots for stale files/bytecode. Exact commands and boundary are in the audit.

Run an installed FreeCADCmd probe that denies unittestgui, tkinter and
FreeCADGui imports, asserts GuiUp=false, then executes TestApp.TestText('UnitTests')
and checks success, count and forbidden-module absence. Run existing-stage
packaged lifecycle/licensing pytest with CADEX_ENGINE_ROOT pointing to the
local stage. Check cadexd.py source/stage byte equality at c8d99e61. No build
or source mutation required; no GUI or remote work.

## Result

One 399-line / 15,021-byte candidate qualifies. Its sole tracked copy/install
row is the future disable boundary. Identical source/release/install bytes
are inventoried; debug/stage copies and matching pyc under inspected Mod/Test
roots are absent. Whole Test removal remains unqualified. Unsupported direct
or external Tk-runner use is the later removal's compatibility risk.

Native probe: 12 tests passed, exit 0, explicit TEST55 PASS tests=12 marker.
Existing packaged lifecycle/licensing baseline: 26 passed in 13.36 s, no
failures/skips. This is an existing local stage, not a new build, complete
source/payload equivalence or portable-release proof. Full engine suite and
CTest were not run for docs-only work. git diff --check passes.

Next: designated maintainer/planner may adopt the separate one-row disable,
then deletion only after its fresh gates. The unreconciled tail reaches three
records including this one; contributor restrictions remain in force. Four
servos and seven inclusively counted powered identities remain: at least one
servo and three powered identities are still missing, and breadth/L3 evidence
requirements are unchanged. No product criterion closes here.
Dispatch closed: 1 unit — qualify Test's standalone Tk runner removal boundary.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: c8d99e614c93bd421645d6711f4e112b9056d689

## State Impact

- target: round-glacier-2865 — ADR-230 qualifies only unittestgui.py copy/install disable then deletion; retain MainCmd/TestSources and all other Test files. Native GUI-denied text tests pass 12; existing packaged baseline passes 26. No removal yet.
