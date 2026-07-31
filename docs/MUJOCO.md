# MUJOCO.md — Dynamics, and the Road to a Trained Policy

Verified against source: 2026-07-31
Status: **M0 recorded (ADR-060, ADR-061), M1 passed, M2 closed (ADR-062),
M3 closed (ADR-064), M4 closed (ADR-065), M5 closed (ADR-066), M6 closed
(ADR-069), M7 closed (ADR-070).** M8 is plan, not built.

**Branch `MJC`, permanently (ADR-063).** This file, and everything it
describes, exists on `MJC` and not on `main`. The branch is not awaiting a
merge window: a user who is not going to simulate a mechanism should not
build a physics engine or ship 53.5 MB of one. Changes flow `main` → `MJC`
and never back; ADR-063 lists what a sync must not drop, and why a branch
was chosen over a `WITH_DYNAMICS` build flag.

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
| **Coupled** (4) | `screw`, `gears`, `belt`, `rack_pinion` | `equality/joint` between coordinates *other* joints own — they attach nothing (M2, ADR-062). `rack_pinion` is refused until its convention is measured |
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

**Done — 2026-07-30.** `pixi run stage-engine` produces a 2.4 GB payload
whose own `bin/python` imports mujoco 3.10.0 from its own site-packages and
integrates the reference free fall identically, with no GL module loaded.
Packaged lifecycle gate: 6 passed.

The import gate earned its keep on its first run by failing — not on mujoco,
but on `bin/python`, which was a **dangling symlink**. A conda `bin/python`
points at `bin/pythonX.Y`, the interpreter was not in the prune's keep list,
and the payload had been shipping a broken link for as long as the prune has
existed. Nothing noticed because nothing ran it: discovery goes through
`cadex-engine.json`, which names `freecadcmd`. Fixed by carrying one level of
same-directory symlink target. This is the ADR-023 rule paying out exactly as
written — a source tree that passes proves nothing about a payload.

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
so M3's budget work was about the API limit, not the byte limit, and it
turned out to be about a *second* limit the API never had: what the solver
does between frames (§5 hazard 6, ADR-064).

---

### M2 — `assembly` → `mjSpec` `(DONE 2026-07-30, ADR-062)`

The real builder, and the largest single piece of engineering in M1–M4.

`assembly.dynamics(asm, bodies, ...)` walks the assembly graph and
constructs an `MjSpec`: one body per component with exact OCCT inertia, a
spanning forest grown breadth-first from the grounded components, loop
closures as `equality/connect` or `equality/weld` against sites, the five
direct joint mappings, and gear/belt/screw couplings as `equality/joint`.
`assembly.body(component, density_kg_m3=...)` is the intermediate that gives
a component mass; density is required and never defaulted. The unmappable
joint kinds are refused with a sentence naming which joint and why. The
translator is `src/Mod/cadex/CadexDynamics.py`: pure Python, no FreeCAD,
staged into the sandbox by filename, and the only module in the tree that
may import `mujoco`.

**Done, and closed.** The trace publishes through the path `api.simulation`
already used — same `output_type`, same `artifact_kind`, no protocol change,
no `shell/` diff. Engine suite **447 passed** at closure (445 at the ADR, plus
the two that came with the `describe_api` note and the `CadexDynamics`
tidy), and the **packaged lifecycle gate 7 passed** against a payload
restaged from the closing commit — which is the gate that matters, since
ADR-023's rule is that a passing source tree proves nothing about a
payload. `pixi run gate` passed at M2's verification commit and has not been
re-run since, because the branch has never contained a `shell/` diff to
invalidate it: `git diff main...MJC` names no file under `shell/`. That
invariant, not a repeated run, is what the shell claim rests on.

Closed 2026-07-30 with its two documentation debts paid: `docs/VISION.md`
gained the scope ADR-060 owed it and `docs/ROADMAP.md` gained Phase 14, both
as branch-marked appended blocks per ADR-063. **Nothing in M2 is left
open.** What M2 deferred is named in ADR-062's "not in this slice" list and
belongs to M3 or later — read that list before assuming a gap is a bug.

**Nine things this slice learned by measuring, seven of which contradict
what is written above or in the plan it came from.**

1. **`Shape.MatrixOfInertia` is about the centre of mass, not the origin.**
   This document said the origin. The reading is taken from a copy
   translated to the origin, which is right under either convention.
2. **Geoms are not needed to infer mass, so collision is deferred to M3.**
   "Primitives only" above assumed they were. A geomless body with explicit
   inertia compiles and simulates; `model.ngeom == 0` is a test, and
   contact cannot participate in a result this slice has not validated.
3. **All four coupled kinds attach nothing.**
   `AssemblyObject::isJointTypeConnecting` returns false for exactly them,
   so FreeCAD's own solver never uses them to place a part. "A screw is a
   hinge plus a coupling" was one joint too generous.
4. **`rack_pinion` is refused.** Its native constraint acts along a marker
   frame OndselSolver derives specially and the measurement run did not
   produce a clean `x = R·θ`. Measuring exists so the guess does not ship.
5. **Screw pitch is millimetres per revolution.** Hazard 7's 2π ambiguity,
   settled by driving one turn through the real kinematics path: a 4 mm
   pitch moved the nut 4.000 mm. Gears counter-rotate at −r1/r2; a belt
   drives at +r1/r2. `test_dynamics_ondsel_parity` keeps all three pinned to
   what FreeCAD actually does.
6. **`compiler.degree` defaults to degrees**, and silently turned a `[-1, 1]`
   joint range into `[-0.017, 0.017]`.
7. **A body-anchored `connect` resolves its second anchor through the
   model's reference configuration**, which here is deliberately not the
   solved pose — it closed a four-bar 16 mm out, in XML that looked
   ordinary. Closures are written against sites instead.
8. **Equality constraints are soft enough to matter.** Default `solref` let
   a driven four-bar drift 3 mm open on a 200 mm mechanism; default `solimp`
   let a heavy nut overwhelm its screw coupling entirely (610 mm of travel
   where the pitch allows 105). Stiffened, those are 0.05 mm and 0.8%.
9. **`balanceinertia` really does invent numbers**: `[0.001, 0.001, 1.0]`
   compiles to `[0.334, 0.334, 0.334]`. It is asserted off, and the compiled
   inertia is re-checked against the OCCT numbers on every build, because a
   flag is only a promise about a default.

**The exit criterion, and why it is shaped that way.** The model's reference
configuration is the one where each joint's two connector frames coincide —
*not* the solved pose. The solved pose is derived from
`component_placements` by inversion, `mj_forward` runs, and every body's
world pose is compared back. Building the model at the solved pose and
checking its own reference configuration would assert only that the same
numbers were written twice; it passes on a model whose joint axes are
entirely wrong. Pose parity alone still cannot tell a hinge from a slide
sharing a frame, so each joint is also displaced by δ in turn and exactly
its subtree must move, by exactly that joint's own motion.

