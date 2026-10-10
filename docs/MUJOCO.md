# MUJOCO.md — Dynamics, and the Road to a Trained Policy

Verified against source: 2026-10-09
Status: **M0 recorded (ADR-075, ADR-076), M1 passed, M2 closed (ADR-077),
M3 closed (ADR-079), M4 closed (ADR-080), M5 closed (ADR-081), M6 closed
(ADR-083), M7 closed (ADR-084), M8 closed (ADR-085).** The arc is complete:
a mechanism designed in Cadex trains to a policy offboard and comes home to
a viewport playing the gait.

**This is part of the product (ADR-102).** Everything this file describes
lived on a branch called `MJC` from 2026-07-30 to 2026-08-01, kept separate
on the reasoning that a user who is not going to simulate a mechanism should
not build a physics engine or ship 53.5 MB of one. Measured, that cost is
2.3% of a staged payload, 1.6% of the shipped application and nothing at all
at runtime — mujoco is imported nowhere at module scope — so the branch was
merged and its rules retired. ADR-078, ADR-082 and ADR-086 are the split and
are superseded; ADR-102 is the merge and carries the numbers. Passages below
written while the branch existed are left as they were: they are the record
of how the decision looked from inside it.

This is the framework for adding **rigid-body dynamics** to Cadex on
MuJoCo, and then following that capability all the way to its end: an agent
that takes a robot from an idea, through a designed mechanism, to a trained
control policy running on it.

`docs/VISION.md` is still authoritative. Where this plan extends the
product's scope it says so, and the extension is a decision the owner makes
in `docs/DECISIONS.md` (ADR-075, slice M0) — not something this document
grants itself.

Provenance: everything described here is `[Cadex-new]`. MuJoCo is a
dependency in the **OCCT category** — a kernel we keep, upstream and
unmodified — not a tree we fork. See "Why not a fork" below.

---

## 1. The thesis

Cadex already simulates. `assembly.simulation(...)` runs native
kinematics in the worker, retains a time-series trace under the schema
`cadex-assembly-simulation-trace-v1`, and publishes it as
`simulation_trace_preview` (ADR-048). The Blender shell baked that trace
to F-Curves in `cadex_animate.py` and played it in the Simulation panel
(ADR-050); since ADR-498 the dashboard plays it from its own trace reader.

That trace is a list of frames, and each frame is nothing but
`{frame_index, nominal_time_s, component_placements{name: placement}}`.

**It does not care what produced it.** A MuJoCo integration that emits the
same schema needs:

- no new op in `CadexdProtocol.OP_ARG_SPECS`
- no new response key, no new golden fixture shape
- no row in the `docs/INTEGRATION.md` op table
- no change to the shell's assistant package at all

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
| Payload cost | **53.5 MB**, measured (ADR-076). The conda package is ~14 MB, but what we ship is the pypi wheel, which bundles the plugin dylibs conda-forge splits out. |
| Unwanted deps | pulls `glfw`, `pyopengl`, `pyglfw`, `absl-py`, `etils`, `fsspec`. The GL ones are for `mujoco.viewer` only; core `import mujoco` must not need them, and the payload should prune them (slice M0). |
| Model construction | **`mjSpec`** — programmatic build (`spec.worldbody.add_body(...)`, `spec.compile()`), one-to-one with MJCF. No XML string-building layer needed. |
| Determinism | deterministic for a **fixed binary, fixed platform, single-threaded**. Explicitly **not** bitwise-reproducible across versions — MuJoCo's own `VERSIONING.md` says so. Multi-threaded island solving has open reproducibility issues upstream. |
| Licence flow | Apache-2.0 → engine LGPL-2.1**+**. The "+" is doing the work: Apache-2.0 is incompatible with LGPL-2.1-*only* and compatible with the v3 family. Clean, and it is a Python import in a payload-carried conda package like every other. NOTICE gets an entry. |

**The 14 MB figure is the one to distrust, and it is the conda package.**
An earlier revision of this document read the ~14 MB conda-forge package and
recorded the payload cost as "cheaper than expected." We do not ship that
package — the manifest has not been re-solvable as conda since conda-forge
moved past `occt ==7.8.1`, so what ships is the **pypi wheel**, which bundles
the plugin dylibs conda-forge splits out. **53.5 MB, measured** (ADR-076),
and that is the number the whole branch argument rested on (ADR-078,
ADR-082) — and, once weighed against a 3.3 GB application, the number that
ended it (ADR-102). About 30 MB of it is `mujoco/experimental/`, which the
engine never imports; pruning it is known and deferred.

*(ADR-082 writes the same measurement as "51 MB". It is 51 **MiB** as `du`
reports it and 53.5 MB decimal — one measurement, two units, not a
disagreement. Re-confirmed 2026-07-31 against a freshly staged payload.)*

### Joint mapping

MuJoCo has exactly four joint types — `free`, `ball`, `slide`, `hinge` —
plus equality constraints (`connect`, `weld`, `joint`, `tendon`, `flex*`).
Our thirteen map in three groups:

| Group | Cadex joints | How |
|---|---|---|
| **Direct** (5) | `fixed`, `revolute`, `slider`, `ball`, `cylindrical` | no joint / `hinge` / `slide` / `ball` / `hinge`+`slide` on one axis |
| **Coupled** (4) | `screw`, `gears`, `belt`, `rack_pinion` | `equality/joint` between coordinates *other* joints own — they attach nothing (M2, ADR-077). `rack_pinion` is refused until its convention is measured |
| **No equivalent** (4) | `distance`, `parallel`, `perpendicular`, `angle` | these are *placement* constraints, not runtime ones. **Refuse with a sentence.** |

**Loops.** Our assembly graph is a constraint graph and may contain loops;
MuJoCo is a kinematic *tree* plus equality constraints. A four-bar becomes
a tree with `equality/connect` closing the loop. Tree extraction — picking
the spanning tree and deciding which joints become closures — is the single
hardest piece of slice M2.

**Closed linkages, driven (ADR-593, 2026-10-07).** A connect pins a
revolute closure's pin and lets its axis go. `build_model` now measures what
that costs: the closure Jacobian over every degree of freedom, by central
differences at the solved pose, ranked once with what the export pins and
once with what the joint pins (pin *and* axis). Equal ranks mean the export
moves exactly as the mechanism does, and `built["loop_mobility"]` publishes
both mobilities. A larger joint rank is a loop whose closing axis would have
to tilt — over-constrained on the bench, floppy in MuJoCo — and is refused
as `overconstrained_loop`, naming the closure and pointing at a ball end. A
drive on a coordinate the loops lock (a pinned triangle is a truss) is
refused as `actuator_locked_by_loop`. Measured in
`test_dynamics_linkages.py`: a position servo on the crank of a Grashof
four-bar (200/80/220/120 mm) turns it 450° and the rocker stays within
0.01 mm of the circle-intersection answer at every frame; a slider-crank
(80/200 mm) sweeps its full 160 mm stroke within 0.01 mm of
`r cos θ + sqrt(l² − r² sin² θ)`. Both at `solver_step_s = 0.0005`, because
the closure is soft with a two-step time constant and its error grows with
step² and speed²:

| crank speed | 2 ms | 1 ms | 0.5 ms |
|---|---|---|---|
| 90 °/s | 0.018 mm | 0.0025 mm | 0.0004 mm |
| 225 °/s | 0.045 mm | 0.0062 mm | 0.0012 mm |
| 450 °/s | 0.090 mm | 0.018 mm | 0.0048 mm |

(worst closure residual, four-bar, crank driven by a position servo.) The
fit sweep drives a closed loop from its limited joint and re-closes it at
every sample (ADR-621; before it refused every joint of the loop): on this
four-bar the crank's 10-90° range at 2° puts the rocker tip within 1e-6 mm
of circle intersection at all 41 samples, and the coupler-rocker pin driven
on its own stops closing at -24°, just past the linkage's 23.56°
transmission minimum, and says so.

**The same linkage, built live (ADR-594, 2026-10-07).** The table above is
the fixture route, a tree handed straight to `build_model`. Through the
engine a four-bar of four parallel `revolute` pins never reaches the
export: FreeCAD's solver reports the planar loop as redundant (a revolute
pins five freedoms, and a planar loop needs only three of each closing
one's) and the script is refused. What does build is the pushrod:
a coupler with a `ball` at each end, which gives the coupler one idle spin
about its ball line. Nothing damps it (a ball joint takes no
`joint_dynamics`), and with the coupler's mass on that line it falls off
balance — 9° in 2 s of holding, into the links beside it — so the mass
hangs below the line and the spin is a pendulum. On the scratch project
`orun5-fourbar` (200/80/220/120 mm bars at 1200 kg/m³), the crank servo
turning 225 °/s through `assembly.dynamics` swept 447° and opened the loop
by 0.70 mm at the 2 ms default, 0.0061 mm at 0.5 ms and 0.0013 mm at
0.25 ms — steeper than step² (a 115-fold drop for a fourfold step), so
the step² rule `cadex smoke` uses to name a step is conservative. Smoke's
fifth check, `closure`, measures every site-to-site equality at every
solver step against `MJCF_POSE_TOLERANCE_MM` (0.01 mm) and, on a failure,
names the 1-2-5 step under `step × sqrt(0.01 / worst)`. Held at its solved
pose the live four-bar's loop stays within 0.00094 mm at 2 ms and smoke
passes.

**Four ordinary pins, built live (ADR-595, 2026-10-07).** The solver's
redundancy is a count, not a fault: it charges six constraints per loop,
and a planar loop needs three. The worker now takes the rank of the loop
joints' unit screws at the pose the solver reached — the same closure
Jacobian ADR-593 ranks on the exported model, read before any model
exists — and accepts a code-0 *redundant* verdict only when the loops
keep a degree of freedom and every loop joint's connectors meet
within 0.01 mm. Since ADR-621 the freedom is counted per linkage (loops
sharing a joint): a four-bar in each of two legs is two linkages of one
freedom each and builds, where ADR-595's single count of two refused it;
a leg whose closing pin is tilted has none and is refused even beside a
leg that moves. The planar four-pin four-bar: four freedoms, rank three,
mobility one, redundancy three, accepted. A pinned triangle (mobility 0)
and a four-bar whose closing pin is tilted 30° (mobility 0) keep the
refusal. Built live with four `revolute` pins and driven 225 °/s at
0.5 ms, the crank swept 447.6° and the rocker stayed within 0.0032° of
circle intersection (0.0066 mm at its 120 mm tip); the worst closure
residual was 0.0061 mm, and the dynamics evidence now carries it beside
`closure_tolerance_mm` (0.01) and `closure_within_tolerance`.

**Free base (ADR-335, 2026-09-13).** An assembly that grounds *nothing* is
not an error: it is a mechanism whose fixed frame is not part of the design
— a biped, a balancer, anything meant to fall. Both halves used to refuse it
(`no_grounded_component`, code −6). Now `assembly.solve` **holds the first
component in script order** for the native solver — a grounded joint the
script did not write, reported in the diagnostics as `free_base` with
`grounded_components: []` — so the pose is exactly the one the placements
state (hazard 11 below is about an island the solver was *not* holding);
`extract_tree` gives that same component a free joint through the island
path it always had; and `build_model` writes **the environment's floor**, one
infinite plane named `environment/floor` on the world body at z = 0 with
MuJoCo's default contact parameters, recorded in the manifest as
`dynamics.environment.floor`. A grounded model gets no floor and `environment:
null` — its ground is whatever it grounded, and a design that wants a slab
still declares a plane on that part. The floor's friction is 1.0 and a
pair's friction is the elementwise maximum, so a sole's declared friction
is what the contact sees. The design owns none of this: the charter that
asked for a free base (ADR-328) also forbids a floor, wall or stage in any
script, and the first mechanism through it, Finch, has soles on z = 0 and
nothing else in the world (`docs/probes/ot6/finch/free_base.json`: held for
2 s it stands, shoved at 0.3 m/s it falls onto the floor and not through it).
Only `require_solved=True` holds a base — the unsolved path never refused,
and holding there would move placements an accepted project may carry.

---

## 3. Three tensions to resolve before code

### 3.1 A trained policy is not rebuildable from the script

VISION principle 3: *the script is the truth; everything else is a cache.
Any state that can't be rebuilt from the script is a bug.* A policy is
weights produced by hours of stochastic GPU compute. It cannot be rebuilt
from a script, ever, and pretending otherwise would be a lie the tests
eventually catch.

