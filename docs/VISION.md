# VISION.md — What Cadex Is Becoming

Verified against source: 2026-09-05

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
- **Robotics-class dynamics and control on MuJoCo** — the mechanism you
  designed falls, collides, is actuated, exports as MJCF with *exact* OCCT
  inertias, and plays back a policy trained on it. MuJoCo is a kernel we
  keep, like OCCT (ADR-075). This shipped on a branch of its own until
  2026-08-01 and is now simply part of the product (ADR-102).

Until the replacements land, both forks remain the working substrate, and
since ADR-030 both live **in this repository**: the engine at the root, the
shell under `shell/`. Replacing either is unscheduled and unblocked; what is
live is deleting from both, in place. The staging is in `docs/ROADMAP.md`;
every resting place in it is shippable.

**What the last claim buys, concretely.** "Design me a quadruped and teach it
to walk" is a sequence of chat turns that terminates in a viewport playing a
learned gait: the mechanism is designed through the ordinary assembly
surface, `assembly.mjcf` exports it, `assembly.task` defines the problem,
`training/cadex_train.py` solves it on a machine we do not ship to,
`assembly.policy` verifies what comes back, and `assembly.rollout` plays it.
That arc closed on 2026-07-31 (ADR-085), and has since been rehearsed
end to end on one CPU-only desk machine at toy scale (ADR-170,
`docs/MUJOCO.md` §7b). Its full form is the product's North Star — *"design
me a quadruped robot, all 3D-printable, MG90 servos, and train it to walk
and wave"*, one prompt ending in a part sheet, print files, a BOM, a policy
and a gait video — and 0.1.0 roughly means that sentence works.

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
  shell: `shell/scripts/startup/mesh_agent/` plus the
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

Seven capability areas — four modeling, the sketcher they rest on, and the
two that make a mechanism move (ADR-075, ADR-086):

1. **Part** — direct OCC shape modeling.
2. **Part Design** — sketch-based feature modeling (bodies, pads, pockets…).
3. **Sketcher** — the constraint solver the other two build on.
4. **Assemblies** — links, joints, solved placements, motion.
5. **Mesh** — import, tessellate, boolean, decimate (Phase 4, ADR-016).
6. **Dynamics** — mass, inertia, gravity, contact and force, on MuJoCo
   (Phase 14, ADR-077). Not a replacement for area 4's kinematics but its
   complement: kinematics prescribes motion and reports where things end up,
   dynamics is given inertia and forces and reports what the mechanism
   actually does. Both exist; `api.motion` and `api.dynamics` are siblings,
   and a script uses one, the other, or a policy rollout — never two.
7. **Control** — task definitions, offboard training, and trained policies
   rolled out in-engine (`docs/MUJOCO.md` M5–M8; ADR-081, ADR-083, ADR-084,
   ADR-085). This is the genuine direction change: Cadex is a robot design
   *and* control tool.

Areas 6 and 7 add **no sixth domain**: they are operations on the `assembly`
domain, which is why they cost no protocol op, no new output type and no
`shell/` diff. Seven capability areas, still five domain APIs.

**Areas 6 and 7 shipped on a separate branch until 2026-08-01** and are now
part of the one product (ADR-102). The split existed to keep a bracket
modeller from paying for a physics engine; measured, that cost is 53.5 MB on
a 3.3 GB application and nothing at all at runtime, which did not justify a
second branch. What the merge did *not* dissolve is the boundary underneath
it: dynamics is engine-side, the shell never learns MuJoCo exists, and
training happens on a machine we do not ship to.

**Correction worth stating plainly:** this list used to promise "real mesh
editing arrives with the Blender shell (BMesh)". The Blender shell arrived;
that did not. ADR-030 deleted the local bpy modes, which were the only code
in the shell that authored geometry with BMesh, because a second authoring
path contradicts "nothing happens outside the script". Interactive mesh
editing is therefore unscheduled and would have to arrive as engine ops, not
as shell tools.

