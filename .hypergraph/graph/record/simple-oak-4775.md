---
node_id: 5d43afc6-c361-5df3-bfac-337fd6a733f2
slug: simple-oak-4775
title: Disable Test's standalone Tk runner copy and install path
created_at: '2026-09-07T04:23:56+00:00'
parents:
- twilight-wolf-7995
summary: ''
---
## What

Disabled only Test's standalone unittestgui.py copy/install row. Retained its 399-line source, all other Test files, TestSources and MainCmd dependencies. Updated ADR-230, the Test audit, FREECAD ledger and the separate ROADMAP disable/delete checkboxes.

## Why

Mission 3, frontier round-glacier-2865, follows the qualified boundary and short-rank bet twilight-wolf-7995. The overseer's reconciliation request was superseded by this dispatch's explicit prohibition; the supplied plan already promotes this pair. Choose the reversible one-row disable, not deletion or broader Test changes. Servo qualification stays stopped. Unsupported users of the installed Tk runner lose that entry point; this is the audited compatibility cost.

## Method

Starting HEAD 862cb137928944206d77c95e1b2f148cf504321e. Both pixi configure-debug/configure-release passed; assert regenerated debug/release build.ninja and Test/cmake_install.cmake omit unittestgui. Quarantine the release and pixi-install copies, each with SHA-256 958cb529f117594a43ecf874791751d902518a698509f57a5db4d29b938afc91; debug/stage had none and no matching bytecode existed. One pixi run build-release followed by install-release and completed stage-engine passed before payload readers.

Fresh gates: full engine pytest; CADEX_ENGINE_ROOT set to the local staged payload for test_cadexd_lifecycle.py plus test_licensing_compliance.py; installed FreeCADCmd runs the audit's import-denied TestApp.TestText('UnitTests') probe; ctest -R Cadex and full test-release. Compare full CTest JSON inventory before/after configure and failed, disabled and skipped names against recorded evidence. TEST-TK-AUDIT.md contains commands, identities and results. Logs remain local under /tmp/cadex-56-*.log. Existing inherited notice/manifest membership apply to the already-modified CMake file; rerun licensing after committing to check committed HEAD.

## Result

Configure, build, install and stage exit 0. All four inventoried output roots lack runner source/bytecode, while retained source hash is unchanged. Full engine: 2023 passed, 52 skipped in 262.59 s, exit 0. Fresh packaged lifecycle/licensing: 26 passed in 18.07 s, exit 0. Installed GUI-denied probe: 12 UnitTests passed, exit 0. Cadex CTests: 4/4 passed in 19.12 s. Full CTest exit 8: 162 failures out of 1526 run in 131.15 s; zero new names against the 164-name baseline. DlgVersionMigrator and SpreadsheetRenameProperty remain already retired. Inventory identical at 1533 entries; seven disabled and three skipped names identical to iteration 51.

Changed CMake SHA-256 b6c1d03c5d20fb9d643f7a0021f49fecb69b509bb9cbb14a11219a51e48a7523. Source/stage cadexd.py share aadb8d25a4046b5ebdacd0bcd73bd7917bb6ac6c9642052853eb177d3553dd9e; not whole-payload identity. The 2.4 GB stage retains external libraries and is not a portable release. No GUI, shell, Windows or remote execution. No source-file savings or broad fork-delta closure claimed. Next: after this separate disable commit and committed-HEAD licensing check, delete only the retained runner in a new unit and repeat fresh gates; no new dependency or unexplained failure was found here. Do not reconcile in a work dispatch.

Dispatch closed: 1 unit — disable the standalone Test Tk runner copy/install path with retained headless behavior verified.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 862cb137928944206d77c95e1b2f148cf504321e

## State Impact

- target: round-glacier-2865 — Standalone Test Tk runner copy/install disabled with source retained; fresh build/stage, full engine, packaged and retained text gates pass, inherited CTest unchanged baseline; separate source deletion is next.
