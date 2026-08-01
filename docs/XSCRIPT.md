# XSCRIPT.md — The Scripting Model

Verified against source: 2026-08-01

xscript is the single scripted modeling engine: the AI writes ONE
declarative Python project script; the script runs in a sandboxed headless
worker; only validated results reach the live document. The one-script
system below landed in Phase 2 (`docs/ROADMAP.md`, ADR-011..014) and
replaced the VibeCAD-era per-domain multi-program surface `[Cadex-new]`.

---

## Part I — One project script

### THE script and its store

- A project has exactly one script: `<project>/script.py`. It composes all
  five capability domains and is the sole source of truth — the user can
  open it, read it, and diff it; nothing model-shaped exists outside it.
  Assets the script names live under `<project>/assets/` (flat): mesh
  geometry `.stl`/`.obj`/`.ply` (ADR-043) and, on branch `MJC`, trained
  policies `.cxpolicy` (ADR-084). Nothing outside cadexd writes that
  directory: the `put_asset` op copies a file the user picked into it and
  returns the name the script may then reference, and
  `inspect scope="assets"` lists what is there.
- Sidecar state: `<project>/script.json` (schema `cadex-project-script-v1`,
  `CadexScriptStore.py:62`, class `CadexProjectScriptStore` — split out of
  `CadexProject.py` in C1) — cached `param_specs`,
  `param_values`, working/accepted revision, accepted contract (output
  names/types/domains), `accepted_digest`, latest candidate/failure.
  Writes are atomic; unknown fields are rejected.
- **The two parameter caches move together** (ADR-039). `param_specs` is what
  the script declares; `param_values` is what the sliders were last set to.
  Every accepted run prunes `param_values` to the declared names
  (`validate_project_result`), and `set_params` narrows the stored base to
  those names before merging its patch over them
  (`_project_param_values`). A parameter the script drops takes its value with
  it; a name in the *patch* that the script does not declare is still a loud
  `UNKNOWN_PROJECT_PARAMETER`. Pruning is digest-neutral — the worker resolves
  declared parameters by name and ignores the rest — so only the revision
  moves, and every revision the store keeps derives from the pruned dict.
  Before this, a rewritten script left dead values behind and every later
  `set_params` failed on a name the caller never sent, permanently.
- Execution artifacts live under `<project>/script_artifacts/<revision>/`.
- Revision = `project_script_revision` over `{schema, domain: "project",
  source, param_specs, param_values}` (`CadexScriptedDomains.py`) —
  content-addressed, key-order independent. Every mutation tool carries an
  `expected_revision` guard; a mismatch returns `STALE_PROGRAM_REVISION`
  with the observed current revision.

### Script vocabulary

The exec namespace carries the five domain APIs plus the parameter
vocabulary (`cadex_project_api.py`, `cadex_project_worker.py`):

```python
p = params(width=num(100, unit="mm", min=10, max=500, step=1, label="Width"))

profile = sketcher.sketch(...)           # sketcher API
plate   = part.box(p.width, 20, 5)       # part API
body    = partdesign.body(...)           # partdesign API (sketcher/part co-staged)
hull    = mesh.from_shape(plate)         # mesh API (tessellate/import/boolean/decimate)
base    = assembly.component(plate, grounded=True)
asm     = assembly.assembly([base, ...])

result = {"plate": plate, "hull": hull, "asm": asm}  # named outputs, by domain
```

- `params(...)` may be called at most once; `num(...)` declares one numeric
  control (`default`, optional `min`/`max`/`step`, `unit`/`label`/
  `description` — the `CONTROL_FIELDS` vocabulary). Collected specs are
  cached in `script.json`; **values** live there too and are patched by
  `set_params` without touching source.
- **`part.box`'s `origin` is a corner, not a centre.** `part.box(40, 40, 200)`
  occupies x ∈ [0, 40], y ∈ [0, 40], z ∈ [0, 200] — the origin is the
  minimum corner, and the solid is entirely on the positive side of the
  component frame. Centring it takes an explicit
  `origin=[-20, -20, -100]`. This is worth stating because of what reads
  the frame *afterwards*: `assembly.connector(...)`'s `offset` and
  `assembly.collision(...)`'s `offset` are both in the **component frame**,
  not in the solid's bounding box, and neither has any way to know where
  the solid was put. A corner-origin box with connector offsets written as
  if it were centred is a perfectly legal model that is half its own size
  out of position, and nothing refuses it. The measured instance is in
  ADR-087: a floor whose collision box stood 20 mm above the floor it was
  drawn on, through a whole training run.
- `assembly.component()` accepts same-script part/partdesign values: the
  worker records the source payload under a deterministic inline token
  (`document_uid: "xscript-project"`) and requires the value to ALSO be a
  declared output, so publication can bind each live component to a
  published stable object. Cross-document component references are retired;
  v0.0.1 assemblies are rigid, same-script solids (ADR-011).
