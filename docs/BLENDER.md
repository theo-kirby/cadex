# BLENDER.md — The Shell

Verified against source: 2026-07-25

**The shell is the product, and since ADR-030 it is in this repository**, at
`shell/` — a Blender fork whose `mesh_agent` add-on is the interface. Nothing
under `src/` has a UI, so this document is the reference for where the
interface actually lives: its files, its tools, how to run its suites, and
which Blender internals the integration depends on.

Companion documents: `docs/INTEGRATION.md` is the wire contract between the
two halves, and `docs/BLENDER-TREE.md` is the inherited-tree ledger — what is
kept, what is a removal candidate, and the complete three-file diff against
upstream Blender. This one is about how the shell works.

**How to run the shell's suites:**

```bash
pixi run gate     # bl_mesh_agent_cadex.py against the built bundle,
                  # with every MESH_* engine override unset

# or by hand, e.g. the engine-free agent suite
bash package/app/build_app.sh gate tests/python/bl_mesh_agent.py
```

`pixi run gate` prints one `CADEX-BLENDER-GATE {...}` line: picking fidelity,
slider latency, restore, cancellation, and whether the engine came from the
bundle.

Engine changes need `pixi run build-engine` to reach `build/release/Mod/cadex`,
and `pixi run stage-engine && pixi run build-shell` to reach the *bundled*
engine the gate actually runs.

Everything here is `[Cadex-new]` unless marked as upstream Blender.

---

## 1. Repo policy: every upstream edit is listed

- **Squashed, not tracked.** `shell/` is a snapshot of the Blender fork
  (ADR-030); we delete from it and do not merge upstream tags into it. The
  branch-and-merge policy that governed the standalone repository is
  therefore retired, and with it the reason the delta had to stay tiny —
  but the delta *does* stay tiny, because a small edit surface is still what
  makes the tree legible and a future upstream re-baseline possible at all.
- **The additive-only policy ended with Phase 7** (ADR-020 decision 6,
  ADR-024). Shipping one application that works with no configuration needed
  edits to three upstream files; the Cadex bundle identity (ADR-030) reused
  the same three plus the macOS `Info.plist`.
- The rule is **"every edit is listed in `docs/BLENDER-TREE.md` §2, kept
  minimal, and justified"** — each row says what changed, why, and what a
  merge conflict in it would mean.

This mirrors the stance toward inherited FreeCAD core (see `CLAUDE.md`),
which likewise moved from "don't touch" to "reduce the delta where you can,
and say what you did" (ADR-022).

## 2. The add-on: `shell/scripts/addons_core/mesh_agent/`

A chat-driven, single-script parametric modeler inside Blender. It is the UX
that `docs/VISION.md` describes, and the protocol client that
`docs/INTEGRATION.md` specifies.

### File map

