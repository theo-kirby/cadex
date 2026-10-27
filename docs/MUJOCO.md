# MUJOCO.md — Dynamics, and the Road to a Trained Policy

Verified against source: 2026-10-27

Rigid-body dynamics on MuJoCo is part of the engine (ADR-102), and it runs
to its end: an agent takes a robot from an idea, through a designed
mechanism, to a control policy trained offboard (`training/`, ADR-084) and
played back in the dashboard. The development slices M0–M9 are closed (§4).
`docs/VISION.md` carries dynamics and control as capability areas 6 and 7.

MuJoCo is a dependency in the OCCT category — a kernel kept upstream and
unmodified, not a tree we fork — and everything Cadex adds on it is
`[Cadex-new]`. mujoco is imported nowhere at module scope (ADR-102). The
superseded record — the `MJC` branch, the design tensions settled before
code, answered questions, handled hazards in full, the 2026-09 CPU
rehearsal and lifecycle audit, and the retired live mode — is
[`history/MUJOCO-HISTORY.md`](history/MUJOCO-HISTORY.md), under the section
numbers it had here.

---

## 1. The thesis

Cadex already simulates. `assembly.simulation(...)` runs native kinematics
in the worker, retains a time-series trace under the schema
`cadex-assembly-simulation-trace-v1`, and publishes it as
`simulation_trace_preview` (ADR-048); the dashboard plays it from its own
trace reader.

That trace is a list of frames, and each frame is nothing but
`{frame_index, nominal_time_s, component_placements{name: placement}}`.

**It does not care what produced it.** MuJoCo dynamics emits the same
schema, so getting dynamics onto the screen needed no new op in
`CadexdProtocol.OP_ARG_SPECS`, no new response key or golden fixture shape,
and no row in the `docs/INTEGRATION.md` op table. The cost is engine-side,
behind a contract that already existed, and the same seam carries the whole
arc: a *policy rollout* is also just a trace.

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

## 2. What the engine models

### The dependency

Checked 2026-07-30; the pin is unchanged (`pixi.toml`: `mujoco = "==3.10.0"`,
and `training/requirements.txt` pins the same release for the trainer).

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

About 30 MB of the 53.5 MB is `mujoco/experimental/`, which the engine never imports;
pruning it is known and deferred.

### Joint mapping

MuJoCo has exactly four joint types — `free`, `ball`, `slide`, `hinge` —
plus equality constraints (`connect`, `weld`, `joint`, `tendon`, `flex*`).
Our thirteen map in three groups:

| Group | Cadex joints | How |
|---|---|---|
| **Direct** (5) | `fixed`, `revolute`, `slider`, `ball`, `cylindrical` | no joint / `hinge` / `slide` / `ball` / `hinge`+`slide` on one axis |
| **Coupled** (4) | `screw`, `gears`, `belt`, `rack_pinion` | `equality/joint` between coordinates *other* joints own — they attach nothing (M2, ADR-077). `rack_pinion` follows OndselSolver's `x + R·θ` over the tree path from rack to pinion (ADR-641) |
| **No equivalent** (4) | `distance`, `parallel`, `perpendicular`, `angle` | these are *placement* constraints, not runtime ones. **Refuse with a sentence.** |

**Loops.** Our assembly graph is a constraint graph and may contain loops;
MuJoCo is a kinematic *tree* plus equality constraints. A four-bar becomes
a tree with `equality/connect` closing the loop. Tree extraction — picking
the spanning tree and deciding which joints become closures — is the single
hardest piece of slice M2.

### Loops and machine drives

**Closed linkages (ADR-593..595, ADR-621).** A connect pins a revolute
closure's pin and lets its axis go. `build_model` ranks the closure
Jacobian (central differences at the solved pose) once with what the export
pins and once with what the joint pins; equal ranks mean the export moves
exactly as the mechanism does, and `built["loop_mobility"]` publishes both.
A larger joint rank — a loop whose closing axis would have to tilt — is
refused as `overconstrained_loop`, pointing at a ball end; a drive on a
coordinate the loops lock is refused as `actuator_locked_by_loop`. The
worker reads the same rank before any model exists, so FreeCAD's code-0
*redundant* verdict on a planar loop is accepted when, per linkage (loops
sharing a joint, ADR-621), the loops keep a degree of freedom and every loop
joint's connectors meet within 0.01 mm: a planar four-pin four-bar builds
(mobility one); a pinned triangle, or a four-bar whose closing pin is
tilted, is refused. A pushrod — a coupler with a `ball` at each end — also
builds; hang its mass below the ball line, because the idle spin about that
line is undamped.

The closure is soft, with a two-step time constant, so its error grows with
step² and speed². Worst closure residual, four-bar, crank driven by a
position servo:

| crank speed | 2 ms | 1 ms | 0.5 ms |
|---|---|---|---|
| 90 °/s | 0.018 mm | 0.0025 mm | 0.0004 mm |
| 225 °/s | 0.045 mm | 0.0062 mm | 0.0012 mm |
| 450 °/s | 0.090 mm | 0.018 mm | 0.0048 mm |

At `solver_step_s = 0.0005` a Grashof four-bar (200/80/220/120 mm) and a
slider-crank (80/200 mm) track their closed-form answers within 0.01 mm
(ADR-593). `cadex smoke`'s `closure` check measures every site-to-site
equality at every solver step against `MJCF_POSE_TOLERANCE_MM` (0.01 mm) and
on a failure names the 1-2-5 step under `step × sqrt(0.01 / worst)`;
dynamics evidence carries the worst residual beside `closure_tolerance_mm`
and `closure_within_tolerance`. A fit sweep drives a closed loop from its
limited joint and re-closes it at every sample (ADR-621); fit sweeps are
documented once, in `docs/XSCRIPT.md` ("Sampled hinge and slider fit"). A
closure's connect names two sites, read through the same kept-site
renumbering as the `site_*` fields (ADR-775), so a closed linkage can sit
beside contact observations' touch sites.

**Machine drives (ADR-640..645, 2026-10-10).** Four refusals that stopped
a printer, a router, a loader and a tractor hitch are gone, each measured
on fixtures and on three proof projects.

* **A slider on a loop.** Breadth-first by joint order still builds every
  tree it always built; only a graph that would close a loop on a slider or
  cylindrical joint is grown again with every sliding joint taken into the
  tree when its first component is reached, so the loop closes on a pin. A
  cylinder between two pins builds whatever order its joints are listed
  in; a loop of sliders alone (two parallel rails on one pair) is still
  refused, saying to make them one slider.
* **`rack_pinion`.** OndselSolver's own law, read from
  `RackPinConstraintIJ` and `getRackPinionMarkers` rather than measured:
  the rack's marker has X along the rack connector's +Z and Z along the
  pinion's, and `x + R·θ` is constant. Each tree joint on the path from
  rack to pinion contributes its share of `ẋ + R·θ̇` at the solved pose;
  exactly one slider and one revolute may, and every turning joint must
  turn about the pinion's centre, which keeps the law linear. So a rack
  fixed to the frame with the pinion riding a carriage (the gantry) works,
  as does a rack on a slider beside a fixed pinion. Fixture: R = 10 mm, a
  pinion turned 90 °/s for 1 s rolls its carriage −15.7 mm (−R·Δθ, within
  5%); `lib.rack_and_pinion`'s datum gives slope +R.
* **n-joint couplings.** `assembly.coupling` is `sum(c_i·q_i)` held at its
  solved value: an `equality/joint` row for two terms, a `fixed` tendon and
  an `equality/tendon` row for three or more, coefficients scaled so the
  residual is metres of the largest slider. CoreXY is two tendons; with
  both motors turned 90° the same way the carriage moves 10 mm in X and
  the equalities hold to 1e-12. **A coupled motor needs its rotor
  inertia**: a 18 g pulley under a velocity gain of 50 N·mm·s/deg left the
  soft tendon equality 20 mm open; with a NEMA17's 5.4 kg·mm² armature
  and 0.05 N·mm·s/deg, 0.008 mm (0.015 mm on `proof-corexy`).
* **The cylinder.** `kind='cylinder'` is a position actuator with an
  asymmetric `forcerange`: `−p·π(bore²−rod²)/4` to `+p·π·bore²/4`. **Give
  the stroke an armature** (`joint_dynamics(armature_kg=...)`, the piston,
  rod and oil): on `proof-loader` (an 11.5 kg boom, a 40/18 bore at
  120 bar, a 0.7 kg rod) the servo rang against the closure and opened it
  4.6 mm at 0.5 ms; with 5 kg the boom rose smoothly and the loop held to
  0.0004 mm.