- `mesh.from_shape()` tessellates a same-script part value (`Mod/MeshPart`);
  `mesh.import_file()` reads one flat asset file; `mesh.transform()` places
  one (same kwargs and same order of operations as `part.transform`, composed
  into a single matrix because `Mesh` has no `scale`); `mesh.union`/
  `difference`/`intersection` and `mesh.decimate` run on the native mesh
  kernel. Going the other way, `part.shape_from_mesh()` converts a mesh value
  into BREP topology (`makeShapeFromMesh`, then promoted to a solid unless
  `solid=False`) so an imported component can be cut against, assembled and
  padded around — see ADR-043 for what that costs. Every
  mesh output is rebuilt in canonical vertex/facet order (booleans
  immediately, all outputs before export), and the digest identifies a mesh
  by its exact sorted vertex set (`geometry_sha256`) — the native set
  operations return run-dependent orderings and occasionally re-triangulate
  coplanar regions differently for identical geometry. `decimate` is
  approximating (run-dependent result), so decimate trees are
  digest-identified by their canonical definition instead (ADR-016).
- `part.terminals()` / `mesh.terminals()` name the places a wire attaches to
  a component, from its geometry rather than from a measured constant
  (ADR-062) — see *Terminals* below. The result is not geometry: it
  publishes nothing and is subscripted by signal name to produce a port.
- `part.cable()` routes a wire instead of authoring one (ADR-056,
  **experimental**): given two ports — a terminal or a literal
  `(point, direction)` pair, interchangeably — and a `gauge_mm`,
  it searches a path clearing the `avoid` obstacles — `part` values and
  `mesh` values mixed — and sweeps a round conductor along it, one `solid`
  per wire. The route is recomputed every rebuild, so a cable follows the
  components it connects instead of going stale; waypoints must never be
  baked back into the script. Part obstacles are tessellated and rasterised
  into the search lattice; mesh obstacles are their bounding box, so a
  concave body belongs in `avoid` as the part solid it is, and the two
  components a cable lands on do not belong in its `avoid` at all.
- `part.bundle()` routes several wires along **one** path (ADR-057,
  **experimental**): given one `(start_port, end_port)` pair per conductor,
  it searches a single route at the bundle's outer diameter, lays the
  conductors about that shared centreline — `style="twisted"` helically, or
  `style="flat"` side by side — and sweeps the one named by `conductor`, so N
  conductors are N calls differing only in that index and cost one search
  between them. One `solid`, and therefore one model-tree row, per conductor:
  a compound would hydrate as a single row with no way to name a wire inside
  it. The order of `connections` is the order around the bundle, which is how
  the caller says which wire sits where. A twisted lay's radius is computed
  so no two conductors touch, which only has a solution when
  `twist_pitch_mm > len(connections) * gauge_mm`; a flat lay's `spacing_mm`
  defaults to `gauge_mm`, so its conductors are separate tangent solids with
  no web between them. `up` orients a ribbon where the run starts and is
  carried along it rather than re-levelled. Everything else — `avoid`,
  `clearance_mm`, `slack`, `cell_mm`, `min_bend_radius_mm` — means what it
  does on `part.cable` and applies to the bundle as a whole.
- `part.solder()` builds the joint that lands a wire on the component it
  connects to (ADR-063, **experimental**): given one terminal — never a
  literal port — and the `gauge_mm` of the lead, it fuses the filled bore
  barrel, the meniscus fillet and the far-face cap, and cuts the lead out of
  the lot. One call, one joint, one `solid`, sized entirely from the terminal
  so it moves when the terminal moves. See *Soldering a terminal* below.
- `assembly.dynamics()` runs the assembly as rigid-body dynamics instead of
  prescribing its motion (ADR-077, **experimental**): give every component an
  `assembly.body(component, density_kg_m3=...)` and the mechanism falls,
  swings and settles under gravity on MuJoCo. It produces the same
  `simulation` output type `assembly.simulation` does — a script has one
  simulation whichever solver ran it, and two would leave the shell baking
  neither. **Three things now produce one** — `assembly.simulation`
  (kinematics), `assembly.dynamics` (MuJoCo) and `assembly.rollout` (a
  trained policy, ADR-085) — and a script carries **exactly one of the
  three**, never two. Mixing `api.motion` with `api.dynamics` is refused.
  `density_kg_m3` has **no default**: mass, inertia and every fall time scale
  with it, and a guessed density makes the animation plausible and wrong
  (steel 7850, aluminium 2700, ABS 1040). Mass and the inertia tensor come
  from the component's own solids exactly, not from a bounding box, which is
  the part standard robot-model authoring gets wrong. Loops close as
  equality constraints and the published evidence records what each one gave
  up — a `connect` closing a revolute pins position and lets axis alignment
  go, which is exact for a planar four-bar and one constraint short for a
  spatial one. `gravity_m_s2` and `solver_step_s` are authorable (ADR-079);
  gravity is metres per second squared, and `[0, 0, 0]` is how you isolate a
  joint's behaviour from the falling.
  Refused rather than approximated: `distance`/`parallel`/
  `perpendicular`/`angle` joints (they constrain where the solver *put* a
  part, not how it moves), `rack_pinion`, slider and cylindrical loop
  closures, flexible subassemblies, and any component without a body.
