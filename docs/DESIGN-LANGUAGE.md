# The Cadex design language — small printed robots that look engineered

Verified against source: 2026-10-04. Provenance: `[Cadex-new]`.

This is how a robot that Cadex designs should look: a small legged,
wheeled or fixed machine, 3D-printed around hobby servos, gearmotors,
boards, a battery and sensors. It is what the agent driving Cadex is
taught, through the engine's overlay `Mod/cadex/CadexAgentGuidance.md`
(which `cadex guidance` prints and `cadex mcp` points the agent at;
Cadex has no agent of its own, ADR-538), and what the renderer presents.

**Where it comes from (orun1, ADR-479).** ot10 wrote this language from a
set of reference images (ADR-411). The owner's verdict on what it produced
was that the robots look finished but are not well designed. So orun1
replaced it with a language written from the owner's own blind ratings of 55
sweep designs, 7 robot types by 8 design theses
(`docs/probes/orun1/README.md`, `docs/probes/orun1/sweep/ratings.json`),
and from three readings in the charter that the owner has not yet confirmed:

- **A1.** Both the face and the soft pillow-box body are out. A focal
  sensor may sit where a face was, as a real part.
- **A2.** One family, two finishes: an exposed, ordered mechanism, or an
  enclosed but panelled hard-surface body. The agent picks one per robot and
  says why.
- **A3.** The accent stays small and functional.

**How a rule cites its evidence.** Every rule names sweep designs by id with
the owner's verdict (Love 3, Like 2, Meh 1, No 0) and the set the design is
in (`dev` or `held-out`). Alternatively, it quotes the charter or is marked
**[judgement]**: the run's or the operator's own call, with no rating behind
it. Thesis means are from the README's table. The evidence is thin: there are
55 ratings, 4 Loves and 3 Nos, and a thesis is confounded with how well one
agent turn carried it out. Read a rule's citations as direction, not as
proof. Citing a held-out design here tunes nothing D1 measures: D1's judge
was frozen and measured before this was written (ADR-478), and the
held-out set has had its one use.

**What reaches the agent.** Only the rules reach the agent, as plain
instructions in the overlay. The overlay quotes no rating and no design id,
shows no sweep render, and contains nothing of the judge's prompt. This
document is the evidence for the rules, and it is not in any prompt.

**Exists today versus target.** The overlay teaches §1–§6 and the procedure
in §8 (ADR-479). Whether an unassisted design follows them, and whether the
frozen judge v2 rates the result above the sweep's Likes and Loves, is D4's
measurement and not a claim this document makes.

## 0. The one-sentence version

**An engineered machine built from the inside out: real parts chosen and
placed first, a structure that visibly carries them, then either an
ordered, exposed mechanism or a panelled hard-surface enclosure. No face, no
pillow body, and one small functional accent.**

## 1. Form: an engineered machine, in one of two finishes

- **Not the mascot box.** The robot is never a large, soft, rounded box
  with a visor slot or dot eyes, over short or thin limbs, with blocks
  hanging under it. All three Nos are this design:
  `biped-a-servo-joint` (No, dev), `hexapod-g-minimal` (No, dev) and
  `biped-h-free` (No, held-out). The same body with better limbs is still
  only Meh: `quadruped-d-product-shell` (Meh, dev),
  `hexapod-f-creature` (Meh, held-out). The owner's own description, in the
  charter, was "a rounded box with four legs". (ADR-481 removes the
  rule that prescribed it.)