| File | Role |
|---|---|
| `__init__.py` | Add-on registration; preferences (model selection, Claude CLI path, tool-call limit); save/load lifecycle handlers; undo-batching hookup. |
| `agent.py` | Turn orchestration and event loop. Queues tool calls from the bridge; drains them on the main thread; pushes **one undo step per chat turn**. |
| `model.py` | The script mirror (`bpy.data.texts["model.py"]`, read-only) and the dynamic PropertyGroup at `scene.mesh_params`; 0.15 s debounced rebuild on slider drag, dispatched to the engine. |
| `model_api.py` | `clamp()` — coerce a value to its spec's type and range. All that is left of a script-facing API that no script imports any more (ADR-030). |
| `bridge.py` | Localhost TCP server (127.0.0.1, auto-assigned port, 16-byte hex token auth). Two wire ops: `list_tools`, `call`. Queues socket-thread requests for main-thread execution. |
| `mcp_shim.py` | Standalone MCP stdio server spawned by the Claude CLI via `--mcp-config`. No `bpy` import; relays MCP tool calls to the bridge over TCP. |
| `backend.py` | Spawns `claude -p` as a subprocess per turn; writes the MCP config (shim path/port/token); session continuity via `--resume <session-id>`. |
| `tools.py` | Tool definitions/executors. Tools: `get_script`, `write_script`, `edit_script`, `set_params`, `inspect_model`, `describe_cad_api`, `get_attached_image`, `scene_summary`, `viewport_screenshot`, `export_stl`, `focus_view`. Marks `write_script`/`edit_script`/`set_params` as mutating for undo counting, and preflights the engine-reaching ones so a missing engine reads as one sentence. |
| `ui.py` | Chat panel in the 3D-viewport sidebar plus operators (send, cancel, attach image, paste); the chat input bar is rewired into the Properties header at the bottom of the right panel. |
| `history.py` | Chat transcript as JSON in `bpy.data.texts["mesh_chat.json"]`; persists inside the .blend file. |
| `capture.py` | Viewport screenshot (base64 PNG) and attached-image loading (downscaled, default max 768 px). |
| `modes.py` | The Cadex system-prompt overlay and `system_prompt()`. What remains of a three-mode registry after ADR-030 collapsed it to one. |
| `mock_backend.py` | Test harness that replays scripted turns through the real bridge without spawning Claude. |
| `cadexd_client.py` | **Phase 6 (ADR-019).** Dependency-free NDJSON stdio client for cadexd; spawns `FreeCADCmd` (add-on preference / `MESH_FREECADCMD` / bundled manifest / PATH), ready banner, serialized requests, cancel, crash envelopes. No `bpy`, **no cadex imports** — that last part is a licence boundary, not a style choice, and one repository does not relax it. |
| `cadex_backend.py` | Per-scene cadexd session: project root beside the .blend (`<stem>.cadex/`), revision-guarded `write_script`/`set_params` with stale-revision self-heal, engine params bridged into `scene.mesh_params`, draft-while-dragging + background standard refine. |
| `cadex_hydrate.py` | `cadex-tessellation-v1` buffers → Model-collection mesh objects: `cadex_face` INT face attribute (1-based BREP ids), `cadex_edge` wire children, placements, contract-driven GC by `cadex_output` property. |
| `cadex_pick.py` | Viewport pick → polygon → `cadex_face` → `resolve_pin`; resolved pins queue onto the next chat message (like image attachments). Operator `mesh_agent.pick_pin`. |

### The script loop (source of truth)

- The **single script** is the artifact, and it lives in the engine's project
  store, not here. `bpy.data.texts["model.py"]` (`use_fake_user=True`) is a
  **read-only mirror** of it, so the script is visible and searchable in
  Blender without being editable behind the engine's back.
- The scene is a **rebuildable cache** of that script — the same principle
  the engine applies to its document (`docs/XSCRIPT.md`). What the Model
  collection holds is tessellated BREP the engine returned, hydrated by
  `cadex_hydrate.py`, not geometry Blender authored.
- Parameters: the engine's `param_specs` are bridged into a dynamically
  registered PropertyGroup at `scene.mesh_params`
  (`cadex_backend._bridge_params`). Values live in scene ID properties (saved
  with the .blend), keyed by parameter id so they survive script edits that
  keep ids stable. The spec JSON is cached in a scene property so sliders
  restore on file load without asking the engine, and the PropertyGroup class
  is only re-registered when the spec JSON changes (prevents a class swap
  mid-drag).
- Slider drag → `_on_param_update()` → `_schedule_rebuild()` → 0.15 s
  `bpy.app.timers` debounce → one revision-guarded `set_params` to the engine,
  draft-quality tessellation while dragging with a background standard
  refine → `bpy.ops.ed.undo_push()` on success. In background mode the
  rebuild runs immediately (no timer).
- **There is one backend.** Until ADR-030 there were two, chosen by a mode
  dropdown: this one, and a local path that `exec()`d the script against
  `bpy`. The local path and everything serving it — `cad_api.py` (the
  `mesh_cad` millimetre solid-modelling helpers), `validation.py` (the BMesh
  geometry checker), `scene_graph.py`, most of `model_api.py`, and
  `tests/python/bl_mesh_agent_cad.py` — were deleted. That was where nearly
  all the deep Blender coupling lived: BOOLEAN/BEVEL modifiers, the
  depsgraph, BVHTree, `orphans_purge`.

### The AI bridge

- Per turn, `backend.py` spawns the Claude Code CLI (`claude -p … --resume`)
  with an MCP config pointing at `mcp_shim.py`. The shim speaks MCP over
  stdio and relays each tool call to `bridge.py` over authenticated localhost
  TCP; the bridge queues the call for the Blender main thread and returns the
  result.
- Undo policy: mutating tool calls (`write_script`, `set_params`) increment a
  counter; when the turn finishes, if any mutation happened, exactly one
  `ed.undo_push()` is issued, labeled "Mesh: " + the first 60 chars of the
  user prompt. **One user turn = one undo step.**

