---
node_id: 972534f9-19a7-58f2-be20-5f1762f468c2
slug: clear-sand-8062
title: Explored xscript-driven Blender geometry
created_at: '2026-09-05T10:01:06+00:00'
parents:
- solemn-chart-6274
- kind-ledge-5493
summary: ''
---
## What

Reviewed the existing CAD/mesh boundary and proposed ways for xscript to use Blender-native geometry. The user requested brainstorming prompted by agents' perceived competence with both CAD scripts and Blender Python; no implementation or architecture decision was requested. Interpreted the spoken name "vpy" as bpy, explicitly stated to the user.

## Why

Follows the organic modelling vertical and the earlier ambition to let the agent use multiple modelling paradigms without asking the user to select one. The prior unification attempt recorded in kind-ledge-5493 is interview evidence, not a verified implementation to restore.

## Method

Read STATE.md, the graph contract, VISION.md, relevant sections of XSCRIPT.md, ARCHITECTURE.md, ORGANIC.md and BLENDER.md. Inspected cadex_mesh_api.py, cadex_part_worker.py's shape_from_mesh branch, CadexScriptedDomains.py's source validator, and mesh_agent/cadex_hydrate.py. Checked the inherited Blender operator-context documentation and dependency-graph examples. Consulted official Blender web search results; direct page fetches failed with HTTP 402. No runtime experiment or test suite was run; findings are source inspection and design hypotheses.

## Result

Existing xscript mesh operations use FreeCAD Mesh/MeshPart; the Blender scene mirrors accepted output. Source imports are refused. mesh.from_shape tessellates BREP; part.shape_from_mesh sews faceted topology and attempts solid promotion, not recovery of analytic design intent. Decimation is explicitly run-dependent, digest-identified by definition, and refused as input to shape_from_mesh. Hydration replaces geometry when its source digest changes. The standing vision deliberately removed local bpy authoring and intends eventual Blender independence.

Suggested three approaches: generated Blender assets imported through today's asset path (cheap experiment, no automatic regeneration); a proposed Blender build step declared in the authoritative project script (preferred direction to investigate, no API exists); or a portable Cadex mesh API implemented using Blender (narrower language reuse and more wrapper maintenance). The preferred proposal would retain native bpy/BMesh/modifier/Geometry Nodes authoring within a declared recipe executed in an isolated headless worker, with named inputs, outputs, parameters, runtime version and explicit units. It requires real execution isolation, scheduling across process boundaries, validation, output identity and rollback; a subprocess or Python allowlist alone is not a sandbox. Backend-specific recipes would establish a durable Blender dependency even after a future UI replacement, requiring an explicit vision/ADR decision before implementation.

Suggested bridging through named CAD mounting frames, clearances and cutting shapes while preserving mesh-native skins. Mesh tessellation does not retain exact analytic interfaces; engineering checks must measure the final manufacturing representation. Quad cages and modifier recipes should be retained even if evaluated output is triangulated. Proposed a copied wolf enclosure benchmark: CAD mounts and clearance envelope, Blender organic skin, parameter-driven regeneration, reopen/rebuild without scene state, independent mesh and fit validation, export, undo and failure rollback. No claim of measured speed, reliability or deterministic Blender output was made. No architecture decision was adopted.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: c99e6e6002de2366e441f8ef77228019123e4147

## State Impact

none: Brainstorming only; no implementation or architecture decision adopted.