- `assembly.mjcf()` exports that same model as a MuJoCo MJCF file instead of
  running it (ADR-081, **experimental**): the six parameters it shares with
  `assembly.dynamics` mean what they mean there and are validated by the same
  code, and what is absent is everything that counts a *trace* —
  `start_time_s`, `end_time_s`, `frames_per_second` — because nothing is
  integrated. One self-contained `.xml` per output, retained as a program
  artifact; collision meshes are written *into* it, so there is no sidecar
  and no asset directory. It carries the OCCT mass and inertia, which is the
  part everyone else botches, and a keyframe named `solved` — MuJoCo's own
  reference configuration is the one where each joint's connector frames
  coincide, so a file without that keyframe opens with the mechanism folded
  up, and anything reading one should reset to it. **Collision geometry
  only**, exactly as in a dynamics run, which means a mechanism with no
  `assembly.collision` shapes opens *invisible* in MuJoCo's viewer. Unlike
  `assembly.simulation` and `assembly.dynamics` a script may declare **more
  than one**: nothing bakes an exported model, so two of them — Earth gravity
  and lunar, say — is a reasonable script, and `assembly.mjcf` may sit beside
  `assembly.motion` as well as beside `assembly.dynamics`. The exporter
  reloads and verifies its own output before writing it, so an inertia that
  did not survive the file is a refusal rather than an artifact; MuJoCo's XML
  writer emits about six significant figures and has no precision setting, so
  the match is a stated tolerance and the published evidence reports how much
  of it this file used.
- `assembly.task()` turns one `assembly.mjcf` value into a **trainable
  reinforcement-learning task** (ADR-083, **experimental**) and writes one
  JSON bundle, `cadex-training-task-v1`, beside that model's file. It is the
  only output that consumes another output; a script may declare more than
  one, and two tasks may share one model, for the same reason two
  `assembly.mjcf` outputs are legal — nothing bakes either. The bundle
  references its model by relative path *and* sha256, so a pair that came
  apart is detectable rather than merely unlucky.
  The **observation space is declared on the model, not the task**:
  `assembly.mjcf(..., observations=[assembly.observation(target, kind,
  name=...)])` writes each channel into the exported file as a MuJoCo
  `<sensor>`, so **stock MuJoCo computes the observation vector** and no
  Cadex code is on the path between the mechanism and the array a trainer
  reads. The kinds are `position`/`velocity` on a joint,
  `component_position`/`component_orientation`/`component_linear_velocity`/
  `component_angular_velocity`/`centre_of_mass` on a component, and
  `actuator_force` on an actuator. Values reach a trainer in this API's own
  units — degrees, millimetres, N·mm — as a per-channel `scale` in the
  bundle, so the trainer *multiplies* rather than converting. A vector
  channel expands to suffixed scalar names — `name="hand"` on a
  `component_position` is `hand_x`, `hand_y`, `hand_z` — and those are the
  names a reward writes; two channels that would produce one name are
  refused, including when the collision comes from an expansion. One thing
  worth knowing before choosing a channel: a `component_position` reads the
  component's **frame origin**, so a link hinged at its own origin never
  moves in it — `centre_of_mass` is the channel for where a part actually
  is.
  `assembly.reward(expression, weight=...)` terms are summed and a policy
  maximises the total, reported term by term so "which part of the reward is
  doing the work" is answerable; a cost is a positive quantity with a
  negative weight. An expression may call `abs`, `asin`/`arcsin`, `arctan`,
  `cos`, `sin`, `exp`, `sqrt` and `tanh` — three more than `assembly.motion`,
  which does not get them because its formula is rendered back into an
  Ondsel expression. `assembly.termination(expression, above=...)` (or
  `below=`) ends an episode early, which is what distinguishes a failure
  from a horizon. `assembly.randomise(target, property, scale=[low, high])`
  varies `mass` on a component or `damping`/`armature`/`friction_loss` on a
  joint, once per episode; a mass draw scales the inertia tensor with it,
  because scaling one alone leaves a body whose rotational inertia no longer
  matches its mass.
  `assembly.reset_variation(component, tilt_degrees=..., height_mm=...,
  angular_velocity_dps=...)` starts each episode somewhere else and already
  moving, and `assembly.disturbance(component, newtons=..., direction=...,
  at_seconds=..., duration_s=...)` — or `sustained=True`, which is what wind
  is — pushes it while the episode runs. Both are drawn afresh **every
  episode**, unlike a randomisation, which a trainer holds per environment
  for a whole run. Without them a task never asks a posture a second
  question, and bracing beats balancing (ADR-097). A reset variation moves
  the mechanism's floating base **rigidly** and never its joint angles: the
  reset pose is the solved one with the soles on the floor, so a few degrees
  at a knee is a foot through it, and the engine measures whether the
  declared tilt clears at the declared lift and refuses the pairing that
  does not.
  **Action ranges are derived from the mechanism or refused, never
  defaulted.** A `motor` is bounded by its `torque_limit_nmm`/`force_limit_n`
  and a `position` servo by its joint's own limits with *both* endpoints
  declared. A `velocity` actuator has no derivable range at all — a joint
  states position limits and never a speed — and a one-sided limit is
  likewise refused, because its missing endpoint is filled in with a margin
  worth a hundred turns to keep the solver treating the joint as free, which
  is a convenience rather than a bound anybody designed. Each actuator keeps
  the control formula it already required; that becomes its deterministic
  action when no policy is driving, which is what lets the engine run and
  verify one episode from the bundle before publishing it.
