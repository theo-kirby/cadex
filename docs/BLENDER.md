# BLENDER.md — The Shell

Verified against source: 2026-09-06

**Native geometry recipes (ADR-185).** `cadex_backend._client` passes
`bpy.app.binary_path` to `cadexd_client.default_command`, which sets
`CADEX_BLENDER_EXECUTABLE` in that child alone. An xscript `mesh.blender`
operation can therefore run the same installed binary as an isolated geometry
worker. The visible scene still only hydrates accepted engine output, and
script/slider/history changes use the existing undo path. Recipe code never
executes in the visible process. See `docs/BLENDER-RECIPES.md`. [Cadex-new]

**The shell is the product, and since ADR-030 it is in this repository**, at
`shell/` — a Blender fork whose `mesh_agent` package is the interface:
application code registered by the script loader from `scripts/startup`,
like `bl_ui` — not an add-on, since ADR-183. Nothing
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

This mirrors the stance toward inherited FreeCAD core (see `AGENTS.md`),
which likewise moved from "don't touch" to "reduce the delta where you can,
and say what you did" (ADR-022).

## 2. The assistant package: `shell/scripts/startup/mesh_agent/`

A chat-driven, single-script parametric modeler inside Blender. It is the UX
that `docs/VISION.md` describes, and the protocol client that
`docs/INTEGRATION.md` specifies. **Application code, not an add-on**
(ADR-183): the script loader imports it and calls `register()` at every
launch — background and `--factory-startup` included — so there is no
`bl_info`, nothing to enable, and nothing in the Add-ons list. Two costs of
registering that early, both paid in `__init__.py`: `keyconfigs.addon` does
not exist yet, so the landing screen's and the drawings editor's keymap
items install from a deferred timer; and the suites re-register the package
from source after putting down the bundled copy, so `register()` and
`unregister()` are idempotent.

### File map

