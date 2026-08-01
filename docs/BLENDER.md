# BLENDER.md — The Shell

Verified against source: 2026-08-01

**The shell is the product, and since ADR-030 it is in this repository**, at
`shell/` — a Blender fork whose `mesh_agent` add-on is the interface. Nothing
under `src/` has a UI, so this document is the reference for where the
interface actually lives: its files, its tools, how to run its suites, and
which Blender internals the integration depends on.

Companion documents: `docs/INTEGRATION.md` is the wire contract between the
two halves, and `docs/BLENDER-TREE.md` is the inherited-tree ledger — what is
kept, what is a removal candidate, and the complete diff against upstream
Blender (§2a identity, §2b the Cadex editors, §2c the message box). This one
is about how the shell works.

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
  the same three plus the macOS `Info.plist`. **ADR-035 and ADR-036 roughly
  tripled that surface**, knowingly: owning two space types and not shipping
  nine others is additive in almost every file it touches, it bought the
  removal of ~550 lines of Python layout hacks, and Phase 12 retires the
  Blender shell wholesale. The delta is now grouped by how it ages —
  `docs/BLENDER-TREE.md` §2a identity, §2b the Cadex editors, §2c the message
  box — rather than counted as one number.
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
| `model.py` | The script mirror (`bpy.data.texts["model.py"]`, soft read-only) and the dynamic PropertyGroup at `scene.mesh_params`; 0.15 s debounced rebuild on slider drag, dispatched to the engine, plus an undebounced ~30 Hz `preview_params` pump in front of it for motion parameters (ADR-055). `set_script()` is a no-op when the source is unchanged and restores the cursor when it is not, and stamps the digest the dirty marking compares; `last_error()` carries a failed drag to the panel (ADR-039). `rewrite_defaults()` splices slider values into the script's `num()` declarations for **Apply as Defaults** (ADR-040) — pure text in, text out. |
| `model_api.py` | `clamp()` — coerce a value to its spec's type and range. All that is left of a script-facing API that no script imports any more (ADR-030). |
| `bridge.py` | Localhost TCP server (127.0.0.1, auto-assigned port, 16-byte hex token auth). Two wire ops: `list_tools`, `call`. Queues socket-thread requests for main-thread execution. |
| `mcp_shim.py` | Standalone MCP stdio server spawned by the Claude CLI via `--mcp-config`. No `bpy` import; relays MCP tool calls to the bridge over TCP. |
| `backend.py` | Spawns `claude -p` as a subprocess per turn; writes the MCP config (shim path/port/token); session continuity via `--resume <session-id>`. |
| `tools.py` | Tool definitions/executors. Tools: `get_script`, `write_script`, `edit_script`, `restore_version`, `set_params`, `rebuild_model`, `inspect_model`, `describe_cad_api`, `get_attached_image`, `scene_summary`, `viewport_screenshot`, `export_stl`, `import_geometry`, `focus_view`. `import_geometry` copies an external STL/OBJ/PLY into the engine's asset store so a script can name it (ADR-043); `inspect_model` gained the `output` and `assets` scopes with it, and the `history` scope with ADR-045. `restore_version` puts a previously accepted version back — it reads `inspect scope=history` and writes the result through `write_script`, so a restored version re-runs and is re-accepted rather than trusted (ADR-045); `write_script` itself now refuses to drop outputs the model currently has unless `replace` is set, because "add a part" answered with a whole-script rewrite is how a project gets deleted. Marks `write_script`/`edit_script`/`restore_version`/`set_params`/`rebuild_model` as mutating for undo counting, and preflights the engine-reaching ones so a missing engine reads as one sentence. `rebuild_model` re-runs the script the engine already holds (ADR-039) — the tool to reach for when the model and the engine have drifted. |
| `ui.py` | The panels of the two Cadex editors — transcript, message box, parameter sliders — plus the operators (send, cancel, new chat, attach image, paste, toggle parameters, toggle script, rebuild from saved script, rebuild model, apply as defaults). No `poll` here asks *where* it is drawing: the space type answers that (ADR-035). The parameters panel draws a failed drag as an alert row with **Rebuild Model** beside it (ADR-039), and an **Apply as Defaults** button that is live only while a slider sits away from its declared default (ADR-040). |
| `spaces.py` | Headers for `CADEX_CHAT` and `CADEX_PARAMS`, and the script view: `MESH_AGENT_OT_show_script` (a **toggle** — a Text Editor on the `model.py` mirror, opened or closed), `MESH_AGENT_OT_revert_script`, and `CADEX_PT_script`, its sidebar panel, which says whether the buffer matches the model and offers **Apply to Model** / **Revert to Model** / **Rebuild Model** accordingly (ADR-039). Headers live here rather than in `bl_ui` because `bl_ui` is inherited and this is ours. |
| `topbar.py` | The Cadex top bar (ADR-041): `CADEX_MT_file` (New, Open…, Open Recent, Revert, Save, Save As…, Save Copy…, **Import Geometry…**, Import ▸, Export ▸, Quit) and `CADEX_MT_edit` (Undo, Redo, Preferences…), and the `install()` / `uninstall()` pair that swaps `TOPBAR_HT_upper_bar`'s draw. Everything the menus point at is a stock operator or a stock menu **except** `MESH_AGENT_OT_import_asset`, which has to be ours: stock Import loads into the Blender scene, which here is the display mirror, so importing *into the model* means a `put_asset` op (ADR-043). Registering the add-on does **not** install the bar — the app template does that, so `mesh_agent` in a stock Blender session leaves that session's bar alone; `unregister()` does uninstall, because a header naming menus that are gone draws errors. |
| `history.py` | Chat transcript as JSON in `bpy.data.texts["mesh_chat.json"]`; persists inside the .blend file. |
| `capture.py` | Viewport screenshot (base64 PNG) and attached-image loading (downscaled, default max 768 px). |
| `modes.py` | The Cadex system-prompt overlay and `system_prompt()`. What remains of a three-mode registry after ADR-030 collapsed it to one. |
| `mock_backend.py` | Test harness that replays scripted turns through the real bridge without spawning Claude. |
| `cadexd_client.py` | **Phase 6 (ADR-019).** Dependency-free NDJSON stdio client for cadexd; spawns `FreeCADCmd` (add-on preference / `MESH_FREECADCMD` / bundled manifest / PATH), ready banner, serialized requests, cancel, crash envelopes. No `bpy`, **no cadex imports** — that last part is a licence boundary, not a style choice, and one repository does not relax it. |
| `cadex_backend.py` | Per-scene cadexd session: project root beside the .blend (`<stem>.cadex/`), revision-guarded `write_script`/`set_params` with stale-revision self-heal, engine params bridged into `scene.mesh_params`, draft-while-dragging + background standard refine. |
| `cadex_animate.py` | an accepted simulation trace → F-Curves on the component instances: time-keyed (not frame-index-keyed), wxyz quaternions walked into one hemisphere, bulk `foreach_set` onto slotted actions, cleared and re-baked per revision. A sibling of `cadex_hydrate.py`, so a bad trace never costs you the geometry. |
| `cadex_hydrate.py` | `cadex-tessellation-v1` buffers → Model-collection mesh objects: `cadex_face` INT face attribute (1-based BREP ids), `cadex_edge` wire children, placements, contract-driven GC by `cadex_output` property. |
| `cadex_pick.py` | Viewport pick → a pin queued onto the next chat message (like image attachments), in two flavours sharing one eyedropper modal and one queue. **Face pin** (`mesh_agent.pick_pin`): polygon → `cadex_face` → `resolve_pin` → `@face-N`, BREP outputs only. **Point pin** (`mesh_agent.pick_point`, ADR-056): the ray-cast hit and its normal, pushed back through the object's placement into the output's own space — no engine round-trip, and it works on mesh outputs, which have no faces to name. A point and a direction *is* a `part.cable` port. |
| `wiring.py` | **ADR-066.** The Wiring graph's model: `CadexWiringTree`, `CadexBoardNode`, `CadexTerminalSocket`, `ensure_tree`, `sync_from_engine`, `rows_from_tree` and the 0.15 s debounced push. The graph is a *projection* of `inspect scope="wiring"` — nodes, sockets and links are rebuilt from the engine and never from the canvas, so a failed push resyncs rather than retries; the one thing it owns is `Node.location`. Two sockets per terminal (Blender refuses an input→input link), keyed by a registered `terminal` property (duplicate socket names dedup into `sda`/`sda_001`), with solder state carried as socket colour (a link holds no properties). |
| `wiring_ui.py` | **ADR-066.** Its chrome — header, two sidebar panels, `NODE_MT_add`, the sync operator. The only module in the add-on allowed to fail registration: a `Panel` naming an unregistered space type raises and would abort the whole loop (the ADR-036 failure), so it guards each class and sets `EDITOR_AVAILABLE = False`. That is what lets everything else run on a bundle built before the C++ half. |

