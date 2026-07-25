# BLENDER.md — The mesh Fork and the Future Shell

Verified against source: 2026-07-25 (repo: `/Users/theo/mesh`, branch `mesh-main`)

Cadex's confirmed endpoint is a Blender shell (see `docs/INTEGRATION.md` and
`docs/DECISIONS.md`). The shell lives in a separate repository: **mesh**, a
Blender 5.0.3-alpha fork at `/Users/theo/mesh`. This document records what
exists there today and which Blender internals matter for the integration, so
future agents do not have to re-explore that repo.

Everything here is `[Cadex-new]` unless marked as upstream Blender.

---

## 1. Repo policy: additive-only

- Branch: `mesh-main`. Merge strategy: `git merge <upstream tag>` (never
  rebase) to keep the conflict surface minimal.
- Policy through the fork's Phase 3 (from `docs/mesh/UPSTREAM_DIFFS.md`):
  **additive only** — new files, zero edits to upstream Blender code. As of
  2026-07-24 the modified-upstream-files ledger reads "(none yet)"; the first
  upstream edits are expected in the fork's Phase 4 (default app template
  selection, branding).
- New files so far: the `mesh_agent` add-on, the Mesh app template, tests, and
  `docs/mesh/`.

This mirrors cadex's own conservative stance toward inherited FreeCAD core
(see `CLAUDE.md`).

## 2. The prototype: `scripts/addons_core/mesh_agent/`

This add-on is the working prototype of the exact target UX: a chat-driven,
single-script parametric modeler inside Blender. It is the UX north star for
cadex (`docs/VISION.md`) and the concrete integration point for the future
`cadexd` backend (Phase 6 in `docs/ROADMAP.md`).

### File map

| File | Role |
|---|---|
| `__init__.py` | Add-on registration; preferences (model selection, Claude CLI path, tool-call limit); save/load lifecycle handlers; undo-batching hookup. |
| `agent.py` | Turn orchestration and event loop. Queues tool calls from the bridge; drains them on the main thread; pushes **one undo step per chat turn**. |
| `model.py` | Script storage + parametric rebuild. Source lives in `bpy.data.texts["model.py"]`; manages the dynamic PropertyGroup at `scene.mesh_params`; 0.15 s debounced rebuild on slider drag. |
| `model_api.py` | The script-facing API imported as `mesh_model`. `params()` declares Float/Int/Bool/Color parameter specs with defaults and returns current effective values. |
| `bridge.py` | Localhost TCP server (127.0.0.1, auto-assigned port, 16-byte hex token auth). Two wire ops: `list_tools`, `call`. Queues socket-thread requests for main-thread execution. |
| `mcp_shim.py` | Standalone MCP stdio server spawned by the Claude CLI via `--mcp-config`. No `bpy` import; relays MCP tool calls to the bridge over TCP. |
| `backend.py` | Spawns `claude -p` as a subprocess per turn; writes the MCP config (shim path/port/token); session continuity via `--resume <session-id>`. |
| `tools.py` | Tool definitions/executors. Tools: `get_script`, `write_script`, `set_params`, `get_attached_image`, `scene_summary`, `viewport_screenshot`, `export_stl`, `focus_view`. Marks `write_script`/`set_params` as mutating for undo counting. |
| `ui.py` | Chat panel in the 3D-viewport sidebar plus operators (send, cancel, attach image, paste); the chat input bar is rewired into the Properties header at the bottom of the right panel. |
| `history.py` | Chat transcript as JSON in `bpy.data.texts["mesh_chat.json"]`; persists inside the .blend file. |
| `capture.py` | Viewport screenshot (base64 PNG) and attached-image loading (downscaled, default max 768 px). |
| `scene_graph.py` | JSON scene summarizer: object types, transforms, dimensions, modifiers, materials. |
| `validation.py` | Part-Design-mode geometry checker (evaluated mesh + BMesh analysis): boundary/non-manifold edges, zero-area faces, self-intersections, etc.; results appended to the rebuild report. |
| `modes.py` | Mode system (currently a CAD overlay): mode-specific system-prompt overlays and a validation flag, stored in a scene property. |
| `cad_api.py` | `mesh_cad` module importable inside scripts: millimeter-based solid-modeling helpers (boxes, cylinders, gears, booleans with cleanup). |
| `mock_backend.py` | Test harness that replays scripted turns through the real bridge without spawning Claude. |
| `cadexd_client.py` | **Phase 6 (ADR-019).** Dependency-free NDJSON stdio client for cadexd; spawns `FreeCADCmd` (add-on preference / `MESH_FREECADCMD` / PATH), ready banner, serialized requests, cancel, crash envelopes. No `bpy`, no cadex imports. |
| `cadex_backend.py` | Per-scene cadexd session: project root beside the .blend (`<stem>.cadex/`), revision-guarded `write_script`/`set_params` with stale-revision self-heal, engine params bridged into `scene.mesh_params`, draft-while-dragging + background standard refine. |
| `cadex_hydrate.py` | `cadex-tessellation-v1` buffers → Model-collection mesh objects: `cadex_face` INT face attribute (1-based BREP ids), `cadex_edge` wire children, placements, contract-driven GC by `cadex_output` property. |
| `cadex_pick.py` | Viewport pick → polygon → `cadex_face` → `resolve_pin`; resolved pins queue onto the next chat message (like image attachments). Operator `mesh_agent.pick_pin`. |

