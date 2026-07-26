# ARCHITECTURE.md — What Exists Today

Verified against source: 2026-07-26

This document describes the code as it **is**, not as it will be. Targets live
in `docs/VISION.md`, `docs/XSCRIPT.md` (direction section),
`docs/INTEGRATION.md`, and `docs/ROADMAP.md`.

Provenance tags: `[FreeCAD-inherited]` upstream FreeCAD code we build on;
`[VibeCAD-era]` built during the VibeCAD phase and still current;
`[Cadex-new]` added or reshaped since the cadex import.

## 1. The one-paragraph picture

Cadex is one application built from two forks in **one repository**
(ADR-030). The **engine** is a FreeCAD fork at the repo root, stripped to a
single AI-native modeling engine and building `FreeCADCmd` and
`CadexGeometryWorker` and no application of its own (ADR-021/022). It runs
as **cadexd** — a persistent headless `FreeCADCmd` service, one child per
open project, speaking `cadex-cadexd-v1` NDJSON over stdio (ADR-017/018).
cadexd owns the script store, executes **ONE declarative xscript project
script** in a sandboxed windowless worker that produces detached BREP (and
mesh) artifacts for all five capability domains — **partdesign, sketcher,
part, mesh, assembly** — in one pass, validates the result, and publishes
it into its own *ephemeral* `App::Document` (lint, contract GC, output
identity) with an accepted content digest. Every `open_project` re-runs the
accepted script and asserts digest equality, so restart determinism is
proven on every open rather than once per audit. The **shell is a Blender
fork under `shell/`**: a protocol client that hydrates the tessellated
results into its scene, and the thing a user actually launches. It carries
the engine inside its own bundle as a payload it finds by manifest
(`docs/INTEGRATION.md`, ADR-023) — a payload now built two directories away
rather than downloaded (ADR-030).

The boundary between them is a **process boundary, not a repository
boundary**, and it did not move when the repositories merged. Nothing links
across it; nothing shares memory; the only thing that crosses is the
protocol. That is what keeps either half replaceable (ROADMAP Phases 11 and
12) and it is what the tests pin.

## 2. The xscript pipeline `[Cadex-new]`

```
 shell/  (the application)              cadexd child (per project)
 ────────────────────────────           ─────────────────────────────────────────────
 chat / sliders / picking               cadexd.py → CadexScriptedRuntime
 mesh_agent/cadex_backend.py  ══NDJSON══▶ (serial dispatch; persist source, spawn ONE
 mesh_agent/cadexd_client.py             --safe-mode worker, validate, publish into the
 mesh_agent/cadex_hydrate.py  ◀═════════ ephemeral App::Document, accept, tessellate)
 (hydrates tessellation +
  face/edge ID maps into the scene)
```

The whole left-hand column lives under `shell/scripts/addons_core/`. What
crosses the boundary is the protocol in `docs/INTEGRATION.md` and nothing
else: no shared code, no shared process, no shared licence obligation. Being
in one repository does not relax that — the left column may not `import`
anything from `src/`, and `cadexd_client.py` is deliberately a plain GPL
NDJSON client with no cadex imports.

