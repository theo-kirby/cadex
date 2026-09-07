# Surviving FreeCAD diff audit

Verified against source: 2026-09-07

[Cadex-new] ADR-227; audit baseline `870150b8`, after the Material and Main
subsets. The subsequent implementation removes only the four-line Preferences
import guard in `src/Mod/Assembly/JointObject.py:79`, replacing it with `import Preferences`.
Its surrounding explanation, all Qt/Coin guards, and Preferences.py remain intact.

## Measurement and finite scope

Use each tree's `import_commit`, `scopes` and `ours` from
`docs/inherited-modifications.json`. Run `git diff --numstat --diff-filter=M
<import> <ref> -- <scopes>`, excluding `ours` prefixes. Count inherited files
remaining by intersecting `git ls-tree -r --name-only` paths at import and ref,
with the same exclusions. This counts tracked symlinks without following them.
Git warned that exhaustive rename detection was skipped; these are the same
manifest-scoped M measurements as the existing ledger, not a rename audit.

| Tree / revision | M files | Inserted | Deleted | Inherited remaining |
|---|---:|---:|---:|---:|
| FreeCAD nt2 start `7dd3d045` | 47 | 1804 | 1907 | 7277 |
| FreeCAD audit HEAD | 56 | 1637 | 1819 | 3434 |
| FreeCAD implemented guard removal | 56 | 1634 | 1819 | 3434 |
| Blender start, audit and implementation | 44 | 1046 | 129 | 19052 |

Documentation audit delta: zero. Implementation delta: 0 M files, -3 inserted,
0 deleted, 0 inherited remaining. JointObject alone changes from 42/5 to
39/5 inserted/deleted. Its ledger-only notice remains valid; manifest membership
is unchanged. Neither the broader fork-delta nor GUI-source criterion closes.

## Selected boundary and consumers

`Preferences.py` imports only FreeCAD at module scope; its FreeCADGui import
is deferred to PreferencesPage construction. JointObject already imports
FreeCAD before this guard. Assembly/CMakeLists.txt installs both files in the
same Assembly_Scripts list. `cadex_assembly_worker.py` imports JointObject in
both the assembly and dynamics preparation paths (lines 1271 and 5336).
JointObject.solveIfAllowed calls `Preferences.preferences()` unconditionally
for assemblies; assigning None offers no functioning fallback. Joint creation
calls solveIfAllowed when deriving connector frames. The GUI-only color lookup
also requires Preferences; it does not make the module optional.

Removing the guard restores the upstream unconditional-import behavior while
retaining the headless fix in Preferences.py. In a damaged installation a
missing Preferences module will fail at import instead of later with an
AttributeError. That is the only intended error-path change. No retired
feature returns and no supported feature is disabled; a separate source-delete
unit is unnecessary for these three redundant wrapper lines.

## Executable retained-behavior check

The audit ran `/tmp/cadex-50-probe.py` with `pixi run FreeCADCmd`, exit 0.
The script loaded current source and the proposed replacement into separate
module namespaces without changing a tracked file. It installed a MetaPathFinder
that raises ImportError for FreeCADGui, PySide, PySide2, PySide6 and pivy,
asserted GuiUp=false, Preferences present and coin=None, then exercised
solveIfAllowed against a recorder with Type='Assembly'. With
SolveInJointCreation=true it recorded `[False, True]` for the default and
storePrev=true calls; with the preference false it recorded no further call.
It restored the prior preference in a finally block. Both versions passed; the combined run printed `AUDIT50 PASS`. This is an import/dispatch probe,
not an actual mechanism solve or a newly installed payload.

To reproduce, use the following source substitution in an isolated namespace,
with source Assembly first on sys.path, inside the same FreeCADCmd probe:

```python
guard = 'try:\n    import Preferences\nexcept ImportError:\n    Preferences = None\n'
assert source.count(guard) == 1
candidate = source.replace(guard, 'import Preferences\n')
exec(compile(candidate, str(path), 'exec'), module.__dict__)
```

Implementation must rerun that check on tracked source, run the full engine
pytest suite, install/stage via the documented engine workflow (at most one
full build), and run fresh packaged lifecycle/licensing tests. Include a real
assembly/joint regression run; compare inherited CTest failures with
`build/ctest_baseline_failures.txt`. Verify the committed-HEAD manifest and
actual numstat, since an uncommitted diff is invisible to its equality test.
Do not let inherited formatting expand the file: JointObject is already
ledger-only because of the recorded formatter fight. If mandatory formatting
would widen the change, stop and record the blocker; no formatter-policy change
is qualified by this audit.