- `assembly.policy()` and `assembly.rollout()` close the arc that
  `assembly.task` opens (ADR-084, ADR-085, **experimental**).
  `assembly.policy(task, weights="walk.cxpolicy", sha256="<64 hex>")`
  declares a **trained control policy** for one task. Training does not run
  in the engine and cannot — it needs JAX on a GPU — so
  `training/cadex_train.py` runs on a machine that has one and the `.cxpolicy` it
  writes comes back through `put_asset` like any other asset. There is **no
  train button and nothing to press**. `sha256` is required and never
  inferred: a trained policy is the one part of a project that cannot be
  rebuilt from the script (VISION principle 3), so the script carries which
  bytes it meant and the engine refuses anything else, naming the digest it
  observed. Before publishing a receipt the engine checks the policy against
  the task it claims — the bundle's digest, the model that bundle
  references, the observation channels in order, the action table, the
  output map the task's action ranges imply — and re-evaluates the
  **witness** the trainer recorded with its own forward pass, so a policy
  whose weights arrived intact but whose network the engine reads
  differently is a refusal rather than a bad gait. A script may declare more
  than one; nothing bakes a policy.
  `assembly.rollout(policy, frames_per_second=..., seed=...)` **plays** one,
  and this is the one that reaches the viewport. It produces the same
  `simulation` output `assembly.simulation` and `assembly.dynamics` produce,
  so a script has exactly one of the three, a rollout cannot sit beside
  `assembly.motion`, and the shell bakes it with code that never learned a
  third kind of producer exists. The policy it names must also be **returned
  as an output**, because an unpublished policy is one the engine never
  verified. The model is reloaded from the file the task bundle names rather
  than reused from memory — measured, those are not the same trajectory
  after a hundred closed-loop steps — so a rollout runs the exact model the
  policy's digest attests to. `frames_per_second` must **divide the task's
  `control_hz` exactly** and defaults to it: an action is held for a whole
  control step, so a frame between two of them would make the trace depend
  on floating-point accumulation, and the refusal names the rates that task
  can be played at. `seed` draws the task's `assembly.randomise` entries for
  that one episode.
- `assembly.collision(kind, ...)` says what a body may touch things with
  (ADR-079, **experimental**), and a body given none touches nothing — it is
  carried by its joints and passes through the rest of the mechanism, which
  is what every dynamics run did before M3. Four primitives — `box`,
  `sphere`, `cylinder`, `capsule` — placed with `offset` in the component's
  own frame, plus `mesh` for the component's own tessellated solids. Prefer
  the primitives: **MuJoCo takes the convex hull of any collision mesh and
  does not say so**, so a bracket with a slot silently becomes a solid
  block. `mesh` therefore measures its own convexity against its hull and
  refuses a part the hull would change, naming the volume error; `hull` is
  the same geometry with that refusal turned off, which is how a script says
  in its own text that the hull was read and accepted. A mesh too coarse to
  be the part is refused separately, and that refusal is not waived by
  `hull`. Contact takes `friction`, `condim`, `margin_mm`, `restitution` and
  a `contact_group`/`collides_with` pair. Restitution is 0 or between 0.3
  and 0.9 — MuJoCo has no restitution coefficient, bounce comes out of the
  contact spring's damping, and outside that band the translation is not
  honest — and above 0 it needs a `solver_step_s` of 0.001 or finer, which
  is refused rather than silently under-delivered. Components that a joint
  connects never collide with each other: they overlap at the joint by
  construction.
- Outputs are evaluated per domain in fixed order sketcher → part →
  partdesign → mesh → assembly, reusing the per-domain evaluators and
  serializers.

### Naming geometry: selectors, not indices `[Phase 10b, ADR-029]`

Five part ops — `subshape`, `defeature`, `fillet`, `chamfer`, `thicken` —
choose subshapes of a shape. They take a **geometric selector**, never an
ordinal:

```python
drilled = part.cut(part.box(40, 30, 10), holes)

rounded = part.fillet(drilled, 0.5,
    edges={"geometry_type": "Circle", "radius": 3.0, "expected_count": 8})
healed  = part.defeature(drilled,
    {"geometry_type": "Cylinder", "radius": 3.0, "expected_count": 4})
top     = part.subshape(drilled, "face", {"normal": [0, 0, 1]})
cup     = part.thicken(part.box(20, 20, 10),
    {"normal": [0, 0, 1], "expected_count": 1}, -1.5)
```

`fillet` and `chamfer` also accept `edges="all"`. Everything else must be a
selector; `subshape` fixes `expected_count` to 1.

**Why the index form is gone.** It named a position in the kernel's
`TopExp::MapShapes` enumeration. ADR-028 proved that ordering is
*reproducible*; it is not *stable across edits*. Any parameter change that
alters topology renumbers every subshape after it, so a saved `edges=[3, 7]`
keeps validating and silently starts filleting different edges. A selector
either keeps meaning the same thing or fails loudly.

Selector keys (the closed set — an unrecognised key is rejected rather than
ignored, because a typo would otherwise widen the match):

| key | matches |
|---|---|
| `expected_count` | **required** — the declared cardinality; a mismatch fails |
| `geometry_type` | `Plane`, `Cylinder`, `Sphere`, `Toroid`, `Line`, `Circle`, … |
| `normal` / `direction` | face normal / edge tangent, within `normal_tolerance_degrees` / `direction_tolerance_degrees` (default 1.0) |
| `radius` | circular edges **and** cylindrical/spherical faces, within `radius_tolerance` (default 1e-6) |
| `min_area` / `max_area` / `min_length` / `max_length` | size bands |
| `near_point` | centre of mass within `max_distance` (default 1e-6) |