### The app template: `scripts/startup/bl_app_templates_system/Mesh/`

`__init__.py` reshapes Blender into the product layout:

- Removes all workspaces but one; collapses all areas to a single 3D viewport;
  then splits **50/50 vertical** — left half 3D viewport (headers hidden,
  solid shading, toon matcap), right half a Properties editor pinned to the
  Tool tab hosting the chat and param panels.
- Blanks the top menu bar; flips the Properties header (which hosts the chat
  input bar) to the bottom of the right panel; hides foreign Tool-category
  panels while keeping `VIEW3D_PT_mesh_chat` / `VIEW3D_PT_mesh_params`.
- Applied via a repeating `bpy.app.timers` state machine because area
  geometry only settles between redraws.

## 3. Blender internals relevant to the shell integration

All upstream Blender code, listed here as orientation for Phase 6 work
(paths relative to `/Users/theo/mesh`):

| Area | Path | Why it matters |
|---|---|---|
| Draw engines | `source/blender/draw/engines/` (`eevee`, `workbench`, `overlay`, `select`, `compositor`, `gpencil`, `image`, `external`) | Rendering quality/feel that Coin3D can't match; `overlay` and `select` are where BREP face/edge highlighting and picking feedback would hook in. |
| BMesh | `source/blender/bmesh/` | Native mesh editing; the reason real mesh editing waits for the Blender shell rather than being built on FreeCAD's Mesh module. |
| Attributes / CustomData | mesh attribute system (accessed via BMesh/Mesh APIs) | Where per-face/per-edge **BREP ID maps** land when cadexd streams tessellated shapes, so picking can resolve back to `@face-N` / `@edge-N` pins. |
| DNA/RNA | `source/blender/makesdna/`, `source/blender/makesrna/` | Blender's struct + reflection system; how `scene.mesh_params` properties exist; a model for parameter reflection (see `docs/IDEAS.md`). |
| Depsgraph | `source/blender/depsgraph/` | Evaluation/dirty-propagation if cadexd outputs ever become depsgraph-integrated rather than rebuild-on-demand. |
| Window manager / editors | `source/blender/windowmanager/`, `source/blender/editors/` | Layout, operators, event handling — what the app template scripts against. |
| Undo | `source/blender/blenkernel/intern/undo_system.cc`, `blender_undo.cc` (memfile), headers `BKE_undo_system.hh` / `BKE_blender_undo.hh` | Memfile snapshot undo; why one `undo_push` per turn is cheap and sufficient. |

## 4. The shell's own machinery (Phase 7)

Added in Phase 7 (ADR-023/024); the bundled engine itself is §6 below.

| Concern | Where |
|---|---|
| Engine discovery | `cadexd_client.find_freecadcmd` / `read_engine_manifest` / `preflight` — preference → `MESH_FREECADCMD` → bundled manifest → `PATH` |
| Bundled payload | `cadex_backend.bundle_roots()` from `bpy.app.binary_path`; installed by `WITH_CADEX_ENGINE` |
| Engine build | `pixi run stage-engine` then `pixi run build-shell`; installed by `WITH_CADEX_ENGINE`. The version pin and SHA256 fetch that used to sit here are deleted (ADR-030) — the payload no longer crosses a repository boundary |
| Off-thread modeling | `cadex_backend.Lifecycle` + `tools.Pending`; the agent's drain loop polls, so Blender stays live during a rebuild |
| Cancellation | a per-turn `threading.Event` bound into the client's `cancellation_check`; the engine answers `RUN_CANCELLED` |
| API truth | the `describe_cad_api` tool; the mode prompt carries **no** API names |
| Conversation | transcript + Claude `session_id` in the `.blend` (`history.py`) |
| CI | `.github/workflows/cadex-app.yml` — engine → payload → shell, then the suites with no engine env set |

## 5. What carried from mesh_agent into the cadex integration (Phase 6, landed)

Implemented 2026-07-25 (ADR-019) as the "Cadex CAD" assistant mode, which
ran alongside the local-exec path until ADR-030 deleted that path and the
mode dropdown with it. The right-hand column is now simply how the shell
works:

