> **SUPERSEDED (2026-07-24).** Historical verification record from the VibeCAD era; it references the retired build123d/OpenSCAD engines and culled domains (CAM, FEM, TechDraw, …). Current runtime behavior is documented in `docs/XSCRIPT.md`; tests live in `src/Mod/cadex/cadex_tests/`. Kept for history only.

# Cadex Tool Runtime Verification

Updated: 2026-07-14

This record describes the current AI-native tool surface. It is not a speculative
manual checklist for deleted tools.

## Current Surface

- One unique registry definition per provider tool.
- One explicit AI-native tool pack per supported workbench.
- Exact equality between registered names and core/pack-owned names.
- No provider tool can create a document or switch workbenches.
- OpenSCAD exposes its focused source-modeling surface only when the human selects
  the OpenSCAD engine in PartDesign. It is not mixed with native PartDesign or
  build123d tools.
- The former OpenSCAD workbench registers no commands, file handlers, or UI. Its
  headless CSG conversion modules remain available to the isolated OpenSCAD engine.
- Part has no primitive-creation or arbitrary-placement escape hatch.
- PartDesign has no arbitrary property editor.
- Sketcher exposes native translation only; hand-built copy/mirror/offset/array modes
  were deleted.

## Automated Engine Verification

The scripted engines (build123d and OpenSCAD) are verified by an automated pytest
suite in `cadex_tests/` (run with `pytest src/Mod/cadex/cadex_tests`), not by
manual checklists. `test_engine_contracts.py` exercises both engines' contracts
directly, without a GUI session:

- Source policy: disallowed imports/calls/dunder access, size and syntax limits,
  NUL bytes, and unsafe project-relative paths are rejected with
  `SOURCE_POLICY_VIOLATION` and offending line numbers.
- Exporter escape hatch: build123d sources using `export_step`/`export_stl`/
  `export_brep`/`export_gltf`/`ExportSVG`/`ExportDXF`/`Mesher` or importing
  `build123d.exporters`/`exporters3d`/`mesher` are rejected at validation, and the
  sidecar worker independently denies those imports and strips the symbols from the
  `build123d` module and `Shape` class before user code runs. Its filtered
  `build123d.__all__` keeps normal `from build123d import *` modeling source valid
  without exposing the file-writing symbols.
- Source edits: non-unique or zero-match edits fail with structured edit errors;
  single-match edits re-validate the whole source.
- Revision integrity: content-addressed revision hashes are stable, ignore
  parameter key order, and change with every hashed field; artifacts whose
  recorded revision or source no longer match are rejected
  (`MODEL_ARTIFACT_REVISION_MISMATCH`).
