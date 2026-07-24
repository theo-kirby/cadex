# ARCHITECTURE.md — What Exists Today

Verified against source: 2026-07-24

This document describes the code as it **is**, not as it will be. Targets live
in `docs/VISION.md`, `docs/XSCRIPT.md` (direction section),
`docs/INTEGRATION.md`, and `docs/ROADMAP.md`.

Provenance tags: `[FreeCAD-inherited]` upstream FreeCAD code we build on;
`[VibeCAD-era]` built during the VibeCAD phase and still current;
`[Cadex-new]` added or reshaped since the cadex import.

## 1. The one-paragraph picture

Cadex is a FreeCAD fork stripped to a single AI-native modeling engine. The
user chats with an assistant in a Qt panel; the assistant authors **ONE
declarative xscript project script** through four lifecycle tools
(`xscript.project.*`); the script executes in a sandboxed, windowless
`FreeCADCmd` subprocess that produces detached BREP (and mesh) artifacts for
all five capability domains — **partdesign, sketcher, part, mesh, assembly**
— in one pass; a
publisher validates the result and applies it to the live document under ONE
transaction. The document is a rebuildable artifact: a headless rebuild from
the script must reproduce the accepted content digest. The Qt app is the
interim shell; the endpoint is a Blender shell fed by a headless `cadexd`
service (`docs/INTEGRATION.md`).

## 2. The xscript pipeline `[Cadex-new]`

```
 chat panel            session               runtime                worker                 publisher            document
 CadexGui.py    →   CadexSession.py   →  CadexScriptedRuntime  →  FreeCADCmd          →  CadexScripted*     →  live App::Document
 (user turn)        (provider loop,      .py (persist source,     --safe-mode -c …       Publication.py        (ONE transaction,
                     tool dispatch)       validate, spawn ONE     (exec THE script,      (per-domain apply,     tagged objects,
                                          project worker)         detached BREP out)      lint + orphan GC)     one undo step)
```

- **Session** (`src/Mod/cadex/CadexSession.py`): one provider turn at a
  time; dispatches the project lifecycle (`_run_project_xscript_tool`;
  public entry `run_project_xscript_operation`, also used by the Parameters
  panel); turn-start context is deliberately small — detail is pulled
  through `core.inspect` on demand.
- **Runtime** (`src/Mod/cadex/CadexScriptedRuntime.py`): the project
  lifecycle. Captures bounded state on the document thread
  (`capture_project_state`), persists source + values + revision to the
  script store BEFORE execution (`prepare_project_candidate`; stale-revision
  guard), stages the worker bundle, executes off-thread
  (`execute_candidate`), validates geometry host-side
  (`validate_project_result`), publishes, accepts
  (`accept_project_candidate` — records the accepted contract + digest).
  `edit_script` reuses unique-match find/replace (`_apply_replacements`);
  `set_params` patches values only.
- **Worker**: `FreeCADCmd --safe-mode -c <bootstrap>` subprocess launched
  via `src/Mod/cadex/CadexScriptedProcess.py` (`run_process`: no console
  window, new session, stdin closed, hard timeout + memory watchdog;
  budgets from preferences `ScriptedTimeoutSeconds` /
  `ScriptedMemoryLimitMB`). The project bundle stages all five domain
  api/worker modules with entry `cadex_project_worker.py`; the script
  executes once, outputs are grouped by domain and evaluated sketcher →
  part → partdesign → mesh → assembly. Mesh assets (`assets/*.stl|obj|ply`
  under the project root) are staged beside the worker for
  `mesh.import_file`. Wire schema: `cadex-xscript-project-worker-v1`.
- **Publisher** (`src/Mod/cadex/CadexScriptedDomainPublication.py`,
  `CadexScriptedPublication.py`): `publish_project_candidate` applies all
  domains under ONE transaction (per-domain sub-publishes with
  `manage_transaction=False`), rewrites same-script assembly component
  tokens to live names, garbage-collects owned objects whose outputs left
  the contract, and aborts on any untagged document object
  (`PUBLICATION_UNTAGGED_OBJECT`). Failed candidates stay inspectable
  without replacing the accepted revision.
- **Geometry checks**: `src/Mod/cadex/CadexGeometryWorker.cpp` — an
  isolated C++ helper (built to `build/release/bin/CadexGeometryWorker`)
  for BREP validation (`BOPAlgo_ArgumentAnalyzer`) and exact
  minimum-distance queries; JSON job schema `cadex-geometry-job-v1`.