### The script loop (source of truth)

- The **single script** is the artifact, and it lives in the engine's project
  store, not here. `bpy.data.texts["model.py"]` (`use_fake_user=True`) is a
  **mirror** of it, so the script is visible and searchable in Blender.
  `MESH_AGENT_OT_show_script` opens it in the stock **Text Editor** — no
  custom editor, because that buffer already exists and the Text Editor brings
  syntax highlighting, line numbers and find for free (ADR-035).
- The mirror is *soft* read-only, and the sidebar panel says so. Blender text
  datablocks have no read-only flag, and the two directions are not
  symmetric: `get_script` reads this buffer, so the assistant sees a hand edit
  at once, while `write_script` goes to the engine, so the engine does not —
  until **Apply to Model** (`MESH_AGENT_OT_adopt_script` →
  `cadex_backend.adopt_saved_script`) runs. Any *accepted* engine round-trip
  overwrites the buffer.
- Divergence is **marked, not inferred** (ADR-039). `model.set_script()` stamps
  the digest of what it wrote onto the text datablock as an ID property (so it
  saves with the .blend); `model.script_is_dirty()` compares it against the
  buffer, and `CADEX_PT_script` draws one of three states: matches the model,
  modified and not applied, or not in the model yet. A source the engine
  **refused** is mirrored with `accepted=False` — it stays in the buffer to be
  fixed and does not get the clean stamp. An unstamped buffer counts as clean,
  so a .blend saved before ADR-039 does not open with a false alert.
