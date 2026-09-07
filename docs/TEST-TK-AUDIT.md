# Test harness Tk runner removal audit

Verified against source: 2026-09-07

[Cadex-new] ADR-230, source baseline `c8d99e61`. This audit qualifies only
`src/Mod/Test/unittestgui.py` for a separate copy/install-disable commit,
then a source-delete commit. Both steps are now implemented separately;
their fresh verification is recorded below.

## Boundary and dependency evidence

The audited 38-file Test tree was not a whole-tree removal candidate;
37 files remain after the bounded deletion. With
`BUILD_TEST=ON`, `src/Main/CMakeLists.txt` makes FreeCADMainCmd depend on
TestSources. `src/App/FreeCADTest.py` imports TestApp and calls
RunConfiguredTextTest; Application.cpp selects TestApp.All/PrintAll.
Init.py registers eight headless test modules. Keep all of these, Test data,
TestSources, and the remaining GUI test files/resources outside this audit.

The selected file was a standalone 399-line / 15,021-byte Python-licensed
PyUnit Tk runner. It imports tkinter, defines GUI runners and starts tk.Tk()
only through main. Its SHA-256 is
`958cb529f117594a43ecf874791751d902518a698509f57a5db4d29b938afc91`.
A tracked-tree case-insensitive search (`git grep -n -i unittestgui --
':!*.md' ':!*.json'`) finds exactly one reference: Test/CMakeLists.txt's
Test_SRCS row. No tracked importer or CTest registration was found.
TestGui uses QtUnitGui, not this runner; its InitGui workbench importer and
Menu consumers are a different boundary. Do not delete them by association.
Arbitrary external imports and direct execution are not covered by the scan;
those unsupported GUI usages are the compatibility cost of later removal.

Test_SRCS feeds Test_COPY_OUTPUTS, TestSources, the Test ALL target,
fc_copy_sources and INSTALL. Removing precisely the unittestgui.py row
therefore disables all its tracked copy/install consumers without disabling
Test. No new option or wrapper is needed. Both existing debug/release caches
have BUILD_GUI=OFF and BUILD_TEST=ON; both generated install rules still list
this file, and release build.ninja has its copy rule.

## Existing outputs and verification

At the baseline, source, release Mod/Test and the pixi install's Mod/Test
contain identical bytes with the hash above. Debug Mod/Test and the existing
`build/engine/cadex-engine-0.0.0-macos-arm64/Mod/Test` lack the file. No matching
pyc was found beneath those four Mod/Test roots. The payload builder's
keep_mods excludes Test. This is a local inventory, not an assertion about
other installations or every filename in the payload.

The installed engine passed a GUI-denied retained-behavior probe: install an
importlib.abc.MetaPathFinder raising ImportError for top-level unittestgui,
tkinter and FreeCADGui, assert not FreeCAD.GuiUp, import TestApp and run
`result = TestApp.TestText('UnitTests')`. Assert result.wasSuccessful(),
result.testsRun > 0 and absence of all three forbidden modules in sys.modules.
`pixi run FreeCADCmd /tmp/cadex-55-test-probe.py` exited 0 and printed
`TEST55 PASS tests=12`; all twelve native UnitTests passed. This proves this
retained text-runner path, not every inherited test or proposed removal.

Existing-stage baseline:

```sh
CADEX_ENGINE_ROOT="$PWD/build/engine/cadex-engine-0.0.0-macos-arm64" \
  pixi run python -m pytest -q \
  src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py \
  src/Mod/cadex/cadex_tests/test_licensing_compliance.py
```

26 passed in 13.36 s, no skips/failures. Source/stage cadexd.py bytes match (SHA-256
`aadb8d25a4046b5ebdacd0bcd73bd7917bb6ac6c9642052853eb177d3553dd9e`);
this is not whole-payload identity.
No configure/build/install/stage, full engine suite, full CTest, GUI or
portable-release validation ran for this documentation-only audit. The
existing stage retains local external-library dependencies.

## Separate implementation obligations

First remove only the Test_SRCS row; retain the source. Reconfigure both
caches and verify regenerated rules no longer copy/install it. Quarantine
stale copies/bytecode from debug, release and install before building; check
the finished stage too. Run at most one release build, install and completed
stage, then the full engine suite, packaged lifecycle/licensing gate, the
GUI-denied text-runner probe and Cadex CTests. Compare inherited CTest names,
skips and inventory with the recorded baseline rather than assuming green.
Keep TestSources and headless registration unchanged. CMakeLists.txt already
has the modification notice and manifest membership; verify against committed
HEAD. Record actual output, local-stage limitations and any new failures.

Only after that separate verified disable commit, delete the one source file
and repeat applicable gates. Preserve its upstream licence in history; no
licence/header rewrite is part of this work. Measure whole-file savings
separately from surviving-file M deltas. Neither whole-Test removal nor the
broad fork-delta criterion is established by this audit.

## Copy/install disable (2026-09-07)

Removed only unittestgui.py from Test_SRCS; the 399-line source retains its
audited SHA-256. TestSources, MainCmd dependencies, headless registration and
every other Test file are unchanged. Both debug/release configure commands
passed, and neither regenerated build.ninja nor Test/cmake_install.cmake
mentions the runner. The complete 1,533-entry CTest inventory (including
commands and properties) is identical before and after configuration.

