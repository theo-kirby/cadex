# Test harness Tk runner removal audit

Verified against source: 2026-09-07

[Cadex-new] ADR-230, source baseline `c8d99e61`. This audit qualifies only
`src/Mod/Test/unittestgui.py` for a separate copy/install-disable commit,
then a source-delete commit. No runtime or inherited file changes here.

## Boundary and dependency evidence

The 38-file Test tree is not a whole-tree removal candidate. With
`BUILD_TEST=ON`, `src/Main/CMakeLists.txt` makes FreeCADMainCmd depend on
TestSources. `src/App/FreeCADTest.py` imports TestApp and calls
RunConfiguredTextTest; Application.cpp selects TestApp.All/PrintAll.
Init.py registers eight headless test modules. Keep all of these, Test data,
TestSources, and the remaining GUI test files/resources outside this audit.

The selected file is a standalone 399-line / 15,021-byte Python-licensed
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
