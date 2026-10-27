# VISION.md — What Cadex Is For

Verified against source: 2026-10-27

This document is the product vision, and it is authoritative: a change that
conflicts with it is wrong, or the vision changes first by an entry in
`docs/DECISIONS.md`. What exists today is `docs/ARCHITECTURE.md`; what comes
next is `docs/ROADMAP.md`. The longer vision this replaces, with its
answered open questions, is [`history/VISION-2026-10-16.md`](history/VISION-2026-10-16.md).

## The North Star

> **Describe a robot or mechanism to your agent; get back a design you can
> build and a policy that moves it.**

One conversation, carried by the person's own agent, ends in: exact
parametric geometry, print and machining files (STEP, STL), a bill of
materials, an MJCF model with exact inertias, a trained policy that passes
its task's success spec, and a film of it working. The person judges; the
agent does the work; Cadex makes the work checkable.

It is measured on a small **benchmark set**, one machine per kind of
problem, each started from an empty project by an agent driving `cadex mcp`
with no human help:

| | Brief | What it exercises |
|---|---|---|
| **B1 — printed servo robot** | *"Design me a quadruped robot, all 3D-printable, MG90 servos, and train it to walk and wave."* (the original North Star, kept) | printable parts, hobby servos, BOM, a small gait trained on a CPU |
| **B2 — QDD creature** | an articulated animal robot on quasi-direct-drive actuators that stands, walks, turns and runs | catalog drives within rated torque, closed linkages, covers that wrap the mechanism, gait references, GPU training |
| **B3 — non-legged machine** | a machine from [`MACHINES.md`](MACHINES.md), e.g. a gantry or a rover, doing its job | assembly kinematics, workspace and path tasks, a success spec that is not a gait |

A release is measured by how far each brief gets unattended, and where it
stops. B1 is the oldest and least recently exercised; B2 is where most work
since October 2026 has gone (the cat line: feline, leo, leon); B3 still lacks
a task vocabulary of its own.

## The product

Cadex is **three things and nothing else** (ADR-500):

1. **The engine**: a FreeCAD fork on OCCT that builds, verifies, measures,
   renders, simulates and exports a design from its script. `cadexd` runs
   the script in sandboxed workers and publishes only validated results.
2. **The dashboard** (`cadex app`): the only UI, and read-only (ADR-537).
   A person watches the design and its training there while their agent
   works.
3. **The agent bindings**: one MCP tool surface, one guidance text (a
   domain-neutral base plus optional named styles, ADR-560) and the `cadex`
   commands. Cadex has no agent of its own (ADR-538).

Offboard, beside the product and never shipped in it: the trainer
(`training/`, ADR-084) and structural analysis (`analysis/`, ADR-141).

## Principles

1. **Elegance and simplicity.** Prefer the design that removes a concept over
   the one that adds a switch.
2. **Remove more than we add.** Subtraction is normal work, logged in
   `docs/DECISIONS.md` and proved by build and tests.
3. **The script is the truth; everything else is a cache.** Every part,
   joint and parameter exists because a line of the one project script made
   it, and the full model rebuilds from it. The one stated exception is a
   trained policy: an asset in `assets/`, referenced by hash, whose training
   the script declares and whose weights the engine verifies.
4. **Validated results only.** Geometry is built in sandboxed workers and
   published only after validation; the live process never runs user or AI
   code. A policy is held to the same standard: the engine recomputes the
   trainer's witness and refuses a mismatch.
5. **The agent is the only modeller; the person is the only judge.** People
   steer by talking to their agent and judge in the dashboard. There are no
   modelling buttons, and no train button: the agent authors the task,
   dispatches training, and declares the result.
6. **Design follows function.** A machine should look like what it does.
   The guidance gives principles with a reason and a check, not fixed
   placements; styles add taste for a kind of machine and stay optional
   (`docs/DESIGN-LANGUAGE.md`).
7. **The cheap path stays cheap.** A declared parameter rebuilds without the
   agent (`cadex params`); a rebuild builds only the parts that changed.

## Scope

Seven capability areas on five domain APIs (part, partdesign, sketcher,
mesh, assembly):

1. **Part**: direct OCCT shape modelling, including organic lofts from
   declared cages (`docs/ORGANIC.md`) and a linear stress verdict per part
   (`docs/STRUCTURAL.md`).
2. **Part Design**: sketch-based features.
3. **Sketcher**: the constraint solver both rest on.
4. **Assembly**: links, joints, solved placements, kinematic motion, and
   the parts library (`lib`).
5. **Mesh**: import, tessellate, boolean, decimate.
6. **Dynamics** on MuJoCo: mass, inertia, contact, actuators, terrain, and
   MJCF export with exact OCCT inertias.
7. **Control**: tasks, gait references, success specs and evaluation;
   training happens offboard and the engine verifies and rolls out the
   policy.

Dynamics and control are operations on the assembly domain, not new
domains. Interchange is first-class: STEP, STL and MJCF go out; meshes and
other Cadex projects' accepted parts (`.cxpart`, ADR-138) come in. STEP
import, for manufacturer models, is not built yet.

Everything else FreeCAD offers (FEM workbench, CAM, TechDraw, BIM, Draft,
Spreadsheet, …) is out of scope and deleted or being deleted
(`docs/FREECAD.md`).

## Non-goals

- **Two of anything.** One engine, one UI, one script format, one tool
  surface. The Qt shell (ADR-021) and the Blender shell (ADR-498) are gone;
  the CLI and the dashboard are clients of one protocol.
- **Hands-on modelling.** No fillet button, sketch editor or ring drag. A
  change a person wants is something they tell their agent.
- **An agent, model loop, API key or provider SDK of its own** (ADR-538).
- **A FreeCAD distribution or compatible fork.** OCCT and MuJoCo are kernels
  we keep upstream; the FreeCAD application layer is ours to shrink.
- **Shipping training.** No JAX or MJX in the engine or its payload; the
  engine verifies a policy and never produces one (ADR-084).
- **A front-end toolchain.** No npm, bundler or framework in the dashboard.

## Parked directions

Available behind the test-pinned protocol, deliberately not started:

- **A replacement engine** (a direct OCCT binding, "Phase 11") and **a
  desktop app** (which would copy the dashboard).
- **Subdivision surfaces** for organic shapes (O4).
- **An interactive pose or joint gimbal** in the dashboard, if it can stay
  read-only with respect to the design (`docs/IDEAS.md`).

## Open question

- Where the line sits between a *parameter* (changed with `cadex params`,
  no agent) and a *change request* (asked of the agent), for things like
  suppressing a feature.
