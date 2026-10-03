# Shell parity ledger (orun2, W1)

Verified against source: 2026-10-03, at `a375745c`, before any deletion.
`shell/` is now deleted (ADR-498); every row was written before it was, and
the tag `v1-blender-shell` holds the code each row describes.
`[Cadex-new]`

This ledger records what the Blender shell (`shell/scripts/startup/mesh_agent/`,
its 23 agent tools and its seven Cadex editors) could do, and where each piece
went. Its job is to make sure nothing is deleted unread. Every module listed here was
read in full on 2026-10-03, about 29.6k lines. The descriptions are re-derived
in our own words, because the shell is GPL and `cli/` is LGPL, and **no line
was or may be copied** (AGENTS.md, ADR-061).

The headless counterparts named below were checked against `cli/` and
`src/Mod/cadex/` at the same commit. One fact frames the whole ledger. Today's
dashboard (`cli/cadex_cli/review_server.py` + `review_static/`) **only
displays**: it opens no engine, rebuilds nothing and accepts nothing (ADR-286).
So every PORT row that steers is new dashboard work under D2.

**Status vocabulary.** The charter's three final answers are:
- **ported** — where it went, and the test that proves it;
- **already covered** — where;
- **dropped** — why, and the ADR.

This ledger also uses one interim answer, which must be resolved before
W1 is claimed:
- **to port** — with the criterion that will carry it.

Every row that said *drop (proposed)* became **dropped (ADR-498)** with the
delete commit, which is that ADR. Its reasons are the ones the rows give.

Rows marked **owner to confirm** follow the charter's question policy: when
unsure, drop and say so. No row may say **ported** without a test.

Owner's defaults (charter A1):
- **Port:** the viewer, sliders, accept/reject/restore, look/render, section,
  exploded, collision, sim/rollout playback, training curves and films,
  drawings and sheets as outputs, exports, transcript, image attach, printable
  and appearance-role display, and pick-to-comment.
- **Drop:** cage ring-drag, the wiring editor, the interactive blueprint
  editor, Blender playback baking, the landing page, top bar and chrome, and
  the Blender-side transcript store.

## 1. Modules

