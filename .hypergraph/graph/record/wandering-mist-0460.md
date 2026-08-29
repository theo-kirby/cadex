---
node_id: 85f965f9-af1b-5543-8dc7-e78fde9ee5ad
slug: wandering-mist-0460
title: 'ADR-167 addendum: the landing screen restyled native — theme greys, the logo mark, rounded geometry'
created_at: '2026-08-29T10:31:02+00:00'
parents:
- lucid-otter-3511
summary: ''
---
## What

ADR-167 addendum: the landing screen restyled to the operator's feedback —
functionally unchanged, cosmetically native.

1. **Theme colours, no palette of its own.** `_palette()` reads the running
   theme: scrim from the viewport ground, widget fills from
   `wcol_regular.inner` composited at the theme's own alpha, text/outline
   from the same widget theme, hover by brightening. The blue constants are
   gone; `_FALLBACK` greys remain for a themeless session.
2. **The logo mark.** `docs/images/cadex-mark.svg` rasterized at 512 px to
   `mesh_agent/landing_logo.png` (git-LFS). QuickLook (the only available
   rasterizer) bakes a white page behind the alpha — every pixel came back
   alpha=255 — so the border-connected near-white component was flood-keyed
   to transparent with scipy.ndimage.label, plus a 2-px luminance-keyed
   antialiasing ring; the glyph's interior whites survive by construction.
   Drawn spanning the wordmark + tagline block.
3. **Rounded corners by geometry.** `rounded_rect_points(rect, radius,
   segments)` — pure, convex, CCW, clamped radius — fan-triangulated into
   TRIS (Metal dropped TRI_FAN); borders are LINE_LOOPs of the same points;
   the card image rounds by mapping UVs onto the same polygon, no mask
   pass. Radii: buttons 6 px, card 10 px, scaled.
4. **Card art** switched from the blueprint render to the shaded
   three-quarter (`demo/card.png`) — the blueprint blue was most of the
   blue on the page.
5. Fonts: already `blf` font 0, the app's UI font — verified, unchanged.

## Why

Operator feedback on the shipped page: "I don't want the blue style — go
with the default colors of the UI, the two-tone gray"; "put our logo in
there — we have a logo SVG"; "a little more modern — rounding on the
corners of the frame and the buttons"; "same fonts as the rest of Cadex".

## Method

Texture loading generalized to `_gpu_texture(relative_path)` with one
module cache (image → numpy → gpu.types.Buffer, datablock removed).
Palette cached per `show()` so a theme change is picked up next launch.
Tests extended: `rounded_rect_points` purity (28 points, stays inside its
rect, zero-radius degenerates, oversize radius clamps) and the logo file
pinned shipped. Suite "All tests passed"; `pixi run gate` green after a
real build-shell; windowed probe screenshots confirm the mark on
transparent alpha (first attempt showed the baked white box — caught by
screenshot, fixed by the flood key), theme-grey card and buttons, rounded
corners, "soon" tag inside the Tutorial button.

## Result

The page looks like the app: same greys, same font, same widget language,
plus the mark. Docs updated in place (BLENDER.md row + section, ADR-167
addendum). Uncommitted with the rest, on `114e90ec`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 114e90ec6d2f973c06f48a3b8e4ccd286b75422f

## State Impact

- target: shy-crane-2573 — the landing screen draws in the running theme's greys with the logo mark and rounded corners; no palette of its own to maintain