Quarantined the release and pixi-install copies, each matching the audited
source hash; debug and stage had no copy, and none of the four roots had
matching bytecode. One `pixi run build-release`, `pixi run install-release`
and completed `pixi run stage-engine` passed. Afterwards all four Mod/Test
roots contain no unittestgui source or bytecode. Test remains excluded from
the payload by the pre-existing keep_mods policy.

Verification source parent: `862cb137`; changed Test/CMakeLists.txt SHA-256:
`b6c1d03c5d20fb9d643f7a0021f49fecb69b509bb9cbb14a11219a51e48a7523`.
Source and fresh staged cadexd.py still share the audit's
`aadb8d25a4046b5ebdacd0bcd73bd7917bb6ac6c9642052853eb177d3553dd9e` hash.
This identifies those files, not the whole payload. The 2.4 GB local stage
reports external library paths and is not a relocatable release.

Fresh packaged lifecycle/licensing: **26 passed in 18.07 s**, exit 0, using
the command above. The installed GUI-denied TestApp probe again reports
**12 UnitTests passed**, exit 0. `pixi run ctest --test-dir build/release
-R Cadex --output-on-failure`: **4/4 passed**, 19.12 s.
`pixi run test-release`: **162 failures out of 1,526 run**, 131.15 s, exit 8.
All failure names occur in the 164-name recorded baseline; the two absent
names are the already-retired DlgVersionMigrator and SpreadsheetRenameProperty
cases. The seven disabled and three skipped names match iteration 51 exactly.
No new failure, skip or inventory change is attributed to this disable.

Full source engine suite: `pixi run python -m pytest -q
src/Mod/cadex/cadex_tests`: **2,023 passed, 52 skipped in 262.59 s**, exit 0.
The existing inherited modification notice and manifest membership cover
Test/CMakeLists.txt; this change adds no modified-file member and removes
no source file. Recheck licensing against committed HEAD at close.
Local verification logs use `/tmp/cadex-56-` with configure-debug,
configure-release, build, install, stage, engine, packaged, probe, cadex-ctest
and ctest suffixes. No shell, GUI, Windows or portable-release gate ran.
The next unit may delete only the retained runner after this disable is
committed; repeat the audit's fresh gates and stale-copy checks.

## Separate source deletion (2026-09-07)

After verified disable commit `bd755c50`, delete only
`src/Mod/Test/unittestgui.py`. All 37 other Test files, TestSources,
MainCmd dependencies, headless registrations and resources remain unchanged.
The unsupported direct source runner is now unavailable; its Python licence
and original bytes remain in git history. No new inherited modification
notice or manifest member is required for deleting this unmodified import.

Fresh debug/release configure, one release build, install and completed stage
all exit 0. Neither generated build.ninja nor Test/cmake_install.cmake
mentions the runner; the complete CTest JSON inventory is identical before
and after at 1,533 entries. All four audited Mod/Test output roots have no
runner source or bytecode, with no further stale files to quarantine.
Source/stage cadexd.py retain the audit hash above, and Test/CMakeLists.txt
retains the disable hash. Source parent is `bd755c50`; these identities do
not assert whole-payload identity. The 2.4 GB stage still uses local external
libraries and is not a relocatable release.

Full source engine pytest: **2,023 passed, 52 skipped in 262.72 s**, exit 0.
Fresh packaged lifecycle/licensing: **26 passed in 19.02 s**, exit 0.
Installed GUI-denied TestApp probe: **12 UnitTests passed**, exit 0.
Cadex CTests: **4/4 passed in 22.85 s**. Full inherited CTest exits 8:
**162 failures out of 1,526 run in 130.46 s**. All failure names equal the
previous disable run and occur in the 164-name baseline; the two absent
names remain DlgVersionMigrator and SpreadsheetRenameProperty. The seven
disabled and three skipped names also equal the disable run. No unexplained
failure or inventory change blocks this deletion.

Whole-file savings: **one file, 399 lines, 15,021 bytes**. Manifest-scoped
inherited remaining paths fall from 3,434 to **3,433**, versus **7,277** at
nt2 start `7dd3d045`. Count tracked import/current path intersections with
manifest scopes and ours exclusions; do not follow tracked symlinks.
Surviving FreeCAD modified-file totals are **56 / 1,634 / 1,820**
(files / inserted / deleted), unchanged by this deletion, versus start
**47 / 1,804 / 1,907**. The separate disable accounts for the one additional
deleted line since the Preferences measurement. Blender remains
**44 / 1,046 / 129**, with **19,052** inherited paths, at both revisions.
Manifest membership is unchanged; whole-file savings are not surviving-file
line changes, and neither whole-Test nor broad fork-delta closure follows.

Local logs use `/tmp/cadex-57-` with configure-debug, configure-release,
build, install, stage, engine, packaged, probe, cadex-ctest, ctest, inventory
and metrics suffixes; CTest inventories use before/after JSON files.
No shell, GUI, Windows, remote or portable-release gate ran.
