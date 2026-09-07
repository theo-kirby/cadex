---
node_id: 2eb15d4d-9b79-50f5-a1fe-93501ba96295
slug: zesty-aspen-6846
title: Named-angle probe selects CPU tessellation after background renderer refusal
created_at: '2026-09-07T23:02:08+00:00'
parents:
- clear-ash-2884
summary: ''
artifacts:
- docs/probes/named-angle/README.md
- docs/probes/named-angle/background.log
- docs/probes/named-angle/front.svg
- docs/probes/named-angle/top.svg
- docs/probes/named-angle/right.svg
- docs/probes/named-angle/iso.svg
---
## What

Probed named-angle rendering from an accepted hinged-arm revision, recorded
ADR-239's CPU tessellation route before implementation, and retained reproducible
probe scripts, the four SVGs and the valid background refusal log under
docs/probes/named-angle/. Ticked only the ROADMAP probe item.

## Why

Follow clear-ash-2884 and the overseer's explicit rendering-probe dispatch.
Advances the charter criterion “The agent can see its work without a screen”
(damp-moon-9297), missions 6 and 2. Choose the reversible engine-only route after
measuring the existing renderer; do not expand the unit into CLI implementation,
section integration, a bundle rebuild or a lifecycle rerun. No human question,
state edit, plan edit or reconcile was needed.

## Method

The complete commands, scripts, dependencies and measurements are in
`docs/probes/named-angle/README.md`. Create the documented hinged-arm recipe
with the public `cadex script` entry point into build/render-probe-11. Invoke
Cadex.app/Contents/MacOS/Cadex with --background --factory-startup
--python-exit-code 1 and the probe script. Ensure the project opens/restores and
hydrates before calling render_blueprint for front/top/right/custom ortho iso
(azimuth -45, elevation 35.264389682754654); also invoke render_views.

The ordinary bundle failed before rendering: cannot import
library_catalog_identity from its bundled cadex_library_api.py. Repeat using
the supported MESH_CADEX_ENGINE override to the freshly staged payload.
Early calls with invalid view shapes were corrected before the final valid
four-view probe; iso needs view=custom. Literal strings and missing view keys
exercise validation, not the renderer. Preserve that distinction in the report.

Acquire accepted display through the LGPL CLI client: open_project with restore,
then rebuild(display={quality: standard, edges: true}). An initial exploratory
unknown tessellate field was refused; the corrected call succeeds. Render with
an independently authored standard-library script, reading little-endian float32
vertices and uint32 triangles, applying each component's row-major placement
once through source_output and excluding unposed definition copies. Another
rebuild invalidated old attempt paths during the experiment; recapturing display
fixed it. Record the snapshot/lock requirement for production.

Measure with /usr/bin/time -l. Parse the four actual SVG files, assert 24 polygons
inside each 640x640 frame, rasterize their XML polygon elements using existing
Pillow 12.1.0, and visually inspect the contact sheet. Pillow is inspection-only;
no renderer dependency was installed. No training, GUI or remote dispatch.

## Result

Unmodified bundle: exit 1, 5.06 s, maximum RSS 205963264 bytes, stale bundled
engine import failure. Supported override: exit 0, 1.62 s, maximum RSS
206602240 bytes; accepted model hydrates but all four valid blueprint calls
return the explicit background-mode refusal, and render_views refuses too.
No Blender PNG exists. The exit 0 is successful observation of returned errors,
not a successful render. Log retained as background.log. No bundle rebuild was
attempted; ordinary bundled lifecycle operation is not qualified by this probe.

Accepted revision is de0dae7f91cb701274254132f3855ae23b2e3d40085165c946233fad4e847cc6.
Display acquisition exit 0: 1.73 s, maximum RSS 176488448 bytes. CPU projection
exit 0: 0.20 s, maximum RSS 51609600 bytes including pixi/Python startup,
excluding display acquisition and inspection. These are warm single samples;
maximum RSS is the time command statistic, not a sampled simultaneous process-tree
sum. Standard-library projection needs no Blender or graphics context.

Two components, 24 triangles. Asserted base bounds (0,0,0)..(60,60,6) mm and swing
bounds (12,0,6)..(92,8,14) mm; union matches Blender hydration. This uses the
accepted solved translation (12,0,6), not the authored initial (0,0,40). Front
extent 92x14 mm, top 92x60, right 60x14. The four views were parsed, checked
nonblank and visually inspected: plate and arm have the expected orientation,
seating and overhang. Project-relative outputs are review/render-probe/front.svg,
top.svg, right.svg, iso.svg and summary.json; committed SVG copies carry no
machine paths. No project state, policy or rollout is committed.

Chosen route: accepted-tessellation CPU rendering, independently authored on the
engine side. The experiment uses centroid painter ordering and exposes triangle
diagonals: not production occlusion, engineering drawings, curved-geometry or
large-assembly qualification. Rendering needs bounded buffers, revision-safe
snapshots, correct visibility and broader fixtures before integration. Sections
can reuse transformed triangles/projection but need clipping, contours/caps and
approximation labels. Ordinary engine-only projects need no Blender renderer;
Blender recipe geometry retains its ADR-185 runtime dependency.

No product code, protocol, payload or shell source changed: no zone suite or full
build ran. Probe execution, placement assertions, SVG inspection and git diff
--check passed. Graph export/check is run after minting and must pass before the
single commit. Headless-review remains open: render/section CLI calls and walk
integration are still missing before the charter criterion can be ticked.
The tail becomes three unreconciled records including this one; the separate
maintainer owns that pass. Next work is product rendering on the recorded route;
the stale local bundle must be refreshed before claiming bundled verification.
Dispatch closed: 1 unit — measured background-render refusal and selected accepted-tessellation CPU rendering with four inspected views.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 915c3dd9e847ad2f67bd9c1de3b752c126697255

## State Impact

- target: damp-moon-9297 — Valid front/top/right/iso blueprint calls refuse background rendering after accepted hydration; ADR-239 selects independent CPU tessellation rendering with four inspected placement-correct SVG probes. Product render, sections and walk integration remain open.
- target: early-arbor-7123 — Rendering probe observed stale local bundle engine import failure for library_catalog_identity; supported MESH_CADEX_ENGINE override to fresh stage restores correctly. Ordinary bundle remains unverified pending refresh.