Published objects are tagged (`src/Mod/cadex/CadexScriptedDomains.py`):
`CadexXScriptProgramId` (= `"project"`), `CadexXScriptDomain`,
`CadexXScriptWorkbench`, `CadexXScriptRevision`, `CadexXScriptOutputName`.
Ownership closure, lint, and orphan queries live in
`CadexScriptedOwnership.py`.

## 3. File map of `src/Mod/cadex/`

### Engine core

| File | Role |
|---|---|
| `CadexScriptedRuntime.py` | The project lifecycle: store persistence, source policy, worker staging/exec, validation, acceptance. `[Cadex-new]` |
| `CadexScriptedDomains.py` | `PROJECT_PACK` + the five capability packs (worker/publication contracts), project tool specs, `project_script_revision`, object-tag constants, source sandbox rules. `[Cadex-new]` |
| `cadex_project_api.py` / `cadex_project_worker.py` | The project domain: `params`/`num` vocabulary, inline assembly-source tokens, multi-domain exec namespace, per-domain evaluation, worker-side content digest. `[Cadex-new]` |
| `CadexScriptedDomainPublication.py` / `CadexScriptedPublication.py` | Project publication (one transaction, lint, GC) over the per-domain apply routines. `[VibeCAD-era]`, reshaped `[Cadex-new]` |
| `CadexScriptedOwnership.py` | Ownership tagging, owned closure, untagged/orphan queries. |
| `CadexScriptedProcess.py` | Bounded subprocess runner (timeout, memory watchdog, cancellation). `[VibeCAD-era]` |
| `CadexDigest.py` | Document-side diagnostic digest (`cadex-document-digest-v1`). `[Cadex-new]` |
| `cadex_rebuild.py` | Headless rebuild + digest comparison (`pixi run rebuild <root>`). `[Cadex-new]` |
| `cadex_{partdesign,sketcher,part,assembly}_{api,worker}.py` | The original four domain APIs (staged into the project worker) and worker implementations. `[VibeCAD-era]` |
| `cadex_mesh_api.py` / `cadex_mesh_worker.py` | The Phase 4 mesh domain on `Mod/Mesh`+`Mod/MeshPart`: tessellate/import/boolean/decimate, canonical vertex/facet ordering + vertex-set digest fingerprint (ADR-016). `[Cadex-new]` |
| `cadex_domain_api.py` / `cadex_domain_worker.py` | Shared domain API/worker plumbing (`_execute_source` is the composition substrate). `[VibeCAD-era]` |
| `CadexGeometryWorker.cpp` | Isolated C++ BREP validation / distance worker. `[VibeCAD-era]` |

### Session, providers, tools `[VibeCAD-era]`

| File | Role |
|---|---|
| `CadexSession.py` | Turn orchestration, tool surface resolution, provider loop, project tool dispatch. |
| `CadexProvider.py` | Providers: `AnthropicProvider`, `OpenAIProvider` (also serves xAI/Ollama/OpenAI-compatible endpoints via base URL), `ChatGPTSubscriptionProvider` (bundled Codex app-server), `OfflineProvider`. |
| `CadexCodex.py`, `CadexAuth.py` | Codex app-server integration; keyring/.env/env-var credential handling. |
| `CadexTools.py`, `tool_impl/` (`service/`, `sketcher/`) | Tool registry and implementations (`core.*`, `file.*`, `xscript.project.*`). |
| `CadexInspection.py` | The bounded `core.inspect` read surface (scopes `document`, `selection`, `object`, `script`, `api`, `image`). |
| `CadexReferenceContracts.py` | Geometry pins (`@edge-1`, `@face-2`): shared handle + owner + subelement hint + geometric fingerprint; fingerprint-based re-resolution when the document revision moved. |
| `CadexTransactions.py` | Transaction wrapper for tool execution. |
| `CadexModelingSurface.py` | The global project surface id (any workbench, one script). `[Cadex-new]` |

### UI `[VibeCAD-era]`, being reshaped `[Cadex-new]`

