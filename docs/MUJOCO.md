# MUJOCO.md — Dynamics, and the Road to a Trained Policy

Verified against source: 2026-07-30
Status: **M0 recorded (ADR-060), M1 passed.** M2 onward is plan, not built.
Branch `MJC`.

This is the framework for adding **rigid-body dynamics** to Cadex on
MuJoCo, and then following that capability all the way to its end: an agent
that takes a robot from an idea, through a designed mechanism, to a trained
control policy running on it.

`docs/VISION.md` is still authoritative. Where this plan extends the
product's scope it says so, and the extension is a decision the owner makes
in `docs/DECISIONS.md` (ADR-060, slice M0) — not something this document
grants itself.

Provenance: everything described here is `[Cadex-new]`. MuJoCo is a
dependency in the **OCCT category** — a kernel we keep, upstream and
unmodified — not a tree we fork. See "Why not a fork" below.

---

## 1. The thesis

Cadex already simulates. `assembly.simulation(...)` runs native
kinematics in the worker, retains a time-series trace under the schema
`cadex-assembly-simulation-trace-v1`, and publishes it as
`simulation_trace_preview` (ADR-048). The shell bakes that trace to
F-Curves in `cadex_animate.py` and plays it in the Simulation panel
(ADR-050).

That trace is a list of frames, and each frame is nothing but
`{frame_index, nominal_time_s, component_placements{name: placement}}`.

**It does not care what produced it.** A MuJoCo integration that emits the
same schema needs:

- no new op in `CadexdProtocol.OP_ARG_SPECS`
- no new response key, no new golden fixture shape
- no row in the `docs/INTEGRATION.md` op table
- no change to `mesh_agent` at all

The entire cost of getting dynamics onto the screen is engine-side, behind
a contract that already exists and is already test-pinned. That is an
unusually cheap seam, and it is the reason to do this now rather than after
Phase 11 or 12. The same seam carries the whole arc: a *policy rollout* is
also just a trace.

**What MuJoCo adds that Ondsel cannot.** Today's simulation is
*kinematics* — you prescribe motion with `api.motion` formulas of `time`
and the solver tells you where everything ends up. There is no mass, no
gravity, no contact, no force, no actuator. MuJoCo is the *dynamics*
answer to the same question: given inertia and forces, what does the
mechanism actually do. They are complements, and both should exist.

**What Cadex adds that the robotics world does not have.** Standard MJCF
authoring guesses inertia from convex hulls or hand-tunes it. We have the
BREP. Exact `GProp_GProps` mass properties into `<inertial>` is close to
free for us and is the part everyone else gets wrong.

---

## 2. Verified facts

Checked 2026-07-30 against conda-forge, the MuJoCo docs, and this tree.

| Question | Answer |
|---|---|
| Package | `mujoco-python` **3.10.0** (conda-forge, 2026-06-22), Apache-2.0 |
| Platforms | all five pixi platforms, including `osx-arm64` |
| Python/numpy fit | an `np2py311` build exists depending on `numpy >=1.23,<3` — **compatible** with our `python >=3.11,<3.12` and `numpy >=1.26,<1.27` pins. No conflict. |
| Payload cost | **53.5 MB**, measured (ADR-061). The conda package is ~14 MB, but what we ship is the pypi wheel, which bundles the plugin dylibs conda-forge splits out. |
| Unwanted deps | pulls `glfw`, `pyopengl`, `pyglfw`, `absl-py`, `etils`, `fsspec`. The GL ones are for `mujoco.viewer` only; core `import mujoco` must not need them, and the payload should prune them (slice M0). |
| Model construction | **`mjSpec`** — programmatic build (`spec.worldbody.add_body(...)`, `spec.compile()`), one-to-one with MJCF. No XML string-building layer needed. |
| Determinism | deterministic for a **fixed binary, fixed platform, single-threaded**. Explicitly **not** bitwise-reproducible across versions — MuJoCo's own `VERSIONING.md` says so. Multi-threaded island solving has open reproducibility issues upstream. |
| Licence flow | Apache-2.0 → engine LGPL-2.1**+**. The "+" is doing the work: Apache-2.0 is incompatible with LGPL-2.1-*only* and compatible with the v3 family. Clean, and it is a Python import in a payload-carried conda package like every other. NOTICE gets an entry. |