- **Pick a finish, and say why.** Per A2 there are two finishes, and the
  agent records its choice in the project's `DECISIONS.md` before any geometry:
  - **Exposed mechanism.** This finish has the highest thesis mean in the
    sweep (2.14). The actuators, boards, battery and cable run are visible
    and laid out with order. Examples: `balancer-c-exposed-mechanism`
    (Love, dev): two slotted side frames, an orange cradle holding the
    electronics, a visible power lead. `biped-c-exposed-mechanism` (Love,
    held-out): a stacked servo column with horn caps and a board deck with
    routed wires. Also `quadruped-c-exposed-mechanism` (Like, held-out) and
    `hexapod-c-exposed-mechanism` (Like, held-out).
  - **Panelled hard surface.** Thesis mean 1.71. The body is enclosed, but
    by flat panels, chamfers, a real seam between tub and lid, a bolted
    hatch and visible fasteners, never by one soft skin. Examples:
    `quadruped-e-hard-surface` (Love, held-out), `biped-e-hard-surface`
    (Like, held-out) and `balancer-e-hard-surface` (Like, held-out). At its
    plainest the enclosure is a few well-proportioned volumes with nothing
    decorative: `arm5-g-minimal` (Love, dev). Plain is not enough on its
    own, though, because `hexapod-g-minimal` (No, dev) is also plain.
  - The consumer product shell, the old default, has a thesis mean of 1.43.
    The creature thesis scores 1.29, and the agent's free choice 1.00. None
    of them is a finish this language offers.
