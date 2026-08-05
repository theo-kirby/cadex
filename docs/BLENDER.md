# BLENDER.md — The Shell

Verified against source: 2026-08-05

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
| `tools.py` | Tool definitions/executors. Tools: `get_script`, `write_script`, `edit_script`, `restore_version`, `set_params`, `rebuild_model`, `inspect_model`, `describe_cad_api`, `get_attached_image`, `scene_summary`, `viewport_screenshot`, `render_views`, `export_stl`, `import_geometry`, `focus_view`, `render_views` (ADR-124), which renders the MODEL from four fitted cameras rather than the user's viewport — it deliberately does not replace `viewport_screenshot`, which answers the different question of what the user is looking at, and because it hides the collision cage the collision workflow still goes through the pair below; and `collision_view` (ADR-091), which shows or hides the collision overlay and reports what is already touching at t = 0. It is the agent that catches this class of bug, via `viewport_screenshot`, and it cannot press a button; it is read-only, so it is in neither `_ENGINE_TOOLS` nor `MUTATING_TOOLS` — a view toggle must not enter the undo stack. `import_geometry` copies an external STL/OBJ/PLY into the engine's asset store so a script can name it (ADR-043) — **and it is also how a trained `.cxpolicy` comes home** (ADR-084), because `import_geometry` and the `put_asset` op beneath it perform no suffix check of their own and let the engine refuse. One rough edge, stated rather than papered over: the tool is named for geometry and its success message advises `mesh.import_file(...)`, which is wrong for a policy. Fixing the wording is a `shell/` diff, and although ADR-091 has since spent that diff on the collision overlay it deliberately did not spend it here — one authorised feature does not license unrelated edits (ADR-086 §4) — so the engine-side refusals still carry the correct advice instead; `inspect_model` gained the `output` and `assets` scopes with it, and the `history` scope with ADR-045. `restore_version` puts a previously accepted version back — it reads `inspect scope=history` and writes the result through `write_script`, so a restored version re-runs and is re-accepted rather than trusted (ADR-045); `write_script` itself now refuses to drop outputs the model currently has unless `replace` is set, because "add a part" answered with a whole-script rewrite is how a project gets deleted. Marks `write_script`/`edit_script`/`restore_version`/`set_params`/`rebuild_model` as mutating for undo counting, and preflights the engine-reaching ones so a missing engine reads as one sentence. `rebuild_model` re-runs the script the engine already holds (ADR-039) — the tool to reach for when the model and the engine have drifted. `describe_cad_api` narrows in three steps (ADR-123): no arguments is the contract plus every domain's function *names*; `domain` is that domain's **compact** block — every signature, each description cut to its first sentence, served by `cadex_backend.compact_domain()` and never truncated; `domain` plus `functions=[...]` is the **full**, untouched entries for the ones the model named, and the only path `_API_DOMAIN_CHARS` (now 32768) still caps. Serving the full block for a whole domain is what broke: at 16 KB it cut `part` and `assembly` mid-structure, so the reply was not JSON and half of each domain was unreachable — while the tool's own description told the model never to guess an API from memory. |
| `ui.py` | The panels of the two Cadex editors — transcript, message box, parameter sliders — plus the operators (send, cancel, new chat, attach image, paste, toggle parameters, toggle script, toggle collision shapes, rebuild from saved script, rebuild model, apply as defaults). The Collision panel (ADR-091) polls a scene flag the way the Simulation panel does and surfaces the initial-contact line — *touching at t = 0 … at z = 20.00 mm* — which is the one row that would have caught the hopper ADR-087 found. No `poll` here asks *where* it is drawing: the space type answers that (ADR-035). The **Policy Outputs** panel (ADR-096) does the same for a rollout: one `layout.progress` bar per actuator, drawn from `scene.frame_current` at draw time against the range the task bundle derived, so a bar pinned at an end *is* the policy saturating that motor. It is a readout, not a control — `progress` takes no input, and these numbers are a recording. The **Training** panel (ADR-098) is the third of that family and the only one that is not about a finished artifact: state, iteration against total, elapsed, ETA, reward, **mean episode length** (ADR-101), best-so-far **and the iteration it happened at**, and the checkpoints pulled so far. The episode-length row is the one to read against the reward: a reward climbing while it falls is a policy failing sooner and being paid more for it, which is what two runs did with nothing recording it. That best-so-far pair is the rest of the point — the gap between the best iteration and the current one is the decision to stop, and `mg-legs` peaked at 1200 of 2000 with nobody able to see it. It polls `cadex_training.read_progress`, so it is absent on a project with no run and stays up on `done`/`failed` rather than vanishing, because "it finished" is information and an empty panel is not. The parameters panel draws a failed drag as an alert row with **Rebuild Model** beside it (ADR-039), and an **Apply as Defaults** button that is live only while a slider sits away from its declared default (ADR-040). |
| `spaces.py` | Headers for `CADEX_CHAT` and `CADEX_PARAMS`, and the script view: `MESH_AGENT_OT_show_script` (a **toggle** — a Text Editor on the `model.py` mirror, opened or closed), `MESH_AGENT_OT_revert_script`, and `CADEX_PT_script`, its sidebar panel, which says whether the buffer matches the model and offers **Apply to Model** / **Revert to Model** / **Rebuild Model** accordingly (ADR-039). Headers live here rather than in `bl_ui` because `bl_ui` is inherited and this is ours. |
| `topbar.py` | The Cadex top bar (ADR-041): `CADEX_MT_file` (New, Open…, Open Recent, Revert, Save, Save As…, Save Copy…, **Import Geometry…**, Import ▸, Export ▸, Quit) and `CADEX_MT_edit` (Undo, Redo, Preferences…), and the `install()` / `uninstall()` pair that swaps `TOPBAR_HT_upper_bar`'s draw. Everything the menus point at is a stock operator or a stock menu **except** `MESH_AGENT_OT_import_asset`, which has to be ours: stock Import loads into the Blender scene, which here is the display mirror, so importing *into the model* means a `put_asset` op (ADR-043). Registering the add-on does **not** install the bar — the app template does that, so `mesh_agent` in a stock Blender session leaves that session's bar alone; `unregister()` does uninstall, because a header naming menus that are gone draws errors. |
| `history.py` | Chat transcript as JSON in `bpy.data.texts["mesh_chat.json"]`; persists inside the .blend file. |
| `capture.py` | Viewport screenshot (base64 PNG), attached-image loading (downscaled, default max 768 px), and **`render_views`** (ADR-124): four cameras fitted to the Model collection's bounding box — front (−Y), right (+X), top (+Z) orthographic and a three-quarter perspective at azimuth 45° / elevation 25° — rendered at equal size and composited 2×2 into one image, with sibling collections hidden, solid studio shading and overlays off. `view_matrices(bbox, aspect)` is the pure half: it fits the cameras, returns plain tuples and imports no `bpy`, which is the half `bl_mesh_agent.py` tests and the half Phase 12 re-binds. Isolating the model needs `view_layer.update()` after toggling `hide_viewport` — the flag syncs lazily and `draw_view3d` runs first, so without it the collection you just hid is still in shot. |
| `modes.py` | The Cadex system-prompt overlay and `system_prompt()`. What remains of a three-mode registry after ADR-030 collapsed it to one. |
| `mock_backend.py` | Test harness that replays scripted turns through the real bridge without spawning Claude. |
| `cadexd_client.py` | **Phase 6 (ADR-019).** Dependency-free NDJSON stdio client for cadexd; spawns `FreeCADCmd` (add-on preference / `MESH_FREECADCMD` / bundled manifest / PATH), ready banner, serialized requests, cancel, crash envelopes. No `bpy`, **no cadex imports** — that last part is a licence boundary, not a style choice, and one repository does not relax it. |
| `cadex_backend.py` | Per-scene cadexd session: project root beside the .blend (`<stem>.cadex/`), revision-guarded `write_script`/`set_params` with stale-revision self-heal, engine params bridged into `scene.mesh_params`, draft-while-dragging + background standard refine. |
| `cadex_animate.py` | an accepted simulation trace → F-Curves on the component instances: time-keyed (not frame-index-keyed), wxyz quaternions walked into one hemisphere, bulk `foreach_set` onto slotted actions, cleared and re-baked per revision. A sibling of `cadex_hydrate.py`, so a bad trace never costs you the geometry. **The trace may come from kinematics, from rigid-body dynamics, or from a learned policy rollout** — `_simulation_entries` selects on `artifact_kind == "assembly_simulation_json"` and all three produce it, so this file plays a trained gait without one line of it knowing that policies exist (ADR-077, ADR-085). That is not luck: it is why a rollout deliberately reuses the output type instead of inventing one. Selecting on a *kind* rather than trying to enumerate producers is the property to preserve — the same code must ignore, never fail on, the MJCF / task / policy-receipt kinds it will also be shown. It also holds the pure half of the Policy Outputs readout: `commands_table` turns a rollout's `actuator_commands` into a flat frame-indexed table on the scene, and `commands_at` returns the row **at or before** a frame — a zero-order hold, because a command is a decision taken at a control step and held, not a continuous quantity to interpolate (ADR-096). A trace with no `actuator_channels` yields no table, which is what keeps the panel off kinematics and plain dynamics runs. |
| `cadex_hydrate.py` | `cadex-tessellation-v1` buffers → Model-collection mesh objects: `cadex_face` INT face attribute (1-based BREP ids), `cadex_edge` wire children, placements, contract-driven GC by `cadex_output` property. |
| `cadex_collision.py` | **ADR-091.** The collision geometry a dynamics model actually simulates, drawn as an edge-only wire cage per shape. Reads what the engine already publishes — `model_evidence`, either from a simulation trace's `dynamics` key or via `inspect` on the mjcf publication object's `CadexAssemblyMjcfValidation` — so it cost **no engine change and no protocol change**; both readers are needed, because an mjcf-only model has no trace and a rollout's trace carries the evidence dict without the collisions block. Objects are named exactly the MuJoCo geom (`<component>/collision<n>`) and live in a **`Collision` collection that is a SIBLING of `Model`, not a child** — `cadex_hydrate._cadex_objects` walks `all_objects`, which recurses, so a child would be swept by the contract GC; they are tagged `cadex_collision_of` and never `cadex_output`, which is the same isolation on a second axis. Zero polygons, so picking is unaffected and nothing occludes the surface being compared against. Parented with an identity `matrix_parent_inverse`, so the cage follows the bake, the preview and the solved placement for free. The pure half holds the `size_m` conversion table exactly once — box is half-extents, capsule's half-length is of the cylindrical section only — and imports no `bpy`. A sibling of `cadex_hydrate.py` exactly as `cadex_animate.py` is, so a bad collision record never costs you the geometry. |
| `cadex_training.py` | **ADR-098.** The shell's view of a training run happening on another machine, and it is one JSON file: `training-progress.json` in the project root, which `training/remote_train.sh watch` mirrors off the GPU box. Its whole import list is `json`, `os` and `bpy` — **no mujoco** (`test_the_shell_never_learns_about_mujoco` is the branch-wide form of that) and **no transport**, because a panel that opened a network connection would block Blender's main thread the first time a box was slow. A gate check asserts that closure exactly. Absent, unreadable, half-written and wrong-schema all read as *no run*, which is what keeps the panel invisible on a project that never trained; a partial read is deliberately not cached, so the panel notices the moment the writer's `replace` lands rather than on the next write. The `bpy.app.timers` poll is an interactive convenience — it stats the file and tags the parameters editor for redraw — and every function it calls is written to be callable directly, because timers do not fire under `--background` and that is where the gate runs. |
| `cadex_pick.py` | Viewport pick → a pin queued onto the next chat message (like image attachments), in two flavours sharing one eyedropper modal and one queue. **Face pin** (`mesh_agent.pick_pin`): polygon → `cadex_face` → `resolve_pin` → `@face-N`, BREP outputs only. **Point pin** (`mesh_agent.pick_point`, ADR-056): the ray-cast hit and its normal, pushed back through the object's placement into the output's own space — no engine round-trip, and it works on mesh outputs, which have no faces to name. A point and a direction *is* a `part.cable` port. |
| `wiring.py` | **ADR-066.** The Wiring graph's model: `CadexWiringTree`, `CadexBoardNode`, `CadexTerminalSocket`, `ensure_tree`, `sync_from_engine`, `rows_from_tree` and `push`. **Nothing is sent until Apply is pressed (ADR-122):** every edit sets `cadex_dirty` and the 0.15 s leading-edge debounce that used to fire behind it is gone — it turned a burst of twenty drags into one push plus nineteen that piled up on the client lock and were then refused as stale, in silence. `push` is now called from exactly one place, sends both declared tables in one `set_params`, and keeps every guard it had; `on_push_finished` is the single completion path, and **on failure it keeps the canvas** rather than resyncing, because losing twenty drags to one refusal is worse than an inconsistent canvas (Revert is how you discard them). The graph is a *projection* of `inspect scope="wiring"` — nodes, sockets and links are rebuilt from the engine and never from the canvas, so Revert puts back what the engine actually holds; the one thing it owns is `Node.location`. Two sockets per terminal — `tree.links.new` raises `Same input/output direction of sockets` for output→output *and* input→input, so one row per terminal and drag-to-connect cannot both hold — keyed by a registered `terminal` property (duplicate socket names dedup into `sda`/`sda_001`), drawn `sda ▸` and `▸ sda` so the pair reads as one terminal (ADR-122), with solder state carried as socket colour *and* a checkbox on the socket row (a link holds no properties, and `part.solder` takes a terminal and never a wire — ADR-063). **Solder is edited on the socket and pushed like any other edit (ADR-113):** `soldered` carries an `update=` callback, because `NodeTree.update()` fires on topology and never on a property written into a socket, so without it the debounce never armed; the callback mirrors onto the terminal's twin socket, and `_solder_for` reads the sockets as the answer — either end ticked means the row is soldered, both clear means it is not — rather than falling back to the stored row, which could only ever turn solder on. **The canvas is only pushed while it is a whole projection (ADR-115):** `apply_state` refuses to reconcile two components onto one node, records any row it could not draw and raises `cadex_stale`, and `push` stands down while that flag is up — an empty canvas describes an empty table, and a push replaces the declared list wholesale. A completed sync also clears `cadex_pending`, which saves into the `.blend` and otherwise left "applying…" in the header forever. Rows marked `editable: false` (a cable or bundle the script built outside `nets(...)`) draw like any other link; `declared_rows` strips them from the pushed table. **A socket also carries its own row since ADR-120** — `origin`/`axis`/`hole_dia`/`depth`, millimetres in the board's own frame, with the same `update=` mirror the solder flag has — so the terminal table rides the same debounce as the connection table and a rename that moves a terminal *and* the wires addressing it is one `set_params`. Two bugs went with it (ADR-121): the no-op guards compared canvas rows against engine rows carrying a route and so could never fire, which made a redrawn link cost a full re-execute; and `on_push_finished` stored the canvas flat, wiping `path` off the table, which is what made Edit Wire Path report no published route. The duplicate-port skip now reports rather than dropping a node in silence. **A fresh socket reads soldered since ADR-122** — the state of a terminal nothing has landed on yet — so a drawn wire carries a joint without anyone ticking anything; `apply_state` therefore has to set the flag in *both* directions, per address and with the same *any* rule `_solder_for` reads back out, or an unticked row would come back soldered. |
| `wiring_ui.py` | **ADR-066.** Its chrome — header, three sidebar panels, `NODE_MT_add`, and the **Apply / Revert** pair (ADR-122): `MESH_AGENT_OT_apply_wiring` is the only thing that sends the canvas and its poll is false while one push is in flight; `MESH_AGENT_OT_sync_wiring` keeps its idname — `bl_mesh_agent.py` asserts exact idnames on the button row — and is labelled Revert, because "rebuild from the accepted revision" *is* discarding edits once the canvas can hold ones that were never sent. The Terminal panel lists the selected board as one row per terminal with its solder checkbox, which is where a board reads as the single list it is. The only module in the add-on allowed to fail registration: a `Panel` naming an unregistered space type raises and would abort the whole loop (the ADR-036 failure), so it guards each class and sets `EDITOR_AVAILABLE = False`. That is what lets everything else run on a bundle built before the C++ half. |
| `cadex_wire_path.py` | **ADR-118.** The wire-path round trip: **Edit Wire Path** opens the route the engine published for the active cable as a real `POLY` curve in a sibling collection (the `cadex_collision.py` pattern, but selectable — it exists to be grabbed), **Confirm** reads the control points back, queues a note and **starts the turn itself** with a fixed prompt, and **Cancel** throws the curve away. There is no gizmo code because there is no gizmo: G/R/S, snapping, axis constraints, proportional edit and the N-panel's numeric fields are Blender's, and all of them work on curve control points. The wire is identified by the **object** in the 3D view and not by a link on the canvas — a Blender `NodeLink` carries no selection state at all, and two selected board nodes would be ambiguous the moment two signals run between the same pair. Seeds from the row's `waypoints`, so no stub-knot arithmetic lives here; a bundle conductor publishes an empty one and is refused by name. |
| `cadex_terminal_pick.py` | **ADR-067, ADR-117.** Edit-Mode selection → a measured terminal, handed to the next chat turn. The bore axis is the scatter matrix's *odd-one-out* eigenvector (two of three eigenvalues are equal on a circle) and not its smallest, which is the plane-fit answer and is wrong for any bore deeper than its radius. **Two models are then fitted to the same points** (ADR-117): a closed-form least-squares circle, and a minimum-area enclosing rectangle by rotating calipers over the convex hull — a pad is usually square, and four corners fit a circle *exactly*, so a circle alone is meaningless on one. `AUTO` takes whichever has the smaller residual once normalised by its own scale (radius, half-diagonal) and **refuses when the two tie**, naming both fits: that case is genuinely ambiguous and the operator's `kind` enum is the override. Refuses under four vertices and refuses a fit worse than 15% of the winning model's scale — a quality gate, never a classifier. One ring is enough for a bore; selecting both rims drops the far one and says so. The row carries `origin`/`axis` (plus `hole_dia` for a bore) and **never a depth** — the terminal lands in the selected plane; a pad's width and height go in the *report*, so `pad_dia_mm` can be chosen without putting a rectangle field on a layout row. Its own queue and its own wording: a pin is not a terminal. **ADR-119** adds `define_board` beside it: click an object the engine built, name it, and the next turn is asked to declare that output as a port in `nets(ports=...)`. It is the one gesture that starts from a click on the *mirror*, so the note carries the engine's output key and never `obj.name`; it also stamps the object, so every later terminal pick on it says which board it is on — click board, click terminals, one turn declares the whole port. The note states two limits rather than promising around them (a component cannot avoid itself as a mesh; `shape_from_mesh` cannot express a multi-shell import) and one more: a board with no terminals yet draws no node, because a node is a terminal set. **ADR-121 changes where the measurement goes:** when the script declares `boards(...)`, the fitted row is written straight into `board_values` through `set_params(boards=[...])` — no chat turn, and the socket simply appears. It goes out in **world** coordinates marked `frame: "world"`, because a click has no other frame and a hydrated object's transform is a display placement rather than the asset's declaration chain; the engine inverts the chain it resolved. The note path remains for a project with no board to write onto, where creating one is authoring and the assistant's job. |

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
| `RGN_TYPE_HEADER` | model selector, the pinned count | `CADEX_CHAT_HT_header` |

