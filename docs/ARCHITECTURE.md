# ARCHITECTURE.md — What Exists Today

Verified against source: 2026-07-25

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
(`xscript.project.*`). Since Phase 5 the engine runs behind **cadexd** — a
persistent headless `FreeCADCmd` service, one child per open project,
speaking `cadex-cadexd-v1` NDJSON over stdio (ADR-017/018). cadexd persists
the script store, executes the script in a sandboxed windowless worker that
produces detached BREP (and mesh) artifacts for all five capability domains
— **partdesign, sketcher, part, mesh, assembly** — in one pass, validates
the result, and publishes it into its own *ephemeral* `App::Document`
(lint, contract GC, output identity) with an accepted content digest. The
Qt shell is a protocol client: it hydrates the accepted artifacts into the
document of record (.FCStd) as tagged display objects in one transaction.
Both documents are rebuildable artifacts — a headless rebuild from the
script must reproduce the accepted content digest, and every cadexd open
re-proves it. The Qt app is the interim shell; the endpoint is a Blender
shell speaking the same protocol (`docs/INTEGRATION.md`).

## 2. The xscript pipeline `[Cadex-new]`

```
 chat panel         session                 cadexd child (per project)                                shell hydration
 CadexGui.py  →  CadexSession.py  →  CadexdClient  ══NDJSON══▶  cadexd.py → CadexScriptedRuntime  →  CadexShellHydration.py
 (user turn)     (provider loop,     (spawn/own child,           (serial dispatch; persist source,    (ONE transaction into the
                  tool dispatch)      cancel poll, crash          spawn ONE --safe-mode worker,        .FCStd of record: tagged
                                      respawn + reopen)           validate, publish into the           Part::/Mesh::Feature
                                                                  ephemeral App::Document, accept)     mirrors, contract GC)
```

- **Session** (`src/Mod/cadex/CadexSession.py`): one provider turn at a
  time; dispatches the project lifecycle to the project's cadexd
  (`_run_project_xscript_tool` → `CadexdClient.request`; public entry
  `run_project_xscript_operation`, also used by the Parameters panel — the
  panel and provider dispatch are unchanged by the split). Engine-truth
  `core.inspect` scopes (`document/object/script/api/image`) route to
  cadexd; `selection` stays shell-local. There is **no in-process modeling
  fallback** (guardrail: `test_engine_shell_split_guardrails.py`).
- **cadexd** (`src/Mod/cadex/cadexd.py`, protocol
  `src/Mod/cadex/CadexdProtocol.py`): one `FreeCADCmd` child per open
  project (no `--safe-mode` — trusted engine code), spawned/owned by the
  shell via `src/Mod/cadex/CadexdClient.py`; `pixi run cadexd` for a
  standalone instance. Serial dispatch, `CADEXD_BUSY` refusal for a second
  modeling request, mid-run `cancel`, stdin-EOF lifetime, fd-1 hijack so
  only protocol frames reach the parent. Hosts the persistent ephemeral
  document and runs a digest-verified **restore pass** on every open.
- **Runtime** (`src/Mod/cadex/CadexScriptedRuntime.py`): the project
  lifecycle, engine-side. `run_project_lifecycle` (shared by cadexd and
  `cadex_rebuild`) captures bounded state (`capture_project_state`; budgets
  from `service.scripted_budgets()` with preferences fallback), persists
  source + values + revision to the script store BEFORE execution
  (`prepare_project_candidate`; stale-revision guard), stages the worker
  bundle, executes (`execute_candidate`), validates geometry host-side
  (`validate_project_result`), publishes into the ephemeral document,
  accepts (`accept_project_candidate` — records the accepted contract +
  digest + `accepted_attempt` locator). `edit_script` reuses unique-match
  find/replace (`_apply_replacements`); `set_params` patches values only.
  Opt-in per-request `display` produces `cadex-tessellation-v1` buffers +
  face/edge ID maps per output (`cadex_tessellation.py`, digest-neutral);
  `CadexPinResolution.py` resolves pins headlessly against the accepted
  staged BREP.
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
  without replacing the accepted revision. Since Phase 5 publication runs
  **only inside cadexd's ephemeral document** (and `cadex_rebuild`) — the
  split is process-level, so the pipeline modules stay in-tree, but shell
  modules must not import them (ADR-018).
