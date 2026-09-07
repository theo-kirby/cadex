# Start whole-tree removal audit

Verified against source: 2026-09-07

[Cadex-new] Audit at `6761304e`, after the Help sequence (ADR-216, ADR-217,
ADR-218, [HELP-AUDIT.md](HELP-AUDIT.md)) completed the first engine-side
whole-tree removal. **Start qualifies for a separate disable commit under
ADR-219.** Documentation only: no build, configure, install, stage or test
execution was performed for this audit. Deletion is conditional on the disable
commit's verification. Test is not qualified by this audit; Assembly, Measure
and retained Qt are outside it.

## What the tree is

`git ls-files src/Mod/Start` is 23 files, 82,210 bytes: `CMakeLists.txt`,
`Init.py`, `InitGui.py`, `StartMigrator.py`, `README.md`, `StartGlobal.h` and
an `App/` directory of one CMake file and sixteen C++ sources and headers.
`tests/src/Mod/Start` adds 4 files (2,986 bytes): two CMake files and two
gtest sources. That is 27 tracked files in total. This is source volume, not
fork delta.

Unlike Help, **Start has a native App target**: `App/CMakeLists.txt` builds
`Start` as a shared library that is also the Python extension module
`Start.so` (`set_python_prefix_suffix`), linking only `FreeCADApp`, with six
`Q_OBJECT` headers moc'd against QtCore. The `Gui/` half (70 files) was
deleted under ADR-214; the tracked `CMakeLists.txt` diff against the import
commit is exactly the removal of its `BUILD_GUI` block.

## Dependency boundary

| Consumer | Source evidence and disposition |
|---|---|
| Build entry | `src/Mod/CMakeLists.txt:46` enters Start on `BUILD_START` alone. `InitializeFreeCADBuildOptions.cmake:166` declares it `option(... ON)`; `PrintFinalReport.cmake:111` reports it. No other tracked `BUILD_START` assignment exists in `pixi.toml`, `package/`, `cMake/` or any preset. **Both existing Debug and Release caches are ON** with `BUILD_GUI` OFF. |
| App target | `add_library(Start SHARED ...)` with `Start_LIBS = FreeCADApp`; `install(TARGETS Start DESTINATION lib)`. In the release `build.ninja` the only link consumer of `Mod/Start/Start.so` is `Start_tests_run`. No tracked source outside `src/Mod/Start` and `tests/src/Mod/Start` names `Start::`, `humanReadableSize`, or any of the six model/source classes. `CheckInterModuleDependencies.cmake` has no Start line. Nothing in `src/App`, `src/Base` or `src/Main` links or loads it; `MainCmd` depends on `TestSources`, which is Test, not Start. |
| GSL | `src/Mod/Start/CMakeLists.txt:25-34` is the **only** tracked consumer of `src/3rdParty/GSL` (directory-scoped `include_directories`, or `find_package(Microsoft.GSL)` with a `SEND_ERROR` fallback), and `App/AppStart.cpp` holds the only `#include <gsl/...>` under `src/` outside Start. `pixi.toml:260` still checks the submodule out in `setup-engine`. After a Start delete the GSL submodule and that setup line become a separate follow-on candidate; this audit does not widen to it. |
| Scripts | `Start_Scripts` is `Init.py` only: copied to `Mod/Start` by `fc_target_copy_resource` and installed there. `Init.py` sets `System parameter:Modules/Start` `WorkBenchName`/`WorkBenchModule=Start.py`; **no `Start.py` exists** in the tree and no tracked code reads that group. `FreeCADInit.py` executes every `Mod/*/Init.py` at startup of the installed engine, so this runs on each `FreeCADCmd` start today and does nothing observable. `InitGui.py` and `StartMigrator.py` are tracked but in **no** CMake list since the ADR-214 diff removed the `BUILD_GUI` block; they are orphans. `README.md` describes the deleted `Gui/`. |
| Python callers | Tracked executable imports of `Start` or `StartGui`: only Start's own orphaned `InitGui.py`. Engine, CLI and `mesh_agent` have no tracked Start importer; `shell/` has no `Mod/Start`, `BUILD_START` or `StartMigrator` token. |
| Branding | `src/App/Branding.cpp:63` pushes `"StartWorkbench"` into the `branding.xml` key filter. That is an App-side configuration key name, not a consumer of this tree; retain it. |
| Tests | `tests/CMakeLists.txt:47` appends `Start_tests_run` to `TestExecutables` and `tests/src/Mod/CMakeLists.txt:28` enters `tests/src/Mod/Start`, **both gated on `BUILD_START`**. `Start_tests_run` links `GTest::gtest_main`, Python and `Start`. `FileUtilities.cpp` defines **11** `FileUtilitiesTest.humanReadableSize*` cases; `ThumbnailSource.cpp` defines a fixture and no test. The existing release CTest discovery (1,544 registrations, `/tmp/cadex-help-audit-ctest.json`) lists exactly those 11 under `Start_tests_run`; the other 9 "Start"-token names belong to `App_tests_run`/`Base_tests_run` (`MappedName…Startpos`, `ReaderTest.readNextStartElement`, …) and stay. **None of the 11 is in `build/ctest_baseline_failures.txt`**: they pass today, so a disable removes 11 passing registrations (1,544 → 1,533) and one test executable. That is the expected registration delta, to be compared before/after, not a regression. The four `tests/src/Mod/Start` files are unmodified since import and are not manifest entries. |
| Translation maintenance | `src/Tools/updatecrowdin.py:211-215` carries a `StartPage` row pointing at `Mod/Start/Gui/Resources/{translations,Start.qrc}`, both already deleted under ADR-214. Remove only this row in the later delete commit; the file is already a manifest entry with its notice (ADR-218). |
| Developer configuration | `.pre-commit-config.yaml:33` excludes `src/Mod/Start`; `contrib/.vscode/settings.json:47` excludes it from search. Remove at deletion; both are outside the manifest's scopes. |
| Payload | `package/engine/build_engine_payload.sh` `keep_mods` (line 108) omits Start, so `Mod/Start` is pruned. **But `install(TARGETS Start DESTINATION lib)` puts the extension in `lib/`, which the prune does not touch: the existing staged payload `build/engine/cadex-engine-0.0.0-macos-arm64/lib/Start.so` is present, 266,296 bytes.** The claim in `docs/FREECAD.md` and `docs/ROADMAP.md` that Start is "in no shipped payload" was true of `Mod/` only; it is corrected in this audit's commit. This is existing-payload evidence from the Help-delete staging, not a fresh build. The disable removes a shipped binary, which Help's did not. |
| Qt | Start's App sources include QtCore only (`QObject`, `QAbstractListModel`, `QThreadPool`, `QProcess`, `QStandardPaths`, …). The App layer keeps `Qt6Core`/`Qt6Xml` regardless, so the removal reduces no Qt obligation and must not be claimed to. |
| Headless nuance | Static searches cannot rule out arbitrary external or dynamic `import Start`; Cadex does not promise third-party FreeCAD workbench compatibility. The tree has no non-GUI API anyone calls (Help had `Help.show`; Start has file-card models with no caller). |