**Correction to this paragraph's own arithmetic**, recorded because ADR-084
names it as a plan claim the measurements contradicted. It read "tens of
megabytes of weights", and a policy is nothing of the sort: measured
**4.6 KiB to 902 KiB** for the networks this arc trains. That mattered
rather than being a footnote — a multi-megabyte asset would have argued for
its own op and its own transport, and a kilobyte-scale one fits through
`put_asset` and the 128 MB asset budget without anyone noticing. The size
being small is part of why M7 needed no protocol change.

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

*(Written before M0. **Both questions it raises are now answered**, and the
answers are recorded inline rather than by deleting what was asked — the
shape of the question is why the answers came out as they did.)*

VISION listed five capability areas and dynamics was not one of them.

- Slices **M1–M4** are defensible as living inside "Assemblies — links,
  joints, solved placements, **motion**." They extend ADR-048 rather than
  redirecting the product.
- Slices **M5–M8** — task definitions, reward functions, training,
  policies — are a **product direction change**. Cadex becomes a robot
  design *and* control tool. That is a real and probably good expansion,
  and it is the owner's call, recorded in an ADR before a line is written.

The ADR is cheap. Drifting into a robotics simulator without one is not.

**Answered (ADR-075, then ADR-086).** The scope extension was approved
before M1, including M5–M8. `docs/VISION.md` now carries dynamics and
control as capability areas **6 and 7** in its numbered list rather than as
an appendix, and this branch is the product that has them.

It also had to answer a UI question the principles did not: "no
user-accessible modeling tools" is clear, but a **train** button is not a
modeling tool and the human has to be able to press something.

**Answered outright by M7 (ADR-084): there is no train button, and there is
nothing to press.** Training does not run in the engine and cannot — it
needs JAX on a GPU — so the trainer is a program the agent copies to a
machine that has one and runs with its own shell. The weights come home
through `put_asset`, the path an imported STL already travels. M7 built no
UI, no dispatch machinery and no new op, so this is *recorded* rather than
designed around. VISION principle 5 is untouched: the agent authors the
task, dispatches the run and declares the result; the human reads a viewport
and says yes or no.

### Why not a fork, and why not a new repo

**New repo: no.** ADR-030 merged two repos into one; "two of anything" is a
VISION non-goal; Phase 13a *deleted* the cross-repo payload machinery. A
new repo recreates precisely what was just removed and buys nothing.

**Fork MuJoCo: no.** Apache-2.0, actively developed, and its extension
points (`mjSpec`, the plugin system for custom sensors/actuators/forces)
are exactly what a fork would be for. We fork FreeCAD because we are
*replacing* it (Blender was forked too, until ADR-498 deleted the shell).
MuJoCo we keep.

**Branch in this repo, engine-side: yes.** `mujoco-python` joins
`pixi.toml` exactly pinned, for the same reason `occt == 7.8.1` is exactly
pinned. Code lands under `src/Mod/cadex/`. Nothing in the shell ever imported
mujoco — a physics authoring path in the shell would violate "nothing
happens outside the script" the same way the deleted bpy modes did.

**What the branch turned out to be, which is not what "branch" suggests
(ADR-086; superseded by ADR-102, which merged it).** `MJC` was a **product
vertical** — a version of Cadex with dynamics and control built in — rather
than a staging area waiting for a merge window. Two facts settled it. The arc finished: M0–M8 are closed, so
ADR-082's "a branch is where a direction change belongs *until the arc it
opened is finished*" expired on its own terms. And M5 produced evidence
pointing the *opposite* way from what ADR-078 anticipated: `export_mjcf`
calls MuJoCo's own writer, so the capability is not separable from the
dependency, and the round-trip proof that makes the exported file
trustworthy only means anything while the writer and the compiler are the
same pair.

So the three-way choice above resolves as: not a fork, not a new repo, and
not a build flag either (VISION principle 1 — a `WITH_DYNAMICS` option is
two configurations of one product) — but a permanent second edition of the
product, one-directionally synced, whose documentation is its own.

---

## 4. The slices

The development slices M0–M9 (ROADMAP Phase 14, all closed) are in
[`history/MUJOCO-SLICES.md`](history/MUJOCO-SLICES.md); a citation of
"`docs/MUJOCO.md` M2" (or any M-number) resolves there.

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
   **M8 was the sixth payment and it cost nothing again.** The same action
   vector now reaches a *trace* as well as `data.ctrl`, and there is no new
   arithmetic on either path: the action goes through the `clamp then × scale`
   `evaluate_episode` has performed since M6, and the pose goes through
   `vector_mm` and `quaternion_xyzw_from_wxyz` — the same two calls `simulate`
   makes, in the one module where the factors are allowed to live. It needed
   no new test to stay true: `_NO_CONVERSION_MODULES` already covers both
   halves of the worker and the API, so a conversion appearing in the
   rollout's worker half is already a failure. Six payments, six holds; the
   entry can be considered settled unless a new direction appears.

2. ~~**Convexity.**~~ **Handled in M3** (ADR-079), and it needed *two*
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

   **M8's rollout trace joined the same way, for free** — the fourth payout of
   that clause. Which is what makes M8 phase 0's cross-process determinism
   measurement load-bearing rather than reassuring: a rollout puts a
   pure-Python float64 forward pass inside the inner loop, and if its result
   were not byte-identical across two processes then every project containing
   one would fail to reopen. Measured: it is.

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
7. ~~**Scope creep into a UI.**~~ **It did not happen, across four slices
   that wanted it.** M5–M8 each had an obvious button — export, define,
   train, play — and none was built. M7 answered the load-bearing one
   outright (ADR-084: there is no train button and nothing to press; the
   agent authors the task, dispatches with its own shell, and declares the
   result), and M8 needed no button at all because a rollout is a line in a
   script that produces a trace the shell was already baking. **The whole
   arc M0–M8 landed with an empty shell diff.** Still worth listing as a
   hazard for whatever comes next, but the answer is now four slices of
   precedent rather than a pending ADR.
   The diff was spent afterwards, once and deliberately, on the collision
   overlay (ADR-091) — which is the counter-example worth keeping beside
   this one: it is a shell change no engine surface could have made,
   because the thing that was wrong was invisible rather than unreported.
8. **A collision shape and the solid it stands for are in the same frame
   and are otherwise unrelated** (ADR-087). `collision(...)`'s `offset`
   places a primitive in the **component frame**; `part.box(..., origin=…)`
   moves the solid within that same frame. Nothing connects them and nothing
   checks them, so a shape can be the right kind, the right size, in the
   right units, on the right body — and 20 mm from the surface it stands
   for. It is now at least **drawn** (ADR-091); it was not when this hazard
   was written, and that is what made it the quietest one here.
   **Measured, on the one-leg hopper.** A floor authored
   `part.box(4000, 600, 40, origin=[-2000, -300, -40])` has its visible top
   at z = 0; its collision `box` with the same extents and no offset spans
   z = −20…+20. The foot rested on that invisible shelf from frame 0, the
   policy trained against it, every gate passed twice, and the thing that
   caught it was looking at the viewport.
   **Why this ranks where it does:** it is quieter than everything above it.
   Hazard 1 refuses, hazard 3 changes a digest, hazard 5 drifts visibly.
   This one produces a mechanism that runs, exports, trains and plays back —
   and is not the mechanism it is described as.
   **What is done about it.** `model_evidence` reports the contacts present
   at the exported keyframe: the count, the two geom names, the world
   position and the signed distance. On the broken floor that is one contact
   at z = 20.00 mm; on the corrected one it is none. Evidence rather than a
   refusal, because a mechanism designed to start on its feet is ordinary —
   ADR-087 §3 has the reasoning and §2 has why no bounding-box rule works.
   **The real fix, now done** (ADR-091). There is a view of collision
   geometry: `collision_view` / the **Collision Shapes** toggle draws an
   edge-only wire cage per shape, on the part it belongs to, named exactly
   what MuJoCo calls the geom, and the panel carries the initial-contact
   line above. This bug is obvious in one second and invisible in an hour of
   reading, and that asymmetry is the whole argument. It cost a shell
   diff, which was a decision and was taken as one rather than smuggled in.
   The gate now reproduces this exact floor and asserts the overlay draws
   its top 20.000 mm proud, then that the corrected script draws the gap as
   0.000. *(The overlay and its gate went with the shell, ADR-498; the
   dashboard's port of the toggle was cut from the page by ADR-533. What
   stands today is the contact line: the agent reads it with `inspect
   scope=contacts` after an `assembly.mjcf` export, and the server still
   computes `collision_proxies` the page no longer draws —
   `docs/SHELL-PARITY.md`.)*
   **What is still not done**, and is kept honest here rather than implied
   away: a `mesh` or `hull` shape draws a fixed-size frame cross, not its
   geometry, because the evidence deliberately strips the vertices. So the
   overlay says *where* such a shape is and not *what* it is — and for a
   `hull`, whose accepted volume differs from the part's, that residue is
   exactly where this hazard still lives. Drawing the component's own
   display mesh instead would show the **wrong** volume, which is worse than
   showing none. And **escalating interpenetration to a refusal** is still
   waiting on evidence across fixtures (ADR-087 §3).
9. **A reward built on raw Cadex channels is badly conditioned, and it fails
   by training worse rather than by failing.** Observation channels are in
   **millimetres and degrees** (§3.2 — that is the surface's whole unit
   policy, and it is right), so they arrive in the hundreds to thousands
   while `cadex_train.py`'s observation normaliser starts at mean 0 and
   variance 1 and has to walk to them. Nothing warns, nothing refuses, and
   the run completes.
   **Measured both ways on one mechanism**, same trainer, same iteration
   count, same everything but the channel the reward reads:
   - `body_z`, a torso height sitting at ≈ 451 mm: reward/step **4.46 →
     3.66** over the run. It got *worse than doing nothing*.
   - `rail_p`, a slider displacement whose baseline is 0: **−0.243 →
     −0.028**, with loss **8.7 → 0.026**.
   The difference is not the mechanism and not the reward's meaning — both
   terms describe the same height. It is that one channel is an absolute
   position with a large offset and the other is a displacement about zero.
   **What to do:** write rewards against quantities that are naturally near
   zero, or subtract the baseline in the expression —
   `assembly.reward("rail_p + 26.3", ...)` is a term whose value is ~0 at
   rest and positive only for leaving it. Subtracting in the *expression*
   rather than rescaling the channel keeps the units policy intact: the
   channel still means millimetres, and the arithmetic is visible in the
   script.
   **Not fixed in code, deliberately.** Normalising the reward inside the
   trainer would make a run's numbers depend on a hidden transform, which
   is exactly the property that makes two runs incomparable. The trainer
   does now **stop at the first non-finite `reward/step` or `loss`** and
   name the iteration (ADR-088), which is the other half of this hazard:
   the badly-conditioned case that does not merely train worse but diverges
   used to run 150 more iterations and die in `json.dumps`.

10. **A limb can be under-actuated, and the trained policy will look like a
    gait rather than like a failure.** *Discovered by ADR-090, and the most
    expensive hazard in this list so far: it cost a training run and a
    written-down misreading.*
    **The arithmetic is one line.** Holding a limb out against gravity takes
    about **weight × limb length**:
    ```
    machine 13.708 kg -> 134.5 N;  shin 200 mm
    static torque to hold a 90-degree crouch   26.9 N*m
    torque the script gave hip and knee        12.0 N*m
    ```
    A joint that cannot *hold* a pose certainly cannot accelerate out of
    one. That hopper's leg was short by 2.2x for holding, so nothing it
    could have learned would have left the ground — and the training run
    that "found a gait" was answering a question the mechanism had already
    closed.
    **Why it fails quietly.** The policy still converges, the reward still
    improves, and the rollout still plays. ADR-088 §2 read the resulting
    trace as the machine *tucking its leg up*; it was **falling**. Standing
    straight is free because the moment arm is zero, so a policy under this
    constraint learns to stand still and the trace looks deliberate. Nothing
    refuses, because nothing is invalid — the model is exactly what was
    asked for.
    **The number that would have said so is not where the reader was
    looking.** `model_evidence` reports `peak_effort_si` and `saturated`;
    **a rollout's evidence does not.** In all 27 scripted push-offs against
    that model the knee sat at exactly **12.00 N·m — its limit** — which is
    unambiguous, and was not in front of anyone reading the rollout. Treat
    an actuator pinned at its limit for a sustained stretch as a mechanism
    finding, not a control one.
    **What to do:** compute weight × limb length before training and compare
    it to `torque_limit_nmm`, and prove the mechanism with a scripted
    open-loop attempt *before* buying GPU time.
    `~/cadex-hopper/feasibility.py` is the worked example — a 3x3x3 grid of
    crouch-and-extend attempts against the exported MJCF, which runs in
    seconds and has no learning in it. Sizing that leg at 60 N·m took it
    from **0 of 27** configurations leaving the ground to **27 of 27**, best
    **304 ms** of flight.
    **A gate can also fail for the gate's own reasons**, and ADR-092 §5 is
    the worked example: the biped's first feasibility run reported that a
    machine which stands perfectly could not be held up, because the PD
    sweep ran gains a hundred times too stiff for a 307 g machine. Read a
    gate failure as a claim about the *pair* — mechanism and controller —
    and bracket the sweep from both sides so a pass is bounded rather than
    lucky.

