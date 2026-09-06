# Phase 8 deletion-readiness audit

Verified against source: 2026-09-07

[Cadex-new] Audit of [FreeCAD-inherited] source at
`d031bde033aca73242fa7a668f657fa15b16935f`. **Deletion requires its own verified unit.**
The original audit found release code consuming `src/Gui/MetaTypes.h` and
debug enabling GUI. The metatype prerequisite has since moved the declarations
to `src/App/MetaTypes.h`, preserving a forwarding Gui header and migrating all
18 retained includes (ADR-213). Debug disable is now complete: all presets
select OFF and the shared initializer rejects GUI-on requests. Deletion is
still a separate unit. Tables below retain the audit-revision findings and
measurements. Full L3 remains open.

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
`^\s*\d+ - (.*?) \(` from each report and compare the sets. Do not overwrite
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
