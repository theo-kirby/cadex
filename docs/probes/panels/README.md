# Panels probe — `part.envelope` / `part.panel` / `fit.panels` (ADR-633..637)

Verified against source: 2026-10-10. Provenance: `[Cadex-new]`.

Three designs built on the real engine with the new panel ops, each drawn
by the engine's own studio renderer (`cadex render`, or `CadexStudio` on the
kernel shapes for the close-ups), and each judged by `fit.panels`. The
scripts and the fit blocks are beside the images.

| | before | after |
|---|---|---|
| an electronics cover: a 2S pack and an ESP32 on a deck | (no cover) | `electronics-cover.png` |
| a gantry enclosure (a CoreXY-sized cell, `enclosure.py`) | `enclosure-before.png` | `enclosure-after.png`, `enclosure-after-back.png` |
| the leopard (`cfix-leopard-a`, copied; `leopard_panels.py`) | `leopard-before.png`, `leopard-torso-before.png` | `leopard-after.png`, `leopard-torso-after.png`, `leopard-torso-after-back.png` |

## Electronics cover

`part.envelope([pack, board], clearance=1.5, radius=20)` and one
`part.panel(..., side=+Z, max_angle=70, seams=[((1,0,0), [0])],
flange="frame", frame=deck, screw=lib.bolt("m2", 8), screws=3)`. The cover
is flat over the pack, bends down over the lower board in a 20 mm-radius
curve, hangs a skirt to the deck (15 mm median, cut short where the board's
pins come near), and is held by six M2x8s: towers inside the skirt and lugs
outside it, each counterbored so the one stocked length seats with 3.4 mm
of thread in the deck. Nearest approach to the contents 1.39-1.75 mm (the
clearance is 1.5). This is the real-kernel test in `test_panels.py`.

## Gantry enclosure

An extrusion frame with a gantry whose head slides 160 mm in X. The envelope
is the frame, the gantry and the bed with the head's travel swept in, at
`radius="hull"`: a finite rolling ball always dips into an open frame face,
the hull does not. A lid and three side covers (`side=` ±X, +Y,
`max_angle=40`, `inset=0.4`), each seamed once so a piece fits a 256 mm bed,
six M3x8s per cover into the posts and rails, a cable-gland hole in the
back, `avoid=[...]` so no two covers' screws meet in one corner post (the
first build without it put three screws into the same post corner, and the
fit named all three intersections). `enclosure-fit.json`: fit `pass`, sweep
`pass`, eight pieces `pass`, egg ratios 1.41-1.60 (an enclosure encloses
its working space; this is why the egg finding is advisory), seams 0.6 mm,
three screws a piece, the farthest point 100-132 mm from a screw.

## Leopard

`cfix-leopard-a` had no panels at all (the 2026-10-09 runs left them "to
come"). Added (`leopard_panels.py`): a rear cover over the Pi 5, the IMU and
the rear keel (`radius=30`, `flange="frame"`, split at x = -150 for the
electronics and the bed, two M2.5x8 each), a front keel cover kept behind the
neck housing (`within=`), and a head cover that ends behind the camera and
opens round the neck link swept through the head's ±35° nod. The first
draft failed `fit.panels` twice, correctly: the front cover ran through the
neck drive and the neck link, and the head cover's skirt was struck by the
nodding neck link. After the fixes, `leopard-fit.json`: fit `pass`, four
panels `pass`, p90 gaps 3.5-9.6 mm, egg ratios 1.06-1.17, wall 2.0 mm.

**What it does not yet show.** The leopard's torso is a slim keel between
twelve exposed drives, so its covers are lids, not a body shell: covering
its sides needs side panels with openings round each hip housing and the
yokes' motion, and a cover that wraps further than one side's height field
needs several panels meeting at a seam. Both are expressible but not done
here. The leopard build took 430 s of a raised 1200 s budget; the panel
plans are 2-15 s each, and most of the rest is the fit's exact pair
measurement between B-spline covers and the large frames.

## How the images were made

`cadex script --set` and `cadex render` on scratch copies (never the
originals under `~/cadex-projects/`), under `ulimit -v 25000000` (ADR-637).
The close-ups draw the kernel shapes with `CadexStudio._prepare/studio` on
the same dark floor.