11. **A floating base is not a mechanism with the ground left out: an
    ungrounded island does not keep the pose its component placements
    state.** *Discovered by ADR-092, on the first floating-base model on this
    branch.*
    The natural way to pose an assembly is
    `assembly.component(placement=...)`, and for an island the joints never
    reach from ground it is a **starting point rather than a statement**.
    Such an island has six free degrees of freedom, the constraint system is
    under-determined, and the native solver is free to answer with its own
    member of the solution family.
    **Measured.** A three-part probe — ground, `a`, `b`, one revolute, and
    `b` placed at exactly 30° about that hinge's own axis — solves with the
    hinge reading **zero** and the free root `a` carrying `b`'s placement.
    The biped did the same at scale: all eight joints zeroed and the whole
    machine displaced by (90.2, 18.0, 58.1) mm and about 40°. Four control
    probes (zero joints, one revolute, a `fixed` joint, a branching root)
    leave an all-identity island exactly where it was, so the trigger is
    specifically **two connector frames that do not already coincide**.
    **Why it is quiet:** every joint is satisfied, `solve` reports solved,
    the model exports, and the mass and inertia are all correct. What is
    wrong is only *where the machine is*, and on a grounded mechanism — every
    fixture before this one — the question never arises.
    **Narrowed by ADR-335:** when *nothing* is grounded the solver now holds
    the first component in script order, so a single-island free base keeps
    its placements exactly; this hazard remains for a second island, and for
    an island beside a grounded component, which nothing holds.
    **What to do:** put the pose in the solids, and give the two connectors
    of a joint the **identical posed world frame**. The residual is then zero
    at any slider setting and there is nothing to collapse. The cost is worth
    stating in the script: each joint's zero becomes the posed configuration,
    so declared limits are measured from the slider pose rather than from the
    anatomical neutral. At the neutral pose they coincide, which is where a
    task is staged — and the staging is worth enforcing, because the reset
    pose is the project's **stored** `param_values` and a `num(0, ...)` in
    the source is only a default (ADR-092 §4).

