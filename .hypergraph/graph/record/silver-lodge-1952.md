---
node_id: b3e3e92e-45af-53f6-a107-4b3c7d888c46
slug: silver-lodge-1952
title: Delete the verified-disabled standalone Test Tk runner
created_at: '2026-09-07T04:32:13+00:00'
parents:
- simple-oak-4775
summary: ''
---
## What

Deleted only src/Mod/Test/unittestgui.py after separate verified disable commit bd755c50. Preserved all 37 other Test files, TestSources, MainCmd dependencies, headless registrations and resources. Updated ADR-230, FREECAD ledger, dated Test audit and ROADMAP deletion checkbox.

## Why

Mission 3, frontier round-glacier-2865 and green-sea-3991; short rank 2 and the overseer explicitly authorize this bounded deletion after simple-oak-4775. The audited unsupported direct Tk source runner is the compatibility cost. No broader Test, shell, Windows or servo change is inferred. The overseer's reconcile request is delegated to the separate maintainer because work dispatches explicitly forbid reconciliation and state edits.

## Method

Source parent bd755c50. Fresh pixi run configure-debug and configure-release; assert generated build.ninja and Test/cmake_install.cmake omit unittestgui. Full CTest JSON inventory before/after is identical at 1533 entries. One pixi run build-release, install-release and completed stage-engine exit 0 before payload readers. Four debug/release/install/stage Mod/Test roots have no runner source or bytecode; no further stale files needed quarantine.

Run full engine pytest, fresh CADEX_ENGINE_ROOT packaged test_cadexd_lifecycle.py plus test_licensing_compliance.py, GUI-denied installed TestApp.TestText('UnitTests'), ctest -R Cadex, and full test-release. Compare failed (including crash statuses), disabled and skipped names against iteration 56 and the recorded baseline. Measure manifest-scoped import-relative surviving M numstat separately from tracked import/current path intersections, excluding ours prefixes without following symlinks. TEST-TK-AUDIT.md contains commands, file hashes and details; local logs remain under /tmp/cadex-57-*.log, inventories in before/after JSON. Existing CMake notice and manifest membership are unchanged; rerun licensing against committed HEAD after the commit.

## Result

Full engine: 2023 passed, 52 skipped in 262.72 s, exit 0. Fresh packaged lifecycle/licensing: 26 passed in 19.02 s, exit 0. Installed GUI-denied probe: 12 UnitTests passed, exit 0. Cadex CTests: 4/4 in 22.85 s. Full CTest: exit 8, 162 failures out of 1526 run in 130.46 s, identical failure names to the disable iteration and zero new against 164-name baseline. Already-retired DlgVersionMigrator and SpreadsheetRenameProperty remain absent. Seven disabled and three skipped names unchanged; complete 1533-entry inventory identical. No new dependency or unexplained failure found.

Whole-file savings: one file, 399 lines, 15021 bytes. FreeCAD inherited remaining 3433 versus parent 3434 and nt2 start 7dd3d045's 7277. Surviving M files/inserted/deleted stay 56/1634/1820, versus start 47/1804/1907. The preceding disable accounts for one deleted line since Preferences' 1819. Blender unchanged at 44/1046/129 and 19052 inherited paths. Whole-file deletion does not alter manifest membership; no broad fork-delta closure claimed.

Source and staged cadexd.py both SHA-256 aadb8d25a4046b5ebdacd0bcd73bd7917bb6ac6c9642052853eb177d3553dd9e; Test/CMakeLists.txt b6c1d03c5d20fb9d643f7a0021f49fecb69b509bb9cbb14a11219a51e48a7523. These are file identities, not whole-payload equivalence. The 2.4 GB local stage reports external library paths and is not a portable release. No GUI, shell, remote or Windows gate ran.

Next: this record brings the unreconciled tail to three. The separate maintainer should reconcile before further implementation, then the planner should replan after the completed Tk disable/delete pair. No state or plan edits occurred here; broader Test removal remains unqualified.

Dispatch closed: 1 unit — delete the verified-disabled standalone Test Tk runner with retained headless behavior and baseline gates verified.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: bd755c50a2f73d30d0578431344bb2725b6c8e1b

## State Impact

- target: round-glacier-2865 — Qualified Test Tk disable/delete pair complete; only unittestgui.py deleted, fresh build/stage and retained headless gates pass with unchanged inherited CTest baseline; broader Test remains unqualified.
- target: green-sea-3991 — One inherited file removed (399 lines, 15021 bytes); FreeCAD inherited remaining 3433, surviving M totals unchanged at 56/1634/1820; Blender unchanged and broad criterion stays open.