**Correction to the earlier estimate:** the payload cost is ~14 MB, not
"tens of MB." It is cheaper than expected.

### Joint mapping

MuJoCo has exactly four joint types — `free`, `ball`, `slide`, `hinge` —
plus equality constraints (`connect`, `weld`, `joint`, `tendon`, `flex*`).
Our thirteen map in three groups:

| Group | Cadex joints | How |
|---|---|---|
| **Direct** (5) | `fixed`, `revolute`, `slider`, `ball`, `cylindrical` | no joint / `hinge` / `slide` / `ball` / `hinge`+`slide` on one axis |
| **Coupled** (4) | `screw`, `gears`, `belt`, `rack_pinion` | two joints plus `equality/joint` polynomial coupling |
| **No equivalent** (4) | `distance`, `parallel`, `perpendicular`, `angle` | these are *placement* constraints, not runtime ones. **Refuse with a sentence.** |

**Loops.** Our assembly graph is a constraint graph and may contain loops;
MuJoCo is a kinematic *tree* plus equality constraints. A four-bar becomes
a tree with `equality/connect` closing the loop. Tree extraction — picking
the spanning tree and deciding which joints become closures — is the single
hardest piece of slice M2.

---

## 3. Three tensions to resolve before code

### 3.1 A trained policy is not rebuildable from the script

VISION principle 3: *the script is the truth; everything else is a cache.
Any state that can't be rebuilt from the script is a bug.* A policy is tens
of megabytes of weights produced by hours of stochastic GPU compute. It
cannot be rebuilt from a script, ever, and pretending otherwise would be a
lie the tests eventually catch.

**Resolution: a policy is an asset, not a derivation.** The project store
already has `assets/` — a name-checked, sha256'd, 128 MB-budgeted directory
that `put_asset` writes and `_stage_project_assets` hardlinks into the
worker. A policy lives there exactly as an imported STL does. The *script*
declares reproducibly how it was trained — model revision, task definition,
seed, hyperparameters — and references the resulting weights by name and
digest. The weights are carried as data.

This keeps the property that matters: **a rollout of a fixed policy on a
fixed model is deterministic**, so trace digests still hold even though the
training run does not.

### 3.2 Units

FreeCAD is millimetres. MuJoCo is nominally unitless but every default it
ships — gravity, contact stiffness, solver reference values — assumes SI
metres and kilograms. Get this wrong and a part falls at 9810 mm/s²
through the floor while looking entirely plausible on screen.

**Resolution:** one conversion boundary, one function, its own test, and
the script surface speaks whichever unit we choose *once* and never
negotiates. This is the highest-probability silent failure in the whole
plan; it gets a test before it gets a feature.

### 3.3 Scope, and the ADR

VISION lists five capability areas and dynamics is not one of them.

- Slices **M1–M4** are defensible as living inside "Assemblies — links,
  joints, solved placements, **motion**." They extend ADR-048 rather than
  redirecting the product.
- Slices **M5–M8** — task definitions, reward functions, training,
  policies — are a **product direction change**. Cadex becomes a robot
  design *and* control tool. That is a real and probably good expansion,
  and it is the owner's call, recorded in an ADR before a line is written.

The ADR is cheap. Drifting into a robotics simulator without one is not.
It also has to answer a UI question the current principles do not: "no
user-accessible modeling tools" is clear, but a **train** button is not a
modeling tool and the human has to be able to press something.

### Why not a fork, and why not a new repo

**New repo: no.** ADR-030 merged two repos into one; "two of anything" is a
VISION non-goal; Phase 13a *deleted* the cross-repo payload machinery. A
new repo recreates precisely what was just removed and buys nothing.