| File | Role |
|---|---|
| `__init__.py` | Package registration (idempotent, ADR-183); the deferred keymap timer; save/load lifecycle handlers; undo-batching hookup. |
| `prefs.py` | **ADR-183.** The AI settings: a JSON file in the app's config dir (`cadex_agent.json`), mirrored into a `PropertyGroup` on the WindowManager, drawn by two panels — AI Assistant (assistant selection, Claude Code / Codex / pi, ADR-174/ADR-175, with a per-provider model picker and CLI path) and Engine (override, budgets, resolved-engine row) — registered into the **AI** section of the Preferences window (`bl_context = "ai"`; the rail entry is one RNA row, BLENDER-TREE §2b). Not `AddonPreferences`, which only exists for add-ons. |
| `agent.py` | Turn orchestration and event loop. Queues tool calls from the bridge; drains them on the main thread; pushes **one undo step per chat turn**. |
| `model.py` | The script mirror (`bpy.data.texts["model.py"]`, soft read-only) and the dynamic PropertyGroup at `scene.mesh_params`; 0.15 s debounced rebuild on slider drag, dispatched to the engine, plus an undebounced ~30 Hz `preview_params` pump in front of it for motion parameters (ADR-055). `set_script()` is a no-op when the source is unchanged and restores the cursor when it is not, and stamps the digest the dirty marking compares; `last_error()` carries a failed drag to the panel (ADR-039). `rewrite_defaults()` splices slider values into the script's `num()` declarations for **Apply as Defaults** (ADR-040) — pure text in, text out. |
| `model_api.py` | `clamp()` — coerce a value to its spec's type and range. All that is left of a script-facing API that no script imports any more (ADR-030). |
| `bridge.py` | Localhost TCP server (127.0.0.1, auto-assigned port, 16-byte hex token auth). Two wire ops: `list_tools`, `call`. Queues socket-thread requests for main-thread execution. |
| `mcp_shim.py` | Standalone MCP stdio server spawned by the agent CLI (Claude via `--mcp-config`, Codex via `-c mcp_servers.*` overrides). No `bpy` import; relays MCP tool calls to the bridge over TCP. |
| `pi_tools.js` | The non-MCP transport (ADR-175): a native pi extension (node built-ins only, loaded with `pi -e`) that registers the bridge's tools via `pi.registerTool()` and relays each call over the same TCP bridge. The bridge's address arrives in `MESH_BRIDGE_PORT`/`MESH_BRIDGE_TOKEN`. |
| `backend.py` | One agent-CLI subprocess per turn: `ClaudeCodeBackend` (`claude -p`, `--resume <session-id>`), `CodexBackend` (`codex exec --json`, `exec resume <thread-id>`, ADR-174) or `PiBackend` (`pi -p --mode json`, minted `--session-id`, ADR-175). All push the same Claude-shaped stream frames onto the agent's queue; the non-Claude backends translate their JSONL into them. |
| `tools.py` | Tool definitions/executors. Tools: `get_script`, `write_script`, `edit_script`, `restore_version`, `set_params`, `rebuild_model`, `inspect_model`, `describe_cad_api`, `get_attached_image`, `scene_summary`, `viewport_screenshot`, `render_views`, `export_stl`, `import_geometry`, `link_part`, `focus_view`, `render_views` (ADR-124), which renders the MODEL from four fitted cameras rather than the user's viewport — it deliberately does not replace `viewport_screenshot`, which answers the different question of what the user is looking at, and because it hides the collision cage the collision workflow still goes through the pair below; and `collision_view` (ADR-091), which shows or hides the collision overlay and reports what is already touching at t = 0. It is the agent that catches this class of bug, via `viewport_screenshot`, and it cannot press a button; it is read-only, so it is in neither `_ENGINE_TOOLS` nor `MUTATING_TOOLS` — a view toggle must not enter the undo stack. `section_view` (ADR-148) is its sibling on both counts: it cuts the model open on a plane so the agent can see whether a bore broke through or a wall is thinner than it asked for, takes `show`/`axis`/`offset`/`flip`, and is checked the same way — turn it on, then `viewport_screenshot`, because `render_views` deliberately suspends the cut to answer "what did I build". `exploded_view` (ADR-149) and `blueprint_view` (ADR-150) complete the view-toggle family on the same two exclusions: spread the assembly along its declared explosion moves (factor 0..1, refused while a simulation is baked), and draw the model as white outlines on a blueprint-blue / cutting-mat-green / grey ground — or black lines on drawing-paper white with theme `technical` (ADR-176) — with an optional 10 mm grid, layering over the section and the explosion, restoring the viewport exactly on toggle off. `make_blueprint` (ADR-150, composable since ADR-151) renders an **agent-composed** sheet in that style — up to 6 views (named orthos, three-quarter, custom azimuth/elevation, or the `params` panel cell — ADR-153), per-view `hide`/`only`/`explode`/`section`/`callouts` overrides, a `layout` (templates plus the freeform `mosaic` — ADR-152; an omitted `views` is the triptych default — ADR-151 addendum) and an `aspect` (16:9 default — ADR-153), the specs validated by `cadex_sheet` and travelling in `put_blueprint`'s free-form `meta` when a draft is saved — and since ADR-178 it renders the sheet as the live **draft** (`cadex_drawings.set_draft`) and **stores nothing**: `save_blueprint` is the store write, sharing `cadex_drawings.save_draft` with the panel's Save button, `put_blueprint` beneath. Both are in `_ENGINE_TOOLS` (`based_on` reads the store, save writes it) and neither is in `MUTATING_TOOLS` (the `import_geometry` precedent — a store write is not a scene edit); unlike `render_views` it deliberately draws the *current presentation* (per-cell overrides inherit it and are flat-restored after), and the stored sheets read back through `inspect_model scope=blueprint`. ADR-157 makes a sheet **revisable**: `name` is the drawing's identity rather than a caption (render again under it and the store keeps the next version), `based_on` reads a stored sheet's recipe back out of the project store through `cadex_backend.read_blueprint` and renders it again with this call's arguments on top, and three per-view keys land at once — `aspect` (a cell's own width:height), `title` (the heading drawn over any cell) and `text` (with `view: "text"`, a panel of the agent's own words). The reply names the version and tells the model how to revise it. ADR-176 is the technical-drawing turn: the script's declared `part.measurement` dimensions (lengths, diameters, radii, angles) draw on every orthographic cell by default, a per-view `dimensions` flag overrides that, and `theme: "technical"` renders the whole sheet as black lines on drawing-paper white. ADR-177 opens `inspect_model` scope `blueprint` for real — the description had promised it since ADR-157 while the executor's whitelist refused it. ADR-178 is the draft turn: `make_blueprint` renders and iterates (nothing stored, the draft live in the user's Blueprint Editor window since ADR-179, the user tagging cells that arrive as `@cell-N`), `save_blueprint` stores the version the user approved. `import_geometry` copies an external STL/OBJ/PLY into the engine's asset store so a script can name it (ADR-043) — **and it is also how a trained `.cxpolicy` comes home** (ADR-084), because `import_geometry` and the `put_asset` op beneath it perform no suffix check of their own and let the engine refuse. One rough edge, stated rather than papered over: the tool is named for geometry and its success message advises `mesh.import_file(...)`, which is wrong for a policy. Fixing the wording is a `shell/` diff, and although ADR-091 has since spent that diff on the collision overlay it deliberately did not spend it here — one authorised feature does not license unrelated edits (ADR-086 §4) — so the engine-side refusals still carry the correct advice instead. `link_part` is its lossless sibling (ADR-138) and is a different tool rather than a wider `import_geometry` for one reason: what it takes is not a file at all but **another Cadex model**, named by its `.blend` or its `.cadex` folder, out of which the engine pulls one accepted solid. Its success message advises `part.import_part(...)`, which is the call that actually takes the stored name — the wording rough edge above, not repeated. Calling it again with the same arguments is refreshing, and the reply's `changed` is how the model tells whether the other file moved; `inspect_model` gained the `output` and `assets` scopes with it, and the `history` scope with ADR-045. `restore_version` puts a previously accepted version back — it reads `inspect scope=history` and writes the result through `write_script`, so a restored version re-runs and is re-accepted rather than trusted (ADR-045); `write_script` itself now refuses to drop outputs the model currently has unless `replace` is set, because "add a part" answered with a whole-script rewrite is how a project gets deleted. Marks `write_script`/`edit_script`/`restore_version`/`set_params`/`rebuild_model` as mutating for undo counting, and preflights the engine-reaching ones so a missing engine reads as one sentence. `rebuild_model` re-runs the script the engine already holds (ADR-039) — the tool to reach for when the model and the engine have drifted. `describe_cad_api` narrows in three steps (ADR-123): no arguments is the contract plus every domain's function *names*; `domain` is that domain's **compact** block — every signature, each description cut to its first sentence, served by `cadex_backend.compact_domain()` and never truncated; `domain` plus `functions=[...]` is the **full**, untouched entries for the ones the model named, and the only path `_API_DOMAIN_CHARS` (now 32768) still caps. Since ADR-181 the parts library rides the same three steps: the no-argument overview lists `lib` beside the domains with its generators and a per-family part-number summary, and `domain="lib"` serves the library block with its full catalog — the one block whose compact form keeps a `catalog` key, because the catalog is the point of asking. Serving the full block for a whole domain is what broke: at 16 KB it cut `part` and `assembly` mid-structure, so the reply was not JSON and half of each domain was unreachable — while the tool's own description told the model never to guess an API from memory. `get_script` takes optional `offset`/`limit` **line** arguments (ADR-140); with neither it serves the whole script exactly as ADR-044 requires, and with either it serves a window behind a banner carrying the range, the totals and the next `offset=` to call. The window exists because the cap that bites a 55 KB script is the **host's** tool-result limit, not ours — `_SCRIPT_CHARS` is 65536 and `MAX_RESULT_CHARS = 4096` governs every mesh tool *except* this one, a distinction an agent got wrong badly enough to start deleting comment blocks out of a user's script to make the next read smaller. The window carries no line numbers, because the text served is the text `edit_script` must match. |
| `ui.py` | The panels of the two Cadex editors — transcript, message box, parameter sliders — plus the operators (send, cancel, new chat, attach image, paste, toggle parameters, toggle script, toggle collision shapes, toggle dimensions, toggle section view, measure, rebuild from saved script, rebuild model, apply as defaults). **Dimensions** (ADR-139) reads as a view toggle in the same one-button-is-the-state row the collision overlay uses, and **Section View** (ADR-148) is the third button in it — its plane is aimed from a box at the bottom of the parameters editor (axis, offset in mm, flip) for the reason the cage's box is there: it is set without the AI in the loop, and a space type of its own would spend BLENDER-TREE §2b budget. It is the one control in that editor that changes nothing about the model, which is why it sits under the ones that do, and **Measure** sits with the pin gestures instead — it is a gathering, not a view: two face picks arm it, and what it does is queue the sentence asking for a `part.measurement` between them. It deliberately does **not** write the script. `begin_write_script` is right there and `restore_version` already calls it with no agent in the loop, but adding a measurement means appending a call *and* editing the result dict, and mechanically rewriting the one artifact this product treats as the source of truth is how a script gets quietly corrupted. The script keeps exactly one author. If a turn per measurement proves too expensive in practice, the clean answer is a sixth `set_params` table beside `nets`/`boards`/`mounts`/`cages` — that mechanism exists for viewport-edited model state, and it is a decision rather than something to slip in. The Collision panel (ADR-091) polls a scene flag the way the Simulation panel does and surfaces the initial-contact line — *touching at t = 0 … at z = 20.00 mm* — which is the one row that would have caught the hopper ADR-087 found. No `poll` here asks *where* it is drawing: the space type answers that (ADR-035). The **Policy Outputs** panel (ADR-096) does the same for a rollout: one `layout.progress` bar per actuator, drawn from `scene.frame_current` at draw time against the range the task bundle derived, so a bar pinned at an end *is* the policy saturating that motor. It is a readout, not a control — `progress` takes no input, and these numbers are a recording. The **Training** panel (ADR-098) is the third of that family and the only one that is not about a finished artifact: state, iteration against total, elapsed, ETA, reward, **mean episode length** (ADR-101), best-so-far **and the iteration it happened at**, and the checkpoints pulled so far. The episode-length row is the one to read against the reward: a reward climbing while it falls is a policy failing sooner and being paid more for it, which is what two runs did with nothing recording it. That best-so-far pair is the rest of the point — the gap between the best iteration and the current one is the decision to stop, and `mg-legs` peaked at 1200 of 2000 with nobody able to see it. It polls `cadex_training.read_progress`, so it is absent on a project with no run and stays up on `done`/`failed` rather than vanishing, because "it finished" is information and an empty panel is not. The parameters panel draws a failed drag as an alert row with **Rebuild Model** beside it (ADR-039), and an **Apply as Defaults** button that is live only while a slider sits away from its declared default (ADR-040). |
| `harness.py` | **ADR-184.** Pure subprocess discovery of account display metadata and harness-owned model catalogs; bounded JSON-line RPC lifetimes, native CLI sign-in via Terminal, no model turns or credential persistence. |
| `spaces.py` | Headers for `CADEX_CHAT` and `CADEX_PARAMS`, and the script view: `MESH_AGENT_OT_revert_script` and `CADEX_PT_script`, its sidebar panel, which says whether the buffer matches the model and offers **Apply to Model** / **Revert to Model** / **Rebuild Model** accordingly (ADR-039). The Text Editor showing the mirror is opened with Blender's editor dropdown — ADR-165 removed `MESH_AGENT_OT_show_script` with the other open-a-view operators. Headers live here rather than in `bl_ui` because `bl_ui` is inherited and this is ours. |
| `topbar.py` | The product's file operators (ADR-041, ADR-166). The File and Edit *menus* are native since ADR-166 — built in `GHOST_SystemCocoa.mm`, mapped to operators in `wm_window.cc` — and the in-window bar with its `install()`/`uninstall()` swap is deleted; what this module keeps is the four operators those menus call plus their dialog halves. `MESH_AGENT_OT_import_asset` has to be ours: stock Import loads into the Blender scene, which here is the display mirror, so importing *into the model* means a `put_asset` op (ADR-043). The two linked-part rows (ADR-138) are ours for that reason plus one of their own: what they bring in is another Cadex model's accepted output, pulled out of that project's store as the exact solid. Both go through one op — `link_part` — so `MESH_AGENT_OT_refresh_linked_parts` is a loop over what `MESH_AGENT_OT_link_part` does once, and `MESH_AGENT_OT_choose_linked_part` is only the enum step the file browser cannot host: the first call omits the output, and the refusal's `candidates` is what populates the dialog. **Export Printable Parts…** (cadex ADR-156) is the way back out, and ours for `Import Geometry`'s reason exactly — stock Export writes the display mirror, so a slicer would be handed a tessellation instead of the model. It calls `export_printable`, which writes one STL per part ticked in the Parameters editor, off the accepted solid, each at its own origin. `MESH_AGENT_OT_resolve_print_conflict` is the linked-part enum step one more time: the first call names no `conflict`, the engine **refuses** rather than overwriting, and the refusal's `observed.existing` is what populates the Overwrite / Keep Both dialog. Neither operator sets `bl_options` — a store write is not a scene edit, so there is nothing for Ctrl-Z to give back. |
| `history.py` | Chat transcript as JSON in `bpy.data.texts["mesh_chat.json"]`; persists inside the .blend file. |
| `capture.py` | Viewport screenshot (base64 PNG), attached-image loading (downscaled, default max 768 px), and **`render_views`** (ADR-124): four cameras fitted to the Model collection's bounding box — front (−Y), right (+X), top (+Z) orthographic and a three-quarter perspective at azimuth 45° / elevation 25° — rendered at equal size and composited 2×2 into one image, with sibling collections hidden, solid studio shading and overlays off. `view_matrices(bbox, aspect)` is the pure half: it fits the cameras, returns plain tuples and imports no `bpy`, which is the half `bl_mesh_agent.py` tests and the half Phase 12 re-binds — since ADR-151 it is a wrapper over **`fit_view`** (one camera fitted at one cell's aspect, from `VIEWS` or the superset `NAMED_VIEWS` table: the six axis orthos plus the three-quarter), and `composite_2x2` is likewise a wrapper over **`composite_rects`** (rect-based placement, row-slice copies, the pure suite pins both equivalences). Isolating the model needs `view_layer.update()` after toggling `hide_viewport` — the flag syncs lazily and `draw_view3d` runs first, so without it the collection you just hid is still in shot. `render_views` suspends every registered view through `cadex_views.suspend_for_render()`; **`render_blueprint`** (ADR-150, composable since ADR-151) is the renderer that does the opposite — agent-composed cells validated by `cadex_sheet`, each styled by `cadex_blueprint.present` and drawing the current presentation plus that cell's own hide/explode/section overrides (applied and flat-restored by `cadex_sheet`'s snapshot machinery), with the exploded leader lines kept in shot (`_isolate_model(keep=...)`), composited by rect, dressed by `cadex_sheet._dress_sheet`, and returned as a temp PNG that since ADR-178 belongs to the draft (`cadex_drawings` keeps it; `put_blueprint` copies it out on save), the payload since then also carrying `margin` and `theme` — the rects are field-relative and the draft editor's hit test needs the dress-time band. Spec validation runs BEFORE the background refusal, so a bad spec refuses for what is wrong with it even in the headless gate. Since ADR-153 the sheet defaults to **16:9** (`aspect` pass-through to `cadex_sheet.sheet_aspect`), an exploded cell renders at a wider fit margin and collects callout anchors through the SAME fitted matrices its tile draws with, and `params` cells are drawn tile-shaped after the flat restore, on the same sampled ground as the rendered tiles. ADR-157 adds the per-cell asks (passed straight to `cadex_sheet.layout_rects` as `aspects`), the second panel kind (`text` cells drawn by `_draw_text_tile` on the same sampled ground, overflow reported as a note), and the sheet's **recipe** in the returned payload — what `make_blueprint` stores in `meta` so the sheet can be drawn again. ADR-176 resolves the declared measurements once per sheet (`cadex_dimension.records_from_display`, the viewport overlay's own reader, so sheet and live view can never disagree), collects `cadex_sheet.dimension_jobs` per dimensioned cell through that cell's fitted matrices, and hands them to `_dress_sheet`; a cell that asks for dimensions on a script that declares none gets a note carrying the fix. |
| `modes.py` | The Cadex system-prompt overlay and `system_prompt()`. What remains of a three-mode registry after ADR-030 collapsed it to one. |
| `mock_backend.py` | Test harness that replays scripted turns through the real bridge without spawning Claude. |
| `cadexd_client.py` | **Phase 6 (ADR-019).** Dependency-free NDJSON stdio client for cadexd; spawns `FreeCADCmd` (add-on preference / `MESH_FREECADCMD` / bundled manifest / PATH), ready banner, serialized requests, cancel, crash envelopes. No `bpy`, **no cadex imports** — that last part is a licence boundary, not a style choice, and one repository does not relax it. `engine_version(bundle_roots)` (ADR-151) reads the manifest's `version` for the blueprint sheet's title block — a separate reader because `read_engine_manifest`'s signature is pinned, and deliberately tolerant where the launcher is strict. |
| `cadex_backend.py` | Per-scene cadexd session: project root beside the .blend (`<stem>.cadex/`), revision-guarded `write_script`/`set_params` with stale-revision self-heal, engine params bridged into `scene.mesh_params`, draft-while-dragging + background standard refine. **Hydrate on open** (ADR-186): `load_post` calls `queue_open`, and a timer-driven pump — the drag pump's shape — runs the restore-verified `open_project` and the display `rebuild` off the main thread and hydrates on it; under `--background` the gate drains it with `open_now`. A failed open lands in the parameters panel's alert row, as a chat status line, and as `open_failure_code` on the per-root state — which both open paths cache, and which `locked_out_project()` reads to draw the **Re-accept Stored Script** box (ADR-187): `reaccept_stored_script()` reopens without restoring and sends the engine's own stored source back through `write_script`. |
| `cadex_animate.py` | an accepted simulation trace → F-Curves on the component instances: time-keyed (not frame-index-keyed), wxyz quaternions walked into one hemisphere, bulk `foreach_set` onto slotted actions, cleared and re-baked per revision. A sibling of `cadex_hydrate.py`, so a bad trace never costs you the geometry. **The trace may come from kinematics, from rigid-body dynamics, or from a learned policy rollout** — `_simulation_entries` selects on `artifact_kind == "assembly_simulation_json"` and all three produce it, so this file plays a trained gait without one line of it knowing that policies exist (ADR-077, ADR-085). That is not luck: it is why a rollout deliberately reuses the output type instead of inventing one. Selecting on a *kind* rather than trying to enumerate producers is the property to preserve — the same code must ignore, never fail on, the MJCF / task / policy-receipt kinds it will also be shown. It also holds the pure half of the Policy Outputs readout: `commands_table` turns a rollout's `actuator_commands` into a flat frame-indexed table on the scene, and `commands_at` returns the row **at or before** a frame — a zero-order hold, because a command is a decision taken at a control step and held, not a continuous quantity to interpolate (ADR-096). A trace with no `actuator_channels` yields no table, which is what keeps the panel off kinematics and plain dynamics runs. |
| `cadex_hydrate.py` | `cadex-tessellation-v1` buffers → Model-collection mesh objects: `cadex_face` INT face attribute (1-based BREP ids), `cadex_edge` wire children, placements, contract-driven GC by `cadex_output` property. **ADR-177**: component instances (and their wire children) link into an `Assembly` collection **inside** Model rather than at its root — the exploded-view pattern publishes every part twice (the solid and its component), and the copies grouped under one toggleable outliner row is what keeps a 17-part blowout readable. A *child* of Model deliberately: every walker here uses `all_objects`, which recurses, so find, GC, posing and bounds see the components exactly as before (the opposite trade from `cadex_collision`'s sibling collection, which exists to be outside that recursion). The collection follows its contents — created on the first component, removed by the GC with the last. |
| `cadex_cage.py` | **ADR-127.** The section cage's rings, drawn as an edge-only overlay so they can be dragged. A **sibling** collection of Model at the scene root and never tagged `cadex_output`, both for `cadex_collision`'s reasons: the hydrate GC walks `all_objects` and hunts that property, so either would have the overlay swept on the next rebuild. The pure half — the superellipse profile, the cage frame, and `row_from_placement`, which turns a dragged transform back into a row — imports no `bpy`. **Apply, not auto-push** (ADR-122): a ring drag is a stream of transform events, so edits accumulate in the viewport and one button sends the whole table through `set_params(cages=…)`. Two gestures are deliberately ignored: movement *across* the spine (a cage is straight by construction; a curved one is `part.sweep(scale_law=…)`) and rotation (roll and exponent stay editable as numbers, because inventing them from a gesture is the quiet reinterpretation a declared table exists to prevent). |
| `cadex_print.py` | **cadex ADR-156, ADR-158.** Which outputs are parts to print: a cache of the engine's **roster** (every accepted output that could become an STL) and the **ticks**, which are ours. A tick lives in one scene ID property, `cadex_printable`, so it saves with the .blend, costs no round trip, no store write and no revision, and never reaches the engine until `export_printable` names the job. `toggle()` checks the name against the roster and flips it in the scene; `marked()` is what the export sends, filtered against the roster so a stale tick cannot turn a whole job into one refusal. Nothing here draws and nothing here writes a file — the panel is one operator row per entry in `ui.py`, and the STLs are the engine's to write. The roster costs no round trip either: it rides in the `inspect scope="script"` block `cadex_backend._adopt_script_state` already takes on open and after every accepted rebuild, which is also where a tick for a part the script stopped publishing is dropped (cadex ADR-039's drop-on-drift, now on this side of the boundary). |
| `cadex_collision.py` | **ADR-091.** The collision geometry a dynamics model actually simulates, drawn as an edge-only wire cage per shape. Reads what the engine already publishes — `model_evidence`, either from a simulation trace's `dynamics` key or via `inspect` on the mjcf publication object's `CadexAssemblyMjcfValidation` — so it cost **no engine change and no protocol change**; both readers are needed, because an mjcf-only model has no trace and a rollout's trace carries the evidence dict without the collisions block. Objects are named exactly the MuJoCo geom (`<component>/collision<n>`) and live in a **`Collision` collection that is a SIBLING of `Model`, not a child** — `cadex_hydrate._cadex_objects` walks `all_objects`, which recurses, so a child would be swept by the contract GC; they are tagged `cadex_collision_of` and never `cadex_output`, which is the same isolation on a second axis. Zero polygons, so picking is unaffected and nothing occludes the surface being compared against. Parented with an identity `matrix_parent_inverse`, so the cage follows the bake, the preview and the solved placement for free. The pure half holds the `size_m` conversion table exactly once — box is half-extents, capsule's half-length is of the cylindrical section only — and imports no `bpy`. A sibling of `cadex_hydrate.py` exactly as `cadex_animate.py` is, so a bad collision record never costs you the geometry. |
| `cadex_training.py` | **ADR-098.** The shell's view of a training run happening on another machine, and it is one JSON file: `training-progress.json` in the project root, which `training/remote_train.sh watch` mirrors off the GPU box. Its whole import list is `json`, `os` and `bpy` — **no mujoco** (`test_the_shell_never_learns_about_mujoco` is the branch-wide form of that) and **no transport**, because a panel that opened a network connection would block Blender's main thread the first time a box was slow. A gate check asserts that closure exactly. Absent, unreadable, half-written and wrong-schema all read as *no run*, which is what keeps the panel invisible on a project that never trained; a partial read is deliberately not cached, so the panel notices the moment the writer's `replace` lands rather than on the next write. The `bpy.app.timers` poll is an interactive convenience — it stats the file and tags the parameters editor for redraw — and every function it calls is written to be callable directly, because timers do not fire under `--background` and that is where the gate runs. |
| `cadex_training_plot.py` | The reward curve, drawn in the Training editor — **the shell's first plot**. Draws the `curve` field the trainer publishes into `training-progress.json` (compact `[iteration, reward]` pairs, capped at 512) as a line in the bottom `PLOT_FRACTION` of the `CADEX_TRAINING` window region; the floating panel keeps the top. A **separate module by necessity, not taste**: the gate pins `cadex_training.py`'s import closure to exactly `{json, os, bpy}`, and even a lazy import of a plot would trip it — so the dependency is one-way, `plot → training`, through `read_progress`, and a gate check asserts `cadex_training` never mentions this module. A progress file from an older trainer has no `curve`, `curve_from` returns `[]`, and the editor is panel-only — degradation by construction, no version check anywhere. **No operator classes at all**: there is no train button (ADR-084 — the agent dispatches, the UI reads out), and no timer of its own either, because `cadex_training.poll` already tags the area when the file moves. Mechanics are `cadex_dimension.py`'s exactly: module-level `POST_PIXEL` handler (on `SpaceCadexTraining` — the first draw handler on a Cadex space type), lazy `gpu`/`blf`, and a pure half (`curve_from`, `axis_ticks`, `plot_layout`) that imports `math` alone and is where every number that can be wrong lives, exercised by the suite that needs no engine. |
| `cadex_pick.py` | Viewport pick → a pin queued onto the next chat message (like image attachments), in two flavours sharing one eyedropper modal and one queue. **Face pin** (`mesh_agent.pick_pin`): polygon → `cadex_face` → `resolve_pin` → `@face-N`, BREP outputs only. **Point pin** (`mesh_agent.pick_point`, ADR-056): the ray-cast hit and its normal, pushed back through the object's placement into the output's own space — no engine round-trip, and it works on mesh outputs, which have no faces to name. A point and a direction *is* a `part.cable` port. Since ADR-139 the queue also carries **requests** — one sentence saying what the pins are *for*, drained by the same call, so a gesture and its instruction can never separate. `mesh_agent.measure_pins` is the only thing that queues one and is inert below two pins. |
| `cadex_dimension.py` | **ADR-139.** Declared measurements, drawn as architectural dimensions: an extension line at each anchor, a dimension line between them, and the number in the middle with the line broken around it. **Everything except the two anchors is computed in screen space**, and that is the design rather than an implementation detail — the number is always upright and the same size at any zoom, the offset direction is perpendicular *on the screen* so it can never go edge-on however you orbit, and every gap, tick and pad is a pixel constant so a 2 mm boss and a 2 m beam read identically. One `POST_PIXEL` handler, not the two `cadex_live` needs, because a dimension is not a world object. **The degenerate case is handled rather than avoided:** look straight down the measured axis and the anchors project to the same pixel, so below `MINIMUM_SPAN_PX` it becomes a *leader* — a stub and the number — and the value is never lost at any angle, which is the whole claim. A diameter is the one view-dependent case: the engine publishes the circle and the overlay picks the widest on-screen diameter from 16 projected samples per frame. Anchors arrive in the measured output's **own** frame and are pushed through `display[subject].placement` once per revision, not per redraw. It creates **no Blender objects**, so unlike `cadex_collision` and `cadex_cage` it needs no sibling collection and cannot be swept by the contract GC. Records refresh on every response including mid-drag — the opposite trade from the collision cage, for the opposite reason: a cage left over from the previous shape is wrong, and a number recomputed for this one is right. **ADR-176 adds the two drafting kinds**: `radius` rides the diameter's published ring and draws centre-to-rim (`radius_geometry` — the projected widest diameter's midpoint IS the projected centre, so no second projection can disagree with the first), and `angle` draws two rays from the engine-published vertex with a chordal arc between them and the degrees upright on the bisector (`angle_geometry`); both degrade to the leader when the projection collapses, so no value is ever lost. The same pure functions draw the blueprint sheet's dimensions, which is why they live in this module's pure half. |
| `cadex_drawings.py` | **ADR-178, ADR-179.** The **Blueprint Editor**: the model's technical drawings in a window of their own — `CADEX_BLUEPRINT`, the seventh Cadex space type (the §2b checklist's first single-editor run), so a drawing and the model arrange side by side and **each editor area holds its own selection** (the live draft, or any sheet in the project's blueprint store — two windows, two drawings). `make_blueprint` renders the sheet as the live draft and **stores nothing**; the draft re-renders on every call and re-renders *itself* when the model rebuilds (an `on_hydrate` hook in the view registry at order 70, debounced `RERENDER_DELAY`; drafts shown nowhere catch up on next draw via `_outdated`). `save_draft` is the one write path — the `save_blueprint` tool and the header's Save button both call it, `put_blueprint` beneath, ADR-157 name/version semantics unchanged — and Export copies the shown sheet's PNG anywhere (draft or stored) without touching the store. The header carries the controls: the sheet menu (draft first, stored newest-first — pure `selection_options`), the pager, Save while the draft shows, Export always; the window's ground is the theme of the sheet it shows. **Tagging a section is the pin idiom, fourth queue**: a click maps region→sheet pixels (`sheet_point`, the letterbox fit inverted)→cell (`hit_cell` over `cell_rects`, which adds the dress-time margin band back exactly once — the compose step's rects are field-relative), queues the cell (`queue_section`), draws its outline and `@cell-N` handle, counts in the chat header beside the face pins, and drains into the next turn via `consume_section_notes` in `Agent.start_turn`. Tagging works on the draft only; a stored sheet is view-only. Clicks arrive through two `poll`-gated add-on keymap items on the **Window** keymap (a custom space installs no keymap; unhandled clicks bubble to window handlers) and pass through outside a cell. The stored list reads straight off `<project>.cadex/blueprints/blueprints.json` (schema-checked; never `inspect scope=blueprint` — the pager stubs any value over 1 KiB, the ADR-177 lesson), cached per root, never read from the draw callback. Per-editor selections are session state keyed by the space pointer — the space's DNA stays a bare `SpaceLink` header (gate-pinned), so nothing has to be versioned into saved files; a reopened file starts on the draft or the newest sheet. On a bundle without the C++ half, `EDITOR_AVAILABLE` goes False and everything space-bound stands down (the `wiring_ui` arrangement) while the draft, queue and tools keep working. Mechanics otherwise ADR-178's: module-level `POST_PIXEL` handler on `SpaceCadexBlueprint`, lazy `gpu`/`blf`, textures image→numpy→`gpu.types.Buffer` so no datablock rides into a save, invisible to offscreen renders by construction, pure half above `-- the bpy half --`. The viewport keeps exactly one blueprint thing: the ADR-150 restyle, now settings-box-free (`blueprint_view` and the toggle button set it; theme and grid ride the scene group for the tool). |
| `cadex_landing.py` | **ADR-167, ADR-168.** The landing screen: the start page drawn *inside* the 3D viewport on a fresh launch — example-project card, New/Open/Tutorial — while the chat column stays live beside it. There is deliberately no Start Chatting button: the chat is already open beside the page and typing into it dismisses the page. Not a popup, and not a reversal of ADR-042: Blender's modal splash stays disabled, and this is the FreeCAD-style alternative to it. Mechanics are `cadex_dimension.py`'s exactly (module-level `POST_PIXEL` handler, lazy `gpu`/`blf`, pure `landing_layout`/`hit_test` the suite drives headless); input is three add-on keymap items on the 3D View (left-click dispatcher that consumes the click while the screen is up, mouse-move hover, Escape) rather than a modal grab, so nothing else stops working. Exits: any action, a real file load, Escape, or the first chat message (`Agent.start_turn` calls `dismiss()` — the hook that makes "the chat on the right is live" true). The page has no palette of its own: colours are read from the running theme (`wcol_regular` composited over the viewport ground at the theme's own alpha), corners are rounded by pure geometry (`rounded_rect_points`, fan-triangulated — no `TRI_FAN`, which Metal dropped), and text is `blf` font 0, the app's own UI font. The header is the product mark, `landing_logo.png` — the 512 px representation extracted from `cadex_icon.icns`, so the page shows exactly what the Dock shows (ADR-059 is that icon's provenance; the stale VibeCAD-era `docs/images/cadex-mark.svg` it warned about is now deleted, ADR-168); the demo's card art is `demo/card.png`. Both are drawn from `gpu.types.Buffer`s so no Image datablock is left to ride into the user's next save. The layout hides the card when `demo_source()` finds nothing, so a compliance removal (as ADR-171 was for the drone) is a file deletion, never a code change; since ADR-173 the biped demo ships. The stamped `cadex_version.txt` is read for the header; a raw ninja build shows none. |
| `demo/` | **ADR-167, ADR-171, ADR-173.** The shipped example project: the MG90S biped (`biped.blend` + `biped.cadex/` + `card.png`, the card a 1152x720 offscreen render of the model in the product viewport look — matcap + cavity + edge wires, three-quarter camera fitted to the robot, the simulation floor hidden for the shot, workspace chrome suppressed). ADR-171 removed the drone here because its seven imported STLs were models of real commercial parts with no recorded origin; the biped meets that bar by construction — entirely script-authored, its only asset the Cadex-trained `biped-balance.cxpolicy` the script replays. The store is sanitized: no transcript, no machine paths, no blueprints/artifacts caches, script history pruned to the accepted revision, both Python scripts carrying GPL-2.0-or-later SPDX headers with matching saved revisions — and the `.blend` itself is scrubbed (the chat transcript saves into it as a text block, and hydrate leaves absolute `cadex_sidecar` cache paths on every object; both removed). All pinned by `test_landing_demo_payload_ships`, including a headless subprocess that opens the shipped `.blend` and holds it to zero text blocks and zero machine paths. A `.blend` plus matching `.cadex/` store placed in `demo/` beside the add-on appears on the landing screen automatically; deleting them hides the card with no code change. **Opening a demo always copies first** — `open_demo()` lands a fresh-stem pair under `~/Documents/Cadex Demo/` (stems must match: the engine root is derived from the .blend name) — so the bundle is never opened in place. |
| `cadex_section.py` | **ADR-148.** The section view: cut the model open on a plane and take the near half away. A hidden cutter box plus a **Boolean DIFFERENCE** modifier on each hydrated solid, and a geometry-nodes clip on each edge-wire child — two mechanisms because the model is drawn as two kinds of object, and a boolean has nothing to say about a mesh with no faces in it. **A boolean rather than `rv3d.clip_planes`** for three reasons, each sufficient: a clip cannot fill what it opens (the cut face is capped here, so a cut bracket reads as material with a ring where the bore is), clip planes are per-region view state that no offscreen render carries, and `--background` has no `RegionView3D` at all so the gate could never see it. Measured cost: **6.3 ms** per offset change on the blind-bore part. **It is a view, not a feature** — nothing reaches the engine, nothing is written to the script, and the gate asserts the accepted revision is unchanged either side of switching it on. Because it is modifiers rather than an overlay it survives a rebuild for free (hydration swaps the mesh datablock and keeps the object), so `cadex_backend.hydrate` calls `refresh` for one reason only: a brand-new output has no modifier on it. `model_bounds` reads the mesh datablocks with numpy rather than `obj.bound_box`, which reflects *evaluated* geometry — measured, not assumed: a 20 mm cube cut at z = 5 reports a top of 5, and every number derived from the model would otherwise feed back on the cut that produced it. The plane is never clamped to the part; when it is off the end the panel and the tool say so. `quiet()` (ADR-151) exposes the settle guard so `cadex_sheet` can write several settings and trigger one explicit `refresh`. The pure half — plane, normal, cutter placement, `is_kept` — imports no `bpy`. |
| `cadex_explode.py` | **ADR-149.** The exploded view: spread the assembly along the explosion moves the *script* declares, with a factor slider from 0 (assembled) to 1 (fully exploded) and leader lines. The engine authors everything — staged cumulative poses, final poses and line segments arrive on the exploded-view output's display entry — and this module only interpolates: lerp positions, slerp orientations (hemisphere-corrected), stage *i* of *N* owning factor window [i/N, (i+1)/N]. Poses are written to `matrix_world` — the channel hydrate already owns — and re-applied by the hydrate hooks after every response, so engine poses land first and the spread lands on top, always; delta channels were rejected as a second owner for the same question. **Refuses while a simulation is baked**: F-Curves and `matrix_world` writes cannot share an object honestly. Leader lines are one wire object in a sibling `Exploded` collection (the `cadex_collision` pattern — must exist under `--background` and in renders), never tagged `cadex_output`. One exploded view per model; two is refused naming both. `render_views` suspends it; `viewport_screenshot` leaves it on. `quiet()` (ADR-151) exposes the settle guard so `cadex_sheet` can write several settings and trigger one explicit `refresh`. The pure half — staged windows, slerp, matrix decomposition, line growth — imports no `bpy` and no `mathutils`. |
| `cadex_views.py` | **ADR-150.** The registry of presentation views. Five modules restyle the viewport without touching the script — collision, section, explode, dimensions, blueprint — and used to be hand-wired into the same call sites; now each registers a record (`name`, `order`, and up to three hooks: `on_hydrate`, `on_preview`, `suspend`) and the call sites walk the registry. Orders: collision 20, section 30, explode 40, dimensions 50, blueprint 60 — section before explode is load-bearing on the preview path, dimensions last because it reads what the others posed. Per-record try/except keeps each view's stated failure terms: a malformed record costs its view, never the geometry, never the views after it. `suspend_for_render()` returns one undo that unwinds in reverse order. Collision and dimensions are installed by `install()` (they own no `register()`); the other three self-register. |
| `cadex_blueprint.py` | **ADR-150.** The blueprint view: the model as white outlines on a blueprint-blue, cutting-mat-green or grey ground, live in the viewport. Pure viewport state — one field table (`shading_values`) written to `space.shading`/`space.overlay`, the replaced look captured on the scene and restored exactly on toggle off (fallback `PRODUCT_LOOK` = the gate-pinned startup styling, used only when the capture is lost). The one measured dependency: the true-BREP `… Edges` wires draw in the *overlay* wireframe pass, so this view turns `show_overlays` ON (the product look now ships it on too, bare) and must hold every sub-overlay explicitly False. `wireframe_color_type='OBJECT'` turns the wires white because nothing writes `obj.color`. Layers over section and explode by construction; suspends for `render_views`; `present(space, theme)` is the offscreen-render half `render_blueprint` uses. The pure half — themes and the field table — imports no `bpy`. Theme colours darkened ~20–25% with ADR-151, lines still white; the contrast invariant is pinned in the pure suite (in either direction since ADR-176). **ADR-176 adds the fourth theme, `technical`** — black lines on drawing-paper white, the print-style technical drawing — and with it the one theme-dependent field: a dark-lined theme writes `wireframe_color_type='THEME'` (the shipped UI theme's wire colour is black) where the white-lined themes keep `'OBJECT'`, because white wires on paper white would erase the model's own edges. |
| `cadex_sheet.py` | **ADR-151, ADR-152, ADR-153, ADR-157.** The composable blueprint sheet: spec, tiling, dressing, and per-cell scene state. The pure half validates the tool's `views`/`layout` into specs (`normalize_views` — refusals are full sentences carrying the fix; at most `MAX_VIEWS = 6`; duplicates allowed on purpose; per-cell `hide` or `only` — the isolate, normalized into the complement hide), picks the template (`choose_layout` — seven templates; an omitted `views` is the **triptych** default: front/top/bottom stacked down the left third, the three-quarter perspective in the centre third, the rear (Z+180) perspective fully exploded in the right third, degrading to unexploded when the model declares none; the **mosaic** is the freeform one — every view carries `cell [row, column]` + optional `span`, the grid inferred from the placements, overlap and missing cells refused, unclaimed cells left as ground on purpose, ADR-152), tiles by shared integer boundary arrays (`layout_rects` — no-gap/no-overlap by construction for the templates, by refusal for the mosaic; paint-count-tested at awkward sizes), and computes the drawing-sheet dressing: `zone_grid` (page grid with border zone marks — columns `1..` along the top, rows `A..` down the left; owner chose zones over mm graph paper), `title_lines` (project top-left; `CADEX <version> · rev · date · theme` bottom-right, version read from the engine manifest the shell already ships) and `cell_legend`. The sheet ground is ONE colour: the margin band takes the colour-managed value the tiles arrived in (sampled off the field, `display_color` as the pure fallback — the ADR-151 addendum). The bpy half is the per-cell state machine: `snapshot_state` once before the loop, `apply_view_state` per cell (hides via `hide_set` — `hide_viewport` is hydrate's channel — then explode, then section, in that order because the wire clip bakes the plane in each object's own frame), `restore_state` as ONE flat exception-hardened restore, and `_dress_sheet`, the second offscreen pass that draws the tile field as a textured quad plus grid/zones/labels/titles with the in-tree blf recipe (`blf.size` is two-arg in this build; DejaVuSansMono loaded via `system_resource`, falling back to font 0). ADR-153 widens the surface three ways: sheets are **16:9 by default** (`sheet_aspect` — any `width:height`, `auto` for the layout-derived shapes; the mosaic defaults to auto because its shape IS the agent's grid, and `layout_rects` tiles the non-square field off the same boundary arrays); exploded cells grow **part-name callouts** (leader lines to each visible output's projected centre — side/stack/drop arithmetic pure in `callout_layout`, on by default exactly when a cell is exploded, glyph measurement left to `_dress_sheet` because only `blf` knows where a text ends); and `{"view": "params"}` renders the **parameters panel** as a cell — `param_rows` mirrors `cadex_backend._bridge_params`'s range defaulting on purpose, `params_panel_layout` collapses overflow into one `+N more` line, `_draw_params_tile` draws the slider rows on the sampled ground, and a script with no parameters refuses the cell in `validate_against_model` (gate-testable headless).. ADR-157 widens it three more ways. **Per-cell shape**: any cell takes an `aspect`, honoured by measurement rather than algebra — `_boundaries` now takes weights instead of a count, `_place_rects` is one placement pass, and `layout_rects` places, measures what shape each cell came out at, scales the track that cell owns toward its ask and places again (`ASPECT_PASSES`, clamped by `MAX_CELL_SCALE`, an ask that would starve a neighbour below 8 px dropped whole). The cells compete for one fixed field, so the caption reports **the shape drawn** rather than the shape asked for, and the tiling invariant is unchanged — the same paint-counting now runs over random asks. **Text panels**: `{"view": "text"}` with up to `MAX_PANEL_TEXT_CHARS` of words, wrapped by `wrap_text` against a caller's `measure` (so the pure half wraps at real glyph widths without importing `blf`), laid out by `text_panel_layout` and drawn by `_draw_text_tile`; overflow becomes one `+N more lines` row and a note, never a silent clip. `params_panel_layout` took the same `top_pad` at the same time, which fixed an ADR-153 defect a windowed probe found: in a short cell the first slider row was drawn through the word "parameters". Any cell also takes a `title`, which is its drawn heading. **The recipe**: `recipe_view`/`recipe_views`/`sheet_recipe` turn validated specs back into the tool's own input form, pinned by `normalize_views(recipe_views(specs)) == specs`, and `trim_meta` drops the optional records before the engine's `meta` cap can refuse a sheet that is already drawn — the recipe is what a trim defends. **ADR-176 makes the sheet a functional technical drawing**: every model cell takes a `dimensions` flag (explicit wins; omitted, on for orthographic cells — `dimensions_active` is the rule, `callouts_active`'s shape), `dimension_jobs` projects the script's declared `part.measurement` records into cell pixels through the SAME fitted matrices the tile renders with (subjects hidden in the cell are skipped), and `_dress_sheet` turns each job into drafting geometry — extension lines, the dimension line broken around its number, radius line, angle arc — via `cadex_dimension`'s pure functions, fed the measured glyph widths, in the theme line colour above the dressing alphas. A dimensioned cell renders at `DIMENSION_FIT_MARGIN` so the numbers have ground to sit on; the legend echoes only explicit asks and the renderer's note carries the drawn count. |
| `wiring.py` | **ADR-066.** The Wiring graph's model: `CadexWiringTree`, `CadexBoardNode`, `CadexTerminalSocket`, `ensure_tree`, `sync_from_engine`, `rows_from_tree` and `push`. **Nothing is sent until Apply is pressed (ADR-122):** every edit sets `cadex_dirty` and the 0.15 s leading-edge debounce that used to fire behind it is gone — it turned a burst of twenty drags into one push plus nineteen that piled up on the client lock and were then refused as stale, in silence. `push` is now called from exactly one place, sends both declared tables in one `set_params`, and keeps every guard it had; `on_push_finished` is the single completion path, and **on failure it keeps the canvas** rather than resyncing, because losing twenty drags to one refusal is worse than an inconsistent canvas (Revert is how you discard them). The graph is a *projection* of `inspect scope="wiring"` — nodes, sockets and links are rebuilt from the engine and never from the canvas, so Revert puts back what the engine actually holds; the one thing it owns is `Node.location`. Two sockets per terminal — `tree.links.new` raises `Same input/output direction of sockets` for output→output *and* input→input, so one row per terminal and drag-to-connect cannot both hold — keyed by a registered `terminal` property (duplicate socket names dedup into `sda`/`sda_001`), drawn `sda ▸` and `▸ sda` so the pair reads as one terminal (ADR-122), with solder state carried as socket colour *and* a checkbox on the socket row (a link holds no properties, and `part.solder` takes a terminal and never a wire — ADR-063). **Solder is edited on the socket and pushed like any other edit (ADR-113):** `soldered` carries an `update=` callback, because `NodeTree.update()` fires on topology and never on a property written into a socket, so without it the debounce never armed; the callback mirrors onto the terminal's twin socket, and `_solder_for` reads the sockets as the answer — either end ticked means the row is soldered, both clear means it is not — rather than falling back to the stored row, which could only ever turn solder on. **The canvas is only pushed while it is a whole projection (ADR-115):** `apply_state` refuses to reconcile two components onto one node, records any row it could not draw and raises `cadex_stale`, and `push` stands down while that flag is up — an empty canvas describes an empty table, and a push replaces the declared list wholesale. A completed sync also clears `cadex_pending`, which saves into the `.blend` and otherwise left "applying…" in the header forever. Rows marked `editable: false` (a cable or bundle the script built outside `nets(...)`) draw like any other link; `declared_rows` strips them from the pushed table. **A socket also carries its own row since ADR-120** — `origin`/`axis`/`hole_dia`/`depth`, millimetres in the board's own frame, with the same `update=` mirror the solder flag has — so the terminal table rides the same debounce as the connection table and a rename that moves a terminal *and* the wires addressing it is one `set_params`. Two bugs went with it (ADR-121): the no-op guards compared canvas rows against engine rows carrying a route and so could never fire, which made a redrawn link cost a full re-execute; and `on_push_finished` stored the canvas flat, wiping `path` off the table, which is what made Edit Wire Path report no published route. The duplicate-port skip now reports rather than dropping a node in silence. **A fresh socket reads soldered since ADR-122** — the state of a terminal nothing has landed on yet — so a drawn wire carries a joint without anyone ticking anything; `apply_state` therefore has to set the flag in *both* directions, per address and with the same *any* rule `_solder_for` reads back out, or an unticked row would come back soldered. |
| `wiring_ui.py` | **ADR-066.** Its chrome — header, three sidebar panels, `NODE_MT_add`, and the **Apply / Revert** pair (ADR-122): `MESH_AGENT_OT_apply_wiring` is the only thing that sends the canvas and its poll is false while one push is in flight; `MESH_AGENT_OT_sync_wiring` keeps its idname — `bl_mesh_agent.py` asserts exact idnames on the button row — and is labelled Revert, because "rebuild from the accepted revision" *is* discarding edits once the canvas can hold ones that were never sent. The Terminal panel lists the selected board as one row per terminal with its solder checkbox, which is where a board reads as the single list it is. The only module in the add-on allowed to fail registration: a `Panel` naming an unregistered space type raises and would abort the whole loop (the ADR-036 failure), so it guards each class and sets `EDITOR_AVAILABLE = False`. That is what lets everything else run on a bundle built before the C++ half. |
| `cadex_wire_path.py` | **ADR-118.** The wire-path round trip: **Edit Wire Path** opens the route the engine published for the active cable as a real `POLY` curve in a sibling collection (the `cadex_collision.py` pattern, but selectable — it exists to be grabbed), **Confirm** reads the control points back, queues a note and **starts the turn itself** with a fixed prompt, and **Cancel** throws the curve away. There is no gizmo code because there is no gizmo: G/R/S, snapping, axis constraints, proportional edit and the N-panel's numeric fields are Blender's, and all of them work on curve control points. The wire is identified by the **object** in the 3D view and not by a link on the canvas — a Blender `NodeLink` carries no selection state at all, and two selected board nodes would be ambiguous the moment two signals run between the same pair. Seeds from the row's `waypoints`, so no stub-knot arithmetic lives here; a bundle conductor publishes an empty one and is refused by name. |
| `cadex_terminal_pick.py` | **ADR-067, ADR-117.** Edit-Mode selection → a measured terminal, handed to the next chat turn. The bore axis is the scatter matrix's *odd-one-out* eigenvector (two of three eigenvalues are equal on a circle) and not its smallest, which is the plane-fit answer and is wrong for any bore deeper than its radius. **Two models are then fitted to the same points** (ADR-117): a closed-form least-squares circle, and a minimum-area enclosing rectangle by rotating calipers over the convex hull — a pad is usually square, and four corners fit a circle *exactly*, so a circle alone is meaningless on one. `AUTO` takes whichever has the smaller residual once normalised by its own scale (radius, half-diagonal) and **refuses when the two tie**, naming both fits: that case is genuinely ambiguous and the operator's `kind` enum is the override. Refuses under four vertices and refuses a fit worse than 15% of the winning model's scale — a quality gate, never a classifier. One ring is enough for a bore; selecting both rims drops the far one and says so. The row carries `origin`/`axis` (plus `hole_dia` for a bore) and **never a depth** — the terminal lands in the selected plane; a pad's width and height go in the *report*, so `pad_dia_mm` can be chosen without putting a rectangle field on a layout row. Its own queue and its own wording: a pin is not a terminal. **ADR-119** adds `define_board` beside it: click an object the engine built, name it, and the next turn is asked to declare that output as a port in `nets(ports=...)`. It is the one gesture that starts from a click on the *mirror*, so the note carries the engine's output key and never `obj.name`; it also stamps the object, so every later terminal pick on it says which board it is on — click board, click terminals, one turn declares the whole port. The note states two limits rather than promising around them (a component cannot avoid itself as a mesh; `shape_from_mesh` cannot express a multi-shell import) and one more: a board with no terminals yet draws no node, because a node is a terminal set. **ADR-121 changes where the measurement goes:** when the script declares `boards(...)`, the fitted row is written straight into `board_values` through `set_params(boards=[...])` — no chat turn, and the socket simply appears. It goes out in **world** coordinates marked `frame: "world"`, because a click has no other frame and a hydrated object's transform is a display placement rather than the asset's declaration chain; the engine inverts the chain it resolved. The note path remains for a project with no board to write onto, where creating one is authoring and the assistant's job. **ADR-126 adds `define_mount`**, the same gesture one table over: it fits the same way, writes into `mount_values` through `set_params(mounts=[...])`, and never queues a note — there is nothing an assistant could usefully transcribe about a frame. What a rim selection does not contain is the **roll**, so the operator projects world +Z across the fitted axis (+X where that vanishes), writes it, and reports the roll it wrote; the row is in a table the user can edit, which is the argument for the table. It refuses outright when the script declares no mounts for that component, rather than sending a row the engine would reject with the measurement lost. |

### The script loop (source of truth)

- The **single script** is the artifact, and it lives in the engine's project
  store, not here. `bpy.data.texts["model.py"]` (`use_fake_user=True`) is a
  **mirror** of it, so the script is visible and searchable in Blender.
  It is viewed in the stock **Text Editor** (editor dropdown, then the text
  dropdown) — no custom editor, because that buffer already exists and the
  Text Editor brings syntax highlighting, line numbers and find for free
  (ADR-035; the open-a-view operator went with ADR-165).
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
  every session a moment after the new name takes effect (ADR-046). Its
  sibling for the other way a file stops opening is the **Re-accept Stored
  Script** box (ADR-187): a project whose stored script no longer
  reproduces its accepted digest — accepted under a different engine build,
  or edited outside Mesh — refuses to open, `locked_out_project()` reads
  the cached failure code, and the operator sends the *engine's* stored
  source back through `write_script`, which is the one op that runs on an
  unrestored project (ADR-044). A hand edit is accepted as edited.
  **Imported geometry is the one thing that does come across**: assets are
  inputs, not derived state, and a script that names one cannot re-run
  without it, so `migrate_assets()` carries `assets/` into the new project
  through `put_asset` when the script is adopted — the imported meshes, the
  linked `.cxpart`s (ADR-138) and, since ADR-188, a trained `.cxpolicy` with
  the `.json` task bundle and `.xml` MJCF it travels with, which is the one
  input nothing can rebuild. `CARRIED_ASSET_SUFFIXES` is the list, and it is
  now the engine's whole stored union. `save_pre` is what records
  *which* project to carry from (`SOURCE_PROP` — `bpy.data.filepath` still
  names the old file there, and the value saves into the new one) — but
  **only when the root actually moves** (ADR-155). `save_pre` fires on every
  write, and recording unconditionally meant one ordinary Ctrl-S after a
  Save-As overwrote the pointer to the original with the file's own root,
  leaving the carry with nowhere to carry from and no way to say so.
  `remember_source_root` compares `destination_root(scene, filepath)` — the
  path `save_pre` is handed — against the current root, and writes nothing
  when they match.
- **There is one backend.** Until ADR-030 there were two, chosen by a mode
  dropdown: this one, and a local path that `exec()`d the script against
  `bpy`. The local path and everything serving it — `cad_api.py` (the
  `mesh_cad` millimetre solid-modelling helpers), `validation.py` (the BMesh
  geometry checker), `scene_graph.py`, most of `model_api.py`, and
  `tests/python/bl_mesh_agent_cad.py` — were deleted. That was where nearly
  all the deep Blender coupling lived: BOOLEAN/BEVEL modifiers, the
  depsgraph, BVHTree, `orphans_purge`.

### The AI bridge

**Harness and account settings (ADR-184).** The chat header selects Claude
Code, Codex, or pi and a model; its account popover shows the full account
identity and login controls. Settings > AI also provides
**Sign in / Switch account**, **Refresh**, and the selected CLI path. Sign-in
opens the installed CLI's own flow in Terminal (`claude auth login`, `codex
login`, or pi's `/login`); exit the harness to refresh automatically, or use
**I've finished signing in** after closing Terminal. Cadex stores no credentials.
Claude and Codex expose email/subscription when available. pi has multiple
provider credentials: display metadata identifies the account when provided;
API-key providers explicitly say that identity is not reported.

Model menus are discovered asynchronously, with no prompt/model turn: Claude's
stream-JSON initialize response, Codex app-server `account/read` and paginated
`model/list`, and pi RPC `get_available_models`. pi discovery disables user
extensions just as product turns do. These are the harnesses' offered models,
not an independent guarantee of provider quota or entitlement. There is no
Cadex-owned model catalog. **Harness default** omits `--model` on fresh and
resumed turns. Explicit choices persist as strings separately for each harness;
an unavailable saved choice stays visible and must be changed before sending
when a successful catalog has established it is unavailable. Model menus support
type-to-search. A missing CLI or failed probe shows a remedy, without invented
fallback models. Snapshots are scoped to harness and CLI path, refreshed after
login or explicitly, and refreshed on redraw after 60 seconds. Network-disabled
sessions do not start discovery or login.


- Per turn, `backend.py` spawns the chosen agent CLI — Claude Code
  (`claude -p … --resume`) by default, OpenAI's Codex (`codex exec --json`)
  since ADR-174, or pi (`pi -p --mode json`) since ADR-175. The Mesh tools
  reach the CLI through one of two transports over the same bridge: an MCP
  stdio server (`mcp_shim.py` — Claude and Codex) or a native pi extension
  (`pi_tools.js` — pi speaks no MCP by design, and the extension registers
  the bridge's tools with `pi.registerTool()` instead). Either way every
  tool call lands on `bridge.py` over authenticated localhost TCP; the
  bridge queues it for the Blender main thread and returns the result. MCP
  is a transport here, not the architecture.
- **pi's mechanical differences**, each verified against pi 0.84.4 and
  test-pinned: `--no-builtin-tools` removes pi's own read/bash/edit/write
  (the ADR-163 posture); `--no-extensions`/`--no-skills`/
  `--no-context-files`/`--no-prompt-templates` keep the user's own pi setup
  out of product turns; the session id is *minted by the backend* because
  pi creates a missing `--session-id` fresh — which is also the stale-id
  degradation path, so pi needs no resume fallback; the model is a free
  provider-qualified ID chosen from pi's catalog ("" = its configured default); and the subprocess PATH is prefixed with pi's directory so
  its `#!/usr/bin/env node` shebang resolves under nvm.
- **The provider is a preference, the event contract is not.** The agent
  understands exactly three stream shapes (text deltas, tool_use notices, a
  final result), and every backend produces them; `CodexBackend` translates
  Codex's JSONL vocabulary rather than teaching `agent.py` a second one.
  Codex's mechanical differences, each verified against codex-cli 0.142 and
  test-pinned: the system prompt travels as `AGENTS.md` in a private
  workdir (`-C`); `mcp_servers.mesh.default_tools_approval_mode = "approve"`
  because `codex exec` auto-declines approval prompts, which would silently
  disarm every Mesh tool; its own shell tool cannot be removed, so it runs
  under `--sandbox read-only`; and `exec resume` accepts fewer flags than
  `exec` — an unaccepted one is rejected outright and the resume fallback
  quietly downgrades every follow-up to a fresh conversation.
- **A session id resumes only into the CLI that minted it.** The transcript
  in the .blend carries `session_provider` beside `session_id`; untagged
  saves predate providers and are Claude's. Switching the provider
  preference starts a fresh conversation (the visible transcript stays) and
  says so in the chat.
- **Two settings that only work together** (ADR-163). `--tools ""` disables
  Claude Code's own file and shell tools, so every mutation has to arrive
  through the Mesh tools and run on Blender's main thread. `ENABLE_TOOL_SEARCH
  =false` in the subprocess environment stops Claude Code deferring MCP tool
  *schemas* behind its built-in `ToolSearch` — which is itself one of the
  built-ins `--tools ""` removes. Set one without the other and the model gets
  a list of tool names it cannot open; it then writes `<invoke name="…">` into
  the chat as prose, invents the reply, and changes nothing.
  `agent.py` watches the streamed text for that markup and says so.
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
| `RGN_TYPE_HEADER` | assistant + model selectors, the pinned count, the settings gear | `CADEX_CHAT_HT_header` |

The transcript draws each user and assistant message in a box with a
**copy button** (`mesh_agent.chat_copy`) — Blender's label widget cannot be
text-selected, so the clipboard is the copy path — and collapses a run of
consecutive tool-call status rows into one clickable row (`N tool calls —
last`) that expands via a session-wide WindowManager flag
(`mesh_agent.chat_toggle_tools`, ADR-182). Grouping happens before the
last-40 trim, so a long run no longer eats the visible window.

The split between the two is **status in the header, actions in the row**
(ADR-074), and since ADR-164 the row carries only what acts on the *chat*.
The header's one operator is the settings gear (`screen.userpref_show`
opened onto the AI section, ADR-182/ADR-183) — settings chrome beside the
settings it opens, not a chat action.
Two aligned groups, and the grouping is the documentation:

| Group | Buttons | What they act on |
|---|---|---|
| gather | attach image, paste image, Pin Face, Pin Point, Define Terminal | what the *next message* will carry |
| turn | New Chat, Send/Stop | the *turn* |

Rebuild Model and the viewport switches (Collision Shapes, Dimensions,
Section Cage, Section View, Exploded View, Blueprint) act on the model or
the viewport, so they live in the parameters editor's **Interface** section
(`ui._draw_interface`, ADR-164) rather than under the message box. There are
**no open-this-editor buttons anywhere** (ADR-165): the parameters editor,
the script's Text Editor and the wiring canvas are opened and arranged with
Blender's own editor dropdown and area tiling, like every other editor.

Nothing in the row is hidden when it does not apply — `Define Terminal` greys
out instead, because a row that changes width as you enter and leave Edit
Mode moves every other button under the pointer.

`RGN_TYPE_EXECUTE` is the load-bearing part. `RGN_TYPE_IS_HEADER_ANY`
(`DNA_screen_types.h`) covers `HEADER`, `TOOL_HEADER`, `FOOTER`,
`ASSET_SHELF_HEADER` and `SCRUBBING` and deliberately **not** `EXECUTE` — so
an execute region is an ordinary panel region, not subject to the
one-row limit that once forced the message box into a screen area of its own
(ADR-034). It is `RGN_ALIGN_BOTTOM` and, since ADR-164,
`RGN_FLAG_DYNAMIC_SIZE`: the region hugs the message box and its button row,
which is what keeps them at the bottom of the window instead of floating over
dead region rows. Making the box taller is the box's own grip — more visible
lines is more content, and the region follows. `cadex_chat_init()` enforces
the flags on areas loaded from saved layouts, because the app template and
older user files carry the fixed-height region they were saved with.

**Cadex Parameters**, two regions: `RGN_TYPE_WINDOW` for the sliders
(`CADEX_PARAMS_PT_parameters`) and a header — and since **ADR-108** that is
all it holds. Under the sliders and the print box sits the **Interface**
section (`ui._draw_interface`, ADR-164): Rebuild Model, then one grid of
viewport toggles, two per row — Collision Shapes, Dimensions, Section Cage,
Section View, Exploded View, Blueprint — each depressed while on, with a
settings box under the grid for each toggle that is on and has settings
(ADR-165 unified the grid; the boxes used to be freestanding).

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
There is no operator for opening any of them (ADR-165 removed
`mesh_agent.toggle_params` and its siblings): an editor is opened by
splitting an area and picking it from the editor dropdown, which is the one
tiling mechanism the whole product uses.

**No Cadex space type has DNA fields of its own** — all six are bare
`SpaceLink` headers, and a gate check asserts it. Transcript scroll is region
state, parameter values live in `scene.mesh_params`, the model selector is
an app setting (`prefs.py`, ADR-183), and the draft message is a
`WindowManager` property. DNA is
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
each registers against an editor that no longer exists — and `cycles` has since
been deleted from the tree altogether (ADR-196).

### The window chrome (ADR-166)

The window is the editors and nothing else. Both of Blender's global bars
are gone — `ED_screen_global_areas_refresh` (`screen_edit.cc`) frees them
instead of creating them, which also strips them off windows loaded from
files saved with bars — and what they carried went to where macOS keeps it:

- **File and Edit are native menus**, built in
  `intern/ghost/intern/GHOST_SystemCocoa.mm` beside the app and Window menus
  Blender already had there. Every item carries a tag in
  `representedObject`, targets nil, and lands on the app delegate's
  `cadexMenuAction:`, which pushes a `GHOST_kEventNativeMenu` (the
  `GHOST_kEventOpenMainFile` shape); the tag→operator map lives in
  `wm_window.cc`, so GHOST never learns an operator name.
  `test_native_menu_targets_exist` mirrors that map and pins that every
  target resolves. The items deliberately have **no key equivalents**:
  Blender's keymap owns the shortcuts, and a Cocoa key equivalent would
  intercept the key before the keymap sees it. "Settings…" sits in the app
  menu per the HIG, and the About/Hide/Quit literals say Cadex.
  What did not survive the move: **Open Recent** and the stock
  **Import/Export submenus** — Blender menus a static native menu cannot
  host. Recent files still work via drag-and-drop and Finder; revisit if
  missed.
- **The status bar** carried the mouse-hint icons and the Blender version;
  nothing replaces it. The product version is in the **window title**
  instead: `wm_window_title_text` appends `" - Cadex <version>"`, reading
  `Contents/Resources/cadex_version.txt`, which `build_app.sh` stamps from
  the repo-root `VERSION` file (with `CFBundleShortVersionString` and a
  commit-count `CFBundleVersion` in `Info.plist`, so the Finder and the
  About panel agree). A raw ninja build has no stamp and honestly shows
  none. `package/app/bump_version.sh` is the deliberate bump.

### The landing screen (ADR-167, ADR-168)

A fresh launch opens onto a start page drawn inside the 3D viewport — the
FreeCAD shape, not the Blender one: no modal, no popup, and the chat column
beside it is already live. It has no look of its own to maintain: colours
are the running theme's two-tone grey (read live from `wcol_regular` and
the viewport ground), text is the app's own UI font, and the corners of
the card and buttons are rounded by geometry. The header is the product
mark — the same art as the Dock icon, extracted from `cadex_icon.icns`
(ADR-059) — with the wordmark and the stamped version; the body is the
**example project card** ("EXAMPLE PROJECT" over its `card.png` render —
click it and a fresh copy lands under `~/Documents/Cadex Demo/` and opens;
the shipped demo is the MG90S biped, ADR-173, after ADR-171 removed the
drone) and three actions: **New File**
(the empty scene behind the screen *is* the new file, so this just steps
aside), **Open…**, and **Tutorial** (a stub that says so — coming later).
There is deliberately no Start Chatting button and no sentence explaining
the chat: the page's one line of help is "Esc to skip", because the chat
being open beside it is its own explanation. Every exit is one gesture: an
action, Escape, opening a real file, or simply typing in the chat — the
first message dismisses it from `Agent.start_turn`, which is the single
choke point both the Send button and the Return key pass through.

While the screen is up it owns left-clicks in the viewport (a keymap item
whose `poll` fails the moment it is dismissed — nothing is grabbed, no
modal operator runs); everything else in the window keeps working. ADR-042
stands: Blender's own splash remains disabled, and `wm_splash_screen.cc` is
untouched — this is add-on surface end to end, zero inherited-tree lines.

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
sidebar — which reads `scene.cadex_wiring` directly — listed every board.
The editor is opened from the editor dropdown's **Wiring** row like any
other (`mesh_agent.toggle_wiring` went with ADR-165), and
`get_from_context` is what makes that enough: it attaches the tree on the
first redraw, so a freshly picked Wiring editor is populated without any
setup operator. For anything scripting the space by hand, the old
operator's hard-won ordering still applies: set `area.ui_type` *before*
`space.node_tree`, because `rna_SpaceNodeEditor_node_tree_poll` rejects the
assignment otherwise.

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
lying. Viewport top-left, Cadex Chat the right **third** of the window at
full height, Cadex Parameters beside an **Outliner** under the viewport
(ADR-168); one workspace named "Simple"; an empty scene; solid shading with
the toon matcap and **cavity on**; regions and gizmos off; overlays **on but
bare** — no floor, no ortho grid, only the Z axis. All of that is space data
and saves into the file. The gate pins the area list *and* the proportions — the chat
column at about a third, parameters and outliner sharing the bottom row.

`blo_is_builtin_template` (`versioning_defaults.cc`) does not list "Mesh", so
`BLO_update_defaults_startup_blend`'s destructive pass — free every stored
panel, reset region sizes, rename screens — never runs on ours. That is
load-bearing: do not add "Mesh" to that list.

`__init__.py` does one thing, which a `.blend` cannot carry:

- **Suppresses the splash** (ADR-042) — `preferences.view.show_splash = False`,
  restoring `is_dirty` so the user's `userpref.blend` is not edited. It runs
  *in the load handler*: `creator.c` reads `USER_SPLASH_DISABLE` immediately
  after `WM_init`.

(It enabled the mesh_agent add-on too until ADR-183 made the assistant
application code that registers itself from `scripts/startup`.)

(It installed the in-window top bar too until ADR-166 moved File and Edit to
the OS menu bar and removed both window bars — see *The window chrome*
below.)

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

1. the **Cadex Engine** field in the Preferences window's AI section, if set;
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