- Refreshing the mirror must not move the cursor: `set_script()` returns early
  when the buffer already holds the source, and saves/restores the cursor when
  it does not. The mirror is rewritten on every accepted request, so without
  that a slider drag fights anyone reading the script.
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
  mid-drag). The sliders are drawn by `CADEX_PARAMS_PT_parameters`, the sole
  occupant of the Cadex Parameters editor.
- The specs reach the shell two ways, and only one of them is free.
  `open_project` returns the whole script-state block; `inspect` — which is
  how `_refresh_script_state()` re-reads it after a `write_script` — is the
  assistant's *bounded* reader, so it pages and it replaces any value over
  1 KiB with a pointer to itself. `cadex_backend._inspect_full()` walks both
  (ADR-038). Read that before touching anything that consumes an `inspect`
  reply: taking the first page at face value is correct for a
  one-parameter fixture and empty for every real model.
- The sliders are an **override layer** over what the script declares, and
  **Apply as Defaults** collapses it: each declared parameter's `num()` default
  becomes the value its slider is sitting at, in the script itself
  (`model.rewrite_defaults` → `cadex_backend.apply_slider_defaults` →
  `write_script`). It splices only each default's own source span, so comments,
  spacing and every other argument survive byte for byte, and it refuses a
  dirty buffer rather than sweeping unapplied edits into the rewrite (ADR-040).
- Slider drag → `_on_param_update()` → `_schedule_rebuild()` → 0.15 s
  `bpy.app.timers` debounce → one revision-guarded `set_params` to the engine,
  draft-quality tessellation while dragging with a background standard
  refine → `bpy.ops.ed.undo_push()` on success. In background mode the
  rebuild runs immediately (no timer).
- **In front of that, for sliders that drive motion:** `_schedule_preview()`
  → `cadex_backend.note_preview()` → a ~30 Hz pump that keeps at most one
  `preview_params` in flight, drops every intermediate value, and is
  deliberately **not** debounced — a 33 ms engine behind a 150 ms debounce is
  still a 150 ms drag (ADR-055). The reply is placements, not a display
  block, so `cadex_hydrate.apply_placements()` sets `matrix_world` on the
  component instances and nothing else runs: no sidecar, no buffers, no mesh
  rebuild, no GC. Measured at **5.6 ms** median through the gate.

  It serves a subset of sliders by construction — a parameter that changes an
  output's definition is refused, correctly — so degrading cleanly is part of
  the contract: a refusal latches previews off for the rest of *that
  parameter's* drag (re-asking cannot change the answer), lifts when a
  different parameter moves or the drag settles, and **never** reaches
  `model.last_error()`. The debounced `set_params` behind it is the real
  answer either way, and it is the only thing that makes a change real.
