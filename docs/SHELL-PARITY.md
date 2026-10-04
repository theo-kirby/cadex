# Shell parity ledger (orun2, W1)

Verified against source: 2026-10-04. Rows first written 2026-10-03 at
`a375745c`, before any deletion; audited row by row on 2026-10-04 (§5);
repointed after ADR-537 and ADR-538 the same day.
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
`src/Mod/cadex/` at the same commit. One fact framed the ledger then. The
dashboard of that commit (`cli/cadex_cli/review_server.py` + `review_static/`)
**only displayed**: it opened no engine, rebuilt nothing and accepted nothing
(ADR-286). So every PORT row that steered was new dashboard work under D2.
D2 built those writes (ADR-503 to ADR-511), and ADR-537 took them out again:
the dashboard is read-only once more, and steering is the agent's.

**2026-10-04, after the merge: the page was cut to the minimum (ADR-533).**
The owner had the dashboard reduced to the model, a design turn, the
parameter sliders and the revisions. The page no longer shows the comments
and part pick, the agent's notes, export, drawings, the collision toggle and
contact readout, the dimension overlay, the explode slider, the section cut,
rollout playback, the parts' roles and print roster, image attach, or the
`look` images, so rows below that name one of those as the dashboard's are
now **headless only**. Nothing they describe was lost then. Each server route
still answered and each CLI command (`cadex comment`, `cadex export`,
`cadex section`, `cadex -p --image`, `inspect scope=contacts`,
`draw_blueprint`) still worked with its tests, and the agent's tools were
unchanged. ADR-538 later deleted `cadex comment` and `cadex -p` (below). The browser tests that drove those panels were removed with
them. A panel added back is page work only.

**2026-10-04, later: the dashboard is read-only, and Cadex has no agent of
its own (ADR-534, ADR-537, ADR-538, ADR-539).** ADR-534 brought back the
read-only views: a run's model with its rollout playback in the 3D viewport,
and the drawing sheets, presentation images, project documents and training
curves in the 2D viewport. ADR-537 then removed every write from the page:
the Chat editor (the design turn), the parameter sliders, Accept, Reject and
Restore. The revision trail stays in the Revisions menu, read-only (ADR-539).
ADR-538 removed Cadex's own model loop: `cadex -p` and its `--image`,
`--model` and `--resume`, `agent.py` (`ClaudeTurn`, `CLI_OVERLAY`, turn
usage and the imitated-tool-call warning), the turn store, the owner
channel (`cadex comment`, `leave_note`, the notes) and `cadex revision
accept`. The person brings their own agent, which drives the engine through
`cadex mcp` and the `cadex` commands, and is told what it needs by
`cli/cadex_cli/guidance.py` (`cadex guidance`). So a row below that says
**ported** to the dashboard's chat, sliders, revision buttons, comments,
image attach or `cadex -p` now reads **ported, then removed (ADR-537 or
ADR-538)**. What steered moved to the person's agent, through the tools and
the CLI (`cadex params`, `cadex revision reject|restore`, `cadex section`,
`cadex export`). The rows below are corrected to say so, and the tests they
cite are the ones in the tree today.

**Status vocabulary.** The charter's three final answers are:
- **ported** — where it went, and the test that proves it;
- **already covered** — where;
- **dropped** — why, and the ADR.

This ledger also uses one interim answer, which must be resolved before
W1 is claimed:
- **to port** — with the criterion that will carry it.

Every row that said *drop (proposed)* became **dropped (ADR-498)** with the
delete commit, which is that ADR. Its reasons are the ones the rows give.

