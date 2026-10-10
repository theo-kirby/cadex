# MACHINES.md — The Breadth Bench

Verified against source: 2026-10-10 (a test catalogue, not a claim about the engine; the tiers are estimates made before the 2026-10-10 architecture review)

These are machines to give Cadex as design briefs, chosen to test how broad
the system is. Creatures (raptor, heron, leopard) and the mini excavator
(orun5) have been tried. Everything below is a candidate. Each entry names:

- **Stresses**: the capability axes (codes below) the design has to get right.
- **Autonomy**: what the machine could *do* in simulation once designed — the task, policy or check that proves it works.
- **Tier**: an estimate of what it takes, given today's library and engine.
  - **1**: buildable with today's parts and checks.
  - **2**: needs new catalog parts or library helpers, such as rails, belts, wheels, cylinders, spindles or sheet-metal panels.
  - **3**: needs new engine capability, such as fluids, soil, deformables, aerodynamics or contact-rich process physics.
- **Panel**: how hard the machine tests the panel and enclosure system.
  - **●** means the machine is mostly its skin: an injection-moulded shell, sheet-metal enclosures or doors.
  - **○** means it has some covers.
  - **–** means it is a bare mechanism.

## Capability axes

| Code | Axis | Examples of what it demands |
|---|---|---|
| **G** | Linear motion | Profile rails, carriages, belts and pulleys, leadscrews and ballscrews, endstops, CoreXY and H-bot kinematics |
| **W** | Wheeled drivetrain | Hubs, differential and skid steer, Ackermann, articulated steering, mecanum or omni wheels, suspension |
| **T** | Tracks | Sprockets, idlers, road wheels, tensioners, flippers |
| **L** | Closed linkages | Four-bars, Z-bars, pantographs, Jansen and Klann legs, scissor lifts, three-point hitches, rocker-bogies |
| **H** | Fluid power | Hydraulic and pneumatic cylinders, rotary actuators, hoses on a path |
| **F** | Frame | Aluminium extrusion, sheet metal with bends, welded tube, castings, stiffness and deflection |
| **E** | Enclosure and skin | Moulded shells with bosses and ribs, sheet-metal covers, doors and windows, seals, access panels |
| **X** | Process tool | Spindle, hotend, laser, blade, nozzle, pipette, gripper, auger, brush |
| **A** | Serial arm | 4–6 DOF arms, wrists, tool changers, remote-centre-of-motion linkages |
| **P** | Propulsion and fluids | Propellers, thrusters, buoyancy, pumps, sails, rotors |
| **C** | Compliance | Cables and tendons, springs, soft or origami parts, series-elastic joints |
| **K** | Kinematic trains | Gearboxes, cams, Geneva drives, cranks, clutches, escapements |
| **S** | Perception | Placement and field of view of lidar, cameras, RTK GNSS, bumpers and force sensors |

## 1. Digital fabrication

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| Cartesian "bed-slinger" FDM printer (Prusa MK-class) | G F X K | Toolpath following; bed-mesh probing; ringing vs. acceleration | 2 | ○ |
| Enclosed CoreXY printer (Bambu/Voron-class) | G F E X | Toolpath following at speed; input-shaper tuning; filament changing | 2 | ● |
| Delta printer | L G F X | Delta inverse kinematics; workspace and accuracy map | 2 | ○ |
| Belt printer (infinite Z) | G X F | Continuous part ejection; tilted-gantry kinematics | 2 | ○ |
| Tool-changer printer (Prusa XL / E3D-class) | G A X E | Tool docking and pickup; tool-offset calibration | 2 | ● |
| SCARA printer or plotter | A X | Polar workspace; arm compliance at the tip | 1 | ○ |
| Resin MSLA printer | G E X | Peel-force cycle; Z-lift profile | 2 | ● |
| 3-axis CNC router (gantry, extrusion frame) | G F X S | Toolpath; frame deflection under cutting load; probing | 2 | ○ |
| Desktop CNC mill (cast column, ballscrews) | G F X E | Chatter and stiffness; tool-length probing | 2 | ● |
| 5-axis trunnion mill | G A X E | 5-axis inverse kinematics; collision envelope of the trunnion | 3 | ● |
| CNC lathe with turret | G K X E | Turret indexing; tool-path collisions | 2 | ● |
| CO₂ or diode laser cutter | G E X | Raster and vector paths; lid interlock; air-assist routing | 2 | ● |
| Pen plotter (AxiDraw-class) | G X | Path following; pen lift | 1 | – |
| Vinyl or knife cutter | G X W | Media feed by pinch rollers; drag-knife offset | 2 | ○ |
| PCB pick-and-place (OpenPnP-class) | G X S E | Vision fiducials; nozzle-tip changing; feeder indexing | 2 | ○ |
| Hot-wire foam cutter (4-axis) | G X | Synchronised dual-gantry paths | 1 | – |
| CNC wire bender | K X G | Bend sequence; springback compensation | 2 | ○ |
| Filament winder (composite tubes) | G K X | Helical winding pattern; mandrel sync | 2 | – |
| 3D-scanner turntable and arm | K S | View planning for coverage | 1 | ○ |
| Desktop injection-moulding press | L H F E | Toggle clamp force; shot cycle | 2 | ● |