- **A .blend and its `.cadex` are two halves of one model.** The file carries
  the baked tessellation, the `model.py` mirror, the specs JSON and the
  values; `<stem>.cadex/` carries the xscript source, the BREP artifacts and
  the accepted digest. `project_root()` derives the root from the file name
  every time, so duplicating a .blend (file manager or Save-As) names a
  project that does not exist — deliberately, since copying `.cadex` would
  fork the model's history behind the user's back. `open_project` **mkdirs
  the root it is handed**, so that missing project opens empty and `ok`;
  `_adopt_script_state(..., preserve_local=True)` is what stops that
  emptiness from erasing the specs and the mirror, and
  `cadex_backend.orphaned_project()` drives the **Rebuild From Saved Script**
  offer in the chat panel (ADR-033). That offer is reachable *before* any
  open — the root simply not existing is enough — because Save-As closes
  every session a moment after the new name takes effect (ADR-046).
  **Imported geometry is the one thing that does come across**: assets are
  inputs, not derived state, and a script that names one cannot re-run
  without it, so `migrate_assets()` carries `assets/` into the new project
  through `put_asset` when the script is adopted. `save_pre` is what records
  *which* project to carry from (`SOURCE_PROP` — `bpy.data.filepath` still
  names the old file there, and the value saves into the new one).
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

### The two Cadex editors

Chat and Parameters are **real Blender space types** — `SPACE_CADEX_CHAT` and
`SPACE_CADEX_PARAMS`, named entries in the editor-type dropdown that split,
dock and resize exactly like the 3D Viewport (ADR-035). Their C side is two
files, `source/blender/editors/space_cadex_{chat,params}/`, and both are
deliberately empty of content: everything drawn in them is a panel or header
registered by the add-on.

**Cadex Chat**, three regions:

| Region | Draws | Panel |
|---|---|---|
| `RGN_TYPE_WINDOW` | the transcript | `CADEX_CHAT_PT_transcript` |
| `RGN_TYPE_EXECUTE` | the message box and its button row | `CADEX_CHAT_PT_input` |
| `RGN_TYPE_HEADER` | model selector, Pin Face, Pin Point, the pinned count, the script button | `CADEX_CHAT_HT_header` |

`RGN_TYPE_EXECUTE` is the load-bearing part. `RGN_TYPE_IS_HEADER_ANY`
(`DNA_screen_types.h`) covers `HEADER`, `TOOL_HEADER`, `FOOTER`,
`ASSET_SHELF_HEADER` and `SCRUBBING` and deliberately **not** `EXECUTE` — so
an execute region is an ordinary sizable panel region, not subject to the
one-row limit that once forced the message box into a screen area of its own
(ADR-034). It is `RGN_ALIGN_BOTTOM`, `prefsizey = 6 * HEADERY`, and
user-resizable.

**Cadex Parameters**, two regions: `RGN_TYPE_WINDOW` for the sliders
(`CADEX_PARAMS_PT_parameters`) and a header. `mesh_agent.toggle_params` — the
`OPTIONS` button at the end of the chat button row, depressed while the editor
is open — closes it, or splits the viewport and sets `area.type`. That is the
whole operator now: no pointer bookkeeping and no retry timer, because there
is no space-data swap to wait on.

Neither space type has DNA fields of its own. Transcript scroll is region
state, parameter values live in `scene.mesh_params`, the model selector is an
add-on preference, and the draft message is a `WindowManager` property. DNA is
append-only forever, so keep it that way.

**What this replaced.** Until 2026-07-26 the three columns were three
*Properties* editors pinned to the Tool tab, drawing `bl_space_type='VIEW_3D'`
sidebar panels that only appeared there because the Properties Tool tab
mirrors the viewport's Tool-category sidebar. Which of the three an area *was*
got decided at draw time by comparing `area.x` and `area.y`, and every `poll()`
hung off that. `CADEX_PARAMS_PT_parameters` still says what ADR-032 said — an
empty model says so rather than the panel vanishing — but the caveat that its
poll was "about *where* this draws" is simply gone.

### The editor menu is short

The dropdown offers only what Cadex builds: 3D Viewport, Cadex Chat, Cadex
Parameters, **Wiring**, Properties, Outliner, Text Editor, Python Console,
Info, Preferences, File Browser. The dope sheet, graph editor, NLA, image/UV
editor, the four stock node editors, sequencer, spreadsheet, movie clip editor
and asset browser are not offered, because each destroyed the layout if picked
and none has a use in a CAD app.

