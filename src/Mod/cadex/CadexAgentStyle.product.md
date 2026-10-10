<!--
SPDX-FileCopyrightText: 2026 Cadex Authors
SPDX-License-Identifier: LGPL-2.1-or-later

A named, optional style for the agent guidance (ADR-653): the product --
an appliance, instrument or consumer device whose enclosure is most of what
shows. Provisional: written from how such products are built, with no rated
designs behind it yet (docs/DESIGN-LANGUAGE.md, its section). It adds to the
base and never restates it. Same format as the base: everything below the
marker line is the guidance, verbatim, with the same tool placeholders.
-->
<!-- guidance -->
STYLE: THE PRODUCT. The project chose this style: an appliance, instrument or consumer device whose enclosure is most of what shows -- a pet feeder, a desktop instrument, a charging dock, a kiosk, a kitchen appliance. It is provisional: written from how such products are built, not yet from rated designs, so where a rule here and a measurement disagree, the measurement wins. Its rules add to the design rules above.

- THE ENCLOSURE IS DESIGNED FROM THE INSIDE. Lay out the internals first, as the base says, then design the enclosure around them for the process that will make it: a moulded shell of even wall with draft, bosses for its screws and ribs where it must be stiff, or bent sheet with its bends and flanges. Record the process and the wall in DECISIONS.md. Check it: `{{look}}` `focus` on the shell's inside; every boss lines up with a screw, and every rib carries something.
- IT COMES APART WHERE IT IS ASSEMBLED AND SERVICED. Split the enclosure into the parts it is assembled from -- a base and a lid, a front and a back -- with the seam where the split is, and put access where a person loads, empties, cleans or replaces something: a door, a drawer, a hatch, a lid on a hinge.
- EVERY OPENING HAS A REASON: a vent where air flows, a button where a finger goes, a port where a cable goes, a window where a sensor or a person looks through. An opening with no reason is decoration.
- THE TOUCH POINTS ARE SIZED FOR A HAND. Controls, handles and whatever a person fills or empties sit on the face they meet, at a size a hand uses, and read as what they are without a label.
- ONE FAMILY OF RADII, ONE QUIET PALETTE. Consistent radii and a restrained palette make the parts read as one product; an accent marks a control, a status light or a part the person touches.
- WHEN YOU LOOK, ALSO NAME a seam where nothing separates, an opening with no reason, a screw with no boss, a service part with no access, and a shell that is a box around the parts rather than designed from them.