The split between the two is **status in the header, actions in the row**
(ADR-074). The button row is four aligned groups, and the grouping is the
documentation:

| Group | Buttons | What they act on |
|---|---|---|
| gather | attach image, paste image, Pin Face, Pin Point, Define Terminal | what the *next message* will carry |
| model | Rebuild Model | the *model*: re-runs the script the engine holds, sends nothing |
| views | Parameters, Script, Wiring | open/close, each depressed while its view is open |
| turn | New Chat, Send/Stop | the *turn* |

Nothing in the row is hidden when it does not apply — `Define Terminal` greys
out instead, because a row that changes width as you enter and leave Edit
Mode moves every other button under the pointer.

`RGN_TYPE_EXECUTE` is the load-bearing part. `RGN_TYPE_IS_HEADER_ANY`
(`DNA_screen_types.h`) covers `HEADER`, `TOOL_HEADER`, `FOOTER`,
`ASSET_SHELF_HEADER` and `SCRUBBING` and deliberately **not** `EXECUTE` — so
an execute region is an ordinary sizable panel region, not subject to the
one-row limit that once forced the message box into a screen area of its own
(ADR-034). It is `RGN_ALIGN_BOTTOM`, `prefsizey = 6 * HEADERY`, and
user-resizable.

**Cadex Parameters**, two regions: `RGN_TYPE_WINDOW` for the sliders
(`CADEX_PARAMS_PT_parameters`) and a header — and since **ADR-108** that is
all it holds.

