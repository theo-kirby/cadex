<!--
SPDX-FileCopyrightText: 2026 Cadex Authors
SPDX-License-Identifier: LGPL-2.1-or-later

A named, optional style for the agent guidance (ADR-653): the vehicle --
mowers, tractors, loaders and rovers, on wheels or tracks. Provisional:
written from how such machines are built, with no rated designs behind it
yet (docs/DESIGN-LANGUAGE.md, its section, and docs/MACHINES.md). It adds to
the base and never restates it. Same format as the base: everything below
the marker line is the guidance, verbatim, with the same tool placeholders.
-->
<!-- guidance -->
STYLE: THE VEHICLE. The project chose this style: a machine that drives over the ground on wheels or tracks -- a robot or ride-on mower, a tractor, a loader, a rover. It is provisional: written from how such machines are built, not yet from rated designs, so where a rule here and a measurement disagree, the measurement wins. Its rules add to the design rules above.

- THE DUTY IS THE SPEC. In step 1, state the ground (lawn, field, gravel, rubble), the steepest slope and the highest step it must take, its payload or tool, its speed, its run time and its turning room, because the drivetrain, the clearance and the stability are all sized from them.
- THE DRIVETRAIN COMES FROM THE LOAD. Size each drive's torque from the vehicle's mass, its wheel radius and the steepest slope with rolling resistance -- about mass x g x radius x (sine of the slope + the rolling coefficient), shared among the driven wheels, with margin -- and write the sum in docs/actuators.md. Choose the layout from the duty, and say why: skid steer for a compact machine that turns in place, Ackermann for one that drives faster and turns gently, articulation for a loader that must stay rigid under its bucket, tracks where traction or ground pressure matters most.
- STEERING AND SUSPENSION ARE JOINTS. A steering knuckle, a pivoting axle, a rocker or a bogie is a real joint with its range taken from the sweep: sweep steering to full lock and the suspension through its travel, and keep every wheel and track clear of the body at both ends.
- STABILITY IS MEASURED. State the ground clearance, and keep the centre of mass low and well inside the wheel or track footprint: measure it on the model and record the slope at which it would tip, sideways and fore-aft, with and without its load raised. A loader's arm or a mower's deck moves the centre of mass; measure at both ends of its travel.
- THE BODY COVERS A CHASSIS. The chassis carries the loads; a hood or body over it covers the drivetrain, the power source and the electronics, opens where they are serviced (battery, blade, filter) and guards every moving part a hand or a foot could reach -- a blade, a chain, a belt, a pinch point in a linkage. It is shaped by what it covers and the duty -- shedding grass, water and dust -- rather than a box set on wheels.
- SMALL VEHICLES HAVE A KIT: `lib.gearmotor("pololu-2367")` driven by `lib.board("tb6612-adafruit-2448")` (one board drives two motors), with `lib.wheel("pololu-1430")` pressed on its shaft on a revolute with `angle_limits_degrees=(-180, 180)` so the sweep checks a full turn, and its `wheel.tyre()` as its own `mechanism` component. Larger drives, wheels and tyres may not be in the catalog at your size: check, and record each stand-in.
- WHEN YOU LOOK, ALSO NAME a wheel that hits the body at full lock or full travel, a centre of mass high or near the edge of the footprint, an exposed blade or chain, a service part with no access, and a body that is a box on wheels.
