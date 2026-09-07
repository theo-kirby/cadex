# Phase 8 deletion-readiness audit

Verified against source: 2026-09-07

[Cadex-new] Audit of [FreeCAD-inherited] source at
`d031bde033aca73242fa7a668f657fa15b16935f`, followed by the prerequisite and
deletion evidence below. The metatype contract now lives in `src/App/MetaTypes.h`
and all eighteen retained includes migrated (ADR-213). All presets select
headless builds and explicit GUI-on requests are rejected. **The thirteen
audited GUI directories are now deleted** (ADR-214); historical findings below
retain their audit-revision context. Broader GUI-lineage disposition and full
L3 remain open. See the final sections for deletion gates and the residual-source audit.

## Disable evidence and measured boundary

The actual Phase 7 C6b disable commit is
`d2c8bcc5abc962a7ecef32a99552fffdfaa49c84` (ADR-022). It set
`BUILD_GUI=OFF` in the conda-release preset and rattler package build, moved
LinguistTools outside the GUI dependency block, and guarded the Gui tests and
InventorBuilder Qt test. Its recorded gate was two passing cadex ctests and
162 inherited failures against a 164-failure environmental baseline. It did
**not** disable debug: `InitializeFreeCADBuildOptions.cmake` defaults GUI ON,
and `conda-debug` has no override.

Tracked files and working-file byte sizes at the audited revision (not `du`
allocation, and not the old 729-file estimate):

| Directory | Files | Bytes |
|---|---:|---:|
| src/Gui | 1,960 | 65,331,470 |
| src/Mod/Assembly/Gui | 96 | 3,918,211 |
| src/Mod/Import/Gui | 15 | 80,556 |
| src/Mod/Material/Gui | 123 | 2,750,837 |
| src/Mod/Measure/Gui | 76 | 1,061,995 |
| src/Mod/Mesh/Gui | 164 | 5,920,387 |
| src/Mod/MeshPart/Gui | 71 | 1,363,887 |
| src/Mod/Part/Gui | 310 | 17,425,559 |
| src/Mod/PartDesign/Gui | 283 | 13,527,229 |
| src/Mod/Sketcher/Gui | 487 | 24,281,893 |
| src/Mod/Start/Gui | 70 | 1,228,929 |
| src/Mod/Test/Gui | 59 | 311,854 |
| tests/src/Gui | 17 | 121,969 |
| **Total** | **3,731** | **137,324,776** |

Reproduce by `git ls-files src/Gui src/Mod tests/src/Gui`, retaining paths
under the first/last directory or whose fourth component is `Gui`, grouping
by those directory prefixes, and summing `Path(path).stat().st_size`.

## Dependencies and residual references

| Consumer | Finding and required treatment |
|---|---|
| `src/Mod/Material/App` | **Active release blocker.** Twelve files directly include `Gui/MetaTypes.h`: Array2DPyImp.cpp, Array3DPyImp.cpp, MaterialFilterOptionsPyImp.cpp, MaterialFilterPyImp.cpp, MaterialLibraryPyImp.cpp, MaterialLoader.cpp, MaterialPyImp.cpp, MaterialValue.cpp, MaterialValue.h, Materials.cpp, PropertyMaterial.cpp, PyVariants.h. |
| `tests/src/Mod/Material/App` | Six retained tests include the same header: TestMaterialCards.cpp, TestMaterialFilter.cpp, TestMaterialProperties.cpp, TestMaterialValue.cpp, TestMaterials.cpp, TestModelProperties.cpp. |
| `src/Gui/MetaTypes.h` | QtCore `Q_DECLARE_METATYPE` declarations over Base/App types; no widget or Coin implementation. Needs a retained App-level home, with includes migrated and upstream attribution preserved. Do not discard Qt wholesale: App translations still need LinguistTools, Material needs QtConcurrent, and Base/App retain QtCore functionality. |
| `src/CMakeLists.txt` | GUI directory and Linux XDGData are inside `BUILD_GUI`. Remove the deleted directory registration; do not unwrap it into an unconditional add. |
| Eleven `src/Mod/*/Gui` parents | All eleven directory registrations are GUI-guarded. Remove those registrations in the delete commit. Keep their App directories, script copying and headless install lists. Part and PartDesign also have guarded GUI resources; review whole guarded blocks, not just the directory line. |
| `tests/CMakeLists.txt` | Defines `setup_qt_test`, linking FreeCADGui, and conditionally registers Gui_tests_run. Delete the helper and GUI executable-list entry with their callers. |
| `tests/src/CMakeLists.txt`, `tests/src/Base/CMakeLists.txt` | Delete the Gui registration and guarded `setup_qt_test(InventorBuilder)` call. Its `tests/src/Base/InventorBuilder.cpp` is an orphan candidate in the same boundary; retain Base's other tests and source. All other helper callers are under tests/src/Gui. |
| `src/Main/CMakeLists.txt` | GUI executable (MainGui.cpp), FreeCADGuiPy.cpp shared module, TestGuiSources dependency, and Windows GUI portable launcher are guarded. Keep FreeCADMainCmd, GeometryWorker and the command-line portable launcher. MainGui.cpp and FreeCADGuiPy.cpp are outside the directory boundary; removing their retired targets/sources is needed before claiming literally no GUI source. |
| `src/Doc/CMakeLists.txt` | Doxygen input contains source/build src/Gui and its Icons path. Remove dead references even though release builds need not run Doxygen. |
| Build setup and packaging | Root CMake gates Coin, Shiboken/PySide and related setup on GUI. Retain the headless Qt components. `package/rattler-build/build.sh` already forces OFF. `package/engine/build_engine_payload.sh` keeps Assembly/Material and prunes GUI libraries; it must continue carrying the retained modules. `src/MacAppBundle` separately builds QuickLook on macOS/conda and has optional Homebrew bundle rules; it is not part of this directory deletion. |
| Python files outside Gui directories | Assembly commands are mixed App/GUI modules. Material unconditionally installs InitGui.py/MaterialEditor.py/TestMaterialsGui.py; Measure installs MassPropertiesGui.py; MeshPart installs InitGui.py; Help copies/installs GUI scripts without a Gui directory. These require separate dependency audits before removal. A directory deletion cannot honestly claim all GUI-lineage source is gone. |
| `test_engine_identity_contract.py` | The lowercase-preference test reads five src/Gui files unconditionally. Replace that obsolete branch with an absence assertion at deletion, preserving the engine preference check. Do not silently skip the test. |
| Modification ledger | Removed manifested files leave the manifest; newly changed inherited parents/consumers enter it with notices and ledger coverage. Do not hide new changes to make counts smaller. |