Until then, four more panels shared that window, each behind its own `poll`:
Collision (ADR-091), Simulation, Policy Outputs (ADR-096) and Training
(ADR-098). The reason given every time was **no new editor and no new space
type**, so each cost the inherited Blender tree zero lines. That reasoning was
right while the ask was a readout and it is **reversed** now that the ask is
four independently arrangeable workspaces: five panel groups in one editor
cannot be *arranged*, and arranging them is most of what a person does with a
workspace. The four are now four editors:

| Editor | Space type | Panels |
|---|---|---|
| Cadex Parameters | `CADEX_PARAMS` | `CADEX_PARAMS_PT_parameters` |
| Cadex Environment | `CADEX_ENV` | `CADEX_ENV_PT_collision` |
| Cadex Policy | `CADEX_POLICY` | `CADEX_POLICY_PT_simulation`, `..._PT_actuators` |
| Cadex Training | `CADEX_TRAINING` | `CADEX_TRAINING_PT_training` |
| Cadex Live | `CADEX_LIVE` | the live-session panels (ADR-109) |

Live is an editor of its own rather than a group inside Policy because it is a
**session** — stateful, running, and mutually exclusive with baked playback —
where Policy is a **recording**. One editor holding both would make the play
button ambiguous.

**Live mode also owns the add-on's only draw handlers** (ADR-110): a
`POST_VIEW` one drawing the force arrows and a `POST_PIXEL` one labelling
them, both in `cadex_live.py`, added in `start()` and removed in `stop()` and
in `unregister()`. Two rules, both test-pinned in the gate:

