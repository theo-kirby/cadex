---
node_id: 6b1cb66a-b08d-53d2-b47b-9c5a4ac025ff
slug: green-stone-3882
title: Disable deleted GUI translation writer dispatch and preserve App/Base
created_at: '2026-09-07T05:06:28+00:00'
parents:
- damp-sand-1115
summary: ''
---
## What

Disable only the inherited translation updater's deleted GUI writer dispatch. Apply/install now ends after translation installation; updateTranslator prints an explicit retirement diagnostic without requesting progress. Retain updateTranslatorCpp and its exclusive PySide import for a separate delete commit. Add isolated regression coverage and update ADR-232, ROADMAP, FREECAD ledger and translation audit.

## Why

Mission 3, round-glacier-2865 and green-sea-3991, following bounded planner bet damp-sand-1115. The overseer's requested reconciliation and planner handoff already landed in c8219dd1/de421847/e72d714f; no actor reconciliation is needed or permitted. Assume unknown external maintenance users may rely on GUI registration: this stage explicitly retires that side effect but preserves direct helper imports, startup, all other commands, App/Base translations and Qt consumers. No wider cleanup or whole-tool deletion is justified.

## Method

Read actor/record skills, STATE, PLAN, hypergraph contract, VISION, audit, disposition and bet. Change only src/Tools/updatecrowdin.py among inherited sources (+1/-12). Tests execute the original AST dispatch after stubbing PySide imports, credentials, Crowdin service and GUI writer; synthetic archive/copy/QRC paths stay in pytest temporary directories. Preserve actual helper code during disable. Run tests against current and previous source, full engine pytest, one release build, baseline-compared inherited CTest, App/Base source byte comparison, generated resource inventory and installed FreeCAD.Qt translation probe. No live service, GUI, install, staging or external-machine action.

## Result

Eleven updater tests pass. Against previous source exactly three fail (updateTranslator, apply, install) and eight retained-behavior tests pass. Full engine suite: 2034 passed, 52 skipped in 258.56 seconds, exit 0. Single pixi run build-release exits 0. Inherited CTest exits 8: 162 failures/1526 enabled tests in 133.10 seconds; zero new failure names against 164-name baseline. The absent baseline names are already-retired DlgVersionMigrator_Tests_run and SpreadsheetRenameProperty.renameProperty; seven disabled and three skipped registrations are separate from failures.

All 78 App/Base TS files are byte-identical to previous HEAD; generated App_translation.qrc references 76 existing QMs. Installed FreeCADCmd with a headless PySide6 QCoreApplication loads App_de.qm, translates QObject/Unnamed to Unbenannt, removes translators and restores Unnamed. Initial bare Python FreeCAD import exited 139; FreeCADCmd without QCoreApplication returned false on installation. Creating the required headless Qt application made the probe pass; no production fix was made or inferred. Licensing first caught the new test's missing SPDX declaration, then passed after correction: combined updater/licensing 21 passed, 1 packaged-license skip. Full engine suite includes the corrected file. git diff --check passed. Export/check and committed-HEAD licensing verification follow record minting and the single commit; delete remains conditional on that final check.

Surviving FreeCAD M files/inserted/deleted: 56/1635/1832 versus previous 56/1634/1820; Blender unchanged 44/1046/129. Existing manifest membership and modification notice remain accurate. Zero whole-file saving. No install/stage, fresh packaged lifecycle or shell gate was run or claimed: updater has no build/install rule and payload was untouched. No network workflow success follows from stubs. Next is only the separately gated helper/PySide deletion after committed-HEAD checks; broader inherited and catalog criteria remain open. Logs and temporary old-source/probe fixtures are outside the repository; durable commands/results are in TRANSLATION-UPDATER-AUDIT.md. This record brings the unreconciled tail to two, below the three-record threshold.

Dispatch closed: 1 unit — disable the deleted GUI translation writer paths while preserving App/Base translation behavior.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: e72d714f09af968cea8747bf876c858bc1381ef4

## State Impact

- target: round-glacier-2865 — GUI translator writer dispatch disabled under ADR-232 with isolated regressions, release build, 2034 engine passes, baseline-only CTest failures and retained translation probe; helper/PySide deletion remains a separate gated unit.
- target: green-sea-3991 — Updater-only inherited diff changes surviving FreeCAD M totals from 56/1634/1820 to 56/1635/1832; no whole-file saving, Blender unchanged and manifest membership retained.
