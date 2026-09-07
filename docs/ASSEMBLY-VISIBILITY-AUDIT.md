# Assembly camera visibility qualification

Verified against source: 2026-09-07

[Cadex-new] ADR-228; audit only. The `hide_render` gap is reproduced and
qualified for the next implementation unit. No application code changed.

## Experiment

Run the built Cadex headlessly through the environment-scrubbing wrapper:

```bash
bash package/app/build_app.sh exec \
  shell/build_darwin/bin/Cadex.app/Contents/MacOS/Cadex \
  --background --factory-startup --python-exit-code 1 \
  --python /tmp/cadex-52-probe.py
pixi run gate
```

The temporary probe is deliberately not a shipped test. To reconstruct it:
load the source `mesh_agent` after unregistering/purging the bundled module
(the preamble in `bl_mesh_agent_cadex.py` does this). Write a real v1
sidecar/binary containing a unit square in XY, vertices
`(-.5,-.5,0), (.5,-.5,0), (.5,.5,0), (-.5,.5,0)`, triangles
`(0,1,2), (0,2,3)`, one face range and a closed five-vertex edge polyline.
Call `hydrate_display` with that tessellation for `source` at x=-2 and
`ordinary` at x=0, plus `posed` referencing `source_output=source` at x=2.
Use row-major 4x4 translation matrices. This exercises actual sidecar reads,
mesh creation, component sharing, edge parenting and visibility ownership;
it does not exercise engine generation of the supplied display response.

Render with EEVEE, a white emission material, transparent film and an
orthographic camera at (0,0,10), zero rotation, scale 8, 256x128 pixels.
Read the saved PNG's alpha and count pixels above .5 in column bands
[32,96), [96,160), [160,224), over all rows. The original implementation
produced **1024 / 1024 / 1024** source/ordinary/posed pixels. Temporarily
setting `hide_render=True` only on objects with `cadex_hidden_source`
produced **0 / 1024 / 1024**. This intervention was undone before the
remaining transition probes. Edges are loose mesh edges: their flags were
measured separately; this image does not prove visible edge rasterization.

The first attempt selected Cycles and failed before rendering: the bundle's
engine enum contains only `BLENDER_EEVEE` and `BLENDER_WORKBENCH`. EEVEE
completed both camera renders without a GUI. No renderer build is needed.

## Observed ownership and qualified boundary

`cadex_hydrate._hide_instanced_sources` owns the source visibility decision.
It visits Model recursively, including Assembly, skips component solids,
and hides source solids **and source edge companions** by output id.
Components share mesh datablocks but have independent object visibility.

- First hydration: source solid/edges have viewport hidden, render visible,
  and `cadex_hidden_source=True`. Posed solid/edges and ordinary solid/edges
  have both channels visible and no marker.
- Repeated identical hydration retains these states. Explicit viewport,
  render and `hide_set` hiding of the ordinary solid survives the repeat.
- Removing the component from the response deletes its solid/edges and the
  empty Assembly collection. The retained source solid/edges become viewport
  visible and lose the marker; render visibility was never changed.
- A source explicitly hidden in both channels before instancing loses its
  prior viewport hiding after instancing is removed, but retains render
  hiding. The existing marker is set unconditionally: its comment promises
  more preservation than it implements for sources. Unrelated hidden outputs
  are preserved. Do not mistake that marker for a saved prior render value.
- `cadex_sheet._apply_hides` owns `hide_set` independently. Collision, cage,
  section and wire-path helpers explicitly set render hiding themselves.

The smallest qualified render fix stays in the owned hydrator and its owned
shell tests. Hide instanced source solids/edges from renders, retaining posed
components and ordinary outputs. Track render changes independently: acquire
ownership only on a false-to-true render transition; release only that owned
change when instancing ends. Repeated hydration must retain ownership. A
pre-hidden render source must stay hidden after removal, including an object
with a legacy viewport marker but no new render marker. Leave unrelated
objects, `hide_set`, helper objects and the existing viewport policy alone.
The pre-existing viewport restoration limitation is recorded, not silently
expanded into this render fix. Manual visibility changes made during an owned
hide cannot be distinguished from the already-true flag; no override UI is
proposed.

## Implementation validation obligation

Add a permanent regression in `shell/tests/python/bl_mesh_agent_cadex.py`:
actual hydration plus the camera/count assertion above must fail on old
source and pass after the fix. Assert source and component edge flags too;
repeat hydration, remove instancing, and cover initially render-hidden
sources, legacy viewport markers, unrelated explicitly hidden outputs and
`hide_set`. Keep the camera fixture independent of arbitrary scene contents.
Run `pixi run gate` headlessly. Its suite deliberately reloads source startup
code, so a Python-only hydrator edit does not require a full shell build to
exercise that edit; do not claim it updates the installed startup copy.
If a build is needed, use `pixi run build-shell`, at most once.

Update BLENDER/IDEAS, the ADR and a ROADMAP checkbox when the fix lands.
Neither the general headless review tools nor rollout video is delivered by
this fixture. No inherited Blender file, engine protocol or payload changes
are qualified here.

Baseline `pixi run gate` exited 0 with `ok: true`: bundled engine discovered,
372/372 picks, median slider latency 0.523 s against the 0.65 s bar, and one
model object on reopen. The temporary EEVEE probe exited 0. No build ran.
