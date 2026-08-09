---
node_id: 9d2889d7-cdc8-54fa-9028-853bca72c947
slug: lone-haven-0640
title: 'Prehistory: VibeCAD, and why Cadex left it'
created_at: '2026-08-09T15:15:47+00:00'
parents:
- odd-banner-6071
summary: 'Cadex broke off from VibeCAD — a FreeCAD fork with an agent inside — to pursue a different north star: FreeCAD''s constraint engine inside Blender''s shell, with an agent on top.'
---
## What

Before this repository existed, the work happened inside **VibeCAD** — another
developer's project, a vendored fork of FreeCAD with an AI agent inside it:
"Cursor, but for CAD". The author contributed to it, and then broke the work off
into a separate project rather than keep maintaining a personal fork. Cadex's
first commit is 2026-07-23 (`b3b9abb7c41a`, "Initial commit"); everything above
that line is prehistory, carried in the author's memory and in the
`[VibeCAD-era]` provenance tags that still label code in the tree.

## Why

Independent workstream branched from the record root: this is the project's
origin and has no causal parent inside the repository.

VibeCAD worked, and is still under active development by its maintainer. The
break was not dissatisfaction with it — it was that the author's north star had
stopped being VibeCAD's, and continuing would have meant steering someone else's
roadmap.

## Method

Author's account, given in the adoption interview (2026-08-09). Corroborated by
what survives in the tree: `docs/PROVENANCE.md` credits VibeCAD;
`docs/ARCHITECTURE.md` tags surviving modules `[VibeCAD-era]`
(`CadexScriptedProcess.py`, `CadexScriptedPublication.py`,
`cadex_{partdesign,sketcher,part,assembly}_{api,worker}.py`,
`CadexGeometryWorker.cpp`); `docs/history/` keeps two superseded VibeCAD-era
design documents; and ROADMAP Phase 13b records deleting `/Users/theo/vibecad`
(5.9 GB) once its branch tip was pushed and verified.

## Result

The north star that came out of the break, in the author's own framing: take
FreeCAD's **parametric, constraint-based modelling engine** — plus everything
VibeCAD taught about how an agent and a human drive the same tools together —
and inject it into **Blender's shell**. Blender has the modern UI and UX, the
extensibility and the Python API; what it does not have is constraint-based
modelling, because its paradigm is mesh-native (vertices, edges, faces,
sculpting, armature rigging). FreeCAD has the modelling and not the shell. Smush
them together, and put an agent on the whole thing.

Every structural decision in this repository is downstream of that sentence. In
particular it is why the two inherited trees are **forks to be reduced** rather
than dependencies: what we fork we intend to replace (FreeCAD's application
layer, Blender's shell), and what we keep we keep unmodified (OCCT, and later
MuJoCo).

What carried over from VibeCAD: the xscript idea (the agent authors a
declarative Python program; the program *is* the model), the sandboxed-worker
publication pipeline, and four of the five domain APIs. What did not: multi-engine
scripting (build123d, OpenSCAD), the 18-domain surface, and eventually the whole
of FreeCAD's UI.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW engine — the engine is a FreeCAD fork carrying VibeCAD-era pipeline code; provenance is a live licensing and design constraint, not trivia.