**And that is how it arrived** (ADR-127, 2026-08-05). Not as BMesh, and not
as editing: a shape is a `cage(...)` of superellipse rings the script
declares, `part.loft_cage` builds, and `set_params(cages=[...])` sets. The
shell draws those rings as an overlay and supplies the *gesture* — drag a
ring, press Apply — while the script stays the only thing that authors
geometry. The prediction in the paragraph above held exactly: engine ops, on
a declared table. `docs/ORGANIC.md` is the arc, and O4 (subD) is the part
that is still unscheduled.

Everything else FreeCAD offers (FEM, CAM, TechDraw, BIM, Draft, Points,
Robot, Spreadsheet, …) is out of scope. Deleted in the VibeCAD teardown at
the runtime level; the remaining source trees are slated for removal
(`docs/FREECAD.md`).

**And FEM arrived the same way mesh editing did** (ADR-145, 2026-08-11). Not
as a workbench, and not as a solver you drive: `part.stress(...)` is one
primitive on the part domain that takes an ADR-029 selector for what holds
the part, a list of loads, four declared material properties with their units
in their names, and an element budget — and publishes a **safety factor and
no geometry**, exactly as `part.measurement` publishes a dimension. Three
facts make that honest rather than a walk-back:

- **Nothing is being resurrected.** FreeCAD's `Fem` tree was *deleted*, not
  disabled — 3,589 files in commit `e85fe5ea` — so there is no workbench
  here to switch back on. This is new Cadex surface that happens to compute
  the same physics.
- **There is no sixth domain.** It is one operation on `part`, so by the test
  the line above sets for scope it costs no protocol op, no new
  `artifact_kind` and no `shell/` diff. The count of domains is still five.
- **The expensive half stays offboard.** Topology optimisation, refinement
  sweeps, CalculiX as a second opinion and load cases measured off a MuJoCo
  rollout all live in `analysis/`, which is not the engine and never will be
  (ADR-141). What came in is the single linear solve that a *rebuild* needs
  in order for a verdict to follow its part — and it is pinned equal by test
  to the offboard implementation that was verified against a closed form and
  against CalculiX.

The prediction in the mesh-editing paragraph above held again: engine ops, on
declared inputs, with the script still the only thing that authors geometry.
`docs/STRUCTURAL.md` is the arc.

**Interchange is in scope and first-class.** A parametric CAD app that
cannot emit STEP is not a product; STEP import/export is an engine
deliverable (Phase 11), not a shell convenience (ADR-025). **MJCF export is
the same commitment on the dynamics side** and it is already built
(ADR-081): `assembly.mjcf` writes one self-contained file that loads in a
stock MuJoCo which cannot import Cadex, and verifies its own output before
returning it.

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
- **A second provider stack.** The shell delegates the model loop and
  authentication to the user's installed agent CLI: Claude Code, Codex, or pi
  (ADR-174/175). Cadex has no API-key entry or provider SDK stack. Its harness
  and model selectors expose those CLIs' own account state and model catalogs;
  sign-in runs through the chosen CLI (ADR-184). The headless `cli/` client
  remains Claude-only.

  The shell and the headless CLI each orchestrate their own turns (ADR-061).
  Neither states the xscript API: both ask the engine through `describe_api`,
  and the headless CLI generates tool schemas from `OP_ARG_SPECS`.
- **Dependence on FreeCAD or Blender.** OCCT stays as the geometry kernel,
  and so does **MuJoCo** as the dynamics kernel — a dependency in the OCCT
  category, kept upstream and unmodified rather than forked (ADR-075).
  What we fork we intend to replace; what we keep, we keep.
  Vendored LGPL components (OCCT, planegcs, OndselSolver, `modelRefine`)
  keep their attribution obligation in the NOTICE file, as does MuJoCo's
  Apache-2.0 (`docs/PROVENANCE.md` §4); "references to
  neither" applies to dependencies, API names and runtime, and never to
  attribution (ADR-025).

## Guiding principles

1. **Elegance and simplicity.** Prefer the design that removes a concept over
   the one that adds a switch.
2. **Remove more than we add.** Subtractive change in `src/Mod/cadex/**`,
   `cli/**` and docs is encouraged, not merely permitted (policy in
   `AGENTS.md`; every removal logged in `docs/DECISIONS.md`).