The mechanism is **not registering the space type**: `rna_Area_ui_type_itemf`
(`makesrna/intern/rna_screen.cc`) skips any row whose `BKE_spacetype_from_id`
returns null, so eight `ED_spacetype_*()` calls simply left
`ED_spacetypes_init()` (ADR-036). The enum rows themselves must stay —
`ED_area_name()` and `ED_area_icon()` index `rna_enum_space_type_items` by
`area->spacetype`. Their trees are still compiled: kept subsystems reference
252 symbols across them, so compiling them out is Phase 13b work, not this.

**The menu is still short, and now it has a node editor in it.** ADR-066
registered `SPACE_NODE` again, and the rule above is what makes that a
narrowing rather than a reversal: `rna_Area_ui_type_itemf` lists a space
type's *subtypes* where it has them, so what the menu gained is one tree type
called "Wiring" and not a row called "Node Editor" — an area showing our tree
is titled and iconned from `tree_type->ui_name`. The four stock trees stay off
it because `rna_SpaceNodeEditor_tree_type_poll` is filtered to `Cadex`-prefixed
tree idnames, which is a *stronger* claim than not-registering could make and
is exactly the shape the asset browser is hidden with. For this one editor,
hiding moved from "do not register the space type" to "do not offer the
subtype".

Consequences worth knowing if you touch this: their `bl_ui` modules are out of
`_modules` (as a group — they cross-import each other), and `bl_ui/space_node`
stays out even now, because `mesh_agent/wiring_ui.py` supplies our header and
the stock one is 1,277 lines of shader/geometry/compositor UI; the asset
browser is a `SpaceFile` *subtype* and is filtered in
`file_space_subtype_item_extend` instead; and three bundled add-ons (`cycles`,
`pose_library`, `io_mesh_uv_layout`) are no longer enabled by default because
each registers against an editor that no longer exists.

### The Wiring graph

`inspect scope="wiring"` (ADR-065) hands the shell every terminal the accepted
run resolved plus the connection table over them; `wiring.py` draws that as a
node tree and turns a dragged link back into one `set_params(nets=[...])` —
the same op, the same debounce and the same optimism a slider drag uses. The
tree lives at `scene.cadex_wiring`, which is a real user, so it saves in the
.blend without a fake user and node positions round-trip. A board that is not
a declared output still gets a node; a script that predates `nets(...)` draws
read-only, with the banner naming the conversion.

Run its suite with no engine and no rebuild:

```bash
cd shell && env -u MESH_FREECADCMD -u MESH_CADEXD_MODULE -u MESH_CADEX_ENGINE \
  /Applications/Cadex.app/Contents/MacOS/Cadex --background --factory-startup \
  --python tests/python/bl_mesh_agent_wiring.py
```

**Edit Mode on a hydrated object is Edit Mode on a display mirror** — the next
`hydrate_display` replaces `obj.data` wholesale. The terminal pick only reads,
so nothing is lost, but a user who starts extruding there deserves to have
been told.

### The startup file: `scripts/startup/bl_app_templates_system/Mesh/`

**The layout is `startup.blend`, not code** (ADR-037). It became expressible as
a saved screen the moment the columns became real editors, because a saved
screen can only record area *types* — and until then the area types were
lying. Viewport left, Cadex Chat right at full height, Cadex Parameters under
the viewport; one workspace named "Simple"; an empty scene; solid shading with
the toon matcap, overlays and regions off. All of that is space data and saves
into the file.

`blo_is_builtin_template` (`versioning_defaults.cc`) does not list "Mesh", so
`BLO_update_defaults_startup_blend`'s destructive pass — free every stored
panel, reset region sizes, rename screens — never runs on ours. That is
load-bearing: do not add "Mesh" to that list.

`__init__.py` is 111 lines and does three things, none of which a `.blend`
can carry:

- **Enables the add-on.** `preferences.addons` is `UserDef`, not `Main`.
  Shipping a `Mesh/userpref.blend` would work and would also pin the user's
  theme, paths, keymap and autosave, so this stays four lines of Python.
- **Installs the Cadex top bar** — File and Edit, from `mesh_agent.topbar`
  (ADR-041). A header's draw function is code, not screen data, so no `.blend`
  can carry it. It is the *template* that installs rather than the add-on, so
  that `mesh_agent` in a stock Blender session leaves that session's bar alone.
  Until ADR-041 this line blanked the bar instead, which is how `File > Open`,
  `Save As`, Import/Export and Preferences went missing.