Reproducible static and compiler-dependency probes (no source deletion):

```sh
git show d2c8bcc5 -- CMakePresets.json cMake/FreeCAD_Helpers/SetupQt.cmake tests/src package/rattler-build/build.sh
rg -n 'setup_qt_test|BUILD_GUI|add_subdirectory\(Gui\)' tests src/CMakeLists.txt src/Mod/*/CMakeLists.txt
rg -n '#include.*Gui/' src/App src/Base src/Main src/Mod/*/App tests/src/Mod
rg -n 'src/Gui|FreeCADGui' src/Doc/CMakeLists.txt src/Main/CMakeLists.txt
pixi run ninja -C build/release -t deps | rg '/src/(Gui/|Mod/[^/]+/Gui/)' | sort -u
```

The last probe returned **only src/Gui/MetaTypes.h** in the existing release
object dependency database. In particular MaterialValue.cpp.o lists it as a
VALID dependency. This is direct build evidence, but not a clean rebuild or
proof about every optional configuration.

## Headless Assembly and exploded views

`src/Mod/Assembly/CMakeLists.txt` installs CommandCreateView.py,
JointObject.py, Preferences.py and UtilsAssembly.py outside `if(BUILD_GUI)`;
its App directory is also unconditional. Preserve these modules and the
Assembly payload keep-list entry.

The worker no longer imports CommandCreateView (ADR-197), but
`CadexScriptedDomainPublication._configure_assembly_exploded_view` imports it
and instantiates **ExplodedView** and **ExplodedViewStep**, native App proxy
objects. CommandCreateView imports UtilsAssembly and Preferences; PySide and
pivy imports have headless fallbacks, and FreeCADGui import is guarded by
App.GuiUp. Preferences loads FreeCADGui only inside its GUI constructor.
JointObject has equivalent guards and supplies native joint publication.
Neither a command-like filename nor a view-provider class makes the whole
module removable. No replacement publisher is a prerequisite to deleting the
listed directories. Packaged lifecycle tests exercise both joint solving and
exploded-view display/radial arithmetic without FreeCADGui.

## Smallest coherent next steps

1. **Prerequisite unit:** move the headless metatype contract to a retained
   App header (retain a forwarding header for existing GUI consumers until
   deletion), migrate the 18 retained direct includes, and verify a release
   build and retained Material tests. This is a small justified conservative
   core edit, not a replacement engine. Record inherited moves/edits honestly.
2. **Complete disable unit:** make ordinary debug configure headless too and
   prevent GUI-on requests from reaching soon-to-be-deleted targets. Preserve
   release/package behavior, run debug configure and the release gates. The
   historic disable remains evidence but does not cover this debug behavior.
3. **Separate delete unit:** remove the 13 directory trees as one boundary,
   the InventorBuilder test and their build/test/doc references; remove retired
   Main GUI-only sources/targets if included in the declared boundary. Adapt
   the source-presence test and manifest, ADR and ROADMAP together. Do not
   partially delete src/Gui around the live header. Keep mixed Assembly
   Python modules, all headless App trees and shared command-line launchers.

Phase 8's directory deletion is thereby sized; its broad “no GUI source” exit
wording needs a separate, explicit disposition of mixed modules, not a false
checkbox. Phase 13b Start/Test/Help removal is not bundled into this audit or
assumed safe from absence in the shipping keep-list.

## Run-start inherited delta

Run nt2 starts at `7dd3d0458c61d300100177955267eca074d6865b`
(`ouroboros: start run nt2`), after the nt1 merge. Compare that revision with
`d031bde033aca73242fa7a668f657fa15b16935f`, not the earlier nt1 run.

| Metric | nt2 start | Audit HEAD |
|---|---:|---:|
| FreeCAD manifest entries / modified inherited files | 47 / 47 | 47 / 47 |
| FreeCAD modified-file inserted / deleted lines | 1,804 / 1,907 | 1,804 / 1,907 |
| Blender manifest entries / modified inherited files | 44 / 44 | 44 / 44 |
| Blender modified-file inserted / deleted lines | 1,046 / 129 | 1,046 / 129 |
| Blender entries marked premodified | 1 | 1 |

Both snapshots' manifest bytes are identical. Each line metric uses
`git diff --no-renames --numstat --diff-filter=M IMPORT REV -- SCOPES`, with
`import_commit`, `scopes` and exclusions (`ours`) read from that revision's
manifest. Sum numeric columns after excluding ours; there were no binary M
rows. The premodified entry is also modified relative to import here; do not
subtract it twice. The imports are the manifest's FreeCAD/Blender snapshots,
not unsquashed upstream histories. This matches the compliance guard's M-file
scope; deleted-file volume and new independent files are **not** this metric.
A future deletion may reduce M count while increasing deleted upstream lines;
report both interpretations. The fork-delta criterion stays open: **no reduction
from run start has been measured.**

## Validation and limits

Executed on the unmodified source baseline for this documentation-only audit:

- `pixi run configure`: exit 0; configuration 17.8 s, generation 0.8 s;
  build/debug cache confirms Debug and BUILD_GUI=ON. No GUI launched.
