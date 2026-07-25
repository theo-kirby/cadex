# VISION.md — What Cadex Is Becoming

Verified against source: 2026-07-25

This document is the product vision. It is authoritative: when a change
conflicts with this document, the change is wrong or the vision needs an
explicit decision in `docs/DECISIONS.md`. What exists **today** is documented
in `docs/ARCHITECTURE.md`; the path from here to there is `docs/ROADMAP.md`.

## The product

One ultimate agentic CAD app — **one application we own**, a derivative of
but not dependent on either FreeCAD or Blender (ADR-025), combining:

- **FreeCAD-class capability** — real parametric BREP modeling **on OCCT**.
  OCCT is the kernel and it stays; FreeCAD is the application layer around
  it, and that layer is being removed.
- **Blender-class UX** — the look, feel, viewport and interaction quality of
  the `/Users/theo/mesh` prototype, rebuilt as our own Rust + wgpu + egui
  shell. Blender is the reference, not the host.
- **The xscript methodology** — the AI authors a declarative Python program;
  the program is the model.

Until the replacements land, both forks remain the working substrate: this
repository is the engine and `/Users/theo/mesh` is the shell. The staging is
in `docs/ROADMAP.md`; every resting place in it is shippable.

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
  detailed in `docs/BLENDER.md`. That prototype is the **specification** for
  the Rust shell, not its permanent home (ADR-025).
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

**Interchange is in scope and first-class.** A parametric CAD app that
cannot emit STEP is not a product; STEP import/export is an engine
deliverable (Phase 11), not a shell convenience (ADR-025).

## Non-goals

- A general-purpose FreeCAD distribution or a FreeCAD-compatible fork.
- Manual CAD workflows of any kind; feature parity with FreeCAD's UI.
- Supporting all FreeCAD workbenches, file formats, or addons.
- Multi-engine scripting (build123d, OpenSCAD — retired in the teardown).
- **Two of anything in the finished product**: one shell, one engine, one
  script format, one document, one model loop, one installer. The Qt/Coin3D
  shell was interim and was deleted in Phase 7 (ADR-021). The Blender shell
  is the working substrate until the Rust shell replaces it (ADR-025) — the
  Rust shell is not a second shell, it is the first one we own, and the
  Blender fork is deleted when it lands.
- A second model loop. The AI runs as the Claude Code CLI inside the shell;
  there is no API-key provider path (ADR-020).
- **Dependence on FreeCAD or Blender.** OCCT stays as the geometry kernel.
  Vendored LGPL components (OCCT, planegcs, OndselSolver, `modelRefine`)
  keep their attribution obligation in the NOTICE file; "references to
  neither" applies to dependencies, API names and runtime, and never to
  attribution (ADR-025).

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
- ~~Whether the Qt shell is retired outright or kept headless-only as an
  engineering harness after Phase 7~~ — answered 2026-07-25 (ADR-020/021):
  **retired outright**, together with the provider stack it served. This
  repository is the engine; it builds no application.
- ~~How far the local (mesh-native) modes and the one-project-script model
  should converge~~ — answered 2026-07-25 (ADR-025 decision 3): **the local
  modes are deleted.** One script format, one source of truth; ADR-020
  decision 5's knowing exception is resolved rather than carried.
- ~~Whether parameter sliders count as "human edit controls"~~ — answered
  2026-07-25 (ADR-025): **no.** Principle 5 has humans steer via chat *and*
  sliders; sliders move declared parameters, they do not author geometry.
- **The time shape of the FreeCAD replacement.** Not knowable before Phase
  10's enumeration probe and characterization time-box. The binding is
  weeks; the characterization corpus is the unknown that sets the scale.
- macOS notarization of a Rust app bundling an OCCT engine that spawns
  subprocesses (inherited open item, ADR-023).
