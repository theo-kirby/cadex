# MUJOCO-SLICES.md — the dynamics arc, slice by slice (M0–M9)

> **HISTORICAL (moved to `docs/history/` 2026-10-10, ADR-629).** Dated records cut out of `docs/MUJOCO.md`; never cite them as current. The live doc is `docs/MUJOCO.md`.

Moved verbatim from `docs/MUJOCO.md` §4. Section numbers it cites (§3, §5, §6, §7)
are that doc's.

Numbered **M0–M8** to avoid colliding with ROADMAP's phases. The whole
sequence **is** ROADMAP Phase 14, and all nine slices are closed (M8,
ADR-085). Every slice is a resting place: the product works at the end of
each one, which is what made stopping at any of them survivable.

---

### M0 — Decide, depend, deliver `(ADR-075, ADR-076)`

The paperwork slice, and it was not as small as billed.

ADR-075 records the direction: dynamics is in scope, MuJoCo is the engine,
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
`CARRIED_PYPI_PACKAGES` to carry it into the payload by name (ADR-076). The
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

**Result: passed, with an empty shell diff.** Both halves — the pure one
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
does between frames (§5 hazard 6, ADR-079).

---

### M2 — `assembly` → `mjSpec` `(DONE 2026-07-30, ADR-077)`

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
no shell diff. Engine suite **447 passed** at closure (445 at the ADR, plus
the two that came with the `describe_api` note and the `CadexDynamics`
tidy), and the **packaged lifecycle gate 7 passed** against a payload
restaged from the closing commit — which is the gate that matters, since
ADR-023's rule is that a passing source tree proves nothing about a
payload. `pixi run gate` passed at M2's verification commit and has not been
re-run since, because the branch has never contained a shell diff to
invalidate it: `git diff main...MJC` names no file under the shell tree. That
invariant, not a repeated run, is what the shell claim rests on.

Closed 2026-07-30 with its two documentation debts paid: `docs/VISION.md`
gained the scope ADR-075 owed it and `docs/ROADMAP.md` gained Phase 14, both
as branch-marked appended blocks per ADR-078. **Nothing in M2 is left
open.** What M2 deferred is named in ADR-077's "not in this slice" list and
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

### M3 — Dynamics for real `(DONE 2026-07-30, ADR-079)`

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
- **Prove OndselSolver's own byte reproducibility.** ADR-077 made this the
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
  `CARRIED_PYPI_PACKAGES` exception — the thing ADR-076 named so it would be
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
every trace and moves nothing — silent, which ADR-077 called strictly worse
than loud.

**Phase 6 — the falling thing.** A mechanism that topples, lands, and stops,
with contact doing the work.

**Done when:** a thing falls over correctly, and does so identically twice
in two different processes.