## 2. Lab, bench and precision automation

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| Liquid-handling robot (Opentrons-class) | G X E S | Pipetting protocol; deck-collision checking; tip pickup | 2 | ● |
| Microplate-handling SCARA | A X | Plate transfers between instruments | 1 | ○ |
| Colony picker | G X S | Vision-guided picking | 2 | ● |
| Motorised microscope stage / slide scanner | G K S | Tiled scanning; focus stacking | 2 | ○ |
| Camera motion-control slider and pan-tilt | G K S | Repeatable keyframed moves | 1 | – |
| Equatorial GoTo telescope mount | K F S | Sidereal tracking; plate-solve pointing | 2 | ○ |
| Dual-axis solar tracker | K F S | Sun tracking; wind stow | 2 | – |
| Rubik's-cube solver | K X S | Solve sequence; grip timing | 1 | ○ |
| Chess-playing gantry or arm | G A S | Piece picking from board vision | 1 | ○ |
| Cable-driven parallel robot (camera cam / facade) | C G F | Cable-tension feasibility; workspace | 2 | – |

## 3. Home, yard and consumer

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| **Robot lawn mower** | W X E S | Coverage planning; docking; slope traction; blade-stop safety | 2 | ● |
| Ride-on or zero-turn mower | W X F E | Zero-turn control; deck height linkage | 2 | ● |
| Reel-mower robot for golf greens | W K X | Stripe-pattern coverage | 2 | ○ |
| Robot vacuum with self-empty dock | W X E S | Coverage; docking; cliff and bump sensing | 2 | ● |
| Window-cleaning robot | W P X E | Suction adhesion; edge detection on glass | 3 | ● |
| Pool-cleaning robot | T W P X E | Wall-climbing coverage underwater | 3 | ● |
| Gutter-cleaning auger robot (Looj-class) | T X | Linear traverse in a channel | 2 | ○ |
| Snow-blower / yard multi-tool robot (Yarbo-class) | T W X E | Swappable tool modules; path coverage | 2 | ● |
| Garden gantry (FarmBot) | G X S F | Seed, water, weed by plant map | 1 | – |
| Laundry-folding machine | G K X E | Fold sequence on cloth | 3 | ● |
| Automated pet feeder or litter box | K E S | Portioning; rotation cycle | 1 | ● |
| Dog ball launcher | K X E | Launch speed vs. range | 1 | ● |
| Robotic arm for dishwasher loading | A X S | Grasping varied objects | 2 | ○ |

## 4. Agriculture

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| **Compact autonomous tractor with three-point hitch and PTO** | W L F K E S | Row following; implement raise and lower; headland turns | 2 | ● |
| Laser weeder implement (Carbon-class) | F X S | Weed detection; laser dwell scheduling at ground speed | 2 | ● |
| Mechanical intra-row weeder | L X S | Hoe in and out around crop plants | 2 | ○ |
| Small solar field rover (Naio Oz / FarmDroid-class) | W X F S E | RTK row-following; seeding and hoeing | 2 | ○ |
| Multi-arm strawberry harvester | A G X S F | Detect and pick; arm scheduling | 3 | ○ |
| Vacuum-tube apple harvester | A P X S | Pick sequence; tube routing | 3 | ○ |
| Orchard sprayer platform (GUSS-class) | W X P S E | Canopy-tracking spray | 3 | ● |
| Grain-bin auger robot (Grain Weevil-class) | X W T | Traverse loose grain; break crust | 3 | ○ |
| Milking robot (box or rotary) | A X S E | Teat detection; cup attach | 3 | ● |
| Barn feed pusher (Lely Juno-class) | W E S | Perimeter following | 1 | ● |
| Crop-phenotyping gantry | G F S | Sensor-head scanning over plots | 1 | – |
| Tree-climbing pruner | W C X | Climb a trunk; trim limbs | 3 | ○ |
| Agricultural spray drone | P X F | Swath coverage; payload sloshing | 3 | ○ |

