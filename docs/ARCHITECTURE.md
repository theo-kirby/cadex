# ARCHITECTURE.md — What Exists Today

Verified against source: 2026-07-24

This document describes the code as it **is**, not as it will be. Targets live
in `docs/VISION.md`, `docs/XSCRIPT.md` (target section), `docs/INTEGRATION.md`,
and `docs/ROADMAP.md`.

Provenance tags: `[FreeCAD-inherited]` upstream FreeCAD code we build on;
`[VibeCAD-era]` built during the VibeCAD phase and still current;
`[Cadex-new]` added or reshaped since the cadex import.

## 1. The one-paragraph picture

Cadex is a FreeCAD fork stripped to a single AI-native modeling engine. The
user chats with an assistant in a Qt panel; the assistant authors declarative
**xscript** Python programs through lifecycle tools; each program executes in
a sandboxed, windowless `FreeCADCmd` subprocess that produces detached BREP;
a publisher validates the result and applies it to the live document under a
transaction. Four domains exist: **partdesign, sketcher, part, assembly**.
The Qt app is the interim shell; the endpoint is a Blender shell fed by a
headless `cadexd` service (`docs/INTEGRATION.md`).

## 2. The xscript pipeline `[VibeCAD-era]`

```
 chat panel            session               runtime                worker                 publisher            document
 CadexGui.py    →   CadexSession.py   →  CadexScriptedRuntime  →  FreeCADCmd          →  CadexScripted*     →  live App::Document
 (user turn)        (provider loop,      .py (stage attempt,      --safe-mode -c …       Publication.py        (transaction,
                     tool dispatch)       validate source,        (sandboxed exec,       (validate, apply       tagged objects)
                                          spawn worker)           detached BREP out)      under transaction)
```

- **Session** (`src/Mod/cadex/CadexSession.py`): one provider turn at a time;
  builds the bounded tool surface for the active domain; dispatches tool
  calls (`_run_session_turn`); turn-start context is deliberately small —
  detail is pulled through `core.inspect` on demand.
- **Runtime** (`src/Mod/cadex/CadexScriptedRuntime.py`): the async program
  lifecycle. Captures bounded state on the document thread, then does all
  source validation, artifact persistence, worker execution, and geometry
  validation off-thread, and calls the publisher once with detached values.
  Worker staging manifest: `_DOMAIN_WORKER_BUNDLES`
  (`CadexScriptedRuntime.py:65`) — exactly the four real domains.
- **Worker**: `FreeCADCmd --safe-mode -c <bootstrap>` subprocess
  (`CadexScriptedRuntime.py:2163`), launched via
  `src/Mod/cadex/CadexScriptedProcess.py` (`run_process`: no console window,
  new session, stdin closed, hard timeout + memory watchdog; budgets from
  preferences `ScriptedTimeoutSeconds` / `ScriptedMemoryLimitMB`). Wire
  schema: `cadex-xscript-domain-worker-v2` (`CadexScriptedRuntime.py:34`).
- **Publisher** (`src/Mod/cadex/CadexScriptedPublication.py`,
  `CadexScriptedDomainPublication.py`): applies validated, precomputed native
  state to the live document under a FreeCAD transaction
  (`src/Mod/cadex/CadexTransactions.py`); failed candidates stay inspectable
  without replacing the accepted revision.
- **Geometry checks**: `src/Mod/cadex/CadexGeometryWorker.cpp` — an isolated
  C++ helper (built to `build/release/bin/CadexGeometryWorker`) for BREP
  validation (`BOPAlgo_ArgumentAnalyzer`) and exact minimum-distance queries;
  JSON job schema `cadex-geometry-job-v1`.

Published objects are tagged with `[VibeCAD-era]` properties
(`src/Mod/cadex/CadexScriptedDomains.py:68`): `CadexXScriptProgramId`,
`CadexXScriptDomain`, `CadexXScriptWorkbench`, `CadexXScriptRevision`,
`CadexXScriptOutputName`.

## 3. File map of `src/Mod/cadex/`

### Engine core `[VibeCAD-era]`

| File | Role |
|---|---|
| `CadexScriptedRuntime.py` | Program lifecycle: staging, source policy, worker exec, validation, revisions. The largest module. |
| `CadexScriptedDomains.py` | Domain packs (`XSCRIPT_WORKBENCH_PACKS`, 4 entries), lifecycle-operation registry, object-tag constants, source sandbox rules, adapter protocol. |
| `CadexScriptedDomainPublication.py` / `CadexScriptedPublication.py` | Domain-specific and shared publication paths (contains dead branches for culled domains — see `docs/FREECAD.md` §4). |
| `CadexScriptedOwnership.py` | Program/output ownership of document objects. |
| `CadexScriptedProcess.py` | Bounded subprocess runner (timeout, memory watchdog, cancellation). |
| `CadexScriptedEditor.py` | Model Code Editor UI for program source. |
| `cadex_{partdesign,sketcher,part,assembly}_{api,worker}.py` | The four domain APIs (staged into workers; the `x` global in program source) and worker implementations. |
| `cadex_domain_api.py` / `cadex_domain_worker.py` | Shared domain API/worker plumbing. |
| `CadexGeometryWorker.cpp` | Isolated C++ BREP validation / distance worker. |

### Session, providers, tools `[VibeCAD-era]`