- `CADEX_ENGINE_ROOT="$PWD/build/engine/cadex-engine-0.0.0-macos-arm64" pixi run python -m pytest -q src/Mod/cadex/cadex_tests/test_licensing_compliance.py src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`:
  **26 passed in 16.22 s**, using the existing payload, not a newly staged one.

- `pixi run ctest --test-dir build/release -R '^(CadexProjectRebuildDigest|CadexdLifecycle)$' --output-on-failure`: **2/2 passed**, 2.19 s and 14.93 s (21.85 s total).

No source deletion, full build, full engine suite or full inherited ctest run
was performed. These baseline passes are not deletion-readiness proof.
For each later source-changing unit, the exact required gate sequence is:

```sh
pixi run configure
pixi run configure-release
pixi run build-release
pixi run python -m pytest src/Mod/cadex/cadex_tests
pixi run ctest --test-dir build/release -R '^(CadexProjectRebuildDigest|CadexdLifecycle)$' --output-on-failure
pixi run test-release > /tmp/cadex-phase8-ctest-full.log 2>&1
```

Compare failure **names**, not test numbers, to
`build/ctest_baseline_failures.txt`; report new failures, removed tests and
changed skip/disabled cases separately. Extract lines matching
`^\s*\d+ - (.*?) \(` **only after `The following tests FAILED:`** in
each report and compare the sets; the earlier “did not run” list contains
skips and disabled cases, not failures. Do not overwrite
the baseline. Both cadex ctests choose .pixi's FreeCADCmd first, so even a
release-directory ctest pass alone does not establish GUI independence.

For deletion and any payload/install/protocol change, follow the one release
build with `pixi run install-release` and `pixi run stage-engine`, then:

```sh
CADEX_ENGINE_ROOT="$PWD/build/engine/cadex-engine-0.0.0-macos-arm64" pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_licensing_compliance.py
```

Use the newly staged manifest directory if its version/platform name differs;
ensure no stale removed GUI files survive the old build/install tree. Inspect
Ninja dependencies again: no deleted source path may remain a live dependency.
Shell source is untouched; `pixi run gate` becomes mandatory if a later unit
touches shell. Export/check the hypergraph before each commit. No full L3,
Phase 8 deletion, or fork-delta completion is claimed by this audit.

## Metatype prerequisite verification (2026-09-07)

The declaration body in `App/MetaTypes.h` is byte-identical to the original
Gui header below `#pragma once`. All 18 retained direct includes migrated;
remaining GUI consumers use the forwarding header. No build/install rules
changed. The working-tree manifest comparison finds exactly 66 modified
inherited FreeCAD files, including all 19 edits in this unit.

- Debug configure, release configure and the single release build: exit 0.
  Debug remains GUI ON; release remains OFF.
- Retained Material/Model name-filter ctest: 30/30 passed in 7.22 s. The full
  inherited run below covers **all 35** Material executable registrations,
  all passed, including the five `TestModel` cases outside that narrow filter.
- Both cadex ctests: 2/2 passed in 17.09 s. As above, these prefer the installed
  engine and are not fresh-payload proof.
- Full inherited ctest: 162 failures / 1,537 enabled tests, 127.69 s, exit 8.
  Every failure name occurs in the 164-failure baseline. Baseline-only
  `DlgVersionMigrator_Tests_run` and `SpreadsheetRenameProperty.renameProperty`
  are absent from the current inventory; this unit changes no registrations.
  Three skipped and seven disabled tests are reported separately from failures;
  the historical failure-only baseline does not establish prior skip status.
- Full engine suite before commit: 2,015 passed, 52 skipped, one failure in
  316.58 s. The sole failure is `test_the_manifest_matches_git_reality`, whose
  import-to-HEAD comparison cannot see uncommitted source edits. The equivalent
  import-to-working-tree equality passes; rerun licensing after commit.
- Release Ninja dependency inspection: zero paths under the audited GUI
  directories; 190 occurrences of retained `src/App/MetaTypes.h`.

No installation or staging ran, since this unit changes neither contract.
No shell changes, GUI launch, second build, directory deletion or claim of
fork-delta reduction. Debug disable is the next separate unit.

## Complete disable verification (2026-09-07)

The common preset now supplies BUILD_GUI=OFF, migrating the existing debug
ON cache. The standalone rpm preset also selects OFF. A regression resolves
all nine public presets, including that non-inheriting rpm preset. The shared initializer defaults OFF and rejects truthy GUI requests
before dependency setup and target registration. GUI sources and build guards
remain for the separate deletion unit. QtCore, QtConcurrent and LinguistTools
remain configured in debug and release. No release install, payload or protocol
rule changed; no installation, staging or fresh packaged gate was required.

- `pixi run configure`, `pixi run configure-release` and the single
  `pixi run build-release`: exit 0. Caches confirm Debug/OFF and Release/OFF.
  Debug Ninja targets have no FreeCADGui library or Gui_tests_run target;
  release Ninja dependencies have zero audited GUI paths.
- `pixi run cmake --preset conda-macos-debug -B /tmp/cadex-disable-explicit-debug
  -DBUILD_GUI=ON` and the equivalent release command: expected exit 1 with
  `Cadex no longer supports BUILD_GUI=ON`. Reconfiguring that debug directory
  without a preset or override also rejects its stale ON cache, exit 1.
- The five CMake execution regressions cover unset/OFF and ON/TRUE/1. All
  pass. Executing the previous initializer with ON returns 0, confirming
  that the new rejection regression fails on the old behavior.
- Both cadex ctests: 2/2 passed in 22.18 s. Their installed-engine preference
  still applies; these do not establish fresh-payload independence.
- Working-tree manifest equality passes: 66 FreeCAD and 44 Blender files.
  The initializer already carries its notice and manifest entry; no manifest
  membership changed. No directory deletion or fork-delta reduction claimed.