## 5. Construction, mining and heavy equipment

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| Excavator at full scale, with a real bucket four-bar | H L T F E | Dig-and-dump cycle; trench to a grade (orun5 W12 left the four-bar unbuilt) | 2 | ● |
| **Skid steer / compact track loader** | H L T W F E | Bucket fill; lift-arm path; skid-steer driving | 2 | ● |
| Wheel loader (Z-bar, articulated steer) | H L W F E | Load-and-carry cycle | 2 | ● |
| Bulldozer | H T F E | Push to grade | 3 | ● |
| Articulated dump truck | W L H F E | Haul route; tip cycle | 2 | ● |
| Rebar-tying gantry (TyBOT-class) | G X S F | Find and tie intersections along a bridge deck | 2 | ○ |
| Bricklaying robot (SAM / Hadrian-class boom) | A G X F | Course placement; boom stabilisation | 3 | ● |
| Drywall-finishing robot (Canvas-class) | A G X W | Spray and sand passes over a wall | 3 | ○ |
| Layout-printing rover (Dusty-class) | W X S | Print lines from a plan; localisation | 1 | ● |
| Ceiling-drilling robot (Jaibot-class) | T G A X S | Drill-hole placement overhead | 2 | ○ |
| Concrete 3D-printing gantry | G F X | Layered extrusion path | 2 | – |
| Tower crane | F K C | Load sway; slewing | 2 | ○ |
| Scissor lift | L H F W | Platform stability vs. height | 1 | ○ |
| Remote demolition robot (Brokk-class) | H T A L | Outrigger stance; breaker reach | 2 | ○ |
| Tunnel-boring machine cutterhead and shield | K H F | Thrust and torque balance | 3 | ○ |
| Lunar regolith excavator (RASSOR-class, counter-rotating drums) | W X K | Dig with net-zero reaction | 3 | ○ |

## 6. Logistics and industrial

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| Shelf-lifting AMR (Kiva-class) | W K S E | Fleet routing; lift under a pod | 1 | ● |
| Autonomous forklift | W G H S E | Pallet engagement; mast-height stability | 2 | ● |
| Grid storage robot (AutoStore-class) | W G X E | Dig and stack bins on a grid | 2 | ● |
| Tilt-tray or cross-belt sorter module | K G X | Divert timing | 2 | ○ |
| Palletising arm cell | A X F | Pallet patterns; layer stability | 1 | ○ |
| Delta pick-and-place robot | L X S | High-speed vision picking from a conveyor | 1 | ○ |
| SCARA assembly robot | A X | Peg-in-hole insertion | 1 | ● |
| 6-axis industrial arm on a linear track | A G F | Reach study; cycle time | 1 | ● |
| Truck-unloading mobile manipulator (Stretch-class) | W A X S E | Box picking from a wall | 2 | ● |
| Sidewalk delivery robot (Starship-class) | W L E S | Curb climbing; navigation | 2 | ● |
| Delivery-drone winch and payload | P K C | Lowering on a tether in wind | 3 | ○ |
| Mobile manipulator (AMR + cobot) | W A S E | Fetch and place across a room | 1 | ● |

