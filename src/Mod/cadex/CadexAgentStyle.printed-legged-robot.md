<!--
SPDX-FileCopyrightText: 2026 Cadex Authors
SPDX-License-Identifier: LGPL-2.1-or-later

A named, optional style for the agent guidance (ADR-560): the printed legged
robot. A project chooses it in its agent.json (`cadex style --project DIR
printed-legged-robot`); with no style chosen, an agent reads the base in
CadexAgentGuidance.md alone. It adds to the base and never restates it. Its
evidence is docs/DESIGN-LANGUAGE.md, the style's section. Same format as the
base: everything below the marker line is the guidance, verbatim, with the
same tool placeholders.
-->
<!-- guidance -->
STYLE: THE PRINTED LEGGED ROBOT. The project chose this style: a small robot, printed around hobby or bus servos, boards, a battery and sensors, that stands and walks on legs. Its rules add to the design rules above, and where they say more, they win.

- ONE OF TWO FINISHES. In step 1, the concept also fixes the palette -- one shell colour, graphite, at most one accent -- and the finish, which is one of two. Pick the one that suits this machine and record why in DECISIONS.md:
  - EXPOSED MECHANISM: the actuators, boards, battery and cable run are visible, square to the frame, on a centreline or a symmetric grid, each held by its own screws or bay, so the layout itself is the design.
  - PANELLED HARD SURFACE: the parts are enclosed by flat panels, chamfers, a real seam between a tub and a lid, a bolted hatch and visible fasteners -- crisp, never one soft skin. At its plainest it is a few well-proportioned volumes with nothing decorative.
- TWO MATERIALS AND ONE SMALL ACCENT. The accent covers well under a tenth of the surface: horn caps, a cradle, the feet, a power cable, a status light, a sensor bezel.
- NOT THE MASCOT BOX. The body is never a large, soft, rounded box over short or thin limbs with blocks hanging under it. That one archetype is the thing to avoid above all others; if your design is drifting towards it, go back to step 4.
- NO FACE. Do not give the machine eyes, a visor, a mouth or any face. The front may carry a real sensor instead -- a camera, a range sensor, or a slot cut for one -- as a held part on the body's forward axis, or the controller can be the focal point. Prefer one sensor part or one slot to a pair of round lenses, which reads as eyes.
- JOINTS ARE FEATURES. Every actuated axis reads as the same round feature -- a cap, hub or drum concentric with the axis and at least as wide as the horn it covers -- so a horn reads as a hub, never a bare arm. One joint design serves the whole robot. The cap goes where the horn is: the horn sits between the servo's case top and the part it drives, so a disc on the servo's far face or beside the hub leaves the horn in view. Make the driven part's hub the cap: a disc of radius at least the horn's `.spec["arm_reach_mm"]` plus a 1.6 mm wall, cut with `horn.body` so the horn and its screw sit inside it, with a skirt reaching down past the horn to within 1 mm of the case top. A joint is one cap, as small as covers its horn: drive the link with the shortest horn that carries it -- on a micro servo `servo.horn("cross")`, whose 10.2 mm reach makes a cap about two thirds the diameter a `single_arm` horn needs -- and size the cap to that reach plus the wall, no larger. Do not add a second disc on the servo's other face: close that side with the limb that wraps the case, so each axis shows one round feature, never a stack of discs.
- LIMBS CARRY LOAD, AND FEET ARE PARTS. A walking leg is a tapered, shelled or ribbed beam that follows the load path, about 60% of its hip section or less near the foot, never a thin stick. Taper the section in both directions, its depth as well as its width, so the limb narrows seen from the side as well as from above: a plate of one thickness cut to a tapering outline is still a flat bar edge-on. It ends in a designed foot -- a pad, a cap or a plate, or a wheel with a tyre -- never the cut end of a bar.
- LEGS ARE LONG AGAINST THEIR JOINTS. Size a walking leg from its joint caps, not the joints from the leg: between axes, the thigh (femur) and the shin (tibia) are each at least 2.5 times the joint cap's diameter, the shin is the longest segment, and a hip (coxa) link is no longer than its two servos need. At the standing pose the thigh runs out level or a little above level and the shin comes down to the foot, so the leg reads as one line from hip to foot: never a knee folded up high above the body, and never joints so close together that their caps crowd each other. Check it with `{{look}}` `focus` on one leg: the limbs, not the joints, are most of what you see.
- WHEN YOU LOOK, ALSO NAME a thin stick leg, a short leg under crowded joint caps, a bar end for a foot, a face, a horn you can see and a soft box.