- Full engine suite: **2,021 passed, 52 skipped in 261.86 s**. The subsequent
  standalone rpm preset correction and added preset regression were verified
  by the focused suite: **6 passed in 0.11 s**. The full run included the
  five CMake execution cases; the sixth test was added afterward. Linux,
  Windows and rpm toolchains were not configured on this macOS machine.
- Full inherited ctest: exit 8, **162 failures / 1,537 enabled tests** in
  128.98 s. No new failure names against the 164-failure baseline; the same
  baseline-only DlgVersionMigrator_Tests_run and
  SpreadsheetRenameProperty.renameProperty remain absent. Test inventory is
  unchanged from the metatype prerequisite. All 35 Material registrations
  pass. The three skipped and seven disabled cases listed in the prerequisite
  record are unchanged by name; no baseline file was overwritten.

Local logs use `/tmp/cadex-disable-*.log`. No GUI launched or shell files
changed. Next is the separately verified directory deletion; mixed Assembly
modules remain retained, and broad Phase 8/fork-delta completion stays open.

## Directory deletion verification (2026-09-07, ADR-214)

The separate deletion removes **3,731 files / 137,324,213 bytes** under the
thirteen audited directories. `src/Gui` accounts for 1,960 files / 65,330,907
bytes; its forwarding metatype header explains the difference from the original
audit. MainGui.cpp, FreeCADGuiPy.cpp and tests/src/Base/InventorBuilder.cpp add
three files / 51,916 bytes: **3,734 files / 137,376,129 bytes total**. Sizes are
tracked working-file bytes immediately before deletion, not filesystem allocation.

Retired registrations are removed from the eleven workbench parents, src/Main,
src, tests and Doxygen inputs. GUI-only script/resource lists in those parents
are removed with their guards, but their source files and all unconditional
install lists remain for the residual audit. Main's GUI resource configuration
and Windows GUI launcher target are retired; the shared command-line launcher
source remains. No Qt component or App tree is removed. Identity tests preserve
MainCmd/MainPy and lowercase preferences, replacing retired-source reads with
absence assertions. No shell source changes or GUI launches.

The modified-file metric, computed by the audit's import/scopes/ours method
with `--no-renames`, is distinct from removed volume:

| Metric | nt2 start 7dd3d045 | Deletion working tree |
|---|---:|---:|
| FreeCAD manifest entries / modified files | 47 / 47 | 56 / 56 |
| FreeCAD M-file inserted / deleted lines | 1,804 / 1,907 | 1,633 / 1,795 |
| Blender manifest entries / modified files | 44 / 44 | 44 / 44 |
| Blender M-file inserted / deleted lines | 1,046 / 129 | 1,046 / 129 |

FreeCAD's M-file line footprint falls by 283 lines, but file count rises by
nine; deleted upstream volume is not included in that metric. All 56 FreeCAD
files (40 src, 16 build/tests) have notices or the four retained ledger-only
entries. Working-tree equality and the notice checker pass. The broad
fork-delta claim remains open rather than choosing one favorable measure.

Debug/release configure and the **single release build** exit 0. Both caches
are GUI OFF. Release Ninja dependencies contain zero paths under the deleted
GUI boundary. Full engine suite: **2,021 passed, 52 skipped, one failure in
263.29 s**. The sole failure is the licensing manifest's import-to-HEAD check:
it cannot see this uncommitted deletion. Working-tree equality passes; the
committed check must be repeated after landing. Both cadex ctests pass in
16.74 s, still using their installed-engine preference.

Initial concurrent CTest discovery produced a malformed generated Start test
file and duplicate registrations. Removed the generated `*_tests.cmake` files
and regenerated serially: all **1,544 registrations and their properties are
identical** to the pre-deletion inventory, with no duplicates. The completed
inherited run reports **162 failures / 1,537 enabled tests**, exit 8, 128.33 s:
no new failure names against the 164-failure baseline. Baseline-only
DlgVersionMigrator_Tests_run and SpreadsheetRenameProperty.renameProperty
remain absent. The same three skips and seven disabled cases remain unchanged;
all 35 Material registrations pass. A summary initially counted those ten
non-runs as failures; the corrected failure-section extraction above avoids
that error. No baseline file was overwritten.

The residual-source audit is next. Main's retired resource template and shared
launcher GUI branch, mixed Assembly modules and the unconditional Material,
Measure, MeshPart, Test and Help Python lists are outside this deletion's source
boundary. Their presence prevents a literal “no GUI source” exit claim; this
unit does not weaken that exit criterion or assume these sources are removable.

A final serial inherited rerun confirms the same **162 failures / 1,537 enabled
tests in 123.54 s**, exit 8, with no new failure names. Before installation,
quarantined 38 stale local paths: the thirteen debug GUI build directories,
two generated Main GUI resources, 22 obsolete FreeCAD GUI libraries/bindings
and the old GUI executable. Release contained no GUI directory or live GUI
compiler dependency. `pixi run install-release` exits 0 without another build.

`pixi run stage-engine` exits 0 after the fresh install. This is the documented
2.4 GB local **stage-only** payload, with external library paths; it is not a
relocated distributable. The stage's rpath audit reports those external paths
as expected for this mode. Post-stage inspection finds no `*Gui.so`,
`*Gui.dylib`, MainGui.cpp, FreeCADGuiPy.cpp or InventorBuilder.cpp in the
payload; retained Assembly CommandCreateView, JointObject, Preferences and
UtilsAssembly are present. The release dependency database still contains
190 references to retained App/MetaTypes.h and zero deleted GUI paths.

Fresh packaged lifecycle/licensing run before commit: **25 passed, one failure
in 19.78 s**. Only the expected import-to-HEAD manifest comparison fails;
all lifecycle and payload-license checks pass, and import-to-working-tree
equality passes. Repeat the unchanged packaged command against committed HEAD
as the final check. Logs use `/tmp/cadex-delete-*.log`. Hypergraph export/check
runs before commit; no state graph or generated STATE/PLAN file is edited.