### The model.py loop (source of truth)

- The **single script** is the artifact. It is stored as a text datablock
  (`bpy.data.texts["model.py"]`, `use_fake_user=True` so it persists), and
  executed with `compile()` + `exec()` in a namespace where `bpy` and
  `mesh_model` are available.
- Rebuild clears the "Model" collection before running, so the scene is a
  **rebuildable cache** of the script — the same principle cadex is adopting
  for its document (`docs/XSCRIPT.md`, target section).
- Parameters: `mesh_model.params()` specs are collected during exec, then
  mirrored into a dynamically registered PropertyGroup at `scene.mesh_params`.
  Values live in scene ID properties (saved with the .blend), keyed by
  parameter id so they survive script edits that keep ids stable. The spec
  JSON is cached in a scene property so sliders restore on file load without
  re-running the script, and the PropertyGroup class is only re-registered
  when the spec JSON changes (prevents a class swap mid-drag).
- Slider drag → `_on_param_update()` → `_schedule_rebuild()` → 0.15 s
  `bpy.app.timers` debounce → rebuild → `bpy.ops.ed.undo_push()` on success.
  In background mode the rebuild runs immediately (no timer).

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

## 4. Working-state note

As of 2026-07-25 the mesh working tree is **dirty**: the CAD
mode/validation layer (`cad_api.py`, `modes.py`, `validation.py`,
`tests/eval/`, `bl_mesh_agent_cad.py`) and the Phase 6 cadex backend
(`cadexd_client.py`, `cadex_backend.py`, `cadex_hydrate.py`,
`cadex_pick.py`, `bl_mesh_agent_cadex.py`, small routing edits to
`model/tools/agent/ui/modes/__init__`) are uncommitted. All three
headless suites (`bl_mesh_agent`, `bl_mesh_agent_cad`,
`bl_mesh_agent_cadex`) pass. Verify current state before building on it.

## 5. What carried from mesh_agent into the cadex integration (Phase 6, landed)

Implemented 2026-07-25 (ADR-019) as the "Cadex CAD" assistant mode — the
local-exec path stays alongside; `modes.py` selects the backend per scene:

| mesh_agent concept | cadex counterpart (shipped) |
|---|---|
| `model.py` in `bpy.data.texts` as sole source of truth | THE xscript project script in the cadexd store; the text block is a read-only mirror |
| `mesh_model.params()` → `scene.mesh_params` sliders | Engine `param_specs` bridged into the same `scene.mesh_params` group (`cadex_backend._bridge_params`) |
| Local `exec()` of the script | `write_script`/`set_params` through cadexd; tessellated BREP + ID maps hydrated into the Model collection (`cadex_hydrate.py`) |
| `scene_summary` / `viewport_screenshot` tools | Unchanged (they read the hydrated scene) |
| Picking a Blender face | `mesh_agent.pick_pin`: ray-cast → `cadex_face` attribute → `resolve_pin` → `@face-N` pin on the next message |
| One `undo_push` per turn | Unchanged (verified in cadex mode) |

Gate evidence lives in `tests/python/bl_mesh_agent_cadex.py` (run:
`MESH_FREECADCMD=<cadex>/build/release/bin/FreeCADCmd blender --background
--factory-startup --python tests/python/bl_mesh_agent_cadex.py`) and is
summarized in `docs/INTEGRATION.md` gate status + ADR-019.
