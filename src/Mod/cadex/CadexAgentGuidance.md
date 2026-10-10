<!--
SPDX-FileCopyrightText: 2026 Cadex Authors
SPDX-License-Identifier: LGPL-2.1-or-later

The agent guidance Cadex hands any agent that drives it (ADR-446, ADR-538):
the design loop, proof by measured facts, the build reply's blocks as
floors, what a self-moving machine carries, what a policy may read, how a
learned motion is paid, and honesty about what is unfinished. It is the
base: it holds for a printer, a tractor, a lab robot or a creature alike,
and names no kind of machine as the default (ADR-560, ADR-650). A look or a
convention that holds for one family of machines only is a named, optional
style, one CadexAgentStyle.<name>.md beside this file, which a project
chooses. The base states principles with their reasons and a check the
agent can run, not fixed taste rules (ADR-651). It is engine data, shipped
in the payload beside CadexStudio.py. It is not code: the CLI reads it from
the engine it resolved.

Everything below the marker line is the guidance, verbatim, except a line
that is wholly an HTML comment, which the client drops: such a line marks a
placeholder paragraph that parallel work replaces (ADR-654). Tool names are
placeholders: {{look}}, {{inspect}}, {{write_script}}, {{edit_script}},
{{set_params}}, {{rebuild}}. The client today is the CLI's guidance.py,
which fills them with the `cadex mcp` tool names and prints the result
inside `cadex guidance`; a placeholder a client does not fill is an error in
that client, never text the model reads.
-->
<!-- guidance -->
YOU SEE YOUR WORK WITH `{{look}}`, AND YOU PROVE IT WITH FACTS. `{{look}}` renders the last accepted revision, each part in the appearance role you declared (`assembly.component(..., appearance="shell"|"mechanism"|"accent")`, colours from `assembly.assembly(..., palette=...)`), with `focus=[names]` for a close-up. The numbers say whether a design fits; only a look says whether it is designed. Do both. `{{inspect}} scope=output` gives each output's volume, bounding box and face counts: compare them with what you intended, because an accepted shape exists but is not necessarily the one you meant. A SOLID BUILT FROM TANGENT PRIMITIVES IS MEASURED: a fuse of cylinders and spheres that only touch along a line or a point can come back with pieces missing, so check its volume, and prefer one body with filleted edges.

FIT IS MEASURED, NOT PRINTED. Every build reply ({{write_script}}, {{edit_script}}, {{set_params}}, {{rebuild}}) carries blocks the engine measured on the exact solids of the accepted revision, and each says in its own `source` and `note` what it measured and what it did not. They are the evidence; a script's `print(...)` is only a claim, and a block that disagrees with it wins. Never report a design as fitting, held, swept or complete while a block says otherwise: change the geometry and build again. `unavailable` or `incomplete` has checked nothing, and is never a pass.
- `fit`: every component pair at the solved pose, failing pairs worst first, with minimum distance (mm) and common volume (mm³); `{{inspect}} scope=clearance` lists them all. Declare intent only where the design means it -- `clearances=[(a, b, 0.05)]` for a running gap under the 0.1 mm default, `contacts=[(a, b)]` for parts meant to touch -- never to silence a pair you have not thought about. A pair welded by a `fixed` joint is exempt from the gap; `fit.attachments` says whether its two sides meet, and a weld across a gap nothing spans is a connection the design does not make.
- `fit.sweep`: every limited joint driven through its range, once the assembly declares `sweep_step_degrees` and `sweep_step_mm`. An unswept joint was checked at one pose only. A closed loop is swept from its limited joints and re-closed at each sample; a pose it cannot close is a real limit of the linkage. When a joint runs out of time, rebuild rather than coarsen the step.
- `fit.mounting`: what holds each purchased part -- screws in its own holes that thread into something, a bay cut with its `.bay()`, a press fit, a drive's output -- or that nothing does. Contact, or sitting inside a cover, holds nothing.
- `inventory`: which placed components are catalog parts as built. A purchased part under `uncatalogued_sources` lost its identity when you cut it: place the untouched catalog body and cut the made part that receives it.
- Other blocks -- the moving regions, the shell check, any the engine adds -- work the same way: read the `note` first.
A MET CHECK IS A FLOOR, NOT THE GOAL. A rectangle bolted to a rectangle passes every block.

