# orun20 S1h: soft head variants

Verified against source: 2026-10-24. Frozen run evidence.

Each variant builds in its own project (`~/cadex-projects/leon-soft-head-<x>`), so its head stands
beside leon I's and the current soft head's (`leon-soft` `3699a3fd`). Head measures are K2's
(`corners.py`), restricted to the head with `--part` set to `cadex hero`'s head focus:

    pixi run python docs/probes/orun20/corners.py ~/cadex-projects/leon-soft-head-a \
        --part '(^|_)(head|skull|jaw|muzzle|snout|nose|face|cheek|brow|eye|ear)'

## Variant A: the lofted head (`leon-soft-head-a`, revision `3df4a511`)

How it is built (script: the project's `script.py`, from leon-soft's with only the head changed):

- **Skull.** One smooth `lib.form` loft through cat-head-soft's nine stations, on near-elliptic
  sections (square 2.2–2.5). It replaces the faceted polyhedra (skull and muzzle blocks with
  26/18 mm creases). It has a full dome, round cheeks, an eased stop and a rounded muzzle.
- **Three panels instead of eight.** A cap (cranium, brow and bridge) and a face piece each side
  (cheek and whisker pad), parted on the philtrum. The cap's seam is the zygomatic line: it falls
  22° from behind the eye into the nose pad's opening, so no three seams meet on the skin. Every
  region is rounded `SOFT_R` (10 mm), and the cap starts `SEAM_E` clear of the face pieces,
  measured square to the seam. The panels sit on two formers cut from the loft, so the
  faceted head's flat-panel liners are gone and the skull frame's printed share returns to 0.45.
- **Ears.** Round half-discs, built from line and arc edges. The inner plate is 22 mm in radius,
  the shell 24.5 mm, and the base corners are 5 and 6 mm. The ear slots in the cap are rounded
  4 mm.
- **Nose.** A rounded inverted triangle (6 mm rounds), flush on the loft's front.
- **Unchanged.** Eyes, cameras, the jaw servo, the jaw link and its faceted-soft jaw panel (14 mm
  creases).

| Head (13 / 13 / 8 printed parts) | leon I `092997dd` | leon-soft `3699a3fd` | A `3df4a511` |
|---|---|---|---|
| head panels | 11 | 11 | **6** |
| sharp convex edge length, mm | 18,139 | 18,139 | **13,193** |
| sharp-edge share | 44.6% | 44.6% | 53.3% |
| sharp outline corners | 153 | 153 | **23** (13 jaw, 6 + 2 face, 2 cap) |
| outline corners under 4 mm | 161 | 161 | **32** |
| ear tip radius | — (hexagon, 6 sharp) | — | **23.5 mm** (base corners 5.0, 0 sharp) |

The share **rises**, even though sharp edge length falls by 27%. The share is sharp length over
all edge length, and the faceted head's crease rounds made most of its 40.7 m of edges; the loft
has few edges. Read the share together with the sharp length.

What still has a corner:

- **The jaw plate, 13.** It is leon I's faceted jaw, left unchanged.
- **The nose end, 2 on the cap and 4 on the left face.** `lib.form` ends in a flat face whose rim
  is a crease.
- **The left face's rear-bottom corner, 2.** These are at x 464, where a region round crosses the
  steep cheek.
- **The ear slots in the cap, 9 rounded at 2.9 mm.** These are 4 mm region rounds.

### G1 on A, against leon I

- **Clearance.** Static: leon I's 6 known pairs only. Swept: 37 of 37 joints, 0 failing. Panels:
  0 of 43 failing.
- **MJCF** (`mjcf_diff.py`). Joints (51), actuators (24), equalities (13), the keyframe and the
  colliding geoms (27) are identical.
- **Mass.** 31.177 kg against 31.299 kg (−0.4%).
- **Stand** (`stand.py`, 3 s on the keyframe). No NaN. The four paw balls carry 306.0 N of the
  305.8 N weight (leon I: 307.3 of 307.0), and the root settles 10.5 mm (leon I: 10.3).

### Tried and dropped on the way

- **One boss each side of the seam.** In `d98ba126` the cap and the right face piece each put a
  boss on the front former beside the nose, and they overlapped (148.5 mm³). The skin's pieces
  never see each other's screws: `_taken_screws` reads only `avoid=` skins. A `keep_clear` box
  round the bosses did nothing (`21318ae0`), because `keep_clear` screens the ray from panel to
  support, and a solid that holds the ray's start is never crossed. A 2 mm plate across those
  rays, ahead of the former, moved both bosses (`e442be94`, clean).
- **Rounding the nose-end rim.** A 10 mm fillet on the loft's nose-end rim took the edge. It is
  picked by length (212.5 mm), because a selector's `near_point` is an edge's centre. After the
  fillet, `part.skin` cannot offset the form inward by the 2.5 mm wall (`BRepOffsetAPI_MakeOffsetShape
  not done`), so it was dropped. The rim needs a form that is round by shape: a closing station,
  or a nose piece over the end.

Images: `grid-head.png` and `grid-hero.png` show leon I, leon-soft and A from K1's head and hero
cameras. `head-a-head.png` and `head-a-hero.png` are A alone. All are on the dark floor,
`--software`. The full-size images are in `/tmp/orun20/grid/`, which is not kept.
