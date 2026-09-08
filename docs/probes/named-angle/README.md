# Named-angle rendering probe

Verified against source: 2026-09-08. [Cadex-new]. ADR-239.

**Chosen route for the next unit: render accepted tessellation on the CPU in
an independently authored engine-side client.** The existing blueprint renderer
cannot run headlessly. This directory is evidence, not a CLI feature or a
replacement engine/shell. No product source changed.

The built Blender 5.3.0 Alpha bundle (2026-09-06 build) restored and hydrated the
hinged-arm recipe with the supported engine override, then refused front, top,
right and a custom orthographic iso view with:
`Blueprint rendering is unavailable in background mode; use scene_summary instead.`
`render_views` also refused. See [background.log](background.log).
The probe process exited 0 because refusal was returned as data; **zero PNGs
were produced**. The valid iso spec is `view=custom`, azimuth -45°, elevation
35.264389682754654°, projection `ortho`; literal `iso` is not a named sheet view.
Earlier exploratory calls used strings rather than objects and omitted
`view=custom`; those validation refusals were corrected before this measurement.

The first, unmodified-bundle attempt exited 1 before reaching rendering:
its engine failed to import `library_catalog_identity` from its bundled
`cadex_library_api.py`. The supported `MESH_CADEX_ENGINE` override to the fresh
staged payload isolated the rendering probe. This is a stale local bundle
finding, not evidence that the ordinary bundle works. No bundle was rebuilt.
Do not rewrite an accepted project to work around this packaging mismatch.

## Reproduce

From the repository root, using a fresh `project` and the existing build:

```sh
project=build/render-probe-11
./cadex script --project "$project" --set examples/lifecycle/hinged-arm/script.py --json
MESH_CADEX_ENGINE="$PWD/build/engine/cadex-engine-0.0.0-macos-arm64" \
  /usr/bin/time -l shell/build_darwin/bin/Cadex.app/Contents/MacOS/Cadex \
  --background --factory-startup --python-exit-code 1 \
  --python docs/probes/named-angle/background_probe.py -- "$project"
```

Capture a fresh accepted display **after** that probe: another rebuild can
remove the old attempt's tessellation paths. An exploratory use of the unknown
`tessellate` field was refused with `INVALID_DISPLAY_REQUEST`; use `quality`:

```sh
/usr/bin/time -l pixi run python - "$project" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, 'cli')
from cadex_cli.client import CadexdClient, open_project
from cadex_cli.engine import resolve_engine
root = Path(sys.argv[1]).resolve()
with CadexdClient(resolve_engine()) as client:
    open_project(client, root)
    reply = client.request('rebuild', {'display': {'quality': 'standard', 'edges': True}})
    assert reply['ok'] and reply['revision'] == reply['accepted_revision']
    (root / 'accepted-display.json').write_text(json.dumps(reply))
PY
/usr/bin/time -l pixi run python docs/probes/named-angle/tessellation_probe.py "$project"
```

The four SVGs and summary land under `PROJECT/review/render-probe/`.
Committed SVGs here are copies of this experiment's outputs. The snapshot
contains absolute attempt paths locally and is deliberately not committed.
No checkpoints, policies, rollouts, machine paths or project-store data are
committed with the evidence.

## Measurements and inspection

| Operation | Exit | Wall seconds | `time -l` maximum RSS bytes |
|---|---:|---:|---:|
| Unmodified bundle, failed restore | 1 | 5.06 | 205963264 |
| Override, hydration and four valid blueprint refusals | 0 | 1.62 | 206602240 |
| CLI client restore and display rebuild | 0 | 1.73 | 176488448 |
| CPU projection, four SVGs plus summary | 0 | 0.20 | 51609600 |

These are single warm local samples. `time -l` reports the command's maximum
RSS statistic, **not a sampled sum of simultaneous process-tree memory**.
The projection timing includes pixi/Python startup, excludes display acquisition
and preview rasterization. No training, GUI, remote execution, new installation
or full build occurred. No full CLI/engine/shell zone gate was run: only docs
and evidence changed. The experiment itself and graph checks are the validation.

Accepted revision throughout:
`de0dae7f91cb701274254132f3855ae23b2e3d40085165c946233fad4e847cc6`.
The source recipe's arm placement `[0,0,40]` is a pre-solve guess. The accepted
component transform places it at `[12,0,6]`. The probe applies each row-major
matrix once, instances `source_output`, and excludes the unposed source shapes:

| Component | Source | World bounds mm |
|---|---|---|
| base | plate | (0,0,0) to (60,60,6) |
| swing | arm | (12,0,6) to (92,8,14) |

Both bounds are asserted numerically; their union matches Blender's hydrated
bounding box `(0,0,0)` to `(92,60,14)`. Two components, 24 triangles total.
Front projected extents are 92×14 mm, top 92×60, right 60×14; iso uses an
orthonormal camera basis toward `(1,-1,1)` with world Z upright.
All four actual SVG files parsed successfully, each with 24 polygons inside
its 640×640 frame. A local Pillow raster preview of their XML polygon elements
was visually inspected: blue plate, orange arm correctly seated on its top,
extending past the plate in front/top/iso and appearing end-on from the right.
Pillow 12.1.0 was already in pixi and used only for inspection; the projection
script itself imports only the Python standard library.

## Limits and next unit

The probe is intentionally specialized to verifying the recipe's two instances.
It is not qualified for arbitrary assemblies, standalone outputs, rotations,
curved geometry, malformed/untrusted buffers, large scenes or concurrent writes.
Its triangles use centroid painter ordering and show triangulation diagonals;
that is **not** a robust hidden-surface algorithm or an engineering drawing.
The next product unit needs depth-correct visibility, validated bounded buffers,
explicit revision/pose metadata, output ownership rules and tests beyond boxes.
Hold the project lock while obtaining/consuming display paths, or copy validated
buffers into the review snapshot before releasing it: this probe encountered a
stale path after a subsequent rebuild and recovered by recapturing display.

An ordinary headless engine-only project already supplies this protocol display;
rendering need not acquire Blender, GPU context, Qt, or a new dependency. Recipe
projects keep their existing Blender geometry-runtime requirement (ADR-185).
The existing GPL renderer stays in its process; none of its implementation was
copied into the LGPL projection. This route removes the need for a renderer
subprocess and scene hydration from the prospective CLI design.

Section views can reuse the validated world-space triangle snapshot, projection
and visibility machinery. Plane clipping, section contours/caps and their
numerical/topological tests still need implementation; tessellated sections
must be labelled approximate, not exact OCCT cuts. No section result is claimed.
Render and section CLI calls, project artifact conventions, walk integration,
mode parity and their gates remain subsequent units. Headless review stays open.
