# ARCHITECTURE.md — What Exists Today

Verified against source: 2026-07-25

This document describes the code as it **is**, not as it will be. Targets live
in `docs/VISION.md`, `docs/XSCRIPT.md` (direction section),
`docs/INTEGRATION.md`, and `docs/ROADMAP.md`.

Provenance tags: `[FreeCAD-inherited]` upstream FreeCAD code we build on;
`[VibeCAD-era]` built during the VibeCAD phase and still current;
`[Cadex-new]` added or reshaped since the cadex import.

## 1. The one-paragraph picture

Cadex is a FreeCAD fork stripped to a single AI-native modeling engine, and
since Phase 7 that is **all** it is: this repository builds `FreeCADCmd`
and `CadexGeometryWorker` and no application (ADR-021/022). The engine runs
as **cadexd** — a persistent headless `FreeCADCmd` service, one child per
open project, speaking `cadex-cadexd-v1` NDJSON over stdio (ADR-017/018).
cadexd owns the script store, executes **ONE declarative xscript project
script** in a sandboxed windowless worker that produces detached BREP (and
mesh) artifacts for all five capability domains — **partdesign, sketcher,
part, mesh, assembly** — in one pass, validates the result, and publishes
it into its own *ephemeral* `App::Document` (lint, contract GC, output
identity) with an accepted content digest. Every `open_project` re-runs the
accepted script and asserts digest equality, so restart determinism is
proven on every open rather than once per audit. The **shell is the Blender
fork** (`/Users/theo/mesh`): it is a protocol client that hydrates the
tessellated results into its scene, and it carries this engine inside its
own bundle as a payload it finds by manifest (`docs/INTEGRATION.md`,
ADR-023).

## 2. The xscript pipeline `[Cadex-new]`

```
 Blender shell (mesh repo)              cadexd child (per project)
 ────────────────────────────           ─────────────────────────────────────────────
 chat / sliders / picking               cadexd.py → CadexScriptedRuntime
 mesh_agent/cadex_backend.py  ══NDJSON══▶ (serial dispatch; persist source, spawn ONE
 mesh_agent/cadexd_client.py             --safe-mode worker, validate, publish into the
 mesh_agent/cadex_hydrate.py  ◀═════════ ephemeral App::Document, accept, tessellate)
 (hydrates tessellation +
  face/edge ID maps into the scene)
```

The whole left-hand column lives in the **other repository**. What crosses
the boundary is the protocol in `docs/INTEGRATION.md` and nothing else: no
shared code, no shared process, no shared licence obligation.