- **Fetch the shader inside the callback, never at module scope.**
  `gpu.shader.from_builtin` raises *"requires the gpu module to be
  initialized"* under `--background`, so a module-scope shader breaks every
  headless run. `gpu`, `gpu_extras`, `blf` and `bpy_extras` are all imported
  lazily for the same reason, and the gate asserts no shader has been fetched
  after the add-on registers.
- **Every handler that is added is removed twice over.** A leaked handler
  draws against a session that is gone and raises on the next add-on reload,
  so `unregister()` removes them again unconditionally rather than trusting
  that `stop()` ran.

What the arrows draw is the `applied_forces` a `live_step` frame carries —
what the engine *measured* in `xfrc_applied`, at the body's centre of mass.
The shell never draws the push it asked for: that would keep drawing after
the window lapsed, after a clamp and after a refusal.

Each of the four costs the sixteen touch points listed as a checklist in
`docs/BLENDER-TREE.md` §2b. Reach for them deliberately; the §2b lines are a
future merge conflict against upstream Blender, which is why they are all
*additive rows* the compiler finds rather than rewritten logic.
`mesh_agent.toggle_params` — the
`OPTIONS` button at the end of the chat button row, depressed while the editor
is open — closes it, or splits the viewport and sets `area.type`. That is the
whole operator now: no pointer bookkeeping and no retry timer, because there
is no space-data swap to wait on.