**Done, and closed.** A mast hinged level on a post swings down under
gravity alone, slaps a floor slab it is not jointed to, rebounds through
twenty degrees, comes back, and by 1.25 s is motionless to under a
micro-degree — end to end through the live cadexd gate, with no protocol
change and no shell diff. The same script through two separate cadexd
processes writes the same artifact byte for byte. Engine suite **556
passed** (447 at M2's close); the **packaged lifecycle gate 8 passed**
against a payload restaged from the closing commit, and the collision and
cross-restart suites pass against that same payload, which is what proves
Qhull is really in it. `pixi run gate` was not re-run and did not need to
be — `git diff main...MJC` still names no file under the shell tree.

**What the six phases learned by measuring**, and the plan's own corrections
are in ADR-079 in full. The six that contradict a name, a default or a
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

### M4 — Actuators and closed loop `(DONE 2026-07-30, ADR-080)`

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
protocol change and no shell diff. Engine suite **684 passed** (556 at
M3's close); the **packaged lifecycle gate 8 passed** against a payload
restaged from the closing commit, with the actuator and cross-restart suites
passing against that same payload. `git diff main...MJC` still names no file
under the shell tree.

**Units are in the parameter names, and the wrong one is a refusal.** Every
quantity whose meaning depends on whether the joint coordinate turns or
slides gets a suffixed pair — `control_deg`/`control_mm`,
`stiffness_nmm_per_deg`/`stiffness_n_per_mm`,
`torque_limit_nmm`/`force_limit_n`, `armature_kgmm2`/`armature_kg`, and four
more. That is more names than one `control=` plus a `motion_type` would need,
and it is hazard 1 answered in the surface: the two readings of
`stiffness=4000` differ by five and a half million, and a `control="30"` that
means radians is a 57× error that runs and errors nowhere.

**Six things phase 0 measured**, four of which moved a decision; ADR-080 has
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

### M5 — The model leaves the building — **closed (ADR-081)**

`assembly.mjcf(assembly, bodies, ...)` — a new publishable xscript output
that writes one self-contained MJCF file carrying exact OCCT inertia and a
keyframe at the pose the assembly solver produced. **No protocol change and
no shell diff**, which is the invariant ADR-078 says the shell claim
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
  ADR-078.
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
four-bar fixture (`qpos = [0.873, −0.702, 0.966]`); a planar loop of
revolutes reached a live gate only once ADR-595 accepted the native
solver's redundancy count for a one-freedom loop.

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
no protocol change and no shell diff. The packaged gate is **9 tests**.

---

### M6 — A task is part of the script — **closed (ADR-083)**

`assembly.task(model, ...)` — a new publishable xscript output that writes
one JSON bundle describing a trainable task, beside the model it
references. Four new intermediates compose it: `assembly.observation`,
`assembly.reward`, `assembly.termination`, `assembly.randomise`. **No
protocol change and no shell diff**, which is the invariant ADR-078 says
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
* **The same trap, one derivative up** (ADR-112, added after B5):
  `component_linear_velocity` reads the velocity of *one link's frame
  origin*, which is not the velocity of the machine's centre of mass. On
  `mg-legs` the pelvis frame differs from the true whole-body CoM velocity
  by **19%** at recovery speeds — 9 mm of capture-point error at 400 mm/s,
  against a 24.5 mm backward support margin. `centre_of_mass_velocity`
  (`mjSENS_SUBTREELINVEL`) is the ninth kind and exists for that reason;
  the two channels agree at rest and nowhere else, which is what the
  measured test pins.
* **And the rotational half of the same trap** (ADR-116, added after B6):
  `component_angular_velocity` reads how fast *one link's frame* is
  turning, which is not the machine's angular momentum about its own centre
  of mass. `centroidal_angular_momentum` (`mjSENS_SUBTREEANGMOM`) is the
  tenth kind, in **N·mm·s**. It is what a *tipping* failure is written in —
  every B6 death was `tipped` and not one was `collapsed` — and the
  strongest statement of the difference is the one the measured test makes:
  kick a child link alone and the parent's frame reads **exactly zero**
  while the subtree carries real momentum. A machine can be upright, still,
  and already going over.
* **A one-sided limit reports its declared pair intact** (`[None, 95.0]`),
  so the refusal says *which* endpoint is missing rather than merely that
  one is.

**Who reads a channel, and what measures it (ADR-408).** Every channel
above is something MuJoCo can read; far fewer are something a small robot
can. An observation carries a `role`: `policy` (the default) is an input the
trained network reads on the machine, and `privileged` is a
simulation-only quantity the reward, the terminations and the trainer's
critic may read and the shipped policy never does. A policy channel is
*grounded* when it names the `api.sensor` that measures it on the robot:

| sensor kind | declared on | grounds |
|---|---|---|
| `imu` | the IMU board's own `api.component` | that component's `component_orientation` and `component_angular_velocity` |
| `joint_encoder` | an `api.joint` | that joint's `position` and `velocity` (a servo's potentiometer tapped out, or a servo that reports position) |
| `position_tracker` | the `api.component` it is mounted on (a touch panel's plate, a camera's mast) | *another* body's `tracked_position` in the mount's frame (ADR-588), and its differenced `tracked_velocity` (ADR-590) |
| `load_sensor` | an `api.actuator` with an effort limit (a bus servo's load register, a current sensor on a motor's supply) | that actuator's `actuator_force`, rounded, noised and held within its stall line (ADR-591) |

The API refuses a sensor that does not measure what it is passed to, or
that is mounted on something else. An ungrounded policy channel still
builds, and the exported task marks it, and **`cadex train` refuses to
train on it** unless given `--allow-ungrounded`. The keys this adds to a
task row (`role`, `grounded_sensor`, `grounded_kind`) appear only when they
are not the default, so a task written before ADR-408 exports
byte-identical and every policy trained on it still verifies. The trainer
is an asymmetric actor-critic: the actor reads the policy channels, the
critic and the running normaliser read every channel, and the policy
header lists the actor's channels only, which is what
`CadexDynamics.policy_channels` verifies it against. The motivation is
hex2 (2026-09-25): a hexapod whose policy read joint angles its MG90S
servos cannot report and a centre-of-mass velocity nothing on it measures.

**A position tracker reads a free body (ADR-588).** A touch panel reading
a ball, or a camera reading a marker, is a `position_tracker` declared on
its mount with a datasheet: `range_mm` (a box in the mount's frame),
`resolution_mm`, `rate_hz` and `noise_mm`, all required. Its
`tracked_position` is a stock `framepos` sensor with the mount as
`reftype="xbody"`/`refname`, so MuJoCo computes the body's position in
the mount's frame through every tilt and turn. The task row carries
`frame` and the `tracker` declaration, and four channels over a three-wide
slice: `<name>_x/_y/_z` and `<name>_in_range`. `tracker_reading` (engine)
and its `jnp` copy in `training/cadex_train.py` (pinned equal by
`test_dynamics_position_tracker.py`) apply it: inside the range on every
axis — judged on the true position — the reading is rounded to the
resolution and the flag is 1; outside, every value is 0, never a clamped
edge or the last reading. The trainer adds Gaussian noise of the declared
spread, drawn per control step, to what the actor and critic read, before
the rounding; the reward and terminations read the noise-free reading, and
evaluations draw no noise. A tracker whose `rate_hz` is below the task's
control rate is refused (`tracker_slower_than_control`) rather than held,
so a policy never acts on a reading the part has not made.

**Its velocity is the firmware's difference (ADR-590).** A panel's
controller subtracts successive readings `1 / rate_hz` apart, and so may a
policy: `assembly.observation(body, "tracked_velocity", sensor=tracker)`,
listed after the same tracker's `tracked_position` of the same body
(otherwise `observation_tracker_velocity_unpaired`), reads `<name>_x/_y/_z`
in mm/s. It is a stock `framelinvel` with the mount as reference — the
exact derivative of the tracked position, the frame's own rotation
included — with the noise of a difference, `sqrt(2) * noise_mm *
rate_hz`, drawn per step, and one resolution step per interval,
`resolution_mm * rate_hz`, as its quantum (`tracker_velocity_reading`, its
`jnp` copy pinned equal). It reads zeros whenever the position's
`_in_range` is 0, and its normaliser floor is the larger of those two,
squared. What it does not model: the half-interval lag of a difference and
the anticorrelation of successive differences' noise, both small at a
panel's rate. A velocity no part reports, a world `component_linear_velocity`,
stays privileged.
The running normaliser follows the noisy readings the policy acts on, not
the noise-free ones the reward reads, and holds each tracked axis's
variance at no less than the larger of its resolution and noise, squared,
and the in-range flag's at no less than 0.25 (ADR-589): an axis the body
barely moves along — a ball's height above the panel it rolls on — would
otherwise reach the policy at tens of standard deviations of pure noise,
and a lost touch at thousands.

**A load sensor reads what an actuator applies (ADR-591).** A bus servo
reports its load over the bus and a current sensor reads a motor's supply;
a hobby PWM servo reports nothing back. `assembly.sensor(actuator,
"load_sensor", resolution_nmm=, noise_nmm=, rate_hz=)` (`resolution_n` and
`noise_n` on a sliding coordinate) declares one, and grounds that
actuator's `actuator_force` — the stock `actuatorfrc` sensor, already
clamped by MuJoCo at the actuator's `forcerange`. Its full scale is the
actuator's own `torque_limit_nmm` (or `force_limit_n`), the stall line,
and an actuator without one is refused. The task row carries `load`
(`full_scale`, `resolution`, `rate_hz`, `noise`); `load_reading` (engine)
and its `jnp` copy in the trainer (pinned equal by
`test_dynamics_load_sensor.py`) add the noise drawn per control step,
hold the result within `±full_scale`, and round it to the resolution. Its
normaliser floor is the larger of resolution and noise, squared, and a load
sensor slower than the control loop is refused
(`load_sensor_slower_than_control`). `lib.servo(sku).load_sensor(actuator,
name=)` is the catalog's path: a servo whose row carries `load_feedback`
(the STS3215: its Present Load register, 0.1 % of full drive per count,
with 1 % noise and 100 Hz polling assumed) fills those figures as
fractions of the actuator's stall torque, and every PWM servo refuses with
the reason. What it does not model: the register reads drive duty, which
equals load only near stall — a turning motor's back-EMF takes a share —
so at speed the real reading runs above the simulated one.

**A goal can be a clock (ADR-598).** `assembly.goal(..., kind="phase",
period_seconds=T)` is a bundle row with `low` 0, `high` 2π, `nominal` [0],
`period_s` and `radians_per_step` (2π·dt/T), and `goal_algorithm` gains
`GOAL_PHASE_ALGORITHM` only where one is stated. Its start phase is drawn
by the value draw already stated, so the engine, the trainer's host pool
and the reference runner draw the same numbers; at step s the angle is
`start + radians_per_step * (s - segment start)`, read as `name_sin` and
`name_cos` by `CadexDynamics.goal_values` and the trainer's
`phase_channels`. It is the only channel that carries time, because the
trainer's reset does not rewind `data.time` and a MuJoCo `clock` sensor
would therefore read wrong after the first episode.

**A goal can be held in a body's frame, and a position read in one
(ADR-592).** `assembly.goal(..., kind="point", frame=base)` draws its
target as any point goal is drawn, then keeps it as
`transpose(xmat[frame]) * (p - xpos[frame])` at the drawn pose: the bundle
row carries `frame` and `frame_id`, `goal_algorithm` gains
`GOAL_FRAME_ALGORITHM`, and the engine, the trainer's host-side pool and
the reference runner keep the same numbers. The goal channels are then the
target as the base sees it, which is what the policy reads. The reward's
partner is `assembly.observation(tip, "component_position",
frame=base, role="privileged")`, exported as a stock `framepos` with
`reftype`/`refname` — the same element a tracker's reading is, with no
noise because nothing measures it. `CadexEvaluation.reach_metrics` reads
the tip in the frame at every frame of the trace, so a base that drifts
carries its target with it and the error is to where the target was; an
evaluation trace adds the frame to `goal_channels`, and the film places the
marker with the frame's pose. A world goal's bundle and digest are
unchanged.

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
change and no shell diff. The packaged gate is **10 tests**.

`cadex_tests/dynamics_task_episode.py` **is** the environment. M7 becomes
dispatch rather than debugging.

---

### M7 — Training happens elsewhere — **closed (ADR-084)**

`assembly.policy(task, weights=..., sha256=...)` — a publishable xscript
output that names a trained policy by file and digest, verifies it against
the task it claims, and writes one receipt. Plus `training/cadex_train.py`,
a Cadex-free PPO trainer at the repository root that reads an M6 bundle and
writes one `.cxpolicy`. **No protocol change and no shell diff.**

**The honest constraint, unchanged:** training does not run on the user's
laptop. MJX needs JAX-on-GPU, JAX's Apple Silicon story in 2026 is
`jax-metal` 0.1.0, MuJoCo Warp needs CUDA, and the published reference — a
Unitree G1 walking policy in ~90 minutes — is 4096 parallel environments on
an RTX 4090. On CPU that is days.

So training is **offboard by design**, and M7 confirms it is a clean
boundary rather than a compromise. It makes the *engine* simpler: the engine
verifies a policy and never produces one, so it needs no optimiser, no
autodiff, no accelerator and — measured, see below — no numpy.

**The three questions ADR-082 named as M7's, answered:**

| Question | Answer |
|---|---|
| Where does training run? | The user's own machine with a GPU, dispatched by the agent's shell. M7 ships a movable run directory and a trainer; it builds **no dispatch machinery, no network I/O, no new op**. |
| Does the policy extend `put_asset` or get its own op? | **Extends `put_asset`.** A new op would cost a shell diff — `cadexd_client.py` — and ADR-078 says the branch rests on there not being one. Widening the store's accepted suffixes costs none. |
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
| MJX sensordata, the eight observation kinds M7 had, worst channel | **3.5e-7** |
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

**ADR-083's central claim survived the trainer.** MJX evaluates every
observation kind and vectorises them exactly, so *MuJoCo computes the
observation vector* still holds and no fourth implementation was needed —
which was risk 2, and it did not fire. Nor did risk 1: MJX carries our
equality constraints and our mesh geoms, so the batched-CPU-`rollout`
fallback was never reached.

**It survived the ninth kind too** (ADR-112). A kind stock MuJoCo computes is
not automatically a kind MJX computes, and the failure is silent — an
unimplemented sensor comes back as **zeros**, not as an error, so a reward
term built on it trains as whatever is left when that channel is 0. Ask MJX
directly before spending a run on a new kind: given the **same state**,
`SUBTREELINVEL` agrees with stock MuJoCo to **7.3e-08 m/s**, the same
float32 order as the 3.5e-7 above.

**And the tenth** (ADR-116): `SUBTREEANGMOM` agrees to **6.5e-07 relative**
in float32 and **1.3e-15** with x64 on, over six randomised poses, and
returns a non-zero value where stock MuJoCo does. That check now lives in
the suite rather than in a one-off script —
`test_dynamics_mjx_agreement.py` asks it of the exported fixture, and
`test_dynamics_policy_measured.py`'s coverage test compares its row list
against `OBSERVATION_KINDS` as a set. The latter is a repair: it was written
against a literal count of eight, ADR-112 added a ninth kind without adding
a row, and an MJX-gated test that `pixi run test-engine` skips is exactly
the kind that goes stale unwatched.

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
  `CARRIED_PYPI_PACKAGES` stays one entry long, which is what ADR-076 named
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

**What the live training gate proves, and what it does not.** The gate
trains a *tiny* task — one hinge, swing-up, 150 iterations, 128
environments — on **CPU**, because that is what a test machine has, and it
takes the best of three seeds, stopping at the first that converges: PPO
from a fixed seed is bimodal on this task (a converged run scores 3.3+
reward per step, a failed one 0.9–1.8, and a zero-torque episode about
0.9), and *which* seeds win is platform arithmetic — seed 0 converged on
the machine that authored the gate and plateaued on an M4 Mac Mini. One
attempt is ~7 s on that M4. Note the gate runs only where jax does — the
pixi CI environment deliberately lacks it, so it skips there and a venv
run is what actually exercises it. **The GPU is a speed difference, not a
semantic one, and it is the same trainer file — but this gate does not
prove the GPU path.** A remote GPU run is exercised manually.

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
no protocol change and no shell diff. The packaged gate is **11 tests**.

---

### M8 — The policy comes home — **closed (ADR-085)**

`assembly.rollout(policy, frames_per_second=..., seed=...)` — the verified
policy plays against the model its task bundle names, and the rollout leaves
as `cadex-assembly-simulation-trace-v1`. The shell baked it with the code it
had had since ADR-050 (since ADR-498 the dashboard plays it). **No protocol change and no shell diff**, for the
third slice running.

**A new operation and no new output type**, which is the whole design. A
rollout produces a `simulation`, the type `api.simulation` and `api.dynamics`
already share, so the "exactly one simulation" rule and the `api.motion`
incompatibility catch a rollout for free — and so does the shell's bake,
which never learned that a third kind of producer exists.

**Nothing here was a discovery.** M6 wrote `evaluate_episode`'s `actions=` as
a callable so that a policy could be dropped into it and said so; M7 wrote
`policy_forward` to emit in the bundle's advertised units so that no
conversion would be needed at the seam; M2 gave a dynamics run the shared
output type so a third producer would need no shell work. What M8 adds to the
pure module is **sampling**: `evaluate_episode` gained a keyword-only
`sample` callable invoked at control-step boundaries, and `rollout_policy`
turns what it returns into frames. One episode loop stays one episode loop —
M7 already made three evaluators of the reward whitelist, and a second
stepping loop would have been a fourth place for the same drift.

**What was measured before anything was built** (phase 0,
`test_dynamics_rollout_measured.py`, 6 tests — and unlike M7's phase 0,
**none of it needs MJX**, because M8 measures the engine rather than a
trainer):

| Finding | Number |
|---|---|
| Reloaded model vs the one in memory, same policy, one episode | **8.1e-6 at step 1, 5.8e-3 worst** |
| ...their episode reward totals | **9.4e-6 apart** |
| A policy-driven rollout across two processes at a fixed seed | **byte-identical** |
| float32 vs float64 forward pass, compounded over an episode | **2.8e-5 at step 1, 5.8e-3 worst** |
| ...their episode reward totals | **7.0e-6 out of 61.9** |
| A ten-second 50 Hz episode, 4609-parameter net | **85 ms**, 0.17 ms/step |
| 50 Hz control played at 60 fps | frames 1, 2, 4 land **between two actions** |

**Two of these mattered:**

* **Reloading the model is load-bearing, not tasteful.** The plan chose to
  reload the exported MJCF on the rule M6 and M7 follow — resolve against the
  bytes somebody else opens — and expected the two models to agree. They do
  not: the XML writer's six significant figures become a different trajectory
  within a hundred closed-loop control steps. So *which* model ran is a fact
  about the numbers, and the answer is the file the policy's digest attests
  to.
* **The trajectory is not portable and the reward is.** The float32/float64
  gap M7 measured at 1.7e-9…3.6e-8 for one forward pass compounds five orders
  of magnitude over an episode, while the total survives it and each precision
  reproduces itself exactly. The trace's sha256 is therefore a claim about
  **this engine's own arithmetic**, never about somebody else's inference of
  the same weights — recorded here rather than discovered in a gait.

**`frames_per_second` must divide `control_hz` exactly** and defaults to it.
This is `simulate`'s solver-step rule one level up: an action is held for a
whole control step, so a frame between two of them makes the trace depend on
floating-point accumulation. The refusal lists the rates that task can be
played at, which matters because the *policy* picked the control rate.

**Done when — and it is:** a mechanism designed in Cadex, a task defined in
M6, a policy trained offboard in M7 and verified on arrival, played by the
engine and baked by the shell. Through the live cadexd gate; the packaged
gate is **12 tests**. The bake is real evidence rather than a formality:
`rollout_bake_integration.py` writes a trace from a live `cadexd` and bakes
it inside the shipped bundle through the shell's own `cadex_animate`
functions — **357 keyframes per component**, the grounded base stationary,
the swing arm translated and rotated. *(Since ADR-495 the shell is disabled, and since ADR-498 deleted,
and the file is `rollout_review_integration.py`: the same live trace — 52
solver frames, base stationary, swing arm moved — is read through the review
dashboard's own trace reader instead of baked.)*

At which point the agent can be asked for a robot, and answer with one that
walks.

---

### M9 — The episode stops starting in the same place — **closed (ADR-097, ADR-098, ADR-099; follow-ons M9b ADR-100, M9c ADR-101)**

M8 closed the arc and M9 is what reading the result of it forced. `mg-legs`
stood, and ADR-096's Policy Outputs panel showed **how**: it held
`hip_pitch_l/r` and both knees between 93 % and 99 % of the MG90S limit for
the entire six-second episode while both ankles sat under 72 N·mm. It did not
balance — it **braced**, widening its stance from ±30.00 mm to ±37.2/37.4 mm
and pulling the right foot 13 mm back, then holding that splay with torque.

Three separate things made that the winning strategy, and M9 addresses all
three:

1. **216 N·mm was available.** That is MG90S *stall* — a momentary rating. No
   servo holds 98 % of stall for six seconds. `mj_inverse` measures static
   standing at **2.39 N·mm** and a hand-written PD peaks at **4.5**, so the
   213 N·mm was entirely self-inflicted.
2. **Bracing was cheap.** Effort is weighted −0.0002/N·mm, so pinning four
   motors costs ≈0.17 against a +0.39 reward/step, while falling costs the
   alive bonus, the tilt penalty *and* the rest of the episode.
3. **Nothing ever disturbed it.** Every episode reset to the identical
   keyframe with `qvel = 0`, and `_RANDOMISATION_TARGETS` varies only
   `mass`/`damping`/`armature`/`friction_loss` — drawn per environment and
   held fixed for the run. A posture found once was never tested, so
   "balance" was never the task.

#### The mechanism (ADR-097)

Two new intermediates beside `assembly.randomise`, both passed to
`assembly.task`:

```python
start = assembly.reset_variation(pelvis_c,
                                 tilt_degrees=[0.0, 6.0],
                                 height_mm=[5.5, 9.0],
                                 angular_velocity_dps=[-20.0, 20.0])
shove = assembly.disturbance(pelvis_c, newtons=[0.05, 0.35],
                             direction="horizontal",
                             at_seconds=[1.0, 2.5], duration_s=0.12)
wind  = assembly.disturbance(pelvis_c, newtons=[0.0, 0.08],
                             direction="horizontal", sustained=True)
```

**One entry is one event.** Three shoves is three entries — the shape
`randomise` already has, and what keeps the draw order statable in one
sentence. Wind is a push whose window is the whole episode, which is why
there is no second surface for it.

**Two more knobs since ADR-104**, both additive and both defaulting to what
the block above already did:

```python
start = assembly.reset_variation(pelvis_c, tilt_degrees=[0.0, 15.0],
                                 height_mm=[15.0, 45.0],
                                 angular_velocity_dps=[-90.0, 90.0],
                                 linear_velocity_mm_s=[0.0, 250.0])
shove = assembly.disturbance(pelvis_c, newtons=[0.15, 0.9],
                             direction="horizontal",
                             azimuth_degrees=[-60.0, 60.0],
                             at_seconds=[0.3, 1.5], duration_s=0.12)
```

`azimuth_degrees=[lo, hi]` aims a horizontal push at an arc about **world
+X**, anticlockwise seen from above; omitted is the full circle. The engine
has **no concept of which way a mechanism faces** — work out which world
axis your machine's forward is, from where its feet and toes sit, before
declaring an arc. For mg-legs forward is **+Y**, so the `[-60, 60]` above is
a *lateral* band, not the sagittal one it was written to be (ADR-107). Then
aim it where the mechanism has actuators — a machine with no ankle roll
drawn over the whole circle spends most of every batch on a question it
cannot answer, which ADR-087 predicted and `capability.py` measured. It is
**refused on a vertical push**, whose draw is a sign rather than an angle,
and it adds no draw to the stream.

`linear_velocity_mm_s=[lo, hi]` is a **stumble**: a speed with its azimuth
drawn, written into the base's *world-frame* linear velocity — the other
frame from the angular velocity beside it, which is MuJoCo's asymmetry. It
gives every episode a recovery to do from step 1 instead of a second of
standing still, and it is safe for the reason the rigid tilt is: it cannot
change the mechanism's shape. This one **does** add two draws per reset
variation, taken unconditionally, so a bundle written before ADR-104 replays
a different sequence.

The floor should be a **`plane`** (also ADR-104): a plane's surface is its
own origin where a box's is its top face, so it needs none of the offset
ADR-074 records — and ADR-103 measured the box floor as the one place MJX
and stock MuJoCo disagree.

**What phase 0 measured, before any surface was written:**

| Question | Answer |
|---|---|
| Where does `xfrc_applied` act? | The body's **centre of mass**. A 1 N push on a body whose mass sits 100 mm from its frame origin gave **zero** angular acceleration; the frame-origin hypothesis predicted 10 rad/s². |
| In which frame? | **World.** The same world-frame force on the body yawed 90° gave the same world-frame linear acceleration. |
| A free joint's `qvel[3:6]`? | The **body's own frame**. Set to `(1,0,0)` on a body yawed 90°, the world angular velocity reads `(0,1,0)`. |
| Is a joint-angle perturbation survivable? | **No**, and this is the load-bearing finding. |

That last one shaped everything. The reset pose is the *solved* configuration
with the soles exactly on the floor; a ±3° knee jitter moves a foot ~5 mm
through the floor and MuJoCo answers that with an impulse nothing could stand
up to. **So a reset variation perturbs the free root rigidly and perturbs
velocities — never joint positions.** A rigid tilt plus a lift cannot change
the mechanism's shape, so it cannot self-interpenetrate however far it leans.

**The lift is measured, not reasoned about.** A tilt swings the far side of a
stance downward, so `height_mm` is what pays for `tilt_degrees` — and the
engine applies the widest declared tilt at the smallest declared lift at
sixteen azimuths, reads the deepest contact, and refuses the pairing that
does not clear, with the millimetres in the message. This immediately caught
its author: `mg-legs` was written with `height_mm=[0.0, 3.0]` against a 6°
tilt on the reasoning that 6° across a ±30 mm stance is about 3 mm at the
sole. The engine printed **5.13 mm at 135°**. The estimate was wrong because
a tilt pivots about the base's own *frame origin*, and the far thing from the
pelvis origin is not the near sole edge — it is a toe, diagonally, most of a
leg away.

**Two seeding algorithms, both stated in the bundle.** Model randomisation is
unchanged: `random.Random(base_seed + env)`, per environment, held for the
run. Episode variation is per episode — the engine and the reference runner
use `random.Random(seed)` continuing in bundle order, and the trainer uses a
split `jax.random` key inside the jitted loop, because the draw happens on
device every time an environment resets. **They deliberately do not produce
the same numbers and the bundle says so.** Nobody replays a training episode;
what VISION principle 3 requires is that the *rollout* be reproducible from
the script, and that is the stdlib path.

Both streams draw the same number of values whether or not a branch uses them
— three per disturbance, six per reset variation. A stream whose *position*
depends on a branch is a stream two implementations get wrong differently.

**Three evaluators, one arithmetic** — hazard 1's seventh payment, and the
same mitigation that worked six times: everything resolves to **indices at
bundle-build time** (qpos/qvel addresses, body id), so no evaluator
introspects the model, and the six-line quaternion product is written out in
all three places rather than shared through a helper two of them cannot call.

Budgets are separate: `MAXIMUM_RESET_VARIATIONS = 4`, `MAXIMUM_DISTURBANCES =
8`, because `MAXIMUM_RANDOMISATION_ENTRIES` was already 31/32 spent on
mg-legs and a shared ceiling would have made "vary one more mass" and "add
one more shove" compete for one seat.

**Not a protocol change.** `assembly.*` is the xscript surface, not the
cadexd op table, so `CadexdProtocol.OP_ARG_SPECS` and `docs/INTEGRATION.md`
are untouched.

#### The run stops being a black box (ADR-098)

`--checkpoint-every N` writes a **complete, witness-checked `.cxpolicy`**
mid-run — not a weight dump — plus `<out>.best.cxpolicy` tracking the best
`reward_per_step`. mg-legs peaked at iteration 1200 of 2000, so roughly
thirty of its seventy-six minutes made the policy worse; `.best` alone would
have saved them. Cost is about one iteration each, so every hundredth of two
thousand is one per cent.

The witness check runs on checkpoints too, which is ADR-094's lesson applied
where it now costs nothing: the error is *relative* and grows with the
activations a policy learns, so a checkpoint that fails it is a run that is
going to fail it.

`progress.json`, rewritten atomically every iteration, is the one artifact
everything downstream reads. `remote_train.sh` gained `train --detach`,
`watch`, `pull` and `stop`; `watch` mirrors the file to
`training-progress.json` beside the project, which is what the shell's
Training panel polled (deleted with the shell, ADR-498). **No ssh in the shell, no protocol change, no engine
change** — and nothing parses a log, which is ADR-093's finding kept.

**Two bugs the dispatch work surfaced, both silent:**

* **`train.pid` held the wrapper, not the trainer.** `echo $!` after
  backgrounding records the subshell and `setsid` forks again on top of it.
  Measured on a live 5090: `stop` reported "stopped", killed the subshell,
  and left a 4000-iteration run training with nothing pointing at it. The
  inner shell now writes its **own** pid and then `exec`s, and `stop`
  verifies with `kill -0` rather than trusting `kill` returning zero.
* **`shquote` was wrong in bash 3.2.** The `${1//.../...}` form turns `a'b`
  into `'a\'\\'\''b'` rather than `'a'\''b'`. Nothing had ever passed it a
  string containing a quote, so it worked for a year and then broke the first
  command that did — with an error pointing at the wrong line.

#### The re-rating, and the gate re-spec (ADR-099)

`MG90S_STALL_NMM = 216.0` → **`MG90S_CONTINUOUS_NMM = 86.0`**, ~40 % of
stall. This is an **engineering judgment, not a datasheet number** — hobby
servos publish no continuous rating — and it is stated rather than buried so
that if the machine cannot stand at it, the number moves with the reasoning
recorded. It is still ~19× the measured static requirement.

**The feasibility gate had to be re-specified, and that is a decision rather
than a fix.** `feasibility.py`'s arithmetic column reads 117–129 N·mm at the
hip and knee; against 86 it goes red everywhere — on precisely the check
ADR-095 already established is over-conservative, because it multiplies full
body weight by a full limb length, which is a one-legged iron cross and not a
stance. Hazard 14's own instruction is that the failure mode to avoid is
*learning to click past a red gate*, so the answer is to stop printing a red
gate nobody should obey rather than to keep one and ignore it. The column
stays **printed** — it bounds what this robot could do if it had to hold a
leg out — and stops gating.

What gates in its place took **three attempts**, and the two that failed are
recorded because both looked right:

1. **`mj_inverse` with the force applied.** Measured nothing. Inverse
   dynamics on a floating base solves for the force needed at *every* dof
   including the six unactuated ones, so a horizontal push at the pelvis is
   absorbed by the free joint's own residual and the leg torques come back
   **bit-identical to the undisturbed case** — 2.39 N·mm at every hip, worst
   azimuth 0° for all eight, which is the signature of a number that was
   never computed.
2. **The hand-written PD, pushed.** It fell from every direction on a 0.042
   N·s impulse — but a *joint-space* PD holds joint angles and has no
   base-attitude feedback, so it cannot resist the whole machine rotating
   about its ankles however good the mechanism is. That is a fact about the
   controller, and gating a mechanism on it would fail every mechanism.
3. **The statics** — which is the same question ADR-095 asked about the foot.
   A horizontal force `F` at height `h` is a moment `F·h`, and exactly two
   things resist it: the footprint (the centre of pressure cannot leave the
   sole) and the ankles.

Measured, on the re-rated build:

| Quantity | Value |
|---|---|
| Worst instant the task's windows allow | 0.080 N sustained + 0.350 N for 0.12 s |
| Righting moment that needs, at a CoM 146.0 mm up | **62.8 N·mm** |
| The footprint can give (2.581 N × 45.5 mm) | 117.4 N·mm |
| The two ankles can give (2 × 86.0) | 172.0 N·mm |
| So the machine has, and what binds | **117.4 N·mm — the foot** |
| Margin | **1.87×**; the CoP moves 24.3 mm of 45.5 mm |

The first version of even *this* check summed all three declared forces and
held them for three seconds — 2.34 N·s against the 0.042 N·s a 0.35 N shove
lasting 0.12 s actually delivers, 56× — which is the arithmetic column's
mistake in a new costume. The windows are read now.

**Which constraint is active changed, and that is a mechanical improvement.**
At 216 a single ankle could out-torque the whole footprint by 1.8×, so the
machine could tip *itself* by over-torquing one ankle. At 86 no single ankle
command can roll a foot.

**Success metric, decided before dispatch:** recovery rate — episodes
surviving a shove over episodes shoved — **not reward**. The curve gets
noisier with variation in it, ADR-088's stopping rule gets harder to apply,
and the +0.391 baseline is no longer comparable to anything. `compare.py`
plays every checkpoint locally against five seeds and prints survival,
drift, tilt and peak/mean torque per motor.

**The first disturbed run may well fail, and that is the correct outcome to
report rather than iterate on** (ADR-088). A policy with no torque headroom
cannot reject a push; that is the whole finding. A shove big enough to need a
*step* cannot be answered at all, because the toe is welded and this policy
has no gait — which is why the shove is sized from what the ankle can absorb.

**Deliberately not in this slice:** walking and stepping (the toe is still
welded, so recovery means in-place recovery); thrown blocks (the same force
to the policy as a shove — a demo of this mechanism, and it belongs after the
policy can take one); live policy rollout in the UI (the shell may never
import mujoco, so that is a streaming-rollout feature over the existing
protocol and its own slice); and training video streamed from the box (the
progress file is the contract).

#### M9b — the shove never left the foot (ADR-100)

**No engine, trainer or shell change: all three findings below are project
script.** M9 dispatched, the run stood, and watching it showed hips moving
while the ankles and knees stayed put and the feet never left the floor. It
looked like there were sandbags in the feet. There were not — three
measurements say what was actually happening, and each one is a number in
`~/cdx-mjc/mg-legs.cadex/script.py`.

**1. The push never left the foot.** The right measure of a shove is the
**capture point** `ξ = v/ω₀` with `ω₀ = √(g/h)` — how far ahead of the feet
the centre of mass would have to be caught. Measured off the export: `h` =
146.0 mm so `ω₀` = 8.20 rad/s, mass 263.1 g, support polygon 45.5 mm forward
/ 24.5 mm back / ±50 mm lateral. The M9 shove of 0.35 N × 0.12 s is 0.042 N·s
→ 0.16 m/s → **ξ = 19.5 mm**, inside the polygon in every direction including
the narrow backward one. Nothing was asked of the knees because nothing
needed to be. ADR-099 sized that shove deliberately and answered its own
question correctly; the question was the small one.

**2. The reward made falling a better trade than recovering.** Price one step
of a stumble — CoM 100 mm out, moving 800 mm/s, tilted 20°, which is the
state a machine catching itself passes through:

| term | M9 weight | value there | M9b weight | value there |
|---|---|---|---|---|
| `over_feet` | −0.02 /mm, linear | **−2.00** | −0.5 × tanh(d/40 mm) | −0.49 |
| `drift` (new) | — | — | −0.002 /mm | −0.20 |
| `stillness` | −0.002 /(mm/s) | **−1.60** | −0.0005 | −0.40 |
| `height` | −0.02 /mm | −0.60 | −0.010 | −0.30 |
| `posture` (8 joints) | −0.004 /deg | −0.40 | −0.001 | −0.10 |
| `splay` (new, 2 hip rolls) | — | — | −0.004 /deg | −0.12 |
| `tilt`, `spin`, `effort` | | −0.60 | | −0.30 |
| `alive` | +1.0 | +1.00 | +1.0 | +1.00 |
| | | **≈ −4.2 /step** | | **≈ −0.9 /step** |

Falling immediately forgoes the +1 alive bonus and nothing else. At −4.2 a
150-step stumble followed by a full recovery scores *worse* than going down
at once; at −0.9 it is worth several hundred over the episode against 0 for
falling. **The policy was not refusing to step — it was correctly declining a
bad deal.** `over_feet` had to change *shape*, not weight: linear in
displacement there is no distance at which "get back" beats "go down", so it
became a saturating `tanh` plus a tiny linear `drift` term that keeps a
gradient pointing home from anywhere. Every term still reads exactly 0 at the
standing pose (hazard 9), verified term by term.

**3. The discount could not see a recovery.** `--discount 0.97` at 100 Hz is
an effective horizon of `1/(1−γ)` = 33 steps = **0.33 s**. A
stumble-and-recover takes 1–2 s, so the payoff for catching yourself was past
the policy's horizon. `--discount 0.99` is 100 steps = 1.0 s. One word.

What changed with them: shove `[0.05, 0.35]` → **`[0.4, 2.0]` N** (ξ 22 mm to
111 mm — a curriculum inside the distribution, not a schedule); reset lift
5.5–9.0 → **15–45 mm** and tilt 6° → **15°**, so absorbing a 0.54–0.94 m/s
landing is knee and ankle work before anything pushes; `collapsed` 0.70 →
**0.60 ×** standing height so a deep absorb is not instant death; two new
observation channels' worth of foot position (`ft_l`, `ft_r`, 40 → **46** of
64), because foot-relative-to-CoM *is* the state variable a step is written
in.

**What the mechanism can actually do, which is what bounds the shove.** The
leg is 100 + 95 = **195 mm**; a 45° hip swing places a foot 138 mm out, so
one step catches ξ at **183 mm forward / 162 mm backward**. The usable band
is therefore ξ ∈ 45–180 mm: past in-place recovery, inside single-step reach.
**Laterally the machine is worse and that is a mechanism fact** — no ankle
roll and no hip yaw, so sideways balance is hip_roll plus weight shift and
the CoP cannot be held at a sole's outer edge. If the trained result recovers
sagittally and not laterally, that argues for ankle-roll servos, not for more
iterations, and `compare.py` now splits survival by shove azimuth so the
question is answerable at all.

**Feasibility check 3 is re-specified a third time, for a different reason
than the first two.** Those measured nothing (above). This one measured the
right thing and the *task* moved: against a 2.0 N shove it reads 304 N·mm
needed against 117.4 available, 0.39×, red — and it is right, we now
deliberately want a shove the machine cannot reject in place. It becomes the
reach question, with the in-place number still printed:

```
in place:  capture point vs support polygon
stepping:  capture point vs support + 195 mm × sin(swing)
gate:      worst declared capture point <= steppable reach
```

Measured, green: ξ 111.3 mm against 174.9 mm forward (**1.57×**), 153.9 mm
backward (**1.38×**), 121.5 mm lateral (**1.09×**), with "A STEP IS REQUIRED"
printed rather than hidden and the lateral row called out as the mechanism's
weak axis.

**500 iterations is a probe, not a solution.** Learning a stepping recovery
from scratch typically wants 10–100× these env-steps. What the run can
honestly answer is whether the reward now points the right way: read the
peak-torque columns first (do the knees and hips move at all, above the
21–56 N·mm the M9 policy spent?), then the recovery-rate *trend* across
checkpoints. Flat at zero by 500 means the reward or the shove is still
wrong and more iterations will not fix it. Success is **not** a higher reward
number — the reward function changed, so +0.391 and +0.243 are not
comparable to anything this run prints.

#### M9c — the trainer never ended an episode (ADR-101)

**Trainer only: no engine change, no protocol change, no new dependency, and
one label row in the shell.** M9b's run reproduced M9's anti-correlation on a
task sharing nothing with it — different reward, different observations,
different forces — which made the instrument the suspect rather than the
task. Reading it found this:

```python
# training/cadex_train.py, before ADR-101
horizon = int(episode["max_steps"])     # ...and never used again
```

`done` came only from the task's `tipped`/`collapsed` terms and there was no
step counter anywhere, **so an environment whose policy did not fall over
never reset.** Past the last shove window (4.32 s on `mg-legs`) it was never
pushed again, never re-drawn, and stood still collecting `alive` +1 with
every other term near zero. The bundle declares 600 steps and
`evaluate_episode` honours it, so **the trainer was optimising a different
problem from the one the script declared** — enough on its own to make its
reward non-comparable with any evaluation.

Three things changed. The scan carries an integer step counter and truncates
at the bundle's own `max_steps`. A **timeout is bootstrapped and a failure is
not** — `terminated` cuts the bootstrap, `done` cuts the GAE carry — because
collapsing the two would teach the critic that surviving to step 600 is worth
exactly as much as falling over, a new bias traded for the old one; the
bootstrap value comes from `landed`, the post-step pre-reset observation, so
the old shifted-`values`-plus-trailing-bootstrap arrangement disappears. And
**mean episode length is reported** — stderr, `progress.json`, the policy
header's curve rows, the shell's Training panel.

**Every reward figure this branch has recorded predates the fix and is not a
baseline** (+0.391, +0.5118, +0.2149). Survival numbers are unaffected: they
come from the engine's reference runner, which always honoured `max_steps`.

**And the third reading, ADR-106: part of what looked like hazard 19 was a
task out of range.** With the instrument fixed, `capability.py` swept a
scale factor over m9c's declared shove band and the same policy that reads
0/12 at the declared 0.40–2.00 N reads **11/12 at 0.06–0.30 N and 12/12
unshoved**, on 2–5 N·mm of mean torque against a limit of 86. It stands, it
absorbs a 45 mm drop and a 15° lean, and it dies because it is asked to
reject pushes three to six times beyond its mechanism's reach. A single row
of `compare.py` cannot distinguish "has not learned" from "was never asked
something answerable"; a curve can, and that is what `capability.py` is for.
Run it before concluding anything about a run that reads zero.

What is **not** established is that this is the whole of hazard 19. The
hypothesis — the batch fills with standing-still steps, the disturbed
fraction falls toward zero, reported reward drifts up toward `alive` while
the policy forgets the states it no longer sees — predicts the observed shape
but has not been tested. **The test is M9b rerun with the identical bundle
and hyperparameters**, so the trainer is the only thing that changed:

```bash
training/remote_train.sh train <the same bundle> ~/cdx-mjc/runs/m9c/stand4.cxpolicy \
  --detach -- --seed 0 --iterations 500 --envs 4096 --unroll 20 \
              --discount 0.99 --checkpoint-every 25
pixi run python ~/cdx-mjc/compare.py --task <that bundle> ~/cdx-mjc/runs/m9c
```

**It was run — `stand-task-20260801-210806`, 500 iterations × 4096
environments, 43 minutes — and it refutes the hypothesis.** The trainer's
reward rose monotonically to **+0.175** and its episode length rose with it
**58 → 149**; played over 12 seeds the engine measured **0/12 survival at
every checkpoint**, steps peaking at **162** around iteration 125 and
collapsing to **39**, and reward falling to **−1.036**. The
anti-correlation reproduced exactly, on the fixed trainer.

**What the fix bought is a sharper question, not an answer.** Before it the
two sides could only be compared through a reward; now **the same quantity —
mean episode length — moves in opposite directions on the two sides of the
seam**, 58 → 149 in MJX against 162 → 39 in MuJoCo, on the same weights and
the same bundle. Two simulators disagreeing about how long a policy stays up
is not a reward-shaping question, and it is what §6 candidate (a) predicts.

Candidate (b), sampled versus mean action, is still the **cheap test and
goes first** — but note the direction: the trainer rolls out the stochastic
policy and `compare.py` plays the mean, so (b) needs noise to make a policy
survive four times longer. `compare.py` has no `--sample` flag today; adding
one is a project-script change. §6 stays **open** with two candidates.