- **Suppresses the splash** (ADR-042) — `preferences.view.show_splash = False`,
  restoring `is_dirty` so the user's `userpref.blend` is not edited. This one
  runs *in the load handler*, not in the timer: `creator.c` reads
  `USER_SPLASH_DISABLE` immediately after `WM_init`, before any timer fires.

The first two run from a deferred timer that skips background mode, so a
headless suite that wants the bar has to call `_cadex_topbar()` itself — the
gate does, and `_hide_splash()` with it.

To re-author the layout: launch, arrange by hand, `File > Defaults > Save
Startup File`, then copy `<config>/Mesh/startup.blend` over the one in the
tree. **Do it in one commit** — the file is git-LFS-tracked and every re-save
is a new object that is never reclaimed. `test_startup_layout_is_the_shipped_file`
in `bl_mesh_agent_cadex.py` is what catches it silently failing to load (and
the shipped template failing to install the bar), and it puts `startup_areas`
in the `CADEX-BLENDER-GATE` line as evidence.

### The message box, and what sends it

`draw_chat_input` uses `layout.textbox()` — a text-box widget
(`ButtonType::TextBox`), not a text field. It wraps onto as many lines as it
is tall, scrolls when the message outgrows them, and carries a grip for
making it taller.

**Return sends; Shift+Return puts in a newline.** The second half is the
widget's own C behaviour (`interface_handlers.cc`, `EVT_RETKEY` under
`ButtonType::TextBox`). The first half is the `update=` callback on
`WindowManager.mesh_chat_input`: Blender commits a text button's value when
the edit ends, and that callback is the only place Python hears about it.

**Clicking outside the box does not send.** A Blender text button has exactly
one "the edit finished" signal, reached by Return and by a click elsewhere
alike, and committing is the only thing Python hears about — so without help,
a stray click sent the draft. `layout.textbox(..., confirm_only=True)` adds
the distinction on the C side, and it is the one behavioural edit in the
inherited-Blender delta (`docs/BLENDER-TREE.md` §2c). Escape still cancels the
edit without sending.

What the widget does *not* do is grow by itself as you type. The wrapped line
count (`ButtonTextBox::last_total_lines`) and the box's height
(`TextboxState::visible_lines`) both live in C, reachable from the layout API
only as the `initial_visible_lines` argument at the moment the region first
creates the state.

That is now a *choice* rather than a wall. The box lives in a region of an
editor we own, and `RGN_FLAG_DYNAMIC_SIZE` lets a region size itself from its
`ARegionType::layout()` callback (`DNA_screen_types.h`) — so a custom layout
callback could set `sizey` from the wrapped line count without touching
inherited Blender at all. Not built; recorded in ADR-035 as the obvious
follow-up.

## 3. Blender internals relevant to the shell integration

All upstream Blender code, listed as orientation (paths relative to
`shell/`):

| Area | Path | Why it matters |
|---|---|---|
| Draw engines | `source/blender/draw/engines/` (`eevee`, `workbench`, `overlay`, `select`, `compositor`, `gpencil`, `image`, `external`) | Rendering quality/feel that Coin3D can't match; `overlay` and `select` are where BREP face/edge highlighting and picking feedback would hook in. |
| BMesh | `source/blender/bmesh/` | Native mesh editing; the reason real mesh editing waits for the Blender shell rather than being built on FreeCAD's Mesh module. |
| Attributes / CustomData | mesh attribute system (accessed via BMesh/Mesh APIs) | Where per-face/per-edge **BREP ID maps** land when cadexd streams tessellated shapes, so picking can resolve back to `@face-N` / `@edge-N` pins. |
| DNA/RNA | `source/blender/makesdna/`, `source/blender/makesrna/` | Blender's struct + reflection system; how `scene.mesh_params` properties exist; a model for parameter reflection (see `docs/IDEAS.md`). |
| Depsgraph | `source/blender/depsgraph/` | Evaluation/dirty-propagation if cadexd outputs ever become depsgraph-integrated rather than rebuild-on-demand. |
| Window manager / editors | `source/blender/windowmanager/`, `source/blender/editors/` | Layout, operators, event handling. `editors/space_cadex_{chat,params}/` are ours and live here (ADR-035); `space_project/` is the upstream file they were modelled on. |
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
| API truth | the `describe_cad_api` tool; the system prompt carries **no** API names, and a test asserts it (`bl_mesh_agent.py`) |
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
| Picking a point on anything | `mesh_agent.pick_point`: ray-cast → hit + normal → the output's own space → a point pin on the next message. The only pick that works on an imported mesh (ADR-056) |
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
