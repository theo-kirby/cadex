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

## Variant B: lofted jaw, round ends (`leon-soft-head-b`, revision `77ee9670`)

B is A with its two remaining corners removed by shape. The jaw is lofted, and the nose and chin
end in round tip pieces. The script is `~/leon-queue/leon_soft_head_b.py`.

- **Jaw.** A `lib.form` loft of five stations replaces leon I's faceted jaw polyhedron. Each
  section is inscribed 2 mm inside the old jaw's planes, checked numerically, so the jaw never
  swings wider than the faceted one did. The jaw former is cut from the loft (`former_`, not
  `block_former`). The polyhedron helpers (`planes`, `halfspace`, `block`, `block_former`) are
  gone from the script.
- **Round ends, by shape.** Each loft's flat end is capped by an ellipsoid on the end's own axis.
  The cap meets the end ring on the loft's taper: for a cap of length a set back d, the slope at
  the ring is r·d/(a²−d²), so a² = d² + d/k, where k is the taper over the radius (skull 0.034,
  chin 0.021). The cap's axes are 1.5% over the ring.
- **Tip pieces.** The skin cannot offset the loft fused with its cap (b-1: `BRepOffsetAPI_MakeOffsetShape
  not done`, the same refusal as A's rim fillet). So the panels are cut from the plain loft and
  stop `SEAM_E` short of x 614 (nose) and x 584 (chin). Each end is then a shell piece of its own:
  the hull (loft ∪ cap) less the inner hull (the loft offset in by the wall, ∪ the cap shrunk by
  the wall). No fused form is ever offset. Each tip sits on a 3 mm liner `panel_clear` inside it,
  fused to the skull frame or the jaw link. Bars carry the muzzle tip's liner, and the nose pad's
  stem now runs to the hull.
- **Ear slots** in the cap are rounded 6 mm (A: 4). The right slot took the full 6 mm. The kernel
  reduced the left slot's round (`on_failure="reduce"`), so it still reads 2.95 mm.
- **Unchanged from A.** The cap and face pieces, the ears, the eyes and cameras, the jaw servo, the
  link and the hinge.

| Head | leon I `092997dd` | leon-soft `3699a3fd` | A `3df4a511` | B `77ee9670` |
|---|---|---|---|---|
| head panels | 11 | 11 | 6 | **8** (+ muzzle tip, jaw tip) |
| sharp convex edge length, mm | 18,139 | 18,139 | 13,193 | 14,900 |
| total edge length, mm | 40,695 | 40,695 | 24,752 | 24,788 |
| sharp-edge share | 44.6% | 44.6% | 53.3% | 60.1% |
| sharp outline corners | 153 | 153 | 23 | **0** |
| outline corners under 4 mm | 161 | 161 | 32 | **4** (the left ear slot, 2.95 mm) |
| smallest corner on the face pieces, muzzle and jaw | 0 | 0 | 0 | **5.82 mm** (muzzle tip 7.72, jaw 28.1, chin 23.5) |

Sharp length rises 1,707 mm over A. The face panels lose 672 mm (cap −251, face pieces −206 and
−215). The new structure adds more: the tip pieces' cut rims add 911 mm, the liners and bars add
906 mm to the skull frame, the jaw link's loft former and bar add 287 mm, and the jaw plate's rim
adds 276 mm. The share rises because the edge total barely moves. Read the share, the sharp length
and the corner count together.

**A fix to K2 (`corners.py`).** A periodic face's seam edge has that one face on both sides, so the
measure counted it as outline. Where a flat cut crossed a loft's seam, it then reported a 90°
corner. The revision before this one (`11342ce6`, no tip liners) showed 4 such false corners, on
the jaw plate (2), the jaw tip (1) and the muzzle tip (1). Seams (`Edge.isSeam`) are now inside the skin. Re-measured with the fix, leon I's
head, leon-soft's head and A's head are unchanged, and so is leon I's whole-model K2 baseline
(68.9%, 313 sharp, 321 under 4 mm).

### G1 on B, against leon I

- **Clearance.** Static: leon I's 6 known pairs only, of 7,503 checked. Swept: 37 of 37 limited
  joints complete, 0 failing pairs; the jaw's nearest moving pairs are leon I's (servo 0.6 mm,
  skull frame 1.7 mm). Panels: 0 of 45 failing.
- **MJCF** (`mjcf_diff.py`). Joints (51), actuators (24), equalities (13), the keyframe and the
  colliding geoms (27) are identical.
- **Mass.** 31.218 kg against 31.299 kg (−0.26%).
- **Stand** (`stand.py`, 3 s). No NaN. The paw balls carry 306.7 N of the 306.3 N weight, and the
  root settles 10.4 mm (leon I: 10.3).

### Tried and dropped on B

- **The fused hull as the skin's form** (b-1). It was refused: `part.skin` cannot offset a loft
  fused with its cap. This held in an OCCT lab for caps 1.000–1.12× the ring. The plain loft offsets.
- **Closing the loft on a vertex** (lab). It offsets (join 2), but the end is a cone point: the
  half-thickness grows linearly behind the tip, which means radius 0.
- **Tips on bars alone** (`11342ce6`). Both failed the panel gate as floating: the inner face's
  p90 gap was 21.2 mm and 19.7 mm, against an 8 mm limit. Hence the liners.
- **An axis-level nose cap** (`82639212`). The skull's last station is square to a path that falls
  10.6°, so a level cap left a sliver of the flat end. That gave 6 sharp corners on the muzzle
  tip. The cap now takes the last segment's axis.

Images: `grid-head.png` and `grid-hero.png` show leon I, leon-soft, A and B from K1's head and hero
cameras. `head-a-*.png` show A alone and `head-b-*.png` show B alone. All are on the dark floor,
`--software`. The full-size images are in `/tmp/orun20/grid/` and `/tmp/orun20/gridb/`, which are
not kept.
