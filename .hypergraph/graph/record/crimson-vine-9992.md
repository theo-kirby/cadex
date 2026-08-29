---
node_id: ae606e35-a507-5512-8bdc-e474a6f8eb10
slug: crimson-vine-9992
title: The demo card becomes a viewport render of the biped, not its blueprint
created_at: '2026-08-29T21:45:27+00:00'
parents:
- dawn-oak-0677
summary: ''
artifacts:
- shell/scripts/addons_core/mesh_agent/demo/card.png
---
## What

The demo card art is now a viewport render of the model, replacing the
blueprint-sheet card that shipped with dawn-oak-0677. Operator direction:
the card should show the model as the viewport shows it, not a drawing
of it.

## Method

Windowed probe against the built bundle (the gate is `--background` and
`draw_view3d` refuses there): opened a copy of the shipped demo, waited
for hydration plus a 6 s settle, fitted the three-quarter `NAMED_VIEWS`
camera at 1152/720 aspect to the robot's bbox — the 400 mm ground plate
excluded from the fit by extent (>300 mm) so the robot fills the frame
with the plate as ground context — and drew offscreen via
`capture._tile_pixels` with the file's own shading (matcap + cavity).
Overlays stayed ON because the BREP edge wires draw in the overlay
wireframe pass (turning them off flattened the first attempt), with
workspace chrome (cursor, axis lines, origins, relationship lines, text)
suppressed for the draw and restored after. One probe bug worth keeping:
`bpy.app.timers.register` defaults to persistent=False, so
`open_mainfile` silently killed the first probe — windowed probes that
open files need `persistent=True`.

## Result

`card.png` 1152x720 replaced in `mesh_agent/demo/`; bundle rebuilt,
installed to /Applications (sha match confirmed), `bl_mesh_agent.py`
suite green. ADR-173 and `docs/BLENDER.md` amended before commit (both
still uncommitted). The demo remains unpushed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 268cbee80aefa415519365d66c7d23529d1f5a5d

## State Impact

- target: shy-crane-2573 — the demo card art is a 1152x720 viewport render (matcap+cavity, edge wires, three-quarter fit to the robot, chrome suppressed) per operator direction, replacing the blueprint-sheet card