**The kinematics-parity check named below was not the gate in the end.**
Running the same mechanism under prescribed motion and under gravity does
not compare like with like — the two produce different trajectories by
construction. What replaced it is stronger: pose parity against a *real*
Ondsel solve (the first solved frame of a dynamics trace reproduces
FreeCAD's placements to the micrometre), plus the perturbation test, plus a
closure-residual gate that needs no MuJoCo at all.

### M3 — Dynamics for real `(DONE 2026-07-30, ADR-064)`

Contact, friction, restitution, gravity as a script parameter, and the
determinism gate. Phased like M2 was, and for the same reason: the phase
that measures comes before the phase that builds.

**Three corrections to what this section said before it was planned**, all
from reading the M2 code and measuring against mujoco 3.10.0:

1. **M2 already split solver step from trace step.** `api.dynamics` takes
   `frames_per_second` and derives a finer `solver_step` from
   `DEFAULT_TIME_STEP_S = 0.002`; the trace records `solver_step_s`
   alongside. What M3 actually owes here is not the split but the *budget*
   (phase 4) and making the solver step authorable.
2. **"The units boundary gets built here, first" is already paid.** M2
   phase 0 wrote `test_dynamics_units.py` before the feature, and the split
   rule — the pure module does every arithmetic operation *including every
   unit conversion*, the worker does every FreeCAD read and nothing else —
   is stated and tested. M3 inherits it and must not leak a second
   conversion site; contact parameters are where that would happen.
3. **"Forced single-threaded" is not the flag it sounds like.** Measured:
   `mjDSBL_ISLAND` is a *disable* bit and `m.opt.disableflags == 0` on a
   default compile, so islands are **on** by default, not off. Separately,
   MuJoCo only actually parallelises when an `mjData` is given a thread
   pool, which we never do — so we are probably already single-threaded and
   the hazard is about constraint *ordering*, not threads. Probably is not a
   test.

---

**Phase 0 — measure, before anything is built.** The M2 lesson that paid
best was writing the units test first; the analogue here is that every
determinism assumption gets a number before contact exists to blame.

- **Is a trace byte-identical across processes today, with no contact at
  all?** Run the M2 four-bar in two separate interpreters and compare. If it
  already is not, contact is not the cause and the gate has a prior problem
  worth finding now rather than after mesh collision has muddied it.
- **Does `mjDSBL_ISLAND` change any number in our usage?** Measure both
  ways. Then set it explicitly whichever way the measurement lands, because
  a flag is only a promise about a default — the lesson `balanceinertia`
  charged us for in M2.
- **Assert `mjENBL_SLEEP` off.** Measured off by default in 3.10.0. A
  sleeping body freezes a settling mechanism, which is exactly the M3
  scenario, and the trace difference is silent.
- **Prove OndselSolver's own byte reproducibility.** ADR-062 made this the
  precondition for deciding whether trace bytes enter the project digest.
  Answer it here, in this phase, and record the answer either way.

**Phase 1 — collision geometry, and what it refuses.** The hazard is
hazard 2: MuJoCo hulls a collision mesh without complaint, so a bracket
with a slot silently becomes a solid block.

- **The mesh source is `cadex_tessellation.tessellate_shape`**, which
  already exists worker-side and already respects the M2 split rule.
- **A collision mesh must not ride the display deflection.** Display
  deflection is chosen for looks and scales with the bounding box; a
  collision mesh derived from it is a physics result that changes when the
  view does. Separate, explicitly declared, recorded in the evidence.
- **Convex decomposition is not in M3 unless phase 2 proves it necessary.**
  Measured today: `scipy` 1.17.0 with Qhull (`scipy.spatial._qhull`) is
  already in the staged payload, so a convex *hull* costs no new dependency
  and no new payload weight. CoACD would cost a second
  `CARRIED_PYPI_PACKAGES` exception — the thing ADR-061 named so it would be
  easy to find and delete, not so it would grow — plus a decomposition whose
  cross-version determinism nobody has established and which we assert digest
  equality over. That trade needs evidence, not enthusiasm.
- **Convexity is measured, not assumed.** We have the BREP, so compare the
  solid's exact `GProp_GProps` volume against its convex hull's. If they
  differ beyond tolerance the body is concave, MuJoCo would silently hull
  it, and the build **refuses** — naming the component and the volume error
  — exactly as `rack_pinion` was refused in M2. Measuring exists so the
  guess does not ship.
- **The script says what to do about it**, and the refusal names the
  options: explicit primitives (box, sphere, cylinder, capsule) as the
  declarative escape hatch, or an explicit opt-in that the author has
  accepted the hull. Never an inferred one.

**Phase 2 — contact parameters.** Friction, restitution, `condim`,
`margin`/`gap`, and the `contype`/`conaffinity` pairs that decide what may
touch what.

- **Restitution is a translation, not a pass-through.** MuJoCo has no
  restitution coefficient; bounce comes out of `solref`. That conversion is
  arithmetic, so it lives in the pure module with its own test, and it is
  the most likely place for a second unit-conversion site to sneak in.
- **Parent/child filtering is a default we must verify, not inherit.**
  `mjDSBL_FILTERPARENT` exists and is off; what it does by default to a
  jointed chain decides whether every mechanism M2 can already build starts
  self-colliding the moment geoms appear.

**Phase 3 — gravity and solver as script surface.** `gravity_m_s2` is a
module constant today (`DEFAULT_GRAVITY_M_S2`) and should be authorable —
a mechanism on the Moon, or with gravity off to isolate a joint. The
integrator is measured as Euler by default; contact usually wants
`implicitfast`, and that choice is a digest-moving decision that gets
written down rather than defaulted into. `solver_step_s` becomes authorable
with `DEFAULT_TIME_STEP_S` as its default.

**Phase 4 — the frame budget.** The 10 000 frame / 100 000 component-pose
caps were sized for kinematics. With solver and trace steps already
separate, the open question is what the cap should *count* once an M7-scale
rollout exists — and it is now the only open question left in §6.

**Phase 5 — the determinism gate.** Same script, same params →
identical trace digest across cadexd restarts, single-threading settled by
phase 0 rather than asserted. Then the digest decision phase 0 gathered
evidence for: whether a trace's `artifact_sha256` joins the project digest,
given that today it is in **no** digest and so a MuJoCo version bump changes
every trace and moves nothing — silent, which ADR-062 called strictly worse
than loud.

**Phase 6 — the falling thing.** A mechanism that topples, lands, and stops,
with contact doing the work.

**Done when:** a thing falls over correctly, and does so identically twice
in two different processes.

**Done, and closed.** A mast hinged level on a post swings down under
gravity alone, slaps a floor slab it is not jointed to, rebounds through
twenty degrees, comes back, and by 1.25 s is motionless to under a
micro-degree — end to end through the live cadexd gate, with no protocol
change and no `shell/` diff. The same script through two separate cadexd
processes writes the same artifact byte for byte. Engine suite **556
passed** (447 at M2's close); the **packaged lifecycle gate 8 passed**
against a payload restaged from the closing commit, and the collision and
cross-restart suites pass against that same payload, which is what proves
Qhull is really in it. `pixi run gate` was not re-run and did not need to
be — `git diff main...MJC` still names no file under `shell/`.

**What the six phases learned by measuring**, and the plan's own corrections
are in ADR-064 in full. The six that contradict a name, a default or a
documented rule:

1. **`mjDSBL_ISLAND` is a *disable* bit, so islands were on** — the opposite
   of what "force single-threaded" implied. It moves nothing without geoms
   and ~2e-14 with them, which is physically nothing and digest-wise
   decisive. Islands are now off explicitly, sleep is off by assertion, and
   both are recorded in the trace.
2. **The restitution formula everyone quotes is the bilateral one.** A
   contact is unilateral: it separates when the normal force would turn
   tensile, not after a full half period. `e = exp(−ζ(π − 2 arcsin ζ)/√(1−ζ²))`
   matches a dropped ball to 1% where `e = exp(−ζπ/√(1−ζ²))` is out by 44%.
3. **A bouncing contact needs twenty solver steps per contact time
   constant.** At the ten the default step gives, a requested 0.9 measures
   **3.45** — a ball bouncing higher than it was dropped from. Refused now,
   with the required step named.
4. **MuJoCo's parent/child filter does not cover a body hinged to a grounded
   one**, because it exempts parents welded to the world and every grounded
   component here is one. Without the explicit exclusions the translator now
   writes, every mechanism M2 could build would self-collide at its pins.
5. **Euler gains 51% of a tumbling part's kinetic energy in twenty
   seconds.** `implicitfast` conserves both energy and angular momentum and
   tracks RK4 through three Dzhanibekov flips at a quarter the cost. The
   integrator is a written-down choice now, not a default.
6. **MuJoCo sums the two contact margins** rather than taking the larger, and
   averages the two `solref`s — so a bouncy part on a dead floor bounces half
   as much as it asked to. `contype`/`conaffinity` are signed int32, so there
   are 31 collision groups and not 32.

**And one correction to this plan's own text.** It said to measure convexity
by comparing the convex hull against the exact `GProp_GProps` volume. That
would charge every curved part for its faceting — a tessellated cylinder is
an inscribed prism, 0.34% short of its exact volume at 44 sides before any
concavity exists. Concavity is hull-against-*mesh*, both from the same
vertices, where a real OCCT cylinder measures −7.7e-16. Fidelity —
mesh-against-exact — is a second, separate question with its own tolerance,
and it is not waived by the `hull` opt-in: accepting the hull of a bracket is
not accepting an eight-sided cylinder.

**Explicitly not in M3:** actuators (M4 — and the "control callbacks" half
of that phrase turned out to be a thing M4 refused rather than built), MJCF export
(M5), tendons — and therefore slider and cylindrical loop closures, which
need one — flexible subassemblies, and convex decomposition unless phase 2
earns it.

---

### M4 — Actuators and closed loop `(DONE 2026-07-30, ADR-065)`

Three of MuJoCo's actuator kinds — `motor`, `position`, `velocity` — become
an xscript surface, and with them the joint properties a driven mechanism
needs: damping, armature and friction loss.

This is the last slice that is unambiguously *CAD*. Everything after it is
robotics, and M0's ADR already said we are going there.

**Two corrections to this section's own text**, both decided before code and
both from measuring against mujoco 3.10.0.

1. **"A control callback runs in the worker" is the wrong shape, and it is
   also unnecessary.** xscript is a declarative graph builder, not a runtime;
   a Python callable invoked every solver step would put unbounded arbitrary
   code inside the determinism gate and break "nothing happens outside the
   script" the same way the deleted bpy modes did. It is not needed either:
   MuJoCo's `position` and `velocity` actuators **are** the PD loop —
   `gainprm = [kp]`, `biasprm = [0, −kp, −kv]`, closed in C, measured rather
   than read. What a script supplies is a **setpoint**, and a setpoint that
   varies is a whitelisted formula of `time`, reusing the validator
   `api.motion` has had since ADR-048.
2. **Joint damping and armature are part of this slice.** A position gain
   stiff enough to hold an arm rings on a frictionless, armature-free joint —
   measured, sixty degrees peak to peak, not decaying — and MuJoCo's defaults
   for all three are zero. A gain that only behaves because of an undeclared
   default is the failure class M2 and M3 were each organised against, so
   `api.joint_dynamics` is its own declared intermediate.

**Done, and closed.** A two-link arm on a grounded post, both links
horizontal so gravity has its full moment arm, holds a commanded 30° and
settles at **30.44** — the 0.44 being the load's torque divided by the gain,
on gravity's side, which is what a proportional servo does. The same script
with its `actuators=` list emptied falls to 75°, which is what makes the
first number mean anything. End to end through the live cadexd gate, with no
protocol change and no `shell/` diff. Engine suite **684 passed** (556 at
M3's close); the **packaged lifecycle gate 8 passed** against a payload
restaged from the closing commit, with the actuator and cross-restart suites
passing against that same payload. `git diff main...MJC` still names no file
under `shell/`.

**Units are in the parameter names, and the wrong one is a refusal.** Every
quantity whose meaning depends on whether the joint coordinate turns or
slides gets a suffixed pair — `control_deg`/`control_mm`,
`stiffness_nmm_per_deg`/`stiffness_n_per_mm`,
`torque_limit_nmm`/`force_limit_n`, `armature_kgmm2`/`armature_kg`, and four
more. That is more names than one `control=` plus a `motion_type` would need,
and it is hazard 1 answered in the surface: the two readings of
`stiffness=4000` differ by five and a half million, and a `control="30"` that
means radians is a 57× error that runs and errors nowhere.

**Six things phase 0 measured**, four of which moved a decision; ADR-065 has
them in full.

1. **`compiler.autolimits` defaults on**, so a `ctrlrange` silently becomes a
   `ctrllimited`. Off, a range without its flag is a compile error, which is
   the version to have — and every `limited` this translator relies on is now
   stated.
2. **`gear` rescales the *setpoint*, not only the effort**: at gear 2 a
   commanded 0.5 holds the joint at 0.25. So the gear is pinned at 1,
   asserted on the compiled model, and the surface has no ratio argument at
   all.
3. **The stability ceiling is `ω·h = 2` and it is dimensionless** — measured
   at 2.02 on four solver steps and invariant across a 400× range of inertia,
   because `implicitfast` integrates damping implicitly and stiffness
   explicitly. Stated dimensionlessly, one refusal is right for every
   mechanism; stated as a gain it would be right for one.
4. **A damping gain does not explode, it freezes.** Past `c / M ≈ 1.2e10` per
   second a velocity actuator commanded to 1 rad/s delivers 1e-9, finite the
   whole way, warned about by nothing. Silence is the worse failure, so it is
   the one with a refusal in front of it.
5. **A `motor` at zero control is bitwise the unactuated run**, four-bar
   included. Its converse is a separate test, because a `position` actuator
   at zero control is a servo holding zero and not "no actuator".
6. **`MjsJoint.damping` is a three-vector while `.armature` is a scalar.**
   Assigning a float to the first is a `TypeError` — the loud kind of wrong.

**Explicitly not in M4:** MJCF export (M5), `general` and `muscle`
actuators, tendon transmissions, and any per-frame actuator state in the
trace — the frame schema is `{frame_index, frame_kind, nominal_time_s,
component_placements}` and it is the reason this whole arc needs no shell
change.

---

### M5 — The model leaves the building — **closed (ADR-066)**

`assembly.mjcf(assembly, bodies, ...)` — a new publishable xscript output
that writes one self-contained MJCF file carrying exact OCCT inertia and a
keyframe at the pose the assembly solver produced. **No protocol change and
no `shell/` diff**, which is the invariant ADR-063 says the shell claim
rests on.

Two corrections to what this section used to say, both found while
measuring:

* **Not "a first-class engine op, alongside STEP".** There is no STEP
  export in this tree — `file.export_model` is a name in
  `CadexModelingSurface.py` with no op behind it, and Phase 11 owns it. M5
  is the engine's first user-facing export path, and it is *not* a cadexd
  op: that would need `OP_ARG_SPECS`, `OP_RESPONSE_SPECS`, both
  `docs/INTEGRATION.md` tables, a golden fixture and the shell's client.
  A publishable output type needs none of them. The sentence also predates
  ADR-063.
* **Not "no determinism problem".** `to_xml()` writes about six
  significant figures and has no precision knob. Mass survives a round trip
  to 1e-16 relative; an inertia triple whose smallest entry is 1e-5 of its
  largest does not, and lands at 2.4e-6. So "matches the in-engine
  simulation" is a **tolerance**, measured per mechanism, and the export
  reports how much of it each file actually spent. Byte determinism is
  fine — the same script through two cadexd processes writes the same XML —
  but numeric identity was never available.

**What was measured before anything was built** (phase 0,
`test_dynamics_mjcf_measured.py`, 55 tests):

| Finding | Number |
|---|---|
| Reload: worst mass error | 3.2e-16 relative |
| Reload: worst inertia error | 2.4e-6 relative (four-bar) |
| Reload: worst other field | 1.8e-6 (`body_pos`) |
| Trajectory divergence, 500 steps | 4.1e-4 mm worst; four-bar **0** |
| A stock load with no keyframe | **61.3 mm** out of pose |
| Collision mesh cost | ~51 bytes a vertex, written **inline** |
| Solver options across a reload | bit-identical |

Two findings came out differently from the plan. `explicitinertial` off
does not quietly drop the masses on a mechanism with no geoms — the file
stops loading at all, which is the good failure mode; but give a body a
collision geom and the same file loads with inertia inferred **from the
geom**, silently, which is exactly the failure the whole arc exists to
avoid, and now has its own test. And a solved pose of all zeros writes
`<key name="solved"/>` with no `qpos` attribute, because `to_xml()` omits
anything equal to a default — so the keyframe assertion is the pose after a
reset and never the attribute text.

**The design, and why each part is what it is:**

* **Surface.** A publishable output, not a cadexd op and not a flag on
  `api.dynamics` — the latter would couple export to running the solver
  loop M5 exists to avoid. `mjcf` gets an output type of its own where
  `dynamics` deliberately shares `simulation`: that sharing exists because
  `cadex_animate` bakes exactly one `assembly_simulation_json` and silently
  bakes *neither* on finding two. Nothing bakes an MJCF file, so a script
  may declare several, each naming its own artifact
  (`outputs/<output>-model.xml`), and `api.mjcf` beside `api.motion` is
  legal and useful — kinematics on screen, a dynamics model on disk.
* **Geometry: collision only.** A component with no `api.collision` exports
  no geom, exactly as it contributes none in a dynamics run. The exported
  file is provably the simulated model, which is what the exit criterion
  asks. The consequence, stated plainly: **a mechanism with no collision
  geometry opens invisible in MuJoCo's viewer.** Visual meshes are an M6+
  question.
* **The copy.** The solved keyframe is added on `spec.copy()`, never on the
  caller's spec, so a script carrying both `api.dynamics` and `api.mjcf`
  cannot have its simulation's numbers moved by an export. Structural
  rather than careful, and gated live: the same script with and without the
  export retains identical trace bytes.
* **Self-verification.** `export_mjcf` reloads its own output and diffs it
  against the model it came from — counts first, then every numeric field,
  then every solver option bit-for-bit — and re-runs the OCCT inertia
  comparison against the *reloaded* model, because the claim being sold is
  about the file. Anything past tolerance is a `DynamicsError` and never an
  artifact.
* **Zero arithmetic.** Hazard 1's M5 form, answered structurally rather
  than by promise: the spec is already SI, `to_xml()` converts nothing, and
  `qpos_solved` is already in MuJoCo coordinates. There is no number for a
  second conversion site to appear in, and `test_dynamics_units`'s grep
  covers the worker half for free. **Third payment, third time it held.**

**The pinned tolerances** (`CadexDynamics`): mass 1e-12, inertia **1e-5**,
fields 1e-5, pose **1e-2 mm**. The inertia bound is the tight one — the
four-bar spends a third of it and there is no precision knob to buy more.
`MAXIMUM_MJCF_BYTES` is 64 MiB, sized from ~51 bytes a vertex against
`MAXIMUM_COLLISION_VERTICES`, which admits five maximal meshes.

**One finding about FreeCAD, recorded because M5 is where it becomes
visible.** The native assembly solver drives a *tree* mechanism to the
configuration where each joint's connector frames coincide — which is
exactly MuJoCo's reference configuration — so an exported tree opens
correctly with a keyframe that happens to be all zeros. Initial placements
and joint limits do not move it. The keyframe becomes load-bearing when a
loop closure forces a nonzero coordinate, and that is proved on the
four-bar fixture (`qpos = [0.873, −0.702, 0.966]`) rather than live,
because a planar loop of revolutes is reported redundant by this tree's
native solver and cannot reach a live gate at all.

**Known consequence at the time, closed a day later (hazard 3).** When M5
landed, `compute_project_digest` gave anything that was not `brep`/`mesh` a
`payload_sha256` of its canonical definition JSON, so the exported XML bytes
were in **no** project digest and a MuJoCo version bump changed every
exported file silently — identical to how the trace behaved. **ADR-068 fixed
both at once**, on `main`, by keying the digest's bytes clause on *having an
artifact* rather than on a list of known kinds: `assembly_mjcf_xml` was
covered by the sync with no code on this branch, which is the property that
clause was written for. `CadexMjcfMuJoCoVersion` is still published and still
earns it — the digest says that something changed, the field says which
version wrote it.

**Done when — and it is:** an assembly designed in Cadex exports an MJCF
file that loads in a stock MuJoCo with no Cadex on its path (asserted by
the subprocess, which tries to import `CadexDynamics` and reports that it
could not), opens in the pose it was solved at, carries the OCCT inertias
to a stated and tested tolerance, and integrates to the same trajectory the
engine produced within that tolerance — through the live cadexd gate, with
no protocol change and no `shell/` diff. The packaged gate is **9 tests**.

---

### M6 — A task is part of the script — **closed (ADR-069)**

`assembly.task(model, ...)` — a new publishable xscript output that writes
one JSON bundle describing a trainable task, beside the model it
references. Four new intermediates compose it: `assembly.observation`,
`assembly.reward`, `assembly.termination`, `assembly.randomise`. **No
protocol change and no `shell/` diff**, which is the invariant ADR-063 says
the shell claim rests on.

A model is not a task. Training needs observation space, action space,
reward, termination, episode length and domain randomisation — none of
which is geometry, all of which is *data*, and the script is already the
sole source of truth for data.

**The four forks, decided before planning:**

| Fork | Decision |
|---|---|
| **Observations** | MJCF `<sensor>` elements, declared on `assembly.mjcf(..., observations=[...])`. Stock MuJoCo computes the observation vector; the task names the channels. |
| **Exit criterion** | A reference episode runner importing only `mujoco` runs a full episode from the bundle and matches an in-engine episode. |
| **Action bounds** | Derived from the joint's limits (position) or the effort limit (motor); underivable is a refusal, not a default. |
| **Randomisation** | In scope, resolved to concrete compiled-model field indices at export time. |

**What was measured before anything was built** (phase 0,
`test_dynamics_task_measured.py`, 11 tests):

| Finding | Number |
|---|---|
| Sensors added, 500 steps, `qpos` difference | **exactly 0.0** |
| XML cost per sensor | ~54 bytes |
| A frame sensor's `objtype="body"` vs `"xbody"` | **180°** apart on a plain box |
| ...and in position, on an offset centre of mass | **60 mm** apart |
| `ctrlrange` with `ctrllimited` FALSE (what M4 builds) | inert; action space unbounded |
| `ctrlrange` set: control 5.0 into ±0.2 | `actuator_force` clamped to 0.2, `data.ctrl` **unchanged** |
| A one-sided limit's synthetic endpoint | **100 full turns** |
| `body_mass` scaled alone | `body_subtreemass` follows, `body_inertia` does **not** |
| The keyframe through `to_xml()` | 0.3000000000000001 → **0.3** |

**Two of these changed the design before it was written**, which is what a
phase 0 is for:

* **`objtype="body"` is the inertial frame.** MuJoCo's frame sensors accept
  two object types a reader would take for one thing. `body` resolves to
  `xipos`/`ximat` — the frame the principal axes of inertia define — and
  `xbody` to `xpos`/`xquat`, the frame the assembly solver placed and the
  one `_verify_exported_pose` already compares against. On a plain box the
  orientations differ by a **half turn**, because MuJoCo orders principal
  axes by eigenvalue and that order is not the link's local x, y, z. Every
  `component_*` channel is an **xbody** channel because of this
  measurement. A reward naming a position would otherwise have been handed
  the centre of mass, silently.
* **A mass draw has to scale the inertia too.** MuJoCo keeps `body_mass`
  and `body_inertia` in independent arrays and derives `body_subtreemass`
  from the first at `mj_setConst`. Scaling the mass alone leaves a body
  whose rotational inertia no longer matches it — not a heavier part, a
  part whose density depends on which equation you ask. One draw therefore
  scales both, which is what changing the density of a fixed shape means
  and is how `mass_kg` and `inertia_kg_m2` produced the two numbers in the
  first place, each linear in the density. The bundle's randomisation entry
  is consequently `{label, target, mode, low, high, fields: [...]}` — one
  draw, several field indices — rather than the single `field`/`index` pair
  the plan sketched.

**The design, and why each part is what it is:**

* **Surface.** `observation`, `reward`, `termination` and `randomise` are
  **intermediates** — like `body`, `collision`, `actuator` and
  `joint_dynamics` they have no native type and nothing publishes them.
  `task` is the one new publishable output, and the **first output that
  consumes another output**: it takes one `api.mjcf` value and writes one
  JSON that references that model by relative path and sha256. One output,
  one artifact — no second XML, and a bundle whose model moved is
  detectable. Like `api.mjcf` and for the same reason it is *not* under the
  "exactly one simulation" rule: nothing bakes a task, so two of them
  sharing one model is a reasonable script.
* **A vector channel expands to suffixed scalar names.** `name="hand"` on a
  `component_position` gives `hand_x/_y/_z`; an orientation gives
  `hand_qw/_qx/_qy/_qz`. Reward formulas do arithmetic on scalars, so the
  names a formula may use are enumerable and every one is checked —
  including a collision produced *by* an expansion.
* **The whitelist division.** `api.reward` is written before there is a
  task to belong to and cannot know which channels exist, so the **API
  checks syntax and function calls** and the **engine checks vocabulary** —
  where the channel list is not only known but expanded, and the refusal
  can name what was available instead. `_checked_formula` grew a
  `functions=` parameter for this; `api.motion`'s whitelist did not move,
  because its formula is rendered back into an Ondsel expression and Ondsel
  has no `tanh`.
* **The action bound is derived or refused.** A motor is bounded by its
  effort limit; a position servo by its joint's own two-sided limits. Four
  refusals, each with the correction that resolves it: a velocity actuator
  (its control is a speed, and a FreeCAD joint states position limits and
  never a speed — deriving one would need a time the model does not carry),
  a motor with no effort limit, an unlimited joint, and a **one-sided**
  limit, whose filled-in endpoint phase 0 measured at a hundred turns and
  which is a solver convenience rather than a mechanical bound.
* **The bound is advertised, not compiled in.** `ctrlrange` is deliberately
  left alone: one model may serve several tasks with different action sets,
  so the bundle states the range and whoever runs the episode clamps to it.
  `forcerange` and `jnt_range` still hold independently in the model, so a
  policy that ignores the bound cannot drive a different mechanism. Note
  that MuJoCo's joint limits are *soft* — a driven joint overshoots one by
  ~10° and is pushed back — so an action range is not a hard promise about
  where the joint can go.
* **Control formulas stay required on `api.actuator`, unchanged.** A
  policy-driven actuator's formula becomes its deterministic fallback
  action, which is exactly what the in-engine episode needs to run without
  a policy. Zero diff on an existing surface.
* **The engine evaluates the episode on the reloaded exported bytes**, not
  on `built["model"]` — so the comparison against the stock runner is a
  claim about the *task spec* rather than a re-proof of M5's physics. The
  worker also runs one episode from the bundle it just wrote before
  publishing it: not the training run, the receipt that the spec executes.

**Units — hazard 1's fourth payment, and a new shape of it.** Everything
before M6 converted a number the script wrote into the unit MuJoCo reads.
These go the other way, and that is *more* dangerous rather than less
because of who does the arithmetic: a reward formula is evaluated **outside
the engine**, by a trainer holding raw `sensordata`. A reward written in
degrees and evaluated in radians is a silent factor of 57.

The answer is the M2/M4 one. Every conversion is one number computed in
`CadexDynamics` and emitted into the bundle as a per-channel `scale`, so the
trainer **multiplies rather than converts** — the only shape that cannot be
performed backwards. The four inverse conversions (`angle_degrees`,
`speed_mm_per_s`, `torque_nmm`, reusing `length_mm`) went into
`test_dynamics_units.py` before they had a caller, per §3.2, and were
committed failing. `angle_degrees` is the one that matters: every other
conversion on this boundary is a power of ten, so getting one wrong moves a
decimal point and *looks* wrong. 57.29578 does not. **Fourth payment,
fourth time it held.**

**The bundle — `cadex-training-task-v1`.** `observations` (name, sensor,
`adr`, `dim`, channels, unit, scale), `actions` (actuator, index, unit,
low, high, scale, source, fallback), `reward`, `termination`, `episode`,
`randomisation`, `model` (path, sha256, bytes), and `functions`.

That last array is in the file on purpose: the reference runner has its own
evaluator, and **two evaluators is a place for a whitelist to drift**. A
test asserts the runner's globals keys equal the engine's `REWARD_FUNCTIONS`
equal this array, and the runner *refuses outright* when they differ rather
than failing mid-episode. This codebase keeps catching drift by writing the
second copy down; here it costs one array.

**The caps** (`CadexDynamics`): 64 observation channels (counted on
*scalars*, so a `component_position` is three), 16 reward terms, 8
termination rules, 32 randomisation entries, 200 000 episode steps, and
`MAXIMUM_TASK_BYTES` of 1 MiB — three orders of magnitude below
`MAXIMUM_MJCF_BYTES` on purpose, because a task is names, numbers and short
expressions and a megabyte of it is a mistake with a loop in it.

**Two findings the live path surfaced**, both recorded where they are
visible:

* **`component_position` reads the body frame origin**, and a link hinged
  at its own origin has that point *on* the rotation axis — so its position
  channel never moves however far the arm swings. Correct, and useless
  there, which is exactly why `centre_of_mass` is a separate kind. The live
  test asserts it as a constant rather than working around it.
* **A one-sided limit reports its declared pair intact** (`[None, 95.0]`),
  so the refusal says *which* endpoint is missing rather than merely that
  one is.

**Deferred, and named rather than half-built:** `touch` and
`accelerometer` need a *site* with a placement the assembly graph does not
carry; `contact_force` reports per-contact, so its width depends on what is
touching what at the instant it is read, which is not a fixed-width
channel. `DEFERRED_OBSERVATION_KINDS` carries the reason each is absent, so
a refusal about one is not mistaken for a typo.

**§6's open question — "does the policy asset extend `put_asset` or get its
own op" — is M7's and is not answered here.** M6 adds no op and no protocol
field; a bundle arrives as an ordinary output with an `artifact_kind` the
shell has never heard of, which `cadex_hydrate` skips for want of a
tessellation and `cadex_animate` for want of the simulation kind.

**The digest needed no work.** ADR-068's clause is keyed on an output
*having an artifact* rather than on a roster of kinds, so
`assembly_training_task_json` joined the project digest by inheritance. A
test asserts that outcome rather than trusting the reasoning — a reward
weight changed in the bundle and nothing else moves the project's identity,
which is what stops a stored task being retrained against different numbers
under the same digest.

**Done when — and it is:** a script fully specifies a trainable task; the
bundle it writes is read by a process with no Cadex on its path (asserted
by the subprocess, which tries to import `CadexDynamics` and reports that
it could not), which resets the model to the solved keyframe, acts,
observes, accumulates reward and terminates — producing the same numbers
the engine produced, compared step by step as `repr` text, seeded domain
randomisation included, through the live cadexd gate, with no protocol
change and no `shell/` diff. The packaged gate is **10 tests**.

`cadex_tests/dynamics_task_episode.py` **is** the environment. M7 becomes
dispatch rather than debugging.

---

### M7 — Training happens elsewhere — **closed (ADR-070)**

`assembly.policy(task, weights=..., sha256=...)` — a publishable xscript
output that names a trained policy by file and digest, verifies it against
the task it claims, and writes one receipt. Plus `training/cadex_train.py`,
a Cadex-free PPO trainer at the repository root that reads an M6 bundle and
writes one `.cxpolicy`. **No protocol change and no `shell/` diff.**

**The honest constraint, unchanged:** training does not run on the user's
laptop. MJX needs JAX-on-GPU, JAX's Apple Silicon story in 2026 is
`jax-metal` 0.1.0, MuJoCo Warp needs CUDA, and the published reference — a
Unitree G1 walking policy in ~90 minutes — is 4096 parallel environments on
an RTX 4090. On CPU that is days.

So training is **offboard by design**, and M7 confirms it is a clean
boundary rather than a compromise. It makes the *engine* simpler: the engine
verifies a policy and never produces one, so it needs no optimiser, no
autodiff, no accelerator and — measured, see below — no numpy.

**The three questions ADR-067 named as M7's, answered:**

| Question | Answer |
|---|---|
| Where does training run? | The user's own machine with a GPU, dispatched by the agent's shell. M7 ships a movable run directory and a trainer; it builds **no dispatch machinery, no network I/O, no new op**. |
| Does the policy extend `put_asset` or get its own op? | **Extends `put_asset`.** A new op would cost a `shell/` diff — `cadexd_client.py` — and ADR-063 says the branch rests on there not being one. Widening the store's accepted suffixes costs none. |
| Is there a **train** button? | **No, and there is nothing to press.** The agent authors the task, dispatches with its own shell, and calls the existing `put_asset` path. VISION principle 5 is untouched: the human still only judges. |

**What was measured before anything was built** (phase 0,
`test_dynamics_policy_measured.py`, 18 tests, run in a venv from
`training/requirements.txt` because the engine environment deliberately has
none of it):

| Finding | Number |
|---|---|
| MJX vs CPU MuJoCo, four-bar with `equality/connect`, 5 steps | **3.8e-8** |
| ...two-link arm, position actuators + joint limits | **4.8e-10** |
| ...mesh geom onto a slab, 400 steps, `ncon > 0` | **3.4e-4 m** (0.34 mm) |
| MJX sensordata, all eight observation kinds, worst channel | **3.5e-7** |
| `vmap` over 8 environments vs the unbatched run | **exactly 0.0** |
| A reward expression under `jnp`, vs the engine's float64 evaluator | **9.5e-8** |
| `np.savez` byte-determinism | **deterministic** |
| A PPO policy with its normaliser: one hinge → humanoid | **4.6 KiB → 902 KiB** |
| numpy float64 vs JAX float32 forward pass | **1.46e-5** relative |
| JAX jitted vs un-jitted, same weights, same process | **~1e-7** |
| Pure-Python forward pass, arm-sized / humanoid-sized | **219 µs / 5.29 ms** |
| JAX-on-CPU across two processes at a fixed seed | **bit-identical** |
| sha256 over the full 128 MB asset budget | **~46 ms** |

**Four of these changed the design**, which is what a phase 0 is for:

* **`np.savez` is byte-deterministic, and the plan said it would not be.**
  The plan justified the hand-rolled container by "zip entries carry an
  mtime"; numpy writes a fixed `date_time`, and two processes an hour apart
  produced one sha256. **That argument does not hold and is recorded as
  wrong rather than dropped.** The container is still hand-rolled for
  reasons that survive: the engine reads it inside a `--safe-mode` sandbox
  from a module that imports no numpy at all, and a length-prefixed header
  plus a flat float32 blob needs neither a zip parser nor an `allow_pickle`
  flag that has to stay false.
* **A policy is kilobytes, not the "tens of megabytes" §3.1 guessed** —
  three orders out. `MAXIMUM_POLICY_BYTES` is 4 MiB, sized from 902 KiB.
* **Pure Python is fast enough, so numpy did not enter `CadexDynamics`.**
  The plan said it would be added deferred, as `scipy.spatial` is, *if* the
  measurement demanded it. 4 564 Hz against a 50 Hz control rate says it
  does not. A measurement paying for itself by preventing an import.
* **A mesh geom that never touches proves nothing.** The first contact
  measurement stepped 20 times, made zero contacts and would have reported
  success. Rewritten to drop a box onto a slab and assert `ncon > 0`. The
  0.34 mm MJX/CPU difference under contact is a fidelity note for M8, not a
  blocker: MJX is float32 with its own contact path, training happens there
  and evaluation happens on CPU.

**ADR-069's central claim survived the trainer.** MJX evaluates all eight
observation kinds and vectorises them exactly, so *MuJoCo computes the
observation vector* still holds and no fourth implementation was needed —
which was risk 2, and it did not fire. Nor did risk 1: MJX carries our
equality constraints and our mesh geoms, so the batched-CPU-`rollout`
fallback was never reached.

**The design, and why each part is what it is:**

* **The policy is an asset; the receipt is the output.**
  `compute_project_digest` takes `(root, outputs)` and never walks
  `assets/`, so a policy that nothing published would land with a sha256 in
  `put_asset`'s reply and in no project identity at all. Declaring it as an
  output fixes that twice: the declared `sha256` is inside the definition
  JSON, and the receipt's bytes join by ADR-068's have-an-artifact clause —
  the third time that clause has paid out with no code.
* **`sha256=` is required and never inferred.** A policy is the one artifact
  in a project that cannot be rebuilt from the script (VISION principle 3),
  so the script carries the one thing that *can* be checked. The refusal
  names the digest observed, so the agent can paste it back.
* **The container carries a witness**, and it is what makes M8 safe:
  N observation vectors and the actions the trainer's own network produced
  for them. `verify_policy` checks six claims — task digest, model digest,
  channel list, action table, output map, witness — of which the first five
  are equality against the bundle and the sixth is a re-computation. **A
  container whose weights are intact but whose architecture the engine reads
  differently passes the first five and fails the sixth.** Without it that
  is a gait somebody has to watch and distrust.
* **The tolerance is measured, not chosen.** `POLICY_WITNESS_TOLERANCE` is
  1e-4 relative to each action's own range — seven times the worst measured
  disagreement, and above the ~1e-7 JAX differs from *itself* by. Relative
  rather than absolute because 2 N·mm is nothing on a 2000 N·mm motor and
  everything on a 2 N·mm one. Trained policies verify at 1.7e-9 to 3.6e-8,
  because the trainer rounds to float32 *before* taking the witness.
* **`_ASSET_SUFFIXES` keeps its exact three members.** The shell mirrors
  that constant by name in a comment, so widening it would make the comment
  false. `_POLICY_ASSET_SUFFIXES` sits beside it and `_STORED_ASSET_SUFFIXES`
  is the union. `put_asset` and `import_geometry` perform **no** suffix check
  of their own, which is why a `.cxpolicy` reaches the store through the tool
  that already exists.
* **The trainer lives at the repository root**, never installed by CMake,
  in no payload, with four exactly-pinned dependencies in
  `training/requirements.txt`. **Nothing entered `pixi.toml`** —
  `CARRIED_PYPI_PACKAGES` stays one entry long, which is what ADR-061 named
  it for — and `test_engine_purity_guardrails` asserts no `jax` and no `mjx`
  reach the source or the staged payload.

**Units — hazard 1's fifth payment, and it cost nothing.** The direction is
new again: an action vector crosses *out* of a trainer and *into*
`data.ctrl`. The answer is M5's and it is structural: the network's bounded
output is mapped through `output_scale`/`output_bias`, **which the engine
checks against the half-range and midpoint the *bundle* derived from the
mechanism** — so the numbers come from a torque limit rather than from the
trainer's imagination. What leaves the forward pass is already in
newton-millimetres, and the only conversion is the `clamp then × scale`
`evaluate_episode` has performed since M6. **M7 added zero conversion
sites**, and `test_dynamics_units`'s existing regex now greps
`training/cadex_train.py` too, so one appearing later is a test failure.
Fifth payment, fifth time it held.

**Three evaluators, and two encoders.** M6 had two evaluators of the reward
expressions; M7 makes three. Three is where a whitelist drifts, so the
bundle's `functions` array is asserted equal to all three and the trainer
refuses outright when it differs. The container format has two
implementations for the same structural reason — the engine cannot import
the trainer and the trainer must not import the engine — and a test compares
their bytes.

**The caps** (`CadexDynamics`): `MAXIMUM_POLICY_BYTES` 4 MiB, 1 000 000
parameters, 8 layers, 1024 width, 8–256 witness samples.

**What the CI gate proves, and what it does not.** The live training gate
trains a *tiny* task — one hinge, swing-up, seed 0, 150 iterations, 128
environments — on **CPU**, because that is what a test machine has. It
converges visibly: reward per step 1.10 → **2.487** against a ceiling of
2.5, in 4.2 seconds. **The GPU is a speed difference, not a semantic one,
and it is the same trainer file — but this gate does not prove the GPU
path.** A remote GPU run is exercised manually.

**M8 is a swap, not a discovery.** `evaluate_episode`'s `actions=` callable
was written in M6 as M8's seam and already takes `policy_forward`: through
the live gate the trained policy scores 243.4 against 98.4 for doing
nothing, holds the pendulum inverted, and costs 17 ms per 100 control steps
in pure Python.

**Done when — and it is:** a task defined in M6 trains to a policy; the
`.cxpolicy` lands in the project store through the `put_asset` path that
already exists; a script declares it and the engine verifies it against the
task it was trained on — refusing a policy whose task, model, channels,
actions, output map or witness disagree — and publishes a receipt whose
bytes are part of the project's identity. Through the live cadexd gate, with
no protocol change and no `shell/` diff. The packaged gate is **11 tests**.

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

1. ~~**Units**~~ (§3.2). **Handled in M2**, which wrote the test before the
   feature: millimetres at the surface, one conversion site in the pure
   module, `test_dynamics_units.py`. **M3 and M4 were each the predicted
   regression and it held both times.** M3's contact parameters were named
   as the likeliest place a second conversion site would appear and none
   did; M4 was the harder case and it was answered in the *parameter names*
   rather than only in the module. Every quantity whose meaning depends on
   whether a joint coordinate turns or slides carries a **suffixed pair** —
   `control_deg`/`control_mm`, `stiffness_nmm_per_deg`/`stiffness_n_per_mm`,
   `armature_kgmm2`/`armature_kg` and five more — and passing the wrong one
   is a refusal rather than a factor of five and a half million. All six M4
   conversions were written into `test_dynamics_units.py` before they had a
   caller, and the worker forwards actuator parameters without touching a
   number, which it can because they come off the graph and there is nothing
   to read out of FreeCAD for a motor.
   **M5 was the third payment and it held again**, and this time the answer
   was structural rather than disciplined: the export path performs *no
   arithmetic at all*. The spec is already SI, `to_xml()` converts nothing,
   and `qpos_solved` is already in MuJoCo coordinates, so there is no number
   for a second conversion site to appear in — the failure mode this entry
   predicted was not avoided, it was made unavailable.
   **M6 was the fourth payment, and it was a new direction.** Every
   conversion before it carried a number the script wrote *into* the unit
   MuJoCo reads; an observation channel carries one *out*, and that is more
   dangerous rather than less because of who does the arithmetic downstream:
   a reward formula is evaluated **outside the engine**, by a trainer
   holding raw `sensordata`. A reward written in degrees and evaluated in
   radians is a silent factor of 57. The answer is the M2/M4 one — every
   conversion is one number computed in `CadexDynamics` and emitted into the
   bundle as a per-channel `scale`, so the trainer *multiplies* rather than
   converts, which is the only shape of the operation that cannot be
   performed backwards. The four inverse conversions went into
   `test_dynamics_units.py` before they had a caller and were committed
   failing. `angle_degrees` is the one that matters: every other conversion
   on this boundary is a power of ten, so getting one wrong moves a decimal
   point and *looks* wrong, while 57.29578 looks like a mechanism.
   **M7 was the fifth payment, and it cost nothing.** The direction was new
   again — an action vector crosses *out* of a trainer and *into*
   `data.ctrl` — and the answer was M5's rather than M2's: made unavailable
   rather than performed carefully. The network emits through
   `output_scale`/`output_bias`, and the engine checks those two arrays
   against the half-range and midpoint the *bundle* derived from the
   mechanism, so the numbers come from a torque limit rather than from the
   trainer. What leaves the forward pass is already in newton-millimetres,
   and the only conversion is the `clamp then × scale` `evaluate_episode`
   has performed since M6. **Zero new conversion sites**, and
   `test_dynamics_units`'s existing regex now greps `training/cadex_train.py`
   too, so one appearing later is a test failure rather than a silent factor.
   Still live for M8, where a rollout carries the same vector back into a
   trace.

2. ~~**Convexity.**~~ **Handled in M3** (ADR-064), and it needed *two*
   measurements rather than the one this list assumed. Concavity is the
   hull's volume against the **mesh's own**, both from the same vertices —
   a real OCCT cylinder measures −7.7e-16, a notched plate measures 20 000
   mm³ inside a 28 000 mm³ hull and is refused. Comparing the hull against
   the *exact* volume, which is what this entry used to say, would have
   reported concavity for every round part in the tree: an inscribed 44-gon
   is 0.34% short of its cylinder before any concavity exists. That second
   comparison is still made, under its own tolerance, as a *fidelity*
   check — is this still the part — and the `hull` opt-in does not waive it.
   Still live as a regression hazard: `mesh` and `hull` are two kinds
   precisely so that accepting a hull is a word in the script.
3. ~~**Cross-version drift.**~~ **Half-handled, and the silent half is the
   half that went.** MuJoCo disclaims numerical reproducibility across
   releases, and M3 proved reproducibility everywhere it could — the same
   script through two cadexd processes writes the same artifact byte for
   byte, and OndselSolver does too — which is what left a version bump as the
   one thing that still moved every number. A trace's bytes were in **no**
   project digest, so that bump changed the physics of every stored project
   and the one mechanism designed to notice said nothing.

   **ADR-068 landed on `main` and arrived here on the sync**, so a retained
   artifact's SHA-256 is now part of the project digest — added to the
   canonical definition rather than substituted for it, so the change is
   strictly monotonic. It is keyed on *having an artifact* rather than on a
   list of known kinds, which is why M5's `assembly_mjcf_xml` is covered too
   without a line of code on this branch. A version bump is now a loud
   `open_project` refusal instead of a silent substitution.
   **What is left is the migration, not the detection.** A project containing
   a simulation, opened after a solver upgrade, refuses to open;
   `open_project restore=false` is the existing escape hatch and re-accepting
   records the new digest, but nothing offers that to a user in words. The
   `solver_version` and `CadexMjcfMuJoCoVersion` fields keep earning their
   place — the digest says *that* something changed, and only those say
   *which* version wrote it. Exact pin, M0, still load-bearing.
4. ~~**Multi-threading**~~ — **handled in M3 phase 0**, and it was never
   about threads. `mjDSBL_ISLAND` is a *disable* bit and a bare compile has
   `disableflags == 0`, so islands were **on**. Measured both ways: with no
   geoms the flag changes nothing, with three boxes settling on a plane it
   changes qpos by ~2e-14 — physically nothing, digest-wise decisive. Both
   settings are separately reproducible, so islands are now off *explicitly*
   and sleep is off by assertion, both checked on the compiled model where a
   MuJoCo default change would land, and both recorded in the trace. The
   remaining hazard is the ordinary one: a version bump may move numbers,
   which is hazard 3.
5. ~~**Loop extraction.**~~ **Handled in M2**, and it was the predicted
   hazard that behaved as predicted: the split is a breadth-first spanning
   forest from the grounded components, everything else is an equality
   constraint, and the drift is real — a driven four-bar sat 3 mm open on a
   200 mm mechanism at MuJoCo's default `solref`, because equality
   constraints are soft. Stiffened to two timesteps, it is 0.05 mm. What was
   *not* predicted is that a body-anchored `connect` resolves its second
   anchor through the reference configuration; closures go against sites.
6. ~~**Frame budget.**~~ **Handled in M3 phase 4**, by splitting it in two.
   The 10 000 frame / 100 000 pose caps stay and now say what they count:
   what *leaves* the engine — artifact bytes, keyframes the shell bakes.
   `MAXIMUM_SOLVER_STEPS` bounds what the engine *does*, which stopped being
   proportional to the first the moment `solver_step_s` became authorable:
   the same 600-frame trace is 4 800 steps at the default step and 1 200 000
   at the finest allowed. An RL rollout wants exactly that trade — minutes of
   integration, a hundred poses — and one cap cannot express it.
7. **Scope creep into a UI.** M5–M8 want buttons — train, stop, load
   policy — and "no user-accessible modeling tools" does not obviously
   answer whether those are allowed. ADR-060 should.

## 6. Open questions

- ~~Does the script surface speak millimetres or metres?~~ — answered by M2:
  **millimetres**, and kilograms-per-cubic-metre for density, which is the
  one place the surface is already SI because that is how material densities
  are quoted. The whole conversion lives in `CadexDynamics.py` and nowhere
  else: the split rule is that the pure module does every arithmetic
  operation *including every unit conversion*, and the worker does every
  FreeCAD read and nothing else. `test_dynamics_units.py` was written before
  the feature, per §3.2.
- ~~Does dynamics extend `api.simulation` or become a sibling
  `api.dynamics`?~~ — answered by M2 (ADR-062): **a sibling authoring
  surface, sharing the output type.** Not a compromise but a forced move —
  `cadex_animate._simulation_entries` selects on `artifact_kind ==
  "assembly_simulation_json"` and on finding two bakes **neither**, clearing
  the scene and dropping the Simulation panel into a message the UI never
  shows. A sibling *type* would let a script declare a kinematics and a
  dynamics run and silently lose the animation it already had. Sharing the
  type puts both under the existing "exactly one simulation" rule, and mixing
  `api.motion` with `api.dynamics` is refused.
- ~~Where the frame budget goes when a rollout needs more than 10 000
  frames?~~ — answered by M3 phase 4 (ADR-064): **two budgets, because there
  are two costs.** The frame and pose caps count what *leaves* the engine —
  artifact bytes, keyframes the shell bakes — and stay where they were.
  `CadexDynamics.MAXIMUM_SOLVER_STEPS` counts what the engine *does*, which
  stopped being proportional to the first when `solver_step_s` became
  authorable. A rollout is long in steps and short in frames, and one
  combined cap cannot express that trade.
- ~~**Does a trace's `artifact_sha256` join the project digest?**~~ — decided
  *yes* by ADR-064 on M3's evidence (both solvers reproduce byte for byte
  across processes), routed to `main` because `compute_project_digest` is
  shared code that treats a kinematics and a dynamics trace identically, and
  **landed there as ADR-068 on 2026-07-31** with `main`'s own three-process
  reproducibility evidence behind it. It arrived here on the sync. The rule
  is keyed on having an artifact rather than on a roster of kinds, so M5's
  exported models joined at the same time and for free. What is still open is
  the *migration* — a solver upgrade now refuses to open the project, and
  nothing tells the user that `restore=false` and a re-accept is the way
  through.
- ~~Where does the training run — a service we operate, or the user's own
  GPU box under their credentials?~~ — answered by M7 (ADR-070): **the
  user's own machine, dispatched by the agent's own shell.** Not a service
  we operate, and M7 built no dispatch machinery at all — no network I/O, no
  daemon, no new op. You copy two files to a box, run
  `training/cadex_train.py`, and copy one file back; it comes into the
  project the way every other byte does, through `put_asset` (ADR-043).
  Three independent mechanisms would each have to be breached for a worker
  to open a socket, and none of them was touched. The related product
  question — **is there a train button?** — is answered in the same ADR:
  *no, and there is nothing to press.* The agent authors the task,
  dispatches the run, and declares the result; VISION principle 5 is
  untouched.
- ~~Does the policy asset extend `put_asset` (which today gates extensions
  to STL/OBJ/PLY) or get its own op?~~ — answered by M7 (ADR-070): **it
  extends `put_asset`, and the deciding cost is a `shell/` diff.** A new op
  needs `OP_ARG_SPECS`, `OP_RESPONSE_SPECS`, both `docs/INTEGRATION.md`
  tables, a golden fixture, a handler — *and* `cadexd_client.py` in the
  add-on, which is exactly the diff ADR-063 says the branch rests on not
  having. Widening the store's accepted suffixes costs none, and it works
  because `put_asset` and `import_geometry` perform **no** suffix check of
  their own: they pass the path through and let the engine refuse.
  `_ASSET_SUFFIXES` therefore keeps its exact three members — the shell
  mirrors that constant by name in a comment — and `_STORED_ASSET_SUFFIXES`
  is the union that the store actually uses. What is left is one rough edge,
  taken deliberately: the tool is called `import_geometry` and advises
  `mesh.import_file(...)` on success, which is wrong for a policy. Fixing
  the wording is a `shell/` diff, so the engine-side refusals carry the
  correct advice instead.
- Is there a Phase 11 story here? A pybind11 binding over OCCT and a
  MuJoCo integration are independent, but the `assembly` domain is
  Phase 11f — the largest — and this plan puts new weight on it.