## 7. Field, inspection and extreme environments

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| Snake robot (modular, pitch and yaw) | K C S | Lateral undulation; pole climbing | 1 | ○ |
| In-pipe crawler (wall-press or inchworm) | L W C S | Navigate bends and diameter changes | 2 | ○ |
| Magnetic wall-climbing crawler (tanks, hulls) | W T S | Climb steel; adhesion margin | 2 | ○ |
| Power-line inspection robot | W K S | Cross obstacles on a conductor | 2 | ● |
| Wind-turbine blade crawler | T C S X | Grip a tapering blade | 3 | ○ |
| Skyscraper window-washing gondola robot | G C X P | Facade coverage; sway | 3 | ○ |
| **Rocker-bogie planetary rover** | L W F S | Passive terrain following; obstacle up to one wheel diameter | 1 | ○ |
| Coaxial Mars-helicopter (Ingenuity-class) | P K F | Hover and climb (thin-air aerodynamics) | 3 | ○ |
| Planetary hopper | P C | Hop trajectory | 3 | ○ |
| Bomb-disposal tracked robot with flippers and arm | T A S E | Stair climbing; manipulation | 2 | ○ |
| Firefighting robot (hose turret) | T P X E | Nozzle aiming; heat shielding | 3 | ● |
| Nuclear-decommissioning manipulator | A C F | Teleoperated cut and remove | 2 | ○ |
| Spherical rolling robot (pendulum drive) | K W E S | Steering by shifting mass | 2 | ● |
| Tensegrity rolling robot | C L | Rolling by cable actuation | 3 | – |

## 8. Marine and air

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| Vectored-thruster ROV (BlueROV-class) | P F E S | Station keeping; 6-DOF control | 3 | ○ |
| Torpedo AUV | P E K S | Depth and heading control; dive | 3 | ● |
| Hull-cleaning crawler | W T P X | Adhere to and cover a ship hull | 3 | ○ |
| Autonomous wingsail boat | P K F S | Tack and gybe | 3 | ○ |
| Underwater glider | P K E | Buoyancy-driven sawtooth path | 3 | ● |
| Quadcopter with gimbal | P F S E | Hover; waypoint flight; gimbal stabilisation | 2 | ○ |
| Tilt-rotor or tail-sitter VTOL | P K F E | Transition from hover to forward flight | 3 | ● |
| Ornithopter | K P C | Flapping lift | 3 | ○ |
| Indoor blimp | P E | Slow 3D navigation | 3 | ● |

## 9. Vehicles and personal mobility

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| Electric go-kart | W F K E | Lap following; steering geometry | 1 | ○ |
| Autonomous golf cart / shuttle | W F E S | Route following; stop for obstacles | 2 | ● |
| Self-balancing two-wheeler (Segway-class) | W S E | Balance; turning | 1 | ● |
| Self-balancing bicycle (steer or reaction wheel) | W K S | Balance at low speed | 2 | ○ |
| Ballbot | W S | Balance on a sphere | 2 | ● |
| Mecanum-wheel omni base | W F E | Holonomic motion | 1 | ● |
| Stair-climbing wheelchair (tri-star wheels or tracks) | W T L S | Climb stairs stably | 2 | ○ |
| Cargo e-trike | W F K E | Tilt-steer; load | 2 | ○ |

## 10. Kinetic, art, toys and food

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| **Strandbeest (Jansen linkage walker)** | L K F | Crank-driven walking; foot-path shape | 1 | – |
| Klann-linkage walker | L K | Step height over obstacles | 1 | – |
| Cam-driven automaton (writing / drawing figure) | K L | Cam-profile design for a target path | 2 | ○ |
| Marble machine with lift | K G | Lift and release timing | 1 | – |
| Mechanical clock or orrery | K | Gear-train ratios; escapement | 2 | ○ |
| Harmonograph / drawing machine | K C | Pendulum figures | 1 | – |
| Animatronic face (eyes, brows, jaw) | C L K E | Expression poses; lip-sync | 2 | ● |
| Table-tennis robot (ball launcher) | K X S | Serve spin and placement | 2 | ● |
| Juggling robot | A S | Catch and throw cycle | 2 | ○ |
| Robot barista kiosk (arm + espresso) | A X E | Drink sequence | 2 | ● |
| Burger-flipping gantry arm (Flippy-class) | G A X | Grill scheduling | 2 | ○ |
| Pizza assembly line | G X K | Sauce, cheese and topping dispensers | 2 | ● |
| Salad-bowl assembly line (Infinite Kitchen-class) | G K X E | Bowl conveyance; dispenser timing | 2 | ● |

## 11. Medical and assistive

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| Tele-surgical arm with remote-centre-of-motion linkage | L A C | Hold a fixed pivot at the incision | 2 | ● |
| Powered knee or hip exoskeleton | A C F | Gait assist torque profile | 2 | ○ |
| Tendon-driven prosthetic hand | C K | Grasp types | 2 | ● |
| Upper-limb rehabilitation end-effector | G A S | Guided reaching; force assist | 2 | ● |
| Patient lift / transfer robot | L A W | Lift with stability margin | 2 | ● |
| Assistive feeding arm (Obi-class) | A X S | Scoop and deliver | 1 | ● |
| Pharmacy dispensing robot | G X E | Pick packs from shelves | 1 | ● |