| File | Role |
|---|---|
| `CadexSession.py` | Turn orchestration, tool surface resolution, provider loop. |
| `CadexProvider.py` | Providers: `AnthropicProvider`, `OpenAIProvider` (also serves xAI/Ollama/OpenAI-compatible endpoints via base URL), `ChatGPTSubscriptionProvider` (bundled Codex app-server), `OfflineProvider`. |
| `CadexCodex.py`, `CadexAuth.py` | Codex app-server integration; keyring/.env/env-var credential handling. |
| `CadexTools.py`, `tool_impl/` (`service/`, `sketcher/`) | Tool registry and implementations (`core.*`, `file.*`, `xscript.<domain>.*`). |
| `CadexInspection.py` | The bounded `core.inspect` read surface. |
| `CadexReferenceContracts.py` | Geometry pins (`@edge-1`, `@face-2`): shared handle + owner + subelement hint + geometric fingerprint; fingerprint-based re-resolution when the document revision moved. |
| `CadexTransactions.py` | Transaction wrapper for tool execution. |

### UI `[VibeCAD-era]`, being reshaped `[Cadex-new]`

| File | Role |
|---|---|
| `CadexGui.py` | Assistant chat panel (conversations, attach image/view, send/steer/stop). |
| `CadexExperimentalMode.py` | The only mode (`is_experimental_mode_session()` returns `True`): hides all toolbars/status bar/MDI tabs, right-docks Assistant (420 px) + Parameters + Tree view, forces `PartDesignWorkbench`, launch screen when no document. ~80% of the target 50/50 layout. |
| `CadexExperimentalChat.py`, `CadexPromptStarters.py` | Experimental-mode chat surface and starters. |
| `CadexParametersPanel.py` | Parameter sliders; a drag re-runs the program through the same `xscript.<domain>.set_inputs` path with no provider turn, debounced 600 ms (`DEBOUNCE_MS`). |
| `CadexPreferences.py` | Preferences page (provider, model, keys, budgets). Pref group `User parameter:BaseApp/Preferences/Mod/cadex`. |
| `CadexEditState.py`, `CadexGrid.py`, `CadexModelingSurface.py` | Edit-state tracking, viewport grid, active-surface resolution. |

### Project store `[VibeCAD-era]`

`src/Mod/cadex/CadexProject.py`. Root: `$CADEX_HOME` if set, else the FreeCAD
appdata dir + `Cadex` (e.g. `~/.local/share/FreeCAD/Cadex` on Linux,
`~/Library/Application Support/FreeCAD/Cadex` on macOS). Layout:

```
<root>/projects/<slug>-<hash8>/
  project.cadex.json            project manifest
  conversations/…               chat transcripts per conversation
  xscript/<domain>/<program_id>/
    program.json                manifest (schema cadex-xscript-program-v2)
    …                           source, revisions, accepted artifacts (BREP …)
```

Documents reopen with their conversations and programs attached; the
assistant is disabled for unsaved documents so records have a durable home.

### Support

`CadexCore.py`, `CadexDebug.py`, `CadexGeometry.py`,
`CadexAssemblyBOM.py`, `CadexAssemblyHierarchy.py`,
`CadexPointArtifacts.py`, `Init.py`, `InitGui.py`, icons (`cadex-*.svg`).

### Tests

`src/Mod/cadex/cadex_tests/` — ~35 pytest files; `conftest.py` stubs
`FreeCAD`/`FreeCADGui` so the suite runs headless without a built FreeCAD:

```
pixi run python -m pytest src/Mod/cadex/cadex_tests
```

(373 passing / 1 skipped as of 2026-07-24.)

`test_engine_contracts.py` is xscript-only (build123d/OpenSCAD engines were
removed); `test_tool_surface_guardrails.py` pins the exact tool surface and
asserts culled modules stay deleted.

## 4. The FreeCAD substrate `[FreeCAD-inherited]`

What the engine stands on (details and the removal plan in
`docs/FREECAD.md`):

- `src/App` — `App::Document`, properties, expressions, **transactions** —
  the persistence and undo model the publisher relies on.
- `src/Gui` — Qt6 main window, Coin3D/Quarter viewport (interim shell only).
- `src/Base` — units, vectors, persistence primitives.
- `src/Mod/{Part,PartDesign,Sketcher,Assembly}` — the four capability areas.
- Support trees: `Import`, `Material`, `Measure`, `Show`, `Start`, `Test`,
  `Mesh`, `MeshPart`.
- ~18 more workbench trees are present but unused, slated for removal
  (`docs/FREECAD.md` §3).

## 5. Build & run

- Toolchain: pixi + CMake, Qt6/PySide6, Coin3D, OCCT. Tasks in `pixi.toml`:
  `configure`/`build`/`test`/`freecad` (debug default) and `*-release`
  variants.
- Artifacts: `build/release/bin/FreeCAD`, `build/release/bin/FreeCADCmd`,
  `build/release/bin/CadexGeometryWorker`.
- Packaging: `docs/cadex-release-packaging.md`.

## 6. Open questions

- Whether `CadexModelingSurface.py`'s workbench/engine resolution survives
  the no-workbench product model or collapses in Phase 2/3.
- How much of `CadexProject.py`'s store becomes the `cadexd` project store
  verbatim in Phase 5.