| mesh_agent concept | cadex counterpart (shipped) |
|---|---|
| `model.py` in `bpy.data.texts` as sole source of truth | THE xscript project script in the cadexd store; the text block is a read-only mirror |
| `mesh_model.params()` → `scene.mesh_params` sliders | Engine `param_specs` bridged into the same `scene.mesh_params` group (`cadex_backend._bridge_params`) |
| Local `exec()` of the script | `write_script`/`set_params` through cadexd; tessellated BREP + ID maps hydrated into the Model collection (`cadex_hydrate.py`) — **deleted** on the left, ADR-030 |
| `scene_summary` / `viewport_screenshot` tools | Unchanged (they read the hydrated scene) |
| Picking a Blender face | `mesh_agent.pick_pin`: ray-cast → `cadex_face` attribute → `resolve_pin` → `@face-N` pin on the next message |
| One `undo_push` per turn | Unchanged (verified in cadex mode) |

Gate evidence lives in `shell/tests/python/bl_mesh_agent_cadex.py`
(`pixi run gate`) and is summarized in `docs/INTEGRATION.md` gate status,
ADR-019 and ADR-030.

## 6. The bundled engine

Absorbed from the shell's own `docs/mesh/CADEX_ENGINE.md`, deleted with the
two-repository split it documented; half of it described a fetch-and-verify
step that no longer exists (ADR-030).

**What ships**, inside the application bundle:

```
macOS    Cadex.app/Contents/Resources/cadex/
Linux    <install>/cadex/           (portable)
         <install>/<version>/cadex/ (system)
Windows  <install>/cadex/
```

```
cadex-engine.json     the discovery manifest
bin/freecadcmd        the engine host; cadexd runs inside it
bin/CadexGeometryWorker
bin/python
lib/                  no Qt GUI, no PySide, no Coin
Mod/cadex/            cadexd and the xscript pipeline
Mod/{Part,PartDesign,Sketcher,Assembly,Mesh,MeshPart,Import,Material,Measure,Show}
```

It carries no widget toolkit — the engine is built `BUILD_GUI=OFF` — but it
does carry Qt6Core, Qt6Xml, Qt6Concurrent and Qt6Network, because FreeCAD's
App layer links them for XML parsing and string handling. Non-GUI Qt is
unavoidable; Qt GUI is absent and asserted absent at packaging time.

**Discovery.** Finding `cadex-engine.json` is the whole of it: the manifest
names the binary and the module directory with paths relative to itself, so
nothing guesses at a platform layout. A manifest whose `schema` or `protocol`
the add-on does not recognise is **refused**, not attempted — a version
mismatch should fail at preflight with a sentence, not mid-request with a
protocol error.

Resolution order (`cadexd_client.find_freecadcmd`):

1. the **Cadex Engine** add-on preference, if set;
2. `MESH_FREECADCMD`;
3. the **bundled payload's manifest**, relative to `bpy.app.binary_path`;
4. `FreeCADCmd` / `freecadcmd` on `PATH`.

`MESH_CADEX_ENGINE` overrides step 3 with a directory of your choosing;
`MESH_CADEXD_MODULE` overrides the module directory alone.
`cadex_backend.preflight()` returns `(ok, reason, remedy)` and is what the
preferences panel, the chat panel and the first engine tool call all report
from, so one problem reads as one problem.

**The zero-configuration criterion** is that with all three `MESH_*`
variables unset, step 3 finds the engine. That is what `pixi run gate`
asserts via `engine_from_bundle: true`, and it is the Phase 7 exit criterion
that had to survive the merge intact.

**Pointing at a development engine.** `pixi run build-engine && pixi run
stage-engine && pixi run build-shell` rebuilds the bundled one, which is
usually what you want. To test a payload the bundle does not carry:

```bash
export MESH_CADEX_ENGINE=/path/to/cadex-engine-<version>-<os>-<arch>
# or a plain engine build tree:
export MESH_FREECADCMD=/path/to/build/release/bin/FreeCADCmd
```

The second form needs `Mod/cadex` beside the binary's directory or its
parent; both installed layouts are probed.

**Protocol version.** If the wire protocol changes, the engine bumps
`protocol` in the manifest and `PROTOCOL_SCHEMA` in `cadexd_client.py` must
move with it in the same commit — an unrecognised protocol is refused at
discovery, so a mismatched pair fails at preflight rather than at runtime.
Being in one repository makes that a single commit rather than a release
sequence; it does not make it optional.

**Open.** macOS codesigning of the embedded engine (hardened-runtime
entitlements: `freecadcmd` spawns subprocesses and dlopens OCCT) is not yet
exercised end to end through notarization.