**Fork MuJoCo: no.** Apache-2.0, actively developed, and its extension
points (`mjSpec`, the plugin system for custom sensors/actuators/forces)
are exactly what a fork would be for. We fork FreeCAD and Blender because
we are *replacing* them. MuJoCo we keep.

**Branch in this repo, engine-side: yes.** `mujoco-python` joins
`pixi.toml` exactly pinned, for the same reason `occt == 7.8.1` is exactly
pinned. Code lands under `src/Mod/cadex/`. Nothing in `shell/` ever imports
mujoco — a physics authoring path in the shell would violate "nothing
happens outside the script" the same way the deleted bpy modes did.

---

## 4. The slices

Numbered **M0–M8** to avoid colliding with ROADMAP's phases. The whole
sequence is a candidate ROADMAP Phase 14 once ADR-060 lands. Every slice is
a resting place: the product works at the end of each one.

---

### M0 — Decide, depend, deliver `(ADR-060, ADR-061)`

The paperwork slice, and it was not as small as billed.

ADR-060 records the direction: dynamics is in scope, MuJoCo is the engine,
MuJoCo is a kept dependency and not a fork, and M5–M8 either are or are not
approved. `mujoco-python` is added to `pixi.toml` **exactly pinned**, with
the ADR-025-style comment explaining that the pin is exact because MuJoCo's
own versioning policy disclaims cross-version numerical reproducibility and
we assert digest equality on every project open. The payload build learns
to prune `glfw`/`pyopengl`, and the payload smoke test grows one line
proving `import mujoco` works in a tree with no GL at all.

What actually happened: the dependency could not be added at all. Adding any
conda package forces a full re-solve, and the manifest has not been
re-solvable for some time — conda-forge moved past `occt ==7.8.1` and
`qt6-main <6.9`, which we hold on purpose. `pixi.lock` has been carrying it.
So MuJoCo arrives as a pypi wheel, and `relocate_conda_environment.py` gains
`CARRIED_PYPI_PACKAGES` to carry it into the payload by name (ADR-061). The
GL prune the slice planned turned out to be unnecessary — the wheel imports
no GL module at all.

**The manifest is now a known, written-down problem** and not this slice's
to fix: repairing it means re-pinning the environment that builds geometry,
which moves accepted digests. `CARRIED_PYPI_PACKAGES` is named so that the
day it is repaired, the exception is easy to find and delete.

**Done when:** `pixi run stage-engine` produces a payload whose own
`bin/python` imports mujoco at the pinned version — asserted by the payload
build itself, because a source tree that passes proves nothing about a
payload (ADR-023). *Not yet run end to end: staging copies a 4.2 GB
environment and this machine has 4.5 GB free. The carrying logic, the rpath
survival and the import are each verified in isolation; the full stage is
outstanding.*

---

### M1 — Prove the seam in a day `(PASSED 2026-07-30)`

Deliberately throwaway. Build a mechanism in MuJoCo, step it, emit a
`cadex-assembly-simulation-trace-v1`, and feed it to `cadex_animate`.

A **double pendulum**, not a falling box: its links pass through full
rotations, so the trace exercises the quaternion-hemisphere flip that
`cadex_animate` documents as one of its five silent failure modes. A seam
proven on a box proves much less.

**Result: passed, with an empty `shell/` diff.** Both halves — the pure one
without bpy, and `apply()` inside the built `Cadex.app` — accepted a
MuJoCo-produced trace unmodified. 2 components, 121 frames, 1694 keyframes
baked; the played pose matches the trace to **8e-6 mm** and **3.8e-8** on
orientation; the Simulation panel's scene flag appears. `pixi run gate`
stays `ok: true` (picking 372/372, slider median 0.489 s).

The central claim of this document holds: the shell already knows how to
play a MuJoCo simulation, and does not know that it does.

**Four contract details M2 must honour**, all found here rather than
guessed:

- **There is a solved frame at `start_time`, and it is not the input
  frame.** The engine emits `frame_kind: "input"` with a null time *and* a
  `solver_output` whose `nominal_time_s` is
  `start + (frame_index - 1) * step` — so the first solved sample sits at
  `start_time` and lands on Blender frame 1. Stepping before emitting the
  first sample puts the entire run one frame late, and nothing errors. This
  was M1's one failure, and finding it is the slice paying for itself.
- **Units.** MuJoCo integrates in metres; the field is literally
  `position_mm` and the shell treats 1 BU as 1 mm. ×1000, at one boundary.
- **Quaternion order.** MuJoCo's `data.xquat` is wxyz; the trace field is
  `rotation_xyzw`.
- **Sampling rate is part of the contract, not a display setting.**
  `_continuous` repairs a hemisphere flip only when it can still see one. A
  link rotating more than half a turn between trace samples is aliased, and
  no amount of de-flipping recovers it.

**Size, measured:** ~191 bytes per component-pose. The 64 MB trace cap is
therefore worth ~335 000 poses and the API's 100 000-pose cap binds first —
so M3's budget work is about the API limit, not the byte limit.

---

### M2 — `assembly` → `mjSpec`

The real builder, and the largest single piece of engineering in M1–M4.

Walk the assembly `DomainValue` graph and construct an `MjSpec`: bodies
from components, the spanning tree extracted from the joint graph, loop
closures as `equality/connect`, the five direct joint mappings, the four
coupled ones as `equality/joint`. The four unmappable joint kinds are
refused with a sentence in the house style, naming which joint and why.

Collision is **primitives only** at this slice — box, capsule, cylinder,
sphere. No meshes. This is not a limitation to apologise for; it is what
good MJCF authoring does anyway, and it defers the convexity problem to
where it belongs.

Inertia comes from OCCT. This is the differentiator and it lands here.

**Done when:** a mechanism that today runs as kinematics also runs as
dynamics and lands in roughly the same place under prescribed motion —
kinematics parity is the check that the model was built correctly.

---

### M3 — Dynamics for real

Gravity, mass, restitution, friction, contact parameters. The units
boundary from §3.2 gets built and tested here, first.

Mesh collision arrives via convex decomposition, because a bracket with a
slot silently becoming a solid block is a wrong answer that looks right.
The existing `part.cable` obstacle handling already has the "mesh obstacles
are bounding boxes" wart recorded in ROADMAP; this is the same class of
problem and should not get the same workaround.

The determinism gate lands: same script, same params → identical trace
digest across cadexd restarts, with MuJoCo forced **single-threaded**
because upstream has open reproducibility issues with island parallelism.

The frame budget gets revisited. `api.simulation` caps at 10 000 frames /
100 000 component-pose samples, and `time_step_s` currently means both
solver step and trace step. Dynamics wants those separate — 2 kHz solver,
60 Hz trace.

**Done when:** a thing falls over correctly, and does so identically twice.

---

### M4 — Actuators and closed loop

MuJoCo's actuator vocabulary (`motor`, `position`, `velocity`, `general`,
`muscle`, …) becomes an xscript surface. A control callback runs in the
worker, so a PD controller or a scripted trajectory can drive the mechanism
rather than a formula prescribing it.

This is the last slice that is unambiguously *CAD*. Everything after it is
robotics, and M0's ADR should have already said whether we are going there.

**Done when:** a script can specify a motor and a setpoint, and the arm
holds position against gravity.

---

### M5 — The model leaves the building

MJCF export as a first-class engine op, alongside STEP (VISION: "a
parametric CAD app that cannot emit STEP is not a product" — the same
argument applies here).

**This slice is worth shipping even if M6–M8 never happen.** "Design a
mechanism in Cadex, export MJCF with exact OCCT inertias" is a
differentiated capability on its own, because MJCF is the de-facto robot
description format and correct inertia is the universally botched part. It
is also the cheapest possible version of the whole idea: no solver loop, no
determinism problem, no contact tuning.

Everything downstream consumes this artifact, which means M6–M8 are
building on a thing that is independently useful and independently tested.

**Done when:** exported MJCF loads in stock MuJoCo and matches the
in-engine simulation.

---

### M6 — A task is part of the script