SET A LIMIT FROM THE SWEEP. Where two moving parts meet inside a joint's range, move them apart or limit the joint short of where they meet -- asymmetric where the geometry is -- and set the spacing and the limit together from the sweep's rows (`{{inspect}} scope=clearance path=/clearance_sweep/joints`), never from a guess. When a part grows beside its neighbour, the gap is gone: sweep again.

DESIGN IT; DO NOT ONLY MAKE IT FIT. Form follows function: every part takes its shape from what it does -- the load it carries, the part it holds, the motion it allows, how it is made -- and nothing is added to imitate engineering. The bar is a real product, the machine a company would ship, not a model of one. Work from the inside out, in this order:

1. CONCEPT FIRST, BEFORE ANY GEOMETRY. Before your first {{write_script}}, say in a few lines what the machine does, its scale and loads, how its parts are made, its proportions and palette, each with its reason, and record it in the project's DECISIONS.md. Say how real machines of this kind are built -- layout, structure, conventions -- which you follow, and where you depart and why.

2. PARTS FIRST. Choose every purchased part before you shape anything: an actuator per axis, controller, drivers, power, sensors, fasteners, and the bearings, wheels or guides the motion runs on (`describe_api section=library`). SIZE EACH ACTUATOR FROM ITS AXIS'S LOAD -- the mass it moves times its lever, or the force its travel needs, with margin -- and write the sum in docs/actuators.md; never give a light axis the heavy part because the rest of the machine uses it. Decide the cable path.

3. PLACE THEM as components, before any made part exists: heavy parts where they steady the machine, drivers where cables are short, sensors where they see what they measure, actuators at their axes, sides mirrored. Build and read `fit` with the parts alone, while a clash is cheap to move.

4. STRUCTURE THAT CARRIES THEM -- a frame, chassis, column, hull or deck, then the moving members -- around the parts where you placed them:
- HOLD EVERY PART by something you can name, checked in `fit.mounting`: a `lib.bolt` component on each hole's axis, at the part's `spec["mount_thread"]` where its holes are tapped, threading into a hole cut at `lib.tap_drill(size)` in solid material; a pocket cut with the part's own `.bay()`, which leaves room for clearance and leads; a board or drive screwed down with its `.mounting()`; a member grown around the actuator it carries (`lib.housing`). `describe_api section=library_parts` has the helpers.
- NOTHING STUCK ON. A boss, rib, tab or pad is fused and blended into its solid, and nothing hangs off the machine without a structural reason.
- MIRROR WHAT HAS SIDES with `mirror`, so handed parts come out handed.
- MEMBERS FOLLOW THE LOAD: deep where the bending moment is large, lighter where it falls, shelled or ribbed where the process allows. Check it: name each member's load and where it peaks, and see that the section does too. Whatever meets the ground or the work is a designed part, never the cut end of a bar.
- A MADE PART IS MAKEABLE by its process, or it is not a design. For FDM printing: a flat face to print on, no unsupported overhang past about 45 degrees, walls of at least about 1.6 mm (four 0.4 mm perimeters), holes sized to their fastener. Sheet, extrusion, casting and machining have their own limits: name the process in the concept.

5. FINISH, each part its own component with an appearance role:
- HARDWARE THAT SHOWS IS ORDERED: square to the frame, lined up, fastened with screws you can see, cables on a deliberate path.
- DETAIL IS REAL: a seam where parts separate, a fastener that fastens, a hatch, a vent that moves air. No greebles, fake vents or stripes.
- FINISHED EDGES: a fillet or chamfer sized to the part and its process on every outside edge, and inside corners filleted where load turns them; `{{look}}`'s measures report the share left sharp. One large radius over a whole body hides its structure.
- COLOUR FOLLOWS ROLE, not supplier: `shell` for made structure and covers, `mechanism` for hardware, `accent` for a few features that do something. A colour change is a part boundary, never paint.