- Failure-evidence contract (corrected): a failed sidecar execution returns a
  structured failure payload — `ok`/`failure_code`/`failure_stage`/`error`/
  `requested`/`observed`/`required_changes`/`retry_same_call` — instead of raising.
  build123d failures carry `observed.exception_evidence` (including the fillet
  diagnostic ladder's per-component working radii in `required_changes`);
  OpenSCAD compile failures carry parsed `observed.diagnostics` with
  severity/file/line. A runner that cannot start or produces no result returns
  `RUNNER_START_FAILED`/a structured failure rather than an exception.
- Transactional parity: both engines' accept and delete paths run inside FreeCAD
  document transactions; stub-document tests assert open→commit ordering on
  success and open→abort with no orphaned objects on failure, and recompute
  errors during accept raise structured commit failures.
- Display contract: accepted bodies/features are set to Shaded in GUI sessions,
  commits succeed headlessly when `ViewObject` is `None`, and display modes are
  restored on document reload for both engines.
- Output identity: OpenSCAD solids keep their accepted output keys across edits
  when geometrically unchanged, new solids receive fresh never-recycled keys, and
  removed solids' keys are not reassigned.
- Resource budgets: timeout and memory budgets come from preferences
  (`ScriptedTimeoutSeconds`/`ScriptedMemoryLimitMB`, defaults 300 s / 6144 MB) with
  explicit-override support; a parent-side watchdog terminates workers exceeding
  the memory budget on POSIX and Windows and returns `MEMORY_LIMIT_EXCEEDED` with
  observed usage.

Guardrail tests (`test_tool_surface_guardrails.py`) additionally verify that the
build123d/OpenSCAD engine tools are surfaced (no orphans) and that their write
tools carry document-transaction markers.

## Verified In This Build

- The automated engine suite above passes in full, and
  `ruff check --select F,E9` is clean across `CadexBuild123d.py`,
  `CadexOpenSCAD.py`, `build123d_worker.py`, and `openscad_freecad_worker.py`.
- Every tool module imports and every JSON Schema validates.
- Registry, pack, handler signature, duplicate, orphan, dangling-name, and workbench
  ownership audits pass.
- Provider failures use the common structured envelope. Schema branch errors,
  inactive-surface failures, edit-state failures, cancellation, and question UI
  failures all reach the same bounded trace path.
- Document-bound provider tools wait until `Document.Recomputing` is false. Native
  transactions and direct OpenSCAD/build123d commits independently reject a write
  if recompute becomes active before mutation begins.
- Bounded PartDesign distance measurement runs in the isolated
  `CadexGeometryWorker`, with a hard process deadline and cancellation. Exact BREP
  and exact triangle-BVH smoke cases both return the expected 5.0 mm distance.
- Accepted OpenSCAD revisions persist per-output BREP artifacts and source meshes;
  faceted outputs also persist per-component STL artifacts for measurement without
  reconstructing OCC topology in the UI process.
- Cadex viewport capture reads one current framebuffer and does not run nested Qt
  event processing or invoke the offscreen save-image render path.
- FreeCAD exposes generation-scoped recompute diagnostics through
  `Document.getRecomputeDiagnostics()`.
- A live invalid PartDesign fillet reports `BREP_FILLET_FAILED`, object
  `BadFillet`, property `Base`, and subelement `Edge99`.
- Sketcher live probes pass for native profile/FaceMaker diagnostics,
  non-mutating constraint feasibility, and geometry/constraint mutation maps.
- PartDesign Hole catalog and transform occurrence/child diagnostics are native and
  queryable.
- TechDraw projected-element/source mappings and Mesh defect counts are native and
  queryable.
- Assembly solver diagnostics are native and queryable.
- Gmsh and CalculiX use asynchronous cancellable process operations with operation
  IDs and structured process/result state.
- CAM face, outside-profile, and through-drilling chains generate nonempty paths and
  native stock/collision results.
- Exact CAM circular sweeps produce valid single solids for ball-end, chamfer, and
  V-bit tools; no chord-discretization path remains.
- Python compilation and `git diff --check` pass.
- OpenSCAD source revisions include the main file and every project-local
  `include`/`use` dependency. Accept and Revert operate on that complete graph.
- OpenSCAD exact CSG conversion and explicitly selected faceted conversion report
  their fidelity and diagnostics instead of silently substituting one path for the
  other.
- Packaged OpenSCAD renders a real STL in the isolated runtime smoke test, with
  bundled BOSL2 and MCAD libraries available through the project library path.
- Targeted App, Part, PartDesign, Sketcher, CAM, PathSimulator, and Cadex builds
  pass.
- The complete incremental build passes, including all application, workbench, and
  native-test targets.

## Environment-Dependent Checks

These are external-state checks, not alternate code paths:

- A real Gmsh installation is required to complete a production volume mesh.
  Missing Gmsh must fail before a mesh object is claimed complete.
- A real CalculiX installation is required to complete a solve. Missing CalculiX
  must fail before a solve is claimed started.
- Holder and fixture collision checks are unavailable when the CAM job contains no
  holder or fixture geometry; the result reports each unavailable check explicitly.
- Screenshot capture and panel rendering require a GUI process and should be checked
  in the normal Cadex application after visual changes.
- Machine postprocessing remains a human-controlled CAM export action and is not a
  provider tool.

## Release Gate

Before a release, require:

1. A complete incremental build with no errors.
2. Clean FreeCADCmd startup and Cadex registry initialization.
3. The live Sketcher, recompute-diagnostic, and exact CAM sweep probes above.
4. GUI startup without Cadex Python errors.
5. Provider SDK/keyring smoke tests inside each packaged artifact.