Training needs more than a model: observation space, action space, reward,
termination, episode length, domain randomisation. All of it is
declarative, all of it belongs in the project script, and none of it is
geometry.

This is the slice where the xscript language grows a genuinely new concept,
and it deserves design time rather than a first guess. The constraint that
saves us: it is all *data*, and the script is already the sole source of
truth for data.

**Done when:** a script fully specifies a trainable task, and the spec
round-trips into a training-ready bundle.

---

### M7 — Training happens elsewhere

**The honest constraint:** training does not run on the user's laptop.
MJX needs JAX-on-GPU, and JAX's Apple Silicon story in 2026 is `jax-metal`
0.1.0 plus two community MPS backends with known compatibility problems.
MuJoCo Warp needs CUDA. The published reference — a Unitree G1 walking
policy converging in ~90 minutes — is 4096 parallel environments on an RTX
4090. On CPU that is days.

So training is **offboard by design**, and that turns out to be a clean
boundary rather than a compromise: the engine stays a geometry-and-dynamics
service, the shell stays a viewer, and the training bundle from M6 goes to
a machine that has a GPU. The agent's job is to author the task, dispatch
the run, and interpret what comes back.

The likely stack is MJX / MuJoCo Playground with PPO, because that is what
the reference results are measured on and sim-to-real is its explicit
purpose. Whether we vendor a training harness or shell out to an existing
one is an M7 design decision, not a commitment made here.

**Done when:** a task defined in M6 trains to a policy on a remote GPU, and
the policy artifact lands in the project store with a digest.

---

### M8 — The policy comes home

The loop closes, and it closes on the same seam it opened on.

A trained policy is loaded from the project store, rolled out in-engine
against the M2 model, and the rollout is emitted as
`cadex-assembly-simulation-trace-v1`. The shell plays it with the code it
has had since ADR-050.

At which point the agent can be asked for a robot, and answer with one that
walks.

**Done when:** "design me a quadruped and teach it to walk" is a sequence
of chat turns that terminates in a viewport playing a learned gait.

---

## 5. Known hazards

Ranked by how quietly they fail.

1. **Units** (§3.2). Silent, catastrophic, and the whole plan's most likely
   own-goal. Tested first, in M3.
2. **Convexity.** MuJoCo hulls collision meshes without complaint. Wrong
   contacts that look plausible. M3.
3. **Cross-version drift.** MuJoCo disclaims numerical reproducibility
   across releases and we assert digest equality on every project open.
   Exact pin, M0 — and a version bump is a deliberate, digest-moving event
   like an OCCT bump, not a routine update.
4. **Multi-threading.** Island parallelism has open upstream reproducibility
   issues. Single-threaded until proven otherwise. M3.
5. **Loop extraction.** Which joints become tree edges and which become
   equality constraints is not always obvious, and a bad split produces a
   model that simulates but drifts. M2.
6. **Frame budget.** The 10 000-frame cap was sized for kinematics. An RL
   rollout blows through it. M3.
7. **Scope creep into a UI.** M5–M8 want buttons — train, stop, load
   policy — and "no user-accessible modeling tools" does not obviously
   answer whether those are allowed. ADR-060 should.

## 6. Open questions

- Does the script surface speak millimetres (consistent with the rest of
  Cadex) or metres (consistent with MuJoCo defaults)? One of them requires
  conversion at the boundary; the other requires it everywhere the user
  looks.
- Does dynamics extend `api.simulation` or become a sibling `api.dynamics`?
  The trace schema is shared either way; the question is whether the
  *authoring* surfaces should be.
- Where does the training run — a service we operate, or the user's own
  GPU box under their credentials? M7 has to answer this and it is as much
  a product question as a technical one.
- Does the policy asset extend `put_asset` (which today gates extensions to
  STL/OBJ/PLY) or get its own op?
- Is there a Phase 11 story here? A pybind11 binding over OCCT and a
  MuJoCo integration are independent, but the `assembly` domain is
  Phase 11f — the largest — and this plan puts new weight on it.