## Exclusions and inventory

The large TestPartApp difference is predominantly formatting: an AST comparison
matches HEAD exactly after removing just the TestPartMirror import and
testIssue2671/testIssue2876 methods from import-era source. Restoring
it wholesale would resurrect Spreadsheet tests. Restoring only formatting
would conflict with the repository's Black 26.5.1, line-length 100 configuration;
no formatter exception or whole-file rewrite is selected. App/Base behavior,
Qt build tools, active geometry extensions and retirement registrations remain
required. Restoring references to deleted modules merely improves a metric.
Trimming explanatory comments is not selected as useful product work.
Windows launcher arms remain deferred to an explicit bet and Windows validation.
Completed Material/Main deletions and motor searches are excluded.

All 56 manifest entries were inspected; categories below give the disposition.
`retirement` means restore would reintroduce removed modules, tests or GUI
registration; `required` means active behavior or build support; `candidate`
is the sole boundary above.

| File | + / - | Disposition |
|---|---:|---|
| `CMakeLists.txt` | 1 / 10 | retirement |
| `cMake/FindPySide6.cmake` | 1 / 3 | retirement |
| `cMake/FreeCAD_Helpers/CheckInterModuleDependencies.cmake` | 2 / 13 | retirement |
| `cMake/FreeCAD_Helpers/InitializeFreeCADBuildOptions.cmake` | 12 / 29 | retirement |
| `cMake/FreeCAD_Helpers/PrintFinalReport.cmake` | 1 / 21 | retirement |
| `cMake/FreeCAD_Helpers/SetupQt.cmake` | 6 / 2 | required: headless LinguistTools |
| `src/App/ApplicationDirectories.cpp` | 7 / 2 | required: 0.x config paths |
| `src/Base/Interpreter.cpp` | 4 / 4 | required: Cadex identity |
| `src/CMakeLists.txt` | 1 / 6 | retirement |
| `src/Doc/CMakeLists.txt` | 1 / 3 | retirement |
| `src/Main/CMakeLists.txt` | 1 / 105 | retirement |
| `src/Mod/Assembly/App/AppAssembly.cpp` | 1 / 6 | retirement |
| `src/Mod/Assembly/App/CMakeLists.txt` | 1 / 11 | retirement |
| `src/Mod/Assembly/CMakeLists.txt` | 1 / 7 | retirement |
| `src/Mod/Assembly/CommandCreateView.py` | 22 / 2 | required: headless import |
| `src/Mod/Assembly/InitGui.py` | 4 / 5 | retirement |
| `src/Mod/Assembly/JointObject.py` | 42 / 5 | candidate: Preferences guard only |
| `src/Mod/Assembly/Preferences.py` | 10 / 1 | required: headless import |
| `src/Mod/Assembly/UtilsAssembly.py` | 1 / 14 | retirement |
| `src/Mod/CMakeLists.txt` | 1 / 99 | retirement |
| `src/Mod/Import/CMakeLists.txt` | 1 / 7 | retirement |
| `src/Mod/Material/App/Array2DPyImp.cpp` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/App/Array3DPyImp.cpp` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/App/MaterialFilterOptionsPyImp.cpp` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/App/MaterialFilterPyImp.cpp` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/App/MaterialLibraryPyImp.cpp` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/App/MaterialLoader.cpp` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/App/MaterialPyImp.cpp` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/App/MaterialValue.cpp` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/App/MaterialValue.h` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/App/Materials.cpp` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/App/PropertyMaterial.cpp` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/App/PyVariants.h` | 2 / 1 | required: App metatypes |
| `src/Mod/Material/CMakeLists.txt` | 1 / 6 | retirement |
| `src/Mod/Measure/CMakeLists.txt` | 1 / 5 | retirement |
| `src/Mod/Mesh/CMakeLists.txt` | 1 / 9 | retirement |
| `src/Mod/MeshPart/CMakeLists.txt` | 1 / 4 | retirement |
| `src/Mod/Part/App/BRepOffsetAPI_MakePipeShell.pyi` | 19 / 0 | required: sweep law / per-edge fillet |
| `src/Mod/Part/App/BRepOffsetAPI_MakePipeShellPyImp.cpp` | 66 / 0 | required: sweep law / per-edge fillet |
| `src/Mod/Part/App/TopoShapePyImp.cpp` | 70 / 0 | required: sweep law / per-edge fillet |
| `src/Mod/Part/CMakeLists.txt` | 1 / 18 | retirement |
| `src/Mod/Part/TestPartApp.py` | 1247 / 1292 | formatting plus retirement; excluded |
| `src/Mod/PartDesign/CMakeLists.txt` | 1 / 20 | retirement |
| `src/Mod/Sketcher/CMakeLists.txt` | 1 / 16 | retirement |
| `src/Mod/Test/CMakeLists.txt` | 1 / 4 | retirement |
| `src/Tools/updatecrowdin.py` | 1 / 6 | retirement |
| `tests/CMakeLists.txt` | 66 / 52 | retirement plus required Cadex gates |
| `tests/src/Base/CMakeLists.txt` | 1 / 1 | retirement |
| `tests/src/CMakeLists.txt` | 1 / 1 | retirement |
| `tests/src/Mod/CMakeLists.txt` | 1 / 12 | retirement |
| `tests/src/Mod/Material/App/TestMaterialCards.cpp` | 2 / 1 | required: App metatypes |
| `tests/src/Mod/Material/App/TestMaterialFilter.cpp` | 2 / 1 | required: App metatypes |
| `tests/src/Mod/Material/App/TestMaterialProperties.cpp` | 2 / 1 | required: App metatypes |
| `tests/src/Mod/Material/App/TestMaterialValue.cpp` | 2 / 1 | required: App metatypes |
| `tests/src/Mod/Material/App/TestMaterials.cpp` | 2 / 1 | required: App metatypes |
| `tests/src/Mod/Material/App/TestModelProperties.cpp` | 2 / 1 | required: App metatypes |

## Verification and next unit

Existing-payload command:
`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python
-m pytest -q src/Mod/cadex/cadex_tests/test_licensing_compliance.py
src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`: **26 passed in 14.19 s**,
exit 0. Local output: `/tmp/cadex-50-packaged.log`; import/dispatch output:
`/tmp/cadex-50-probe.log`. No full build, install/stage, full engine suite,
full inherited CTest or GUI execution in this documentation-only audit.
The qualified guard removal is implemented. Verification follows below; other
guards, comments and GUI classes are unchanged.

## Implementation verification (2026-09-07)

Only the qualified Preferences guard changed in inherited code. Repeated the
probe above on tracked source (without the candidate substitution), then on
staged Assembly modules, both under `pixi run FreeCADCmd`: GUI imports denied,
Preferences present, coin=None, solver calls `[False, True]` with no further
call when disabled. Both exited 0; this probe uses the installed FreeCADCmd,
while the lifecycle gate below runs the staged engine itself.

`pixi run build-engine` completed one release build plus install, and
`pixi run stage-engine` completed. Source and staged JointObject.py compare
byte-for-byte equal. Stage-only reports external library paths by design;
this is local verification, not a relocatable release. The same packaged
command as above on this **fresh** payload passed **26 tests in 18.67 s**,
including `test_cadexd_solves_a_jointed_assembly` and simulation/rollout cases.

`pixi run test-release`: **162 failures out of 1526 run**, 148.93 s, exit 8.
Comparing failure names (including SEGFAULT entries, excluding disabled/skipped
lists) against `build/ctest_baseline_failures.txt`: **zero new failures**;
162 of 164 baseline names remain. The already-retired DlgVersionMigrator and
SpreadsheetRenameProperty cases are absent; this change did not fix them.

Local logs: `/tmp/cadex-51-{probe,staged-probe,build,stage,packaged,ctest}.log`
and `/tmp/cadex-51-ctest-comparison.txt`. No shell or GUI run, Windows check,
formatter-policy change or further reduction was attempted. No installed
pre-commit hook requires a broader formatting change. Manifest membership and
its JointObject ledger-only notice remain accurate; the table separates actual
surviving M savings from unchanged inherited-file counts.

Full source gate: `pixi run python -m pytest -q src/Mod/cadex/cadex_tests`
passed **2023 tests, 52 skipped in 272.43 s**, exit 0; output is in
`/tmp/cadex-51-engine.log`. Skips are not claimed as verification.