## Residual-source and install audit (2026-09-07, ADR-215)

Audit baseline: deletion commit `9f7c3268`. This is a dependency audit, not
another removal. The thirteen-directory criterion has build and staging evidence
above; the broader ROADMAP “no GUI source” exit remains unmet. Installation,
importability and execution are different claims: the release cache has
BUILD_GUI=OFF but BUILD_HELP/START/TEST/MEASURE=ON. `FreeCADInit.py`'s
`run_init` contract loads Init.py/init/__init__.py, not InitGui.py.

| Residual boundary | Exact consumers and disposition |
|---|---|
| `Assembly/CommandCreateView.py`, `JointObject.py`, `Preferences.py`, `UtilsAssembly.py` | **Required headlessly.** `CadexScriptedDomainPublication.py` imports JointObject at joint/ground publication and CommandCreateView at `_configure_assembly_exploded_view`, constructing ExplodedView and ExplodedViewStep. `cadex_assembly_worker.py` imports JointObject for solving and UtilsAssembly for connector frames and exploded-view centre/size calculations. CommandCreateView imports UtilsAssembly and Preferences; JointObject separately imports Preferences for `solveIfAllowed`. Keep those imports independent of its optional pivy/SoSwitchMarker block (ADR-060). GUI classes in these modules are not permission to delete their App proxies. |
| Assembly install/copy lists | `Assembly_Scripts` includes the four required modules plus command modules, AssemblyImport, SoSwitchMarker and TestAssemblyWorkbench; INSTALL and AssemblyTests/fc_copy_sources consume it unconditionally. AssemblyScripts separately copies the package and AssemblyTests files. SoSwitchMarker imports pivy directly; JointObject catches failure of that optional import. Command pruning needs a separate closure/test audit; no blanket removal of this list. |
| `Measure/MassPropertiesGui.py` | **Smallest candidate.** The only executable statement is `import MeasureGui`, whose implementation directory was deleted. `Measure_Scripts` feeds MeasureScripts, fc_target_copy_resource and INSTALL without a GUI guard. Tracked source search finds only that list and `Measure/App/MassPropertiesObject.h`'s `getViewProviderName()` string `MassPropertiesGui::ViewProviderMassPropertiesResult`; no retained Python importer. The string is a residual view-provider identity, not an import on the headless path. Preserve the App class and the other four Measure scripts. |
| Material scripts | `MaterialScripts_Files` unconditionally copies/installs InitGui.py, MaterialEditor.py and TestMaterialsGui.py beside Init.py/importFCMat.py/TestMaterialsApp.py. InitGui imports FreeCADGui, registers the MatGui workbench and appends TestMaterialsGui to the test list. MaterialEditor imports FreeCADGui/PySide and loads the retired materials-editor UI; tracked non-documentation references outside itself are its CMake registration. TestMaterialsGui imports `materialtests.TestMaterialDocument.DocumentTestCases`; its three tests guard their ViewObject assertions with GuiUp, so headless return is not GUI coverage. That test file has its own MaterialTest_Files install entry. Audit/remove the GUI registration cluster separately; retain App tests, materialtools, cards and model resources. |
| `MeshPart/InitGui.py` | Unconditional INSTALL beside Init.py; registers MeshPartWorkbench and imports the deleted MeshPartGui only in Initialize. No headless startup consumer; a separate single-file install-disable/delete candidate. Keep MeshPart/App and Init.py. |
| `Help/` | Parent `src/Mod/CMakeLists.txt` gates it on BUILD_HELP, **not** BUILD_GUI. Help_SRCS feeds Help ALL, fc_copy_sources and INSTALL for InitGui.py, Help.py, default.css and dlgPreferencesHelp.ui. Only resource compilation/copy is GUI-guarded. InitGui calls Help.add_preferences_page/add_language_path, which import FreeCADGui (the latter also Help_rc). Help.py has lazy Qt rendering paths. Tracked code import search finds InitGui and Help's own examples; no product-engine importer. Whole-tree disable still needs its own option/packaging audit; absence from payload is insufficient. |
| `Start/`, `Test/` | Start still builds App and copies/installs Init.py; deleted GUI script registrations leave other source behind. Test_SRCS still copies/installs GUI tests (GuiDocument, TestGui, unittestgui, visual/selection tests) alongside App tests. MainCmd still depends on TestSources when BUILD_TEST; TestGui imports TestApp. Neither whole tree can be deleted merely because the payload excludes it. Separate Phase 13b audits must preserve headless testing obligations. |
| Other retained workbench parents | Part still copies/installs AttachmentEditor (including its UI), BOPTools, CompoundTools and parttests; PartDesign still copies/installs Scripts, fcgear and fcsprocket (including fcsprocketdialog.py). Its WizardShaft list remains declared without a copy/install consumer. These mixed helper/test families need their own closure audits; headless geometry helpers are not GUI waste. Sketcher/Mesh/Import retain their App/script registrations. The deleted GUI-guarded registrations did not delete the source files they once listed. |
| `Main/` and other native lineage | freecad.rc.cmake has no tracked build consumer after deletion; freecadCmd.rc.cmake and cadexPortableLauncher.rc.cmake are still configured. CadexPortableLauncher.cpp has four CADEX_GUI_LAUNCHER branches but no remaining build definition of that macro; the WIN32 CadexCmdPortableLauncher target still consumes its command-line branch. Preserve that launcher; branch/template cleanup requires a separate unit and honest Windows validation limits. App view-provider strings/export macros, residual resources and MacAppBundle/QuickLook are outside the deleted directory boundary, not evidence of a remaining FreeCADGui binary or permission to remove QtCore. |