- **Shell hydration** (`src/Mod/cadex/CadexShellHydration.py`): on the Qt
  document thread, ONE transaction (one undo step) mirrors the accepted
  contract into the .FCStd of record — find-or-create `Part::Feature`
  (importBrep + solved placement) / `Mesh::Feature` (Mesh.read) keyed by
  the xscript ownership tags, revision tag updated, contract-driven GC of
  leavers (robust across cadexd restarts and across the switchover from
  publication-era native objects). Qt hydration uses BREP only — the Coin
  providers tessellate natively; the tessellation buffers serve tests and
  the Phase 6 Blender shell. A hydration failure returns
  `SHELL_HYDRATION_FAILED` while the engine state is already accepted (the
  next success self-heals).
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
| `cadexd.py` | The headless engine service: per-project `FreeCADCmd` child, serial dispatch, ephemeral document, restore pass, cancel (`pixi run cadexd`, ADR-017). `[Cadex-new]` |
| `CadexdProtocol.py` | `cadex-cadexd-v1` NDJSON codec, op registry + arg schemas, server failure codes; pure Python, zero FreeCAD imports. `[Cadex-new]` |
| `cadex_tessellation.py` | Phase 5.1 display tessellation: adaptive deflection, per-face triangle ranges + per-edge polylines (`cadex-tessellation-v1` buffer + sidecar), digest-neutral. Staged into the worker bundle. `[Cadex-new]` |
| `CadexPinResolution.py` | Headless pin resolution against the accepted revision's staged BREP: `_query_subelements` fingerprints or direct `{element_type, index}`. `[Cadex-new]` |
| `cadex_rebuild.py` | Headless rebuild + digest comparison (`pixi run rebuild <root>`); drives the shared `run_project_lifecycle`. `[Cadex-new]` |
| `cadex_{partdesign,sketcher,part,assembly}_{api,worker}.py` | The original four domain APIs (staged into the project worker) and worker implementations. `[VibeCAD-era]` |
| `cadex_mesh_api.py` / `cadex_mesh_worker.py` | The Phase 4 mesh domain on `Mod/Mesh`+`Mod/MeshPart`: tessellate/import/boolean/decimate, canonical vertex/facet ordering + vertex-set digest fingerprint (ADR-016). `[Cadex-new]` |
| `cadex_domain_api.py` / `cadex_domain_worker.py` | Shared domain API/worker plumbing (`_execute_source` is the composition substrate). `[VibeCAD-era]` |
| `CadexGeometryWorker.cpp` | Isolated C++ BREP validation / distance worker. `[VibeCAD-era]` |

### Session, providers, tools `[VibeCAD-era]`

| File | Role |
|---|---|
| `CadexSession.py` | Turn orchestration, tool surface resolution, provider loop, project tool dispatch to cadexd. |
| `CadexdClient.py` | Shell-side cadexd owner: lazy spawn, request/progress/cancel, crash → `CADEXD_CRASHED` + respawn/reopen, per-project registry, killed on document close/app exit. `[Cadex-new]` |
| `CadexShellHydration.py` | One-transaction hydration of accepted results into the .FCStd of record; contract-driven GC. `[Cadex-new]` |
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
                                accepted_attempt (staged-artifact locator;
                                that attempt dir is pinned, Phase 5.2),
                                latest candidate
  script_artifacts/<revision>/  staged worker attempts + serialized outputs
                                (+ display/ tessellation buffers when
                                requested)
```

Post-split, **cadexd is the sole writer** of the script store; the shell
may still read it (the Parameters panel reads `script.json` specs).

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

(422 passing / 1 skipped as of 2026-07-25.)

`test_tool_surface_guardrails.py` pins the exact `xscript.project.*` tool
surface and asserts dissolved per-domain operations and culled modules stay
gone; `test_engine_shell_split_guardrails.py` pins the process boundary
(shell modules never import the publication/pipeline internals) and
`test_cadexd_protocol.py` pins the cadexd op list.
`project_xscript_api_integration.py` drives the full lifecycle headlessly
under FreeCADCmd; `tessellation_id_map_integration.py`,
`pin_resolution_integration.py`, and
`cadexd_shell_switchover_integration.py` cover the Phase 5 engine
capabilities and the shell seam (the last one also measures slider-drag
latency). `test_project_rebuild.py` is the digest CI (ctest
`CadexProjectRebuildDigest`); `test_cadexd_lifecycle.py` is the cadexd CI
(ctest `CadexdLifecycle`: open → mutate → inspect → resolve_pin →
kill -9 → respawn → restore digest equality → mid-run cancel). Both skip
themselves when no FreeCADCmd binary is available.

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
  variants, `rebuild` (headless digest check), and `cadexd` (standalone
  engine service on stdio).
- Artifacts: `build/release/bin/FreeCAD`, `build/release/bin/FreeCADCmd`,
  `build/release/bin/CadexGeometryWorker`. On macOS the app runs from the
  installed tree — run `pixi run install-release` after building.
- Packaging: `docs/cadex-release-packaging.md`.

## 6. Open questions

- Whether `CadexModelingSurface.py`'s surface resolution collapses further
  now that one global project surface exists.
- How much of `CadexProject.py`'s store becomes the `cadexd` project store
  verbatim in Phase 5.