**No Cadex space type has DNA fields of its own** — all six are bare
`SpaceLink` headers, and a gate check asserts it. Transcript scroll is region
state, parameter values live in `scene.mesh_params`, the model selector is an
add-on preference, and the draft message is a `WindowManager` property. DNA is
append-only forever, so keep it that way: that is also why `SPACE_CADEX_ENV`
… `SPACE_CADEX_LIVE` were **appended** at 27–30 rather than slotted in.
A space type is stored by number in every saved `.blend`, so renumbering them
silently reinterprets somebody's workspace.

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
`file_space_subtype_item_extend` instead; `NODE_PT_tools_active` had to be put
*back* into `space_toolsystem_toolbar.py`'s `classes`, because registering a
`ToolSelectPanelHelper` is the only thing that initialises its
`_tool_group_active` and the first click into a live node editor reads it; and three bundled add-ons (`cycles`,
`pose_library`, `io_mesh_uv_layout`) are no longer enabled by default because
each registers against an editor that no longer exists.

### The Wiring graph

`inspect scope="wiring"` (ADR-065) hands the shell every terminal the accepted
run resolved plus the connection table over them; `wiring.py` draws that as a
node tree and turns the whole canvas back into one
`set_params(nets=[...], boards=[...])` — the same op a slider drag uses, down
the same pumped path. The tree lives at `scene.cadex_wiring`, which is a real
user, so it saves in the .blend without a fake user and node positions
round-trip. A board that is not a declared output still gets a node; a script
that predates `nets(...)` draws read-only, with the banner naming the
conversion.