| module | lines | what it did | status | where / why |
|---|---|---|---|---|
| `__init__.py` | 281 | Registered the package, its save/load/frame-change handlers, keymaps and teardown order | dropped (ADR-498) | Blender registration. Nothing to port |
| `agent.py` | 819 | The chat turn inside Blender: tool pump on the main thread, one undo step per turn, cancel, provider/model switch, per-turn time/tokens/cost, a warning when the model writes a tool call as text | to port (D2.1, A1) | The turn is `cli/cadex_cli/agent.py` `ClaudeTurn` + `loop.py`. The transcript streams to the page (ADR-504). Image attachments are ported (ADR-507): `cadex -p --image`, the turn panel's **Attach image** (`cli/tests/test_prompt_images.py`, `test_dashboard_writes.py`). Still missing: per-turn cost and the text-tool-call warning. Undo is ported as revision reject/restore: `cadex revision`, the dashboard's revision buttons (ADR-506; `cli/tests/test_revisions.py`, `test_dashboard_writes.py`) |
| `backend.py` | 779 | One subprocess per turn for Claude Code, Codex or pi, normalising their event streams. Built-in tools off | dropped: Codex and pi (charter A4, ADR-497); already covered: Claude | `cli/cadex_cli/agent.py` `find_claude`, `ClaudeTurn._command`. **Open A1 check:** the shell set `ENABLE_TOOL_SEARCH=false` (ADR-163) so that MCP tools are not deferred out of reach when built-ins are off. The CLI's `_environment` sets only the output cap. It is unconfirmed whether the CLI turn is affected. A1 must decide this and record it |
| `bridge.py` | 115 | Token-guarded localhost TCP bridge that queued tool calls onto Blender's main thread | already covered | `cli/cadex_cli/bridge.py` `Bridge` |
| `cadex_animate.py` | 460 | Baked a simulation or rollout trace into Blender F-curves, plus per-frame actuator commands | ported (D2.5, ADR-511) as browser playback; the baking itself dropped (ADR-498) | `review_server.trace_playback` serves a run's rollout trace at `api/playback/run/<name>`, and the dashboard's Play button and `#play-time` slider play it through `setPoses`. The frame rules are re-derived: time-based frames (the untimed input frame dropped), quaternion sign continuity, and zero-order-hold commands. xyzw→wxyz was Blender's convention and three.js needs no conversion. Test: `cli/tests/test_dashboard_inspect.py::test_browser_plays_a_real_rollout_with_the_trace_s_placements` |
| `cadex_backend.py` | 3,262 | Shell↔engine glue: session per project, revision guard, off-main-thread modelling, slider drag preview, restore lockout and re-accept, apply-sliders-as-defaults, Save-As asset carry, link/refresh parts, blueprint store, printable export, pins, live mode | ported (D2.2, D2.4, D2.6); already covered (rest) | Covered: `cli/cadex_cli/session.py`, `bridge.py`, `client.py` `open_project`, `export.py`, and the `link` / `asset` / `script` / `params` subcommands. Ported: export as the dashboard's Export button running `cadex export` (D2.6, ADR-509, `test_dashboard_export.py`; every output, not a printable subset), sliders with rebuild (D2.2, ADR-503, `test_dashboard_writes.py`), and restore / re-accept as `cadex revision` reject/restore, which writes a stored version and its recorded values back and is re-accepted like any write (D2.4, ADR-506, `test_revisions.py`, `test_dashboard_writes.py`). Drop (proposed): drag preview (`params` rebuilds per set), apply-as-defaults (`script --set`), and Save-As carry (no `.blend`). Pins → pick-to-comment, ported at part granularity (ADR-505). Live mode → see `cadex_live.py` |
| `cadexd_client.py` | 544 | Engine child process: discovery, preflight, request/response with progress, cancel, per-op timeouts, crash report | already covered | `cli/cadex_cli/client.py` `CadexdClient`, `engine.py` `resolve_engine` |
| `cadex_blueprint.py` | 495 | Viewport "blueprint" restyle: flat fill, true BREP edges, four themes, 10 mm grid. Also the theme table for sheets | dropped (ADR-498) as a live restyle; themes to port with sheets (D2.6) | Restyling the live viewport is hands-on presentation. The rendered equivalent is `CadexStudio.line_view` / `look` |
| `cadex_cage.py` | 381 | Section-cage rings as draggable wire objects, applied back as table rows | dropped (ADR-498) | On the drop list (cage ring-drag). The data stays engine-side: `CadexCage` via `CadexInspection._script_cages` |
| `cadex_collision.py` | 546 | MuJoCo collision-shape overlay parented to components, plus a contact and interpenetration summary at t=0 | already covered (overlay); ported (ADR-508) the t=0 contact readout | Overlay: `review_server.py` `collision_proxies`, `review_scene.js` proxies, and the `review.js` show-collision toggle. The t=0 readout: `review_server.initial_contacts` and `#collision-contacts`, from the export's stored `dynamics.initial_contacts`; test `cli/tests/test_dashboard_inspect.py::test_browser_names_the_parts_touching_at_rest_and_the_agent_reads_the_same` |
| `cadex_dimension.py` | 770 | Draws declared `part.measurement` dimensions (linear, diameter, radius, angle) in screen space | to port (D2.5) | Nothing headless draws measurements; `CadexStudio.look` deliberately draws none. Re-derive the dimension geometry for the viewer or the sheets |
| `cadex_drawings.py` | 1,294 | Blueprint Editor: live draft or stored sheet, pager, Save/version, PNG export, click a cell to queue `@cell-N` | dropped (ADR-498) as an editor; to port (D2.6) stored sheets as outputs | The interactive blueprint editor is on the drop list. Showing stored sheets needs only `CadexBlueprints.read_blueprints` and `export.py` `export_blueprints`. Cell-click → a comment on the design (ADR-505); cell-level pins are not ported |
| `cadex_explode.py` | 630 | Exploded view 0–1 using the engine's staged moves (slerp per stage), with leader lines | ported (D2.5, ADR-510) | `review_server.exploded_views` turns the engine's `exploded_view` record into pose frames, and the dashboard's `#explode-amount` plays them 0–N with slerp per stage through `setPoses`, with the engine's leader lines. Test: `cli/tests/test_dashboard_inspect.py::test_browser_explodes_the_engine_stages_and_cuts_a_section` |
| `cadex_hydrate.py` | 511 | Decoded `cadex-tessellation-v1` into Blender objects with per-face and per-edge IDs, instanced components, pose-only preview | already covered (geometry); face-ID channel owner to confirm | `review_server.py` `accepted_model`, `tessellation_to_stl`, `review_scene.js` `load` / `install`. The STL route drops face IDs; part picking (ADR-505) does not need them, and only face-level pins would |
| `cadex_landing.py` | 907 | Start page: logo, demo card (copies the biped demo), New/Open/Tutorial | dropped (ADR-498) | On the drop list (landing page) |
| `cadex_live.py` | 1,260 | Live policy session: real-time step, pause/reset, push by drag or compass impulses, force arrows, policy identity, actuator bars | dropped (ADR-498), **owner to confirm** | Interactive real-time experimentation is neither playback nor modelling. Recorded rollouts and films (`film.py`) cover review. The engine API (`CadexLiveSession.py`) stays |
| `cadex_pick.py` | 317 | Eyedropper: ray-cast a face → `resolve_pin` → `@face-N`, or a point pin. Queued into the next prompt | ported at part granularity (ADR-505); face pins owner to confirm | Pick-to-comment: a click in the viewer ray-casts to a part (`review_scene.js` `pick`), and `cadex comment --part` carries the note into the next turn's prompt. Tests: `cli/tests/test_comments.py`, `test_dashboard_writes.py::test_browser_comments_on_a_picked_part_and_the_next_turn_receives_it`. Face-level `@face-N` pins are not ported: A1 asks for a part, and they would need the face-ID channel above. The engine half (`CadexPinResolution.py`, `resolve_pin`) stays |
| `cadex_presentation.py` | 296 | "Renders" panel: hero and concept sheet for the accepted revision, Render Now | already covered | `review_server.py` `presentation`; the concept-sheet block in `review.js`; `cadex render` / `render.py` |
| `cadex_print.py` | 145 | Printable-part roster with ticks stored in the scene | to port (D2.6) | Roster: `CadexPrintables.printable_roster`. The ticks lived in the `.blend`, so they need a project-store home if kept |
| `cadex_roles.py` | 176 | Painted shell / mechanism / accent appearance roles onto the viewport | to port (D2) | The rule exists: `CadexStudio.materials`, `ROLE_COLORS`. `review_scene.js` colours by index, not by role |
| `cadex_runs.py` | 388 | Read-only runs list and detail (status, revision, policy, reward, play video) | already covered | `review_record.py` `list_runs` / `read_run_record` / `read_project_review`; `ReviewProject.run` / `run_video` |
| `cadex_section.py` | 766 | Interactive section cut: axis, offset, flip, filled cut face | ported (D2.5, ADR-510); flip dropped | The dashboard's **Cut** runs `cadex section` (`section.py` `write_section`) for a plane and an optional offset, shows its SVG as the filled cut face, and clips the viewer at the same plane. Flip is dropped: the clip keeps the side below the offset, and a cut at the other side is another offset. Test: `cli/tests/test_dashboard_inspect.py::test_browser_explodes_the_engine_stages_and_cuts_a_section` |
| `cadex_sheet.py` | 2,326 | Blueprint sheet composer: views, layouts, callouts, dimensions, title block, offscreen render | dropped (ADR-498) as a composer; to port (D2.6) the stored sheets as outputs | The composer served the interactive editor (`make_blueprint`). Concept sheets come from `CadexStudio.compose`. **Owner to confirm** whether agent-drafted multi-view blueprints are wanted headlessly |
| `cadex_studio.py` | 135 | Ran `CadexStudio.py` in a subprocess; filled tool names into the guidance | already covered | `cli/cadex_cli/studio.py` `load_studio`; `agent.py` `agent_guidance` |
| `cadex_terminal_pick.py` | 1,132 | Fit a hole or pad to selected vertices → terminal, board or mount rows | dropped (ADR-498) | Hands-on wiring and modelling. The engine keeps `CadexBoards` / `CadexMounts.row_from_world` |
| `cadex_training.py` | 205 | Read live and retained training progress, 2 s poll, ETA | already covered | `review_server.py` `training_telemetry`; `review_record.py` |
| `cadex_training_plot.py` | 354 | Reward curve with a best-so-far marker | already covered | `review.js` SVG curves (reward, loss, episode length) |
| `cadex_views.py` | 195 | Ordering registry for viewport overlays | dropped (ADR-498) | Blender-specific plumbing |
| `cadex_wire_path.py` | 462 | Edit a cable route as a curve, then send its waypoints to the agent | dropped (ADR-498) | Wiring editor (drop list). The engine keeps `CadexRouting.route_path` |
| `capture.py` | 915 | Viewport screenshot, four fitted views, image loading for attachments, blueprint sheet rendering | ported (ADR-507) image attach; already covered: looking | Agent looking is `CadexStudio.look` (the bridge's `look`). Image attach is `cadex -p --image` and the dashboard's **Attach image**: the bytes are checked by signature and sent as image blocks in the turn's message (`cli/tests/test_prompt_images.py`, `test_dashboard_writes.py::test_browser_attaches_an_image_to_a_turn_and_the_turn_receives_it`) |
| `harness.py` | 256 | Account and model discovery per harness; sign-in | dropped | Charter A4, ADR-497: Claude Code is the only harness. The CLI takes `--model` / `CADEX_MODEL` |
| `history.py` | 116 | Transcript and session id stored in a `.blend` text block | dropped (ADR-498); the transcript itself to port (D2.1) | On the drop list (Blender-side transcript store). The session id is already in `session.py` `agent.json`. The dashboard needs a transcript from the project directory |
| `mcp_shim.py` | 139 | MCP stdio server forwarding to the bridge | already covered | `cli/cadex_cli/mcp.py` |
| `mock_backend.py` | 112 | Scripted fake backend for the shell suites | dropped (ADR-498) | Test harness for deleted code |
| `model.py` | 589 | Script mirror into a text block; parameter specs → live sliders; debounced rebuild; rewrite `num()` defaults | to port (D2.2) sliders; dropped (ADR-498) the text-block mirror and default rewriting | Sliders are on the port list. `./cadex script` prints and replaces the script |
| `model_api.py` | 41 | Clamped a parameter value to its type and range | to port (D2.2) | The dashboard slider must clamp to the spec. The engine also refuses out-of-range values |
| `modes.py` | 99 | The Cadex prompt overlay and `system_prompt()` | to port (A1) | `cli/cadex_cli/agent.py` `CLI_OVERLAY` + `CadexAgentGuidance.md` cover most of it. §4 lists what is only here |
| `prefs.py` | 536 | AI settings (harness, model, CLI paths, engine override, timeout and memory budgets), account popover | dropped (ADR-498) | Harness and account UI goes with A4. The engine override is `--engine` / `CADEX_ENGINE_ROOT`. **Owner to confirm:** per-project timeout and memory budgets have no CLI flag |
| `spaces.py` | 235 | Editor headers; the "Model Script" panel (Apply/Revert/Rebuild) | dropped (ADR-498) | Chrome. The script panel is covered by `./cadex script` |
| `tools.py` | 1,961 | The 23 agent tools (§2) | per tool, §2 | The product agent's tools are `cli/cadex_cli/tools.py` |
| `topbar.py` | 337 | Import Geometry, Link Part, Refresh Linked Parts, Export Printable Parts | already covered (import, link); ported (D2.6, ADR-509) export | `./cadex asset`, `./cadex link`. Export: the dashboard's Export button runs `cadex export` (`export.py` `export_outputs`) and offers the STEP and STL for download; test `cli/tests/test_dashboard_export.py::test_browser_exports_step_and_stl_and_downloads_the_concept_sheet`. It writes every output, which includes the printable ones; the printable-only filter is dropped (ADR-509), and the engine's `export_printable` op stays on the cadexd protocol |
| `ui.py` | 1,593 | Panels and operators for Chat, Params, Env, Policy and Training | to port (D2.1–D2.5); already covered (training panel); dropped (ADR-498) (cage/terminal/wire buttons, chrome) | Transcript, image attach, sliders, rebuild/re-accept, the section/explode/collision toggles, sim playback, actuator bars |
| `wiring.py` | 1,135 | Wiring node tree, Apply to nets/boards | dropped (ADR-498) | Wiring editor (drop list). The engine keeps `CadexNets` and `CadexBoards` |
| `wiring_ui.py` | 482 | Wiring editor header, panels and operators | dropped (ADR-498) | Wiring editor (drop list) |
| `pi_tools.js` | 91 | pi extension registering the bridge tools | dropped | Charter A4, ADR-497 |
| `landing_logo.png` | LFS | Landing-page logo | dropped (ADR-498) | Goes with `cadex_landing.py` |
| `demo/` (`biped.blend`, `card.png`, `biped.cadex/`) | — | The landing page's demo project (MG90S biped: script, history, one `.cxpolicy`) | dropped (ADR-498), **owner to confirm** | The `.blend` and card go with the landing page. The `biped.cadex` project could be kept as a sample fixture, but a policy binary may not be committed outside it (charter) |

## 2. The 23 agent tools

The product agent's surface is `cli/cadex_cli/tools.py`: `CLI_TOOL_OPS` +
`BRIDGE_TOOLS`, pinned by `test_project_tool_surface.py`. It has five
tools the shell never had: `train_start`, `train_status`, `train_stop`,
`evaluate`, and `leave_note`, the agent's non-blocking channel to the
owner (ADR-512, charter A1; `cli/tests/test_owner_channel.py`,
`test_dashboard_writes.py::test_browser_shows_the_agents_question_and_the_answer_reaches_the_next_turn`).

| shell tool | what it did | status | where / why |
|---|---|---|---|
| `get_script` | Script (optional line window), param values, revision | already covered | `inspect` scope `script` (no line window) |
| `write_script` | Replace the script, rebuild, add fit and inventory | already covered | `write_script` |
| `set_params` | Set values, rebuild | already covered | `set_params` |
| `edit_script` | Exact find-and-replace | already covered | `edit_script` |
| `restore_version` | Write a stored version back and rebuild | ported (D2.4); already covered (agent) | For the owner: `cadex revision restore SELECTOR` and the dashboard's **Restore** (ADR-506; `cli/tests/test_revisions.py`, `test_dashboard_writes.py`), which also put back the version's recorded values. For the agent: `inspect` `history` then `write_script`, as ADR-045 designed; no new tool |
| `rebuild_model` | Re-run the stored script | already covered | `rebuild` |
| `inspect_model` | Engine inspect, 9 scopes | already covered | `inspect` (adds the `wiring` and `api` scopes) |
| `describe_cad_api` | API overview / domain / functions | already covered | `describe_api` (`bridge.py` `api_view`) |
| `get_attached_image` | Return a chat-attached image | already covered (ADR-507) | No tool: the attached image is already in the turn's own user message as an image block, so the model sees it without a call. The tool surface is unchanged (`cli/tests/test_prompt_images.py`) |
| `scene_summary` | Engine summary plus what the viewport shows | already covered | `inspect` scopes. There is no viewport to describe |
| `viewport_screenshot` | PNG of the user's viewport | dropped (ADR-498) | There is no user viewport. `look` renders the accepted design |
| `look` | Studio render plus design-language measures | already covered | `look` (`BRIDGE_TOOLS`, `bridge.py` `_look`) |
| `render_views` | Four-camera silhouette composite | already covered | `look` with views; `./cadex render` |
| `collision_view` | Toggle the collision overlay, report t=0 contacts | ported (ADR-508): the viewer toggle and readout, and the agent half as `inspect scope=contacts` (owner note, 2026-10-03: kept) | Viewer: the show-collision toggle and `#collision-contacts`. Agent: `CadexInspection._complete_contacts`, offered in `INSPECT_SCOPES`; tests `src/Mod/cadex/cadex_tests/test_contacts_scope.py`, `test_project_tool_surface.py`, and the browser test above, which asserts the agent's scope and the page agree |
| `section_view` | Viewport section cut | already covered (rendered); ported (D2.5, ADR-510) (dashboard) | `./cadex section` / `section.py` `write_section`; the dashboard's Cut runs it and clips the viewer (`test_dashboard_inspect.py`). There is no agent tool |
| `exploded_view` | Play the explosion 0–1 | ported (D2.5, ADR-510) (dashboard) | `review_server.exploded_views` reads the engine's record, and the dashboard's explode slider plays it (`test_dashboard_inspect.py`). There is no agent tool |
| `blueprint_view` | Restyle the viewport as a blueprint | dropped (ADR-498) | A live restyle has no viewport to restyle |
| `make_blueprint` | Render a multi-cell blueprint draft | dropped (ADR-498), **owner to confirm** | Goes with the interactive blueprint editor. Concept sheets cover the rendered output |
| `save_blueprint` | Store the draft, versioned | dropped (ADR-498), **owner to confirm** | As above. Stored sheets stay readable (`export_blueprints`) |
| `export_stl` | Write the viewport meshes to STL | already covered | `./cadex export` (STEP/STL/BREP from exact solids) |
| `import_geometry` | Copy STL/OBJ/PLY into project assets | already covered | `put_asset` |
| `link_part` | Link a solid from another project | already covered | `link_part` |
| `focus_view` | Frame objects in the viewport | already covered | `look` `focus` |

## 3. The seven Cadex editors

Each editor's C++ under `shell/source/blender/editors/space_cadex_*` is a bare
space with one header and one panel region. Everything it showed was drawn by
`mesh_agent`.

| editor | what it showed | status | where / why |
|---|---|---|---|
| Chat (`space_cadex_chat`) | Transcript, message box, image attach, provider, model and account header | ported (ADR-504, ADR-507); dropped (ADR-498) the harness header | `#turn-panel`: prompt, live transcript (ADR-504) and **Attach image** (ADR-507), `cli/tests/test_dashboard_writes.py` |
| Parameters (`space_cadex_params`) | Sliders, apply-as-defaults, rebuild/re-accept, printable ticks, view toggles | ported (D2.2, D2.4); to port (D2.5, D2.6) | Sliders run `cadex params` (ADR-503); accept, reject and restore run `cadex revision` (ADR-506); both browser-tested in `test_dashboard_writes.py` |
| Environment (`space_cadex_env`) | Collision counts, contacts at t=0, interpenetration | already covered (proxies); ported (ADR-508) (contact readout) | `review_server.py` `collision_proxies` and `initial_contacts`; `#collision-contacts` |
| Policy (`space_cadex_policy`) | Simulation play/pause/frame; per-actuator command bars | ported (D2.5, ADR-511); bars dropped | Play, pause and scrub a run's rollout in simulation seconds. Each actuator's command in force is shown as a number against its range in `#play-note`, not as a bar (ADR-511). Test: `test_dashboard_inspect.py::test_browser_plays_a_real_rollout_with_the_trace_s_placements` |
| Training (`space_cadex_training`) | Training state, runs, renders, reward curve | already covered | `review_server.py` `training_telemetry`, runs, presentation; `review.js` curves |
| Live (`space_cadex_live`) | Live policy session, push, actuator bars | dropped (ADR-498), **owner to confirm** | See `cadex_live.py` |
| Blueprint (`space_cadex_blueprint`) | Draft or stored sheet, pager, save, export, cell pin | dropped (ADR-498) as an editor; to port (D2.6) stored sheets as outputs | The interactive blueprint editor is on the drop list |

## 4. Agent guidance that lived only in the shell (A1 input)

These points were in the shell's `agent.py` `SYSTEM_PROMPT` or its `modes.py`
overlay, and are absent from both `cli/cadex_cli/agent.py` `CLI_OVERLAY` and
`CadexAgentGuidance.md`. A1 decides each one, re-derived in new words:

- the script must be deterministic and self-contained;
- derive secondary dimensions from primary ones;
- +Z is up;
- give outputs short, meaningful names;
- face pins (`@face-N of <output>`) and drawing cells (`@cell-N`) are ground
  truth. This becomes live again with pick-to-comment;
- rebuilds take 0.5 s to several s, so batch value changes;
- after `assembly.mjcf`, check the collision shapes and the t=0 contact
  line;
- measured terminals: a fitted row is copied, not re-derived. This goes with
  the terminal picker;
- the board/net declaration walkthrough. The CLI has it only in tool
  descriptions.

Tool-gating rules that do not carry over:
- the undo step per turn (replaced by revisions);
- Codex and pi sandboxing (A4, ADR-497);
- held-back slider drags while a turn runs. The dashboard's write paths
  must serialise against a running turn (charter A3) — D2 must keep this.
