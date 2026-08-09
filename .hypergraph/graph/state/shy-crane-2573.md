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
- Product surface: viewport, chat, parameter sliders, model tree and script view; Cadex File and Edit menus; a saved-layout startup file rather than a Python template [rec: open-dew-7293]. Plus the Wiring editor [rec: crisp-glacier-6395], the Environment/Policy/Training/Live editors and the force-arrow overlay [rec: mellow-hawk-8610], `render_views` and the section-cage overlay [rec: solemn-chart-6274], and **File > Link Part... / File > Refresh Linked Parts** with the `link_part` backend trio behind them [rec: ancient-current-9419].
- The model reaches the shell through **17 MCP tools** in `tools.py` [rec: ancient-current-9419].
- **The diff rule that governs every change here**: every line of our `shell/` diff is under `shell/scripts/addons_core/mesh_agent/` or `shell/tests/python/`, and the inherited Blender tree is untouched. `docs/BLENDER-TREE.md` §2a is eight files and must stay eight [rec: open-key-6334]. Linked parts held to it — +541/-5 across six files, nothing in §2 moved [rec: ancient-current-9419].
- Nothing in `shell/` imports mujoco, and a test asserts it. The shell never learns MuJoCo exists — a policy rollout reaches it as the simulation trace it already knew how to play [rec: sage-wood-0687] [rec: open-key-6334].
- The product gate is `pixi run gate`: one `CADEX-BLENDER-GATE` line against the built bundle, with picking ≥ 0.99 and slider median ≤ 0.65 s [rec: simple-hollow-8675] [rec: merry-eagle-4093].

**A shipped defect, found and fixed while adding linked parts.** `cadex_backend._assets_in` filtered Save-As's carry-forward on the three-suffix `ASSET_SUFFIXES` the shell mirrors by name, so a Save-As would have **dropped every `.cxpart`** and left the new file with a script that could not run — ADR-046's bug arriving on a new file type. A separate `CARRIED_ASSET_SUFFIXES` fixes it and the gate pins it. **The identical gap is still open for `.cxpolicy`**: it was named and deliberately not fixed, because carrying trained weights on every Save-As is its own decision [rec: ancient-current-9419].

## Negative knowledge

- [scope: shell/ edits outside mesh_agent | confidence: high | evidence: open-key-6334] Every line added to the inherited Blender tree is a future merge conflict. Adding one is a decision to bring back, not a fix to slip in — the empty-diff rule was retired but the boundary it stood proxy for was not, and BLENDER-TREE.md section 2a must stay eight files.
- [scope: gate coverage | confidence: high | evidence: solemn-chart-6274] The gate runs blender --background, so anything needing a real VIEW_3D is not covered by it. Verify those by driving the built application and say so, rather than implying coverage the gate does not have.
- [scope: any new asset suffix | confidence: high | evidence: ancient-current-9419] Widening the engine's `_STORED_ASSET_SUFFIXES` is free, but the shell carries its **own** suffix list for Save-As and it does not follow. A new asset type that is not added there is silently dropped by Save-As, and the failure surfaces later as a script that cannot run in the copy.
- [scope: asserting a part is real BREP from the shell | confidence: high | evidence: ancient-current-9419] The viewport polygon count cannot tell a linked BREP solid from a converted STL — the mesh in the viewport is a tessellation either way, and a 40-face solid shows 520 polygons. A gate assertion on `obj.data.polygons` looks like it proves this and does not; the claim has to be made against engine facts.

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