- **Hardware may show, and where it shows it is ordered.** A servo case, a
  board or the battery is not something to hide. It sits square to the
  frame, on a centreline or a symmetric grid, held by its own screws or its
  own bay, and it is placed rather than left where it fell. The evidence is
  `balancer-c-exposed-mechanism` (Love, dev): its notes say every part
  "sits on a centreline, is held by its own screws". Also
  `biped-c-exposed-mechanism` (Love, held-out) and
  `quadruped-c-exposed-mechanism` (Like, held-out), whose board deck is
  open on top. (ADR-482 removes "never an exposed case or a bare
  board".)
- **Nothing looks stuck on.** Every visible part is held by something
  visible or obvious, and no block hangs under the body without a
  structural reason. The charter quotes the owner: the motor pods "look
  stuck on". The dark boxes hanging under `hexapod-g-minimal` (No, dev) and
  the loose blocks under `hexapod-f-creature` (Meh, held-out) are the
  failure.
- **Detail is real.** Surface detail is a part boundary: a seam where two
  printed parts actually separate, a fastener that actually fastens, a
  hatch, a panel, a cable that actually carries power or signal. Detail that
  stands for nothing is not allowed: no greeble, no fake vent and no stripe.
  The evidence is `quadruped-e-hard-surface` (Love, held-out): its notes
  say "every seam, groove and socket-head bolt is a real joint". Also
  `arm5-g-minimal` (Love, dev), with "seams only where parts actually
  separate", and the routed wiring of `biped-c-exposed-mechanism` (Love,
  held-out). (ADR-483 replaces "split lines are the only surface
  detail".)
- **Edges are finished, and the body is not a pillow.** Every printed
  outside edge is filleted or chamfered to suit its part: a chamfer at 45°
  counts as finished, and so does a tangent fillet. One large, uniform
  radius over a whole box is what makes the pillow. The Love among the
  quadrupeds is chamfered (`quadruped-e-hard-surface`, Love, held-out). The
  Nos are heavily rounded boxes (`biped-a-servo-joint`, `biped-h-free`,
  `hexapod-g-minimal`). (ADR-481.)

## 2. Materials and palette: two materials, one small accent

Three **appearance roles**, and every part has exactly one:

| role | what it is | default colour | alternates |
|---|---|---|---|
| `shell` | printed structure and panels: frames, decks, limbs, covers | bone `#E9E6DF` | cool grey `#B9BDC2`, tan `#C9AE86` |
| `mechanism` | purchased hardware that shows, dark panels, links, tyres, jaws | graphite `#2F3237` | — |
| `accent` | a few functional features: horn caps, a cradle, feet, a power cable, a status light, a sensor bezel | signal orange `#F26A1B` | yellow `#F2B40A`, teal `#179C98` |

- **Bone, graphite and one orange.** All four Loves are this palette:
  `balancer-c-exposed-mechanism`, `biped-c-exposed-mechanism`,
  `quadruped-e-hard-surface` and `arm5-g-minimal` (their `palette` fields in
  `ratings.json`). The colour values are ot10's, kept unchanged.
- **The accent marks a function (A3).** It goes on horn caps
  (`biped-c-exposed-mechanism`, Love; `arm5-g-minimal`, Love), on a cradle
  (`balancer-c-exposed-mechanism`, Love), on feet or a sensor slot
  (`quadruped-e-hard-surface`, Love), on a power cable or on a status light.
  It never forms a stripe, a pattern or a face. It covers well under a tenth
  of the surface **[judgement]**.
- **One shell colour, with graphite only where it means something, is
  also valid.** In `arm5-g-minimal` (Love, dev) the body is all white and
  graphite marks only the gripper jaws, so the jaws "read as the tool".
- **Colour follows role, not supplier.** A servo that shows is
  `mechanism` because it is mechanism **[judgement]**, carried over from
  ot10.

xscript declares the role per part and the palette per assembly
(`assembly.component(..., appearance=)`, `assembly.assembly(..., palette=)`,
`docs/XSCRIPT.md`, ADR-413). Inventory, `render`, `look` and review carry
them, and the dashboard's viewport paints them (ADR-449, ADR-522) by the
same rule the studio draws with. A part with no declared role is drawn by supplier until
it declares one.

## 3. Joints are features

- **Every rotation axis reads as a round feature.** That means a horn cap,
  a hub, a drum or a bearing boss, concentric with the axis. Examples: the
  repeated sleeve, hub and orange cap at all six joints of
  `biped-c-exposed-mechanism` (Love, held-out); the flush cap at every tilt
  axis of `arm5-g-minimal` (Love, dev); the hip drums of
  `quadruped-e-hard-surface` (Love, held-out); the hip caps of
  `quadruped-c-exposed-mechanism` (Like, held-out).
- **One joint design for the whole robot.** "One repeated joint module …
  gives the legs a rhythm" (`biped-c-exposed-mechanism` notes, Love).
  `arm5-g-minimal` (Love) uses one joint radius per servo size.
- **The cap goes over the horn.** The cap is the driven part's hub, cut
  around the horn and its screw, so that no bare horn arm shows (ADR-440)
  **[judgement]**: this is a fit rule from ot10, and no rating isolates it.
- **One small cap per axis.** The cap is as small as covers its horn: the
  shortest horn that carries the link (the cross horn on a micro servo), at
  reach plus wall and no larger, and no second disc on the servo's far face
  (ADR-494, which removes that half of ADR-440). Evidence: hexapod trial 1
  (`orun1-t1-hexapod`, rev `35193b3e`) built a 35 mm disc on both faces of
  every servo and lost under frozen judge v2 on "crowded clusters of
  joints". **[judgement]** on the size: no rating isolates cap diameter.

## 4. No face; a sensor where a face was

- **No face, no eyes, no mouth.** Of the 55 sweep designs, the 47 whose
  notes mention a face, eyes or a visor average 1.43. The 8 whose notes do
  not average 2.00 (README, "What the ratings say", point 2). Every No is a
  visor with two dot eyes. (ADR-480 removes the mandated face.)
- **The front may carry a real sensor (A1).** A camera, a range sensor or
  a slot cut for one goes at the front as a held part, on the body's forward
  axis. The forward elements of two Loves are of this kind: the accent slot
  across the front of `quadruped-e-hard-surface` (Love, held-out) and the
  dark lens bar of `biped-c-exposed-mechanism` (Love, held-out). Both sit on
  a hard front, not in a soft box. Their own notes called them an
  "eye-bar" and "a visor with two lenses", and the owner rated them Love
  anyway. So the line this rule draws is between a sensor that is part of
  the machine and a mascot face, not between a front with something on it
  and a bare one. Whether two round lenses side by side read as a sensor or
  as eyes is not settled by 55 ratings **[judgement]**. Prefer one sensor
  part or one slot.
- **The controller can be the focal point.** In
  `balancer-c-exposed-mechanism` (Love, dev), "the controller is the face":
  an orange bezel around the board, "instead of a decorative visor".

## 5. Structure, limbs and feet

- **Structure carries the parts, visibly.** The structure is side frames,
  a spine, a deck, a servo column or a hull, each placed where the load
  goes. Examples: the two slotted side cheeks of
  `balancer-c-exposed-mechanism` (Love, dev) and the stacked servo column of
  `biped-c-exposed-mechanism` (Love, held-out).
- **Limbs look load-carrying.** A walking leg tapers from a deep hip to the
  foot, in depth as well as in width (ADR-428). The tapered legs of
  `hexapod-c-exposed-mechanism` (Like, held-out) and the shins of
  `quadruped-e-hard-surface` (Love, held-out) are the pattern. The thin
  stick legs of `hexapod-g-minimal` (No, dev) and `hexapod-f-creature` (Meh,
  held-out) are the failure.
- **Legs are long against their joints.** Thigh and shin each at least
  2.5 joint-cap diameters between axes, the shin the longest segment, the
  hip link no longer than its servos need, the thigh level or a little above
  at the standing pose (ADR-494). Evidence: hexapod trial 1's 48 mm thigh
  and 70 mm shin under 35 mm caps (1.4 and 2.0 diameters, knee raised)
  drew "upturned segments … cluttered" from frozen judge v2. **[judgement]**
  on the 2.5 figure: it is the run's own ratio, not a rated measurement.
- **Feet are designed parts.** A foot is a pad, a cap or a plate, or a
  wheel with a tyre, never the cut end of a bar. Examples: the orange foot
  pads of `quadruped-e-hard-surface` (Love), the flat foot plates of
  `biped-c-exposed-mechanism` (Love) and the spoked wheel with a dark tyre
  of `balancer-c-exposed-mechanism` (Love). The charter names feet as
  designed parts, not leftovers. A ball on the end of a stick is mixed
  evidence: it appears on `hexapod-g-minimal` (No) and also on
  `quadruped-c-exposed-mechanism` (Like).
- **Mass low and central.** The battery is the heaviest part and goes
  low and between the hips or axles **[judgement]**: this is an engineering
  rule, not a rated one. The Loves follow it
  (`biped-c-exposed-mechanism` notes: "the battery sits between the
  hips").
- **Hexapods are the hardest type** (type mean 1.14, the lowest). Their
  best two show a frame with the servos laid out at the hips
  (`hexapod-b-motors-in-body`, Like, dev; `hexapod-c-exposed-mechanism`,
  Like, held-out). Their worst is the soft box on sticks
  (`hexapod-g-minimal`, No, dev).

## 6. Printability **[judgement]**

None of the ratings tested these rules. They are manufacturing rules,
carried over from the overlay and ot10:

- every printed part has a flat face to print on, no unsupported overhang
  past 45°, walls of at least 1.6 mm and holes sized to their fastener;
- a colour change is a part boundary: each role is its own printed part in
  its own filament, never paint and never a multi-material print;
- covers and panels are 1.6–2.4 mm thick, screwed to the structure that
  carries them, with clearance from what they cover through every joint's
  range;
- fasteners are deliberate: where they show, they form an even pattern
  (`balancer-c-exposed-mechanism`, Love: "three evenly spaced M3 screws per
  cheek").

## 7. Presentation

A design is judged the way it is shown. The owner rated each sweep design
from one studio hero on the dark floor (README, "The ratings"), and judge
v2 sees exactly that picture.

- **The hero shot** is taken from a low three-quarter view: the camera
  15–25° above the floor and 30–45° off the front.
- **Studio light, so that form reads.** A key light, a soft fill and a
  rim light. Flat shading hides chamfers and radii alike.
- **The dark prototype floor** (owner's decision, ot10 A8, ADR-444): every
  presented image stands on the review viewport's mat. That is the scene
  background `#141414`, a `#1c1c1c` / `#232323` checker and a `#3a3a3a`
  major line on every grid pitch, fading into the background with distance,
  so there is no horizon line. The colours are one table,
  `CadexStudio.PALETTE` in the engine (ADR-445). The viewport's copies are
  held equal to it by a test.
- **A soft contact shadow** under the robot, and **antialiased edges**.
- **A concept sheet** presents a design: the hero, orthographic line
  views, the palette swatches, the name and the key numbers (mass,
  actuator count, size). An exploded or cutaway view of where each part
  sits is the long-term direction (charter, long-term rung 2).

Built by ot10 A2 (hero render: `render`'s `hero.png` and `look`'s `hero`
view, ADR-412) and A6 (concept sheet).

## 8. The order of design: inside out

The charter makes this the procedure, not a hint ("choose the actuators,
controller, power, battery, sensors and the cable path; place them; then
design the structure that carries them, and only then any panels or
covers"). Every Love's notes describe this order: `balancer-c` ("the
inner width … was set by motor length and battery width before the frame
was drawn"), `biped-c` ("I fixed the servo, battery and board positions
first and grew the frame around them"), `quadruped-e` ("the battery's bay …
set where the hips go") and `arm5-g` ("I placed the six servos and five
electronics parts first"). The overlay teaches it as six steps:

1. **Concept.** Name the machine, its finish (§1, with the reason), its
   palette and its proportions, before any geometry.
2. **Parts.** Choose every purchased part from the catalog: the actuators,
   the controller, a servo driver if one is needed, the regulator and
   battery, the sensors, the fasteners. Choose the cable path too.
3. **Place them.** Battery low and central, the controller and driver
   where the cables are short, sensors at the front, servos at the axes
   they drive, mirrored about the centre plane. Check the fit with the parts
   alone.
4. **Structure.** Design the printed structure that carries them. Each
   part is held by something named, such as screws through its own tabs, a
   bay cut with its `.bay()`, a clip or a horn, and never only by being
   inside a cover. Add limbs, joints and feet.
5. **Finish.** For the exposed finish, order and fasten what shows. For
   the hard-surface finish, add panels and covers over the structure, with
   real seams and fasteners. Then the joint caps and the accent, each part
   with its role.
6. **Refine with `look`.** Read the measures and the pictures, name what
   reads as crude, fix the worst thing, and look again.

## 9. What was removed, and why

| removed rule (ot10) | why | ADR |
|---|---|---|
| "one soft body primitive with a face" (§0, §1 "the body is one readable primitive", "soft primitives, large radii") | all three Nos are that body (§1) | ADR-481 |
| a mandated face of a set size and contrast (§4, ADR-422) | face 1.43 against no face 2.00; every No has one (§4) | ADR-480 |
| "never an exposed case or a bare board"; shells hide the hardware (§1, ADR-428's cradle rule) | the exposed-mechanism thesis is the best rated (2.14) (§1) | ADR-482 |
| "split lines are the only surface detail" | the Loves use real fasteners, hatches and cables as detail (§1) | ADR-483 |
| the ten-reference citations | the language is now cited from the owner's ratings; ot10's rubric is retired as the authority | ADR-484 |

## 10. What this is not

- **Not a copy.** No sweep render or reference image reaches the product,
  and no rule describes one. The agent learns the direction only as written
  rules.
- **Not ornament over function.** A design that looks right and fails its
  fit checks is not accepted. A visible part that nothing holds is a
  defect, whichever finish it is in.
- **Not the judge.** Judge v2 (`docs/probes/orun1/README.md`) is the
  authority on whether a design clears the owner's bar, and this document
  does not override it. If they disagree, the judge wins, and this
  document is what changes.
