<!--
SPDX-FileCopyrightText: 2026 Cadex Authors
SPDX-License-Identifier: LGPL-2.1-or-later

A named, optional style for the agent guidance (ADR-653): the gantry
machine -- 3D printers, CNC routers and mills, laser cutters, pick-and-place
and liquid handlers. Provisional: written from how such machines are built,
with no rated designs behind it yet (docs/DESIGN-LANGUAGE.md, its section,
and docs/MACHINES.md, the breadth bench). It adds to the base and never
restates it. Same format as the base: everything below the marker line is
the guidance, verbatim, with the same tool placeholders.
-->
<!-- guidance -->
STYLE: THE GANTRY MACHINE. The project chose this style: a machine that moves a tool point over a work area on linear axes -- a 3D printer, a CNC router or mill, a laser cutter, a pick-and-place or a liquid handler. It is provisional: written from how such machines are built, not yet from rated designs, so where a rule here and a measurement disagree, the measurement wins. Its rules add to the design rules above.

- THE TOOL POINT IS THE SPEC. In step 1, state the work envelope (the travel on each axis), the tool and its loads -- a cutting force, a hotend's mass, a pipette's reach -- the accuracy the job needs and the speed it runs at, because every later size serves that envelope at that accuracy. Check it: sweep each axis through its travel, measure where the tool point reaches against the envelope you stated, and record both.
- STIFFNESS FIRST. A gantry's accuracy is its frame's stiffness under the tool's load and the moving mass's acceleration, so close the frame into boxes and triangles rather than open cantilevers, keep the moving mass low, and stack light, fast axes on heavy, slow ones. Check it: name the load path from the tool to the floor, and run `part.stress` on the members that carry the tool when a process load matters.
- LINEAR MOTION IS BOUGHT. Each axis runs on a guide -- a rail and carriage, rods and bearings, wheels on an extrusion -- and is driven by a belt, a leadscrew or a ballscrew chosen from its load and accuracy: a belt for light and fast, a screw for a heavy cut or a vertical axis that must not fall when unpowered. Record the choice and why. Each axis is a slider limited to its travel, with room for its end stop.
- CABLES MOVE WITH THE AXES. Every lead to a moving carriage runs in a cable chain or a strain-relieved bundle, anchored at both ends, at no less than its bend radius, and clear of the axes and the work area through the whole travel.
- AN ENCLOSURE HAS A JOB. Enclose the machine when the process needs it -- heat for printing, fumes and light for a laser, chips and noise for a mill, contamination for a liquid handler -- with doors hinged clear of the moving axes, a window where the operator watches the work, and service access to the electronics. When the process needs none, leave the frame open and ordered.
- THE ELECTRONICS HAVE A BAY. Controller, drivers and supply sit together out of the work area, with a path for cooling air and short runs to the motors.
- WHEN YOU LOOK, ALSO NAME an axis with no visible guide, a cantilever carrying the tool, a cable crossing the work area or stretched at an end stop, a door that meets a moving axis, and an enclosure that does nothing.