**Payload evidence.** The current stage contains Measure/MassPropertiesGui.py,
Material/{InitGui,MaterialEditor,TestMaterialsGui}.py, MeshPart/InitGui.py and
all four required Assembly modules. The release-generated
`src/Mod/{Measure,Material,MeshPart}/cmake_install.cmake` lists those GUI scripts;
this is active install evidence, not merely a stale source listing.
`package/engine/build_engine_payload.sh`'s keep_mods retains all four module
directories, pruning Help/Start/Test as whole directories. Those three are
absent in the inspected stage. Passing binary/payload-license gates therefore
does not imply absence of GUI Python.

**Next separate sequence.** Disable only MassPropertiesGui.py's membership in
Measure_Scripts, keeping its source until a later delete commit. Because all
three copy/target/install consumers share that list, one inherited CMake edit
covers them; it already has a manifest entry and modification notice. Verify
both configurations, one release build, full engine suite and inherited gates
with baseline comparison as prescribed above, then install/stage and run the
packaged gate. Quarantine stale copied/installed shim files and assert absence
in the fresh stage while retaining Measure App behavior and Assembly publication.
After that evidence, delete the shim in a separate verified commit. Preserve
MassPropertiesObject.h's App class/view-provider string in this bounded sequence;
its eventual disposition is still part of the broader GUI-source frontier.
Do not turn this into a Measure tree deletion or a publisher rewrite.

**Reproduction and limits.** Read the named CMake lists and import sites; use
`git grep -n MassPropertiesGui -- src tests cMake package` to reproduce the
shim's complete tracked consumer set. Search MaterialEditor/TestMaterialsGui,
`import Help`, freecad.rc.cmake and CADEX_GUI_LAUNCHER similarly, excluding
translation catalogs and documentation when interpreting code consumers.
Static searches do not prove absence of arbitrary external/dynamic imports;
Cadex does not promise general FreeCAD workbench compatibility.

Existing post-deletion packaged baseline rerun at committed HEAD:
`CADEX_ENGINE_ROOT="$PWD/build/engine/cadex-engine-0.0.0-macos-arm64" pixi run python -m pytest -q src/Mod/cadex/cadex_tests/test_licensing_compliance.py src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`
— **26 passed in 14.43 s**, including the HEAD manifest comparison deferred
by the previous record. Local log: `/tmp/cadex-residual-gates.log`.
No build, configure, install/stage, full engine suite, inherited ctest or GUI
run in this docs-only unit; this reuses the preceding deletion's staged payload.
No runtime behavior, inherited source, manifest or protocol changes. The
manifest-scoped fork-delta measurements above are unchanged and the broad
fork-delta claim remains open. Hypergraph export/check is required before landing.


## Measure shim install disabled (2026-09-07, ADR-215)

Removed only MassPropertiesGui.py from Measure_Scripts; the source remains for
its separate delete commit. Generated debug/release build.ninja and Measure
cmake_install.cmake no longer name it. The tracked consumer search now finds
only MassPropertiesObject.h's retained view-provider identity string. The four
other Measure scripts, App class and required Assembly modules are unchanged.
The CMake file already has its modification notice and manifest entry, so the
manifest membership remains 56 FreeCAD files and 44 Blender files; both
import-to-working-tree equality checks pass. Import-to-HEAD checks before
commit cannot see the changed CMake line, though membership is unchanged.

Verification (local logs `/tmp/cadex-measure-*.log`):

- `pixi run configure`, `configure-release`, and the single `build-release`
  all exit 0. Serial CTest discovery before/after gives identical 1,544 names
  and properties, with no duplicates. Compiler dependency inspection finds
  zero deleted GUI paths and 190 retained App/MetaTypes.h references.
- Full engine suite: **2,022 passed, 52 skipped in 273.31 s**, exit 0.
- Serial inherited CTest: **162 failures / 1,537 enabled tests in 140.29 s**,
  exit 8; no new failure names against the 164-failure baseline. Baseline-only
  DlgVersionMigrator_Tests_run and SpreadsheetRenameProperty.renameProperty
  remain absent. Three skips and seven disabled cases match the prior run.
  CadexProjectRebuildDigest, CadexdLifecycle, CadexSubshapeEnumeration and
  CadexResponseSchemas all pass (2.24, 15.71, 0.77 and 0.19 s). The initial
  lowercase `-R cadex` filter selected no tests; this full run supplies evidence.
- Quarantined three stale MassPropertiesGui.py copies from release/Mod,
  the installed pixi environment and the previous stage, then installed and
  completed staging (both exit 0). None remains in debug/release copies,
  the installed Measure directory or the fresh payload. All four Measure
  scripts and JointObject/CommandCreateView/Preferences/UtilsAssembly remain.
- Fresh packaged lifecycle/licensing: **26 passed in 17.46 s**. This is the
  2.4 GB local stage-only payload, with expected external rpath diagnostics,
  not a relocated distribution. A direct installed-engine script imports
  Measure/MassProperties and creates Measure::Result with GuiUp false
  (`MEASURE-APP-OK`). The same script in the stage also prints that marker,
  but reports a startup `No module named freecad` diagnostic; the native probe
  is not evidence of diagnostic-free standalone startup. An earlier one-line
  installed probe terminated without details; executing the explicit script
  passes. Packaged protocol tests above pass through their supported launch path.

No source file was deleted in this disable unit. Relative to nt2 start
7dd3d045, manifest-scoped FreeCAD M totals are now 56 files / 1,633 inserted /
1,796 deleted lines versus 47 / 1,804 / 1,907; Blender remains 44 / 1,046 / 129.
This does not close the broad fork-delta or two engine-tree-removals criteria.
Next is the separately verified shim source deletion. Other residual GUI
sources, external/dynamic import compatibility and unexercised platforms stay
outside this boundary. Repeat the packaged manifest comparison after commit;
no second build is required for that check.


