# Help whole-tree removal audit

Verified against source: 2026-09-07

[Cadex-new] Audit at `0e1497b1`, following the completed Measure shim
sequence. **Help qualifies for a separate disable commit under ADR-216.**
No build rule or runtime changes here; deletion is conditional on that
commit's verification. Start and Test are not qualified by this audit.

## Dependency boundary

`git ls-files src/Mod/Help` contains 85 files, 802,267 bytes: CMake,
Help.py, InitGui.py, default.css, dlgPreferencesHelp.ui, Help.qrc and 79
translation files. This is source volume, not payload savings or fork delta.
There is no App target, native library, Init.py or test in this directory.

| Consumer | Source evidence and disposition |
|---|---|
| Build entry | `src/Mod/CMakeLists.txt:6` enters Help on BUILD_HELP alone. `InitializeFreeCADBuildOptions.cmake:151` defaults it ON; `PrintFinalReport.cmake:101` reports it. No other tracked BUILD_HELP assignments or explicit preset/package overrides were found. Both existing Debug and Release caches are ON with BUILD_GUI OFF. |
| Target/copy/install | Help/CMakeLists.txt feeds four Help_SRCS into Help ALL, `fc_copy_sources` and INSTALL: InitGui.py, Help.py, default.css, dlgPreferencesHelp.ui. `cMake/FreeCadMacros.cmake` copies or symlinks each source to `Mod/Help`. No consumer target links against Help; it is a script/resource target. |
| Resources | Only BUILD_GUI enables PYSIDE_WRAP_RC and the Help_rc.py resource copy. Help.qrc references 40 QM entries (Swedish twice); the files stay source-only in the supported headless build. `Help.add_language_path` imports Help_rc and registers `:/translations`. Retained App translations and Qt are independent and must remain. |
| Python callers | Tracked executable imports of Help are confined to its InitGui.py. Help.py's import/show examples are docstring text. InitGui calls add_preferences_page and add_language_path, both importing FreeCADGui. Engine, CLI and mesh_agent have no tracked Help importer. |
| Headless nuance | Help.show has a real non-GUI branch printing retrieved Markdown/HTML. Its removal retires that unused inherited API too; Help is not literally GUI-only. FreeCADInit discovers module paths and executes Init.py/init/__init__.py, not InitGui.py. No required engine startup callback is supplied here. Static searches cannot rule out arbitrary external/dynamic imports; Cadex does not promise third-party FreeCAD workbench compatibility. |
| Other resources | Help.py loads default.css and dlgPreferencesHelp.ui from its own directory. Its help-browser icon is a retired GUI resource reference, not a retained App consumer of this tree. Lazy PySide/QtWebEngine, markdown and pypandoc imports do not justify changing dependencies elsewhere. |
| Translation maintenance | `src/Tools/updatecrowdin.py:140` includes Help in its translation/resource map. Its updater can write the QRC/QM resources independently of CMake. Remove only this Help row in the later delete commit; do not claim this tool has no consumer. The script also references previously deleted GUI trees: repairing or running its network workflow is outside this unit. |
| Developer configuration | `.pre-commit-config.yaml:18` excludes this directory; `contrib/.vscode/settings.json:29` includes it in a search exclusion. Remove these obsolete path entries at deletion, with inherited manifest/notices where required. They are not runtime dependencies. |
| Tests | Tracked Help-specific searches find no test consumer. Existing release CTest discovery contains 1,544 registrations, none with a Help token in its name, command or properties. Generic startup and lifecycle tests still matter. |
| Payload | `package/engine/build_engine_payload.sh:108` retains cadex, Part, PartDesign, Sketcher, Assembly, Mesh, MeshPart, Import, Material, Measure and Show. Help is already pruned; no payload saving is claimed. Preserve license collection, root NOTICE, THIRD_PARTY_LICENSES and retained QtCore/QtXml dependencies. |