This is the same vocabulary `resolve_pin` speaks, so a pin captured from a
click and an argument written into the script name geometry identically
(`CadexSubshapeQuery.py`). When a selector fails, the envelope carries
`expected_count`, `actual_count` and the full `available` list, so the next
attempt is a re-query rather than a guess.

### Terminals: ports that name geometry `[ADR-062]`

`part.cable` and `part.bundle` (ADR-056, ADR-057) route a wire between two
ports. A port used to be a literal `(point, direction)` pair, which is wrong
by construction for a through-hole, goes stale the moment a slider moves the
component it was measured off, and does not say which signal it is. A
**terminal** is a port derived from geometry and looked up by name:

```python
fc  = part.terminals(board,
                     holes={"geometry_type": "Cylinder", "radius": 0.5},
                     exit=(0, 0, 1), order_by=(1, 0, 0),
                     names=["vbat", "gnd", "tx", "rx", "sda", "scl"])
esp = mesh.terminals(esp_placed,
                     header=dict(origin=(-11.3, -4.0, 3.8), along=(0, 1, 0),
                                 axis=(-1, 0, 0), pitch=2.54, count=4,
                                 hole_dia=1.0, depth=1.6),
                     names=["vcc", "gnd", "sda", "scl"])

result["i2c_sda"] = part.cable(esp["sda"], fc["sda"], gauge_mm=0.4,
                               avoid=[frame])
```

**A terminal is not geometry.** It has no output type, publishes nothing,
and cannot be returned as an output — it exists to be subscripted by name
and handed to `cable`/`bundle`, which serialise it into their own arguments.
Literal pairs still work everywhere and are unchanged, so a script that uses
no terminals rebuilds byte-identically.

Two ways to state a set:

| form | where | resolves to |
|---|---|---|
| `holes=` selector | `part.terminals` | the axis point on the face **opposite** `exit`, leaving along `exit`; stand-off floors at the bore depth |
| `pads=` selector | `part.terminals` | the face's `CenterOfMass`, leaving along its normal (agreeing with `exit` if given) |
| `header=` / `terminals=` declared | both | `origin + along*pitch*k + axis*depth`, leaving along `-axis`; `depth=0` is a pad |

`holes=` **requires** `exit`: a cylindrical face states an axis but not which
end is outward. A hole lands on the *far* face on purpose — the wire comes in
from the `exit` side, threads the barrel and stops flush on the other one, so
two holes wired together meet in true centres rather than each stopping a
board thickness short. A declared row says the same thing the other way
round: `axis` is the drilling direction, the terminal is
`origin + axis*depth`, and the wire leaves along `-axis`.

`order_by` is a **direction**, and it is what matches `names` to matched
faces: they are projected onto it and taken in ascending order. It is never
the kernel's enumeration order, for the reason above this section. `len(names)`
*is* the selector's `expected_count`.

`mesh.terminals` is declared-only — a triangle mesh has no `Cylinder` face to
select — and its coordinates are the **asset's own**, before any
`mesh.transform`. That is what makes define-once/place-many work: one header
from the datasheet, four placed motors, four correct sets. Non-uniform scale
on the chain is refused rather than silently skewing an axis. On a *part*
value the declared form is a fallback and the selector form is recommended:
a part value is built in final coordinates, so declared numbers there are
world coordinates and go stale exactly like the literals they replace.

#### Soldering a terminal `[ADR-063, ADR-064]`

`part.solder(terminal, gauge_mm=...)` builds the joint that lands the wire —
one call, one joint, one `solid`:

```python
result["sda"]       = part.cable(esp["sda"], fc["sda"], gauge_mm=0.4)
result["sda_joint"] = part.solder(fc["sda"], gauge_mm=0.4)
```

On a **through-hole** that is the barrel of the plating filled around the
lead, a meniscus fillet where the lead leaves the board, and a cap over the
lead's end on the far face. On a **pad** it is the meniscus alone. Every
dimension is sized from the terminal, so the joint moves when the terminal
does.

The meniscus is **concave**: it sweeps up off the pad, flattens as it reaches
the lead, and then runs parallel to the wire for a short collar standing a
tenth of the lead's radius clear of it. That is what stops a joint reading as
a cone on a render. The whole joint is one solid of revolution — one closed
outline, one `revolve`, no booleans (ADR-064).

It is the one operation that takes a terminal and **never** a literal port: a
joint is built from the bore's radius and depth and the two faces it runs
between, and a literal `(point, direction)` pair carries none of them. This
is the first thing a terminal *unlocks* rather than merely improves.

`gauge_mm` is required — the same number the `cable`/`bundle` landing there
was given. `bore_dia_mm` defaults to the hole's measured diameter,
`pad_dia_mm` to twice that (or, for a `pads=` selector, to the matched face's
equivalent-area diameter), and `fillet_mm` to the width of pad the meniscus
sweeps across — which makes the arc an exact quarter round, tangent to the
board where it lands and to the lead where it arrives. That default is also
the **floor**: a shorter fillet spreads further than it climbs, so it would
undercut the board, and it is refused with the floor named. **A declared
layout has no measurements to fall back on**: a declared hole without
`hole_dia` needs `bore_dia_mm`, and a declared pad — which carries no area at
all — needs `pad_dia_mm`. Everything is refused by naming the value it
measured and the one it conflicts with.

