# orun20 K2: leon I's corner measures

Verified against source: 2026-10-24. Frozen run evidence.

One command reads a project's accepted build and prints both K2 numbers:

    pixi run python docs/probes/orun20/corners.py ~/cadex-projects/leon --json leon-i.json

It opens no engine and writes nothing into the project: `script.json` names the accepted revision
and digest, and the attempt under `script_artifacts/<revision>/` whose `result.json` carries that
digest has every output's facts and BREP. 48 panels measure in about 8 s. The method is in the
script's docstring; `leon-i.json` here is its whole output for leon I.

## Leon I, revision `092997dd`

| Measure | Value |
|---|---|
| sharp-edge share (the concept sheet's `sharp_outside_edge_share`) | **68.9%** (151,888 of 220,579 mm, 98 printed components, 0 unresolved) |
| shell panels (`role="panel"`) | 48 |
| smallest outline-corner radius | **0 mm** (every panel has sharp corners) |
| outline corners under 4 mm | **321**: 313 sharp, 8 rounded under 4 mm |
| rounded outline corners (radius < 50 mm) | 38, all on the head (cranium 13, masks 6 + 6, muzzles 7 + 6) |

By panel family: body, limb, neck and tail panels have 4 sharp corners each (chest dorsal 8,
ribs 6, loins 6), the corners of their box and slab regions. The head's faceted panels have the
most: brow 25, cranium 24, masks 16 and 17, muzzles 15, jaw 13, cheeks 8, and each ear 6
(a beveled polygon, no rounded corner). The per-panel table is what the script prints.

## What the outline-corner measure counts

- The skin is grown from a panel's largest face into neighbours at least 1.5 panel thicknesses
  wide, across edges where it turns by under 50°. Faceted creases are crossed. The rim, the
  edge fillets and the screw bosses are not part of it.
- The outline is the skin's boundary. A loop under 40 mm is a screw hole and is skipped.
- A **sharp corner** is an outline vertex that turns by more than 30° in the skin's tangent
  plane. The bend in the panel's surface is not a corner.
- A **rounded corner** is an outline edge whose smallest geodesic radius is under 50 mm. The
  geodesic radius is the outline's curvature radius measured in the skin's tangent plane.

Checked on synthetic panels, a 2.5 mm shell on a 200 mm cylinder cut by a 160 × 120 rounded
rectangle:

| Corner radius of the region | Measured |
|---|---|
| 0 | 4 sharp corners |
| 3 mm | 4 rounded at 2.86 mm |
| 8 mm | 4 rounded at 7.62 mm |

A two-facet shell with a 30° crease, cut by a box, measured 4 sharp corners, and its crease was
not counted.

On a sloping skin the measured radius comes out a little under the region's radius, because the
radius is taken on the surface. A soft style that wants at least 6 mm should round its regions
by about 7 mm.

The sharp-edge share is computed as `CadexStudio.edge_proxy` computes it, from the engine's
`sharp_edges` facts.
As a cross-check, `cadex render` was run on a scratch copy of leon (`cp -a`, then
`./cadex --project <copy> render`). That rebuilt `092997dd` and drew the concept sheet's measure as
0.6886, from 220,578.622 mm of edges, 151,888.47 mm of them sharp, over 98 printed components. That
is the script's figure exactly. `render` commits into the project it reads, as `inventory` does,
so run it only on a copy.