Search basis: tracked `git grep -n -E
'BUILD_HELP|Mod/Help|import Help|from Help|Help_rc|Help\\.qrc|Help_SRCS|Help_QRC|Help\\.show|Help\\.get'`,
plus case-insensitive Help searches in build/preset/package/test/product trees,
source inspection of the named files, and generated Ninja/install inspection.
Exclude translation prose, historical docs and graph records when identifying
live consumers; they remain attribution/history rather than deletion targets.

## Generated and installed state

Both build trees register Help and the four `Mod/Help` copy outputs in Ninja.
Both generated parent install scripts enter `src/Mod/Help/cmake_install.cmake`;
the release child installs exactly those four source files. Debug has no
copied Help files; Release has all four. The shared pixi install has those
four **plus stale Help_rc.py and two Help/Help_rc Python 3.11 bytecode files**.
The existing `build/engine/cadex-engine-0.0.0-macos-arm64/Mod/Help` is absent.
No build, configure, cleanup, install or staging was performed for this audit.

## Separate disable, then delete

The smallest durable disable is replacing the ON option declaration with
`set(BUILD_HELP OFF CACHE BOOL "Build the retired FreeCAD help module" FORCE)`
in the already-manifested initializer, with a short ADR explanation. It
normalizes fresh configurations, existing ON caches and explicit ON requests
to OFF; a mere option default change does not. Keep the parent gate, report
line and all Help sources for this disable commit. This differs deliberately
from BUILD_GUI's rejection: existing supported headless caches already have
HELP ON and should continue to configure without manual repair.

The disable verification must cover fresh option semantics and both real
configurations, including explicit `-DBUILD_HELP=ON` over the stale caches.
Confirm OFF in both caches, no reachable Help target/copy/install rule, and
no required App/Assembly target lost. Inventory and quarantine obsolete
`build/{debug,release}/Mod/Help`, orphan generated `src/Mod/Help` build
subdirectories and the shared install's Mod/Help (including resource/bytecode).
Do not broadly delete similarly named Help or Qt files. CMake regeneration
does not uninstall stale files; absence of a parent install include matters
more than an orphan child script's text. Inspect regenerated compiler/Ninja
dependencies as well as files on disk.

Run at most one release build, the full engine pytest suite, both cadex ctests
and serial inherited CTest. Compare failure names against
`build/ctest_baseline_failures.txt` and the previous Measure-delete evidence
in PHASE8-AUDIT.md; compare CTest registration/commands/properties, skips and
disabled cases before/after. Preserve required Measure/MassProperties and
Assembly CommandCreateView/JointObject/Preferences/UtilsAssembly, and run a
native installed headless import/publication probe with Help absent. Complete
install and stage before the fresh packaged lifecycle/licensing gate. Check
manifest equality against committed HEAD again after committing. Report
platform limits; this audit inspects macOS only.

Only after that passing separate commit, delete `src/Mod/Help/` and remove
its parent gate, obsolete option/report line and the three external tool/config
entries above. Reaudit consumers, regenerate both configurations, quarantine
stale outputs and repeat the same verification. Keep attribution. Recompute
manifest membership and notices for each changed surviving inherited file;
whole deleted files are not M entries. Do not widen the change to Start, Test,
Measure App, required Assembly publishers or retained Qt. A successful Help
sequence counts as one whole-tree removal, not two because it has two commits.

## Disable landed

The disable commit is `a04ca822` (the forced-OFF cache entry, ledger and
ROADMAP lines) and its ADR-217 entry is `504b46bc`. Both landed without a
record node and without any gate output. The gates below ran two units later
(iteration 31, 2026-09-07) on macOS, against those commits unchanged; the
stale `build/{debug,release}/Mod/Help`, shared-install `Mod/Help` and
bytecode listed under "Generated and installed state" were **already absent**
when this unit began, so no quarantine was performed here and it is not known
which of the two unrecorded units removed them.

