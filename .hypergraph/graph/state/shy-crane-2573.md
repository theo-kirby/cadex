---
node_id: b270d71a-7c79-5efb-afe8-4ded59f911eb
slug: shy-crane-2573
title: The shell — the Blender fork and mesh_agent
created_at: '2026-08-09T15:21:41+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: superseded

## Current

**Deleted (ADR-498, commit `6b21d3f7`).** `git ls-files shell` is 0; the tag `v1-blender-shell` is the last tree that carries the Blender fork and `mesh_agent`, and `docs/SHELL-PARITY.md` records where each part went — ported to the dashboard, covered, or dropped [rec: calm-quartz-1493]. It was disabled first (ADR-495: no pixi task, `package/` script or CI job built, launched or gated it) [rec: lucky-haven-1081] and its `mesh.blender` path retired (ADR-496) [rec: clear-heron-4371]; Codex and pi, its alternative harnesses, went with ADR-497 [rec: crimson-union-6659]. No live doc names `shell/`, `mesh_agent`, a `.blend` or `CADEX_BLENDER_EXECUTABLE` — only ADRs and `docs/history/` do, test-pinned (ADR-499) [rec: mellow-pine-4848].

**Superseded by the three-part product** (ADR-500): the dashboard (`./cadex review`; the live review lineage is `crisp-sun-1239`) is the only UI, and the contract rewrite is tracked by `eager-sea-3906`. ADR-500 also supersedes the Rust shell (Phase 12): a desktop app, if ever built, copies the dashboard [rec: smooth-cedar-5324].

What the shell was — a GPL Blender fork shipping the engine in its bundle, a protocol client with viewport, chat, sliders, the Wiring/Live/Training/Blueprint editors, presentation views (section, explode, dimensions, blueprint sheets), printable-part export, a landing screen with the biped demo, and three harnesses — is history in the record nodes cited below and in `docs/history/BLENDER.md` [rec: calm-quartz-1493]. Reconcile judgement: compacted to the deletion plus the lessons that still apply to the agent and the protocol; the record graph keeps the detail. Shell-era state nodes that declared no impact here (e.g. `happy-key-3312`, `simple-willow-8989`) are left for R1's frontier pruning [rec: smooth-cedar-5324].

## Negative knowledge