| File | Role |
|---|---|
| `CadexGui.py` | Assistant chat panel (conversations, attach image/view, send/steer/stop). |
| `CadexExperimentalMode.py` | The only mode (`is_experimental_mode_session()` returns `True`): hides all toolbars/status bar/MDI tabs, forces `PartDesignWorkbench`, launch screen when no document. 50/50 split (viewport left, panel column right — tree/parameters/script/chat) held by a `resizeDocks` event filter; native-route lockdown (minimal About/Preferences/Quit menu, shortcut strip, tree context/double-click block, unsanctioned-edit watchdog) re-applied on every chrome pass (ADR-015). |
| `CadexScriptView.py` | Read-only dock rendering THE project script; refreshes on assistant updates and visibility changes. Deliberately not an editor. |
| `CadexExperimentalChat.py`, `CadexPromptStarters.py` | Experimental-mode chat surface and starters. |
| `CadexParametersPanel.py` | Sliders for the project script's declared parameters (`params`/`num` specs from `script.json`); a drag commits through `xscript.project.set_params` with the working-revision guard, no provider turn, debounced 600 ms (ADR-014). |
| `CadexPreferences.py` | Preferences page (provider, model, keys, budgets). Pref group `User parameter:BaseApp/Preferences/Mod/cadex`. |
| `CadexEditState.py`, `CadexGrid.py` | Edit-state tracking; cadex-owned adaptive viewport grid (pivy line grid, ADR from Phase 1.3). |

### Project store `[Cadex-new]`

`src/Mod/cadex/CadexProject.py`. Root: `$CADEX_HOME` if set, else the
appdata dir + `Cadex` (e.g. `~/Library/Application Support/cadex/Cadex` on
macOS). Layout:

```
<root>/projects/<slug>-<hash8>/
  project.cadex.json            project manifest
  conversations/…               chat transcripts per conversation
  script.py                     THE project script (sole source of truth)
  script.json                   schema cadex-project-script-v1: param specs
                                cache + values, working/accepted revision,
                                accepted contract, accepted_digest,
                                latest candidate
  script_artifacts/<revision>/  staged worker attempts + serialized outputs
```

`CadexProjectScriptStore` owns `script.py`/`script.json` (atomic writes,
schema-checked). Documents reopen with their conversations and script
attached; the assistant is disabled for unsaved documents so records have a
durable home. VibeCAD-era per-domain program stores
(`xscript/<domain>/<program_id>/`) are not migrated (ADR-011).

### Support

`CadexCore.py`, `CadexDebug.py`, `CadexGeometry.py`,
`CadexAssemblyHierarchy.py`, `CadexPointArtifacts.py`, `Init.py`,
`InitGui.py`, icons (`cadex-*.svg`).

### Tests

`src/Mod/cadex/cadex_tests/` — ~30 pytest files; `conftest.py` stubs
`FreeCAD`/`FreeCADGui` so most of the suite runs headless without a built
FreeCAD:

```
pixi run python -m pytest src/Mod/cadex/cadex_tests
```

(333 passing / 1 skipped as of 2026-07-24.)

`test_tool_surface_guardrails.py` pins the exact `xscript.project.*` tool
surface and asserts dissolved per-domain operations and culled modules stay
gone. `project_xscript_api_integration.py` drives the full lifecycle
headlessly under FreeCADCmd; `test_project_rebuild.py` is the digest CI
(ctest `CadexProjectRebuildDigest`; skips itself when no FreeCADCmd binary
is available).

## 4. The FreeCAD substrate `[FreeCAD-inherited]`

What the engine stands on (details and the removal ledger in
`docs/FREECAD.md`):

- `src/App` — `App::Document`, properties, expressions, **transactions** —
  the persistence and undo model the publisher relies on.
- `src/Gui` — Qt6 main window, Coin3D/Quarter viewport (interim shell only).
- `src/Base` — units, vectors, persistence primitives.
- `src/Mod/{Part,PartDesign,Sketcher,Assembly}` — the original capability
  areas; `src/Mod/{Mesh,MeshPart}` — the Phase 4 mesh domain substrate.
- Support trees: `Import`, `Material`, `Measure`, `Show`, `Start`, `Test`,
  `Help`.
- The 17 unused workbench trees were removed in Phase 1 (ADR-007..010;
  `docs/FREECAD.md` §3 is empty).

## 5. Build & run

- Toolchain: pixi + CMake, Qt6/PySide6, Coin3D, OCCT. Tasks in `pixi.toml`:
  `configure`/`build`/`test`/`freecad` (debug default), `*-release`
  variants, and `rebuild` (headless digest check).
- Artifacts: `build/release/bin/FreeCAD`, `build/release/bin/FreeCADCmd`,
  `build/release/bin/CadexGeometryWorker`. On macOS the app runs from the
  installed tree — run `pixi run install-release` after building.
- Packaging: `docs/cadex-release-packaging.md`.

## 6. Open questions

- Whether `CadexModelingSurface.py`'s surface resolution collapses further
  now that one global project surface exists.
- How much of `CadexProject.py`'s store becomes the `cadexd` project store
  verbatim in Phase 5.