| Gate | Command | Result |
|---|---|---|
| Explicit ON over the Release cache | `pixi run sh -c 'CFLAGS= CXXFLAGS= cmake -S . -B build/release -DBUILD_HELP=ON'` | exit 0; `BUILD_HELP:BOOL=OFF` in the cache; 0 `Mod/Help` rules in `build.ninja`; no Help include in `src/Mod/cmake_install.cmake`; no `build/release/src/Mod/Help`; final report `BUILD_HELP: OFF` |
| Explicit ON over the Debug cache | same with `-B build/debug` | same: OFF, 0 rules, no install include, report OFF |
| Release build | `pixi run build-release` | exit 0, 690 Ninja steps |
| Install and stage | `pixi run install-release`; `pixi run stage-engine` | both exit 0; no `Mod/Help` in `.pixi/envs/default/Mod` or in `build/engine/cadex-engine-0.0.0-macos-arm64/Mod` (Start and Test still install; the payload prunes them as before) |
| Installed headless probe | `.pixi/envs/default/bin/FreeCADCmd -c` importing Help and the retained modules | `import Help` → `No module named 'Help'`; Measure, MassProperties, Part, Assembly, Sketcher, PartDesign, Mesh, MeshPart, Material import; no `Mod/Help` under the home path |
| Full engine suite | `pixi run test-engine` | **2,022 passed, 52 skipped** in 267.6 s, exit 0 |
| Cadex ctests | `pixi run ctest --test-dir build/release -R '^Cadex' --output-on-failure` | **4/4 passed** (CadexProjectRebuildDigest, CadexdLifecycle, CadexSubshapeEnumeration, CadexResponseSchemas), 18.4 s |
| Serial inherited CTest | `pixi run ctest --test-dir build/release -j 1` | 162 failed of 1,537 run (1,544 registered, 8 skipped). By name: **0 failures outside `build/ctest_baseline_failures.txt`**; 2 baseline names absent (`SpreadsheetRenameProperty.renameProperty`, `DlgVersionMigrator_Tests_run`), both binaries deleted under ADR-214 |
| Packaged lifecycle and licensing | `CADEX_ENGINE_ROOT=$PWD/build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest -q src/Mod/cadex/cadex_tests/test_licensing_compliance.py src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py` | **26 passed** in 18.1 s against the freshly staged payload, including committed-HEAD manifest equality |

Logs are local under `/tmp/cadex-help-disable-*.log`. Not run: a
fresh-cache configure (both real caches were exercised instead), and no
Linux or Windows configuration. Manifest-scoped M metrics at these commits
are FreeCAD 56 / 1,638 / 1,797 and Blender 44 / 1,046 / 129 — the disable
adds six lines to an already-manifested file and reduces nothing yet. The
delete commit remains a separate unit under "Separate disable, then delete".

## Evidence and limits

Existing-payload check, after Measure deletion was committed:

```sh
CADEX_ENGINE_ROOT="$PWD/build/engine/cadex-engine-0.0.0-macos-arm64" \
  pixi run python -m pytest -q \
  src/Mod/cadex/cadex_tests/test_licensing_compliance.py \
  src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py
pixi run ctest --test-dir build/release --show-only=json-v1
```

**26 passed in 14.48 s**, including committed-HEAD manifest equality.
CTest discovery exited 0; no tests were executed by discovery. Logs are local
`/tmp/cadex-help-audit-gates.log` and `/tmp/cadex-help-audit-ctest.json`.
This is existing-payload evidence, not a fresh disabled build. No full engine
suite or inherited CTest execution was needed for this documentation-only unit;
the required future gates above remain unexecuted.

Manifest-scoped metrics were recalculated with
`git diff --no-renames --numstat --diff-filter=M IMPORT REV -- SCOPES`,
excluding each manifest tree's `ours` paths, as in PHASE8-AUDIT.md:

| Tree | nt2 start `7dd3d045`: files / inserted / deleted | Audit HEAD |
|---|---|---|
| FreeCAD | 47 / 1,804 / 1,907 | 56 / 1,633 / 1,796 |
| Blender | 44 / 1,046 / 129 | 44 / 1,046 / 129 |

These are import-relative modified-file metrics, not an exhaustive unsquashed
upstream comparison. Documentation changes do not alter them. Broad fork-delta
reduction, two whole-tree removals and residual GUI-source closure remain open.
