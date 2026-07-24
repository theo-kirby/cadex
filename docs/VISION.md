# VISION.md — What Cadex Is Becoming

Verified against source: 2026-07-24

This document is the product vision. It is authoritative: when a change
conflicts with this document, the change is wrong or the vision needs an
explicit decision in `docs/DECISIONS.md`. What exists **today** is documented
in `docs/ARCHITECTURE.md`; the path from here to there is `docs/ROADMAP.md`.

## The product

One ultimate agentic CAD app, combining:

- **FreeCAD capability** — real parametric BREP modeling on OCCT (the cadex
  engine, this repo);
- **Blender UX** — the `/Users/theo/mesh` fork's look, feel, viewport, and
  interaction quality (the shell endpoint, see `docs/INTEGRATION.md`);
- **The xscript methodology** — the AI authors a declarative Python program;
  the program is the model.

### Everything is driven by the script

- **Nothing happens outside the script.** Every feature, part, assembly, and
  parameter exists because a line of the project script created it. There are
  no side-channel edits, no direct document mutations, no "quick manual fix"
  paths.
- **The exact full state is rebuildable from the script at any time.** The
  document/scene is a cache. Delete it, re-run the script, and you get a
  byte-equivalent model back. This property is testable and must stay
  testable (Phase 2 exit criterion in `docs/ROADMAP.md`).
- **One project script** (`model.py`-style) is THE user-visible artifact and
  sole source of truth. It composes domain APIs (partdesign, sketcher, part,
  assembly, later mesh); parameters are declared at the top of the script and
  surface as sliders. (Today's runtime uses per-domain programs — that is an
  implementation stage, not the product. See `docs/XSCRIPT.md`.)

### The interface

- **Left half: viewport. Right half: chat, parameter sliders, model tree,
  script view.** That's the whole app. The UX north star is the working
  prototype in the mesh repo: `scripts/addons_core/mesh_agent/` plus the
  `Mesh` app template (50/50 split, chat input docked at the bottom right) —
  detailed in `docs/BLENDER.md`.
- **No user-accessible modeling tools.** No fillet button, no extrude button,
  no sketch editor toolbar. The user talks; the AI writes script; sliders
  tweak declared parameters without the AI in the loop.
- **No workbench concept.** Workbenches are an implementation detail of the
  FreeCAD substrate, not a product concept. The user never selects a mode.
- **One undo step per chat turn.**

### Scope

Exactly four capability areas:

1. **Part** — direct OCC shape modeling.
2. **Part Design** — sketch-based feature modeling (bodies, pads, pockets…).
3. **Assemblies** — links, joints, solved placements, motion.
4. **Mesh editing** — import/tessellate/boolean/repair now; real mesh editing
   arrives with the Blender shell (BMesh).

Everything else FreeCAD offers (FEM, CAM, TechDraw, BIM, Draft, Points,
Robot, Spreadsheet, …) is out of scope. Deleted in the VibeCAD teardown at
the runtime level; the remaining source trees are slated for removal
(`docs/FREECAD.md`).

## Non-goals

- A general-purpose FreeCAD distribution or a FreeCAD-compatible fork.
- Manual CAD workflows of any kind; feature parity with FreeCAD's UI.
- Supporting all FreeCAD workbenches, file formats, or addons.
- Multi-engine scripting (build123d, OpenSCAD — retired in the teardown).
- Long-term investment in the Qt/Coin3D shell (it is interim; the endpoint is
  the Blender shell — `docs/INTEGRATION.md`).

## Guiding principles

1. **Elegance and simplicity.** Prefer the design that removes a concept over
   the one that adds a switch.
2. **Remove more than we add.** Subtractive change in `src/Mod/cadex/**` and
   docs is encouraged, not merely permitted (policy in `CLAUDE.md`; every
   removal logged in `docs/DECISIONS.md`).
3. **The script is the truth; everything else is a cache.** Any state that
   can't be rebuilt from the script is a bug.
4. **Validated results only.** Geometry is produced in sandboxed headless
   workers and published to the live document only after validation, under a
   transaction. The live process never runs user/AI code.
5. **The AI is the only modeler; the human is the only judge.** Humans steer
   via chat and sliders, accept or reject; they never push geometry buttons.

## Open questions

- How assemblies-of-parts compose in a single project script (sub-scripts?
  imports? one flat script?) — Phase 2 design work.
- Where the boundary between "parameter" (slider, no AI) and "change request"
  (chat turn) sits for things like suppressing a feature.
- Whether the Qt shell is retired outright or kept headless-only as an
  engineering harness after Phase 7.