6. REFINE WITH `{{look}}`. After the first accepted build, look at `hero`, `iso`, `iso_back` and `right` (from +X), then `focus` on one repeated subassembly. Read the `measures`, then the pictures. Name in one line each what reads as crude -- a sharp edge, a part stuck on or held by nothing, a disordered cable, a member thinner than its load, a skin hiding the structure, a feature no real machine of this kind would have -- fix the worst, and look again. Stop when every block is clear or answered with a recorded reason, and it reads as the machine of step 1.

<!-- placeholder: panels. Replace this paragraph when the panel system lands. -->
COVERS AND PANELS. A cover is there for a reason you can name -- guarding a moving part, keeping out dust, heat or a hand, giving a surface to touch -- and takes its shape from what it covers: close to it, thin, split where it is assembled or opened, screwed to the structure, and clear of every moving part through its range. Declare it `appearance="shell"`, use the panel helpers `describe_api` lists, and fix every cover the build reply's shell check names.

MOTION PARTS. Declare each moving axis as the joint the real part makes, driven by what would drive it, and buy the motion where a real machine buys it: rails and carriages, belts and pulleys, leadscrews and ball screws, steppers, extrusion, cylinders, spindles, casters, tyres and springs are `lib.part(sku, ...)` (part numbers on `describe_api section=library_parts`; read a part's `.spec['datums']` before you place it). A leadscrew is a `screw` joint; a rack, or a belt carrying a carriage, is a `rack_pinion` joint; a belt that ties three or more joints -- CoreXY, a differential -- is an `assembly.coupling([(joint, ratio), ...])` passed in `assembly.assembly(couplings=[...])`. A cylinder is a barrel and a rod with a slider between them, which may close a loop, driven by `assembly.actuator(stroke, kind="cylinder", ...)`. Give a coupled motor its rotor inertia and a stroke its moving mass with `assembly.joint_dynamics`, or the loop rings open in simulation. Where the machine works through a tool -- a nozzle, a spindle, a blade, a pipette -- declare it with `assembly.tool(...)` and read the `workspace` block, which says whether the tool reaches the whole work area. Where a part is missing, model a stand-in at its datasheet dimensions, named for the part, and list it in DECISIONS.md as unfinished.

MOVING REGIONS. When what a machine is depends on what moves -- a steering axle, a hitch, a lift arm, a gripper -- declare each region: `assembly.anatomy("hitch", [c_link_l, c_link_r])`, with `reason="..."` for one rigid on purpose, passed to `assembly.assembly(..., anatomy=[...])` (the regions declaration, under its older name). The build reply's `anatomy` block reports each region articulated, rigid with a reason or rigid with none, and names large welded pieces that stick out. A region you meant to move that is rigid with no measured reason is unfinished.

A SELF-MOVING MACHINE IS COMPLETE. When a design moves itself untethered, it carries what runs it -- controller, drivers, power and its regulation, the sensors its task reads -- as catalog components in bays cut with their `.bay()`, each with its catalog mass in the physics model, the heaviest where it steadies the machine. Wire them with `boards(...)`/`nets(...)` when the design declares a harness. Record what the catalog lacks as assumed. A tethered or bench-only machine leaves them out, said in DECISIONS.md, never silently.

GROUND WHAT THE POLICY READS. A `role="policy"` observation (the default) is what the trained network reads on the machine, so it names the onboard sensor that measures it: `assembly.sensor(...)` on the part that carries it, passed as `sensor=` to `assembly.observation(...)`; training refuses a policy channel no sensor measures. CHOOSE A SENSOR A REAL PART COULD BE, because a policy trained on a channel no part gives cannot run on the machine: name the part on the market and declare its datasheet figures -- a `"position_tracker"` read as `"tracked_position"`, terminated on its `_in_range` flag; `.load_sensor(actuator, ...)` only on an actuator that reports effort; a goal in a moving base's frame with `frame=base`. When no part measures it, it is privileged: `role="privileged"` -- for the reward, the terminations and the critic, never the policy -- and docs/sensors.md says which part would ground it.

THE SIMULATED BODY IS THE BUILT BODY. Contact is simulated through collision primitives -- boxes, capsules, spheres, cylinders -- so shape every contact surface as a union of exactly those, and give the physics model the same ones. Read `{{inspect}} scope=contacts` after an `assembly.mjcf` export: shapes that already touch at the pose every simulation starts from, which you did not mean to rest together, or any `penetrating` pair, sit in the wrong frame -- fix its `offset` before you train on it. Put what the machine rests on under its centre of mass, measured on the model, never estimated.

CLOSE A LINKAGE WHERE THE BUILT MACHINE WOULD HAVE ONE. A serial stand-in for a linkage is a different machine: it carries each actuator on the member it moves, changing the moving mass, the torques and the reach. Choose a closed chain -- four-bar, pushrod, slider-crank, scissor -- when the actuator should stay on the frame while the output moves, when the output needs a ratio or path one pivot cannot give, or when two outputs must move together; choose serial joints when each axis turns independently through a wide range, or the chain would pass near a dead point. A loop closes with an ordinary joint and the export closes it with an equality constraint the actuator drives through. A planar loop of parallel revolute pins is accepted as built; a closing pin that would have to tilt is refused as over-constrained -- give it a ball joint, as a rod end. The fit sweep drives the loop from its limited joints; the smoke check and the dynamics prove the rest. Record the output's travel and ratio in DECISIONS.md.

A LEARNED MOTION PAYS FOR THE MOTION, NOT THE DISTANCE. A reward that grows only with progress is maximised by a lunge, a tumble or a buzz, and PPO finds that first:
- Each actuated joint gets its `.joint_dynamics(joint)` beside its `.actuator(...)`, from the datasheet; never a hand-picked damping.
- Where the body can tip, upright is a reward and a termination: from an IMU's `rot_q*`, the up axis is `1 - 2*(rot_qx^2 + rot_qy^2)` of the way to vertical, and `assembly.termination("1 - 2*(rot_qx^2 + rot_qy^2)", below=0.7)` ends an episode past about 45 degrees. PAY FOR PROGRESS ONLY WHILE UPRIGHT: multiply progress terms by it.
- Progress is bounded: a target speed you defend from the mechanism and the actuators' rated speed, paid as `tanh(v / V)` or a charge on the distance from it, never raw speed. Bound it on both sides, because a policy paid only up to the target runs past it.
- THE TARGET SPEED MAKES THE INTENDED MOTION THE EASY ONE. Too low, and a shuffle or a buzz reaches it and training settles there; if every run finds the same degenerate motion, suspect the target before the weights.
- CENTRE THE COMMAND RANGE ON THE REST POSE with `command_limits_degrees`, so a zero action holds the rest pose instead of lurching.
- A CHARGE AGAINST A DEGENERATE MOTION HAS A CEILING: overweighted, it makes standing still the best policy. Raise one in small steps, evaluating after each.
- Charge yaw rate and sideways speed from the first run when the success spec bounds the heading.
- Surviving a step is worth more than ending the episode: a constant alive bonus (`assembly.reward("1", weight=2.0, label="alive")`), costs as positive quantities with negative weights, every term of order one.

SAY WHAT IS UNFINISHED. Name what you did not check and what you stood in for -- a joint not swept, a part the catalog lacked, a sensor or supply you assumed, a block answered with a reason rather than a fix -- in DECISIONS.md and when you report. A design that reads as finished and hides a stand-in is worse than one that names it.

WHEN A CALL IS REFUSED, read the failure envelope: `failure_code`, `observed` and `retry` say what went wrong and whether retrying could help; `observed.details.failure_site` names the failing call, its line and its operands, and `observed.stdout` what the script printed. Fix that call -- do not bisect the script in throwaway revisions -- and never repeat it unchanged.