## 12. Unconventional locomotion (research)

| Machine | Stresses | Autonomy | Tier | Panel |
|---|---|---|---|---|
| Wheel-leg biped (Ascento-class) | W L S E | Jump and balance on wheels | 2 | ● |
| RHex-style hexapod with C-legs (whegs) | K C | Rough-terrain running | 2 | ○ |
| Jumping robot (Salto-class) | L C | Repeated wall-jumps | 3 | – |
| Brachiating robot | A C | Swing between bars | 2 | – |
| Modular self-reconfiguring cubes | K S | Change shape | 3 | ● |
| Origami or soft gripper | C | Grasp delicate items | 3 | – |
| Inchworm climber | L C S | Climb poles and trusses | 2 | – |
| Tail-assisted reorienting robot | K A | Mid-air reorientation | 2 | ○ |

## First wave

There are eight briefs. Together they cover every axis except P (fluids, which is tier 3), and four of them are panel-heavy (●). They are chosen to test breadth and the panel system on the same runs:

| # | Brief | Why it is in the wave |
|---|---|---|
| 1 | Enclosed CoreXY 3D printer | G F E X: linear motion, an extrusion frame and a boxy sheet-and-panel enclosure with doors — a panel problem unlike a creature's |
| 2 | Robot lawn mower | W X E S: a consumer product whose shell is most of what you see; a moulded shell fitted over a real chassis, the lid problem |
| 3 | Compact autonomous tractor with a three-point hitch | W L F K E: Ackermann, a closed hitch linkage, a PTO and heavy castings with hood panels |
| 4 | 3-axis CNC router | G F X: a stiffness-driven frame (STRUCTURAL.md applies), ballscrews and a spindle |
| 5 | Skid steer / compact track loader | H L T: hydraulic cylinders and the lift-arm linkage, past the servo-direct excavator |
| 6 | Rocker-bogie rover | L W S: a passive differential suspension and terrain following |
| 7 | Strandbeest | L K: a pure closed-linkage machine, a stress test of ADR-593..595 |
| 8 | Liquid-handling robot | G X E: small, precise and enclosed, with a deck layout and collision checking |

Each brief should stay design-only first, as the creature sweep did, and
then add one autonomy task from its row. Run them with Opus 5.5 in Claude
Code.

## Sources

The catalogue was drawn from these surveys, together with general knowledge of the machines:

- [The agricultural weeding-robot survey on MDPI](https://www.mdpi.com/2624-7402/6/3/187)
- [HowToRobot on fresh-produce robots](https://howtorobot.com/expert-insight/these-8-robot-solutions-automate-fresh-produce-operations-today)
- [HowToRobot on construction robots](https://howtorobot.com/expert-insight/construction-robots)
- [Modula's types of warehouse robotics](https://modula.us/blog/warehouse-robotics)
- [Open Source Manufacturing Tools on the P2P Foundation wiki](https://wiki.p2pfoundation.net/Open_Source_Manufacturing_Tools)
- [The Open Lab Starter Kit](https://github.com/Open-Lab-Starter-Kit)
- [The spherical-robot review](https://arxiv.org/pdf/2310.02240)
- [Glasgow's rocker-bogie notes](https://www.gla.ac.uk/media/media_374988_en.pdf)
- [MIT's linkage examples](https://fab.cba.mit.edu/classes/865.18/mechanisms/linkages_examples/index.html)
- [The Opentrons Flex documentation](https://docs.opentrons.com/flex/introduction/)
- [Modern methods of hull cleaning with ROVs](https://www.transnav.eu/files/Modern_Methods_of_Hull_Cleaning_Using_Remote_Operated_Vehicles,1499.pdf)
- [Axios on restaurant robots](https://www.axios.com/restaurant-automation-robots-fryer-flippy-24f400ee-67b2-4d25-8f09-d23579e7c904.html)
- [Interesting Engineering on farm robots](https://interestingengineering.com/videos/uv-robots-cotton-bots-chatgpt-on-a-broccoli-farm-the-new-face-of-farming)
