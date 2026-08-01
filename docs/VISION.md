# VISION.md — What Cadex Is Becoming

Verified against source: 2026-07-31

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
  the shell under `shell/`, in the long run rebuilt as our own Rust + wgpu +
  egui shell. Blender is the reference, not the permanent host.
- **The xscript methodology** — the AI authors a declarative Python program;
  the program is the model.

Until the replacements land, both forks remain the working substrate, and
since ADR-030 both live **in this repository**: the engine at the root, the
shell under `shell/`. Replacing either is unscheduled and unblocked; what is
live is deleting from both, in place. The staging is in `docs/ROADMAP.md`;
every resting place in it is shippable.

### Everything is driven by the script

- **Nothing happens outside the script.** Every feature, part, assembly, and
  parameter exists because a line of the project script created it. There are
  no side-channel edits, no direct document mutations, no "quick manual fix"
  paths.
- **The exact full state is rebuildable from the script at any time.** The
  document/scene is a cache. Delete it, re-run the script, and you get a
  byte-equivalent model back. This property is testable and must stay
  testable (Phase 2 exit criterion in `docs/ROADMAP.md`).
- **One project script** is THE user-visible artifact and sole source of
  truth. It composes all five domain APIs (partdesign, sketcher, part, mesh,
  assembly); parameters are declared at the top and surface as sliders. This
  is what the runtime does today — it landed in Phase 2 (ADR-011…014) and the
  per-domain multi-program surface it replaced is gone. See
  `docs/XSCRIPT.md`.

### The interface

- **Left half: viewport. Right half: chat, parameter sliders, model tree,
  script view.** That's the whole app. The UX north star is the working
  shell: `shell/scripts/addons_core/mesh_agent/` plus the
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

Five capability areas — four modeling, plus the sketcher they rest on:

1. **Part** — direct OCC shape modeling.
2. **Part Design** — sketch-based feature modeling (bodies, pads, pockets…).
3. **Sketcher** — the constraint solver the other two build on.
4. **Assemblies** — links, joints, solved placements, motion.
5. **Mesh** — import, tessellate, boolean, decimate (Phase 4, ADR-016).

**Correction worth stating plainly:** this list used to promise "real mesh
editing arrives with the Blender shell (BMesh)". The Blender shell arrived;
that did not. ADR-030 deleted the local bpy modes, which were the only code
in the shell that authored geometry with BMesh, because a second authoring
path contradicts "nothing happens outside the script". Interactive mesh
editing is therefore unscheduled and would have to arrive as engine ops, not
as shell tools.

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
  script format, one document, one installer. The Qt/Coin3D shell was interim
  and was deleted in Phase 7 (ADR-021). One repository since ADR-030. The
  Blender shell is the working substrate until the Rust shell replaces it
  (ADR-025) — the Rust shell is not a second shell, it is the first one we
  own, and `shell/` is deleted when it lands.

  **The headless CLI is the one exception, and it is deliberate** (ADR-061).
  `cli/` is a second *front end*: no shell, no window, and no second engine,
  script format or document — the same project script, driven from a
  terminal. It earns the exception by doing something a window cannot,
  which is to be scripted: one expensive turn authors a parametric model,
  and a cheap loop then sweeps it under an external simulator with no model
  in the loop at all. Interactive design and batch design are different
  jobs, and one program that did both would serve neither.
- **A second provider stack.** The AI is the Claude Code CLI — in the shell
  and in `cli/` alike. There is no API-key path, no model picker, no
  provider abstraction (ADR-020).

  What this does *not* forbid, since ADR-061, is a second **turn
  orchestration**: the shell and the CLI each spawn `claude -p` from their
  own code, because one is a chat window and the other is a process with an
  exit code. That is a real duplication and the ADR says so plainly. What
  keeps it from becoming drift is that neither of them states the xscript
  API — both ask the engine through `describe_api` — and that the CLI's tool
  schemas are generated from `OP_ARG_SPECS` rather than written. A third
  front end would need the same discipline or it should not be built.
- **Dependence on FreeCAD or Blender.** OCCT stays as the geometry kernel.
  Vendored LGPL components (OCCT, planegcs, OndselSolver, `modelRefine`)
  keep their attribution obligation in the NOTICE file; "references to
  neither" applies to dependencies, API names and runtime, and never to
  attribution (ADR-025).

## Guiding principles

1. **Elegance and simplicity.** Prefer the design that removes a concept over
   the one that adds a switch.
2. **Remove more than we add.** Subtractive change in `src/Mod/cadex/**`,
   `cli/**` and docs is encouraged, not merely permitted (policy in
   `CLAUDE.md`; every removal logged in `docs/DECISIONS.md`).
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
  **retired outright**, together with the provider stack it served. (What
  followed: for three months this repository built no application at all;
  since ADR-030 it builds the whole one, engine and shell.)
- ~~How far the local (mesh-native) modes and the one-project-script model
  should converge~~ — answered 2026-07-25 (ADR-025 decision 3): **the local
  modes are deleted.** Decided there, *done* in ADR-030: `cad_api.py`,
  `validation.py`, `scene_graph.py`, the mode registry and the dropdown are
  gone. One script format, one source of truth.
- ~~Whether parameter sliders count as "human edit controls"~~ — answered
  2026-07-25 (ADR-025): **no.** Principle 5 has humans steer via chat *and*
  sliders; sliders move declared parameters, they do not author geometry.
- **The time shape of the FreeCAD replacement.** Not knowable before Phase
  10's enumeration probe and characterization time-box. The binding is
  weeks; the characterization corpus is the unknown that sets the scale.
- macOS notarization of a Rust app bundling an OCCT engine that spawns
  subprocesses (inherited open item, ADR-023).