### Declaring a harness: `nets()` and `wire()` `[ADR-065]`

Terminals name the ends of a wire; `nets()` names the wire. It is to a
connection exactly what `params()` is to a slider — **a declaration in the
script whose current values live outside it**:

```python
n = nets(
    ports={"sen": sen_t, "esp": esp_t, "fc": fc_t},   # named TerminalSets
    wires={                                           # named rows
        "s0_e0": wire("sen.s0", "esp.e0", gauge=WG, solder=True,
                      avoid=[sensor_board, esp32_board]),
    },
)

for name, w in n.items():
    if not w.enabled:
        continue
    result["wire_" + name] = part.cable(w.a, w.b, gauge_mm=w.gauge,
                                        avoid=w.avoid)
    if w.solder:
        result["joint_" + name] = part.solder(w.a, gauge_mm=w.gauge)
```

`w.a` and `w.b` are real `Terminal` objects, so `part.cable`, `part.bundle`
and `part.solder` are untouched and a script converted from a comprehension
over literal pairs builds byte-identically. `n.enabled()` is the loop above
without the `continue`.

An endpoint is **`"<port>.<terminal>"`**, validated at declaration against the
actual `TerminalSet`s — a typo is a refusal, not a silent miswire. Port names
are lower_snake_case and carry no dot, so the split is on the first dot and a
terminal name may contain more.

**The table carries exactly what the wiring editor can edit.**

| column | overridable | lives where |
|---|---|---|
| `a`, `b`, `gauge`, `solder`, `enabled` | **yes** | `net_values` in `script.json` |
| `avoid`, `label` | no | the script |
| every routing argument (`clearance_mm`, `slack`, `cell_mm`, `style`, `twist_pitch_mm`, `pad_dia_mm`, …) | no | the script |

Refusals mirror `params()`: `nets()` at most once per script, at most
`MAX_NETS` (256) rows, lower_snake_case names on both halves, an endpoint
naming a port or terminal that does not exist, and both ends the same.

`part.bundle` is deliberately **not** a table concept. Changing a bundle's
membership changes the conductor count, the lay radius and every other
conductor's position; that is a script edit. Bundles draw in the editor and
stay read-only.

### The wiring path `[ADR-065]`

The peer of *The slider path* below, through the same op. `script.json`
carries `net_specs` (the declaration the worker collected) beside
`net_values` (the stored rows), exactly as it carries `param_specs` beside
`param_values`, and `set_params` takes an optional `nets` argument alongside
`values`. A nets-only edit sends `values: {}`.

Two properties are worth stating because they are not the parameter path's:

- **`nets` is a full row list, not a patch.** That is what lets the editor
  add and delete wires. An empty list means "no overrides", never "no
  wires" — deleting the last wire is expressed by disabling it.
- **Strict on the request, lenient on the store.** A request naming an
  endpoint the declared ports do not have is refused with
  `UNKNOWN_PROJECT_NET_ENDPOINT`. A *stored* row a rewritten script no longer
  supports is dropped rather than raised on, in `validate_project_result` —
  ADR-039's rule, for ADR-039's reason: raising would wedge the editor
  forever the moment the AI renamed a port.

`net_specs`/`net_values` join `project_script_revision` **only when
non-empty**, so every project written before ADR-065 keeps a byte-identical
revision and nothing needs re-accepting.

`inspect scope="wiring"` is the read side: every terminal the accepted run
resolved — name, point, direction, kind, bore radius, depth — joined to its
port and its output, plus the connection table over them. The terminals come
from the worker's own resolution, published into the attempt's `result.json`,
because a `holes=` selector needs the built shape and the live process never
runs user code. A script written before `nets()` gets the same graph
reconstructed from the `cable`/`bundle`/`solder` calls it made, marked
`"source": "derived"` and `"editable": false`.

### Lifecycle tools

The tool surface the AI sees is exactly four operations
(`PROJECT_LIFECYCLE_OPERATIONS` in `CadexScriptedDomains.py`, pinned by
`cadex_tests/test_project_tool_surface.py`; ADR-013). They reach the engine
as cadexd ops of the same name (`docs/INTEGRATION.md`), served to Claude
Code over MCP by the shell:

```
xscript.project.describe_api   composed API description for all domains
xscript.project.write_script   whole-script rewrite
xscript.project.edit_script    unique-match find/replace; whole source re-validated
xscript.project.set_params     values-only patch; re-run without touching source
```

The dissolved per-domain operations (`create_program`, `edit_source`,
`set_inputs`, `set_parameter_controls`, `reconfigure_program`,
`delete_program`, `inspect_program`) stay gone — the guardrail test
asserts no registered tool may carry them again. Reads go through the
bounded **`core.inspect`** tool (`CadexInspection.py`; scopes `document`,
`object`, `script`, `api`, `image`, `output`, `assets`, `history` — `script`
pages the source and reports specs/values, revisions, accepted contract +
digest, and the latest candidate; `output` serves any accepted output's
measured facts from the pinned accepted attempt, so they are readable long
after the rebuild that produced them; `assets` lists what a script can name
by filename; the first two added in ADR-043, and `history` in ADR-045 — the
accepted-revision undo trail that `restore_version` reads before writing the
result back through `write_script`). There was one more scope, `selection`; it read the
Qt shell's selection and died with it (ADR-021), and the engine rejects it.

