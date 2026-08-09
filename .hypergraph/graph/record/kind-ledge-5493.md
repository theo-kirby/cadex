---
node_id: e9f9026b-ac5d-5969-b053-88717e1892eb
slug: kind-ledge-5493
title: 'Prehistory: what was tried and left little trace'
created_at: '2026-08-09T15:16:13+00:00'
parents:
- odd-banner-6071
summary: 'The undocumented dead ends, at low confidence: an attempt to unify the mesh and constraint paradigms, and a lot of unwritten cross-paradigm comparison.'
---
## What

The dead ends and background experiments that never became ADRs, recorded
because an adoption that imports only the documented history imports a
flattering version of it.

## Why

Independent workstream branched from the record root: it spans the project
rather than following any one era.

## Method

Author's account in the adoption interview (2026-08-09), plus what the tree
corroborates. **These claims come from memory and are not independently
verifiable in this repository** — some of the work may have happened on
throwaway branches that no longer exist. They are recorded at low confidence and
must be cited as such, never rounded up.

## Result

- **An attempt to unify the mesh-based and constraint-based systems.** The
  author recalls trying this at some point, possibly on a throwaway branch, and
  it did not land as a system. Some UX-level pieces of it may have survived into
  the tree without attribution. No commit range is identified.
- **A lot of ad-hoc comparison across the paradigms the app now contains**:
  Blender's own simulation versus the assembly simulation versus MuJoCo's physics
  constraints versus the RL training environment; constraint-based modelling
  versus mesh-based modelling versus modifiers. Not written up anywhere.
- **Why it keeps being tried**, which is the durable part: the intended end state
  is that **the agent uses everything at its disposal and the user is never asked
  which paradigm they are in** — not "this bit is mesh-based, this bit is
  constraint-based, that simulation came from somewhere else". Getting there is
  hard, so it is being approached one step at a time.

Two things that *did* land are exactly this pattern succeeding rather than
failing, which is the useful reading: `part.shape_from_mesh` feeds imported
meshes into the BREP domains (ADR-043), and the section cage arrived as **engine
ops on a declared table** rather than as mesh editing (ADR-127) — the shell
supplies the gesture and the script stays the only thing that authors geometry.
The prediction in `docs/VISION.md` that interactive mesh editing would have to
arrive as engine ops held exactly.

The largest removal, by contrast, is fully documented: FreeCAD's entire UI,
replaced by the Blender shell (ADR-021, ADR-022). Its delete commit — Phase 8,
`src/Gui`, 66 MB, 729 files — is still pending.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW organic-modelling — one-paradigm-for-the-user is the standing direction behind this vertical; the earlier unification attempt is undocumented and low-confidence.
- target: NEW inherited-tree-reduction — `src/Gui` is disabled but not deleted; Phase 8 is the outstanding delete commit.