## Disabled Measure shim deleted (2026-09-07, ADR-215)

Following disable commit `68b4bbf4` (postcommit packaged gate: 26 passed in
14.16 s), removed only MassPropertiesGui.py: **one file, 22 lines, 1,477 bytes**.
Its only executable statement imported the deleted MeasureGui. The retained
MassPropertiesObject.h view-provider identity, Measure App, four other Measure
scripts and four required Assembly publication modules are unchanged. No new
code or build rule is needed. This unmodified inherited file was not a manifest
entry; working-tree equality still holds at 56 FreeCAD and 44 Blender files.

Verification logs are local `/tmp/cadex-measure-delete-*`:

- Debug/release configurations and the single release build: exit 0; caches
  confirm Debug/OFF and Release/OFF. Generated build/install consumers do not
  name the shim. Ninja dependencies contain zero deleted GUI paths and 190
  retained App/MetaTypes.h references.
- Full engine pytest: **2,022 passed, 52 skipped in 259.65 s**.
- Both cadex ctests: **2/2 passed in 16.78 s** (digest 1.67 s, lifecycle
  15.09 s). These still prefer the installed engine.
- Serial inherited CTest: **162 failures / 1,537 enabled tests in 130.52 s**,
  exit 8. No new failure names against the 164-failure baseline. Baseline-only
  DlgVersionMigrator_Tests_run and SpreadsheetRenameProperty.renameProperty
  remain absent. Serial before/after discovery has identical 1,544 names,
  commands and properties, no duplicates; three skipped and seven disabled
  cases are unchanged from the disable run.

Manifest-scoped FreeCAD M totals remain **56 / 1,633 inserted / 1,796 deleted**
versus nt2 start `7dd3d045` **47 / 1,804 / 1,907**; Blender remains
**44 / 1,046 / 129**. The deleted file volume above is a separate metric.
The precommit HEAD-based check cannot see this deletion, so the committed
comparison must be rerun. No broad fork-delta reduction, two engine-tree
removals, whole Measure removal or no-GUI-source completion is claimed.

Fresh payload follow-through: `pixi run install-release` and completed
`pixi run stage-engine` both exit 0. No stale shim or bytecode remains in
release/Mod, the installed Measure directory or fresh stage; no quarantine
was needed after the preceding disable cleanup. All four Measure scripts and
JointObject/CommandCreateView/Preferences/UtilsAssembly remain. Fresh packaged
lifecycle/licensing: **26 passed in 19.44 s**. The native installed-engine
probe imports Measure/MassProperties and creates Measure::Result with GuiUp
false (`MEASURE-APP-OK`). The stage is 2.4 GB, local stage-only, with expected
external rpath diagnostics; this is not a relocated distribution claim.
No shell change, GUI launch or second build.

## MeshPart initializer disable boundary (2026-09-07, ADR-224)

[Cadex-new] This follow-up qualifies the single-file candidate from ADR-215
for a separate install-disable commit; it does not disable or delete it.

- `src/Mod/MeshPart/CMakeLists.txt` unconditionally installs `InitGui.py`
  beside `Init.py`. Its `add_subdirectory(App)` remains required.
- `App/CMakeLists.txt` builds MeshPart against Part and Mesh (and selected
  SMESH libraries), copies only `../Init.py` through `MeshPart_Scripts`, and
  installs the shared library separately. The generated release Ninja file
  has zero `MeshPart/InitGui.py` references; the generated parent install file
  still lists it. This is an install-only disable, unlike Measure's shared
  target/copy/install list.
- `InitGui.py` defines MeshPartWorkbench, uses GUI-injected Workbench/Gui,
  imports MeshPartGui and MeshPart in Initialize, and registers the workbench.
  No App functionality is defined there. `FreeCADInit.py` sets GuiUp to zero
  and its directory-module loader selects `Init.py`, not this initializer.
- Tracked source searches for MeshPartGui/MeshPartWorkbench find the shim,
  the unused export-macro definitions in MeshPartGlobal.h and two Doxygen
  macro lists. None is a headless importer of this initializer. Keep the
  header/macros outside this boundary. The engine's `cadex_mesh_worker.py`
  imports MeshPart and calls meshFromShape: preserve App, Init.py and the
  MeshPart payload directory, which the payload keep list explicitly retains.
- The source is 73 lines / 3,083 bytes, SHA256
  `841cc70796eb4fc598c26dc7eef66a51831355ee013f7acd350f935a27984903`.
  Both the configured install prefix's `Mod/MeshPart/InitGui.py` and the
  current staged payload's copy match that hash. Release/Mod has no copy.
  A future disable must quarantine the installed copy before staging; merely
  removing INSTALL does not remove files already installed. Inspect all active
  build/install/stage locations for stale copies rather than assuming these
  observations apply to another checkout.

**Next unit:** remove only the parent INSTALL list's InitGui.py entry, retain
its source, configure/build once with `pixi run build-release`, complete
install and stage after stale-copy cleanup, then verify generated install and
fresh payload absence while preserving Init.py and MeshPart's shared library.
Run the full engine suite, inherited ctest against its baseline and packaged
lifecycle/licensing gates. The parent CMake file already has its modification
notice and manifest entry; verify equality rather than adding membership.
Delete the 73-line source only in a later separately verified commit. That
source has no manifest entry today. Do not count this as a whole-tree removal
or closure of the broad no-GUI-source/fork-delta claims.

**Audit verification:** repository consumer searches, direct CMake/loader/worker
inspection, generated Ninja/install inspection and installed/staged byte hashes.
No source, build rule, install or staged payload changed; no full build or
runtime implementation gate is claimed. A packaged lifecycle/licensing baseline
was rerun against the existing payload; its result is recorded below. Static
searches do not prove arbitrary external imports; general FreeCAD GUI/workbench
compatibility is outside the product contract.