### Sandbox rules

Source is validated before any worker runs (AST policy in
`CadexScriptedRuntime.py` / `CadexScriptedDomains.py`):

- Blocked names include `__import__`, `eval`, `exec`, `compile`,
  `breakpoint`, `globals`, `help`, … (`_BLOCKED_NAMES`); no dunder access;
  size and syntax limits; NUL bytes and unsafe project-relative paths
  rejected.
- Violations return `SOURCE_POLICY_VIOLATION` with offending line numbers —
  structured failure payloads, not exceptions.

### Worker isolation

- One attempt = one windowless `FreeCADCmd --safe-mode -c …` subprocess
  (runner in `CadexScriptedProcess.py`). The project bundle stages all five
  `cadex_<domain>_{api,worker}.py` modules with entry
  `cadex_project_worker.py` — **and six more modules by filename**:
  `CadexSubshapeQuery.py`, `CadexRouting.py`, `CadexBundle.py`,
  `CadexDynamics.py`, `cadex_tessellation.py` and `cadex_preview_worker.py`
  (`_DOMAIN_WORKER_BUNDLES["project"]`, `CadexScriptedRuntime.py:38`). Copied
  in rather than imported, so a worker module can `import` them inside the
  sandbox while `cadexd`'s own module closure never reaches them — which for
  `CadexDynamics.py` is a test-pinned invariant rather than a convenience.
  Plus the project's flat `assets/` directory (bounded: 64 files / 128 MB,
  known suffixes only).
- Hard bounds from preferences (`ScriptedTimeoutSeconds`,
  `ScriptedMemoryLimitMB`); a parent-side watchdog kills over-budget
  workers and reports `MEMORY_LIMIT_EXCEEDED` with observed usage.
- The worker executes the script ONCE, evaluates outputs per domain, and
  produces **detached** results (BREP and mesh artifacts, records, collected
  `param_specs`, per-output validations, the content digest) on the
  `cadex-xscript-project-worker-v1` wire schema; it never touches the live
  document.

### Publication, ownership, lint, GC

Since Phase 5 (ADR-017/018) publication runs inside **cadexd's ephemeral
document** (and the headless rebuild driver); the shell receives the
accepted artifacts as a `display` block and draws them however it likes
(the Blender shell hydrates tessellation + ID maps into its scene).
`publish_project_candidate` (`CadexScriptedDomainPublication.py`) applies
one validated candidate under **ONE** document transaction — one undo step:

- Per-domain sub-publishes run through the existing domain publishers with
  `manage_transaction=False` (the project publisher owns the transaction
  and runs the document-revision guard once, before opening it).
- Inline assembly source tokens are rewritten to the live object names
  published earlier in the same pass.
- Published objects are tagged
  `CadexXScriptProgramId/Domain/Workbench/Revision/OutputName`; ownership
  is recoverable from the document alone (`CadexScriptedOwnership.py`,
  closure over Group+OutList).
- **Lint**: any document object outside the owned closure aborts the
  transaction with `PUBLICATION_UNTAGGED_OBJECT` (ADR-012).
- **GC**: owned objects whose outputs left the accepted contract are
  deleted in the same transaction and recorded in the result.
- Output identity is durable: an output keeps its object across edits when
  unchanged; removed outputs' identities are never recycled.

### Digest and headless rebuild

- **Content digest** (D8): SHA-256 over the name-sorted output entries
  `{output_name, domain, output_type,
  shape_sha256|mesh_sha256|payload_sha256 [+ artifact_sha256],
  placement (rounded 1e-9)}`, schema `cadex-project-digest-v1`, computed
  worker-side from serialized artifacts; recorded as `accepted_digest` on
  accept. A BREP output is its exported shape and a mesh output its vertex
  set — for those two the bytes *are* the output. Everything else is its
  canonical definition, **plus `artifact_sha256` when it retained a file**
  (ADR-068): the clause is keyed on having an artifact rather than on a list
  of known kinds, so a new output kind joins the digest by writing a file.
  `mesh` is the one exclusion, because a decimate tree's bytes are
  run-dependent by construction where its recipe is not. `CadexDigest.py:document_digest` recomputes a diagnostic digest
  from the live tagged objects (schema `cadex-document-digest-v1`; a
  different quantity — do not compare across schemas).
- **Headless rebuild** (D9): `cadex_rebuild.py` re-runs THE script into a
  fresh document under FreeCADCmd and compares digests
  (`pixi run rebuild <project_root>`; exit 0 match / 2 mismatch / 1
  failure).
- **CI** (Phase 2 exit criterion): `cadex_tests/test_project_rebuild.py`
  (ctest `CadexProjectRebuildDigest`) seeds a multi-domain project, accepts
  it, deletes the document, rebuilds twice, and asserts
  rebuild-vs-accepted AND rebuild-vs-rebuild digest equality.

### The slider path

The engine's half is `set_params`: a values-only patch, guarded by the
working revision, that re-runs the script without touching source. It is the
same lifecycle the assistant drives — there is no faster private path, and
no AI turn.

