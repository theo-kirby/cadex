# orun20 S1: how to round a panel's outline corners

Verified against source: 2026-10-24. Frozen run evidence.

Leon I's panels are cut by `part.skin` from the designed form: each piece is the skin's wall
common with its region, less the regions before it grown by the seam gap, less the openings
(`CadexEnvelope.py`, the skin's builder). The regions are boxes, so every corner of a panel's
outline is where a box edge pierces the skin. Two ways to round them were tried.

## Fillets on the cut panel: refused too often

`fillet_lab.py` takes each built leon I panel (revision `092997dd`), picks the edges through
its thickness at every sharp outline corner, and fillets them at 7 mm, then at 4.2 and 2.45:

| Radius the kernel took | Panels |
|---|---|
| 7 mm | 17: the 14 tail panels, both shins, `saddle_flank_r` |
| 4.2 mm | 4 |
| 2.45 mm | 10 |
| none (refused at 2.45 too) | 17: every head panel (`BRep_API: command not done`), both ears (no edges it can blend) |

The kernel refuses most panels at 7 mm, so the outlines would not round evenly. Sharp corners
would fall only from 313 to 183. This is dropped as the way to round outlines.

## Rounded regions: every corner rounded

`saddle_lab.py` rebuilds leon I's saddle skin alone: its form, its three regions, 2.5 mm wall,
and the 3 mm seam gap. It builds them twice, once as leon I's boxes (A) and once with every
region edge filleted 7 mm (B). A box takes a fillet on every edge every time. In B, each flank
region starts a gap plus 0.2 mm past the saddle's side, so the earlier region's grown outline
does not trim the flank. A trim would cut the flank's round off at an angle and leave a corner.
The seam stays 3.2 mm wide, where leon I's was 3 mm.

    ./cadex --project <scratch> script --set docs/probes/orun20/s1/saddle_lab.py
    pixi run python docs/probes/orun20/s1/measure_lab.py <scratch>

| Piece | A: boxes (leon I) | B: rounded 7 mm |
|---|---|---|
| saddle | 4 sharp | 0 sharp, 4 rounded at 6.70–6.77 mm |
| flank l | 4 sharp | 0 sharp, 5 rounded at 6.19–6.87 mm |
| flank r | 4 sharp | 0 sharp, 6 rounded at 6.19–7.35 mm |

Each piece measures with no unresolved corners. A 7 mm region round reads 6.2–6.8 mm on the
skin, because the radius is taken on the sloping surface (K2's note). It clears S1's 6 mm.

## What the roll-out needs

- Fillet every region and every opening r 7, or as much as the region's thinnest side allows.
- Where a later region meets an earlier one, start it a seam gap (plus 0.2 mm) away, rather
  than overlapping and leaning on the grown-region trim.
- A limb's region is a slab common with a half-space. Rounding that common rounds the corners
  at its ends.

## The roll-out on leon-soft (revision `3699a3fd`)

Every body region in leon-soft's script is rounded: chest, saddle, pelvis, both necks, every
limb plate and the fourteen tail plates. The head and ears are not yet touched. The script's
helpers are `rnd` (`part.fillet(shape, SOFT_R, on_failure="reduce")`), `rbox` and `xz_prism`.

- Each region and opening is filleted on every edge. A limb's or tail's slab common its
  half-space is rounded after the common.
- Where a later region meets an earlier one, it starts `SEAM_E = panel_gap + 0.2` (3.2 mm) away.
  This applies to the ribs, saddle flanks, pelvis loins, neck sides, and the right tail plates.
- The chest's rib region (two fused boxes in leon I) is one stepped prism, so its inner corner
  is rounded too.
- Two taste calls changed a panel's outline:
  - The dorsal chest panel is narrowed from y ±40 to ±30.8, inside the shoulder openings' y 34.
    At ±40 the openings cut its front corners square (4 sharp corners in the first build).
  - The pelvis loin panels start at z 433, the top of leon I's thigh-clearance notch, rather
    than 412. Under the notch, leon I left a 7 mm strip that cannot take the round.

Two builds were made:

| Build | `SOFT_R` | Body panels with a sharp corner | Smallest body-panel corner |
|---|---|---|---|
| `d795741d` | 7 mm | 1 (dorsal: 4 corners cut by the shoulder openings) | 4.29 mm (rib, steep skin) |
| `3699a3fd` | 10 mm | 0 of 37 | 6.42 mm (ribs); limbs 7.39–8.61, tails 9.94–9.98 |

A 10 mm region round reads 6.4–10 mm on the skin, because a round taken on a sloping skin
reads small. Both builds keep leon I's six static pairs, have 0 failing panels of 48, and
a swept check of 0 failing pairs (incomplete in-build, as leon I's).

Across the whole build, the counts are those of leon I before them:

| Measure | leon I `092997dd` | leon-soft `3699a3fd` |
|---|---|---|
| Sharp corners | 313 | 153 |
| Corners under 4 mm | 321 | 161 |
| Rounded corners | 38 | 225 |
| Sharp-edge share | 68.9% | 68.5% |

All 153 sharp corners left are on the 11 head panels: skull ×9, both ears, the jaw plate. The
sharp-edge share hardly moves. It sums every printed component's sharp convex edge length,
and the frames, links, housings and panel rims dominate it, not panel outlines. Bringing it
"well below" leon I's needs those edges rounded too.

`rollout/` holds the `corners.py` JSON and K1's six views, scaled like `k1/`.