Search basis: tracked `git grep -n -E
'BUILD_START|Mod/Start|import Start|from Start|Start_rc|Start_SRCS|StartScripts|StartGlobal|StartMigrator|Start\\.py|StartWorkbench|Start_Start|libStart|Start\\.so|"Start"'`
outside `docs/`, `.hypergraph/`, `src/Mod/Start/` and `shell/` (then `shell/`
separately); a symbol search for `Start::` and the six class names; a
`Modules/Start` parameter-group search; source inspection of every file named
above; and generated Ninja, install-script and CTest-discovery inspection.
Exclude translation prose, historical docs and graph records when identifying
live consumers.

## Generated and installed state

Release: `build.ninja` has 211 lines with a Start token; `Mod/Start/Init.py`
copy, `Mod/Start/Start.so` link, `StartScripts` and `Start_tests_run` rules;
`src/Mod/cmake_install.cmake:87` and `tests/src/Mod/cmake_install.cmake:82`
both include the Start child install scripts; on disk `build/release/Mod/Start`
holds `Init.py` and `Start.so`, and `build/release/tests/` holds
`Start_tests_run` plus its three `Start_tests_run*.cmake` discovery files.
Debug: configured (199 Ninja lines, generated `src/Mod/Start`), nothing built.
The shared pixi install `.pixi/envs/default/Mod/Start` holds `Init.py` **plus
stale `InitGui.py`, `StartMigrator.py` and
`__pycache__/StartMigrator.cpython-311.pyc`** dated 2026-07-24, from before
the ADR-214 deletion of the `BUILD_GUI` block; and `lib/Start.so` (2026-09-07,
the Help-delete install). The staged payload has no `Mod/Start` and does have
`lib/Start.so`. No build, configure, cleanup, install or staging was performed
for this audit.

## Verdict: qualifies. Separate disable, then delete

**Smallest durable disable.** Replace the `option(BUILD_START ... ON)`
declaration with
`set(BUILD_START OFF CACHE BOOL "Build the retired FreeCAD start module" FORCE)`
in the already-manifested initializer, exactly as ADR-217 did for Help. This
normalizes fresh configurations, both existing ON caches and explicit
`-DBUILD_START=ON` requests to OFF; a default change alone would leave both
real caches ON. Because `tests/CMakeLists.txt` and `tests/src/Mod/CMakeLists.txt`
read the same variable, the forced-OFF also drops `Start_tests_run` with no
edit to either file. Keep the three gates, the report line and all 27 sources
for the disable commit. This is one manifest-covered file, six lines, no new
manifest entry.

**Disable verification**, all in the same unit before any doc claims it, on
macOS (report the platform limit):

1. Explicit `-DBUILD_START=ON` reconfigure over each existing Release and
   Debug cache: exit 0, `BUILD_START:BOOL=OFF` in the cache, 0 `Mod/Start`,
   `Start.so` and `Start_tests_run` rules in `build.ninja`, no Start include
   in `src/Mod/cmake_install.cmake` or `tests/src/Mod/cmake_install.cmake`,
   final report `BUILD_START: OFF`, no required App/Assembly/Test target lost.