* **Sweeps** (`docs/XSCRIPT.md`) move every coordinate a coupling ties to
  the swept joint (`coupled_sweep`): unlimited followers turn, limited ones hold, so a
  swept nut turns its screw and a swept CoreXY axis turns both motors and
  holds the other axis.

### The floor and terrain

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

**Terrain (ADR-714, ADR-716).** `assembly.mjcf(..., terrain=...)` puts a
declared course under a free base **instead of** the plane, built from
`bump`, `step` and `slope` features that add. It replaces the plane rather
than lying on it, so the extent is the course and leaving it is a fall. Two
forms: a MuJoCo heightfield (the default; asset and geom named
`environment/terrain`, sampled by `CadexDynamics.terrain_grid`, its lowest
vertex at the geom's z on a 50 mm base, a step a one-cell ramp of 20 mm) and
the box course below. The manifest carries `environment.terrain` (extent,
grid, lowest and highest, the validated features) in place of
`environment.floor`, and `task_records` copies it into the bundle as
`terrain`, a semantic field: another course is another task.

**Train on the box course.** Under driven motion MJX is not stable on the
heightfield: on ADR-714's block-and-arm rig under random ±0.8 N·m torques,
3 of 32 MJX environments went non-finite on the heightfield and 0 of 32 on
boxes, and on the cat's rig (27 actuators, random targets, 24 starts on
features at up to 3 m/s) the heightfield peaked at 179 rad/s joint speed
against 39–48 on the plane and the boxes. The box course is also cheaper in
MJX (134 s against 338 s for one cat run; 82 s on the plane). MJX has no
hfield contact for a cylinder or an ellipsoid (hazard 20).

**Box course (ADR-716, 2026-10-16).** `terrain={"form": "boxes", ...}` builds
the same features from placed boxes: the plane, lowered to the course's
lowest point and named `environment/terrain`, and one box per record of the
descriptor's `boxes` list, `environment/terrain/<i>`, all on the plane's
contact parameters. Steps and slopes cut the extent along x into segments;
a flat one is a block from below the plane up to its height, a graded one a
20 mm ramp turned to its grade on a block that fills under it. A bump is a
**dome** (ADR-744): a sphere, `environment/terrain/dome/<j>`, buried so its
cap stands `height_mm` above the steps and slopes at its centre and meets
them `radius_mm` from it, so a mogul is round; one taller than its radius
(more than a hemisphere) is refused (`terrain_bump_too_tall`). A
`platform` is a block of its own footprint, its top `height_mm` over the
steps and slopes at its centre, and a `rock` patch a 3 × 3 grid of cells
each holding a stone (or, but the centre, left empty), a box tilted about x
or y by 10–25° and buried so its peak stands up to `height_mm` proud, in
the box slots as `shape: "stone"` (ADR-745). Every level of a course runs
out 50 m past its extent (`TERRAIN_RUNOUT_MM`), so there is no cliff an
episode reaches. A dip is
refused (`terrain_dip_needs_heightfield`), as is a step down off a slope's
high end, where the ramp's leaning end face would stand proud
(`terrain_step_off_slope`). The ground is the highest box top or dome cap
over a point, or the plane (`terrain_box_ground_mm`), which is what MuJoCo's
ray meets (to 4e-12 mm at 1,000 points over 10 held-out drawn courses with
every kind, run-outs included, ADR-745), and what the height scan reads, each
box through its own rotation, in the
engine and the trainer.