**Nothing is sent until you press Apply** (ADR-122). Drag as many wires as you
like: each marks the canvas dirty, the header highlights Apply, and one press
is one re-execute — which is the right unit, because a net edit costs a full
script run (seconds on a small harness, ~18 s on the drone). **Revert** is the
way back: it re-reads the engine, so anything drawn and not applied goes away.
A refused Apply leaves the canvas exactly as it is, with the engine's reason
on the header.

The push is driven to completion by a single-slot pump — `_wiring_slot` /
`_wiring_pump` / `wiring_apply_now` in `cadex_backend.py`, the exact shape of
the slider drag's `_drag_pump`: one request in flight per project root, the
newest one queued (a push carries the whole table, so there is nothing to
coalesce and the newest supersedes), polled on a 0.02 s timer, `project_root`
re-checked before hydrating. Before ADR-122 there was no pump at all: `push`
started a `Lifecycle` and dropped it, so the revision guard never advanced and
every apply after the first was refused `STALE_PROGRAM_REVISION` in silence.
`bpy.app.timers` do not fire under `--background`, so the gate suites call
`wiring_apply_now` — the peer of `pump_drag_once`.

**What puts the nodes on the canvas is `CadexWiringTree.get_from_context`**
(ADR-074), not the panels. Everything `node_draw_space` draws is inside
`if (snode.treepath.last)`, only `ED_node_tree_start` pushes onto `treepath`,
and `snode_set_context` calls it on every redraw *only* for a tree type
supplying that callback. Without it the editor drew an empty grid while the
sidebar — which reads `scene.cadex_wiring` directly — listed every board. The
`NODETREE` button in the chat's row (`mesh_agent.toggle_wiring`) is the
explicit open/close; it matches on `area.spaces.active.tree_type`, never on
`area.type` alone, because `NODE_EDITOR` is shared with the compositor, and
it sets `area.ui_type` *before* `space.node_tree` because
`rna_SpaceNodeEditor_node_tree_poll` rejects the assignment otherwise.

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
| API truth | the `describe_cad_api` tool; the system prompt — base **and** overlay — and every tool description carry **no** API names, and `test_prompt_carries_no_api_names` asserts it (`bl_mesh_agent.py`, widened past the overlay by ADR-123) |
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