3. **The script is the truth; everything else is a cache.** Any state that
   can't be rebuilt from the script is a bug.

   **One exception, stated rather than smuggled: a trained policy is an
   asset, not a derivation** (`docs/MUJOCO.md` §3.1, ADR-084). Weights come
   out of hours of stochastic GPU compute on a machine we do not ship to.
   They cannot be rebuilt from a script and never will be, so they live in
   `assets/` beside an imported STL, referenced by name and sha256, while the
   script declares reproducibly *how* the policy was trained and the engine
   verifies the file against that declaration before it publishes anything.
   The property that actually matters survives intact: **a rollout of a fixed
   policy on a fixed model is deterministic**, and its trace digest joins the
   project digest like every other artifact (ADR-068).
4. **Validated results only.** Geometry is produced in sandboxed headless
   workers and published to the live document only after validation, under a
   transaction. The live process never runs user/AI code. A policy is held to
   the same standard by different means: the engine re-computes the trainer's
   recorded **witness** with its own forward pass and refuses past a measured
   tolerance, so a policy whose weights arrived intact but whose architecture
   the engine reads differently is a refusal rather than a bad gait.
5. **The AI is the only modeler; the human is the only judge.** Humans steer
   via chat and sliders, accept or reject; they never push geometry buttons.

   **There is no train button, and there is nothing to press** (ADR-084).
   "No user-accessible modeling tools" is clear about fillet buttons and says
   nothing about a *train* button, which is not a modeling tool but would
   still be something a human presses. The question had to be answered before
   a UI could be built for it, and the answer is that training does not run
   in the engine and cannot — it needs JAX on a GPU — so the trainer is a
   program the agent copies to a machine that has one and runs with its own
   shell. The weights come home through `put_asset`, the path an imported STL
   already travels. No UI was built, no dispatch machinery, no protocol op:
   the answer is *recorded* rather than designed around. The agent authors
   the task, dispatches the run and declares the result; the human reads a
   viewport and says yes or no. What a trained policy adds to that loop is a
   thing to judge, not a control to operate.

## Open questions

- ~~How assemblies-of-parts compose in a single project script (sub-scripts?
  imports? one flat script?)~~ — answered 2026-08-09 (ADR-138): **none of the
  three.** A project stays one flat script, and it composes another project
  by importing that project's *accepted, verified output* — never its source
  as a second program. `link_part` pulls one accepted solid out of another
  project as a content-addressed `.cxpart` in this project's `assets/`, and
  `part.import_part` reads it back as the exact OCCT solid, along the path an
  imported STL already travels. The sandbox's refusal of every `import`
  statement turns out to be the right answer rather than an obstacle: what
  crosses a project boundary is a built artifact whose bytes are checked,
  carrying the source that built it as provenance, not a program this project
  has to run to find out what the other one means. Sub-scripts would have made
  a rebuild here depend on another project's current state; a container makes
  it deterministic from this project's own `assets/` alone.
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
- ~~Whether dynamics extends `api.simulation` or becomes a sibling
  `api.dynamics`~~ — answered 2026-07-30 (ADR-077): **a sibling authoring
  surface sharing the output type**, so the "exactly one simulation" rule
  covers both solvers and the shell never has to choose between two bakes.
- ~~Whether there is a **train** button~~ — answered 2026-07-31 (ADR-084):
  **no, and there is nothing to press.** Recorded in principle 5 above.
- **How a project migrates when the solver moves.** A retained artifact's
  digest is part of the project's identity (ADR-068), so a MuJoCo or OCCT
  upgrade makes an existing project refuse to open — and nothing tells the
  user that `open_project restore=false` and a re-accept is the way through.
  The rule is right; the migration path is missing.
- ~~Whether interactive mesh editing ever arrives, and if so as engine ops
  rather than shell tools~~ — answered 2026-08-05 (ADR-127): **as engine ops,
  on a declared table, with the shell supplying only the gesture.** A shape
  is a `cage(...)` of rings the script declares, `part.loft_cage` builds and
  `set_params(cages=[...])` sets; the shell draws those rings as an overlay
  and sends them on one button. Nothing is edited outside the script, the
  mesh domain gained no editing surface, and the rule under Scope stands
  unchanged. `docs/ORGANIC.md` is the arc.