- [scope: any per-tool exemption from a result cap | confidence: high | evidence: shy-glade-0050] `MAX_RESULT_CHARS = 4096` governs every mesh tool **except** `get_script`, and that unannounced exemption is what an agent got wrong — it concluded "the engine only shows me a 4 KB window", which was false, and never checked. The general lesson is worse than the specific one: **a tool that cannot serve part of a thing invites the model to make the thing smaller**, and the model has write access. 122 lines and 4.8 KB of a user's design rationale were deleted to advance a read.
- [scope: adding a table to docs/INTEGRATION.md | confidence: high | evidence: forest-wind-3489] Its two contract tables are scraped by regex on any line starting with `` | ` `` — across the whole document for ops, and within the response section for keys. A new markdown table anywhere in the file is read as protocol rows. Document nested records as a bullet list.
- [scope: an agent that cannot reach its tools | confidence: high | evidence: weathered-sand-9705] **It does not say so.** It writes the call out as prose — `<invoke name="mcp__mesh__get_script">` — invents a plausible result, and answers as though the work happened. There is no error, no non-zero exit and no empty reply, so the turn reads *better* than a real one. Caught only from a user transcript in which the model quoted back a complete "current script" that did not exist, in an API this product does not have, on 1670 tokens of context. `agent.py` now watches the streamed text for `<invoke name=` — which a real call can never produce, since it arrives as a `tool_use` block — and says so once per turn.
- [scope: two safety settings that each look right | confidence: high | evidence: weathered-sand-9705] `--tools ""` is correct and MCP schema deferral is a reasonable default; **together** they disable the only key to the tools the product depends on. Neither is wrong alone, so no review of either would have caught it. `test_the_mesh_tools_are_not_deferred_behind_a_disabled_tool` pins the *join*, not the halves.
- [scope: the agent test suite | confidence: high | evidence: weathered-sand-9705] The only test that would have caught this is the one that never runs: `MESH_AGENT_LIVE=1`. Every other agent test drives the mock backend, which by construction cannot reproduce a CLI flag interaction. An opt-in live test is a test you do not have.

## Provenance

- simple-hollow-8675 — the shell became the product when the Qt shell was deleted; it is a protocol client and nothing more
- merry-eagle-4093 — the shell moved into this repository and the engine ships inside its bundle
- open-dew-7293 — the menus, the editor types and the saved-layout startup file
- crisp-glacier-6395 — the Wiring editor
- mellow-hawk-8610 — the Live editor and the force-arrow overlay
- solemn-chart-6274 — render_views and the section-cage overlay
- open-key-6334 — the diff rule that replaced the empty-diff rule
- sage-wood-0687 — nothing in shell/ imports mujoco, and a test asserts it
- ancient-current-9419 — the two linked-part menu rows, the 17th tool, and the Save-As carry-forward defect they exposed
- forest-wind-3489 — `cadex_dimension.py`: the screen-space overlay, the Measure button that does not author the script, the gate's exit-code trap, and the 675-check run
- shy-glade-0050 — `get_script` serves windows, so a read limit is never answered by editing the script; and the 696-check run
- grand-peak-3688 — `cadex_section.py`: the section view is a capped boolean rather than a clip plane, it is a view and not a feature, and `obj.bound_box` reads the cut it made
- neat-tower-5715 — the section view's prompt line did not fit the overlay's 3500-character cap, and the cap did not move
- zesty-cove-4881 — `cadex_explode.py`: the factor slider over the engine's exploded-view record, matrix_world over delta channels, and the baked-simulation refusal
- windy-wolf-5012 — ADR-150: the view registry, the blueprint view, `make_blueprint`/`render_blueprint`, the clear()-fallback stomp the gate caught, and the overlays-ON dependency of the Edges wires
- morning-walrus-8074 — ADR-151: the composed, dressed sheet (`cadex_sheet.py`), hero-right, `hide_set` over `hide_viewport`, the flat snapshot/restore, and the two bit-equality traps its gate test surfaced
- wild-walrus-5718 — the ADR-151 addendum: the triptych default, the graceful explode degrade, and the uniform ground sampled off the colour-managed tiles
- clever-hill-0361 — ADR-152: only (the isolate as a complement hide), the mosaic layout (freeform cells held to the tiling invariant by refusal), and the curation rewrite of the tool description
- humble-peak-6095 — ADR-153: 16:9 by default, part-name callouts with their measured width floor, and the parameters panel as a sheet cell
- careful-key-9041 — ADR-154: Opus 5 as the default model in both front ends, and the one constant the picker now reads
- still-wave-6655 — ADR-156: printable parts in the shell — `cadex_print.py`, the per-row checkbox operator, the File menu row, the conflict dialog built from the engine's refusal, and the two panel-draw bugs only a windowed probe could find
- green-tree-7595 — ADR-157: named, revisable sheets (`based_on` + the stored recipe), the per-cell aspect honoured by measure-and-replace, the text panel, and the params-panel label collision a windowed probe found
- gilded-wind-5121 — ADR-158: the print tick becomes a scene property — no op, no store write, no revision — and drop-on-drift moves to the shell
- weathered-sand-9705 — the tool-deferral bug, its silent failure mode, the fix and the test that pins the join
- tender-crane-5909 — ADR-164: the chat input anchored to the window floor, the chat-only button row, and the Interface section
- civic-glade-9153 — ADR-165: one Interface grid, and the no-open-a-view rule that deleted three operators
- curious-cloud-7186 — ADR-166: native File/Edit via GHOST_kEventNativeMenu, both window bars gone, VERSION 0.0.5 with the commit-count build stamp, and BLENDER-TREE §2d
- lucid-otter-3511 — ADR-167: the landing screen in the viewport, the sanitized wcv12 demo in the bundle, and the restricted-context register trap
- wandering-mist-0460 — the ADR-167 addendum: theme greys, rounded geometry, and the qlmanage baked-white alpha trap
- hollow-spring-0679 — ADR-168: Parameters | Outliner, chat at a third, the Dock's mark on the landing page, and the cursor-on-the-edge poll of the screen ops
- deep-branch-6721 — ADR-172: the default viewport look — cavity on, gizmos off, overlays on but bare
- dawn-oak-0677 — ADR-173: the biped example project returns to the landing screen, provenance-clean
- sleepy-shade-1485 — the demo .blend carried the chat transcript; scrubbed, and the payload test now opens the shipped file
- crimson-vine-9992 — the demo card becomes a viewport render of the model, not its blueprint
- shady-lodge-6077 — the demo refreshed to the current biped and the card drops the floor
- forest-chart-2781 — Codex backend, event contract and provider-tagged sessions
- merry-water-7647 — pi backend and second bridge transport
- happy-valley-9134 — technical theme and sheet/viewport dimensions
- cool-jasper-0086 — Assembly collection and blueprint inspection scope
- calm-flame-0305 — disk index avoids inspect pager stubs
- winter-bloom-8543 — draft/save split, section pins and overlay budget
- wild-prairie-9912 — dedicated Blueprint Editor with independent selections
- damp-fountain-8719 — product tool-call cap removed, test override retained
- twilight-lake-8164 — library catalog surfaced to the assistant
- honest-harvest-7271 — copy buttons, collapsed calls and settings gear; static default later superseded
- curious-sail-8332 — startup application code, JSON settings and AI Preferences
- windy-sage-5295 — harness-owned account/model discovery and login; validation bounds
- simple-bramble-8616 — runtime discovery, accepted hydration and native recipe gate
- sunny-canyon-1138 — headless camera leakage audit, baseline gate and viewport restoration limitation
- civic-moss-7263 — independent source/edge render ownership, regression and latest source-shell/bundled-engine gate
- crimson-trail-6068 — ADR-448: app agent has look, fit/inventory blocks, inspect scopes and engine guidance; slider latency unmoved
- rough-water-0848 — ADR-449: viewport paints parts in their appearance roles from CadexStudio.role_colours
- restless-fjord-9059 — ADR-450: Training editor Runs panel over the run directories
- staid-nest-0170 — ADR-451: selected run's curve drawn in the Training editor
- peaceful-sail-5197 — ADR-452: Renders panel with Render Now; Play Video on runs
- eager-basin-6116 — ADR-453: chat shows running turn and session tokens/cost
- lucky-haven-1081 — ADR-495: shell disabled; nothing builds, launches or gates it; tree on disk pending delete
- clear-heron-4371 — ADR-496: mesh.blender retired, so the shell's runtime-path bullet is dropped
- calm-quartz-1493 — ADR-498: shell/ deleted; v1-blender-shell is the last tree with it
- mellow-pine-4848 — ADR-499: no live doc names the deleted shell
- smooth-cedar-5324 — ADR-500: Cadex is engine + dashboard + agent; the Rust shell superseded too
- crimson-union-6659 — ADR-497: Codex and pi retired with the shell