- **cadexd** (`src/Mod/cadex/cadexd.py`, protocol
  `src/Mod/cadex/CadexdProtocol.py`): one `FreeCADCmd` child per open
  project (no `--safe-mode` — trusted engine code), spawned/owned by the
  shell (the Blender add-on's `cadexd_client.py`, in the mesh repo);
  `pixi run cadexd` for a standalone instance. Serial dispatch, `CADEXD_BUSY` refusal for a second
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
- **Display, not hydration.** The engine's side of the shell boundary ends
  at the response: each accepted output carries a `display` block with
  absolute artifact paths and, on request, `cadex-tessellation-v1` buffers
  plus face/edge ID maps (`cadex_tessellation.py`, digest-neutral, quality
  presets `draft`/`coarse`/`standard`/`fine`). What a shell does with them
  is its own business — the Blender shell hydrates them into its scene with
  per-triangle `cadex_face` attributes so picking round-trips through
  `resolve_pin`. The Qt hydration that used to live here died with the Qt
  shell (ADR-021).
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

### The shell

There is no shell in this repository. `CadexGui`, `CadexSession`,
`CadexProvider`, `CadexCore`, `CadexAuth`, `CadexCodex`, `CadexPreferences`,
`CadexTransactions`, `CadexEditState`, `CadexGrid`, `CadexParametersPanel`,
`CadexScriptView`, the `tool_impl` package, `CadexdClient` and
`CadexShellHydration` were all deleted in Phase 7 (ADR-021). The shell is
`scripts/addons_core/mesh_agent/` in the mesh repository, and it speaks the
protocol in `docs/INTEGRATION.md`.

`test_engine_purity_guardrails.py` keeps it that way: nothing under
`src/Mod/cadex/**` may import `PySide*`, `FreeCADGui`, `tool_impl` or
`jsonschema`, and cadexd's transitive module closure must equal a declared
list.

### Contracts and surfaces `[Cadex-new]`

| File | Role |
|---|---|
| `CadexdProtocol.py` | The wire protocol: NDJSON codec, op registry (`OP_ARG_SPECS`), failure codes. Its op table is asserted equal to `docs/INTEGRATION.md`'s. |
| `cadexd.py` | The service: serial dispatch, cancel, busy, the ephemeral document, the restore pass, the per-output `display` block. |
| `CadexTools.py` | `FAILURE_STAGES`, the `tool_failure` envelope every refusal is shaped as (and every shell parses), `unchanged_state`, `ToolSpec` as a declaration. |
| `CadexEngineSettings.py` | The engine's own preference group and sandbox budget defaults. Split from the Qt preferences in C1. |
| `CadexInspection.py` | The bounded `inspect` read surface (scopes `document`, `object`, `script`, `api`, `image`; `selection` was shell-only and is gone). |
| `CadexReferenceContracts.py` | Geometry pins: shared handle + owner + subelement hint + geometric fingerprint, and fingerprint re-resolution when the revision moved. |
| `CadexPinResolution.py` | Resolves a pick or fingerprint against the accepted revision's staged BREP. |
| `CadexModelingSurface.py` | The global project surface id (any workbench, one script). |

### Project store `[Cadex-new]`

`src/Mod/cadex/CadexProject.py`. Root: `$CADEX_HOME` if set, else the
appdata dir + `Cadex` (e.g. `~/Library/Application Support/cadex/Cadex` on
macOS). Layout:

```
<root>/projects/<slug>-<hash8>/
  project.cadex.json            project manifest
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

**cadexd is the sole writer and the sole reader.** The shell never touches
the store: it asks the engine (`inspect`), which is why the store's layout
is not part of the two-repository contract.

In practice the root is chosen by the shell, not by `$CADEX_HOME`: the
Blender shell passes `<blend-dir>/<stem>.cadex` as `project_root`, so a
model lives beside the file that displays it.

`CadexProjectScriptStore` (`CadexScriptStore.py`, split out of
`CadexProject.py` in C1) owns `script.py`/`script.json` with atomic,
schema-checked writes. **Conversation history is no longer here**: it lives
in the `.blend` with the Claude Code session id (ADR-020, decision 4), and
the engine's conversation store died with the Qt shell. VibeCAD-era
per-domain program stores are not migrated (ADR-011).

### Support

`CadexDigest.py`, `CadexScriptedOwnership.py`, `cadex_tessellation.py`,
`cadex_rebuild.py` (the headless rebuild entry), `Init.py`. No icons, no
`InitGui.py`: this module registers no workbench.

### Tests

`src/Mod/cadex/cadex_tests/` — ~30 pytest files; `conftest.py` stubs
`FreeCAD`/`FreeCADGui` so most of the suite runs headless without a built
FreeCAD:

```
pixi run python -m pytest src/Mod/cadex/cadex_tests
```

(422 passing / 1 skipped as of 2026-07-25.)

`test_project_tool_surface.py` pins the exact `xscript.project.*` tool
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
- `src/Gui` — Qt6 main window, Coin3D/Quarter viewport. **Present but not
  built**: release and package configs set `BUILD_GUI=OFF` (ADR-022), which
  is the disable commit for this tree under `docs/FREECAD.md` §3. Deleting
  it is Phase 8. Debug builds still build it, so the tree stays compilable.
- `src/Base` — units, vectors, persistence primitives.
- `src/Mod/{Part,PartDesign,Sketcher,Assembly}` — the original capability
  areas; `src/Mod/{Mesh,MeshPart}` — the Phase 4 mesh domain substrate.
- Support trees: `Import`, `Material`, `Measure`, `Show`, `Start`, `Test`,
  `Help`.
- The 17 unused workbench trees were removed in Phase 1 (ADR-007..010).
  `docs/FREECAD.md` §3 now carries one entry: `src/Gui`, disabled and
  awaiting deletion.

## 5. Build & run

- Toolchain: pixi + CMake, OCCT, Qt6 (non-GUI: Core/Xml/Concurrent/Network).
  Tasks in `pixi.toml`: `configure`/`build`/`test` (debug default, GUI on),
  the `*-release` variants (**GUI off**, ADR-022), `rebuild` (headless
  digest check), and `cadexd` (standalone engine service on stdio).
- Artifacts, release: `build/release/bin/FreeCADCmd` and
  `build/release/bin/CadexGeometryWorker`. **There is no `FreeCAD` binary
  in a release build** — that is the point of Phase 7. Debug builds still
  produce one, as an engineering convenience only.
- Run the engine's own tests with `pixi run python -m pytest
  src/Mod/cadex/cadex_tests` (no build needed; FreeCAD is stubbed).
  `pixi run python src/Mod/cadex/cadex_tests/cadexd_latency_integration.py`
  is the slider-drag latency bar, driven over raw NDJSON.
- Packaging: `docs/cadex-release-packaging.md` — the engine payload.

## 6. Open questions

- **The warm-standby worker.** The per-drag `FreeCADCmd --safe-mode` spawn
  (~0.4–0.5 s) dominates the ~0.5 s slider median. A warm worker inside
  cadexd is the identified lever for sub-100 ms drags; nothing else in the
  measured path is close to it in cost.
- **`display` on `open_project`** (A1). Would fold the restore pass and the
  hydration rebuild into one script run; the measured cost of not having it
  is 0.49 s per project open.
- Whether `CadexModelingSurface.py`'s surface resolution collapses further
  now that one global project surface exists and no provider consumes it.
- What remains of `CadexProject.py` once the conversation store is gone —
  the script store already moved to `CadexScriptStore.py`.
