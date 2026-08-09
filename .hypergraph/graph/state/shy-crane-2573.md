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
- Product surface: viewport, chat, parameter sliders, model tree and script view; Cadex File and Edit menus; a saved-layout startup file rather than a Python template [rec: open-dew-7293]. Plus the Wiring editor [rec: crisp-glacier-6395], the Environment/Policy/Training/Live editors and the force-arrow overlay [rec: mellow-hawk-8610], and `render_views` and the section-cage overlay [rec: solemn-chart-6274].
- **The diff rule that governs every change here**: every line of our `shell/` diff is under `shell/scripts/addons_core/mesh_agent/` or `shell/tests/python/`, and the inherited Blender tree is untouched. `docs/BLENDER-TREE.md` §2a is eight files and must stay eight [rec: open-key-6334].
- Nothing in `shell/` imports mujoco, and a test asserts it. The shell never learns MuJoCo exists — a policy rollout reaches it as the simulation trace it already knew how to play [rec: sage-wood-0687] [rec: open-key-6334].
- The product gate is `pixi run gate`: one `CADEX-BLENDER-GATE` line against the built bundle, with picking ≥ 0.99 and slider median ≤ 0.65 s [rec: simple-hollow-8675] [rec: merry-eagle-4093].

## Negative knowledge

- [scope: shell/ edits outside mesh_agent | confidence: high | evidence: open-key-6334] Every line added to the inherited Blender tree is a future merge conflict. Adding one is a decision to bring back, not a fix to slip in — the empty-diff rule was retired but the boundary it stood proxy for was not, and BLENDER-TREE.md section 2a must stay eight files.
- [scope: gate coverage | confidence: high | evidence: solemn-chart-6274] The gate runs blender --background, so anything needing a real VIEW_3D is not covered by it. Verify those by driving the built application and say so, rather than implying coverage the gate does not have.

## Provenance

- simple-hollow-8675 — the shell became the product when the Qt shell was deleted; it is a protocol client and nothing more
- merry-eagle-4093 — the shell moved into this repository and the engine ships inside its bundle
- open-dew-7293 — the menus, the editor types and the saved-layout startup file
- crisp-glacier-6395 — the Wiring editor
- mellow-hawk-8610 — the Live editor and the force-arrow overlay
- solemn-chart-6274 — render_views and the section-cage overlay
- open-key-6334 — the diff rule that replaced the empty-diff rule
- sage-wood-0687 — nothing in shell/ imports mujoco, and a test asserts it