**A course re-drawn per episode (ADR-717, 2026-10-16).** A box course
declares `random` in place of `features`: `seed`, `courses` (default 32, at
most 64), `clear_mm` (flat start, default 500), `run_mm` (flat before each
feature, default 300–800), and magnitude ranges `step_mm`, `grade_deg`
(with `slope_mm`, default 400–1000) and `bump_mm` (with `bump_radius_mm`
and at most `bumps`). Course *k* is drawn by
`random.Random('cadex-terrain:<seed>:<k>')` (`TERRAIN_RANDOM_ALGORITHM`):
steps and slopes along x until the extent ends, each signed down while the
course is above z = 0 and up while below, so a long course climbs and
descends; then one to `bumps` bumps. Every course is validated like a listed
one. Course 0 is what the descriptor's `features` and `boxes` describe and
what the model and `rollout_policy` stand on; evaluation draws its own
(ADR-718, below).
The descriptor's `pool` carries every course as features, its lowest and
highest point and its box count, and `slots` the fullest course's count: the
model has that many `environment/terrain/<i>` boxes, the ones course 0 does
not fill parked as 1 mm cubes a metre under the plane. Features, not boxes,
because the bundle is written indented under a 1 MB cap the 30-joint cat's
already fills to 700 KB, and a box is about 3.5 times a feature's bytes
(about 2.5 KB a course on a 13 m course). The trainer rebuilds each
course's boxes with its own copy of the builder (`course_boxes`,
`course_geoms`, held equal to the engine's on every pooled course), and at
every reset gives each environment a course by `jax.random.randint` folded
with 717; `place_course` writes that course's positions, turns, sizes and
derived bounds into the MJX model's terrain geoms inside the vmapped step,
and the height scan reads the same course. The descriptor states `scale`
(the model's metres per millimetre), which the trainer multiplies by, so it
converts no unit itself. Measured under MJX: a block
dropped on each of six pooled courses rests 10 mm above that course's own
ground, so what MJX collides with is what the scan reads. The policy header
records `training.terrain` (mode, the pool algorithm, the bundle's, the
course count). Stock MuJoCo's `mj_ray` cannot check a re-placed course: it
culls static geoms with the bounding-volume tree built at compile, so
ADR-717 checked each course by compiling it as a listed course and
comparing geoms. A build's rollout stands on course 0; evaluation seeds
stand on held-out courses (ADR-718), and every trace carries the course it
stood on (ADR-734).

### Commands and success predicates

**Turning commands and command tracking (ADR-721, 2026-10-16).** A goal
of kind `yaw_rate` is the commanded turning rate of the floating base, in
deg/s about world +Z, anticlockwise positive; drawn, resampled and observed
like a `speed`. `sequence=[...]` scripts a value, speed or yaw-rate goal's
opening segments (each draw still taken, so no other draw moves), which is
how a success spec puts the same reversal on every seed. The tracking
family reads a floating base against the commands in force at every frame:
`speed_error_rms_mm_s` and `yaw_rate_error_rms_deg_s` (centred 0.5 s
window, frames past 1 s and not within 0.5 s after any command change) and
`reversal_heading_error_deg_max` (a held yaw-rate command that turns the
commanded heading 180°, judged when it has). The trainer's host draw
follows the same `GOAL_SEQUENCE_ALGORITHM`.

**Waypoints on the ground (ADR-751, 2026-10-17).** A goal of kind
`waypoint` sends the one floating base to a place on the ground. Each
segment is a leg from the last point (the base's centre of mass at the
reset pose, before the first): its length uniform in `between=[low, high]`
mm, its direction turned from the leg before by uniform ±`bearing_deg`
(default 180; the base's reset heading before the first). The policy reads
it as `name_x` (ahead) and `name_y` (left) in mm from the base's centre of
mass along its heading, as a height scan turns, re-read every step; the
trace and the episode's goal schedule hold the world point. The waypoint
family reads `waypoint_miss_mm_max` (for each point the episode reached,
the closest approach while it was up; the worst) and `waypoints_reached`
(within 300 mm). Points change on the resample clock, not on arrival, so a
spec of three points in 12 s gives each 4 s. The trainer's host draw and
its channel transform are copies (`draw_goals`, `waypoint_vector`).

**Appendage predicates (ADR-722, 2026-10-16).** `assembly.success(...,
appendage=[root, ..., last])` names a chain that hangs from the base and is
not a leg -- a tail, a trunk -- each component below the one before, at
least one with a primitive collision shape. The spec may then bound
`appendage_ground_contact_share` (frames with any of its shapes within 1 mm
of the ground under it), `appendage_pitch_parent_correlation` (r between
its root's pitch and its parent's: is it carried rigidly by the hips?) and,
against a `yaw_rate` goal, `appendage_yaw_turn_correlation` (|r| between
the command and the chain's yaw relative to the base: is it used in turns?).
A contact share is only as true as the collision shapes: a link with none
passes through the floor unseen.

**Heel and footfall predicates (ADR-774, 2026-10-18).** `assembly.success(...,
feet=[...], heels=[...])` names, for some feet, the body that should reach
the floor in stance -- the hock case of a plantigrade hind foot -- on that
foot's leg (above it, or welded to a link above it), with a primitive
collision shape. The spec may then bound `heel_down_stance_share_min`,
`heel_down_at_toeoff_share_min`, `heel_stance_height_mm_max` and
`heel_foot_flat_share_min`. With a task `reference`, the leg labels also give
`touchdown_rate_ratio_max`/`_min` (every landing, taps included, per left-hind
stride), `hind_overreach_mm_min` and `pair_lag_fore_median`/`_hind_median`;
each stride's lag is in the detail, so a speed ramp's lags can be read
against speed. Probe: `docs/probes/orun11/footfall_probe.py` re-reads a
judged evaluation's traces with them.

**Terrain predicates, a held-out course per seed (ADR-718, 2026-10-16).**
A success spec may bound `distance_made_good_mm` (net plan travel along the
starting heading) and `falls` (the base tilted 60°, or its centre of mass
fell to half its starting height above the ground under it) on any floating
base, and, on a declared course, `steps_crossed`, `slopes_crossed`,
`largest_step_crossed_mm` and `steepest_slope_crossed_deg`, and
`platforms_crossed` and `highest_platform_crossed_mm`: a platform whose
footprint the centre of mass was over and whose far end it ended beyond
(ADR-749; before it, any course with a platform or rock patch failed these
predicates with a `KeyError`). With named `feet`, a course of platforms is
also read for leaps (ADR-772): `gap_touches`, `gaps_cleared` and
`widest_gap_cleared_mm` (feet down between two platforms, and the gaps
crossed without), and `highest_platform_reached_mm`,
`leap_takeoff_speed_mm_s` and `leap_peak_mm` (the tallest top a foot stood
on, the speed at take-off and the centre of mass's rise), with each drive's
peak ratio over the push before take-off in the `leap` detail. A foot's
stance there is read against the course's ground, not the flat floor the
gait and flight families read. On a drawn box
course `evaluate_success` plays each seed on its own course,
`terrain_evaluation_course`: the pool's algorithm under the key
`eval:<seed>:<n>`, the first draw whose boxes fit the model's slots, so no
seed is judged on a course the trainer drew. `place_terrain_course` stands
it in the compiled model (positions, turns, sizes, bounds) and re-boxes the
world body's bounding-volume tree: stock MuJoCo culls a static geom by that
tree, built round course 0 at compile, and a block dropped on a re-placed
box fell through it to the plane until the tree was re-boxed. The seed's
scan and predicates read the same course, and its row's
`detail.terrain.course` names it.

### Scans, and the course in the trace

**The course travels with the trace (ADR-734, 2026-10-16).** `rollout_policy`
returns `terrain`, `terrain_drawing` of the course its task stood on: a box
course's boxes as centres, `xyzw` turns and half-extents in mm, without the
parked slots, and the plane; or a heightfield's grid of heights over its
extent, sampled to at most 129 vertices a side. The worker's rollout trace,
each checkpoint's trace and each evaluation seed's trace carry it, so the
dashboard and an evaluation's film show the course an episode actually
stood on, not the model's course 0. It is absent on flat ground, so every
earlier trace is the document it was.

**Height scan (ADR-715, 2026-10-16).** `assembly.observation(trunk,
"height_scan", name="scan", role="privileged")` reads the ground round a
component. `scan_0` .. `scan_14` are its height in mm above the ground at a
fixed grid: 5 points along its heading (100 mm behind to 300 mm ahead) by 3
across it (±100 mm). `scan_4` is the point under the body. The grid turns
with the body's heading, its x axis projected on the ground, and not with
its pitch or roll. The ground is the course's heightfield elevation, read
bilinearly and held at the edge, a box course's highest box top (ADR-716),
or the plane at z = 0. It is no sensor:
the bundle's `scans` section names the body by its index and states the
grid, and the channels come last in every vector, after a reference's
tracking channels. The engine (`height_scan_values`) and the trainer
(`height_scan_vector`, on MJX's `xpos`/`xmat` and the course's own ground)
each compute it. `role="privileged"` keeps it to the critic, the reward and
the terminations (orun7 O5). `role="policy"` gives the actor the same 15
channels, after its reference clock, as a depth sensor's map of the ground
would (orun8 O2, ADR-748); a warm start across that change is refused,
because the actor's inputs move.

**Forward scan (ADR-821, 2026-10-24).** `assembly.observation(trunk,
"height_scan_far", name="scan_far", role="policy")` is the same reading at a
second fixed grid, where a run places its takeoff: 15 points along the
heading from 400 mm to 1800 mm ahead, 100 mm apart, by 3 across at -150, 0
and +150 mm, so `scan_far_0` .. `scan_far_44`, and `scan_far_{3i+1}` is the
centre line at `400 + 100 i` mm. It starts where `height_scan` stops, so the
two read the ground from 100 mm behind to 1800 mm ahead with no point read
twice. Each kind's grid is `CadexDynamics.SCAN_OBSERVATION_KINDS[kind]
["offsets_mm"]`, stated on the bundle's `scans` row, so the engine and the
trainer read every kind alike; `docs/probes/l3r1/scan_far.py` holds them
equal over a hurdle at five distances, the body straight and turned.

## 3. Two rules the design rests on

**A trained policy is an asset, not a derivation.** VISION principle 3 says
the script is the truth and any state that cannot be rebuilt from it is a
bug, and a policy is weights from hours of stochastic GPU compute. So a
policy lives in the project's `assets/` (name-checked, sha256'd, 128 MiB in
all) exactly as an imported STL does, brought home through `put_asset`; the
script declares how it was trained and names the weights by file *and*
digest (`assembly.policy`). Policies are small — measured 4.6 KiB to
902 KiB — so this needed no protocol change. What holds is that **a rollout
of a fixed policy on a fixed model is deterministic**, so trace digests hold
even though training does not.

**One unit boundary.** The script surface speaks millimetres, degrees and
kg/m³; MuJoCo's defaults assume SI. Every conversion is one number computed
in `CadexDynamics.py` — the pure module does all arithmetic, the worker
every FreeCAD read — and an observation leaves in the bundle with a
per-channel `scale` the trainer multiplies by, so nothing converts outside
the engine. A quantity whose meaning depends on whether a joint turns or
slides carries a suffixed pair (`control_deg`/`control_mm`,
`armature_kgmm2`/`armature_kg`, …), and passing the wrong one is a refusal.
Since ADR-725 no test greps for a second conversion site; the rule holds by
review.

There is no train button (ADR-084): training needs JAX on a GPU, so it runs
offboard on the person's own machine, dispatched through `cadex train` or
the `train_start` tool, and the weights come home through `put_asset`.

---

## 4. The slices

The development slices M0–M9 (ROADMAP Phase 14, all closed) are in
[`history/MUJOCO-SLICES.md`](history/MUJOCO-SLICES.md); a citation of
"`docs/MUJOCO.md` M2" (or any M-number) resolves there.

---

## 5. Known hazards

Ranked by how quietly they fail. Hazards 1–7 are handled; one line each
keeps the numbering, and the full record is in the history file.

1. **Units** — one conversion site (§3); a wrong-unit parameter is a refusal.
2. **Convexity** (ADR-079) — concavity is a mesh's hull volume against the
   mesh's own, both from the same vertices, and a concave part is refused
   unless the script says `hull`; a second comparison against the exact
   volume asks whether the mesh is still the part, and `hull` does not waive
   it. `mesh` and `hull` are two kinds so that accepting a hull is a word in
   the script.
3. **Cross-version drift** — a retained artifact's SHA-256 is in the project
   digest (ADR-068), so a MuJoCo bump is a loud `open_project` refusal, not
   a silent change; `open_project restore=false` and a re-accept is the way
   through, and nothing yet offers that in words.
4. **Multi-threading** — islands off explicitly and sleep off by assertion,
   both checked on the compiled model and recorded in the trace.
5. **Loop extraction** — a breadth-first spanning forest from the grounded
   components; every other joint is an equality constraint, closed against
   sites and stiffened to two timesteps.
6. **Frame budget** — two caps: frames and poses for what leaves the
   engine, `MAXIMUM_SOLVER_STEPS` for what it does.
7. **Scope creep into a UI** — none; the dashboard is read-only (ADR-537).
8. **A collision shape and the solid it stands for are in the same frame
   and are otherwise unrelated** (ADR-087). `collision(...)`'s `offset`
   places a primitive in the **component frame**; `part.box(..., origin=…)`
   moves the solid within that same frame. Nothing connects or checks them,
   so a shape can be the right kind, size and body — and 20 mm from the
   surface it stands for. Measured on the one-leg hopper: a floor authored
   `part.box(4000, 600, 40, origin=[-2000, -300, -40])` has its visible top
   at z = 0 while its collision `box` with no offset spans z = −20…+20; the
   foot rested on that invisible shelf, the policy trained against it and
   every gate passed twice. It yields a mechanism that runs, exports, trains
   and plays back — and is not the mechanism it is described as.
   **What catches it:** `model_evidence` reports the contacts present at the
   exported keyframe (count, the two geom names, world position, signed
   distance): one contact at z = 20.00 mm on the broken floor, none on the
   corrected one. The agent reads it with `inspect scope=contacts` after an
   `assembly.mjcf` export; the server computes `collision_proxies`, which
   the dashboard does not draw (ADR-533). Evidence rather than a refusal,
   because a mechanism designed to start on its feet is ordinary (ADR-087
   §2–3). A `mesh` or `hull` shape's evidence carries no vertices, so for a
   `hull` this hazard still lives.
9. **A reward built on raw Cadex channels is badly conditioned, and it fails
   by training worse rather than by failing.** Channels are in millimetres
   and degrees, so an absolute position arrives in the hundreds while the
   trainer's normaliser starts at mean 0, variance 1. Measured on one
   mechanism: a torso height at ≈ 451 mm took reward/step 4.46 → 3.66, worse
   than doing nothing; a slider displacement about 0 describing the same
   height went −0.243 → −0.028. **What to do:** write terms on quantities
   near zero, or subtract the baseline in the expression —
   `assembly.reward("rail_p + 26.3", ...)` — so the channel keeps its unit
   and the arithmetic stays visible. Not normalised in the trainer,
   deliberately: a hidden transform makes runs incomparable. The trainer
   stops at the first non-finite `reward/step` or `loss` and names the
   iteration (ADR-088).

10. **A limb can be under-actuated, and the trained policy will look like a
    gait rather than like a failure** (ADR-090). Holding a limb out takes
    about **weight × limb length**: a 13.7 kg hopper on a 200 mm shin needs
    26.9 N·m to hold a 90° crouch and was given 12.0. The policy still
    converged and played; the knee sat at exactly its 12.00 N·m limit in all
    27 scripted push-offs, and the "tucked leg" was falling. **What to do:**
    compute weight × limb length against `torque_limit_nmm` before training,
    and prove the mechanism with a scripted open-loop attempt (a grid of
    crouch-and-extend tries against the exported MJCF; seconds, no learning)
    before buying GPU time — sized at 60 N·m that leg went from 0 of 27
    configurations leaving the ground to 27 of 27. Treat an actuator pinned
    at its limit as a mechanism finding. And read a gate failure as a claim
    about the *pair*, mechanism and controller: bracket a PD sweep from both
    sides (ADR-092 §5).

11. **An ungrounded island does not keep the pose its component placements
    state** (ADR-092). For an island the joints never reach from ground,
    `assembly.component(placement=...)` is a starting point: the island has
    six free degrees of freedom and the native solver answers with its own
    member of the solution family — a three-part probe with a hinge placed at
    30° solved with the hinge at zero, and a biped had all eight joints
    zeroed and moved (90.2, 18.0, 58.1) mm and about 40°. Every joint is
    satisfied and `solve` reports solved; only *where the machine is* is
    wrong. ADR-335 narrowed it: when *nothing* is grounded the solver holds
    the first component in script order, so a single-island free base keeps
    its placements; the hazard remains for a second island, or one beside a
    grounded component. **What to do:** put the pose in the solids and give
    a joint's two connectors the **identical posed world frame**; each
    joint's zero is then the posed configuration, and the reset pose is the
    project's stored `param_values` (ADR-092 §4).

12. **Float dust in an all-zero MJCF field** (ADR-092). `_field_drift`
    normalises by a field's largest magnitude, so a field that should be
    zero and held ~1e-16 read as a relative drift of 1.0 and refused.
    **Fixed at the source by ADR-441**: the writer emits a float below 1e-12
    as `0`, and `_field_drift` compares values below `MJCF_WRITER_ZERO` as
    zero on both sides.

13. **A witness records what the GPU rounded the network to** (ADR-094).
    `jax.vmap` turns each layer's matrix-vector product into a batched
    matmul that XLA runs at TF32 on Ampere+ tensor cores (eps ~4.9e-4),
    while the engine evaluates in float64. The error is relative, so it grows
    with the activations — 7.3e-6 at iteration 2, 1.43e-4 at 2000 — and a
    3 h 49 m run was refused. The trainer records the witness under
    `jax.default_matmul_precision("highest")` (training itself stays at the
    default) and checks it with `witness_disagreement()`, a float64 copy of
    the engine's test, before writing; it prints the margin and warns under
    100x.

14. **A feasibility gate can encode a worst case the task never reaches**
    (ADR-095). Weight × a full limb length is the arm of a leg held
    horizontal; on a PLA biped it printed DO NOT DISPATCH at 0.84x while
    `mj_inverse` wanted 2.39 of 216 N·mm and a PD stood the whole episode.
    **What to do:** use the arm the *task* uses — for standing a ~30° lean,
    for the ankle the sole's forward reach — and keep the old column beside
    it as a bound. Re-specifying a gate is a decision to record, never a way
    to click past a red one.

15. **A policy that stands can be standing on pinned motors, and the
    trajectory will not say so.**
    *Discovered by ADR-096.*
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
    rollout frame's `actuator_commands`, its `actuator_efforts` against the
    channel's `effort_low`/`effort_high` (ADR-694; for a position drive the
    command is a setpoint, so only the effort shows a torque clamp), drawn
    per motor by the dashboard's Activations editor (ADR-727), and bounded
    in a spec by `effort_clamp_share_max` and `effort_rms_rated_ratio_max`
    (ADR-704, ADR-707). Treat "the reward went up" and "the mechanism is doing something a machine
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


18. **A check that looks like a measurement can be computing nothing**
    (ADR-099). `mj_inverse` with an external force on a floating base
    returns leg torques bit-identical to the undisturbed case, because the
    free joint's residual absorbs the push (the tell: every joint reported
    the same worst azimuth); a joint-space PD has no base-attitude feedback,
    so gating a mechanism on its pushed survival fails every mechanism; and
    summing every declared force over three seconds gave 2.34 N·s where the
    shove delivers 0.042. **What to do:** vary the input and check the output
    moves, and prefer statics you can write down — the gate that survived
    asks whether the righting moment a shove needs is inside what the
    footprint and the ankles can supply.

19. **The trainer's reward is not survival, and can move the other way**
    (ADR-099, ADR-100, ADR-101, ADR-103). The M9 run's curve rose to its best
    while survival fell 12/12 → 0/12. Most of that inversion was the
    evaluator — it compounded domain randomisation in place over one model
    (ADR-103 §9) — and part was a trainer that never ended an episode
    (ADR-101, fixed). What remains is two ordinary facts: MJX and stock
    MuJoCo are different implementations (they agree to machine epsilon
    without contact and differ most on box against box, ADR-103), so they
    compare statistically and in no other way; and reward per step is not
    the result.
    **What to watch:** mean episode length and mean exploration σ
    (`action_std`) beside `reward/step` — on the trainer's stderr line, in
    `progress.json`, in the policy header's curve rows and in the
    dashboard's training plots. A reward climbing while episode length falls
    is this hazard live; a σ that has walked well off its start means the
    rollouts and the installable mean policy are no longer the same policy.
    **What to do:** never install, rank or stop on the trainer's reward.
    Judge checkpoints by what they did — `cadex evaluate` on the spec's
    frozen seeds, or a run's checkpoint rollouts — against **the run's own
    bundle**, and treat `<out>.best.cxpolicy` as a filename, not a verdict.
20. **MJX has no contact function for six geom type pairs, so a model
    every engine check accepts can still be untrainable** (ADR-281).
    Measured on the `ot4-mix52` walk: an agent-authored slider-crank gave
    the frame a `cylinder` collision rail and the coupler a `box`, the two
    are two joints apart so nothing excludes them, and `mjx.put_model`
    raised `NotImplementedError: (mjGEOM_CYLINDER, mjGEOM_BOX) collisions
    not implemented` 2.27 s into the training leg — after the assembly
    solved, the MJCF exported, the pose held to 0.0015 mm and the rollout
    ran. Stock MuJoCo simulates that contact; the limit is the JAX
    backend's. The six are **box/cylinder, cylinder/mesh, box/ellipsoid,
    ellipsoid/mesh**, and on a heightfield course **cylinder/hfield and
    ellipsoid/hfield** (ADR-714). `assembly.task` now refuses them by name
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
    solved placements, which no fixture built forwards ever could.
22. **A light joint's stop is a weak spring, and a bench at standing load
    does not show it** (ADR-724). MuJoCo's joint limit is a soft constraint
    whose default `solreflimit` (0.02 s, damping ratio 1) scales with the
    joint's own effective inertia. On orun7-cat's 144 g passive paw pin
    (1.7e-4 kg·m²) 0.5/2/4 N·m pushed it 6.3/25.2/50.4° past its stop; in a
    rollout the paw folded up to 72° past a 45° stop. A standing check
    passed. `joint_dynamics(limit_time_constant_s=, limit_damping_ratio=)`
    sets the stop (`solref_limit` on the joint; `0.004` gave 1° at 2 N·m),
    and the model evidence carries it as `limit_solref`. MuJoCo silently
    raises a time constant below two solver steps to that floor
    (`refsafe`), so a smaller one is refused
    (`limit_time_constant_below_solver_floor`), and so is a limit stiffness
    on a joint with no limits. Check a passive joint's stop under the load
    the gait puts on it, not the load standing puts on it.


## 6. Open questions

- Is there a Phase 11 story here? A pybind11 binding over OCCT and a MuJoCo
  integration are independent, but the `assembly` domain is Phase 11f — the
  largest — and dynamics puts weight on it.

Every other question this section held is answered — units, a sibling
`api.dynamics`, two frame budgets, a trace in the project digest, where
training runs, a policy as a `put_asset` asset, a rollout's frame rate, and
why the trainer's reward disagreed with survival — and the answers are in
the history file under §6.

## 7. From a drawing to a standing policy

This is **how to use it**. Machines from a one-leg hopper and two bipeds to
the cats have gone through it, and the order is load-bearing: every step but
training is cheap, and training costs hours of a GPU.

**The projects themselves are not in this repository** (ADR-088 §6); what is
reproducible is the method. The commands (`docs/CLI.md` is the contract):
`cadex smoke`, a short stock-MuJoCo hold or zero-action rollout that answers
"does it stand, does it fall, does a loop stay closed" without a trainer
(ADR-352, ADR-594); `cadex train` and `cadex walk` (`--remote`,
`--detach`/`--complete`), or the `train_start` / `train_status` /
`train_stop` tools `cadex mcp` serves (ADR-464); `--checkpoint-every N`,
which rolls each checkpoint out through the engine while it trains
(ADR-544); and `cadex evaluate`, which holds the declared policy against the
script's `assembly.success` spec — behaviour predicates on frozen seeds,
never the reward (ADR-455..457, ADR-587; `docs/XSCRIPT.md`). The trainer's
venv and its seven exact pins are `training/SETUP.md`'s. The steps below
also name the project scripts (`measure.py`, `feasibility.py`,
`capability.py`, `compare.py`, about a hundred lines each, driving `cadexd`
over NDJSON) the first machines were driven with.

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
   origin, and not the proximal joint: the model's fields then carry real
   half-lengths (hazard 12's refusal of an all-dust field is fixed, ADR-441).

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
   per change; the dashboard plots the curves of a run under the project's
   `runs/<run>/` (a `cadex walk --out <project>/runs/<name>` or the
   `train_start` tool). The gap between the best iteration and the current
   one is the stopping decision.

8b. **Before dispatching, check that the box's trainer is the one this
   checkout has.** `remote_train.sh` copies a bundle and a model and runs the
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
   animations do not. In the product today, a local run's
   `--checkpoint-every` rolls each checkpoint out through the engine while
   it trains (ADR-544) and the dashboard plays them; `cadex evaluate`
   judges the one you choose against the spec.

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

13. **Read the commands before you believe any of it** (ADR-096). Each
    rollout frame carries `actuator_commands`, `joint_positions`,
    `joint_velocities` and `actuator_efforts` against the channel's
    `effort_low`/`effort_high` (ADR-694), and the dashboard's Activations
    editor draws a gauge per motor from them and paints the parts each
    motor moves by how hard it works (ADR-727). The
    trajectory says what the mechanism did; this says what the policy
    decided, and the two can disagree in a way only this one shows —
    hazard 15 is a policy that plays as a clean stand while holding three
    motors at 98 % of stall for the whole episode. A command pinned at an
    end is the finding.
    A success spec can now bound it instead of a reader eyeballing it
    (ADR-704): `effort_clamp_share_max` and `effort_rms_clamp_ratio_max` name
    the worst drive against its clamp, `command_rate_rms`,
    `joint_acceleration_rms_deg_s2` and `command_high_frequency_share` say
    how smooth the commands and joints were, and `cost_of_transport` what the
    motion cost. panel-cat-3's r5 trot, the orun6 baseline, reads 5.96
    ranges/s, 8,032 °/s², 6.4 % of command power above 3× its 2.44 Hz
    stride, its left hock at the clamp 19 % of the time, and a cost of
    transport of 0.67 (medians over seeds 1001–1010).
    A drive declared with its continuous rating (`rated_torque_nmm`,
    ADR-707; `lib.qdd` passes the datasheet's) carries it to the bundle's
    action and the trace's channel as `rated_effort` / `effort_rated`, and
    `effort_rms_rated_ratio_max` bounds the worst drive's RMS effort against
    it. r5's right scapula reads 1.46× its 8.3 N·m rating, and 9 of its 19
    drives are over theirs.

### The learner: Brax's PPO (ADR-712)

`training/cadex_train.py` trains with **Brax's PPO** (`brax==0.14.2`,
Apache-2.0), on the same MJX physics as before. The environment is still
Cadex's: `build_environment` turns the bundle into a batched environment
with the observation slices, the command filter and slew, sensor noise,
goals, the gait reference and its random start, reset variation, pushes,
randomised models, reward, terminations and episode. Brax supplies the
learner:

- the policy and value networks: swish MLPs, 512-256-128 by default;
- the tanh-squashed Gaussian;
- the running observation normaliser, with ADR-589's sensor floor kept;
- the PPO loss and GAE, where a timeout is masked as truncation rather than
  scored as a failure (ADR-101);
- minibatched SGD under optax's Adam, with gradients clipped at norm 1.

The trainer's own loop is Brax's `training_step` with one unroll per
iteration, so every iteration still reports, checkpoints and is judged.

**Why.** orun6's benchmark (B1) trained Unitree Go1 on MuJoCo Playground's
joystick task through both learners. The hand-written PPO took four
full-batch gradient steps an iteration and learned to stand still. Brax,
configured as Playground configures it, learned a trot. Measured through the
engine's own rollout at a 1.0 m/s command, 10 seeds:

| | speed | falls | gait | train time |
|---|---|---|---|---|
| the hand-written PPO | 3 mm/s | 0 | none | ~5 min |
| Brax PPO in Cadex | 977 mm/s | 0 | diagonal trot | 340 s |
| Playground's own recipe | 933 mm/s | 0 | diagonal trot | 378 s |

**What a policy file carries.** The `.cxpolicy` format is unchanged. The
network's activation is `swish`, which the engine now evaluates. The
container stores the deterministic half of Brax's last layer, so the engine
still plays `tanh(output) * scale + bias`. The exploration width depends on
the observation, so `exploration.log_std` records its mean over the witness
observations and `exploration.state_dependent` is `true`.

A warm start must name the activation its source was trained with. Every
policy before ADR-712 is `tanh`, so continue one with `--activation tanh`.

### Saying "smooth": the previous action and the action rate (ADR-696)

A policy that jitters can still pass a spec written in speed, tilt and
heading; panel-cat-3's r5 trot did, at 320 °/s of command-rate RMS. Two
standard terms answer it, and both need the commands the policy issued,
which no MuJoCo sensor reads:

- **`assembly.observation(actuator, "command", name="hip")`** gives `hip`,
  the command in force (clamped, after any `--action-filter-alpha` or
  `--command-slew-deg`, in the action's unit), and `hip_rate`, its change
  over the last control step per second. Before the first action both read
  the reset keyframe's command; the first action reports a rate of 0. Left
  `role="policy"` it is the **previous action** as an input, which the
  robot knows exactly and so needs no sensor; `role="privileged"` keeps it
  out of the actor and leaves it to the reward and the critic.
- **An action-rate term** is then a reward: `assembly.reward("-((hip_rate /
  300)^2 + (knee_rate / 300)^2 + ...)", weight=...)`. A reward expression
  may be 512 nodes (ADR-697), so one term covers a 19-drive quadruped.

The bundle carries these rows in `commands`, after the goal channels, so a
task without them keeps its digest and a task that gains them keeps every
other channel's address. `CadexDynamics.evaluate_episode` and the trainer
each compute them from the commands they issued. They do not count against the 128-channel sensor cap: one per actuator, so
the action list bounds them.

### Saying "foot down": the contact channel (ADR-698)

A gait reward that is not a pose needs to know which feet are on the
ground: a contact schedule pays for the right ones, feet air time pays for
swing, and foot slip is a foot's speed while it is down.

- **`assembly.observation(paw, "contact", name="paw", role="privileged")`**
  gives `paw`, the summed normal force of every contact on the paw's
  collision shapes in N, and `paw_down`, 1 while that force is above the
  bundle's `contact.down_above_n` (0) and 0 otherwise. A resting body reads
  its own weight.
- **The file carries it.** The export draws an invisible box site round the
  component's colliding shapes, from each shape's bounding sphere, and puts
  a `touch` sensor on it. Stock MuJoCo and MJX compute the force; the flag
  is one comparison the engine and the trainer each make. A component with no collision shape is refused.
  The export compares the file's touch at the keyframe with the engine's
  unless the body rests exactly tangent to what it touches, where the force
  is round-off (ADR-757).
- **It is privileged.** No sensor in the library measures foot contact, so
  the reward, the terminations and the critic read it and the policy does
  not. A contact schedule term is then `paw_down` (or `1 - paw_down` in
  swing), and a slip term `-(paw_vx**2 + paw_vy**2) * paw_down` beside a
  `component_linear_velocity` of the same paw.

### Saying "smooth": joint acceleration and the regularisers (ADR-699)

- **`assembly.observation(knee, "acceleration", name="knee_acc",
  role="privileged")`** gives `knee_acc`, the joint's `qacc` after the
  control step's last solver step, in deg/s^2 (mm/s^2 on a slider). MuJoCo
  has no sensor for it, so the bundle states the degree of freedom in an
  `accelerations` section after the command channels, and the engine and
  the trainer each read their own simulator's `qacc`. It is the quantity
  MuJoCo Playground's locomotion recipes penalise. It must be privileged:
  nothing on the robot measures it.
- **Every standard regulariser is then a reward term**, each on a channel a
  task already has:

  | term | expression | channels |
  |---|---|---|
  | action rate | `-(hip_cmd_rate / 100)**2` | `command` (ADR-696) |
  | joint acceleration | `-(knee_acc / 10000)**2` | `acceleration` |
  | torque | `-(knee_tau / peak_nmm)**2` | `actuator_force` |
  | mechanical power, W | `-abs(knee_tau * knee_vel) * 1.745e-05` | `actuator_force`, `velocity` |
  | foot slip | `-sqrt(paw_vx**2 + paw_vy**2) * paw_down` | `component_linear_velocity`, `contact` |

  ADR-699 wrote all five on one mechanism, held each to its formula, and
  trained it.

### Showing a gait: the procedural reference (ADR-702)

A reward that describes a gait pays for the cheapest motion that fits the
description. `CadexGait.generate(model, legs, gait, speed_m_s)` builds the
gait to track instead. It returns one periodic stride on the robot's own
legs (`cadex-gait-clip-v1`): joint angles, foot positions, the contact
schedule, and body height and pitch. No motion capture is involved.

- **Footfall.** Named gaits are `walk`, `trot`, `pace`, `canter`,
  `transverse_gallop`, `rotary_gallop`, `half_bound` and `bound`, with
  Hildebrand's phase offsets (left hind = 0). Explicit `offsets` and `duty`
  work as well.
- **Scale.** Stride length is `2.3 h Fr^0.3` (Alexander 1976), where `h` is
  the hip height measured on the model. The frequency is `v / stride`.
  `stride_length_m=` overrides it.
- **IK.** Each leg is solved by damped least squares within its joint
  limits. A joint that more than one leg passes through is a body joint
  (`spine_joint=`). A body joint coupled to the spine joint by an
  `equality/joint` (a cable-driven second spine joint) follows it by its
  polynomial (ADR-783).
- **Refusal.** A foot that cannot be reached raises `GaitUnreachable`,
  naming the leg, the moment in the stride, the miss and the joints at a
  stop. It never clamps silently.
- **Closed legs (ADR-776).** A leg's loop closures (`equality/connect`)
  and joint couplings (`equality/joint`) are held in the same solve, with
  a rod's own pins solved beside the leg's joints, so a coupled paw takes
  the angle its linkage gives it. A loop that cannot close is refused. The
  clip's `ik.closures` names each leg's rows and its worst closure error.
  `heels=`, `heel_from=`, `body_drop_m=`, `body_pitch_deg=` and
  `stance_shift_m=` ask for a plantigrade stance (a heel body's lowest
  point held on the ground from a share of the stance to toe-off, under a
  crouched trunk); `assembly.gait` declares them as `heels=`, `heel_from=`,
  `body_drop_mm=`, `body_pitch_deg=` and `stance_shift_mm=` (ADR-777).
  The heel is eased, not stepped (ADR-778): from touchdown it falls
  linearly to the first held sample, and after toe-off it rises over three
  swing samples to the height a free swing gives it. `flat_feet=True`
  (ADR-780) also holds each such foot at the pitch it stands at while its
  heel is held, so a paw on a passive pin lies flat instead of rolling
  onto its rear pad. `flat_feet="sole"` (ADR-784) holds it instead at the
  pitch where its collision geoms reach the floor together: a paw whose
  home pose stands on its toe still lies with its sole flat.
  `trail_feet=True` (ADR-785) lays a flat foot flat only while it is down,
  so through the heel's ease after toe-off the paw trails the leg instead
  of staying level, which on leo v03 turned its free pin to 56–58° in
  early swing.
- **Two feet (ADR-754).** `legs` keyed `L`, `R` builds a biped's stride:
  `walk` (duty 0.6) and `run` (duty 0.35), the feet half a stride apart and
  the left foot the phase reference (Alexander 1984). In a task,
  `assembly.gait([foot_l, foot_r], gait="walk", speed_mm_s=...)`.

Measured on panel-cat-3's legs (hip height 427 mm), against Alexander's
stride:

| gait | speed | Alexander stride | longest reachable stride |
|---|---|---|---|
| trot | 1.0 m/s | 639 mm | 595 mm |
| trot | 1.7 m/s | 879 mm | 597 mm |
| trot | 2.5 m/s | 1108 mm | 601 mm |
| rotary gallop | 2.5 m/s | 1108 mm | 674 mm |

The joint ranges cap a trot stride near 0.6 m. At 1.7 m/s that forces a
0.35 s stride (2.9 Hz) where dynamic similarity gives 1.9 Hz: the short,
quick trot r5 learned.

**In a task (ADR-703).** `assembly.gait([lf, rf, lh, rh], gait="trot",
speed_mm_s=1000, stride_length_mm=580, spine=j_spine)` passed to
`api.task(reference=...)` puts the stride in the bundle's `reference`
section, generated on the exported model about the reset keyframe, with
every body's pose at each sample. The dashboard's 3D viewport lists it under
**Gait references** and loops it, so the intended gait can be judged before
anything trains on it. An unreachable stride refuses the task
(`gait_unreachable`) rather than building a reference nobody can track.

**Judged against it (ADR-705).** A success spec on a task with a reference
can bound four metrics read against it. The clock is the left hind's own
landings, so a policy is compared stride by stride, whatever its stride
frequency. `footfall_phase_error_max` is the worst foot's median landing
error, in cycles, from the reference's phase offsets (a skipped or doubled
landing is 0.5), counted in whole frames, so two frames of a 20-frame
stride is exactly 0.1 (ADR-719). `duty_factor_error_max` is the worst foot's duty factor
less the reference's. `stride_frequency_ratio` is the measured stride
frequency over the reference's. `reference_joint_rms_deg` is the RMS joint
error at the same phase of each stride. r5's trot, against a trot generated
on its own model at its 1.69 m/s and the 597 mm reachable stride (medians,
seeds 1001–1010): footfall within 0.05 of a cycle (one frame), the right
hind skipping 3 of 21 strides, duty 0.22 short of 0.45 (hinds down a quarter
of the stride), stride frequency 0.88 of the reference's 2.84 Hz, and
18.6° RMS joint error (knees 33°).
`command_rate_reference_ratio` and `joint_acceleration_reference_ratio`
(ADR-708) hold a rollout's smoothness against the clip's own on the same
drives, read by `reference_smoothness(clip, channels)`. Measured, the clip
is not gentle: r5's own-speed trot asks 4.56 ranges/s and 12,485 °/s², so
r5 reads 1.31× and 0.64×. Its excess is jitter, not magnitude, and that is
what `command_high_frequency_share` sees (6.4 %, against the clip's
near-zero). The cat's 1.0 m/s, 580 mm trot asks 2.49 ranges/s and
4,305 °/s².

**Tracking it (ADR-706).** The same reference is a set of channels on a
gait clock. The clock starts at the reference's phase 0, the left hind's
touch-down, on an episode's first step, because the reset keyframe is the
pose the stride was generated about. It turns `control_interval /
period_s` of a cycle per step. `ref_sin` and `ref_cos` are the clock, and
the policy reads them; a controller keeps its own timer, so they are
grounded. For the reward and the critic, each `position` observation of a
joint the stride poses gains `<name>_ref`, the angle the reference asks
for, in degrees. Each foot gains `ref_<foot>_lift`, in mm above the
reference foot's lowest point (0 in stance), and `ref_<foot>_down`, 1 while
the reference has it down. Between two of the clip's samples a channel is
read linearly, and a down flag switches at the midpoint. A step is scored
against the reference where it lands, one step on the clock, so the reward
for a pose is the reference's pose at the same moment. A tracking reward is
then expressions, for example:

```python
reward=[api.reward("exp(-((q_knee_l - q_knee_l_ref)^2 + (q_hip_l - q_hip_l_ref)^2) / 450)", weight=1.0),
        api.reward("exp(-((pfl_z - 22 - ref_lf_lift) / 20)^2)", weight=0.3),
        api.reward("1 - abs(fl_down - ref_lf_down)", weight=0.2)]
```

The bundle carries the clip as a `tracking` table, one row per sample in
each observation's own unit, so the engine and the trainer interpolate it
and never convert.

**Starting inside it (ADR-709).** An episode that starts at a standstill
and is asked for 1 m/s at step 0 falls before it learns to stride (track-s1
and track-s2). `api.task(reference_start="random")` is reference state
initialisation (Peng et al. 2018): a seeded episode draws one of the clip's
samples, `randrange(samples)` after the goal draws, and starts in the
clip's own state there. The pose is the clip's (height, pitch, every
joint) with the base over the keyframe's ground point; the velocity is the
clip's central difference round the stride, so the base moves at the
reference's speed. The gait clock starts at `sample / samples`. A reset
variation is composed on top, its velocities added rather than set. The
bundle's `tracking` section carries `reset_qpos` and `reset_qvel`, one row
per sample; the trainer draws a sample per environment on every reset and
carries it beside the step counter. An unseeded episode, and so the build's
own rollout, starts at the keyframe and phase 0. A success spec's seeds are
seeded episodes, so they start mid-stride too: the spec judges the gait,
not the launch from a standstill.

**A cadence that follows the command (ADR-752).** One clip is one speed:
the cat's 580 mm trot turns at 1.72 Hz however fast it is told to run, and
at a 3 m/s command a fixed clock asks for a 1 m/s stride. With
`api.task(reference_cadence="speed")` the clock turns with the task's one
`speed` goal instead: each step it turns `turn_per_step * (|g| /
clip speed) ** reference_cadence_exponent` of a cycle, `g` the command in
force for that step, summed from the reset and kept in [0, 1). The
exponent defaults to 0.4: at a free stride length, Alexander's dynamic
similarity gives stride frequency ~ v^0.4 (`CadexGait.stride`); 1.0 holds
the stride's length and scales only its rate. On the cat's clip the clock
turns at 1.31, 2.03 and 2.68 Hz at 0.5, 1.5 and 3 m/s, so the clip's poses
ask for 0.76, 1.18 and 1.55 m/s; a zero command stops it, and a reverse
command turns it at its magnitude. The joint table is still the one
stride, so a cadence quickens the gait and does not lengthen it. The
bundle's `tracking.cadence` names the goal, its channel, the clip speed,
the exponent and the rule. The trainer carries the turned cycles per
environment beside the step counter (`tracking_turn`, `tracking_vector`).
A warm start may move onto or off a cadence as a curriculum step
(`tracking.cadence`, ADR-161): the actor reads the same two channels. The
dashboard's Activations editor does not rebuild a cadenced clock from a
trace's time, so it shows those two inputs at the normaliser's mean. The
reference family's `stride_frequency_ratio` is still against the clip's
own frequency.

**A speed schedule: a family of strides over the command (ADR-773).** A
cadence quickens one stride; a real gait also lengthens it and changes its
footfall timing with speed (a cat's rotary gallop: walk-like alternation,
lead/trail lag ~0.25 of a stride, slow; almost a half-bound, lag ~0.05,
at a sprint). `api.task(reference=[slow, ..., fast])` takes two to eight
`api.gait` values, slowest first, on the same feet and spine and in one
footfall order (`schedule_footfall_order` otherwise). The engine generates
them at one sample count, the largest any takes at 50 Hz, so a phase is
one row of every stride. Each control step the task's one `speed` goal
`g` picks the bracketing strides `i, i+1` and a weight `w`; every channel
after the clock is `(1-w) table_i + w table_{i+1}` read at the phase
(a held foot flag thresholded after the blend), and the clock turns
`(1-w) turn_i + w turn_{i+1}`, summed as a cadence's is, so a command that
steps or ramps (`api.goal(ramp_seconds=)`) moves the gait and never the
phase. The command is a goal channel: the policy reads it, so a deployed
robot is told its speed, and a reward pays tracking of it, not top speed.
Its `between` must lie inside the strides' speeds
(`schedule_does_not_cover_command`). With `reference_start="random"` the
start row is a random sample of the stride nearest the opening command
(`reset_qpos` holds every stride's samples, stride by stride). The bundle
keeps `reference` as the slowest stride (with the poses the dashboard
plays), adds `reference_schedule` (every stride, no poses) and
`tracking.schedule` (`speeds_mm_s`, `periods_s`, `turns_per_step`,
`tables`, `rule`, `start_rule`). `CadexDynamics.tracking_turn`,
`tracking_values`, `reference_start` and the trainer's `tracking_turn`,
`tracking_vector`, `schedule_blend` and `schedule_nearest` are the two
copies of the rule; an evaluation judges the gait against the stride
nearest the settled command (`judged_reference`). It cannot be combined
with `reference_cadence="speed"`, and a warm start onto a schedule is not
a curriculum step (`reference` and `tracking` move).

**Weighted command draws (ADR-824).** A speed goal drawn uniformly over a
schedule's whole span trains each band of speeds in proportion to its
width. `api.goal(bands=[[low, high, weight], ...])` weights it instead: the
bands tile `between`, and a segment picks one with probability its weight
over the total (one `random()`), then draws `uniform` inside it. The bundle's
goal keeps its `low` and `high` and gains `bands`; its `goal_algorithm` gains
`GOAL_BAND_ALGORITHM`'s clause, and the trainer's `draw_goals` draws the same
two numbers per segment. A goal without bands draws as before, byte for
byte. Refused: `goal_bands_malformed`.

**Gait families: a switch inside a speed schedule (ADR-822).** A walk or
trot and a gallop land their feet in other orders, so ADR-773 refuses to
blend them. `api.task(reference_switches=[...])` states one entry per
neighbouring pair of strides: `None` where the two blend, or a speed in
mm/s strictly between theirs where one family gives way to the next. Across
a switch `w` is 0 below the speed and 1 from it up, so the reference is
one stride or the other, never a blend; the clock keeps its phase and
turns at the stride in force. The footfall order is checked inside each
family only (`check_schedule_order`), and the start stride and the judged
stride are the bracketing one nearer in `w`, so they are of the family in
force. `tracking.schedule` then carries `switches_mm_s` and a `rule` with
`SCHEDULE_SWITCH_RULE`'s clause; a schedule with no switch is written as
before, byte for byte. Refused: `schedule_switches_count`,
`schedule_switch_outside_strides`, `schedule_switches_empty`.

**Screening drives against it (ADR-710).** Before a design change is
rebuilt or trained, `training/cadex_proxy.py` swaps datasheet drives, moves
and scales mass in the exported model, and replays the task's reference
with the base held, rating each drive's RMS torque and time at its peak
clamp against its datasheet (`training/README.md`). A drive that cannot
follow the clip while held will not track it free. Since a position servo
lags a fast stride, the screen that counts is `--support inverse`
(ADR-711): the clip's exact joint torques, by inverse dynamics with the
stance feet carrying the base. It also says how much of the base wrench no
foot can supply, which is how a reference that is not dynamically possible
(a gallop whose body does not fall in flight) shows itself.

The catalog's largest drive is the RobStride RS04 (`lib.qdd("robstride-rs04")`,
ADR-826): 120 N·m peak, 40 N·m rated, 1420 g, for joints a ~40 kg robot's
gallop asks about 100 N·m of. Its rear face has no published holes, so it is
held by its front face (`seat="front"`), and its straight torque–speed line
reaches 0 at 1200 °/s, so a fast joint on it loses torque early.

### Warm starts, families and teachers (ADR-791, ADR-755..760, ADR-825)

The trainer's flags are `training/README.md`'s; this is what each is for.

- **A wider command range, warm (ADR-791).** A warm start (`--init-from`
  with `--init-from-task-change`) may cross a goal change that touches only
  where the goal is drawn from — `CURRICULUM_GOAL_KEYS`: `low`, `high`,
  `nominal`, `sequence` — named the curriculum step `goal.range`. The actor
  reads a goal value as it is, so a wider range is new values on an input
  the network already has. Every other goal change is still refused. (orun19
  X1: a speed policy asked for a ceiling it was never trained on, instead of
  retrained cold.)
- **A canonical body (ADR-755).** `api.task(body=...)` maps a robot onto a
  family's named slots — `quadruped` (legs `fl`, `fr`, `hl`, `hr`) or
  `biped` (`l`, `r`), each leg `abd`, `hip`, `knee`, `ankle` — plus
  `morph.*` constants (knee direction, thigh and shank lengths, hip height,
  mass). The engine derives each slot's sign from the joint's axis at the
  reset pose (refused below |0.9|) and its offset from the reset angle; the
  bundle carries the resolved block and the trainer never re-derives it.
- **A base remap (ADR-755, ADR-760).** `--init-from-base REASON` lets
  `--init-from` cross onto another robot of the family: inputs and actions
  are matched by canonical name and sign-corrected, a source input the
  target lacks folds into the first layer's bias at its rest value, a target
  input or action the source lacks starts at zero, and `--critic-warmup` is
  required. The base's normaliser weight is kept on the inputs it shares; a
  new input takes its statistics from the target's first batches.
- **A family as one batch (ADR-759).** `--family BUNDLE…` trains one policy
  on built variants of one robot: the bundle is variant 0, the environments
  are split into contiguous blocks, one environment per variant (environment
  *e* seeded `seed + e`), and the actor and critic read each variant's
  `morph.*` constants. Such a policy is a **base, not a controller**:
  `assembly.policy` refuses it, and it is judged through an
  `--init-from-base` fine-tune onto one variant. An iteration costs about
  twice a single robot's (8.7 s against 4.4 s at 8,192 environments).
  `cadex train` and `train_start` pass both as the `family` and
  `init_from_base` settings (`cli/cadex_cli/loop.py`).
- **Teachers by command band (ADR-825).** `--teacher LOW:HIGH:POLICY`
  (repeated), `--teacher-goal` (default `cmd`) and `--distill-weight`
  (default 1) add to PPO's loss, on steps whose goal lies in a teacher's
  band, the squared distance between the student's played action (`tanh` of
  its location) and the teacher's. PPO still trains every step, so an
  untaught band learns from the reward alone and the student may outgrow a
  teacher. A teacher must share the model, the actor channels and the action
  table (its task may differ); bands may not overlap; a `--family` run is
  refused. The header carries `training.distill` (bands, digests, never
  paths) only on a distilled policy. l3r1 joined a stand policy and a gallop
  policy this way (`docs/probes/l3r1/distill.py`). `cadex train` does not
  pass `--teacher`; run the trainer directly.

### Off flat ground, and on command (ADR-714..722)

§2 has the details; the order is:

- **Train on boxes.** Declare the course `terrain={"form": "boxes",
  "random": {...}}`: a pool of seeded courses the trainer re-draws per
  episode (ADR-717). A heightfield is the default form and builds, but MJX
  is unstable on it under driven motion (§2, ADR-714), so it is for smooth
  hills on a model nobody trains.
- **Let the critic see the ground.** A privileged `height_scan` on the
  trunk (ADR-715). The actor never reads it.
- **Command the turn.** A `speed` goal and a `yaw_rate` goal, resampled in
  the episode. `sequence=[...]` scripts the opening segments, so every
  evaluation seed gets the same reversal (ADR-721).
- **Judge it.** `falls`, `distance_made_good_mm`, `steps_crossed` and their
  kin on a course, each seed on a held-out course of its own (ADR-718);
  `speed_error_rms_mm_s`, `yaw_rate_error_rms_deg_s` and
  `reversal_heading_error_deg_max` for the commands; the `appendage`
  metrics for a tail (ADR-722). A stand is judged at a command of 0
  (ADR-823): the speeds are measured and `speed_ratio` and `lateral_ratio`
  read `None`, so a predicate on a ratio fails at a stand; bound the
  measured speeds and the feet instead.
- **Stiffen a light stop** with `joint_dynamics(limit_time_constant_s=)`
  before trusting a passive joint on rough ground (hazard 22, ADR-724).

Two trainer options matter here. `--reward-floor 0` clips each step's
reward at zero, as Playground's locomotion recipes do (ADR-700). A warm
start (`--init-from`, with `--init-from-task-change` and
`--init-from-parent-task` across a reward or disturbance change) may cross
onto a course when the robot is unchanged (ADR-736). Give it
`--critic-warmup 10` (ADR-740). A course that touches only the feet
(`terrain={"collides_with": [feet group], ...}`, ADR-739) keeps MJX off
box–box and capsule–box pairs. What remains costs by the slot: on the cat (8 paw spheres, 8192 environments) an iteration takes about 14 s plus 2.5 s for each box slot, so keep a course to about 11 box slots, and a rock patch's stones count (ADR-747). Such a course also lets the body pass through a platform's wall. terrain-cat's warm start from the flat
turning policy (r1-t3) ran a full 12 s episode on the course by
iteration 50 (ADR-736).

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

### The reward curve is not the result (ADR-099)

The most important rule in this section, measured on the M9 run (its table
and story are in the history file, with hazard 19):

> Judge a checkpoint by what it *did* when you played it, never by the
> number the trainer printed. Install by survival, or by the spec: `cadex
> evaluate` exists for this.

Corollaries, each learned by nearly being caught:

* **Play a run against its own bundle, not the newest one.** A rebuild
  replaces `script_artifacts/`, so a finished run's task can vanish locally
  while its checkpoints sit beside you; `cadex train` exports the bundle
  into the run's own `--out`, the copy that survives.
* **`<out>.best.cxpolicy` is best-by-reward**, and early in a run it can be
  the untrained network standing still before the disturbances bite. Check
  its peak torque.
* **Give every episode its own model** (ADR-103 §9). `evaluate_episode`
  applies domain randomisation by multiplying in place into the model it is
  handed, so an evaluator that loops episodes over one model compounds every
  draw. Reload per episode, and play the same file twice to check the row is
  the same.
* **Read mean episode length beside the reward** (ADR-101): a reward
  climbing while episode length falls is hazard 19 in front of you.


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