- **cadexd** (`src/Mod/cadex/cadexd.py`, protocol
  `src/Mod/cadex/CadexdProtocol.py`): one `FreeCADCmd` child per open
  project (no `--safe-mode` — trusted engine code), spawned/owned by the
  shell (the Blender add-on's `cadexd_client.py`, under `shell/`);
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
  `mesh.import_file` — and, since ADR-043, for `part.shape_from_mesh`, which
  materializes a nested mesh value inside the part build through the entry
  point `configure_part_assets` binds. Wire schema:
  `cadex-xscript-project-worker-v1`.
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
| `CadexScriptedDomainPublication.py` / `CadexScriptedPublication.py` | Project publication (one transaction, lint, GC) over the per-domain apply routines. Publishes the five live domains only — the robot/FEM/inspection/points/reverse-engineering/meshpart/surface paths were deleted in Phase 9 (ADR-026), halving the module. `[VibeCAD-era]`, reshaped `[Cadex-new]` |
| `CadexScriptedOwnership.py` | Ownership tagging, owned closure, untagged/orphan queries. |
| `CadexScriptedProcess.py` | Bounded subprocess runner (timeout, memory watchdog, cancellation). `[VibeCAD-era]` |
| `CadexDigest.py` | Document-side diagnostic digest (`cadex-document-digest-v1`). `[Cadex-new]` |
| `cadexd.py` | The headless engine service: per-project `FreeCADCmd` child, serial dispatch, ephemeral document, restore pass, cancel (`pixi run cadexd`, ADR-017). `[Cadex-new]` |
| `CadexdProtocol.py` | `cadex-cadexd-v1` NDJSON codec, op registry + arg schemas, **response schemas** (`OP_RESPONSE_SPECS`, `NESTED_RESPONSE_SPECS`, the tool-level and server-level failure envelopes, `validate_response`), server failure codes; pure Python, zero FreeCAD imports. `[Cadex-new]` |
| `cadex_tessellation.py` | Phase 5.1 display tessellation: adaptive deflection, per-face triangle ranges + `face_keys` fingerprints + per-edge polylines (`cadex-tessellation-v1` buffer + sidecar), digest-neutral. Staged into the worker bundle. `[Cadex-new]` |
| `CadexSubshapeQuery.py` | **The one subshape vocabulary** (Phase 10b, ADR-029): `subshape_geometry` fingerprints, `query_subelements` / `resolve_selected_subshapes` resolve a selector against a shape, `SELECTOR_KEYS` is the closed key set, `fingerprint_key` is the sidecar handle. Kernel-neutral — no FreeCAD import — and staged into the worker bundle. Extracted from `cadex_partdesign_worker` (Phase 11a's item, forced forward: the part domain could not reach it without an import cycle). `[Cadex-new]` |
| `CadexPinResolution.py` | Headless pin resolution against the accepted revision's staged BREP: `CadexSubshapeQuery` fingerprints or direct `{element_type, index}`. Its three accepted-attempt readers (`accepted_attempt_dir`, `load_worker_report`, `accepted_output_item`) are public since ADR-043 — `inspect scope="output"` reads the same pinned report. `[Cadex-new]` |
| `cadex_rebuild.py` | Headless rebuild + digest comparison (`pixi run rebuild <root>`); drives the shared `run_project_lifecycle`. `[Cadex-new]` |
| `cadex_{partdesign,sketcher,part,assembly}_{api,worker}.py` | The original four domain APIs (staged into the project worker) and worker implementations. `[VibeCAD-era]` |
| `cadex_mesh_api.py` / `cadex_mesh_worker.py` | The Phase 4 mesh domain on `Mod/Mesh`+`Mod/MeshPart`: tessellate/import/transform/boolean/decimate, canonical vertex/facet ordering + vertex-set digest fingerprint (ADR-016). The api also owns `payload_tree_is_deterministic`, which `part.shape_from_mesh` applies at script-eval time (ADR-043); the worker's `canonical_mesh_from_payload` is the BREP-ingest entry point the part worker is *handed* rather than imports, because the part worker is in cadexd's closure and this one deliberately is not. `[Cadex-new]` |
| `cadex_domain_api.py` / `cadex_domain_worker.py` | Shared domain API/worker plumbing (`_execute_source` is the composition substrate). `[VibeCAD-era]` |
| `CadexGeometryWorker.cpp` | Isolated C++ BREP validation / distance worker. `[VibeCAD-era]` |

### The shell

There is no shell under `src/`. `CadexGui`, `CadexSession`,
`CadexProvider`, `CadexCore`, `CadexAuth`, `CadexCodex`, `CadexPreferences`,
`CadexTransactions`, `CadexEditState`, `CadexGrid`, `CadexParametersPanel`,
`CadexScriptView`, the `tool_impl` package, `CadexdClient` and
`CadexShellHydration` were all deleted in Phase 7 (ADR-021). The shell is
`shell/scripts/addons_core/mesh_agent/`, and it speaks the protocol in
`docs/INTEGRATION.md` — a different process, not a different import path.

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
| `CadexInspection.py` | The bounded `inspect` read surface (scopes `document`, `object`, `script`, `api`, `image`, `output`, `assets`; the last two added in ADR-043 — per-output facts from the pinned accepted attempt, and the importable-asset listing. `selection` was shell-only and is gone). |
| `CadexReferenceContracts.py` | Geometry pins: shared handle + owner + subelement hint + geometric fingerprint, and fingerprint re-resolution when the revision moved. |
| `CadexPinResolution.py` | Resolves a pick or fingerprint against the accepted revision's staged BREP. |
| `CadexSubshapeQuery.py` | The selector vocabulary a pin *and* a script argument both speak — since Phase 10b the five index-taking part ops resolve through it, so naming geometry means the same thing in chat and in the script. |
| `CadexModelingSurface.py` | The global project surface id (any workbench, one script). |

### Project store `[Cadex-new]`

`src/Mod/cadex/CadexProject.py`. Root: `$CADEX_HOME` if set, else the
appdata dir + `Cadex` (e.g. `~/Library/Application Support/cadex/Cadex` on
macOS). Layout:

```
<root>/projects/<slug>-<hash8>/
  project.cadex.json            project manifest
  script.py                     THE project script (sole source of truth)
  script_history/               last 25 accepted sources + history.json (ADR-045)
  script.json                   schema cadex-project-script-v1: param specs
                                cache + values, working/accepted revision,
                                accepted contract, accepted_digest,
                                accepted_attempt (staged-artifact locator;
                                that attempt dir is pinned, Phase 5.2),
                                latest candidate
  script_artifacts/<revision>/  staged worker attempts + serialized outputs
                                (+ display/ tessellation buffers when
                                requested)
  assets/                       flat .stl/.obj/.ply the script imports by
                                name (mesh.import_file, part.shape_from_mesh);
                                bounded at 64 files / 128 MB, written only by
                                the put_asset op (ADR-043)
```

**cadexd is the sole writer.** Every byte that lands in the store goes
through an op; the shell asks the engine what is in there (`inspect`), which
is why the store's layout is not part of the contract in
`docs/INTEGRATION.md` — and why it must not become one now that both halves
are in one tree.

The shell reads exactly one directory of it, and only ever to hand the paths
straight back: on Save-As it lists `assets/` in the root it is *leaving*, so
that `put_asset` can carry the user's imported geometry into the new project
(ADR-046). Assets are the one thing in the store the shell supplied in the
first place, and the shell already chooses where the store lives (below).
Nothing else in the store is read by the shell, and nothing at all is
written by it.

In practice the root is chosen by the shell, not by `$CADEX_HOME`: the
Blender shell passes `<blend-dir>/<stem>.cadex` as `project_root`, so a
model lives beside the file that displays it.

`CadexProjectScriptStore` (`CadexScriptStore.py`, split out of
`CadexProject.py` in C1) owns `script.py`/`script.json` with atomic,
schema-checked writes. A candidate is written before it runs and rolled back
if it fails, so `script.py` only ever holds a source that executed; the
accepted revision's own source stays pinned in its staging directory and is
readable with `read_accepted_source()`, which is what the restore pass falls
back to when the working script will not run at all (ADR-044). **Conversation history is no longer here**: it lives
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

(226 passing as of 2026-07-26. The count *fell* from 425: Phase 7 deleted
the Qt shell and the provider stack along with their suites — 36 test files
to 20 — and ADR-030 removed four more that drove the shell's deleted local
bpy path. Fewer tests over less code, not less coverage.)

**The contract guardrails.** `test_project_tool_surface.py` pins the exact
`xscript.project.*` tool surface and asserts dissolved per-domain operations
and culled modules stay gone. `test_engine_purity_guardrails.py` pins the
process boundary — nothing under `src/Mod/cadex/**` may import `PySide*`,
`FreeCADGui`, `tool_impl` or `jsonschema`, cadexd's module closure must equal
a declared list, and `docs/INTEGRATION.md`'s op table must equal
`OP_ARG_SPECS`. `test_cadexd_protocol.py` pins the op list itself and
`test_response_schemas.py` the reply shapes (ADR-027).

**The integration drivers**, all headless under FreeCADCmd:
`project_xscript_api_integration.py` (the full lifecycle),
`tessellation_id_map_integration.py`, `pin_resolution_integration.py`, and
`cadexd_latency_integration.py` (the slider-drag bar over raw NDJSON).

**The five ctests**, in `tests/CMakeLists.txt`:

| ctest | Proves |
|---|---|
| `CadexProjectRebuildDigest` | delete the document, rebuild from the script, digests match — rebuild-vs-accepted *and* rebuild-vs-rebuild |
| `CadexdLifecycle` | open → mutate → inspect → resolve_pin → `kill -9` → respawn → restore digest equality → mid-run cancel |
| `CadexSubshapeEnumeration` | the OCCT ordering fingerprint, so a version bump cannot silently re-index saved scripts (ADR-027) |
| `CadexResponseSchemas` | the golden per-op response shapes |
| `CadexEnginePayloadSmoke` | the *packaged* payload answers the protocol through its own manifest (ADR-023) |

The ones needing a binary skip themselves when no FreeCADCmd is available.
ctest overall has ~160 pre-existing environmental failures — diff against
`build/ctest_baseline_failures.txt`, never expect 100%.

The product gate lives on the other side of the boundary:
`pixi run gate` runs `shell/tests/python/bl_mesh_agent_cadex.py` against the
built bundle and prints one `CADEX-BLENDER-GATE` line.

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

`pixi run setup && pixi run app` builds everything and launches it. What
that runs, and why it is not one CMake project:

**Two toolchains, deliberately isolated.** The engine builds inside the
pixi/conda-forge environment — OCCT 7.8.1, Qt6, conda compilers, a conda
sysroot. The shell builds against `shell/lib/<platform>`, Blender's own
prebuilt library set, with Xcode and a homebrew `cmake`/`ninja`. The two
overlap on names: zlib, libpng, OpenSSL, Python all exist in both, at
different versions. Put `.pixi/envs/default/bin` on `PATH` during a shell
configure and CMake silently resolves the conda ones, which fails at link
time or, worse, produces a binary that misbehaves at runtime.

`package/app/build_app.sh` is what keeps them apart. It filters the pixi and
conda entries out of `PATH` and unsets the ~50 variables conda activation
exports (`CONDA_PREFIX`, `CMAKE_PREFIX_PATH`, `CFLAGS`, `SDKROOT`, `CC`,
`PKG_CONFIG_PATH`, …) before invoking `cmake` on `shell/`. That is why
`pixi run build-shell` shells out to a script instead of being a
`cmd = ["cmake", ...]` task: pixi would otherwise hand cmake the exact
environment being removed. *Verified by construction:* the resulting
`shell/build_darwin/CMakeCache.txt` is identical to a configure run from the
old standalone shell repository apart from the source path — zero references
to `.pixi`, Python resolved out of `shell/lib/macos_arm64`, compilers
`/usr/bin/cc` and `/usr/bin/c++`.

The steps:

| Task | Builds | With |
|---|---|---|
| `pixi run setup` | — | `git submodule update` for `shell/lib/<platform>` (1.3 GB, git-lfs) |
| `pixi run build-engine` | `build/release/bin/{FreeCADCmd,CadexGeometryWorker}` | pixi env, `BUILD_GUI=OFF` |
| `pixi run stage-engine` | `build/engine/cadex-engine-<v>-<os>-<arch>/` + its manifest | pixi env |
| `pixi run build-shell` | `shell/build_darwin/bin/Cadex.app`, engine inside it | **scrubbed** env, `shell/lib` |

- Artifacts, engine: `build/release/bin/FreeCADCmd` and
  `build/release/bin/CadexGeometryWorker`. **There is no `FreeCAD` binary
  in a release build** — that is the point of Phase 7. Debug builds still
  produce one, as an engineering convenience only.
- Run the engine's own tests with `pixi run python -m pytest
  src/Mod/cadex/cadex_tests` (no build needed; FreeCAD is stubbed).
  `pixi run python src/Mod/cadex/cadex_tests/cadexd_latency_integration.py`
  is the slider-drag latency bar, driven over raw NDJSON. `pixi run gate`
  is the product gate against the built bundle.
- Packaging: `docs/cadex-release-packaging.md` — one bundle.

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