The shell's half is `scene.mesh_params`, a PropertyGroup registered from the
engine's `param_specs` (`cadex_backend._bridge_params`). A drag debounces
150 ms (`model._schedule_rebuild`), sends one `set_params` with a `draft`
tessellation preset, and schedules a background `standard` refine at rest.
A failed rebuild leaves the accepted geometry untouched — and says so in the
parameters panel, with a **Rebuild Model** button beside it (`rebuild_model`,
the `rebuild` op re-run over the stored script; ADR-039). The debounce timer
runs outside any operator, so before that a failed drag reached the console
and nowhere else.

The sliders are an override layer, and the shell can collapse it: **Apply as
Defaults** rewrites each `num()` default in the script to the value its slider
is sitting at (ADR-040). That is a `write_script` like any other — the shell
splices the source and sends it whole — so the script stays the single source of
truth rather than gaining a second place where a value can live. The stored
values are left in place, and go on shadowing the defaults they were written
from, so the operation does not move the geometry or its digest.

*(ADR-014's `CadexParametersPanel.py` implemented this in the Qt shell and
was deleted with it in Phase 7, ADR-021. The contract it committed
through — `set_params` plus the revision guard — is unchanged, which is why
the shell swap did not touch the engine.)*

**In front of that path, for the sliders that drive motion**, sits
`preview_params` (ADR-055). A resident `--safe-mode` worker inside cadexd
answers a **pose-only** parameter change — one where every non-assembly
output's canonical definition is byte-identical and only placements moved —
with solved component matrices and nothing else: no BREP, no tessellation, no
digest, no publication, **no store write**. Measured at **33 ms** against the
same model's 0.59 s accepting run.

It is a fast path for *some* sliders, not all, and that is structural rather
than an unfinished edge. A parameter feeding `part.box(p.width, …)` changes
that box's definition, so it is never pose-only — correctly, because the
geometry really did change. What a preview serves is exactly the class the
`set_params` lifecycle is worst at and the user notices most: a component
placement, a joint offset, a motion formula. Everything else falls back to
the debounced `set_params` above, which remains the only thing that makes a
change real: the preview never accepts, so the revision it was guarded by is
still the revision when it is done.

### Reference pins

`CadexReferenceContracts.py`: a click in the viewport becomes `@face-2` on
the next chat message. A pin carries the shared handle, owning object,
subelement hint, and a **geometric fingerprint** (center of mass,
direction/normal/radius/length). The fingerprint is authoritative: when the
revision has moved since capture, the pin is re-resolved by fingerprint
search rather than trusting the stored subelement name — so pins survive
rebuilds that churn object names.

Pins are the *chat* vocabulary. Scripts do not use them: since ADR-029 a
script argument names geometry with a **selector** (above), resolved through
the same `CadexSubshapeQuery.py` vocabulary. Click and script therefore mean
the same thing by "that face" — but only the selector is durable in a saved
script, which is the point of the split. Nothing in the shell yet *writes* a
selector into a script from a click; that round trip is half built
(`docs/ROADMAP.md` Phase 10b).

**A pin is not a terminal.** The two words mean different things here and
must not be swapped. A *pin* is this: a click-captured geometry reference,
in chat (`CadexPinResolution.py`, `resolve_pin`, `pick_pin`). A *terminal*
is an electrical attachment point on a component, named in a script and
resolved from geometry (ADR-062, above). `resolve_pin`'s answer —
`center_mm` plus `normal` — happens to be exactly the shape of a literal
port, which is how a picked pad can be pasted into a `part.cable` call; that
is a coincidence of shape, not the same concept.

---

## Part II — Direction

- **Incremental re-execution**: today every mutation re-runs the whole
  script (one worker attempt). Cached per-region revisions keyed by content
  hash are a possible optimization; the revision machinery points the way.
- **Sub-modules**: whether large projects split into importable sub-modules
  under the project root, or stay one flat script.
- **Interactive mesh editing**: still unscheduled, and still a decision
  rather than an oversight. The plan used to be that it would arrive via
  BMesh in the Blender shell. It has not, and the route narrowed rather than
  widened: ADR-030 deleted the local bpy modes, which were the only code in
  the shell that authored geometry with BMesh. Editing a mesh interactively
  would now mean either a new engine op or re-opening a second authoring
  path — and the second is a direct contradiction of "nothing happens
  outside the script".

  What this paragraph used to also say — that the `mesh` domain is
  deliberately minimal and *stays* that way — is **superseded by ADR-043**.
  The charter it stated was a *modelling* one, and it held; what it
  incidentally froze was the *ingest* path, which was not a decision anyone
  made. External geometry is now a first-class input: `put_asset` gets a
  file into the store, `mesh.transform` places it, `part.shape_from_mesh`
  takes it into the BREP domains, and `inspect scope="output"` measures the
  result. None of that is interactive mesh editing, and the "nothing happens
  outside the script" rule is untouched — the script still names every
  operation; the asset store is an input to it, the way a parameter value
  is.

---

## Historical note

The VibeCAD-era per-domain multi-program surface (eight lifecycle
operations × four domains, program manifests `cadex-xscript-program-v2`)
was dissolved by the Phase 2.4 tool-surface swap (ADR-013); existing v2
program stores were not migrated (ADR-011 — conversations preserved,
scripts start empty). The verification record for the still-earlier
multi-engine runtime is preserved at
`docs/history/RUNTIME_VERIFICATION.md`. Still-current facts — structured
failure envelopes, transactional parity, resource budgets, revision
integrity — are enforced by `src/Mod/cadex/cadex_tests/`.
