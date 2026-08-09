---
node_id: b270d71a-7c79-5efb-afe8-4ded59f911eb
slug: shy-crane-2573
title: The shell — the Blender fork and mesh_agent
created_at: '2026-08-09T15:21:41+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

The shell is a Blender fork under `shell/` carrying the `mesh_agent` add-on. It is the application a user launches, and it ships the engine inside its own bundle, discovered through a `cadex-engine.json` manifest so a built application needs no configuration [rec: simple-hollow-8675] [rec: merry-eagle-4093].

- It is a **protocol client and nothing else**. It may not import anything from `src/`; `cadexd_client.py` is deliberately a plain GPL NDJSON client with no cadex imports. Being in one repository does not relax this [rec: simple-hollow-8675] [rec: merry-eagle-4093].
- Product surface: viewport, chat, parameter sliders, model tree and script view; Cadex File and Edit menus; a saved-layout startup file rather than a Python template [rec: open-dew-7293]. Plus the Wiring editor [rec: crisp-glacier-6395], the Environment/Policy/Training/Live editors and the force-arrow overlay [rec: mellow-hawk-8610], `render_views` and the section-cage overlay [rec: solemn-chart-6274], **File > Link Part... / File > Refresh Linked Parts** with the `link_part` backend trio behind them [rec: ancient-current-9419], and the Dimensions overlay with its Measure button [rec: forest-wind-3489].
- The model reaches the shell through **17 MCP tools** in `tools.py` [rec: ancient-current-9419].
- **`cadex_dimension.py` draws a declared measurement as a drawing sheet would** — extension line at each anchor, dimension line between them, the number in the middle with the line broken around it. Everything except the two anchors is computed **in screen space**: the offset direction is perpendicular *on the screen*, so it cannot go edge-on however far you orbit — by construction rather than by care — and gaps, ticks and text are pixel constants, so a 2 mm boss and a 2 m beam read identically at any zoom. Below `MINIMUM_SPAN_PX`, which is what looking straight down the measured axis gives you, it degrades to a leader still carrying the number, so the value survives every viewing angle. One `POST_PIXEL` pass where the force arrows need two, because a dimension is not a world object [rec: forest-wind-3489].
- It creates **no Blender objects**, so unlike `cadex_collision` and `cadex_cage` it needs no sibling collection and cannot be swept by the contract GC. The Measure button queues a request on the pin queue rather than writing the script, so **the script keeps exactly one author** [rec: forest-wind-3489].
- **The diff rule that governs every change here**: every line of our `shell/` diff is under `shell/scripts/addons_core/mesh_agent/` or `shell/tests/python/`, and the inherited Blender tree is untouched. `docs/BLENDER-TREE.md` §2a is eight files and must stay eight [rec: open-key-6334]. Linked parts held to it — +541/-5 across six files [rec: ancient-current-9419] — and so did dimensions: one new file (650 lines) plus +331/-3 across six, nothing in §2 moved [rec: forest-wind-3489].
- Nothing in `shell/` imports mujoco, and a test asserts it. The shell never learns MuJoCo exists — a policy rollout reaches it as the simulation trace it already knew how to play [rec: sage-wood-0687] [rec: open-key-6334].
- The product gate is `pixi run gate`: one `CADEX-BLENDER-GATE` line against the built bundle, with picking ≥ 0.99 and slider median ≤ 0.65 s. **675 checks, `"ok": true`** as of 2026-08-09 [rec: simple-hollow-8675] [rec: merry-eagle-4093] [rec: forest-wind-3489].

**A shipped defect, found and fixed while adding linked parts.** `cadex_backend._assets_in` filtered Save-As's carry-forward on the three-suffix `ASSET_SUFFIXES` the shell mirrors by name, so a Save-As would have **dropped every `.cxpart`** and left the new file with a script that could not run — ADR-046's bug arriving on a new file type. A separate `CARRIED_ASSET_SUFFIXES` fixes it and the gate pins it. **The identical gap is still open for `.cxpolicy`**: it was named and deliberately not fixed, because carrying trained weights on every Save-As is its own decision [rec: ancient-current-9419].

## Negative knowledge

- [scope: shell/ edits outside mesh_agent | confidence: high | evidence: open-key-6334] Every line added to the inherited Blender tree is a future merge conflict. Adding one is a decision to bring back, not a fix to slip in — the empty-diff rule was retired but the boundary it stood proxy for was not, and BLENDER-TREE.md section 2a must stay eight files.
- [scope: gate coverage | confidence: high | evidence: solemn-chart-6274] The gate runs blender --background, so anything needing a real VIEW_3D is not covered by it. Verify those by driving the built application and say so, rather than implying coverage the gate does not have.
- [scope: reading the gate's result | confidence: high | evidence: forest-wind-3489] **`pixi run gate` exits 0 when a test raises mid-run.** An `AttributeError` in one test ended the suite after 355 checks with no `CADEX-BLENDER-GATE` line at all, and the exit code was still 0. Checking the exit code is not enough — the `"ok": true` line has to be read. Pre-existing and not fixed.
- [scope: any new asset suffix | confidence: high | evidence: ancient-current-9419] Widening the engine's `_STORED_ASSET_SUFFIXES` is free, but the shell carries its **own** suffix list for Save-As and it does not follow. A new asset type that is not added there is silently dropped by Save-As, and the failure surfaces later as a script that cannot run in the copy.
- [scope: asserting anything about an output from the viewport | confidence: high | evidence: ancient-current-9419, forest-wind-3489] The viewport polygon count tells you nothing about what an output *is* — the mesh in the viewport is a tessellation whatever it came from, so a 40-face linked BREP solid shows 520 polygons and a measurement shows whatever its subject shows. A gate assertion on `obj.data.polygons` looks like it proves this and does not; **this assertion has now been written and thrown away twice in this tree.** For a drawn overlay the check that works is calling the drawing function with a made-up region and view matrix — which is why `drawing_for` is a function rather than something living inside a draw handler.
- [scope: an overlay that must read from any angle | confidence: high | evidence: forest-wind-3489] A plane fixed in the model is the wrong home for a dimension: any such plane goes edge-on if you orbit far enough. Compute in screen space instead, and the failure mode is removed by construction rather than defended against. Likewise a circle's in-plane basis must not come off a fixed reference axis — a bore drilled down Z is the single most common thing anyone measures, so the naive choice fails on the first real model rather than an exotic one; take the basis off the world axis least parallel to the circle's own.
- [scope: adding a table to docs/INTEGRATION.md | confidence: high | evidence: forest-wind-3489] Its two contract tables are scraped by regex on any line starting with `` | ` `` — across the whole document for ops, and within the response section for keys. A new markdown table anywhere in the file is read as protocol rows. Document nested records as a bullet list.
- [scope: where model state may live | confidence: high | evidence: forest-wind-3489] Scene data in the `.blend` is much cheaper than a script declaration and is the wrong answer for anything that is part of the model: it would be the only model state not in the script — lost by a Save-As, unauthorable by the agent, and unable to travel in a `.cxpart`. In the script it is anchored by selector and recomputed, which is what makes it follow a parameter.

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
