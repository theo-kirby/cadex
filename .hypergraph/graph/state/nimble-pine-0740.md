---
node_id: 76f41cb1-395d-5a67-b207-edd243158413
slug: nimble-pine-0740
title: cadex — state
created_at: '2026-08-09T15:07:27+00:00'
parents: []
summary: ''
---
Cadex is an AI-native CAD application: you describe the part, the AI authors a declarative **xscript** Python program, the program runs in a sandboxed headless worker, and only validated geometry reaches your model. The script *is* the model.

One product built from two forks in one repository, separated by a process boundary rather than a repository boundary: the **engine** at the root (a FreeCAD fork, running as `cadexd` over NDJSON) and the **shell** under `shell/` (a Blender fork carrying the `mesh_agent` add-on, which ships the engine inside its own bundle). A third protocol client, `cli/`, has no display at all. **Dynamics and control are built in**: a mechanism falls, collides, is actuated, exports as MJCF with exact OCCT inertias, and plays back a policy trained offboard on MuJoCo.

Read `docs/VISION.md` before designing anything; `AGENTS.md` for the repo map, commands and change policy; `docs/DECISIONS.md` for why anything is the way it is.

Adopted the Hypergraph protocol on 2026-08-09 (mode B — no legacy graph existed). Record nodes created before the epoch marker `winter-rain-7897` are prehistory: fourteen era and workstream summaries distilled from the repository and an author interview, not an event-by-event reconstruction.

## Reconciliation

- high_water_mark: tidy-banner-0293, shy-glade-0050, empty-light-4558, neat-tower-5715, careful-key-9041, weathered-falcon-4350, still-wave-6655
- reconciled_at: 2026-08-20T18:35:00+00:00