Existing-payload baseline command:
`CADEX_ENGINE_ROOT="$PWD/build/engine/cadex-engine-0.0.0-macos-arm64" pixi run python -m pytest -q src/Mod/cadex/cadex_tests/test_licensing_compliance.py src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`
— **26 passed in 13.30 s**, exit 0. No configure, build, install/stage, full
engine suite, inherited ctest or GUI launch in this audit-only unit.


## MeshPart initializer install disabled (2026-09-07, ADR-224)

Removed only InitGui.py from the parent INSTALL list; the 73-line source,
App subdirectory, Init.py, meshFromShape and export macros remain. The release
build regenerated its install script without the initializer. Quarantined the
two old installed/staged copies before installing and staging. No initializer
or bytecode remains under debug/release Mod/MeshPart, the installed environment
or fresh payload. Debug has no built App; release, install and stage retain
Init.py and MeshPart.so (installed libraries live under lib/).

One `pixi run build-release`, `install-release` and completed `stage-engine`
all exit 0. The build reports Release and BUILD_GUI=OFF. The payload is 2.4 GB,
local stage-only, with expected external rpath diagnostics. An explicit
installed FreeCADCmd script confirms GuiUp=false and tessellates a 10×20×30 box
through MeshPart.meshFromShape: `MESHPART-APP-OK facets=12`. A one-line `-c`
probe instead printed `Application unexpectedly terminated` despite exit 0;
this matches the prior Measure probe limitation and is not counted as passing.
Fresh packaged lifecycle/licensing: **26 passed in 18.07 s**, exit 0.

The inherited CMake file already carries its notice and manifest membership.
Working-tree manifest equality remains 56 FreeCAD and 44 Blender files after
applying the manifest's `ours` exclusions. No source deletion, whole-tree
removal, broad GUI-source completion or aggregate fork-delta reduction is claimed.
Local verification logs: `/tmp/cadex-meshpart-disable-*.log`.

Serial inherited CTest: **162 failures / 1,526 enabled tests in 141.81 s**,
exit 8, with no new failure names against the 164-failure baseline. The two
baseline-only names remain DlgVersionMigrator_Tests_run and
SpreadsheetRenameProperty.renameProperty. Three skipped and seven disabled
cases are unchanged. All four Cadex ctests pass: digest 2.02 s, lifecycle
15.33 s, subshape enumeration 0.75 s and response schemas 0.19 s.
Discovery now has 1,533 names, eleven fewer than the prior Measure log's
1,544: precisely FileUtilitiesTest.humanReadableSize* from the Start test source
already deleted by `14d47c31`. No names were added. The prior run's stale
Start test discovery is not a MeshPart regression; no test source changes here.

Full engine suite: **2,023 passed, 52 skipped in 265.63 s**, exit 0.
`git diff --check` passes. No shell changes, GUI launch or second full build.
Next: separately delete the retained initializer and repeat the required gates.


## MeshPart initializer source deleted (2026-09-07, ADR-224)

Following the verified install-disable commit `01e85a4e`, deleted only
`src/Mod/MeshPart/InitGui.py`: 73 lines / 3,083 bytes. App, Init.py,
meshFromShape and the MeshPartExport/MeshPartGuiExport definitions remain.
Source/test/package consumer searches find only the retained export macro
and its two Doxygen definitions. Generated MeshPart install instructions do
not name InitGui.py. Debug/release Mod, the install prefix and fresh stage
contain no initializer or bytecode. Debug has no built App; release, install
and stage retain Init.py and MeshPart.so.

Exactly one `pixi run build-release` completed with Release/BUILD_GUI=OFF;
`pixi run install-release` and `pixi run stage-engine` also exit 0. This is a
2.4 GB local stage-only payload, with expected external rpath diagnostics,
not a relocated distribution. An explicit installed FreeCADCmd script
imports FreeCAD, Part and MeshPart, asserts GuiUp=false, and tessellates a
10×20×30 box: `MESHPART-APP-OK facets=12`.

Fresh packaged lifecycle/licensing, with CADEX_ENGINE_ROOT set to the newly
completed stage: **26 passed in 18.15 s**, exit 0. Serial `pixi run test-release`:
**162 failures / 1,526 enabled tests in 142.70 s**, exit 8. Failure names are
all in the recorded 164-name baseline; the two absent names remain
DlgVersionMigrator_Tests_run and SpreadsheetRenameProperty.renameProperty.
Three skipped and seven disabled tests remain; all four Cadex tests pass
(2.41/15.60/0.72/0.19 s). An initial comparison incorrectly included skipped
and disabled summary entries as ten extra failures; filtering actual Failed
and SEGFAULT statuses confirms no additions. No baseline was overwritten.

Manifest equality remains 56 FreeCAD / 44 Blender files. Surviving-file
manifest-scoped M totals remain 1,637 inserted / 1,816 deleted (FreeCAD) and
1,046 / 129 (Blender). The initializer was unmodified against import and had
no manifest row; this deletion changes neither membership nor those M totals.
Report its 73 removed lines separately, not as surviving-file delta savings.
The existing parent CMake modification notice remains. Broader GUI-source,
whole-tree and full fork-delta claims remain open.

Logs are local `/tmp/cadex-meshpart-delete-{build,install,stage,engine,ctest,packaged,probe}.log`.
No shell changes, GUI launch or second full build.

The first full engine run overlapped staging: **2,022 passed, 52 skipped,
1 failed in 267.49 s**. The analysis payload guard saw `bin/ccx` during the
initial environment copy, before staging pruned binaries. The completed stage
contains no ccx. This was verification interference, not accepted payload
content: repeat the full suite after staging, and serialize these operations
in future units because the engine suite reads build/engine implicitly.

Full engine rerun after completed staging: **2,023 passed, 52 skipped in
251.30 s**, exit 0. `git diff --check` passes. Committed-HEAD manifest
equality is checked again after the source-delete commit.