12. **`_field_drift` normalises by the field's own largest magnitude, so a
    model whose every body coincides with its parent refuses on float dust.**
    *Discovered by ADR-092.*
    The MJCF round-trip check is right in general — normalising element by
    element would report the writer's rounding of a near-zero entry as total
    disagreement — and it is pathological when a whole field is identically
    zero. A figure drawn in **one** frame does exactly that: put every
    component at the identity and every relative body placement is the
    identity, so every entry of `body_pos` should be zero. But
    `matrix_multiply(A, matrix_inverse(A))` leaves ~1e-16 m of dust, the
    writer emits six significant figures, and **dust over dust is a relative
    drift of exactly 1.0**. Moving each part onto its own proximal joint
    fixes `body_pos` and moves the same refusal to **`jnt_pos`**, which is a
    joint's position in its *child's* frame.
    **What to do:** give each part a component frame at its own limb's
    **middle**, which is the modelling the hopper already documents ("every
    solid is centred on its own component frame") and which makes both fields
    carry real half-lengths. Note that an exactly-zero field is *fine* —
    `dof_damping` with no `joint_dynamics` is all zeros and passes — so the
    hazard is specifically **a field that should be zero and is dust**.
    **Fixed at the source by ADR-441 (2026-09-29).** The writer emits any
    float below 1e-12 as `0`, and `_field_drift` now compares values below
    `MJCF_WRITER_ZERO` as that zero on both sides, so dust no longer
    refuses and the component-frame workaround above is no longer required.
    hex2 hit this as `hip_pitch=48` being refused inside its own range.

13. **A witness records what the GPU rounded the network to, not what the
    network computes.**
    *Discovered by ADR-094, after it cost 3 h 49 m of an RTX 4070.*
    `training/cadex_train.py` builds its witness with `jax.vmap`, which turns
    each layer's matrix-*vector* product into a **batched matmul** — and XLA
    puts a batched float32 matmul on Ampere+ tensor cores at **TF32**, a
    10-bit mantissa with eps ~4.9e-4. The engine evaluates the same weights
    in float64. The witness therefore compares a tensor-core result against
    an exact one, and the difference is nothing to do with the policy.
    Measured on the same shipped weights: the vmapped path sits **1.4336e-4**
    from float64 while the identical arithmetic run one row at a time sits at
    **5.14e-8** — 2800x closer.
    **Why no short run catches it:** the error is a fixed *relative* one, so
    its absolute size grows with the activations a policy learns. The same
    task, same seed, same box measured **7.3e-6 at iteration 2** and
    **1.43e-4 at iteration 2000**. A smoke test passes and the real run is
    refused.
    **What to do:** record the witness under
    `jax.default_matmul_precision("highest")` — training itself stays at the
    default, because TF32 is why the GPU is fast and no training step needs
    the last four mantissa bits. Then check it *before writing the file*:
    `witness_disagreement()` is a pure-float64 Python copy of the engine's
    own test, copied rather than imported because ADR-084 forbids the import.
    It prints the margin and warns under 100x, because **14x was the visible
    warning nobody was shown.**

14. **A feasibility gate can encode a worst case the task never reaches, and
    a red gate is then worse than no gate.**
    *Discovered by ADR-095.*
    `feasibility.py`'s arithmetic check multiplies the machine's whole weight
    by a **full limb length**. That is the moment arm when the leg is
    *horizontal* and the machine hangs off one hip — a one-legged iron cross,
    not a stance. On a PLA biped with real MG90S torque limits it read 0.84x
    at the hip and printed DO NOT DISPATCH, while `mj_inverse` wanted
    **2.39 N*mm** of a 216 N*mm servo and a hand-written PD stood a whole
    episode on a peak of **4.5**. Four physical checks said sound; one
    closed-form inequality said no.
    **What to do:** make the arm the arm the *task* uses — for standing, a
    lean of ~30 degrees, and for the ankle the sole's own forward reach,
    because the centre of pressure cannot leave the foot. Keep printing the
    old column beside it rather than deleting it: it is a real bound on what
    the machine could do if it ever had to hold a leg out, and it is the
    reason not to ask this one to walk yet. The failure mode to avoid is not
    "the gate was wrong", it is **learning to click past a red gate** — so
    re-specifying one is a decision to record, not a fix to slip in.

15. **A policy that stands can be standing on pinned motors, and the
    trajectory will not say so.**
    *Discovered by ADR-096, on the first trace the Policy Outputs panel
    read.*
    The `mg-legs` standing policy plays as a clean stand and is one: it
    holds the full 6 s, the reward curve is healthy, the engine verified it.
    It is also holding `hip_pitch_l`, `hip_pitch_r` and `knee_r` above 95 %
    of the MG90S limit on **100 % of frames** — a mean of 212-214 N*mm
    against a 216 N*mm bound — while both ankles sit under 72. It braces
    rather than balances: the stance widens from +-30.00 mm to +-37.2/37.4
    and the right foot pulls 13 mm back, and the splay is held by torque.
    216 N*mm is a **stall** rating, which is a momentary number; no real
    servo holds 98 % of it for six seconds.
    Nothing in the poses shows this, which is the point. Effort was already
    a reward term and it was not expensive enough to matter, and the
    feasibility gate had passed because it asked about the *reset* pose and
    the policy settled somewhere else.
    **What to do:** read the commands, not only the trajectory — each
    rollout frame's `actuator_commands`, or `compare.py`'s torque columns
    (the shell's panel that took one glance went with the shell, ADR-498).
    Treat
    "the reward went up" and "the mechanism is doing something a machine
    could do" as two separate claims, and check the second one before
    spending GPU time on a harder version of the first. A policy pinned at
    its actuator limits has no authority left for a disturbance, so this
    also predicts the outcome of the first push.

16. **A task in which nothing ever changes cannot tell balancing from
    bracing, and will reward the wrong one.**
    *Discovered by ADR-097, working out why hazard 15 was rational.*
    Before M9 every episode of a task reset to the identical keyframe with
    every velocity zero, and domain randomisation varied only the
    *mechanism* -- drawn per environment and held fixed for the run. So a
    posture found once was never asked a second question, and pinning four
    motors to hold a wide splay is a **stable** answer as well as a cheap
    one: effort was weighted -0.0002/N*mm, which costs 0.17 against a +0.39
    reward/step, while falling costs the alive bonus, the tilt penalty and
    the rest of the episode.
    **What to do:** declare `assembly.reset_variation` and at least one
    `assembly.disturbance` on any task whose word for success is "balance",
    "hold" or "stand". A reward term cannot fix this -- the problem is not
    that bracing is under-priced, it is that the task never tests the
    difference. And decide the success metric **before dispatching**:
    recovery rate, not reward, because the curve gets noisier the moment
    variation goes in and is no longer comparable with the undisturbed run.

17. **Perturbing joint angles at reset is not a smaller version of
    perturbing the base -- it is a contact impulse.**
    *Measured by ADR-097 phase 0, which is why the surface has the shape it
    has.*
    The reset pose is the **solved** configuration, with the soles placed
    exactly on the floor. A +-3 degree knee jitter moves a foot about 5 mm
    *through* the floor, and MuJoCo resolves that overlap as an impulse
    nothing could stand up to -- so the first thing every episode would
    teach a policy is that the floor hits back.
    **What to do:** perturb the free root **rigidly** -- a tilt, a lift, a
    spin -- and perturb velocities. A rigid tilt cannot change the
    mechanism's shape, so it cannot self-interpenetrate however far it
    leans. The floor is still a question, and it is the one the engine
    measures: the widest declared tilt at the smallest declared lift, at
    sixteen azimuths, against the deepest contact. **Do not do that
    arithmetic by hand.** `mg-legs` was written with a 3 mm lift for a 6
    degree tilt on the reasoning that 6 degrees across a +-30 mm stance is
    about 3 mm at the sole; the measured answer was **5.13 mm**, because a
    tilt pivots about the base's own frame origin and the far thing from a
    pelvis is a toe, diagonally, most of a leg away.

18. **A check that looks like a measurement can be computing nothing, and
    a green light from one is worse than no check.**
    *Discovered by ADR-099, three times in one afternoon.*
    Re-specifying the feasibility gate produced two checks that ran, printed
    a table and gated on it while measuring nothing at all.
    **`mj_inverse` with an external force applied** returns leg torques
    **bit-identical** to the undisturbed case, because inverse dynamics on a
    floating base solves for the force needed at *every* dof including the
    six unactuated ones -- the push is absorbed by the free joint's own
    residual. The tell was that all eight joints reported the same worst
    azimuth, 0 degrees, which is the signature of a value that never varied.
    **A joint-space PD, pushed**, falls from every direction on any impulse,
    because it holds joint angles and has no base-attitude feedback at all.
    That is a fact about the controller; gating a mechanism on it fails
    every mechanism.
    And the third version was over-conservative in the arithmetic column's
    own way -- it summed every declared force and held it for three seconds,
    **2.34 N*s against the 0.042 N*s** a 0.35 N shove lasting 0.12 s
    actually delivers.
    **What to do:** vary the input and check the output moves. If a check's
    numbers do not change when the thing it measures changes, it is not a
    check. And prefer statics you can write down over a simulation you have
    to trust: the gate that survived asks whether the righting moment a shove
    needs is inside what the footprint and the ankles can supply, which is
    three numbers and no controller.

19. **The number the trainer reports and the number that decides whether the
    machine stands can be anti-correlated.**
    *Measured by the M9 run (ADR-099 §5), across all 2000 of its iterations.*
    The curve rose to a best of **+0.5118 at iteration 1944** and was still
    climbing. Played locally over 12 seeds, survival was **12/12 at iteration
    500** — where the trainer reported its *worst* numbers — and **0/12 from
    1700 on**, reaching zero exactly as the trainer reported its best. The
    `best`-by-reward checkpoint falls in **43 steps of 600** from every seed
    and every direction, before the first shove window opens.
    This is not the reward *function* disagreeing: the trainer scores
    `reward_of(vector)` on the raw observation from the bundle's own
    expressions. The cause is unresolved (§6), and the rule does not wait on
    it.
    **Reproduced on a second, unrelated task** (ADR-100, M9b): reward rose
    monotonically to its best at iteration 493 while episode length collapsed
    from 170 steps to 30. Different reward, different observations, different
    forces, same signature. Twice on two tasks makes this the **instrument**,
    not the task — which promotes §6's open question from interesting to
    **blocking**: no reward or shove change can be evaluated while the
    training signal disagrees end-to-end with what the policy does when
    played.
    **Reproduced a third time on the fixed trainer (ADR-101, M9c), which is
    what rules the trainer's episode handling out as the cause.** Same
    bundle, same hyperparameters, one thing changed: trainer reward rose to
    +0.175 and trainer-measured episode length to 149 steps, while the
    engine measured 0/12 survival at every checkpoint and episode length
    peaking at 162 and collapsing to 39. **The same quantity moves in
    opposite directions on the two sides of the seam** — which is the
    sharpest form this hazard has taken and is only measurable because
    ADR-101 added the trainer-side number.
    **One defect behind it has been found and fixed (ADR-101), and the first
    two runs above predate the fix.** The trainer read the bundle's
    `max_steps` and
    never used it, so an environment whose policy did not fall over **never
    reset**: it ran past the last shove window, was never pushed again, and
    stood still collecting the `alive` bonus for the rest of the run. That
    makes **every reward number measured on this branch so far
    non-comparable** — +0.391, +0.5118, +0.2149 alike — and it predicts the
    observed shape, but *predicting* is not *proving* and the rerun that
    would prove it has not been done. The survival numbers are unaffected:
    they were measured through the engine's reference runner, which has
    always honoured `max_steps`.
    **What to watch from now on:** mean episode length, reported beside
    `reward/step` in the trainer's stderr, in `progress.json`, in the policy
    header's curve rows and in the dashboard's training plots (ADR-101). A
    reward that climbs while episode length falls is this hazard happening
    live, and M9b's 170 → 30 would have been visible while it happened.
    **What to do:** never install, rank or stop on the trainer's reward.
    Play every checkpoint and install by **survival** — `compare.py` is
    seconds on a laptop and needs no GPU. Play it against **the run's own
    bundle** (`--task`), because a rebuild replaces `script_artifacts/` and
    the newest bundle may be a different task entirely. And treat
    `<out>.best.cxpolicy` as a filename, not a verdict: early in a run it can
    be the untrained network scoring well by standing still.
    **The inversion above is withdrawn (ADR-103 §9): it was the
    instrument.** `evaluate_episode` applies domain randomisation by
    multiplying **in place** into the model it is handed and never restores
    it, and `compare.py` handed it one model for a whole table — so every
    episode compounded the draws of every episode before it, and after 72
    episodes link masses and inertias stood at **0.23× to 3.9×** their
    exported values. The bottom of every table this project has printed was
    a machine progressively less like the one designed, always drifting the
    same way down the table, which reads exactly like a policy collapsing.
    Given a fresh model per episode, m9c reads **65 → 174 → 201 steps** and
    reward **−0.234 → +0.190**, both rising, both in the *same* direction as
    the trainer's 58 → 149. **Survival is unaffected** — 0/12 is 0/12 on any
    model, and every survival number here stands — and so is the reason for
    it: peak torques of 76–84 N·mm of 86 are ADR-086's no-headroom finding,
    not a training failure. Both engine call sites run one episode per model
    and the shipped product is not exposed; a looping *evaluator* is.
    **Two of the candidates are also measured (ADR-103), and one of them is
    real.** The two engines implement the same physics — with collision
    disabled, or with the floor written as a `plane`, they agree to float64
    machine epsilon on the median step. What they disagree about is **box
    against box**, which is the only contact a Cadex model has, because
    `export_mjcf` writes a grounded body's collision shape as a box: the
    median single-step disagreement is nine orders of magnitude worse than
    with a plane, and the two engines disagree about *how many contact
    points exist* on a fifth of all steps from an identical state. Not the
    integrator (`implicitfast` and `Euler` agree to four digits), not the
    solver iteration counts, not float32. Candidate (b) is measured too:
    σ does not run away — 0.3000 → 0.2973 over 50 iterations, falling —
    but sampled play is five times the torque of mean play and 45 steps
    against 54, so it is a real level difference and not the inversion.
    **This hazard is much smaller than it was, and its rule is unchanged.**
    What is left of it is the plain observation that trainer reward and
    survival are not the same quantity and that only one of them decides
    anything. What is gone is the claim that the two sides of the seam
    measure the same quantity in opposite directions. Trajectory
    agreement between the two is not available on a contacting biped at all
    and never was — a 1e-7 nudge inside *stock MuJoCo alone* separates just
    as fast — so the two are comparable statistically and in no other way.
    The instrument is `~/cdx-mjc/mjx_agreement.py`; the guarantee is
    `test_dynamics_mjx_agreement.py`, and it fails if any of this stops
    being true.
    **A third number to watch, beside reward and episode length:** mean
    exploration σ (`action_std`, ADR-103), on the stderr line, in
    `progress.json` and in `remote_train.sh watch`. The loss subtracts
    `--entropy` times an entropy linear in `log_std`, so nothing bounds it
    upwards; a σ that has walked off `--initial-std` is a run whose rollouts
    and whose installable mean policy are no longer the same policy.
20. **MJX has no contact function for four geom type pairs, so a model
    every engine check accepts can still be untrainable** (ADR-281).
    Measured on the `ot4-mix52` walk: an agent-authored slider-crank gave
    the frame a `cylinder` collision rail and the coupler a `box`, the two
    are two joints apart so nothing excludes them, and `mjx.put_model`
    raised `NotImplementedError: (mjGEOM_CYLINDER, mjGEOM_BOX) collisions
    not implemented` 2.27 s into the training leg — after the assembly
    solved, the MJCF exported, the pose held to 0.0015 mm and the rollout
    ran. Stock MuJoCo simulates that contact; the limit is the JAX
    backend's. The four are **box/cylinder, cylinder/mesh, box/ellipsoid,
    ellipsoid/mesh**. `assembly.task` now refuses them by name
    (`mjx_unsupported_collision_pair`), because a task is only ever read by
    the trainer and the author is still there when it is declared; nothing
    else is refused, and a cylinder stays legal on a model nobody trains.
    Prefer box, capsule or sphere collision geometry for anything that can
    touch. **Note the escape that is not one:** `collides_with=[]` on one
    shape does not separate a pair — MuJoCo's mask test is an `or` over
    both directions, so the other side must omit the group too.

21. **FreeCAD swaps a joint's two connector frames behind the script's back,
    and a body then exports at the exact inverse of its pose** (ADR-393).
    `JointObject.setJointConnectors` calls `ensureUnconnectedIsSecondRef`
    (upstream issue 29355), which swaps `Reference1`/`Reference2` *together
    with* `Placement1`/`Placement2` whenever the first reference's part is
    the unconnected one. Reading `Placement{i}` at the script's own connector
    index then pairs each component with the **other** component's frame, and
    `L_p ∘ inv(L_c)` — correct arithmetic on mislabelled inputs — puts the
    body at the inverse of its parent-relative transform. The trigger is the
    ordinary weld: `joint("fixed", connector(part, "origin"),
    connector(host, ...))`, the bought part first, is exactly the
    unconnected-first order. `ot7-plover-e` wrote 24 of them and every one was
    inverted — `c_tabscrew_knee_l_0` 121.9 mm out, both hip bearings on one
    point — while its four hinges, written host-first, were right. **Nothing
    refused**: the model compiled, carried mass and geoms, and stood for a
    second. Static fit checks read component placements and saw nothing, so
    the design reported zero failing checks. The worker now resolves the
    native slot by the component its reference names; what caught it was
    composing the exported body tree down to world and comparing it with the
    solved placements, which is what `test_dynamics_connector_sides_live.py`
    does and what no fixture built forwards ever could.

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
  `api.dynamics`?~~ — answered by M2 (ADR-077): **a sibling authoring
  surface, sharing the output type.** Not a compromise but a forced move —
  `cadex_animate._simulation_entries` selects on `artifact_kind ==
  "assembly_simulation_json"` and on finding two bakes **neither**, clearing
  the scene and dropping the Simulation panel into a message the UI never
  shows. A sibling *type* would let a script declare a kinematics and a
  dynamics run and silently lose the animation it already had. Sharing the
  type puts both under the existing "exactly one simulation" rule, and mixing
  `api.motion` with `api.dynamics` is refused.
- ~~Where the frame budget goes when a rollout needs more than 10 000
  frames?~~ — answered by M3 phase 4 (ADR-079): **two budgets, because there
  are two costs.** The frame and pose caps count what *leaves* the engine —
  artifact bytes, keyframes the shell bakes — and stay where they were.
  `CadexDynamics.MAXIMUM_SOLVER_STEPS` counts what the engine *does*, which
  stopped being proportional to the first when `solver_step_s` became
  authorable. A rollout is long in steps and short in frames, and one
  combined cap cannot express that trade.
- ~~**Does a trace's `artifact_sha256` join the project digest?**~~ — decided
  *yes* by ADR-079 on M3's evidence (both solvers reproduce byte for byte
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
  GPU box under their credentials?~~ — answered by M7 (ADR-084): **the
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
  to STL/OBJ/PLY) or get its own op?~~ — answered by M7 (ADR-084): **it
  extends `put_asset`, and the deciding cost is a shell diff.** A new op
  needs `OP_ARG_SPECS`, `OP_RESPONSE_SPECS`, both `docs/INTEGRATION.md`
  tables, a golden fixture, a handler — *and* `cadexd_client.py` in the
  add-on, which is exactly the diff ADR-078 says the branch rests on not
  having. Widening the store's accepted suffixes costs none, and it works
  because `put_asset` and `import_geometry` perform **no** suffix check of
  their own: they pass the path through and let the engine refuse.
  `_ASSET_SUFFIXES` therefore keeps its exact three members — the shell
  mirrors that constant by name in a comment — and `_STORED_ASSET_SUFFIXES`
  is the union that the store actually uses. What is left is one rough edge,
  taken deliberately: the tool is called `import_geometry` and advises
  `mesh.import_file(...)` on success, which is wrong for a policy. Fixing
  the wording is a shell diff, so the engine-side refusals carry the
  correct advice instead. (That edge went with the shell, ADR-498: the
  agent's tool is now `put_asset` itself, and its description names
  `.cxpolicy`.)
- ~~At what frame rate is a policy rollout played?~~ — answered by M8
  (ADR-085): **any rate that divides the task's `control_hz` exactly, and by
  default that rate itself.** It is `simulate`'s solver-step rule one level
  up — an action is held for a whole control step, so a frame between two of
  them makes the trace depend on floating-point accumulation. The refusal
  names the rates a given task can be played at, because the *policy* chose
  the control rate and the author of the rollout did not necessarily pick it
  with a frame rate in mind.
- Is there a Phase 11 story here? A pybind11 binding over OCCT and a
  MuJoCo integration are independent, but the `assembly` domain is
  Phase 11f — the largest — and this plan puts new weight on it.
- **Why does the trainer's reward disagree with locally-measured survival —
  in sign, across a whole run?** Opened by the M9 run (ADR-099 §5, hazard
  19): the curve climbed to +0.5118 while survival went 12/12 → 0/12, and the
  two are anti-correlated end to end. Not the reward *function* — the trainer
  scores `reward_of(vector)` on the raw observation from the bundle's own
  expressions, and observation normalisation does not reach it. Three
  candidates, **none tested**: (a) **MJX versus MuJoCo** — training
  integrates in MJX and every local check in stock MuJoCo, so a contact or
  solver difference the policy learns to exploit would show exactly this
  signature, and it is the one worth testing first because it would also
  mean a policy that stands in the viewport need not stand on the bench;
  (b) **sampled versus mean action** — the trainer rolls out the stochastic
  policy, `compare.py` plays the mean; (c) **the auto-reset batch mean** —
  `rewards.mean()` averages `unroll × envs` steps with environments resetting
  inside the jitted scan, so it is a per-step mean over a rolling stream and
  not an episode return. The cheap discriminator is (b): play one checkpoint
  with sampled actions locally and see which number it reproduces. Until this
  is answered the operational rule in §7 stands regardless of the cause.
  **A fourth candidate was found by reading, and it was real (ADR-101): the
  trainer never ended an episode.** `horizon = int(episode["max_steps"])` was
  read and never used again, so `done` was the task's termination terms and
  nothing else and an environment the policy kept upright ran for ever —
  past the last shove window, never pushed again, standing still collecting
  `alive`. It is fixed, with a timeout bootstrapped and a failure cut, and
  mean episode length is now reported. **This does not close the question.**
  It removes a defect that was on its own enough to make the trainer's
  reward non-comparable with any evaluation, and it predicts the observed
  anti-correlation. **The rerun was done (M9c) and refuted it**: the
  anti-correlation reproduced exactly on the fixed trainer. So this question
  is **still open, with two candidates rather than three**, and it is now
  much better posed — the same quantity, mean episode length, moves in
  opposite directions on the two sides of the seam (58 → 149 in MJX,
  162 → 39 in MuJoCo, same weights, same bundle). **(b) is the cheap test
  and goes first**, though the direction argues against it: the trainer
  rolls out the *stochastic* policy and `compare.py` plays the *mean*, so
  (b) requires noise to make a policy survive four times longer. Then (a),
  which is the expensive one.
  **Both were measured (ADR-103), and the question is now much narrower.**
  (a) is **answered and localised**: the two engines are the same physics —
  float64 machine epsilon with collision disabled, and the same with the
  floor written as a `plane` — and they differ only about **box against
  box**, which is what `export_mjcf` writes for every grounded body. Nine
  orders of magnitude on the median single step, and contact counts
  disagreeing on a fifth of all steps from an identical state. It is not
  the integrator (`implicitfast` and `Euler` agree to four digits), not the
  solver iteration counts, and not float32. (b) is **measured and
  partial**: σ falls rather than runs away — 0.3000 → 0.2973 over 50
  iterations, because the surrogate dominates the entropy bonus at
  `--entropy 1e-3` — but sampled play commands five times the torque of
  mean play and 45 steps against 54, so the two sides of the seam were
  never quite playing the same policy. (c) is untouched. **And the effect
  all three were candidates for is itself withdrawn** (ADR-103 §9): the
  engine side of every comparison was measured on a model that compounded
  its own domain randomisation — 0.23× to 3.9× on link masses and inertias
  after six rows of a table, because `apply_randomisation` multiplies in
  place and `compare.py` reused one model. On a fresh model per episode the
  two sides agree in direction and magnitude: 65 → 201 steps against the
  trainer's 58 → 149. **So this question is effectively closed.** What
  remains is not "why do they disagree" but two ordinary facts — that they
  are different implementations (box against box, above), and that trainer
  reward is not survival. Note also what can never be had: trajectory-level
  agreement on a contacting biped, because a 1e-7 nudge inside *stock MuJoCo
  alone* separates the trajectory as fast as MJX does. The two are
  comparable statistically and in no other way.

## 7. From a drawing to a standing policy

The slices above say what was built. This says **how to use it**, because
three machines have now gone through it end to end (a hopper, and two bipeds)
and the order is the same every time. It is written down because the order is
load-bearing: every step but the last is cheap, and the last one costs hours
of a rented GPU.

**The projects themselves are not in this repository** (ADR-088 section 6).
They are ordinary Cadex projects in a directory of their own, and each
carries three small driver scripts of about a hundred lines — `rebuild.py`,
`measure.py`, `feasibility.py` — that drive `cadexd` over NDJSON on stdio and
need no application running. What is reproducible is the *method*, not a
model file.

**Several of those project scripts now have a command in the product**,
and the steps below name the script because that is what the three
machines were driven with. Today (`docs/CLI.md` is the contract):
`cadex smoke` is the short stock-MuJoCo hold or zero-action rollout that
answers step 7's "does it stand, does it fall, does a loop stay closed"
without a trainer (ADR-352, ADR-594); `cadex train` and `cadex walk`
(`--remote`, `--detach`/`--complete`) are steps 8 and 11 as one command,
or the `train_start` / `train_status` / `train_stop` tools `cadex mcp`
serves (ADR-464); `--checkpoint-every N` on a local run rolls each
checkpoint out through the engine while it trains (ADR-544), which is
step 10's comparison, live; and `cadex evaluate` holds the declared policy
against the script's `assembly.success` spec — behaviour predicates on
frozen seeds, never the reward (ADR-455..457, motion predicates ADR-587;
`docs/XSCRIPT.md`) — which is step 12's report and §7's rule below, "judge
a checkpoint by what it did", as a command.

### The order

1. **Check what is actually there.** `grep -c "assembly\." script.py`. A
   parametric model with pose sliders is not a mechanism: the "joints" may be
   `part.transform` calls that rotate solids at build time. If the count is
   zero, authoring the dynamics layer is the large half of the job and the
   RL loop is the small half.

2. **Pose the JOINT FRAMES, not the components.** The tempting design —
   neutral solids, pose in `assembly.component(placement=...)` — does not
   survive the native solver, because an island the joints never reach from
   ground has six free degrees of freedom and the solver answers with its own
   member of the solution family. Measured: it zeroed all eight joints and
   displaced a biped by (90, 18, 58) mm and 40 degrees. Instead give **both
   connectors of a joint the identical posed world frame**; the residual is
   then zero at whatever the sliders say and there is nothing to collapse.

3. **Give every part its own component frame, at its limb's MIDDLE.** Not the
   origin, and not the proximal joint. See hazard 12: both are fields of
   dust, and the MJCF drift check refuses them at exactly 1.0.

4. **Measure before sizing anything.** `measure.py` reads
   `model_evidence.inertials`, so mass and inertia come from OCCT, not from a
   tessellation and not from a guess. It reports total mass, the standing
   centre of mass, each joint's height, and the mass hung below it. Every
   number the next two steps use comes from here — hazard 9's baselines
   included, which are **measured at the exported keyframe** and not read off
   the drawing.

5. **Choose the actuator honestly, and say which question you are answering.**
   Torque motors rather than position servos, so that zero action is
   collapse and there is no degenerate "hold the setpoint" solution
   (ADR-092). Then decide whether the limit models *the hardware* or *the
   mechanism*: an MG90S stalls at 216 N*mm and a mechanism-derived limit for
   the same biped was 750, and a policy trained on the second will command
   torque the bench cannot produce. Both are defensible; only one is what you
   will build.

6. **Declare what changes between episodes, and decide the success metric
   before you dispatch** (ADR-097). `assembly.reset_variation` starts the
   episode tilted, lifted and moving; `assembly.disturbance` pushes it while
   it runs. Without both, "balance" is not the task and bracing wins —
   hazard 16, which is why hazard 15 happened. Never perturb joint angles
   (hazard 17). And the metric is **recovery rate**, episodes surviving a
   shove over episodes shoved: the reward curve gets noisier the moment
   variation goes in, and stops being comparable with the undisturbed run.

7. **Run the gate, and read what it says rather than whether it is green.**
   `feasibility.py` is six checks and none of them learn anything: static
   arithmetic (**advisory since ADR-099**), exact gravity compensation by
   `mj_inverse`, whether the mechanism can reject the **worst declared
   shove** in place, contact sanity, a drop test that must **fall**, and a
   hand-written PD that must **hold**. If a PD can stand it, PPO can. If the
   gate is red, find out which check and why — hazard 14 is the case where
   the gate is wrong, hazard 18 is the case where it is not measuring
   anything, and hazard 10 is the case where it is right and the machine
   cannot do the task.

8. **Dispatch detached, and watch it.** `training/remote_train.sh check`,
   then `train ... --detach` (ADR-089, ADR-098), then `watch <run-id>
   <project.cadex>`. Detached because a run is over an hour and one ssh
   held open that long is a closed laptop away from a lost run; `watch`
   because the reward peaked at iteration 1200 of 2000 the last time and
   nobody could see it. Pass `--checkpoint-every 100`: each one is a
   complete `.cxpolicy` you can pull mid-run and play, and `<out>.best`
   tracks the best so far. Do not pipe any of it through `tail` (ADR-093
   §4). The trainer proves its own witness before writing each file and
   prints the margin — **if that margin is under 100x, stop and read hazard
   13 rather than continuing.**

   While it runs, `watch` prints state, iteration, elapsed, ETA, reward,
   best-so-far and where it happened, and the checkpoints pulled, one line
   per change. (The Blender shell's Training panel, which polled the
   `training-progress.json` `watch` writes, went with the shell, ADR-498;
   the dashboard plots the curves of a run under the project's `runs/<run>/`
   — a `cadex walk --out <project>/runs/<name>` or the `train_start` tool.)
   The gap between the best iteration and the current one is the stopping
   decision.

8b. **Before dispatching, check that the box's trainer is the one the tests
   pinned.** `remote_train.sh` copies a bundle and a model and runs the
   *box's own checkout* of `training/cadex_train.py` — so a trainer that
   predates a surface addition silently ignores the new fields while
   recording the new algorithm string in the policy header, and nothing
   fails loudly. `ssh <box> "cd <repo> && git log --oneline -1"` is the
   whole check and it is not optional after any change to
   `EPISODE_VARIATION_ALGORITHM` (ADR-104).

9. **Ask what the task is actually asking, not just how the run went.**
   `capability.py` sweeps a scale factor over the task's declared shove
   magnitudes and prints survival at each, split by azimuth, with the
   termination mix and how far into its own disturbance schedule each death
   got. A run that reads 0/12 at the declared band and 11/12 at a fifth of
   it has not failed to learn — it was asked something out of range, which
   is ADR-106 and is what three runs of mg-legs turned out to be. A curve
   that is flat across the whole sweep is a curve that measured nothing, and
   the file says so out loud.

10. **Compare the checkpoints before choosing one.** `compare.py` plays every
   `.cxpolicy` in a directory locally against several seeds — stock MuJoCo,
   no GPU, seconds — and prints survival, episode length, final tilt, drift
   and **peak/mean torque per motor** as one table. That is what answers "at
   this many steps it looks like this", and the torque columns are what
   catch hazard 15 without a rebuild. Watching two policies *animate* at
   once is not available and should not be faked: ADR-077 is exactly one
   simulation per script, so the numbers compare side by side and the
   animations do not.

11. **Bring it home through `put_asset`.** The digest is required and never
   inferred: `assembly.policy` names a policy by file *and* SHA-256 because
   VISION principle 3 says any state that cannot be rebuilt from the script
   is a bug, and hours of stochastic GPU compute genuinely cannot be. On
   rebuild the worker re-checks the bundle digest, the model it references,
   the observation channels in order, the action table, and re-evaluates the
   trainer's witness with its own float64 forward pass.

12. **Report what the rollout does, rather than iterating on it.** ADR-088's
   stopping rule. The trace is the evidence: frame count against the episode
   length says whether it terminated early, and pelvis height, tilt and drift
   over the episode say what "it stands" actually meant.

13. **Read the commands before you believe any of it** (ADR-096). The
    Blender shell's Policy Outputs panel drew each actuator's command
    against its own limit; it went with the shell (ADR-498) and the
    dashboard has no counterpart, so read each rollout frame's
    `actuator_commands` against the actuator's limit, or `compare.py`'s
    peak/mean torque columns. The
    trajectory says what the mechanism did; this says what the policy
    decided, and the two can disagree in a way only this one shows —
    hazard 15 is a policy that plays as a clean stand while holding three
    motors at 98 % of stall for the whole episode. A command pinned at an
    end is the finding.

### What a good result looks like

The mg-legs run (ADR-095), for calibration — 263 g of PLA and eight 13.4 g
MG90S, 2000 iterations at 4096 environments, 1 h 16 m on an RTX 5090:

| | |
|---|---|
| reward/step | -1.76 -> +0.391 (peak +0.445 at iteration 1200) |
| episode | 151 frames of 151 — never terminated |
| pelvis height | 284.00 -> 283.60 mm, worst drop 0.84 mm |
| tilt | settles ~5.5 degrees against a 45 degree termination |
| drift | 6.97 mm horizontally over 6 s |
| witness | 1.009e-07, 991x inside the engine's tolerance |
| **actuator duty** | **3 of 8 motors above 95 % of stall on 100 % of frames** — see below |

The comparison that makes it mean something is the gate's own drop test:
**zero torque falls at 0.96 s.** A machine that stands for six seconds is
balancing, not merely stable.

**And the last row is why this table has one.** Every number above it says
the run went well, and they are all true. The commands say the machine is
bracing at the edge of its actuators (hazard 15), which no trajectory
measurement would have surfaced and which the commands showed in one glance.
Calibrate against the whole table, not the top of it: a good result is one
where the reward is high *and* the mechanism is doing something a machine
could actually do.

### The reward curve is not the result — measured (ADR-099)

The M9 run makes the point far more sharply than the table above, and it is
the single most important thing in this section. 2000 iterations × 4096
environments, 89 minutes, no error. The trainer's curve rose to a **best of
+0.5118 at iteration 1944** and was still climbing at the end.

Played locally through the engine's reference runner over 12 seeds, against
**the bundle it was actually trained on**:

| iteration | trainer's reward/step | survived | steps of 600 |
|---|---|---|---|
| 500 | +0.034 | **12/12** | 600 |
| 900 | −0.050 | **12/12** | 600 |
| 1500 | +0.45 | 3/12 | 250 |
| 2000 (`best`) | **+0.5118** | **0/12** | **43** |

**The two are anti-correlated across the whole run.** Survival peaks where
the trainer reports its worst numbers and reaches zero exactly where it
reports its best. The checkpoint the trainer labels `best` — the one an
unexamined pipeline installs — falls in 43 steps of 600, from every seed and
every direction, before the first shove window even opens.

The reward *function* is not the discrepancy: the trainer scores
`reward_of(vector)` on the raw observation from the bundle's own expressions.
Why the two disagree is an open question (§6) with three unverified
candidates — MJX versus MuJoCo dynamics, sampled versus mean action, and the
auto-reset batch mean not being an episode return. **The operational rule
does not wait on that answer:**

> Judge a checkpoint by what it *did* when you played it, never by the number
> the trainer printed. Install by **survival**. `compare.py` exists for this
> and it takes seconds on a laptop.

Two corollaries, both learned by nearly being caught:

* **Play a run against its own bundle, not the newest one.** A rebuild is
  keyed by script digest and replaces `script_artifacts/`, so a finished
  run's task can vanish locally while its checkpoints sit beside you.
  `remote_train.sh train` rsyncs the bundle to the box, so
  `sb1x:<work>/<run-id>/stand-task.json` is the copy that survives, and
  `compare.py --task PATH` is how to use it.
* **`<out>.best.cxpolicy` is best-by-reward, and early in a run it can be the
  untrained network** — which scores well by standing still before the
  disturbance distribution has bitten. Check its peak torque: a policy
  commanding 1–2 N·mm of 86 is not balancing, it is doing nothing.
* **Give every episode its own model** (ADR-103 §9). `evaluate_episode`
  applies the task's domain randomisation by multiplying **in place** into
  the model it is handed, and keeps no baseline — so an evaluator that loops
  episodes over one loaded model compounds every draw it has ever made, and
  its last row is a different machine from its first. `compare.py` reloads
  per episode, at four milliseconds against a two-second episode. **Play the
  same file twice and check the row is the same**; it is a two-second test
  and it is the one that found this.

**One of the three candidates has since been eliminated, and a fourth found
(ADR-101).** The trainer read the bundle's episode length and never used it,
so an environment that did not fall over never reset — every number in the
table above was measured against an unbounded episode and **is not a
baseline for anything measured after the fix**. The rule in the quote box is
unchanged; what is new is a second number to read beside the reward:

> **Mean episode length**, on the stderr line, in `progress.json`, in the
> policy header's curve rows and in the dashboard's training plots. A reward
> climbing while episode length falls is hazard 19 happening in front of
> you. M9b's fell 170 → 30 over 400 iterations with nothing recording it.

### Sizing a shove: the capture point

The reusable part of ADR-100, and the thing to compute **before** dispatching
a disturbed run, because it decides what the run is even asking. A shove is
an impulse, and what matters is not its newtons but where it puts the
**capture point** — how far ahead of the feet the centre of mass would have
to be caught:

```
ω₀ = √(g / h)                 h = CoM height
Δv = F · t / m                the impulse, over the machine's mass
ξ  = Δv / ω₀                  the capture point
```

Then read ξ against two distances, both measured off the export rather than
estimated:

| ξ vs | means | what the policy must learn |
|---|---|---|
| inside the support polygon | in-place recovery | ankle and hip torque; the feet never move |
| polygon … polygon + `leg·sin(swing)` | one step | pick a foot up, place it, catch and return |
| beyond that | nothing | falls are a **mechanism** limit, not a learning failure (ADR-088) |

For `mg-legs` — `h` = 146.0 mm so `ω₀` = 8.20 rad/s, m = 263.1 g, polygon
45.5 mm forward / 24.5 mm back, leg 195 mm, 45° swing → 138 mm of step:

| shove over 0.12 s | impulse | ξ | what it demands |
|---|---|---|---|
| 0.4 N | 0.048 N·s | 22 mm | ankle, in place |
| 0.8 N | 0.096 N·s | 45 mm | at the polygon's edge — hip strategy |
| 1.4 N | 0.168 N·s | 78 mm | a step |
| 2.0 N | 0.240 N·s | 111 mm | a definite step, still catchable |
| 3.5 N | 0.420 N·s | 195 mm | past single-step reach — do not declare this |

**Declaring a range spanning the whole band is a curriculum inside the
distribution** — `newtons=[0.4, 2.0]` puts the in-place problem and the
stepping problem in the same batch from the first iteration, and needs no
scheduling feature. **Sizing the ceiling wrong in either direction wastes the
run**: too small and nothing is asked of the legs (M9 asked for ξ = 19.5 mm
and got a policy that never moved its feet), too large and the falls are
arithmetic. And a *sustained* force is not an impulse — it is a steady lean
that offsets the CoP by `F·h/W` and so **shrinks the polygon ξ has to land
in**; subtract it, do not add it to the shove.

Two mechanism facts fall out of this arithmetic rather than out of training,
and both are worth checking before dispatch: whether the support polygon is
asymmetric front-to-back (mg-legs is, 45.5 vs 24.5, because the toe reaches
and the heel does not), and whether the machine has any lateral authority at
all. Without ankle roll or hip yaw, sideways is hip_roll plus a weight shift
and the effective polygon is well under the geometric half-width — so
**split survival by shove azimuth**, or an aggregate number will average a
mechanism limit together with a learning result and report neither.


…and the split is taken **in the machine's frame**, which is the thing that
was wrong for four runs (ADR-107). `azimuth_degrees` is about **world +X**;
the engine has no concept of which way a mechanism faces and never claims
one. Work out which world axis your machine's forward is — from where its
feet and toes sit — before declaring an arc, and make the instrument assert
it rather than assume it. mg-legs faces **+Y**, so `[-60, 60]` about +X is a
*lateral* band and the column headed `lat` held the *sagittal* pushes.

## 7b. The same arc, locally, on CPU

§7 is the arc at gait scale: a GPU box, detached dispatch, an hour a run.
This is the identical arc run **entirely on one machine** — an M4 Mac Mini,
16 GB, no GPU — at toy scale, measured on 2026-08-29 with a desk balance
toy (ADR-170): an 80 mm puck, a 15 × 15 × 120 mm post, and a 90 mm arm on
one revolute hinge with an MG90-class torque motor (200 N·mm), all PLA at
1240 kg/m³, authored by the agent through `./cadex -p` in one turn (Cadex's own agent
turn, removed by ADR-538; today the agent a person brings, through `cadex mcp`). The
project lives at `~/cadex-balance` — outside this repository, per ADR-088;
what is recorded here is the method and the numbers.

**The loop, and what each leg cost.** Venv per `training/SETUP.md` §b
(Homebrew 3.13, the four pins). Bundle out of the accepted attempt's
`outputs/`. Train with `--progress <project>/training-progress.json`, which
lit the shell's Training panel *and* the reward-curve plot live with no
`watch` leg and nothing else running (both went with the shell, ADR-498;
the dashboard plots a run under `<project>/runs/<run>/`). Policy home through `put_asset` +
`assembly.policy` + `assembly.rollout`, exactly §7's steps 11–12:

- **Training**: 300 iterations × 64 envs in **61.6 s**, then 500 more
  warm-started (`--init-from`) in **79.1 s** — ~5–6 it/s, peak RSS
  **2.2 GB**. Reward per step 0.77 → 1.85 against a ~2.16 inverted-hold
  ceiling; witness error 3.0e-08, a 3300× margin; 4609 parameters, 68 KB.
- **Engine verification**: the receipt records `device: "cpu"` — a
  *feature* at this scale, not a smell: the header says honestly what kind
  of run produced it, and a validation-scale CPU run is exactly what the
  local loop is for.
- **The rollout**: 215.0 total reward against 87.8 for zero torque, the
  full 100-step horizon, 52 frames at 25 fps, baked into the shell as
  ordinary keyframes (the dashboard plays the same trace since ADR-498).
- **Recovery** (§7 step 6's metric): 32/32 episodes survive the declared
  shove band. But the declared band was toothless — 0.15 N peak against
  200 N·mm of authority — so the capability sweep (§7 step 9) is what
  actually measured it: 16/16 at ×1/×10/×30 scale, **9/16 at ×100**
  (15 N), 6/16 at ×300. The edge is real and sits around 30–100× the
  training band.

**What the toy taught, in the order it bit:**

- **`assembly.reset_variation` refuses a grounded mechanism** — correctly;
  it varies a floating base, and this toy has none. The agent's adaptation
  is the pattern to copy: a `StartKick` disturbance drawn in the first
  control interval, so every episode still starts already moving.
- **MJX implements no cylinder↔box collision pair.** The engine accepted a
  puck with the obvious cylinder collision and the trainer refused it at
  `mjx.put_model` (`NotImplementedError`). Box collision on the grounded
  puck costs nothing. The engine does not currently warn at export time;
  until it does, this paragraph is the warning.
- **An overpowered tiny mechanism needs its spin-out guard sized against
  exploration, not physics.** 200 N·mm on an 8 g arm is α ≈ 9300 rad/s²:
  one σ-wide exploration action moves the rate ~3200 deg/s in a single
  control step, so a 3000 deg/s termination ended every young episode in
  2–4 steps and PPO had no horizon to learn from (measured: mean episode
  length 3.7 of 100; reward plateaued at 1.29). Raising the guard to
  12000 and letting the spin *cost* do the shaping took the same trainer
  to 1.85 and a policy that holds inverted. Rule of thumb: the guard must
  exceed `σ · torque_limit / I · Δt` by a comfortable factor, or the
  guard is the curriculum.
- **MuJoCo's warp fallback still prints to stdout** (ADR-093's finding,
  met again): a plain `>` redirection of the trainer's receipt captures
  two `Failed to import warp` lines before the JSON. Read the last line,
  as every harness in this repo already does.

**The rehearsal: the same toy, agent-driven, one prompt.** The arc was
then repeated on a fresh project as a single prompt to the product agent
(`./cadex -p`, 2026-08-29, since removed by ADR-538), with the two traps above given one sentence
each and nothing else. Three turns and two human legs later the engine's
own trace reads **+1729.95 against a −302.17 zero-torque baseline**, full
horizon, arm 2.1° off vertical at t = 3 s — and the agent checked the
bracing hazard (ADR-092) unprompted: holding torque ±5 N·mm of 25,
sign-changing, not pinned. What the rehearsal measured:

- **Both traps were dodged from one sentence each** — and the agent's
  collision fix was *better* than the one above: contact groups
  (`contype`/`conaffinity` masks) so the cylinder–box pair is never
  formed, no geometry compromise at all. It also found and fixed, from
  in-engine evidence alone, a solver-flattened rest pose and damping at
  14× critical.
- **The two human legs are tool-surface gaps, not intelligence gaps.**
  The CLI agent's tools are `describe_api`, `edit_script`, `inspect`,
  `link_part`, `rebuild`, `set_params`, `write_script` — no shell, so it
  cannot *run* the trainer (and, unable to read `training/SETUP.md`, it
  guessed a wrong flag shape for the command it handed back); and no
  `put_asset`, so it cannot bring a policy home. Both refusals were
  clean, precise and resumable. Closing the North Star arc as one CLI
  prompt therefore needed either those tools or a dispatcher; the in-app
  agent had a shell and did not share the first gap. (Both since closed:
  `put_asset`, `train_start` and `evaluate` are in the tool surface, and
  since ADR-538 the agent is one a person brings, with its own shell.)
- **It would not claim success without the engine.** "I will not claim it
  holds inverted until the engine's own trace says so" — and it didn't.

## 7c. The lifecycle audit: which legs still need a person

Measured 2026-09-06, headless, on this machine, on a scratch copy of the
§7b rehearsal project (`~/cadex-balance-ns`, copied out first — a live
project is never built in place). The question was not "does the arc
work" — §7b answered that — but **which of its legs the product agent can
drive from the CLI today, which still need a person or a guess, and what
the iterate step needs before it can run at all.** No code changed; every
row below was actually run, and the numbers are this run's.

| # | Leg | Entry point today | Result | Who does it |
|---|---|---|---|---|
| 1 | Ideation → design (parts as xscript) | your agent, through `cadex mcp` (ADR-538; `./cadex -p` when this row was run) | Works: §7b's rehearsal, three turns | the agent |
| 2 | Assembly: joints, masses, actuator torque, sensors | the same script | Works | the agent |
| 3 | MJCF export + task | any accepted rebuild | Works: `cadex export` rebuilt in **2.6 s** including verify and rollout. On 2026-09-06 it wrote only BREP outputs and the task JSON, model XML, policy receipt and rollout trace came back `"skipped": "not a BREP output"`, so the bundle had to be dug out of `script_artifacts/<revision>/attempt-<id>/outputs/`. **Closed the same day**: `cadex export` now copies every staged non-BREP output into `--out` under its staged filename and names it in the `--json` envelope; the trainer accepted the exported folder as its bundle unchanged (2 it × 8 envs, exit 0, task digest `602d62c1…`, 16 s wall). `docs/CLI.md` §3 | the agent, or a pipeline |
| 4 | Training | On 2026-09-06 (morning): `.venv/bin/python training/cadex_train.py <bundle> --out … --iterations 200 --envs 64 --progress …` — works, 200 it × 64 envs in **22.5 s**, reward/step 5.24, witness error 3.2e-08, but the CLI agent has no shell and guessed the flags. **Closed the same day** (ADR-191): `cadex train --out DIR --iterations N --envs N --put` rebuilds, exports the bundle, runs the venv's trainer with its real flags and stores the policy, the receipt in the envelope as `training` and the stored sha256 as an `assets` row. `cli/tests/test_train.py` runs the real trainer on the toy task (1 it × 4 envs) and the engine's `put_asset` digests the result to the sha256 the trainer printed. `docs/CLI.md` §2 | the agent's caller, or a pipeline — one command, no flags to know |
| 5 | Policy home | On 2026-09-06 (morning): `put_asset` over raw NDJSON (a 40-line scratch driver on the `cadexd_latency_integration.py` client) — works, 54 577 bytes, but not in the CLI tool surface. **Closed the same day** (ADR-190): `cadex asset --put walk.cxpolicy` for a pipeline, `put_asset` in the agent's tool surface for a turn. On a fresh scratch copy: `cadex export` → 2 it × 8 envs in **16.2 s** → `cadex asset --put` stored 28 053 bytes and returned the sha256 → `cadex script --set` with `weights="walk.cxpolicy"` and that digest accepted at `758ef975…` → the exported trace scored the untrained policy at **−297.4** total reward against the rehearsal policy's 1729.9. No staging path, no NDJSON driver, no human step. `docs/CLI.md` §2 | the agent, or a pipeline |
| 6 | Verify + rollout | `cadex script --set` with the new `weights=` name and `sha256=` | Works: **1719.2** total reward, full 300-step horizon, against §7b's 1729.9 from a 400-iteration run | a person edits two lines; the agent could, through `edit_script` |
| 7 | Review | the agent: `inspect scope=output`; a pipeline: the `policy` block of `assembly-simulation-trace.json`, which `cadex export` now copies into `--out` (row 3) | Works for the agent — asked to report the rollout, it read total reward 1719.23 and the five per-term totals through `inspect` unaided. A pipeline reads the same numbers from the exported trace: `total_reward` 1729.95 and the five `reward_totals` on the scratch copy, no staging path read | the agent, or a pipeline |
| 8 | **Iterate** | `cadex params --set shove_n=0.20` | **Refused, exit 3**: the task digest moved (`602d62c1…` → `369a0dd5…`) and the declared policy no longer fits. Correct by ADR-088 — and it means the refusal also never writes the new bundle, so there is nothing to retrain against. Iterating that morning was six legs: edit the script to drop or re-point the policy → rebuild → dig out the bundle → train (`--init-from … --init-from-task-change`) → `put_asset` → re-declare. Three of the six were the person's. **Closed the same day** (ADR-192) with a script convention and no new `params` flag: the policy is declared behind a numeric switch (`policy_on`), so `cadex params --set policy_on=0 --set shove_n=0.20 --out sweep` is accepted (`set_params` never refuses a dropped output) and exports the bundle at `369a0dd5…`; `cadex train --put --init-from … --init-from-parent-task … --init-from-task-change "…"` retrains warm across the change (the ADR-161 pair, now carried by the dispatcher) — 2 it × 8 envs in **17.8 s** wall, iteration 0 already at +1.52 reward/step where a cold network sits near −0.95; the digest edit and `cadex script --set`; `cadex params --set policy_on=1 --out run2` verifies and rolls out. Trace: **127.8** total reward at 0.20 N after one warm toy step, against 1729.9 at 0.12 N for the 400-iteration policy — the comparison exists; row 9 is where it gets recorded. `cli/tests/test_train.py` runs the whole chain on the toy with the real trainer | the agent for the script, a pipeline for the four commands |
| 9 | Compare and record | On 2026-09-06 (morning): nothing — no comparison, no `PROGRESS.md`, and the project directory was not a git repository. **Closed the same day** (ADR-194, on row 10's `PROGRESS.md`): a run's `total_reward` or `reward/step` is written **with its change against the last row that carried it** — delta, that run's digest, that run's value — so the comparison is one recorded row a reader does not assemble by eye; and accepted runs attempt a commit in project-root repositories (ownership and ignore rules: `docs/CLI.md`, **Project history depends on repository ownership**). Measured on the scratch copy: `cadex train --put` (2 it × 8 envs, 4.6 s of training, 20.9 s wall) initialised the repository and landed its row and commit; `cadex script --set` re-declaring the new policy landed `total_reward -293.4 (Δ -421.2 vs 2996fb73 at 127.8)` — a fresh 2-iteration policy against the ADR-192 warm one, on the same task — and a commit of exactly `PROGRESS.md`, `script.py`, `script.json` and the history entry (`git show --stat`). Two runs, two rows, two commits. `cli/tests/test_project_docs.py` pins the delta, the repository and the nested-work-tree refusal | the CLI |
| 10 | Project as a codebase | On 2026-09-06 (morning): nothing — no `ARCHITECTURE.md`, `DECISIONS.md` or `PROGRESS.md`, nothing scaffolds them, nothing reads them on a visit. **Closed the same day** (ADR-193): the CLI scaffolds the three on the first visit (idempotent, never overwrites), pastes them into every turn's system prompt (bounded: architecture head, decisions and progress tails; ADR-265), lands a `PROGRESS.md` row after every accepted run with the revision, digest, what was done and the numbers the run produced (the trace's `total_reward`, the trainer's `reward_per_step`, wall time, sha256), and turns a turn's closing `DECISION:` lines into numbered `DECISIONS.md` entries. Domain docs are a documented convention (`docs/<subject>.md`). `cli/tests/test_project_docs.py` drives it against the engine and a scripted turn. `docs/CLI.md` §2. **Since ADR-538** nothing pastes the documents into a prompt or scrapes `DECISION:` lines — Cadex runs no turn; the agent a person brings reads them and writes `DECISIONS.md` and `docs/<subject>.md` itself | the CLI for the scaffold and the log; the agent for the decisions and notes, with its own file tools |
| 11 | The same walk with the GUI attached | the same `cadex` commands from a terminal beside the open Blender file — **not** the in-app agent, which has only the Mesh tools (`--tools ""`, no shell, no file tool) | **Documented 2026-09-06** (ADR-201, `docs/CLI.md` §2) from the client code, no GUI launched: the CLI's `flock` is per command and released before the `PROGRESS.md` row and the commit; the shell takes no lock, so ownership is sequential by convention; stale shell mutations return `STALE_PROGRAM_REVISION` without adopting the new guard or replaying arguments (ADR-204); Rebuild Model or reopen (`load_post` → `queue_open`), review the refreshed source/values, then retry, never through the re-accept box. Same legs, same docs, same project-relative artifacts. Concurrent rebuilds and simultaneous acceptance are not serialized; sequential use remains required. The headless shell gate covers stale refusal and refresh recovery; no GUI was launched. **Moot since ADR-498**: there is no Blender file to attach; the dashboard beside a walk is read-only (ADR-537) and writes nothing | a person or a pipeline at the terminal; the in-app agent for design turns (today: the agent a person brings, through `cadex mcp`) |
| 12 | The same walk with training on a remote machine | `training/remote_train.sh` (ADR-089) | **Scripted 2026-09-06** (ADR-200): `cadex train --remote` / `cadex walk --remote` run the train leg through `remote_train.sh train <bundle> <out> -- <the same flags>`, verify the returned policy against the receipt, and change nothing else — same `DIR/train` artifacts, same store, same `review.json`. Offline evidence only: `cli/tests/test_train.py` pins the command against the script's usage line and runs the leg end to end against a stand-in dispatcher (real engine, real store, three refusals). **Not executed**: no dispatch, the box's checkout untouched; B7 stays blocked. **A warm start travels since 2026-09-08** (ADR-268): the dispatcher lifts `--init-from` and `--init-from-parent-task` out of the trailing flags, copies both files into the run directory's `warm/` and re-points the flags, so an iterate has the same shape in both modes; tested against the real script with stand-in `ssh`/`rsync` | none; a person for `check` and the box's config |

**One agent turn on top, to see the refusals today.** The same scratch
project was given one `./cadex -p` turn (removed, ADR-538) asking it to retrain at toy scale,
bring the policy home and report the rollout. It did rows 6–7 itself
(rebuilt, reported 1719.23 and the per-term totals) and refused rows 4
and 5 cleanly and resumably — but the command it handed back for row 4
still guesses: `--num-envs` and `--output` where the trainer takes
`--envs` and `--out`, exactly §7b's finding, and it invented a
"`put_asset` CLI command" that does not exist. The contract has to carry
the trainer's real flags, or a dispatcher has to make guessing
unnecessary.

**And one defect, engine-side, found because the CLI checks every reply.**
That turn's first `inspect scope=document` call threw inside the engine,
and the refusal frame `CadexInspection.py` builds on that path
(`failure_code: INSPECTION_FAILED`, with `scope`, `target` and
`result_json_bytes` riding along) does not match
`FAILURE_RESPONSE_SPEC`: it lacks `observed`, `normalized`, `requested`,
`retry`, `candidates`, `allowed_values`, `native_diagnostics` and
`state_change`, and carries three keys the spec forbids. The CLI's
`validate_response` therefore turns every inspect *exception* into a hard
`CadexdError` instead of the clean refusal the agent could act on; the
shell does not validate replies, so it never saw this. A bare
`inspect scope=document` over raw NDJSON succeeds (668 bytes), so the
trigger is the argument shape the agent used, not the scope. The frame
shape is the bug either way, and it is one function. **Fixed 2026-09-06**
(ADR-195): the frame is built by `CadexTools.tool_failure`, so it is the
one tool-level envelope, with `scope`, `target` and `path` under
`requested` and the captured `kind` under `observed`; a test runs
`validate_response` over it and a recorded `inspect.failure` golden pins
the shape beside the other two tool-level failures.

Two smaller things the run turned up. `training/SETUP.md` names the venv
`~/cadex-train-venv`; the one on this machine is `<repo>/.venv`, untracked,
Python 3.13.12 with the four pins — either is fine, the doc just should not
be read as the only place to look. And one `cadex export` left **two**
attempt directories for the one accepted revision, 1.5 s apart, both
complete; harmless, unexplained, not chased (the export that closed row 3
left a third, so it is every export, not one).

**What this orders.** The frontier, in the order that unblocks the most:

1. ~~**Outputs the CLI can hand over** (rows 3 and 7).~~ **Done, 2026-09-06**
   (`cli/cadex_cli/export.py`, no protocol op): the non-BREP files are
   copied beside the STEP and STL under their staged names and named in
   the `--json` envelope, and the trainer takes the exported folder as its
   bundle. The staged name is the whole trick — the task references the
   model by it, so the copy needed no rename and the trainer no change.
2. ~~**`put_asset` in the CLI tool surface** (row 5), and a no-model
   `cadex asset` subcommand.~~ **Done, 2026-09-06** (ADR-190,
   `cli/cadex_cli/tools.py` and `__main__.py`, no protocol op): the
   agent is offered `put_asset` and was told it cannot train (since
   ADR-464 it can: `train_start`, `train_status`, `train_stop` and
   `evaluate` on the bridge, `docs/CLI.md` §4), and
   `cadex asset --put FILE` brings a file home with its sha256 in the
   envelope. Row 5's evidence is the whole chain 3 → 4 → 5 → 6 → 7 run
   on a scratch copy with only the trainer command typed by hand — which
   is item 3.
3. ~~**A training leg the agent can drive** (row 4).~~ **Done, 2026-09-06**
   (ADR-191, `cli/cadex_cli/train.py` and `__main__.py`, no protocol op):
   `cadex train` is the dispatcher — rebuild, export, the venv's trainer
   with its flags pinned by name (a test reads them back out of the
   trainer's own parser, so a rename there fails here), the receipt, and
   with `--put` the policy in the store. Training stays offboard
   (ADR-084): the trainer is a subprocess under an interpreter the engine's
   environment does not have, and the CLI never creates a venv. The
   overlay now names `cadex train --out DIR --put` as the caller's one
   command. The agent itself still cannot run it — it has no shell — so
   the leg is the caller's or a pipeline's; making it the agent's is a
   tool that spawns a fifteen-minute subprocess, which is not taken here.
   (Since taken: ADR-464's `train_start`; and since ADR-538 the agent has
   its own shell and runs `cadex train --wait` itself.)
4. ~~**An iterate shape** (row 8).~~ **Done, 2026-09-06** (ADR-192): the
   script convention, not the flag. The policy sits behind a numeric
   switch parameter the sweep blanks; a blanked sweep is an ordinary
   accepted revision that exports the task at its new digest; `cadex
   train` carries the curriculum pair (`--init-from-parent-task`,
   `--init-from-task-change`) so the retrain is warm across the change;
   the digest edit, `cadex script --set` and `cadex params --set
   policy_on=1` close it. Measured on the scratch copy above and pinned
   by a real-trainer test. Not taken: a `params --drop-policy` flag —
   the refusal is the engine's and the switch is the script's, and a
   convention the agent can author is cheaper than an op it must be
   told about. What the convention cannot do is hide that a stored
   parameter value outlives a script write: the switch stays at 0 until
   a `params` call turns it back on, which is why the last step exists.
5. **The `INSPECTION_FAILED` frame** (above). **Done, 2026-09-06**
   (ADR-195): a `FAILURE_RESPONSE_SPEC` frame built by `tool_failure`,
   a test that runs the validator over it, and a recorded golden — so an
   inspect exception is a refusal the agent reads rather than a client
   crash. No protocol op and no shell diff.
6. **The project as a codebase** (rows 9 and 10). Row 10 **done,
   2026-09-06** (ADR-193, `cli/cadex_cli/project_docs.py`, no protocol
   op, no engine change): `ARCHITECTURE.md`, `DECISIONS.md` and
   `PROGRESS.md` scaffolded on the first visit and pasted into every
   turn's prompt; one `PROGRESS.md` row per accepted run, written by
   the CLI with the numbers; a turn's `DECISION:` lines as numbered
   entries in `DECISIONS.md`; `docs/<subject>.md` for domain notes, by
   convention. (The pasting and the `DECISION:` lines went with Cadex's
   own turn, ADR-538: the agent a person brings writes `DECISIONS.md`
   and the notes with its own file tools.) What row 10 deliberately did not take: a file tool for
   the agent (a convention first, a tool only if reading proves
   insufficient) and a git repository. Row 9 **done, 2026-09-06**
   (ADR-194, the same file, no protocol op, no engine change): the
   comparison is one recorded row — a `PROGRESS.md` number an earlier
   row carried is written with its delta against that row — and the
   CLI attempts a project-root commit. See `docs/CLI.md`, **Project history
   depends on repository ownership**, for initialization, ignore rules and
   nested projects. Only `committed <sha>.` confirms success; a progress row
   alone does not. The measurements above are historical (ADR-266).

### Reproducibility boundary of the audit (2026-09-06)

The twelve leg owners above establish a working sequence, but do not yet
establish the unattended, single-entry-point walk required by the current
charter. At committed revision `7dd3d045`, `docs/CLI.md` §2 still has a
caller edit the policy filename and digest between commands. The original
§7b design also lives outside the repository. Neither is a reproducible
starting point for a fresh machine by itself.

The repo does carry a headless rehearsal, then in
`cli/tests/test_train.py::test_iterate_blanks_the_policy_retrains_across_the_change_and_redeclares`
(since ADR-563 split between `test_iterate_refuses_a_task_change_under_a_declared_policy_until_it_is_blanked`
and `cli/tests/test_walk.py::test_the_walk_takes_the_toy_to_a_verified_rollout_and_iterates`):
it builds a fresh plate-and-arm mechanism with the real kernel, exports the
task, trains on CPU, installs and verifies the policy, exports a rollout,
changes the reward weight, retrains and reviews both traces. Its test helper
supplies the script and rewrites the policy declaration. This proves the
legs, including the refusal of an incompatible incumbent policy; it does
not exercise an agent design turn or a mechanism-independent walk command.

Re-run against the committed CLI at `7dd3d045`: **117 passed in 85.76 s**,
no skips, including the real trainer (1 iteration × 4 environments per run,
CPU). The two rollouts completed 50 steps each, scoring **−27.1094** and
**−55.3480**, with eight project commits and the rounded delta **−28.2** in
`PROGRESS.md`. The reward weight doubled between tasks, so that delta is
bookkeeping evidence, not a claim that one policy is better. Trainer-reported
times were 1.28 s and 1.24 s; the whole suite took 86.26 s under an external
850 s watchdog, with sampled process-group peak RSS **1.05 GB** under a
3 GB stop limit. An isolated copy of committed `cli/` excluded pre-existing,
uncommitted walk edits; the built engine and training venv were reused.
No agent turn, GUI, remote run, build, or packaged gate was performed.

**The entry point, 2026-09-06 (ADR-199).** `cadex walk --out
<project>/runs/<name>` is the one command: the legs above as child `cadex`
commands, the digest edit as a rewrite of the script's one
`assembly.policy` call, and the review as `review.json` in the project.
Run twice on a fresh scratch copy of the same toy before the change
landed — 1 it × 4 envs, 15.5 s and 16 s wall, exit 0 both times — it
reproduced the audit's numbers exactly (**−27.1094**, then **−55.3480** with
`Δ -28.2` in `PROGRESS.md` across the doubled reward weight), and showed
the two things the ADR fixed: the review lived only on stdout, and the
legs' commits carried the policy twice over plus its `.best` checkpoint.
`cli/tests/test_walk.py` now runs both walks with the real engine and
trainer (31.8 s), the review committed and no checkpoint or trace tracked.
The same entry point now also passes on a vertical linear carriage
(ADR-203, `examples/lifecycle/`): 1 iteration × 4 CPU environments,
13.52 s wall, a verified 50-step rollout and total reward −24159.1953563.
The repeated arm baseline was −27.1093842209 in 15.22 s. Both projects'
`PROGRESS.md` explain the identical height term, different force/torque
units, training versus rollout means, and sub-1-GB sampled memory peaks.
The carriage does not hold height after one iteration; this closes pipeline
generality at toy scale, not control performance. GUI attachment remained
documented and unexercised (ADR-201), and is moot since ADR-498 deleted
the GUI. **Remote training is scripted, not run**
(ADR-200, the same
day): `--remote` on `train` and `walk` puts the one leg on the box through
`remote_train.sh` and leaves every artifact where the local walk puts it;
the dispatch itself stays a person's decision, and the box was not touched.

**Named-angle and section review, 2026-09-08 (ADR-239/240).** The walk now rebuilds and
snapshots accepted display in its review session and commits front/top/right/iso
SVG previews plus a summary under `review/render/<accepted-revision>/`.
`review.json` carries revision/digest, project-relative paths, approximation,
limits and acquisition/render timings alongside inventory, clearance and reward.
A revision mismatch or rendering error fails the walk. The shared mode artifact
table in `docs/CLI.md` applies unchanged to local, GUI-attached and remote-flag
walks. Sections share that accepted snapshot at world XZ, at an offset derived
from the snapshot's own bounds rather than a constant (ADR-267), and commit
SVG/JSON under `review/section/<accepted-revision>/XZ-<derived-offset>/`. Review retains plane, units,
revision/digest, approximation, limits and section timing; empty cuts are
available without contours, unsupported cuts unavailable with reasons, and
errors fail the walk without reporting retained files as current success.
These previews show the initial solved pose, not rollout frames or swept clearance.

**Clearance over the poses the run reached, 2026-09-09 (ADR-283).** The gap
that paragraph names is closed on the geometry side: `assembly.dynamics` and
`assembly.rollout` take `clearance=[(a, b)]` and `clearance_mm` on the same
terms `assembly.simulation` has since ADR-130, and measure the named pairs as
exact BREP at **every frame of the trace**, re-posed from each frame's own
`position_mm`/`rotation_xyzw`. What it is not: a MuJoCo contact report. The
geoms the run collides are boxes and capsules (ADR-281), so the solver cannot
be asked about the parts and the parts have to be measured where the solver
left them. Unlike a kinematics sweep this **reports** — the finding lands on
the simulation output under `clearance`, with `closest_approach` naming the
pair, the millimetres and the frame — because refusing a dynamics result
would delete the trace that shows the problem.

## 8. Live mode (retired)

**Retired (ADR-528).** ADR-109 added a live policy session — three read ops,
`live_open`, `live_step` and `live_close`, a resident worker playing the
accepted rollout's policy, and a shove applied by mouse — and ADR-110 and
ADR-136 made it calm-able and endless. Its only client was the Blender
shell's Live editor, deleted with the shell (ADR-498), and the owner dropped
the session on 2026-10-03. The ops, the host (`CadexLiveSession.py`), the
worker (`cadex_live_worker.py`) and the `forces` and `endless` keywords of
`evaluate_episode` are gone. Reviewing a policy is rollout playback in the
dashboard plus `cadex evaluate`'s disturbance tests; `record_steps=False`
stays, as a caller that reads only an episode's totals still asks for it.
`docs/history/` and the ADRs keep the measurements.

### Measuring the capture point, and paying for it (ADR-112)

The section above sizes a shove by ξ. B6 makes ξ a **reward term**, which is
a different job with two requirements the sizing arithmetic does not have.

**It has to be built from the right velocity.** ξ = p_com + ṗ_com/ω₀, and
ṗ_com is the *whole body's* centre-of-mass velocity — `mjSENS_SUBTREELINVEL`
off the root, declared as a `centre_of_mass_velocity` observation. The
pelvis's `component_linear_velocity` is the channel a reader reaches for and
it is wrong by 19% on this machine: 9 mm of error at 400 mm/s and 18 mm at
850 mm/s, against a 24.5 mm margin. A term that decides *must I step?* built
on a quantity carrying 40–75% of the margin as error is the ADR-107 mistake
in a new place.

**It has to be measured against the feet, not against the world.** Through
M9c the two spatial terms compared the centre of mass to the fixed point
`(X0, Y0)` where the machine stood at t=0. Under that objective moving a
foot changes the reward by exactly nothing, and *standing successfully at a
new place after a step* is charged −0.57 per step for the rest of the
episode against the +1.00 `alive` pays. Five runs produced a machine that
absorbs a shove with its joints and never lands a recovery step; the reward
is why. Referencing both spatial terms to the foot centroid — and zeroing
both at the standing pose, hazard 9 — is what converts a **delayed**
survival payoff into an **immediate** one: ξ 40 mm behind the feet costs
−0.61 per step right now, and putting a foot back under it zeroes that
immediately.

**Then check the arithmetic before spending the GPU on it.** The expression
`com + cv/ω₀` should agree with `subtree_com + subtree_linvel/ω₀` computed
directly out of MuJoCo, at disturbed states, to well under a millimetre.
ADR-107 is the precedent: an azimuth convention that was wrong by 90° and
cost a full run to find out.

**The failure mode this shape has** is squatting — both terms are perfectly
satisfied by a deep crouch. The only guard is the `height` term and the
`collapsed` termination floor, so **check mean `com_z` and the
`tipped`/`collapsed` split at the first checkpoint**, not at the end.