Rows still marked **owner to confirm** follow the charter's question policy: when
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
| `agent.py` | 819 | The chat turn inside Blender: tool pump on the main thread, one undo step per turn, cancel, provider/model switch, per-turn time/tokens/cost, a warning when the model writes a tool call as text | ported (ADR-504, ADR-506, ADR-507, ADR-523), then removed (ADR-537, ADR-538); undo already covered | The turn was `cli/cadex_cli/agent.py` `ClaudeTurn` with the dashboard's Chat, image attach (`cadex -p --image`), per-turn usage and the text-tool-call warning. ADR-538 deleted all of it: Cadex runs no model loop, and the person's own agent (Claude Code, Codex, Pi) is the turn, driving the engine through `cadex mcp` (`cli/cadex_cli/mcp.py`, `__main__.py` `McpSession`; `cli/tests/test_mcp_protocol.py`). Its usage, model choice and attachments are that agent's. Undo is revision reject/restore: `cadex revision` (ADR-506; `cli/tests/test_revisions.py`); the dashboard's buttons for it went with ADR-537 |
| `backend.py` | 779 | One subprocess per turn for Claude Code, Codex or pi, normalising their event streams. Built-in tools off | dropped (ADR-497 for Codex and pi; ADR-538 for Claude) | ADR-497 kept Claude Code as the one harness the CLI spawned (`agent.py` `find_claude`, `ClaudeTurn._command`). ADR-538 removed that too: Cadex spawns no agent CLI (`cli/tests/test_project_docs.py::test_cadex_has_no_agent_harness_of_its_own`). Any MCP client, Codex and Pi included again, registers `cadex mcp`. Nothing to port |
| `bridge.py` | 115 | Token-guarded localhost TCP bridge that queued tool calls onto Blender's main thread | already covered | `cli/cadex_cli/bridge.py` `Bridge`, called in process by `cadex mcp` since ADR-538 (no socket or token) |
| `cadex_animate.py` | 460 | Baked a simulation or rollout trace into Blender F-curves, plus per-frame actuator commands | ported (D2.5, ADR-511) as browser playback; the baking itself dropped (ADR-498) | `review_server.trace_playback` serves a run's rollout trace at `api/playback/run/<name>`, and the 3D viewport's Play button and `#play-time` slider play it through `setPoses` when a run is the shown model (ADR-534). The frame rules are re-derived: time-based frames (the untimed input frame dropped), quaternion sign continuity, and zero-order-hold commands. xyzw→wxyz was Blender's convention and three.js needs no conversion. Test: `cli/tests/test_dashboard_inspect.py::test_playback_is_timed_frames_with_a_continuous_quaternion_sign` |
| `cadex_backend.py` | 3,262 | Shell↔engine glue: session per project, revision guard, off-main-thread modelling, slider drag preview, restore lockout and re-accept, apply-sliders-as-defaults, Save-As asset carry, link/refresh parts, blueprint store, printable export, pins, live mode | already covered (headless); the dashboard ports (D2.2, D2.4, D2.6) removed (ADR-537) | Covered: `cli/cadex_cli/session.py`, `bridge.py`, `client.py` `open_project`, `export.py`, and the `link` / `asset` / `script` / `params` / `export` / `revision` subcommands (`cli/tests/test_export.py`, `test_revisions.py`). The dashboard's Export button (ADR-509), sliders (ADR-503) and restore / re-accept buttons (ADR-506) were built and then removed by ADR-537; the agent or the person runs `cadex export`, `cadex params --set` and `cadex revision reject|restore`. Dropped (ADR-498): drag preview (`params` rebuilds per set), apply-as-defaults (`script --set`), and Save-As carry (no Blender file). Pins → pick-to-comment, which went with ADR-538 (see `cadex_pick.py`). Live mode → see `cadex_live.py` |
| `cadexd_client.py` | 544 | Engine child process: discovery, preflight, request/response with progress, cancel, per-op timeouts, crash report | already covered | `cli/cadex_cli/client.py` `CadexdClient`, `engine.py` `resolve_engine` |
| `cadex_blueprint.py` | 495 | Viewport "blueprint" restyle: flat fill, true BREP edges, four themes, 10 mm grid. Also the theme table for sheets | dropped (ADR-498) as a live restyle; themes dropped (ADR-516) | Restyling the live viewport is hands-on presentation. The rendered equivalent is `CadexStudio.line_view` / `look`. Sheets keep one theme, the dashboard's dark floor (`docs/DASHBOARD.md` §4), so a sheet sits in the page as the concept sheet does; four themes were a viewport choice (ADR-516) |
| `cadex_cage.py` | 381 | Section-cage rings as draggable wire objects, applied back as table rows | dropped (ADR-498) | On the drop list (cage ring-drag). The data stays engine-side: `CadexCage` via `CadexInspection._script_cages` |
| `cadex_collision.py` | 546 | MuJoCo collision-shape overlay parented to components, plus a contact and interpenetration summary at t=0 | already covered (headless); the viewer toggle and readout ported (ADR-508), then removed from the page (ADR-533) | The server still computes both into the model manifest: `review_server.py` `collision_proxies` and `initial_contacts`, from the export's stored `dynamics.initial_contacts`, and `review_scene.js` can still draw proxies; the page has no toggle or readout. The agent reads the same contacts with `inspect scope=contacts`. Tests: `cli/tests/test_dashboard_inspect.py::test_initial_contacts_groups_by_pair_and_says_why_when_absent`, `::test_the_agent_reads_the_parts_touching_at_rest_that_the_server_serves`, `test_review_server.py::test_collision_proxies_come_from_the_retained_mjcf_at_the_same_identity` |
| `cadex_dimension.py` | 770 | Draws declared `part.measurement` dimensions (linear, diameter, radius, angle) in screen space | ported (ADR-516) on drawing sheets; the viewer overlay ported (D2.5, ADR-524), then removed from the page (ADR-533) | `CadexStudio.blueprint_sheet` draws each declared `part.measurement` (linear, diameter, radius, angle) once, on the view where it reads, re-derived (`cli/tests/test_blueprint.py::test_declared_measurements_are_drawn_once_where_they_read`). The viewer overlay's `dimensions.js` was deleted by ADR-533; `review_server.declared_measurements` still puts the records in the model manifest, the engine's anchors on the component that shows the measured output (`cli/tests/test_dashboard_dimensions.py`). `CadexStudio.look` deliberately draws none |
| `cadex_drawings.py` | 1,294 | Blueprint Editor: live draft or stored sheet, pager, Save/version, PNG export, click a cell to queue `@cell-N` | dropped (ADR-498) as an editor; ported (ADR-516, ADR-534) stored sheets as outputs | The interactive editor is on the drop list. Stored sheets are outputs: the 2D viewport lists every version newest first under Drawings and shows the one picked (`review_server.blueprint_listing`). Test: `test_blueprint.py::test_the_dashboard_lists_stored_sheets_newest_first_and_serves_only_those`. Cell-click → a comment on the design (ADR-505) went with the owner channel (ADR-538); cell-level pins are not ported |
| `cadex_explode.py` | 630 | Exploded view 0–1 using the engine's staged moves (slerp per stage), with leader lines | ported (D2.5, ADR-510), then removed from the page (ADR-533); headless only | `review_server.exploded_views` still turns the engine's `exploded_view` record into pose frames in the model manifest, and `review_scene.js` keeps its leader lines, but the page has no explode control. Test: `cli/tests/test_dashboard_inspect.py::test_exploded_frames_are_cumulative_from_the_assembled_pose` |
| `cadex_hydrate.py` | 511 | Decoded `cadex-tessellation-v1` into Blender objects with per-face and per-edge IDs, instanced components, pose-only preview | already covered (geometry); face-ID channel owner to confirm | `review_server.py` `accepted_model`, `tessellation_to_stl`, `review_scene.js` `load` / `install`. The STL route drops face IDs, which only face-level pins would need |
| `cadex_landing.py` | 907 | Start page: logo, demo card (copies the biped demo), New/Open/Tutorial | dropped (ADR-498) | On the drop list (landing page) |
| `cadex_live.py` | 1,260 | Live policy session: real-time step, pause/reset, push by drag or compass impulses, force arrows, policy identity, actuator bars | dropped (ADR-498); owner confirmed (owner notes, 2026-10-03) | Interactive real-time experimentation is neither playback nor modelling. Reviewing a policy is rollout playback plus `evaluate`'s disturbance tests. Recorded rollouts and films (`film.py`) cover review. Its engine half — the `live_open`/`live_step`/`live_close` ops, `CadexLiveSession.py` and `cadex_live_worker.py` — is retired too (ADR-528) |
| `cadex_pick.py` | 317 | Eyedropper: ray-cast a face → `resolve_pin` → `@face-N`, or a point pin. Queued into the next prompt | ported at part granularity (ADR-505), then removed (ADR-533, ADR-538) | Pick-to-comment was a viewer click to a part plus `cadex comment --part` into the next turn's prompt. ADR-533 took the pick off the page and ADR-538 deleted `cadex comment` and the turn it fed: the person tells their own agent, naming the part by its output. Face-level `@face-N` pins were never ported. The engine half (`CadexPinResolution.py`, `resolve_pin`) stays |
| `cadex_presentation.py` | 296 | "Renders" panel: hero and concept sheet for the accepted revision, Render Now | already covered | `review_server.py` `presentation`, shown under Images in the 2D viewport (ADR-534); `cadex render` / `render.py` |
| `cadex_print.py` | 145 | Printable-part roster with ticks stored in the scene | ported (ADR-522) the roster display, then removed from the page (ADR-533); dropped (ADR-522) the ticks | The roster is `CadexPrintables.printable_roster`, the list `export_printable` checks, read by the agent through `inspect scope=inventory`; the dashboard's parts list that showed it was cut by ADR-533. The ticks only chose what a printable-only export wrote; that filter is dropped (ADR-509), so they have nothing to feed |
| `cadex_roles.py` | 176 | Painted shell / mechanism / accent appearance roles onto the viewport | ported (ADR-522) | The viewer paints each part by `CadexStudio.materials`, the rule `look` and the concept sheet use: declared role, else mechanism if purchased and shell if printed, in the assembly palette (`review_server.part_looks`, `review_scene.js`). Tests: `cli/tests/test_dashboard_parts.py::test_the_roles_are_the_ones_the_agent_reads_from_the_inventory` (agrees with `inspect scope=inventory`), `::test_no_assembly_keeps_index_colours_and_a_bad_role_says_why` |
| `cadex_runs.py` | 388 | Read-only runs list and detail (status, revision, policy, reward, play video) | already covered | `review_record.py` `list_runs` / `read_run_record` / `read_project_review`; `ReviewProject.run` / `run_video` |
| `cadex_section.py` | 766 | Interactive section cut: axis, offset, flip, filled cut face | ported (D2.5, ADR-510) as the dashboard's Cut, then removed (ADR-533, ADR-537); headless: already covered | `cadex section` (`section.py` `write_section`) cuts a plane at an optional offset and writes the filled cut face as SVG; the server still lists and serves the cuts it left (`review_server.section_listing`). The page has no Cut control and runs nothing. Flip is dropped: a cut at the other side is another offset. Tests: `cli/tests/test_section.py`, `test_dashboard_inspect.py::test_the_cuts_cadex_section_wrote_are_listed_and_served` |
| `cadex_sheet.py` | 2,326 | Blueprint sheet composer: views, layouts, callouts, dimensions, title block, offscreen render | ported (ADR-516), re-derived headlessly | Owner kept the composer as a headless tool (owner notes, 2026-10-03). `CadexStudio.blueprint_sheet` / `blueprint_report`: up to four line views on one shared scale (third-angle default), overall extents on each orthographic view, declared `part.measurement` records drawn once where they read, numbered callouts keyed in a parts list, notes, and a title block; the agent's `draw_blueprint` stores it through `put_blueprint`, versioned by name, recipe in `meta`. Not ported: per-cell explode/section/hide overrides, custom azimuths, the params and text panels as cells, weighted per-cell aspect and layout templates beyond 1, 2 and 2x2 (one sheet per question; notes cover the text panel). Read from `v1-blender-shell` as reference; nothing copied. Tests: `cli/tests/test_blueprint.py` (composer, refusals, measurements, callouts, bridge store and revise, and the dashboard's listing) |
| `cadex_studio.py` | 135 | Ran `CadexStudio.py` in a subprocess; filled tool names into the guidance | already covered | `cli/cadex_cli/studio.py` `load_studio`; `guidance.py` `agent_guidance` |
| `cadex_terminal_pick.py` | 1,132 | Fit a hole or pad to selected vertices → terminal, board or mount rows | dropped (ADR-498) | Hands-on wiring and modelling. The engine keeps `CadexBoards` / `CadexMounts.row_from_world` |
| `cadex_training.py` | 205 | Read live and retained training progress, 2 s poll, ETA | already covered | `review_server.py` `training_telemetry`; `review_record.py` |
| `cadex_training_plot.py` | 354 | Reward curve with a best-so-far marker | already covered | The 2D viewport's Plots (`review.js`): reward, loss and episode length per run (ADR-534) |
| `cadex_views.py` | 195 | Ordering registry for viewport overlays | dropped (ADR-498) | Blender-specific plumbing |
| `cadex_wire_path.py` | 462 | Edit a cable route as a curve, then send its waypoints to the agent | dropped (ADR-498) | Wiring editor (drop list). The engine keeps `CadexRouting.route_path` |
| `capture.py` | 915 | Viewport screenshot, four fitted views, image loading for attachments, blueprint sheet rendering | ported (ADR-516) sheet rendering; already covered: looking; image attach ported (ADR-507), then removed (ADR-537, ADR-538) | Agent looking is `CadexStudio.look` (the bridge's `look`). Sheet rendering is `CadexStudio.blueprint_sheet` (see `cadex_sheet.py`; `cli/tests/test_blueprint.py`). Image attach was `cadex -p --image` and the dashboard's **Attach image**; both are gone, and an image now reaches the person's own agent however that agent takes one |
| `harness.py` | 256 | Account and model discovery per harness; sign-in | dropped (ADR-497, ADR-538) | Cadex has no harness: the account, sign-in and model are the person's own agent's (ADR-538). `--model` / `CADEX_MODEL` went with `cadex -p` |
| `history.py` | 116 | Transcript and session id stored in a Blender text block | dropped (ADR-498) the store; the live transcript ported (ADR-504), then removed (ADR-537, ADR-538) | On the drop list (Blender-side transcript store). The dashboard's live turn transcript and `agent.json`'s session id went with Cadex's own agent (ADR-538); the transcript is the person's agent's. The project keeps what the CLI keeps: the `PROGRESS.md` row and commit that `cadex mcp` lands as a session closes, and the `DECISIONS.md` and docs the agent writes |
| `mcp_shim.py` | 139 | MCP stdio server forwarding to the bridge | already covered | `cli/cadex_cli/mcp.py`, the wire of `cadex mcp --project DIR`, a standalone server any MCP client registers (ADR-538; `cli/tests/test_mcp_protocol.py`) |
| `mock_backend.py` | 112 | Scripted fake backend for the shell suites | dropped (ADR-498) | Test harness for deleted code |
| `model.py` | 589 | Script mirror into a text block; parameter specs → live sliders; debounced rebuild; rewrite `num()` defaults | sliders ported (ADR-503), then removed (ADR-537); dropped (ADR-498) the text-block mirror and default rewriting | Each parameter is set by `cadex params --set k=v` or the agent's `set_params`, one rebuild per set; the page's sliders that ran it are gone. `./cadex script` prints and replaces the script |
| `model_api.py` | 41 | Clamped a parameter value to its type and range | ported (ADR-503), then removed with the sliders (ADR-537) | The slider's range input held the spec's `min`, `max` and `step`. With the sliders gone, a value is set through `set_params` or `cadex params`; `num()` itself checks that a default lies within `[min, max]` (`cadex_project_api.py`) |
| `modes.py` | 99 | The Cadex prompt overlay and `system_prompt()` | ported (ADR-521); rewritten (ADR-538) | `cli/cadex_cli/guidance.py` `OVERLAY` + `CadexAgentGuidance.md`, printed by `cadex guidance` and briefed as `cadex mcp`'s instructions; it was `agent.py` `CLI_OVERLAY` until ADR-538. The points that were only here are re-derived or dropped point by point in §4. Tests: `cli/tests/test_agent_guidance.py`, `src/Mod/cadex/cadex_tests/test_agent_guidance.py::test_the_guidance_checks_the_rest_contacts_after_an_mjcf_export` |
| `prefs.py` | 536 | AI settings (harness, model, CLI paths, engine override, timeout and memory budgets), account popover | dropped (ADR-498); the engine budgets ported to the project (ADR-517) | Harness and account UI goes with A4 and ADR-538. The engine override is `--engine` / `CADEX_ENGINE_ROOT`. The owner moved the timeout and memory budgets to the project (owner notes, 2026-10-03): stored in `agent.json` by `cadex budgets --set`, overridden per call by `--engine-timeout` / `--engine-memory`, sent as `open_project`'s `budgets`. The dashboard's Identity panel that showed them was cut by ADR-533. Test: `cli/tests/test_project_budgets.py` |
| `spaces.py` | 235 | Editor headers; the "Model Script" panel (Apply/Revert/Rebuild) | dropped (ADR-498) | Chrome. The script panel is covered by `./cadex script` |
| `tools.py` | 1,961 | The 23 agent tools (§2) | per tool, §2 | The product agent's tools are `cli/cadex_cli/tools.py` |
| `topbar.py` | 337 | Import Geometry, Link Part, Refresh Linked Parts, Export Printable Parts | already covered | `./cadex asset`, `./cadex link`, `./cadex export` (`export.py` `export_outputs`; `cli/tests/test_export.py`). The dashboard's Export button (D2.6, ADR-509) was removed by ADR-537. Export writes every output, which includes the printable ones; the printable-only filter is dropped (ADR-509), and the engine's `export_printable` op stays on the cadexd protocol |
| `ui.py` | 1,593 | Panels and operators for Chat, Params, Env, Policy and Training | mostly ported (ADR-503–ADR-511), then removed (ADR-533, ADR-537); kept: playback and training; dropped (ADR-498) cage/terminal/wire buttons and chrome, (ADR-511) actuator bars | What stays on the page: sim playback (ADR-511) in the 3D viewport and training curves in the 2D viewport. Gone from it: the transcript and image attach (ADR-537, ADR-538), sliders and rebuild/re-accept (ADR-537), the collision readout, section and explode (ADR-533). Each survives headless as the rows above say |
| `wiring.py` | 1,135 | Wiring node tree, Apply to nets/boards | dropped (ADR-498) | Wiring editor (drop list). The engine keeps `CadexNets` and `CadexBoards` |
| `wiring_ui.py` | 482 | Wiring editor header, panels and operators | dropped (ADR-498) | Wiring editor (drop list) |
| `pi_tools.js` | 91 | pi extension registering the bridge tools | dropped | Charter A4, ADR-497 |
| `landing_logo.png` | LFS | Landing-page logo | dropped (ADR-498) | Goes with `cadex_landing.py` |
| `demo/` (`biped.blend`, `card.png`, `biped.cadex/`) | — | The landing page's demo project (MG90S biped: script, history, one `.cxpolicy`) | dropped (ADR-498); owner confirmed (owner notes, 2026-10-03) | The `.blend` and card go with the landing page, and the owner restored nothing of the demo biped |

## 2. The 23 agent tools

The product agent's surface is `cli/cadex_cli/tools.py`: `CLI_TOOL_OPS` +
`BRIDGE_TOOLS`, served by `cadex mcp` and pinned by
`test_project_tool_surface.py`. It has four tools the shell never had:
`train_start`, `train_status`, `train_stop` and `evaluate`. A fifth,
`leave_note`, the agent's non-blocking channel to the owner (ADR-512), was
removed by ADR-538: the person talks to their own agent directly.

| shell tool | what it did | status | where / why |
|---|---|---|---|
| `get_script` | Script (optional line window), param values, revision | already covered | `inspect` scope `script` (no line window) |
| `write_script` | Replace the script, rebuild, add fit and inventory | already covered | `write_script` |
| `set_params` | Set values, rebuild | already covered | `set_params` |
| `edit_script` | Exact find-and-replace | already covered | `edit_script` |
| `restore_version` | Write a stored version back and rebuild | already covered | For the person: `cadex revision restore SELECTOR` (ADR-506; `cli/tests/test_revisions.py`), which also puts back the version's recorded values; the dashboard's **Restore** that ran it was removed by ADR-537. For the agent: `inspect` `history` then `write_script`, as ADR-045 designed, or the same CLI command; no new tool |
| `rebuild_model` | Re-run the stored script | already covered | `rebuild` |
| `inspect_model` | Engine inspect, 9 scopes | already covered | `inspect` (adds the `wiring` and `api` scopes) |
| `describe_cad_api` | API overview / domain / functions | already covered | `describe_api` (`bridge.py` `api_view`) |
| `get_attached_image` | Return a chat-attached image | dropped (ADR-538) | Image attach (ADR-507) went with `cadex -p` and the dashboard's Chat. An image reaches the person's own agent through that agent; the tool surface never had this tool |
| `scene_summary` | Engine summary plus what the viewport shows | already covered | `inspect` scopes. There is no viewport to describe |
| `viewport_screenshot` | PNG of the user's viewport | dropped (ADR-498) | There is no user viewport. `look` renders the accepted design |
| `look` | Studio render plus design-language measures | already covered | `look` (`BRIDGE_TOOLS`, `bridge.py` `_look`) |
| `render_views` | Four-camera silhouette composite | already covered | `look` with views; `./cadex render` |
| `collision_view` | Toggle the collision overlay, report t=0 contacts | ported (ADR-508): the agent half as `inspect scope=contacts` (owner note, 2026-10-03: kept); the viewer toggle and readout removed from the page (ADR-533) | Agent: `CadexInspection._complete_contacts`, offered in `INSPECT_SCOPES`; tests `src/Mod/cadex/cadex_tests/test_contacts_scope.py`, `test_project_tool_surface.py`, and `cli/tests/test_dashboard_inspect.py::test_the_agent_reads_the_parts_touching_at_rest_that_the_server_serves`, which asserts the agent's scope and the server's manifest agree |
| `section_view` | Viewport section cut | already covered (rendered) | `./cadex section` / `section.py` `write_section` (`cli/tests/test_section.py`). The dashboard's Cut (D2.5, ADR-510) was removed (ADR-533); the server still lists the cuts the command left. There is no agent tool |
| `exploded_view` | Play the explosion 0–1 | ported (D2.5, ADR-510), then removed from the page (ADR-533) | `review_server.exploded_views` still reads the engine's record into the model manifest (`test_dashboard_inspect.py::test_exploded_frames_are_cumulative_from_the_assembled_pose`); the page has no explode slider. There is no agent tool |
| `blueprint_view` | Restyle the viewport as a blueprint | dropped (ADR-498) | A live restyle has no viewport to restyle |
| `make_blueprint` | Render a multi-cell blueprint draft | ported (ADR-516) as `draw_blueprint` | Owner kept it (owner notes). Drafting and storing are one call: a sheet is stored the moment it is drawn, and a revision is the next version under the same name. Tests: `cli/tests/test_blueprint.py` |
| `save_blueprint` | Store the draft, versioned | ported (ADR-516) inside `draw_blueprint` | Stored through `put_blueprint`, versioned by name, recipe in `meta`; leaving a key out on a redraw takes it from the stored recipe. `export --blueprints` copies them out. Tests: `cli/tests/test_blueprint.py` |
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
| Chat (`space_cadex_chat`) | Transcript, message box, image attach, provider, model and account header | ported (ADR-504, ADR-507), then removed (ADR-537, ADR-538); dropped (ADR-498) the harness header | The dashboard's turn panel, later its Chat editor (ADR-534), ran `cadex -p` turns. ADR-537 made the page read-only and ADR-538 deleted the turn: the person's own agent is the chat, and the dashboard beside it redraws what that agent lands (`cli/tests/test_dashboard_read_only.py::test_browser_follows_a_change_the_cli_makes`) |
| Parameters (`space_cadex_params`) | Sliders, apply-as-defaults, rebuild/re-accept, printable ticks, view toggles | ported (ADR-503, ADR-506, ADR-510, ADR-522), then removed from the page (ADR-533, ADR-537); dropped (ADR-498) apply-as-defaults, (ADR-522) the ticks | Headless today: `cadex params --set`, `cadex revision reject|restore` (`cli/tests/test_revisions.py`), `cadex section`. The page keeps the revision trail read-only in its Revisions menu (ADR-539). The view toggles (section, explode, collision) and the parts list were cut by ADR-533; ticks dropped, see `cadex_print.py` |
| Environment (`space_cadex_env`) | Collision counts, contacts at t=0, interpenetration | already covered (headless); the contact readout ported (ADR-508), then removed from the page (ADR-533) | `review_server.py` `collision_proxies` and `initial_contacts` in the model manifest; the agent's `inspect scope=contacts` |
| Policy (`space_cadex_policy`) | Simulation play/pause/frame; per-actuator command bars | ported (D2.5, ADR-511); bars dropped | Play, pause and scrub a run's rollout in simulation seconds, in the 3D viewport when a run is the shown model (`#playback`). The actuator commands are no longer shown. Test: `test_dashboard_inspect.py::test_playback_is_timed_frames_with_a_continuous_quaternion_sign` |
| Training (`space_cadex_training`) | Training state, runs, renders, reward curve | already covered | `review_server.py` `training_telemetry`, runs, presentation; the 2D viewport's Plots and Images (ADR-534) |
| Live (`space_cadex_live`) | Live policy session, push, actuator bars | dropped (ADR-498); owner confirmed (owner notes, 2026-10-03) | See `cadex_live.py` |
| Blueprint (`space_cadex_blueprint`) | Draft or stored sheet, pager, save, export, cell pin | dropped (ADR-498) as an editor; ported (ADR-516, ADR-534) stored sheets as outputs | The 2D viewport's Drawings: every version listed, the one picked shown. Test: `test_blueprint.py::test_the_dashboard_lists_stored_sheets_newest_first_and_serves_only_those` |

## 4. Agent guidance that lived only in the shell (A1, settled by ADR-521)

These points were in the shell's `agent.py` `SYSTEM_PROMPT` or its `modes.py`
overlay. Each is settled below. A point marked ported was written in new words
in `CLI_OVERLAY` (`cli/cadex_cli/agent.py`) unless named otherwise. Nothing
was copied from the tag. ADR-538 rewrote that overlay as `OVERLAY` in
`cli/cadex_cli/guidance.py`, for an agent with a shell and files, and
deleted `agent.py` and its test (`test_turn_loop.py`); the quoted headings
below are the ones in `guidance.py` today, except where a row says
otherwise. The CLI test is `cli/tests/test_agent_guidance.py`.

| point | status | where |
|---|---|---|
| The script is deterministic and self-contained | ported | "THE MODEL IS ONE SCRIPT": same model twice, nothing random, no clock, no network, nothing read from outside the project |
| Derive secondary dimensions from primary ones | ported | "BUILD IT PARAMETRIC": a few primary parameters, the rest computed from them |
| +Z is up | ported | "THE MODEL IS ONE SCRIPT" |
| Short, meaningful output names | ported | "THE MODEL IS ONE SCRIPT": the person, the dashboard and every later change name a part by its output |
| Face pins (`@face-N`) and drawing cells (`@cell-N`) are ground truth | ported at part granularity, then removed (ADR-538); face pins owner to confirm; cells dropped (ADR-498) | The "NOBODY IS WATCHING" section that read a comment `on part <name>` went with the comments (ADR-538): the person names a part to their own agent. Face pins wait on the face-ID channel (§1, `cadex_pick.py`). Cell pins belonged to the blueprint editor, and sheets are outputs now (ADR-516) |
| Rebuilds take 0.5 s to several s, so batch value changes | ported | "EVERY BUILD COSTS SECONDS": one `set_params` call, one `edit_script` call's `replacements` |
| After `assembly.mjcf`, check the collision shapes and the t=0 contact line | already covered | `CadexAgentGuidance.md`: `inspect scope=contacts` after an `assembly.mjcf` export. Test: `test_agent_guidance.py::test_the_guidance_checks_the_rest_contacts_after_an_mjcf_export` |
| Measured terminals: a fitted row is copied, not re-derived | ported in the form that survives | "A HARNESS IS DECLARED": a catalog board's terminal rows are used as they are. The terminal picker that fitted rows by hand is dropped (ADR-498, `cadex_terminal_pick.py`) |
| The board/net declaration walkthrough | ported, reduced | "A HARNESS IS DECLARED": `boards(...)`/`nets(...)` rows, `set_params` changing them, `inspect scope=wiring`. Row shapes stay in `describe_api` and the `set_params` field descriptions, the live source, so the overlay does not copy them |

Tool-gating rules that do not carry over:
- the undo step per turn (replaced by revisions);
- Codex and pi sandboxing (A4, ADR-497);
- held-back slider drags while a turn runs. The dashboard's write paths
  had to serialise against a running turn (charter A3); since ADR-537 the
  dashboard writes nothing, so there is nothing to serialise.

## 5. Audit (2026-10-04)

Every row was checked against the tree at `9c8a740a`. The tag holds 47
entries under `mesh_agent/`, and §1 has a row for each one. §2 has a row
for each of the 23 tools, and §3 has a row for each of the seven editors.
No cell is blank. Every test a row cites exists, and the cited files
pass, with the GPU hidden and none skipped. That is 11 files: 9 in
`cli/tests/` (77 passed against a real engine) and 2 in
`src/Mod/cadex/cadex_tests/` (23 passed).

The audit fixed these rows:
- **Ported on evidence:** `model.py` and `model_api.py` (sliders, ADR-503),
  `history.py` (live transcript, ADR-504) and `ui.py`.
- **Settled:** `backend.py`'s `ENABLE_TOOL_SEARCH` check. A real CLI turn
  used the engine tools without the flag.
- **Owner confirmed:** `cadex_live.py`, the Live editor and `demo/` (owner
  notes).
- **Split:** `cadex_dimension.py`. Sheets draw measurements (ADR-516), and
  the viewer overlay was still open; it is now ported too (ADR-524).
- **Named:** Chat and Parameters, which now cite their exact tests.

Rows a status appears in. A row with a split status counts under each part.

| section | rows | ported | already covered | dropped | still to port | owner to confirm |
|---|---|---|---|---|---|---|
| §1 modules | 47 | 20 | 15 | 25 | 0 | 2 |
| §2 tools | 23 | 6 | 17 | 2 | 0 | 0 |
| §3 editors | 7 | 5 | 2 | 5 | 0 | 0 |

**W1 cannot be claimed while any row says "to port".** No row does now:
the last, `cadex_dimension.py`'s viewer overlay, was ported by ADR-524.

Since the audit, `cadex_roles.py`, `cadex_print.py` and the Parameters
editor were ported (ADR-522), `modes.py` (ADR-521), and `agent.py`'s
per-turn cost and text-tool-call warning (ADR-523), and
`cadex_dimension.py`'s viewer overlay (ADR-524).

The audit's counts and its "77 passed" are as of `9c8a740a`. ADR-533, ADR-537
and ADR-538 later removed much of what it counted as ported (see the note
at the top), and deleted several of the test files it ran
(`test_dashboard_writes.py`, `test_dashboard_export.py`,
`test_prompt_images.py`, `test_comments.py`, `test_owner_channel.py`,
`test_turn_usage.py`, `test_turn_loop.py`). The rows above cite the tests
in the tree today; the table is not recounted.

The two "owner to confirm" rows are face-level pins and the face-ID
channel. A1 asks for part picking, and that is ported.