2. Inventory and quarantine (CMake regeneration does not uninstall):
   `build/release/Mod/Start`, `build/release/tests/Start_tests_run` and its
   `Start_tests_run*.cmake` files, generated `build/{release,debug}/src/Mod/Start`
   and `tests/src/Mod/Start`, the shared install's `Mod/Start` (including the
   stale GUI-era scripts and bytecode) and `lib/Start.so`. Do not delete other
   "Start"-named files.
3. At most one release build, `install-release`, `stage-engine`; confirm no
   `Mod/Start` and **no `lib/Start.so`** installed or staged, and that Test
   still installs.
4. Installed `FreeCADCmd` probe from a script file (the `-c` string form
   crashed during the Help delete): `import Start` fails with `No module
   named`; `App.ParamGet("System parameter:Modules").HasGroup("Start")` is
   false on a fresh parameter set; Measure, MassProperties, Assembly,
   JointObject, UtilsAssembly, Part, PartDesign, Sketcher, Mesh, MeshPart and
   cadexd import; a 10 mm box has volume 1000.
5. Full engine pytest suite; both Cadex ctests (`-R '^Cadex'`, expect 4/4);
   serial inherited CTest with **1,533 registrations expected** (the 11
   `FileUtilitiesTest` names gone, nothing else), 0 failures outside
   `build/ctest_baseline_failures.txt`, skipped and disabled counts unchanged
   from the Help-delete run (3 and 7).
6. The packaged lifecycle/licensing gate against the freshly staged payload,
   including committed-HEAD manifest equality.

**Delete, only after that passing separate commit.** Remove `src/Mod/Start/`
(23 files) and `tests/src/Mod/Start/` (4 files); the `if(BUILD_START)` gates in
`src/Mod/CMakeLists.txt`, `tests/CMakeLists.txt` and `tests/src/Mod/CMakeLists.txt`;
the forced-OFF cache entry (a comment, as ADR-218 left for Help); the
`value(BUILD_START)` report line; the `StartPage` row in `updatecrowdin.py`; and
the two developer-configuration path entries. All six surviving files touched
are already manifest entries with notices, so the delete adds no manifest
entry; `src/Mod/Start/CMakeLists.txt` leaves the manifest because a deleted
file is not an M entry. Reaudit consumers with the search basis above,
regenerate both configurations, quarantine stale outputs, and repeat the same
verification. Do not widen to Test, the GSL submodule, Assembly, Measure or
retained Qt. Start's two commits count as **one** whole-tree removal; with
Help's, that is the two the criterion asks for.

## How whole-tree deletions should count against the fork-delta criterion

The manifest metric (`git diff --no-renames --numstat --diff-filter=M IMPORT
REV -- SCOPES`, minus each tree's `ours` paths, as in PHASE8-AUDIT.md) counts
**modified surviving inherited files** and their inserted/deleted lines. It
measures the merge-conflict surface, which is what the criterion is for. A
whole-tree deletion cannot lower it except by deleting a file that is itself
an M entry, and it usually raises the file count by a few lines in the gates
that reference the tree: Help's delete moved FreeCAD from 56 / 1,638 / 1,797
to 57 / 1,637 / 1,803 because `updatecrowdin.py` became an entry.

The same import commit and scopes give a second, equally mechanical number
that whole-tree deletions *do* move: the inherited files still present.
Recomputed at this audit for the FreeCAD tree:

| Rev | M files / inserted / deleted | D (whole files deleted) | A (added) | Inherited files remaining |
|---|---|---|---|---|
| import `c2ccddfb` | — | — | — | 12,749 |
| nt2 start `7dd3d045` | 47 / 1,804 / 1,907 | 5,472 | 10 | 7,287 |
| this audit `HEAD` | 57 / 1,637 / 1,803 | 9,282 | 1 | 3,468 |

(`git diff --no-renames --name-only --diff-filter=D|A c2ccddfb REV -- src/
cMake/ tests/ CMakeLists.txt` and `git ls-tree -r --name-only REV -- …`, each
minus the `ours` paths.) Blender is unchanged at 44 / 1,046 / 129.

Proposed convention, for the criterion to stay honest: report both numbers
every time. **Credit a whole-tree deletion only against "inherited files
remaining"**, one file each, never against the M metric; book the gate edits
it needs as their real line delta in the M metric. Read "smaller than at the
start of the run" as: inherited files remaining is down (7,287 → 3,468, met)
*and* the M metric's line totals are not up (1,804 / 1,907 → 1,637 / 1,803,
met), while the M file count is reported as is (47 → 57, not met by itself).
Deleting Start would move M to 56 files (its `CMakeLists.txt` entry leaves)
and inherited-remaining to 3,441. This is a proposal recorded here and in the
record node; it changes no test and no criterion text.

## Evidence and limits

Existing-payload and existing-build evidence only: the Help-delete staging's
`lib/Start.so`, the Help-audit CTest discovery JSON, the two `CMakeCache.txt`
files, both `build.ninja` files and the generated install scripts. No fresh
configure, build, install, stage, engine suite, CTest or packaged gate was
run for this audit; the disable's gates above are all future. macOS only.
